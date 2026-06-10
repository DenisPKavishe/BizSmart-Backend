from core.logging_utils import log_activity
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
import csv
from io import StringIO
from django.http import HttpResponse
from .models import AuditLog
from .serializers import AuditLogSerializer
from core.permissions import IsAuditorUserReadOnly
from drf_spectacular.utils import extend_schema
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer
from .permissions import (
    CanRegisterUsers,
    CanViewUsers,
    CanManageUsers,
    IsAuditorUserReadOnly
)
from .email_service import EmailService


# ======================================================
# PUBLIC TEST
# ======================================================
@api_view(['GET'])
@permission_classes([AllowAny])
@extend_schema(description="Test endpoint to verify Swagger is working")
def public_test(request):
    return Response({"message": "Swagger is working!", "status": "ok"})


# ======================================================
# REGISTER USER
# ======================================================
class RegisterView(APIView):
    """
    Register a new user.
    Access: Only Owner and Manager
    """

    def get_permissions(self):
        if getattr(self, 'swagger_fake_view', False):
            return [AllowAny()]
        return [IsAuthenticated(), CanRegisterUsers(), IsAuditorUserReadOnly()]

    @extend_schema(
        request=RegisterSerializer,
        responses={201: UserSerializer}
    )
    def post(self, request):
        self.check_permissions(request)

        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)

            log_activity(
                request=request,
                action='CREATE',
                module='auth',
                description=f"New user {user.email} registered",
                details={'role': user.role.name if user.role else None}
            )


            # Send welcome email
            password = request.data.get('password')
            EmailService.send_welcome_email(user, password)

            return Response({
                'message': 'User registered successfully',
                'user': UserSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ======================================================
# LOGIN
# ======================================================
class LoginView(APIView):
    """
    Login to get access token.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        request=LoginSerializer,
        responses={200: UserSerializer}
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)

            log_activity(
                request=request,
                action='LOGIN',
                module='auth',
                description=f"User {user.email} logged in",
                details={'method': 'password'}
            )

            return Response({
                'message': 'Login successful',
                'user': UserSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            })

        return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)


# ======================================================
# LOGOUT
# ======================================================
class LogoutView(APIView):
    """
    Logout user and blacklist refresh token.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'refresh': {'type': 'string'}
                }
            }
        },
        responses={200: dict}
    )
    def post(self, request):
        log_activity(
            request=request,
            action='LOGOUT',
            module='auth',
            description=f"User {request.user.email} logged out",
            details={'method': 'token'}
        )
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()

            return Response({'message': 'Logged out successfully'})

        except Exception:
            return Response({'message': 'Logged out successfully'})


