from rest_framework.routers import DefaultRouter
from .views import WarehouseViewSet, LocationViewSet, IdentityViewSet, InventoryAuditViewSet
from .workflow_views import OperationViewSet
router=DefaultRouter()
router.register('warehouses',WarehouseViewSet)
router.register('locations',LocationViewSet)
router.register('identities',IdentityViewSet)
router.register('history',InventoryAuditViewSet,basename='inventory-history')
router.register('operations',OperationViewSet,basename='inventory-operations')
urlpatterns=router.urls
from django.urls import path
from .quality_views import QualityViewSet
urlpatterns += [
    path('quality/mode/', QualityViewSet.as_view({'get':'mode'})),
    path('quality/<str:resource>/', QualityViewSet.as_view({'get':'list','post':'create'})),
    path('quality/<str:resource>/<uuid:pk>/', QualityViewSet.as_view({'get':'retrieve'})),
    path('quality/<str:resource>/<uuid:pk>/history/', QualityViewSet.as_view({'get':'history'})),
    path('quality/<str:resource>/<uuid:pk>/<str:step>/', QualityViewSet.as_view({'post':'transition'})),
]
