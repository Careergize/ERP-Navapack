import uuid
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from rest_framework.test import APIClient, APIRequestFactory
from rest_framework.exceptions import PermissionDenied
from apps.accounts.models import Role, Membership
from apps.accounts.permissions import ActionPermission, require_independent_actor
from apps.core.models import AuditEvent, ThrottleWindow

User = get_user_model()


class AuthenticationTests(TestCase):
    def setUp(self):
        ThrottleWindow.objects.all().delete()
        self.user = User.objects.create_user('Operator@Example.com', 'a-long-test-password', name='Operator')
        self.client = APIClient()

    def login(self, email='operator@example.com', password='a-long-test-password'):
        return self.client.post('/api/v1/auth/login/', {'email': email, 'password': password}, format='json')

    def authenticated(self):
        data = self.login().json()
        self.client.credentials(HTTP_AUTHORIZATION='Bearer '+data['access'])
        return data

    def test_login_identity_and_audit(self):
        rid = str(uuid.uuid4())
        response = self.client.post('/api/v1/auth/login/', {'email': 'OPERATOR@EXAMPLE.COM',
                                    'password': 'a-long-test-password'}, format='json', HTTP_X_REQUEST_ID=rid)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.assertEqual(response['X-Request-ID'], rid)
        self.assertEqual(response.data['user']['id'], str(self.user.pk))
        self.assertNotIn('password', response.data['user'])
        event = AuditEvent.objects.get(action='auth.login')
        self.assertEqual(event.actor, self.user)
        self.assertEqual(str(event.request_id), rid)
        self.assertNotIn(response.data['refresh'], str(event.summary))

    def test_failure_is_generic_and_audited_without_email(self):
        a = self.login(password='wrong')
        b = self.login(email='absent@example.com')
        self.assertEqual(a.status_code, 401)
        self.assertEqual(a.json()['error']['code'], 'invalid_credentials')
        self.assertEqual(a.json()['error']['message'], b.json()['error']['message'])
        self.assertEqual(AuditEvent.objects.filter(action='auth.login_failed', actor=None).count(), 2)

    def test_refresh_rotation_and_reuse(self):
        pair = self.login().json()
        response = self.client.post('/api/v1/auth/refresh/', {'refresh': pair['refresh']}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.data['refresh'], pair['refresh'])
        replay = self.client.post('/api/v1/auth/refresh/', {'refresh': pair['refresh']}, format='json')
        self.assertEqual(replay.status_code, 401)
        self.assertTrue(AuditEvent.objects.filter(action='auth.refresh', actor=self.user).exists())

    def test_logout_revokes_refresh(self):
        pair = self.authenticated()
        response = self.client.post('/api/v1/auth/logout/', {'refresh': pair['refresh']}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['revoked'])
        self.assertEqual(self.client.post('/api/v1/auth/refresh/', {'refresh': pair['refresh']}, format='json').status_code, 401)
        # Short-lived access JWT remains valid until expiry by explicit policy.
        self.assertEqual(self.client.get('/api/v1/auth/me/').status_code, 200)

    def test_logout_does_not_revoke_other_users_token(self):
        other = User.objects.create_user('other@example.com', 'other-long-password')
        pair = self.authenticated()
        from rest_framework_simplejwt.tokens import RefreshToken
        foreign = str(RefreshToken.for_user(other))
        response = self.client.post('/api/v1/auth/logout/', {'refresh': foreign}, format='json')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data['error']['code'], 'token_owner_mismatch')
        self.assertEqual(self.client.post('/api/v1/auth/refresh/', {'refresh': foreign}, format='json').status_code, 200)

    def test_inactive_login_access_and_refresh(self):
        pair = self.authenticated()
        self.user.is_active = False
        self.user.save()
        self.assertEqual(self.login().status_code, 401)
        self.assertEqual(self.client.get('/api/v1/auth/me/').status_code, 401)
        self.assertEqual(self.client.post('/api/v1/auth/refresh/', {'refresh': pair['refresh']}, format='json').status_code, 401)

    def test_password_change_invalidates_access_and_refresh(self):
        pair = self.authenticated()
        self.user.set_password('another-long-password')
        self.user.save()
        self.assertEqual(self.client.get('/api/v1/auth/me/').status_code, 401)
        self.assertEqual(self.client.post('/api/v1/auth/refresh/', {'refresh': pair['refresh']}, format='json').status_code, 401)

    def test_unauthenticated_and_malformed_tokens(self):
        self.assertEqual(self.client.get('/api/v1/auth/me/').status_code, 401)
        self.assertEqual(self.client.post('/api/v1/auth/logout/', {}, format='json').status_code, 401)
        self.assertEqual(self.client.post('/api/v1/auth/refresh/', {'refresh': 'invalid'}, format='json').status_code, 401)
        self.assertEqual(self.login(email='invalid').status_code, 400)

    def test_current_user_and_unknown_route(self):
        self.authenticated()
        me = self.client.get('/api/v1/auth/me/')
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.data['email'], self.user.email)
        self.assertEqual(me.data['roles'], [])
        missing = self.client.get('/api/v1/sales-orders/')
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json()['error']['code'], 'not_found')

    def test_login_throttles_after_five_attempts(self):
        for _ in range(5):
            self.assertEqual(self.login(password='wrong').status_code, 401)
        response = self.login(password='wrong')
        self.assertEqual(response.status_code, 429)
        self.assertIn('Retry-After', response)
        self.assertEqual(response.data['error']['code'], 'throttled')

    def test_roles_and_action_object_permissions_fail_closed(self):
        permission = Permission.objects.get(content_type__app_label='accounts', codename='view_user')
        role = Role.objects.create(code='reviewer', name='Example test role')
        role.permissions.add(permission)
        request = APIRequestFactory().get('/')
        request.user = User.objects.get(pk=self.user.pk)
        view = type('View', (), {'action_permissions': {'get': 'accounts.view_user'}})()
        checker = ActionPermission()
        self.assertFalse(checker.has_permission(request, view))
        Membership.objects.create(user=self.user, role=role)
        request.user = User.objects.get(pk=self.user.pk)
        self.assertTrue(checker.has_permission(request, view))
        self.assertFalse(checker.has_object_permission(request, view, self.user))
        view.object_scope = lambda actor, obj: actor.pk == obj.pk
        self.assertTrue(checker.has_object_permission(request, view, self.user))
        self.authenticated()
        self.assertEqual(self.client.get('/api/v1/auth/me/').data['roles'], ['reviewer'])

    def test_independence_including_superuser(self):
        with self.assertRaises(PermissionDenied):
            require_independent_actor(self.user, self.user.pk)
        self.user.is_superuser = True
        with self.assertRaises(PermissionDenied):
            require_independent_actor(self.user, self.user.pk)
        require_independent_actor(self.user, uuid.uuid4())
        with self.assertRaises(PermissionDenied):
            require_independent_actor(self.user, None)

    def test_permission_denial_through_api_view(self):
        from rest_framework.views import APIView
        from rest_framework.response import Response
        from rest_framework.test import force_authenticate
        class ProtectedView(APIView):
            permission_classes = [ActionPermission]
            action_permissions = {'get': 'accounts.change_user'}

            def get(self, request):
                return Response({'allowed': True})
        request = APIRequestFactory().get('/')
        request.request_id = uuid.uuid4()
        force_authenticate(request, self.user)
        response = ProtectedView.as_view()(request)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data['error']['code'], 'permission_denied')

    def test_email_unique_case_insensitive_at_database(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.bulk_create([User(email='OPERATOR@example.com')])

    def test_production_password_hasher_configured(self):
        with override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.PBKDF2PasswordHasher']):
            user = User.objects.create_user('hash@example.com', 'strong-long-password')
            self.assertTrue(user.password.startswith('pbkdf2_sha256$'))
