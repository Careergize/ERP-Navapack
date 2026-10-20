from django.urls import path, include
from apps.accounts.views import LoginView, RefreshView, MeView, LogoutView
from apps.core.views import HealthView, ReadinessView

urlpatterns = [
    path('api/v1/inventory/', include('apps.inventory.urls')),
    path('api/v1/', include('apps.accounts.admin_urls')),
    path('api/v1/', include('apps.masters.urls')),
    path('api/v1/health/', HealthView.as_view(), name='health'),
    path('api/v1/ready/', ReadinessView.as_view(), name='readiness'),
    path('api/v1/auth/login/', LoginView.as_view(), name='login'),
    path('api/v1/auth/refresh/', RefreshView.as_view(), name='refresh'),
    path('api/v1/auth/me/', MeView.as_view(), name='me'),
    path('api/v1/auth/logout/', LogoutView.as_view(), name='logout'),
]
