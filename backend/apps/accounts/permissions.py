from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied


class ActionPermission(BasePermission):
    """Views declare action_permissions and explicitly scope object access."""
    def has_permission(self, request, view):
        if not request.user.is_authenticated or not request.user.is_active:
            return False
        action = getattr(view, 'action', request.method.lower())
        permission = getattr(view, 'action_permissions', {}).get(action)
        return bool(permission and request.user.has_perm(permission))

    def has_object_permission(self, request, view, obj):
        scope = getattr(view, 'object_scope', None)
        return bool(scope and scope(request.user, obj))


def require_independent_actor(actor, maker_id):
    if not actor.is_authenticated or not actor.is_active or maker_id is None:
        raise PermissionDenied('An active actor and recorded maker are required.', code='independence_required')
    if str(actor.pk) == str(maker_id):
        raise PermissionDenied('You cannot approve your own transaction.', code='self_approval_forbidden')
