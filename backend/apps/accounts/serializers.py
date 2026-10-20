from rest_framework import serializers
from .models import User


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=1024)


class RefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField(write_only=True, max_length=4096)


class UserSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'is_active', 'is_master_admin', 'roles', 'permissions', 'created_at', 'updated_at']
        read_only_fields = fields

    def get_roles(self, user):
        return list(user.roles.order_by('code').values_list('code', flat=True))

    def get_permissions(self, user):
        from .backends import explicit_permission_codes
        explicit_domains = ('inventory.', 'commercial.')
        permissions={code for code in user.get_all_permissions() if not code.startswith(explicit_domains)}
        return sorted(permissions | {code for code in explicit_permission_codes(user) if code.startswith(explicit_domains)})
