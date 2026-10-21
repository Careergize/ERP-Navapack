import uuid
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TransactionTestCase
from rest_framework.test import APIClient


class ExistingInterfaceIntegrationTests(TransactionTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('integration@example.test', 'long-development-password')
        self.client = APIClient()

    def login(self):
        response = self.client.post('/api/v1/auth/login/', {'email': self.user.email, 'password': 'long-development-password'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer '+response.data['access'])

    def test_master_schema_denies_anonymous_and_ungranted_identity(self):
        self.assertEqual(self.client.get('/api/v1/customers/schema/').status_code, 401)
        self.login()
        self.assertEqual(self.client.get('/api/v1/customers/schema/').status_code, 403)

    def test_jwt_master_create_edit_refresh_relogin_and_conflict(self):
        self.user.user_permissions.add(*Permission.objects.filter(content_type__app_label='masters', codename__in=['view_customer','add_customer','change_customer']))
        self.login()
        fields = self.client.get('/api/v1/customers/schema/').data['fields']
        self.assertTrue(fields['id']['read_only'])
        self.assertTrue(fields['name']['required'])
        key = str(uuid.uuid4())
        body = {'name': 'Synthetic integration customer', 'email': 'customer@example.test'}
        created = self.client.post('/api/v1/customers/', body, format='json', HTTP_IDEMPOTENCY_KEY=key)
        self.assertEqual(created.status_code, 201, created.data)
        replay = self.client.post('/api/v1/customers/', body, format='json', HTTP_IDEMPOTENCY_KEY=key)
        self.assertEqual(replay.data['id'], created.data['id'])
        url = f"/api/v1/customers/{created.data['id']}/"
        changed = self.client.patch(url, {'name': 'Persisted edit'}, format='json', HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()), HTTP_IF_MATCH='"1"')
        self.assertEqual(changed.status_code, 200, changed.data)
        stale = self.client.patch(url, {'name': 'Stale edit'}, format='json', HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()), HTTP_IF_MATCH='"1"')
        self.assertEqual(stale.status_code, 412)
        self.client.credentials()
        self.login()
        self.assertEqual(self.client.get(url).data['name'], 'Persisted edit')
        self.assertEqual(self.client.get('/api/v1/customers/', {'search':'Persisted', 'is_active':'true'}).data['count'], 1)
        self.assertEqual(self.client.get('/api/v1/employees/').status_code, 403)

    def test_schema_preserves_json_and_nullable_fields_without_related_directory(self):
        self.user.user_permissions.add(Permission.objects.get(content_type__app_label='masters',codename='view_productvariant'))
        self.login()
        response=self.client.get('/api/v1/finished-goods/schema/')
        self.assertEqual(response.status_code,200,response.data)
        self.assertEqual(response.data['fields']['data_notes']['type'],'json')
        self.assertTrue(response.data['fields']['pieces']['allow_null'])
        self.assertNotIn('choices',response.data['fields']['product'])
