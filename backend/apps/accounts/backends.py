from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db.models import Q


def explicit_role_permissions(user_obj):
    from .employee_services import permission_codes, permission_digest
    from .models import RoleAssignmentPolicy
    codes=set()
    for role in user_obj.roles.select_related('approved_revision'):
        policy=RoleAssignmentPolicy.objects.filter(role=role).first()
        if not role.governed and policy and policy.permission_digest != permission_digest(role):
            continue
        codes.update(permission_codes(role))
    return codes


def explicit_permission_codes(user_obj):
    """Actual direct/group/governed grants, excluding Django's superuser override."""
    if not user_obj.is_active or user_obj.is_anonymous:
        return set()
    permissions=Permission.objects.filter(Q(user=user_obj) | Q(group__user=user_obj)).distinct()
    return {f'{a}.{c}' for a,c in permissions.values_list('content_type__app_label','codename')} | explicit_role_permissions(user_obj)


class EmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        email = kwargs.get('email', username)
        if not isinstance(email, str) or password is None:
            return None
        User = get_user_model()
        try:
            user = User.objects.get(email__iexact=email.strip())
        except User.DoesNotExist:
            User().set_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def get_group_permissions(self, user_obj, obj=None):
        base = super().get_group_permissions(user_obj, obj)
        if not user_obj.is_active or user_obj.is_anonymous or obj is not None:
            return base
        return base | explicit_role_permissions(user_obj)
