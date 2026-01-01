"""
URL configuration for pdezzy project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from superadmin.admin import admin_site
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView


class APIRootView(APIView):
    """Root API endpoint"""
    def get(self, request):
        return Response({
            'message': 'Welcome to PDezzy API',
            'api_v1': {
                'admin': '/api/v1/admin/',
                'agent': '/api/v1/agent/',
                'seller': '/api/v1/seller/',
                'buyer': '/api/v1/buyer/',
                'common': '/api/v1/common/',
                'messaging': '/api/v1/messaging/',
            },
            'documentation': {
                'swagger': '/swagger/',
                'redoc': '/redoc/',
            }
        })

# drf_yasg schema view
schema_view = get_schema_view(
    openapi.Info(
        title="PDezzy Admin Dashboard & API",
        default_version='v1',
        description="""
# 📊 Admin Dashboard

**URL**: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

## Features:
- 👥 User Management (Agents, Buyers, Sellers)
- 🏠 Property Listings Management
- 📈 Real-time Statistics & Charts
- 📊 Weekly User Registration Data
- 📝 Recent Activity Feed
- 🔍 Search & Filter Users
- 📱 Responsive Dashboard

## Access Requirements:
- Superuser credentials required
- Login via Django admin

---

# 🔌 API Documentation

Complete API documentation with JWT Bearer token authentication for all endpoints.
        """,
        terms_of_service="https://www.example.com/terms/",
        contact=openapi.Contact(email="support@pdezzy.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    # Admin Dashboard - Custom dashboard with user management and statistics
    # URL: /admin/ or /admin/dashboard/
    path('admin/', admin_site.urls),
    
    # API Root
    path('api/', APIRootView.as_view(), name='api-root'),
    
    # Admin API Endpoints
    path('api/v1/admin/', include('superadmin.urls')),
    
    # API Documentation - drf_yasg (Swagger/OpenAPI)
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    
    # Common Endpoints (includes messaging)
    path('api/v1/common/', include('common.urls')),
    
    # Messaging endpoints
    path('api/v1/messaging/', include('messaging.urls')),
    
    # API Endpoints
    path('api/v1/agent/', include('agent.urls')),
    path('api/v1/seller/', include('seller.urls')),
    path('api/v1/buyer/', include('buyer.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
