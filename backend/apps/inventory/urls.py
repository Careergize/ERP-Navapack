from rest_framework.routers import DefaultRouter
from .views import WarehouseViewSet, LocationViewSet, IdentityViewSet, InventoryAuditViewSet
router=DefaultRouter()
router.register('warehouses',WarehouseViewSet)
router.register('locations',LocationViewSet)
router.register('identities',IdentityViewSet)
router.register('history',InventoryAuditViewSet,basename='inventory-history')
urlpatterns=router.urls