# ======================================================
# PROFILE
# ======================================================
class ProfileView(APIView):
    """
    Get or update profile.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: UserSerializer})
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    @extend_schema(
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'phone': {'type': 'string'},
                    'username': {'type': 'string'},
                }
            }
        },
        responses={200: UserSerializer}
    )
    def patch(self, request):
        user = request.user

        if 'phone' in request.data:
            user.phone = request.data['phone']

        if 'username' in request.data:
            user.username = request.data['username']

        user.save()

        return Response(UserSerializer(user).data)


# ======================================================
# USER LIST
# ======================================================
class UserListView(APIView):
    """
    List users in business.
    """

    def get_permissions(self):
        if getattr(self, 'swagger_fake_view', False):
            return [AllowAny()]
        return [IsAuthenticated(), CanViewUsers(), IsAuditorUserReadOnly()]

    @extend_schema(responses={200: UserSerializer(many=True)})
    def get(self, request):
        self.check_permissions(request)

        from .models import User
        users = User.objects.filter(business=request.user.business)

        return Response(UserSerializer(users, many=True).data)


# ======================================================
# USER DETAIL
# ======================================================
class UserDetailView(APIView):
    """
    Retrieve, update or delete user.
    """

    def get_permissions(self):
        if getattr(self, 'swagger_fake_view', False):
            return [AllowAny()]

        if self.request.method == 'GET':
            return [IsAuthenticated(), CanViewUsers(), IsAuditorUserReadOnly()]
        return [IsAuthenticated(), CanManageUsers(), IsAuditorUserReadOnly()]

    @extend_schema(responses={200: UserSerializer})
    def get(self, request, user_id):
        self.check_permissions(request)

        from .models import User
        try:
            user = User.objects.get(id=user_id, business=request.user.business)
            return Response(UserSerializer(user).data)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)

    @extend_schema(
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'role_id': {'type': 'integer'},
                    'is_active': {'type': 'boolean'},
                    'phone': {'type': 'string'},
                }
            }
        },
        responses={200: UserSerializer}
    )
    def patch(self, request, user_id):
        self.check_permissions(request)

        from .models import User, Role

        try:
            user = User.objects.get(id=user_id, business=request.user.business)

            if 'role_id' in request.data:
                role = Role.objects.get(id=request.data['role_id'])
                user.role = role

            if 'is_active' in request.data:
                user.is_active = request.data['is_active']

            if 'phone' in request.data:
                user.phone = request.data['phone']

            user.save()

            return Response(UserSerializer(user).data)

        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)

    @extend_schema(responses={200: dict})
    def delete(self, request, user_id):
        self.check_permissions(request)

        from .models import User

        try:
            user = User.objects.get(id=user_id, business=request.user.business)

            if user.id == request.user.id:
                return Response({'error': 'Cannot delete your own account'}, status=400)

            user.delete()

            return Response({'message': 'User deleted successfully'})

        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)


# ======================================================
# PASSWORD RESET REQUEST
# ======================================================
class PasswordResetRequestView(APIView):
    """
    Request password reset email.
    Access: Anyone
    """
    permission_classes = [AllowAny]

    @extend_schema(
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'email': {'type': 'string', 'format': 'email'}
                },
                'required': ['email']
            }
        },
        responses={200: dict}
    )
    def post(self, request):
        email = request.data.get('email')
        
        from .models import User
        try:
            user = User.objects.get(email=email)
            
            # Generate reset token (using JWT)
            refresh = RefreshToken.for_user(user)
            reset_token = str(refresh.access_token)
            
            # Create reset link
            reset_link = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}&email={email}"
            
            # Send email
            EmailService.send_password_reset_email(user, reset_link)
            
            return Response({
                'message': 'Password reset email sent if account exists'
            })
        except User.DoesNotExist:
            # Don't reveal if user exists for security
            return Response({
                'message': 'Password reset email sent if account exists'
            })


# ======================================================
# PASSWORD RESET CONFIRM
# ======================================================
class PasswordResetConfirmView(APIView):
    """
    Confirm password reset with new password.
    Access: Anyone
    """
    permission_classes = [AllowAny]

    @extend_schema(
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'email': {'type': 'string', 'format': 'email'},
                    'token': {'type': 'string'},
                    'new_password': {'type': 'string', 'minLength': 8}
                },
                'required': ['email', 'token', 'new_password']
            }
        },
        responses={200: dict}
    )
    def post(self, request):
        email = request.data.get('email')
        token = request.data.get('token')
        new_password = request.data.get('new_password')
        
        from .models import User
        from rest_framework_simplejwt.tokens import AccessToken
        from rest_framework_simplejwt.exceptions import TokenError
        
        try:
            # Validate token
            access_token = AccessToken(token)
            user_id = access_token['user_id']
            
            user = User.objects.get(id=user_id, email=email)
            
            # Set new password
            user.set_password(new_password)
            user.save()
            
            return Response({
                'message': 'Password reset successfully'
            })
        except (User.DoesNotExist, TokenError, Exception):
            return Response({
                'error': 'Invalid or expired token'
            }, status=400)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing audit logs"""
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, IsAuditorUserReadOnly]
    
    def get_queryset(self):
        queryset = AuditLog.objects.all()
        
        # Filter by business
        if hasattr(self.request.user, 'business') and self.request.user.business:
            queryset = queryset.filter(business=self.request.user.business)
        else:
            queryset = queryset.filter(user=self.request.user)
        
        # Date filters
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        
        # Action filter
        action = self.request.query_params.get('action')
        if action:
            queryset = queryset.filter(action=action.upper())
        
        # Module filter
        module = self.request.query_params.get('module')
        if module:
            queryset = queryset.filter(module=module)
        
        # User filter
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        return queryset

