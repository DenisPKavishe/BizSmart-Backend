from django.urls import path,include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    AuditLogActionsView, AuditLogExportView, AuditLogModulesView, AuditLogStatsView, AuditLogViewSet, RegisterView, LoginView, LogoutView, ProfileView,
    UserListView, UserDetailView, public_test,
    PasswordResetRequestView, PasswordResetConfirmView
)


router = DefaultRouter()
router.register(r'audit-logs', AuditLogViewSet, basename='audit-log')

urlpatterns = [
    # Public test
    path('public-test/', public_test, name='public-test'),
    
    # Authentication
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('profile/', ProfileView.as_view(), name='profile'),
    
    # User Management
    path('users/', UserListView.as_view(), name='user-list'),
    path('users/<int:user_id>/', UserDetailView.as_view(), name='user-detail'),
    
    # Password Reset
    path('password-reset/', PasswordResetRequestView.as_view(), name='password-reset'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),

    path('', include(router.urls)),
    path('audit-logs/stats/', AuditLogStatsView.as_view(), name='audit-log-stats'),
    path('audit-logs/export/', AuditLogExportView.as_view(), name='audit-log-export'),
    path('audit-logs/modules/', AuditLogModulesView.as_view(), name='audit-log-modules'),
    path('audit-logs/actions/', AuditLogActionsView.as_view(), name='audit-log-actions'),
]