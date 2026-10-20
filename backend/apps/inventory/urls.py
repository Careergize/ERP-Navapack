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
