from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings

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