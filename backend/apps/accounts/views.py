from django.contrib.auth import authenticate, get_user_model
from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from rest_framework_simplejwt.utils import get_md5_hash_password
from apps.core.audit import record_event
from .serializers import LoginSerializer, RefreshSerializer, UserSerializer
from .throttles import LoginThrottle, RefreshThrottle


def auth_audit(request, actor, action):
    record_event(actor=actor, action=action, entity_type='accounts.User',
                 entity_id=actor.pk if actor else 'unknown', request_id=request.request_id,
                 summary={'outcome': 'success' if actor else 'denied'})


def locked_refresh(raw):
    # Validate once, acquire the row lock, then recheck for a concurrent revocation.
    token = RefreshToken(raw)
    try:
        OutstandingToken.objects.select_for_update().get(jti=token['jti'])
    except OutstandingToken.DoesNotExist:
        raise InvalidToken('Invalid refresh token.')
    token.check_blacklist()
    try:
        user = get_user_model().objects.get(pk=token['user_id'], is_active=True)
    except (get_user_model().DoesNotExist, ValueError):
        raise InvalidToken('Invalid refresh token.')
    if token.get('hash_password') != get_md5_hash_password(user.password):
        raise InvalidToken('Invalid refresh token.')
    return token, user


class PublicAuthView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get_authenticate_header(self, request):
        return 'Bearer realm="api"'


class LoginView(PublicAuthView):
    throttle_classes = [LoginThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(request, **serializer.validated_data)
        if user is None:
            auth_audit(request, None, 'auth.login_failed')
            raise AuthenticationFailed('Invalid email or password.', code='invalid_credentials')
        with transaction.atomic():
            refresh = RefreshToken.for_user(user)
            auth_audit(request, user, 'auth.login')
            return Response({'access': str(refresh.access_token), 'refresh': str(refresh),
                             'user': UserSerializer(user).data})


class RefreshView(PublicAuthView):
    throttle_classes = [RefreshThrottle]

    def post(self, request):
        serializer = RefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                _, user = locked_refresh(serializer.validated_data['refresh'])
                tokens = TokenRefreshSerializer(data=serializer.validated_data)
                tokens.is_valid(raise_exception=True)
                auth_audit(request, user, 'auth.refresh')
                return Response(tokens.validated_data)
        except TokenError:
            raise InvalidToken('Invalid or expired refresh token.')


class MeView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)


class LogoutView(APIView):
    def post(self, request):
        serializer = RefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                token, user = locked_refresh(serializer.validated_data['refresh'])
                if user.pk != request.user.pk:
                    raise PermissionDenied('Refresh token does not belong to this user.', code='token_owner_mismatch')
                token.blacklist()
                auth_audit(request, request.user, 'auth.logout')
        except TokenError:
            raise InvalidToken('Invalid or expired refresh token.')
        return Response({'revoked': True}, status=status.HTTP_200_OK)
