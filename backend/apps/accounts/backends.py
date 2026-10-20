from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model


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
        from .employee_services import permission_codes, permission_digest
        from .models import RoleAssignmentPolicy
        codes = set()
        for role in user_obj.roles.select_related('approved_revision'):
            policy = RoleAssignmentPolicy.objects.filter(role=role).first()
            # Fail closed on unreviewed edits to previously configured legacy roles.
            if not role.governed and policy and policy.permission_digest != permission_digest(role):
                continue
            codes.update(permission_codes(role))
        return base | codes
