"""Security boundary for employee administration and trusted management commands."""
import hashlib
from django.db import connection
from rest_framework.generics import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from apps.core.commands import advance_version, lock_versioned
from apps.core.api import CommandConflict
from .models import User, Employee, Role, Membership, RoleAssignmentPolicy, RoleChangeRequest
from .permissions import require_independent_actor

ADMIN_CAPABILITIES = [
    'manage_role_capabilities','approve_role_capabilities','view_employee','add_employee','change_employee','view_role','manage_employee_status',
    'manage_employee_roles','approve_employee_roles','initiate_employee_reset','view_admin_audit',
]
RESERVED_APPS = {'accounts','auth','contenttypes','sessions','token_blacklist','core'}


def lock_administration():
    # One lock order for all administration entrypoints, including trusted commands.
    # Serializes reporting-chain checks and prevents conflicting access transitions.
    with connection.cursor() as cursor:
        cursor.execute('SELECT pg_advisory_xact_lock(%s)', [70462026])


def require_admin(actor, capability):
    current = User.objects.filter(pk=actor.pk, is_active=True, is_master_admin=True).first()
    if current is None or not current.has_perm('accounts.' + capability):
        raise PermissionDenied('An active Master Admin with this capability is required.')
    return current


def managed_employee(actor, pk, version):
    get_object_or_404(Employee, pk=pk)
    employee = lock_versioned(Employee, pk, version)
    employee.user = User.objects.select_for_update().get(pk=employee.user_id)
    target = employee.user
    if target.pk == actor.pk or target.is_master_admin or target.is_superuser or target.is_staff:
        raise PermissionDenied('Self and privileged-account changes require trusted management tooling.')
    return employee


def bump(employee, actor):
    employee.updated_by = actor
    advance_version(employee, update_fields=['updated_by'])


def raw_permission_codes(role):
    return sorted(f'{app}.{code}' for app, code in role.permissions.values_list('content_type__app_label','codename'))


def permission_codes(role):
    if role.governed:
        revision = role.approved_revision
        if revision is None or revision.role_id != role.pk or revision.status != 'applied':
            return []
        return revision.permission_codes
    return raw_permission_codes(role)


def permission_digest(role):
    return hashlib.sha256('\n'.join(permission_codes(role)).encode()).hexdigest()


def grantable_policy(actor, role):
    policy = RoleAssignmentPolicy.objects.select_for_update().filter(role=role).first()
    if (role.governed and role.approved_revision_id is None) or policy is None or policy.permission_digest != permission_digest(role):
        raise PermissionDenied('Role requires a current trusted assignment policy.')
    if role.governed and policy.requires_independent_approval != role.approved_revision.requires_independent_approval:
        raise PermissionDenied('Approved role independence policy changed; reviewed publication required.')
    codes = permission_codes(role)
    if any(code.split('.')[0] in RESERVED_APPS for code in codes):
        raise PermissionDenied('Technical administration permissions cannot be delegated through employee roles.')
    if not set(codes).issubset(actor.get_all_permissions()):
        raise PermissionDenied('You cannot delegate capabilities you do not hold.')
    return policy


def request_role_change(actor, employee, role_id, operation, assignment_id=None):
    if operation == 'add' and not employee.user.is_active:
        raise ValidationError('Role grants require an active employee.')
    role = get_object_or_404(Role.objects.select_for_update(), pk=role_id)
    policy = grantable_policy(actor, role)
    if RoleChangeRequest.objects.filter(employee=employee, role=role, status='pending').exists():
        raise CommandConflict('A pending change already exists for this employee and role.')
    membership = Membership.objects.filter(user=employee.user, role=role).first()
    if operation == 'add' and membership:
        raise CommandConflict('This role is already assigned.')
    if operation == 'remove' and (membership is None or str(membership.pk) != str(assignment_id)):
        raise CommandConflict('This assignment is no longer current.')
    change = RoleChangeRequest.objects.create(employee=employee, role=role, operation=operation,
        assignment_id=assignment_id, permission_digest=policy.permission_digest,
        requires_independent_approval=policy.requires_independent_approval, requested_by=actor)
    if not policy.requires_independent_approval:
        apply_role_change(actor, employee, change)
    bump(employee, actor)
    return change


def apply_role_change(actor, employee, change):
    role = Role.objects.select_for_update().get(pk=change.role_id)
    policy = grantable_policy(actor, role)
    if change.status != 'pending':
        raise CommandConflict('This change was already applied.')
    if change.permission_digest != policy.permission_digest or change.requires_independent_approval != policy.requires_independent_approval:
        raise CommandConflict('Role policy changed; a new reviewed request is required.')
    if change.requires_independent_approval:
        require_independent_actor(actor, change.requested_by_id)
        maker = User.objects.get(pk=change.requested_by_id)
        maker = require_admin(maker, 'manage_employee_roles')
        grantable_policy(maker, role)
    if change.operation == 'add' and not employee.user.is_active:
        raise ValidationError('Cannot grant roles to an inactive employee.')
    if change.operation == 'add':
        if Membership.objects.filter(user=employee.user, role=role).exists():
            raise CommandConflict('This role is already assigned.')
        change.assignment_id = Membership.objects.create(user=employee.user, role=role).pk
    else:
        membership = Membership.objects.select_for_update().filter(pk=change.assignment_id, user=employee.user, role=role).first()
        if membership is None: raise CommandConflict('Assignment no longer exists.')
        membership.delete()
    change.status = 'applied'; change.approved_by = actor; change.applied_at = timezone.now()
    advance_version(change, update_fields=['assignment_id','status','approved_by','applied_at'])


def require_target_ceiling(actor, employee):
    # Evaluate inactive employees' retained grants too: reactivation/reset must not
    # become a path to capabilities the administrator cannot delegate.
    target = User.objects.get(pk=employee.user_id)
    target.is_active = True
    if not target.get_all_permissions().issubset(actor.get_all_permissions()):
        raise PermissionDenied('Target access exceeds your delegation ceiling.')
