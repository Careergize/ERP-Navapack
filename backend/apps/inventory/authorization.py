from django.db import connection, models
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from apps.accounts.models import Employee, User
from apps.accounts.backends import explicit_permission_codes
from .models import WarehouseScope


def lock_configuration():
    with connection.cursor() as cursor:
        cursor.execute('SELECT pg_advisory_xact_lock(%s)', [70462030])


def effective_codes(actor):
    # Explicit permissions; never use ModelBackend's superuser has_perm shortcut.
    return explicit_permission_codes(actor)


def require_actor(actor, capability):
    current = User.objects.filter(pk=actor.pk, is_active=True).first()
    if current is None or not Employee.objects.filter(user=current).exists() or capability not in effective_codes(current):
        raise PermissionDenied('An active employee with an explicit capability is required.')
    return current


def scopes(actor):
    return WarehouseScope.objects.filter(user=actor, expires_at__gt=timezone.now())


def oversight(actor):
    return scopes(actor).filter(company_wide=True).exists()


def require_scope(actor, warehouse_id=None):
    if not oversight(actor) and (warehouse_id is None or not scopes(actor).filter(warehouse_id=warehouse_id).exists()):
        raise PermissionDenied('Approved warehouse scope is required.')


def authority_snapshot(actor, capability, warehouse_id):
    from apps.accounts.employee_services import permission_digest
    employee=Employee.objects.get(user=actor)
    return {'employee_id': str(employee.pk), 'employee_reference': employee.employee_id,
            'capability_used': capability,
            'roles': [{'id':str(r.pk),'revision':str(r.approved_revision_id) if r.approved_revision_id else None,
                       'capability_digest':permission_digest(r)} for r in actor.roles.all()],
            'scope_evidence': [str(pk) for pk in scopes(actor).filter(
                models.Q(company_wide=True) | models.Q(warehouse_id=warehouse_id)).values_list('pk',flat=True)],
            'policy': 'phase3a-configuration-v1'}
