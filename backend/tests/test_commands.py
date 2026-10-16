import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from django.contrib.auth import get_user_model
from django.db import connection, connections, models
from django.test import TransactionTestCase
from rest_framework.exceptions import PermissionDenied
from apps.core.commands import execute_command, lock_versioned, advance_version
from apps.core.api import CommandConflict, VersionConflict
from apps.core.models import AuditEvent, IdempotencyRecord, VersionedModel


class TestAggregate(VersionedModel):
    status = models.CharField(max_length=30, default='draft')

    class Meta(VersionedModel.Meta):
        app_label = 'foundation_tests'
        db_table = 'test_foundation_aggregate'
        managed = False


class CommandTests(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if connection.vendor != 'postgresql':
            raise RuntimeError('These tests require real PostgreSQL, not SQLite.')
        with connection.schema_editor() as editor:
            editor.create_model(TestAggregate)

    @classmethod
    def tearDownClass(cls):
        with connection.schema_editor() as editor:
            editor.delete_model(TestAggregate)
        super().tearDownClass()

    def setUp(self):
        TestAggregate.objects.all().delete()
        self.user = get_user_model().objects.create_user('command@example.com', 'long-password')
        self.aggregate = TestAggregate.objects.create()

    def command(self, key='command-1', payload=None, version=1, fail=False, authorize=lambda: None):
        def operation():
            obj = lock_versioned(TestAggregate, self.aggregate.pk, version)
            before = obj.status
            obj.status = 'approved'
            advance_version(obj, update_fields=['status'])
            if fail:
                raise RuntimeError('Injected failure')
            return ({'id': str(obj.pk), 'version': obj.version}, 200, {
                'entity_type': 'test.aggregate', 'entity_id': obj.pk,
                'summary': {'before_status': before, 'after_status': obj.status},
                'source_version': version})
        return execute_command(actor=self.user, scope=f'test:{self.aggregate.pk}', action='test.approve',
            key=key, payload=payload or {'id': str(self.aggregate.pk), 'expected_version': version},
            request_id=uuid.uuid4(), authorize=authorize, operation=operation)

    def test_replay_and_actor_audit(self):
        first = self.command()
        second = self.command()
        self.assertEqual(first[:2], second[:2])
        self.assertFalse(first[2])
        self.assertTrue(second[2])
        self.aggregate.refresh_from_db()
        self.assertEqual(self.aggregate.version, 2)
        event = AuditEvent.objects.get(action='test.approve')
        self.assertEqual(event.actor, self.user)
        self.assertEqual(event.source_version, 1)

    def test_payload_conflict_and_stale_version(self):
        self.command()
        with self.assertRaises(CommandConflict):
            self.command(payload={'different': 'payload'})
        with self.assertRaises(VersionConflict):
            self.command(key='second-command')
        self.assertEqual(AuditEvent.objects.filter(action='test.approve').count(), 1)
        self.assertEqual(IdempotencyRecord.objects.count(), 1)

    def test_operation_and_audit_failures_roll_back_everything(self):
        with self.assertRaises(RuntimeError):
            self.command(fail=True)
        self.aggregate.refresh_from_db()
        self.assertEqual(self.aggregate.version, 1)
        self.assertFalse(IdempotencyRecord.objects.exists())
        self.assertFalse(AuditEvent.objects.exists())
        from unittest.mock import patch
        with patch('apps.core.commands.record_event', side_effect=RuntimeError('Audit unavailable')):
            with self.assertRaises(RuntimeError):
                self.command()
        self.aggregate.refresh_from_db()
        self.assertEqual(self.aggregate.version, 1)
        self.assertFalse(IdempotencyRecord.objects.exists())

    def test_authorization_rechecked_on_replay(self):
        self.command()
        def deny():
            raise PermissionDenied()
        with self.assertRaises(PermissionDenied):
            self.command(authorize=deny)

    def test_invalid_keys_and_unsuccessful_results_are_not_retained(self):
        from rest_framework.exceptions import ValidationError
        for key in ('', 'contains space', '\x7f', 'é', 'k' * 201):
            with self.subTest(key=repr(key)), self.assertRaises(ValidationError):
                self.command(key=key)
        with self.assertRaises(ValueError):
            execute_command(actor=self.user, scope='test', action='test', key='valid',
                payload={}, request_id=uuid.uuid4(), authorize=lambda: None,
                operation=lambda: ({'error': 'failed'}, 400, {}))
        self.assertFalse(IdempotencyRecord.objects.exists())
        self.assertFalse(AuditEvent.objects.exists())

    def concurrent(self, worker):
        barrier = Barrier(2)
        def run(number):
            connections.close_all()
            try:
                barrier.wait(timeout=10)
                return worker(number)
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(run, i) for i in range(2)]
            return [future.result(timeout=20) for future in futures]

    def test_concurrent_identical_command_executes_once(self):
        results = self.concurrent(lambda _: self.command())
        self.assertEqual(sorted(row[2] for row in results), [False, True])
        self.assertEqual(AuditEvent.objects.filter(action='test.approve').count(), 1)
        self.aggregate.refresh_from_db()
        self.assertEqual(self.aggregate.version, 2)

    def test_concurrent_different_payload_conflicts(self):
        def worker(i):
            try:
                self.command(payload={'value': i})
                return 'success'
            except CommandConflict:
                return 'conflict'
        self.assertCountEqual(self.concurrent(worker), ['success', 'conflict'])
        self.assertEqual(AuditEvent.objects.filter(action='test.approve').count(), 1)

    def test_concurrent_versions_have_one_winner(self):
        def worker(i):
            try:
                self.command(key=f'independent-{i}')
                return 'success'
            except VersionConflict:
                return 'stale'
        self.assertCountEqual(self.concurrent(worker), ['success', 'stale'])
        self.assertEqual(AuditEvent.objects.filter(action='test.approve').count(), 1)

    def test_concurrent_refresh_only_rotates_once(self):
        from rest_framework.test import APIClient
        pair = APIClient().post('/api/v1/auth/login/', {'email': self.user.email, 'password': 'long-password'}, format='json').json()
        def worker(_):
            return APIClient().post('/api/v1/auth/refresh/', {'refresh': pair['refresh']}, format='json').status_code
        self.assertCountEqual(self.concurrent(worker), [200, 401])