class AuditLogStatsView(APIView):
    """Get statistics for audit logs"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        print("=== Stats endpoint called ===")
        
        # Get all audit logs
        queryset = AuditLog.objects.all()
        
        # Time periods
        now = timezone.now()
        today = now.date()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        # Calculate stats
        total_logs = queryset.count()
        today_logs = queryset.filter(created_at__date=today).count()
        this_week_logs = queryset.filter(created_at__gte=week_ago).count()
        this_month_logs = queryset.filter(created_at__gte=month_ago).count()
        unique_users = queryset.values('user').distinct().count()
        unique_actions = queryset.values('action').distinct().count()
        
        print(f"Stats: total={total_logs}, today={today_logs}")
        
        # Top users
        top_users = queryset.values('user__email', 'user__username')\
            .annotate(count=Count('id'))\
            .order_by('-count')[:5]
        
        top_users_list = []
        for u in top_users:
            username = u.get('user__username') or u.get('user__email') or 'Unknown'
            top_users_list.append({
                'username': username,
                'count': u['count']
            })
        
        # Top actions
        top_actions = queryset.values('action')\
            .annotate(count=Count('id'))\
            .order_by('-count')[:5]
        
        top_actions_list = []
        for a in top_actions:
            top_actions_list.append({
                'action': a['action'],
                'count': a['count']
            })
        
        stats = {
            'total_logs': total_logs,
            'today_logs': today_logs,
            'this_week_logs': this_week_logs,
            'this_month_logs': this_month_logs,
            'unique_users': unique_users,
            'unique_actions': unique_actions,
            'top_users': top_users_list,
            'top_actions': top_actions_list,
        }
        
        return Response(stats)


class AuditLogExportView(APIView):
    """Export all audit logs to CSV - Simple version"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        print("=== Exporting all audit logs ===")
        
        # Get ALL audit logs (no filters)
        queryset = AuditLog.objects.all().order_by('-created_at')
        
        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="all-audit-logs-{timezone.now().date()}.csv"'
        
        writer = csv.writer(response)
        
        # Write headers
        writer.writerow([
            'ID', 
            'User Email', 
            'Action', 
            'Module', 
            'Description', 
            'Details', 
            'IP Address',
            'Created At'
        ])
        
        # Write data rows
        for log in queryset:
            writer.writerow([
                log.id,
                log.user.email if log.user else 'Unknown',
                log.get_action_display(),
                log.get_module_display(),
                log.description,
                str(log.details),
                log.ip_address or 'Unknown',
                log.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            ])
        
        print(f"Exported {queryset.count()} audit logs")
        
        return response


class AuditLogModulesView(APIView):
    """Get list of available modules"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        modules = [
            {'value': 'auth', 'label': 'Authentication'},
            {'value': 'financials', 'label': 'Financials'},
            {'value': 'inventory', 'label': 'Inventory'},
            {'value': 'sales', 'label': 'Sales'},
            {'value': 'hr', 'label': 'Human Resources'},
            {'value': 'bi', 'label': 'Business Intelligence'},
            {'value': 'reports', 'label': 'Reports'},
        ]
        return Response(modules)


class AuditLogActionsView(APIView):
    """Get list of available actions"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        actions = [
            {'value': 'CREATE', 'label': 'Create'},
            {'value': 'READ', 'label': 'Read'},
            {'value': 'UPDATE', 'label': 'Update'},
            {'value': 'DELETE', 'label': 'Delete'},
            {'value': 'LOGIN', 'label': 'Login'},
            {'value': 'LOGOUT', 'label': 'Logout'},
            {'value': 'EXPORT', 'label': 'Export'},
            {'value': 'IMPORT', 'label': 'Import'},
        ]
        return Response(actions)