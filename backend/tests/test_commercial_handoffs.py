import copy
import uuid
from django.test import TransactionTestCase
from apps.commercial.models import CommercialRevision
from apps.inventory.ledger_models import LedgerEntry, LedgerTransaction, BalanceProjection
from tests import test_commercial


class DraftHandoffTests(TransactionTestCase):
    def setUp(self):
        self.fx = test_commercial.CommercialTests(); self.fx.setUp()
        self.client = self.fx.client

    def derive(self, source, key=None, client=None):
        return (client or self.client).post(f'/api/v1/commercial/documents/{source["id"]}/derive/',
            {'source_revision': source['revision'], 'reason': 'Synthetic draft mapping'},
            format='json', HTTP_IDEMPOTENCY_KEY=key or str(uuid.uuid4()))

    def test_costing_quote_order_lineage_retry_and_no_stock(self):
        cost = self.fx.create('COSTING').data
        quote = self.derive(cost); self.assertEqual(quote.status_code, 201, quote.data)
        self.assertEqual(quote.data['snapshot']['input']['lines'][0]['costing_revision'], cost['revision'])
        key = str(uuid.uuid4())
        order = self.derive(quote.data, key); self.assertEqual(order.status_code, 201, order.data)
        retry = self.derive(quote.data, key); self.assertEqual(retry.data, order.data)
        self.assertEqual(order.data['snapshot']['synthetic_source']['revision'], quote.data['revision'])
        self.assertFalse(order.data['snapshot']['synthetic_source']['customer_acceptance'])
        self.assertIsNone(order.data['snapshot']['estimate']['payable_total'])
        self.assertEqual(CommercialRevision.objects.count(), 3)
        for model in (LedgerEntry, LedgerTransaction, BalanceProjection): self.assertEqual(model.objects.count(), 0)

    def test_lineage_retained_on_edit_and_historical_source_not_rebound(self):
        quote = self.fx.create().data
        order = self.derive(quote).data
        old = copy.deepcopy(order['snapshot']['synthetic_source'])
        edited = self.fx.edit(order)
        self.assertEqual(edited.status_code, 200, edited.data)
        self.assertEqual(edited.data['snapshot']['synthetic_source'], old)
        self.fx.edit(quote)
        second = self.derive(quote)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(CommercialRevision.objects.get(pk=order['revision']).snapshot['synthetic_source']['sha256'], quote['sha256'])

    def test_owner_invalid_source_and_cancelled_source(self):
        quote = self.fx.create().data
        self.client.force_authenticate(self.fx.other)
        self.assertEqual(self.derive(quote).status_code, 404)
        self.client.force_authenticate(self.fx.user)
        self.fx.edit(quote, transition='cancel')
        self.assertEqual(self.derive(quote).status_code, 400)
        order = self.fx.create('SALES_ORDER').data
        self.assertEqual(self.derive(order).status_code, 400)

    def test_no_authority_and_prospect_order_blocked(self):
        from apps.masters.models import Prospect
        prospect = Prospect.objects.create(name='Synthetic prospect', created_by=self.fx.user, updated_by=self.fx.user)
        data = self.fx.data(); data.pop('customer'); data['prospect'] = str(prospect.pk)
        quote = self.fx.create(data=data).data
        self.assertEqual(self.derive(quote).status_code, 400)
        self.fx.user.user_permissions.clear()
        self.assertEqual(self.derive(quote).status_code, 403)
