"""HTTP acceptance of draft lineage and isolated, non-operational execution."""
import copy
import uuid
from datetime import timedelta
from django.conf import settings
from django.contrib.auth.models import Permission
from django.test import TransactionTestCase
from django.utils import timezone
from apps.inventory.models import Warehouse, WarehouseScope
from apps.inventory.ledger_models import LedgerEntry, LedgerTransaction, BalanceProjection
from apps.inventory.quality_models import Inspection, QualityAuthorization, QualityPosting
from apps.masters.models import ProductVariant
from apps.commercial.models import CommercialRevision
from tests import test_commercial


class OneDayJourneyTests(TransactionTestCase):
    def setUp(self):
        if not getattr(settings, 'SYNTHETIC_LEDGER_ENABLED', False):
            self.skipTest('Requires the stamped disposable PostgreSQL runner.')
        self.fx = test_commercial.CommercialTests(); self.fx.setUp()
        self.client = self.fx.client
        self.fx.user.user_permissions.add(*Permission.objects.filter(content_type__app_label='rehearsal'))
        self.wh = Warehouse.objects.create(code='JOURNEY', name='Synthetic journey', created_by=self.fx.user)
        WarehouseScope.objects.create(user=self.fx.user, warehouse=self.wh,
            requested_by=self.fx.user, approved_by=self.fx.other,
            policy_reference='synthetic:scope', evidence_reference='synthetic:scope',
            expires_at=timezone.now()+timedelta(hours=1))

    def post(self, url, body, key=None, version=None):
        headers = {'HTTP_IDEMPOTENCY_KEY': key or str(uuid.uuid4())}
        if version is not None: headers['HTTP_IF_MATCH'] = f'"{version}"'
        return self.client.post(url, body, format='json', **headers)

    def command(self, job, action, data=None, key=None):
        return self.post('/api/v1/rehearsal/jobs/'+job['id']+'/command/',
            {'action': action, 'data': data or {}, 'reason': 'Synthetic acceptance'}, key, job['version'])

    def test_customer_to_dispatch_preview_retains_lineage_without_operational_posting(self):
        protected = (LedgerEntry, LedgerTransaction, BalanceProjection, Inspection, QualityAuthorization, QualityPosting)
        before = [m.objects.count() for m in protected]
        customer = self.post('/api/v1/customers/', {'name': 'Synthetic journey customer', 'customer_type': 'B2B'})
        self.assertEqual(customer.status_code, 201, customer.data)
        variant = ProductVariant.objects.create(name='Synthetic second product', product=self.fx.variant.product,
            unit=self.fx.unit, category='packing', created_by=self.fx.user, updated_by=self.fx.user)
        data = self.fx.data(True); data['customer'] = customer.data['id']
        data['lines'].append({**copy.deepcopy(data['lines'][0]), 'variant': str(variant.pk)})
        costing = self.fx.create('COSTING', data)
        self.assertEqual(costing.status_code, 201, costing.data)
        current = costing.data
        for kind in ('QUOTATION', 'SALES_ORDER'):
            derived = self.post('/api/v1/commercial/documents/'+current['id']+'/derive/',
                {'source_revision': current['revision'], 'reason': 'Synthetic draft mapping'})
            self.assertEqual(derived.status_code, 201, derived.data)
            self.assertEqual(derived.data['kind'], kind)
            self.assertEqual(derived.data['snapshot']['synthetic_source']['revision'], current['revision'])
            current = derived.data
        body = {'sales_order_revision': current['revision'], 'warehouse': str(self.wh.pk),
            'routes': [{'line': 0, 'stages': ['EXTRUSION', 'PACKING']}, {'line': 1, 'stages': ['PACKING']}],
            'reason': 'Synthetic journey'}
        created = self.post('/api/v1/rehearsal/jobs/', body, 'journey-create')
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(self.post('/api/v1/rehearsal/jobs/', body, 'journey-create').data, created.data)
        job = created.data
        result = self.command(job, 'review'); self.assertEqual(result.status_code, 200, result.data); job = result.data
        self.assertEqual(self.command(job, 'issue', {'quantity': '10', 'available_quantity': '9'}).status_code, 409)
        result = self.command(job, 'issue', {'quantity': '10', 'available_quantity': '10'})
        self.assertEqual(result.status_code, 200, result.data); job = result.data
        self.assertEqual(self.command(created.data, 'review').status_code, 412)
        self.assertEqual(self.command(job, 'qc', {'outcome': 'PASS'}).status_code, 409)
        for line, stage in ((0, 'EXTRUSION'), (0, 'PACKING'), (1, 'PACKING')):
            started = self.command(job, 'start', {'line': line, 'stage': stage, 'machine': 'synthetic:machine',
                'operator': 'synthetic:operator', 'input_quantity': '3'})
            self.assertEqual(started.status_code, 200, started.data); job = started.data
            complete = self.command(job, 'complete', {'line': line, 'stage': stage,
                'output_quantity': '3', 'waste': '0', 'rejection': '0'})
            self.assertEqual(complete.status_code, 200, complete.data); job = complete.data
        result = self.command(job, 'qc', {'outcome': 'FAIL', 'remarks': 'Synthetic failure'})
        self.assertEqual(result.status_code, 200, result.data); job = result.data
        self.assertEqual(self.command(job, 'finish').status_code, 409)
        for action, values in (('qc', {'outcome': 'PASS', 'remarks': 'Synthetic reinspection'}), ('finish', {}), ('dispatch', {})):
            result = self.command(job, action, values); self.assertEqual(result.status_code, 200, result.data); job = result.data
        self.assertEqual(job['status'], 'DISPATCHED')
        self.assertTrue(job['invoice_preview']['available'])
        self.assertIsNone(job['invoice_preview']['payable_total'])
        self.assertIn('NOT APPROVED FOR CUSTOMER ISSUE', job['invoice_preview']['watermark'])
        self.assertEqual(job['sales_order_revision'], current['revision'])
        self.assertEqual(len(job['snapshot']['source']['input']['lines']), 2)
        self.assertEqual(self.client.get('/api/v1/rehearsal/jobs/dashboard/').data['statuses']['DISPATCHED'], 1)
        history = self.client.get('/api/v1/rehearsal/jobs/'+job['id']+'/history/').data
        self.assertEqual(history['count'], job['version'])
        self.assertEqual(CommercialRevision.objects.get(pk=costing.data['revision']).snapshot, costing.data['snapshot'])
        self.assertEqual([m.objects.count() for m in protected], before)
        self.assertFalse(job['operational_posting'])
        self.client.force_authenticate(self.fx.other)
        self.assertEqual(self.client.get('/api/v1/rehearsal/jobs/').status_code, 403)
        self.fx.other.user_permissions.add(*Permission.objects.filter(content_type__app_label='rehearsal'))
        self.assertEqual(self.client.get('/api/v1/rehearsal/jobs/'+job['id']+'/').status_code, 404)
        self.client.force_authenticate(self.fx.user)
        outside = Warehouse.objects.create(code='OUTSIDE', name='Synthetic outside scope', created_by=self.fx.user)
        self.assertEqual(self.post('/api/v1/rehearsal/jobs/', {**body, 'warehouse': str(outside.pk)}).status_code, 403)
        self.assertEqual([m.objects.count() for m in protected], before)
