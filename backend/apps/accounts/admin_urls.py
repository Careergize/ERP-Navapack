from rest_framework.routers import SimpleRouter
from .employee_views import EmployeeViewSet, AdminAuditViewSet
from .role_views import RoleViewSet
router=SimpleRouter()
router.register('employees',EmployeeViewSet,basename='employees')
router.register('roles',RoleViewSet,basename='roles')
router.register('admin/audit-events',AdminAuditViewSet,basename='admin-audit-events')
urlpatterns=router.urls
