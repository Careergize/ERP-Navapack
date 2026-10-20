import copy
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
from django.db import connections
from django.contrib.auth.models import Permission
from django.db import DatabaseError, transaction
from django.test import TransactionTestCase
from django.utils import timezone
from datetime import timedelta
from apps.inventory.models import Warehouse, WarehouseScope
from apps.inventory.ledger_models import LedgerEntry, LedgerTransaction, BalanceProjection
from apps.rehearsal.models import RehearsalJob, RehearsalRevision
from tests import test_commercial


class RehearsalTests(TransactionTestCase):
    """Reuse commercial fixtures without duplicating their test collection."""
    data = test_commercial.CommercialTests.data
    create = test_commercial.CommercialTests.create

    def setUp(self):
        test_commercial.CommercialTests.setUp(self)
        self.user.user_permissions.add(Permission.objects.get(content_type__app_label='rehearsal', codename='use_simulation'))
        self.warehouse = Warehouse.objects.create(code='SYN-REHEARSAL', name='Synthetic rehearsal',
            created_by=self.user)
        WarehouseScope.objects.create(user=self.user, warehouse=self.warehouse,
            expires_at=timezone.now()+timedelta(hours=1), requested_by=self.user,
            approved_by=self.other, policy_reference='synthetic:policy', evidence_reference='synthetic:scope')

    def job(self, **overrides):
        order = self.create('SALES_ORDER').data
        data = {'sales_order_revision': order['revision'], 'warehouse': str(self.warehouse.pk),
            'routes': [{'line': 0, 'stages': ['PACKING']}], 'reason': 'Synthetic job'}
        data.update(overrides)
        return self.client.post('/api/v1/rehearsal/jobs/', data, format='json', HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()))

    def step(self, job, action, data=None, key=None, version=None):
        return self.client.post('/api/v1/rehearsal/jobs/'+job['id']+'/command/',
            {'action': action, 'data': data or {}, 'reason': 'Synthetic step'}, format='json',
            HTTP_IF_MATCH=f'"{version or job["version"]}"', HTTP_IDEMPOTENCY_KEY=key or str(uuid.uuid4()))

    def test_rehearsal_full_path_no_operational_posting(self):
        before = [m.objects.count() for m in (LedgerEntry, LedgerTransaction, BalanceProjection)]
        response = self.job(); self.assertEqual(response.status_code, 201, response.data)
        job = response.data
        for action, data in [('review', {}), ('issue', {'quantity': '10', 'available_quantity': '10'}),
            ('start', {'line': 0, 'stage': 'PACKING', 'machine': 'synthetic:packing', 'operator': 'synthetic:operator', 'input_quantity': '10'}),
            ('complete', {'line': 0, 'stage': 'PACKING', 'output_quantity': '9', 'waste': '1', 'rejection': '0'}),
            ('qc', {'outcome': 'FAIL'}), ('qc', {'outcome': 'PASS'}), ('finish', {}), ('dispatch', {})]:
            response = self.step(job, action, data); self.assertEqual(response.status_code, 200, response.data); job = response.data
        self.assertEqual(job['status'], 'DISPATCHED')
        self.assertIsNone(job['invoice_preview']['payable_total'])
        self.assertEqual(len(job['snapshot']['qc']), 2)
        self.assertEqual(RehearsalRevision.objects.filter(job_id=job['id']).count(), 9)
        self.assertEqual([m.objects.count() for m in (LedgerEntry, LedgerTransaction, BalanceProjection)], before)

    def test_rehearsal_replay_stale_edit_and_guards(self):
        job = self.job().data; original = copy.deepcopy(job['snapshot'])
        key = str(uuid.uuid4())
        result = self.step(job, 'review', key=key); self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(self.step(job, 'review', key=key).data, result.data)
        self.assertEqual(self.step(job, 'review').status_code, 412)
        self.assertEqual(RehearsalRevision.objects.get(job_id=job['id'], number=1).snapshot['state'], original)
        with self.assertRaises(DatabaseError), transaction.atomic():
            RehearsalJob.objects.filter(pk=job['id']).update(status='DISPATCHED')
        with self.assertRaises(ValueError):
            RehearsalRevision.objects.filter(job_id=job['id']).update(reason='tamper')

    def test_rehearsal_blocked_progression_stock_and_permission(self):
        job = self.job().data
        self.assertEqual(self.step(job, 'finish').status_code, 409)
        job = self.step(job, 'review').data
        self.assertEqual(self.step(job, 'issue', {'quantity': '11', 'available_quantity': '10'}).status_code, 409)
        self.assertEqual(self.step(job, 'issue', {'quantity': 10, 'available_quantity': '10'}).status_code, 400)
        self.user.user_permissions.remove(Permission.objects.get(content_type__app_label='rehearsal', codename='use_simulation'))
        self.assertEqual(self.step(job, 'issue', {'quantity': '10', 'available_quantity': '10'}).status_code, 403)

    def test_rehearsal_scope_and_routes(self):
        self.assertEqual(self.job(routes=[{'line': 1, 'stages': ['PACKING']}]).status_code, 400)
        self.assertEqual(self.job(routes=[{'line': 0, 'stages': ['PACKING', 'EXTRUSION']}]).status_code, 400)
        job = self.job().data
        future = timezone.now() + timedelta(hours=2)
        with patch('apps.inventory.authorization.timezone.now', return_value=future):
            self.assertEqual(self.client.get('/api/v1/rehearsal/jobs/'+job['id']+'/').status_code, 404)

    def test_rehearsal_concurrent_edits_have_one_winner(self):
        from apps.rehearsal.services import command
        from apps.core.api import VersionConflict
        from django.contrib.auth import get_user_model
        job = self.job().data
        barrier = Barrier(2)
        actor_id = self.user.pk
        def edit():
            try:
                actor = get_user_model().objects.get(pk=actor_id)
                barrier.wait(timeout=10)
                command(actor=actor, pk=job['id'], version=1, action='review', data={},
                    reason='Synthetic concurrent review', key=str(uuid.uuid4()), request_id=uuid.uuid4())
                return 'success'
            except VersionConflict:
                return 'conflict'
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: edit(), range(2)))
        self.assertCountEqual(results, ['success', 'conflict'])
        self.assertEqual(RehearsalRevision.objects.filter(job_id=job['id']).count(), 2)

    def test_production_for_stock_costing_source_no_customer_dispatch(self):
        source = self.data(True)
        source.pop('customer')
        source.pop('classification')
        cost = self.create('COSTING', data=source).data
        self.assertIsNone(cost['snapshot']['input']['party_snapshot'])
        response = self.client.post('/api/v1/rehearsal/jobs/', {
            'costing_revision': cost['revision'], 'warehouse': str(self.warehouse.pk),
            'routes': [{'line': 0, 'stages': ['PACKING']}], 'reason': 'Synthetic stock job'},
            format='json', HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()))
        self.assertEqual(response.status_code, 201, response.data)
        job = response.data
        self.assertEqual(job['purpose'], 'PRODUCTION_FOR_STOCK')
        self.assertIsNone(job['sales_order_revision'])
        self.assertEqual(job['snapshot']['material_requirements'][0]['quantity'], '3')
        for action, data in [('review', {}), ('issue', {'quantity': '3', 'available_quantity': '3'}),
            ('start', {'line': 0, 'stage': 'PACKING', 'machine': 'synthetic:packing', 'operator': 'synthetic:operator', 'input_quantity': '3'}),
            ('complete', {'line': 0, 'stage': 'PACKING', 'output_quantity': '2.5', 'waste': '0.4', 'rejection': '0.1'}),
            ('qc', {'outcome': 'PASS'}), ('finish', {})]:
            response = self.step(job, action, data); self.assertEqual(response.status_code, 200, response.data); job = response.data
        self.assertFalse(job['invoice_preview']['available'])
        self.assertEqual(self.step(job, 'dispatch').status_code, 409)
        dashboard = self.client.get('/api/v1/rehearsal/jobs/dashboard/')
        self.assertEqual(dashboard.status_code, 200, dashboard.data)
        self.assertEqual(dashboard.data['production_by_unit'][0]['output_quantity'], '2.5')
        self.assertEqual(dashboard.data['production_by_unit'][0]['waste'], '0.4')
