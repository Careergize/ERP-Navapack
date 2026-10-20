import copy
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from datetime import timedelta
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import connection, connections, transaction, DatabaseError
from django.test import TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from apps.accounts.models import Employee
from apps.masters.models import Customer, Prospect, Unit, Product, ProductVariant, Material, Department
from apps.core.models import AuditEvent, IdempotencyRecord
from apps.commercial.models import CommercialDocument, CommercialRevision
from apps.commercial import services
from apps.inventory.ledger_models import LedgerTransaction, LedgerEntry, BalanceProjection
from apps.inventory.ledger_guard import synthetic_write
from apps.inventory.models import Warehouse, WarehouseScope, StockIdentity


class CommercialTests(TransactionTestCase):
    def setUp(self):
        self.assertEqual(connection.vendor, 'postgresql')
        self.user = get_user_model().objects.create_user('commercial@example.com', 'password')
        self.other = get_user_model().objects.create_user('other-commercial@example.com', 'password')
        fields = {'created_by': self.user, 'updated_by': self.user}
        department = Department.objects.create(name='Synthetic sales', **fields)
        for user in (self.user, self.other):
            Employee.objects.create(user=user, employee_id=str(user.pk), department=department, designation='Synthetic desk', **fields)
            user.user_permissions.add(*Permission.objects.filter(content_type__app_label__in=['commercial', 'masters', 'specifications', 'accounts']))
        self.customer = Customer.objects.create(name='Synthetic customer', customer_type='B2B', **fields)
        self.unit = Unit.objects.create(name='Kilogram', code='kg', dimension='mass', **fields)
        self.ctr = Unit.objects.create(name='Carton', code='ctr', dimension='package', **fields)
        product = Product.objects.create(name='Synthetic product', unit=self.unit, **fields)
        self.variant = ProductVariant.objects.create(name='Synthetic variant', product=product, unit=self.unit, category='packing', **fields)
        self.material = Material.objects.create(name='Synthetic material', unit=self.unit, category='virgin', **fields)
        self.client = APIClient(); self.client.force_authenticate(self.user)

    def data(self, costing=False):
        line = {'variant': str(self.variant.pk), 'unit': str(self.unit.pk), 'quantity': '3',
                'unit_price': '1.005', 'specifications': 'Synthetic specification', 'customisation': ''}
        if costing:
            line['costing'] = {'materials': [{'material': str(self.material.pk), 'unit': str(self.unit.pk),
                'price_unit': str(self.unit.pk), 'currency': 'UGX', 'quantity': '3', 'price': '1.005'}],
                'processes': [{'description': 'Synthetic process', 'currency': 'UGX', 'amount': '1'}],
                'waste_percent': '5', 'rejection_percent': '2', 'assumption_evidence': 'synthetic observation', 'markup_percent': '20'}
        return {'currency': 'UGX', 'money_places': 2, 'rounding': 'HALF_UP', 'customer': str(self.customer.pk),
                'classification': 'B2B', 'terms': '', 'discount': '0', 'lines': [line]}

    def create(self, kind='QUOTATION', data=None, key=None, client=None):
        return (client or self.client).post('/api/v1/commercial/documents/',
            {'kind': kind, 'data': data or self.data(kind == 'COSTING'), 'reason': 'Synthetic draft'},
            format='json', HTTP_IDEMPOTENCY_KEY=key or str(uuid.uuid4()))

    def edit(self, doc, data=None, version=None, transition=None):
        headers = {'HTTP_IF_MATCH': f'"{version or doc["version"]}"', 'HTTP_IDEMPOTENCY_KEY': str(uuid.uuid4())}
        url = '/api/v1/commercial/documents/'+doc['id']+'/'
        if transition:
            return self.client.post(url+'transition/', {'transition': transition, 'reason': 'Synthetic change'}, format='json', **headers)
        return self.client.patch(url, {'data': data or self.data(), 'reason': 'Synthetic amendment'}, format='json', **headers)

    def test_decimal_rounding_and_no_authoritative_total(self):
        data = self.data(); data['lines'][0]['quantity'] = '1'
        response = self.create(data=data); self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['snapshot']['estimate']['net_estimate'], '1.01')
        data['rounding'] = 'HALF_EVEN'
        result = self.create(data=data).data['snapshot']['estimate']
        self.assertEqual(result['net_estimate'], '1.00'); self.assertIsNone(result['payable_total'])

    def test_costing_versions_and_master_change_preserves_snapshot(self):
        first = self.create('COSTING'); self.assertEqual(first.status_code, 201, first.data)
        old = copy.deepcopy(first.data['snapshot'])
        cost = old['estimate']['lines'][0]['costing']
        self.assertEqual(cost['estimated_production_cost'], '4.02')
        self.assertEqual(cost['cost_per_kg'], '1.34'); self.assertIsNone(cost['cost_per_ctr'])
        self.material.name = 'Changed'; self.material.save()
        second = self.edit(first.data, self.data(True)); self.assertEqual(second.status_code, 200, second.data)
        self.assertEqual(CommercialRevision.objects.get(pk=first.data['revision']).snapshot, old)
        self.assertEqual(CommercialRevision.objects.count(), 2)

    def test_units_currency_and_tax_inputs_fail_closed(self):
        for mutate in (
            lambda d: d['lines'][0].update(unit=str(self.ctr.pk)),
            lambda d: d.update(vat_rate='18'),
            lambda d: d['lines'][0]['costing']['materials'][0].update(currency='USD'),
            lambda d: d['lines'][0]['costing']['materials'][0].update(price_unit=str(self.ctr.pk)),
            lambda d: d['lines'][0].update(quantity=3),
            lambda d: d['lines'][0].update(quantity='0'),
            lambda d: d['lines'][0].update(unit_price='0.1234567'),
            lambda d: d.update(discount='0.001'),
        ):
            data = self.data(True); mutate(data)
            self.assertEqual(self.create('COSTING', data).status_code, 400)
        self.assertEqual(CommercialDocument.objects.count(), 0)

    def test_multiline_order_no_stock_mutation(self):
        before = [m.objects.count() for m in (LedgerTransaction, LedgerEntry, BalanceProjection)]
        data = self.data(); data['lines'].append({**data['lines'][0], 'quantity': '7'})
        order = self.create('SALES_ORDER', data); self.assertEqual(order.status_code, 201, order.data)
        quote = self.create(); self.assertEqual(quote.status_code, 201)
        self.assertEqual(len(order.data['snapshot']['input']['lines']), 2)
        self.assertEqual([m.objects.count() for m in (LedgerTransaction, LedgerEntry, BalanceProjection)], before)

    def test_quote_review_reopen_revision_and_cancellation(self):
        doc = self.create().data
        review = self.edit(doc, transition='submit'); self.assertEqual(review.status_code, 200)
        self.assertEqual(self.edit(review.data).status_code, 409)
        reopened = self.edit(review.data, transition='reopen'); self.assertEqual(reopened.status_code, 200)
        cancelled = self.edit(reopened.data, transition='cancel'); self.assertEqual(cancelled.status_code, 200)
        self.assertEqual(self.edit(cancelled.data).status_code, 409)
        self.assertEqual(CommercialRevision.objects.count(), 4)

    def test_approval_and_customer_facing_actions_unavailable_even_superuser(self):
        self.user.is_superuser = True; self.user.save()
        doc = self.create().data
        for transition in ('approve', 'confirm', 'send', 'accept', 'dispatch', 'pdf', 'email'):
            self.assertEqual(self.edit(doc, transition=transition).status_code, 409)
        self.assertEqual(CommercialRevision.objects.count(), 1)

    def test_superuser_without_explicit_grant_denied(self):
        user = get_user_model().objects.create_superuser('technical@example.com', 'password')
        from apps.accounts.serializers import UserSerializer
        self.assertFalse(any(p.startswith('commercial.') for p in UserSerializer(user).data['permissions']))
        client = APIClient(); client.force_authenticate(user)
        self.assertEqual(self.create(client=client).status_code, 403)

    def test_owner_boundary_lists_detail_history_and_writes(self):
        doc = self.create().data
        self.client.force_authenticate(self.other)
        base = '/api/v1/commercial/documents/'
        self.assertEqual(self.client.get(base).data['count'], 0)
        self.assertEqual(self.client.get(base+doc['id']+'/').status_code, 404)
        self.assertEqual(self.client.get(base+doc['id']+'/history/').status_code, 404)
        self.assertEqual(self.edit(doc).status_code, 404)

    def test_idempotent_creation_conflict_and_replay_after_master_change(self):
        first = self.create(key='retry'); second = self.create(key='retry')
        self.assertEqual(first.data, second.data)
        self.customer.is_active = False; self.customer.save()
        self.assertEqual(self.create(key='retry').data, first.data)
        data = self.data(); data['terms'] = 'changed'
        self.assertEqual(self.create(data=data, key='retry').status_code, 409)
        self.assertEqual(AuditEvent.objects.filter(entity_id=first.data['id']).count(), 1)

    def test_replay_rechecks_capability(self):
        self.create(key='retry')
        self.user.user_permissions.clear()
        self.assertEqual(self.create(key='retry').status_code, 403)

    def test_stale_edit_and_required_precondition(self):
        doc = self.create().data
        self.assertEqual(self.edit(doc).status_code, 200)
        self.assertEqual(self.edit(doc).status_code, 412)
        response = self.client.patch('/api/v1/commercial/documents/'+doc['id']+'/', {'data': self.data(), 'reason': 'x'}, format='json')
        self.assertEqual(response.status_code, 428)

    def test_audit_failure_rolls_back_document_revision_and_key(self):
        with patch('apps.core.commands.record_event', side_effect=RuntimeError('Synthetic audit failure')):
            self.assertEqual(self.create(key='rollback').status_code, 500)
        self.assertEqual(CommercialDocument.objects.count(), 0)
        self.assertEqual(CommercialRevision.objects.count(), 0)
        self.assertFalse(IdempotencyRecord.objects.filter(key='rollback').exists())

    def test_db_revision_immutability_and_unstamped_write_denial(self):
        doc = self.create().data
        with self.assertRaises(DatabaseError), transaction.atomic(), connection.cursor() as c:
            c.execute('UPDATE commercial_commercialrevision SET reason=%s WHERE id=%s', ['tamper', doc['revision']])
        with self.assertRaises(DatabaseError), transaction.atomic():
            CommercialDocument.objects.create(kind='QUOTATION', owner=self.user)

    def test_missing_atomic_audit_rejected_by_database(self):
        with self.assertRaises(DatabaseError), synthetic_write():
            doc = CommercialDocument.objects.create(kind='QUOTATION', owner=self.user)
            CommercialRevision.objects.create(document=doc, number=1, actor=self.user, status='DRAFT', reason='unaudited', snapshot={}, sha256='x'*64)
        self.assertEqual(CommercialDocument.objects.count(), 0)

    def test_disabled_environment_denies_reads_and_writes(self):
        with override_settings(SYNTHETIC_LEDGER_ENABLED=False):
            self.assertEqual(self.create().status_code, 403)
            self.assertEqual(self.client.get('/api/v1/commercial/documents/').status_code, 403)

    def test_prospect_quote_but_not_order(self):
        prospect = Prospect.objects.create(name='Synthetic prospect', created_by=self.user, updated_by=self.user)
        data = self.data(); del data['customer']; data['prospect'] = str(prospect.pk)
        self.assertEqual(self.create(data=data).status_code, 201)
        self.assertEqual(self.create('SALES_ORDER', data).status_code, 400)

    def test_product_costing_without_party_and_commercial_party_required(self):
        data = self.data(True); del data['customer']; del data['classification']
        cost = self.create('COSTING', data); self.assertEqual(cost.status_code, 201, cost.data)
        self.assertIsNone(cost.data['snapshot']['input']['party_snapshot'])
        del data['lines'][0]['costing']
        self.assertEqual(self.create('QUOTATION', data).status_code, 400)
        self.assertEqual(self.create('SALES_ORDER', data).status_code, 400)

    def test_costing_link_preserves_exact_snapshot_and_rejects_mismatch(self):
        cost = self.create('COSTING').data
        data = self.data(); data['lines'][0]['costing_revision'] = cost['revision']
        quote = self.create(data=data); self.assertEqual(quote.status_code, 201, quote.data)
        data['lines'][0]['quantity'] = '4'
        self.assertEqual(self.create(data=data).status_code, 400)
        self.assertEqual(quote.data['snapshot']['input']['lines'][0]['costing_snapshot']['source'], cost['snapshot'])

    def test_draft_quotation_cannot_authorize_order(self):
        quote = self.create().data
        data = self.data(); data['quotation_revision'] = quote['revision']
        self.assertEqual(self.create('SALES_ORDER', data).status_code, 409)

    def test_reference_capability_boundary(self):
        self.user.user_permissions.remove(Permission.objects.get(content_type__app_label='masters', codename='view_customer'))
        self.assertEqual(self.create().status_code, 403)

    def test_native_carton_cost_has_no_kg_conversion(self):
        product = self.variant.product
        variant = ProductVariant.objects.create(name='Synthetic carton variant', product=product, unit=self.ctr,
            category='packing', created_by=self.user, updated_by=self.user)
        data = self.data(True); data['lines'][0].update(variant=str(variant.pk), unit=str(self.ctr.pk))
        response = self.create('COSTING', data); self.assertEqual(response.status_code, 201, response.data)
        cost = response.data['snapshot']['estimate']['lines'][0]['costing']
        self.assertEqual(cost['cost_per_ctr'], '1.34'); self.assertIsNone(cost['cost_per_kg'])

    def test_warehouse_identity_reference_requires_scope_and_never_reserves(self):
        warehouse = Warehouse.objects.create(code='SYN', name='Synthetic warehouse', created_by=self.user)
        stock = StockIdentity.objects.create(warehouse=warehouse, variant=self.variant, unit=self.unit, kind='BATCH',
            ownership='COMPANY', ownership_evidence='synthetic:owner', source_system='synthetic:commercial',
            source_reference='synthetic:stock', created_by=self.user)
        data = self.data(); data['lines'][0]['stock_identity'] = str(stock.pk)
        self.assertEqual(self.create('SALES_ORDER', data).status_code, 403)
        self.user.user_permissions.add(Permission.objects.get(content_type__app_label='inventory', codename='view_stockidentity'))
        self.assertEqual(self.create('SALES_ORDER', data).status_code, 403)
        WarehouseScope.objects.create(user=self.user, warehouse=warehouse, requested_by=self.user, approved_by=self.other,
            policy_reference='synthetic:policy', evidence_reference='synthetic:evidence', expires_at=timezone.now()+timedelta(hours=1))
        response = self.create('SALES_ORDER', data); self.assertEqual(response.status_code, 201, response.data)
        self.assertFalse(response.data['snapshot']['input']['lines'][0]['stock_reference_snapshot']['reservation'])
        self.assertEqual(LedgerEntry.objects.count(), 0); self.assertEqual(BalanceProjection.objects.count(), 0)

    def test_concurrent_updates_have_one_winner(self):
        doc = self.create().data; barrier = Barrier(2)
        def worker():
            connections.close_all()
            try:
                actor = get_user_model().objects.get(pk=self.user.pk)
                barrier.wait()
                try:
                    services.command(actor=actor, key=str(uuid.uuid4()), request_id=uuid.uuid4(), pk=doc['id'],
                        version=1, data=self.data(), reason='Synthetic race')
                    return 200
                except Exception as e:
                    return getattr(e, 'status_code', str(e))
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: worker(), range(2)))
        self.assertEqual(sorted(results), [200, 412])

    def test_concurrent_idempotent_create(self):
        barrier = Barrier(2); data = self.data()
        def worker():
            connections.close_all()
            try:
                actor = get_user_model().objects.get(pk=self.user.pk); barrier.wait()
                return services.command(actor=actor, key='same-create', request_id=uuid.uuid4(), kind='SALES_ORDER',
                                        data=data, reason='Synthetic race')[0]['id']
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: worker(), range(2)))
        self.assertEqual(results[0], results[1]); self.assertEqual(CommercialDocument.objects.count(), 1)
