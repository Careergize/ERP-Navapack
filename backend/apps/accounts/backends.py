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
        rows = user_obj.roles.values_list('permissions__content_type__app_label', 'permissions__codename')
        return base | {f'{app}.{code}' for app, code in rows if code}
