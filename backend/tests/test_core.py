import os
import uuid
from unittest.mock import patch
from django.core.exceptions import ImproperlyConfigured
from django.db import connection, DatabaseError, transaction
from django.test import TestCase, SimpleTestCase, override_settings
from rest_framework.test import APIClient
from config.environment import required, boolean, origins
from apps.core.audit import record_event
from apps.core.models import AuditEvent
from apps.core.commands import expected_version, payload_hash
from apps.core.api import PreconditionRequired


class ConfigurationTests(SimpleTestCase):
    def test_required_and_boolean_validation(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ImproperlyConfigured):
                required('MISSING')
            self.assertFalse(boolean('UNSET'))
        with patch.dict(os.environ, {'BAD_BOOLEAN': 'yes', 'BAD_KEY': 'replace-me-secret'}):
            with self.assertRaises(ImproperlyConfigured):
                boolean('BAD_BOOLEAN')
            with self.assertRaises(ImproperlyConfigured):
                required('BAD_KEY')

    def test_origin_allowlist(self):
        for value in ('*', 'http://*.example.com', 'https://example.com/path', 'https://user:pass@example.com', 'http://example.com'):
            with self.subTest(value=value), patch.dict(os.environ, {'ORIGINS': value}):
                with self.assertRaises(ImproperlyConfigured):
                    origins('ORIGINS', production=True)
        with patch.dict(os.environ, {'ORIGINS': 'https://erp.example.com'}):
            self.assertEqual(origins('ORIGINS', True), ['https://erp.example.com'])

    def test_preconditions_and_hashes(self):
        with self.assertRaises(PreconditionRequired):
            expected_version(None)
        self.assertEqual(expected_version('"3"'), 3)
        from rest_framework.exceptions import ValidationError
        for value in ('3', '*', 'W/"3"', '"0"'):
            with self.assertRaises(ValidationError):
                expected_version(value)
        self.assertEqual(payload_hash({'a': 1, 'b': 2}), payload_hash({'b': 2, 'a': 1}))
        with self.assertRaises(ValueError):
            payload_hash({'quantity': float('nan')})


class CoreAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_health_and_readiness(self):
        self.assertEqual(connection.vendor, 'postgresql')
        for path in ('/api/v1/health/', '/api/v1/ready/'):
            response = self.client.get(path, HTTP_X_REQUEST_ID='untrusted\nvalue')
            self.assertEqual(response.status_code, 200)
            uuid.UUID(response['X-Request-ID'])

    def test_unready_is_safe_and_health_does_not_query_database(self):
        with patch('apps.core.views.connection.cursor', side_effect=DatabaseError('secret-dsn')):
            self.assertEqual(self.client.get('/api/v1/health/').status_code, 200)
            response = self.client.get('/api/v1/ready/')
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('secret-dsn', str(response.content))

    @override_settings(CORS_ALLOWED_ORIGINS=['https://erp.example.com'])
    def test_cors_does_not_allow_arbitrary_origins(self):
        allowed = self.client.get('/api/v1/health/', HTTP_ORIGIN='https://erp.example.com')
        blocked = self.client.get('/api/v1/health/', HTTP_ORIGIN='https://evil.example')
        self.assertEqual(allowed['Access-Control-Allow-Origin'], 'https://erp.example.com')
        self.assertNotIn('Access-Control-Allow-Origin', blocked)

    def test_audit_append_only_at_orm_and_database(self):
        event = record_event(actor=None, action='test', entity_type='test', entity_id='1', request_id=uuid.uuid4(),
                             summary={'before_status': 'draft', 'after_status': 'approved'}, source_version=1)
        with self.assertRaises(ValueError):
            event.save()
        with self.assertRaises(ValueError):
            event.delete()
        with self.assertRaises(ValueError):
            AuditEvent.objects.filter(pk=event.pk).update(reason='changed')
        for sql in ('UPDATE core_auditevent SET reason = reason WHERE id = %s', 'DELETE FROM core_auditevent WHERE id = %s'):
            with self.assertRaises(DatabaseError), transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(sql, [event.pk])

    def test_audit_rejects_sensitive_content(self):
        for summary in ({'password': 'value'}, {'changed_fields': ['access_token']}):
            with self.assertRaises(ValueError):
                record_event(actor=None, action='test', entity_type='test', entity_id='1',
                             request_id=uuid.uuid4(), summary=summary)

    def test_unexpected_error_envelope_is_safe(self):
        from apps.core.api import exception_handler
        request = type('Request', (), {'request_id': uuid.uuid4()})()
        response = exception_handler(RuntimeError('database-password'), {'request': request})
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data['error']['code'], 'internal_error')
        self.assertNotIn('database-password', str(response.data))
