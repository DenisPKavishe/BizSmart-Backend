from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# drf-spectacular
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    # =========================
    # Admin Panel
    # =========================
    path('admin/', admin.site.urls),

    # =========================
    # API Schema
    # =========================
    path(
        'api/schema/',
        SpectacularAPIView.as_view(),
        name='schema'
    ),

    # =========================
    # Swagger UI
    # =========================
    path(
        'api/docs/',
        SpectacularSwaggerView.as_view(url_name='schema'),
        name='swagger-ui'
    ),

    # =========================
    # ReDoc Documentation
    # =========================
    path(
        'api/redoc/',
        SpectacularRedocView.as_view(url_name='schema'),
        name='redoc'
    ),

    # =========================
    # Core Authentication APIs
    # =========================
    path('api/v1/auth/', include('core.urls')),

    # =========================
    # Financial Management APIs
    # =========================
    path('api/v1/financials/', include('financials.urls')),

    # =========================
    # Inventory Management APIs
    # =========================
    path('api/v1/inventory/', include('inventory.urls')),

    # =========================
    # Sales Management APIs
    # =========================
    path('api/v1/sales/', include('sales.urls')),

    # =========================
    # Human Resource APIs
    # =========================
    path('api/v1/hr/', include('hr.urls')),

    # =========================
    # Business Intelligence APIs
    # =========================
    path('api/v1/bi/', include('bi.urls')),
]

# =========================
# Media Files
# =========================
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )