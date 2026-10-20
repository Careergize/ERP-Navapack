import copy
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
from django.test import TransactionTestCase, override_settings
from django.db import connection, connections, transaction, DatabaseError
from django.contrib.auth.models import Permission
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.commercial import governance
from apps.commercial.models import GovernanceRecord, GovernanceRevision, CommercialRevision, CommercialDocument
from apps.core.models import AuditEvent, IdempotencyRecord
from apps.inventory.ledger_models import LedgerTransaction, LedgerEntry, BalanceProjection
from apps.inventory.ledger_guard import synthetic_write
from apps.masters.models import Unit, Material, ProductVariant
from apps.specifications.models import ProductModel, ProductModelRevision
from tests import test_commercial


class Phase4BTests(TransactionTestCase):
    def setUp(self):
        self.fx = test_commercial.CommercialTests(); self.fx.setUp()
        self.client = self.fx.client; self.user = self.fx.user

    def proposal(self, kind='POLICY', data=None, key=None, record=None, version=None):
        body = {'data': data if data is not None else self.policy(), 'reason': 'Synthetic evidence only'}
        headers = {'HTTP_IDEMPOTENCY_KEY': key or str(uuid.uuid4())}
        root = '/api/v1/commercial/'+('policy-proposals/' if kind == 'POLICY' else 'decision-submissions/')
        if record:
            return self.client.patch(root+record['id']+'/', body, format='json', HTTP_IF_MATCH=f'"{version or record["version"]}"', **headers)
        return self.client.post(root, body, format='json', **headers)

    def policy(self, **extra):
        return {'policy_type': 'VAT_LED', 'title': 'Synthetic conflicting proposal', 'draft_payload': {'vat': '18', 'denominator': 'unresolved'},
                'evidence': [{'reference': 'synthetic:source-a', 'description': 'Unverified, not fiscal authority'}], 'proposed_effective_date': '2026-11-01', **extra}

    def answer(self, **extra):
        return {'decision_id': 'P4-01', 'answer': 'Client-entered answer remains unverified',
                'evidence': [{'reference': 'synthetic:answer', 'description': 'Not independently reviewed'}], **extra}

    def test_all_nine_policy_types_are_proposals_only(self):
        from apps.commercial.decision_catalog import POLICY_TYPES
        for kind in POLICY_TYPES:
            r = self.proposal(data=self.policy(policy_type=kind)); self.assertEqual(r.status_code, 201, r.data)
            self.assertEqual(r.data['status'], 'PROPOSED_UNVERIFIED')
            self.assertFalse(r.data['authority']); self.assertFalse(r.data['active']); self.assertFalse(r.data['approved'])

    def test_policy_revisions_immutable_replay_stale_and_identity(self):
        first = self.proposal(key='same'); self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(self.proposal(key='same').data, first.data)
        self.assertEqual(self.proposal(data=self.policy(title='Different'), key='same').status_code, 409)
        second = self.proposal(data=self.policy(title='New evidence'), record=first.data)
        self.assertEqual(second.status_code, 200, second.data)
        self.assertEqual(self.proposal(record=first.data).status_code, 412)
        self.assertEqual(GovernanceRevision.objects.get(pk=first.data['revision']).content['title'], 'Synthetic conflicting proposal')
        self.assertEqual(self.proposal(data=self.policy(policy_type='APPROVAL_MATRIX'), record=second.data).status_code, 400)

    def test_decision_registry_preserves_conflicts_and_pending_answers(self):
        policy = self.proposal().data
        answer = self.proposal('DECISION', self.answer(linked_policy_revision=policy['revision']))
        self.assertEqual(answer.status_code, 201, answer.data)
        self.assertEqual(answer.data['status'], 'PENDING_VERIFICATION')
        reg = self.client.get('/api/v1/commercial/decision-registry/').data
        self.assertEqual(len(reg['results']), 8)
        first = reg['results'][0]; self.assertEqual(first['status'], 'PENDING_VERIFICATION')
        self.assertEqual(first['baseline_status'], 'OPEN'); self.assertFalse(first['review_performed'])
        self.assertEqual(len(first['conflicting_evidence']), 3)
        self.assertEqual(first['latest_submission']['content']['linked_policy_snapshot']['revision'], policy['revision'])
        self.assertEqual(self.proposal('DECISION', self.answer()).status_code, 400)
        updated = self.proposal('DECISION', self.answer(answer='Changed answer'), record=answer.data)
        self.assertEqual(updated.status_code, 200, updated.data)
        history = self.client.get('/api/v1/commercial/decision-submissions/'+answer.data['id']+'/history/').data
        self.assertEqual(history['count'], 2); self.assertTrue(all(not r['review_performed'] for r in history['results']))

    def test_proposals_cannot_activate_transitions_or_taxes(self):
        p = self.proposal(data=self.policy(draft_payload={'approved': True, 'active': True, 'vat': '18', 'allow_confirm': True}))
        self.assertEqual(p.status_code, 201)
        doc = self.fx.create().data
        for action in ('approve', 'confirm', 'send', 'accept', 'convert', 'amend_confirmed', 'cancel_confirmed'):
            self.assertEqual(self.fx.edit(doc, transition=action).status_code, 409)
        for field in ('vat_rate', 'led', 'tax_policy', 'policy_revision'):
            d = self.fx.data(); d[field] = p.data['revision']
            self.assertEqual(self.fx.create(data=d).status_code, 400)
        self.assertIsNone(doc['snapshot']['estimate']['payable_total'])
        for model in (LedgerTransaction, LedgerEntry, BalanceProjection): self.assertEqual(model.objects.count(), 0)
        self.assertEqual(self.client.post('/api/v1/commercial/policy-proposals/'+p.data['id']+'/approve/', {}, format='json').status_code, 404)

    def test_proposal_capability_owner_replay_and_link_scope(self):
        p = self.proposal(key='replay').data
        doc = self.fx.create().data
        self.client.force_authenticate(self.fx.other)
        root = '/api/v1/commercial/policy-proposals/'
        self.assertEqual(self.client.get(root).data['count'], 0)
        self.assertEqual(self.client.get(root+p['id']+'/').status_code, 404)
        self.assertEqual(self.client.get(root+p['id']+'/history/').status_code, 404)
        self.assertEqual(self.proposal(record=p).status_code, 404)
        self.assertEqual(self.proposal('DECISION', self.answer(linked_policy_revision=p['revision'])).status_code, 404)
        self.assertEqual(self.fx.edit(doc, transition='submit').status_code, 404)
        self.client.force_authenticate(self.user)
        self.user.user_permissions.remove(Permission.objects.get(content_type__app_label='commercial', codename='manage_proposals'))
        self.assertEqual(self.proposal(key='replay').status_code, 403)
        technical = User.objects.create_superuser('phase4b-technical@example.test', 'password')
        self.client.force_authenticate(technical); self.assertEqual(self.proposal().status_code, 403)

    def test_unknown_status_override_payload_bounds_and_disabled_environment(self):
        for data in (self.policy(status='APPROVED'), self.policy(active=True), self.policy(draft_payload={'huge': 'x'*8001}), self.policy(evidence=[])):
            self.assertEqual(self.proposal(data=data).status_code, 400)
        with override_settings(SYNTHETIC_LEDGER_ENABLED=False):
            self.assertEqual(self.proposal().status_code, 403)
            self.assertEqual(self.client.get('/api/v1/commercial/decision-registry/').status_code, 403)

    def test_proposal_audit_failure_rolls_back(self):
        with patch('apps.core.commands.record_event', side_effect=RuntimeError('Synthetic rollback')):
            self.assertEqual(self.proposal(key='rollback').status_code, 500)
        self.assertEqual(GovernanceRecord.objects.count(), 0); self.assertEqual(GovernanceRevision.objects.count(), 0)
        self.assertFalse(IdempotencyRecord.objects.filter(key='rollback').exists())

    def test_proposal_database_immutability_and_activation_rejection(self):
        p = self.proposal().data
        with self.assertRaises(DatabaseError), synthetic_write(), connection.cursor() as c:
            c.execute('UPDATE commercial_governancerevision SET status=%s WHERE id=%s', ['APPROVED', p['revision']])
        with self.assertRaises(DatabaseError), transaction.atomic():
            GovernanceRecord.objects.create(owner=self.user, kind='POLICY', key='VAT_LED')
        with self.assertRaises(DatabaseError), synthetic_write():
            record = GovernanceRecord.objects.create(owner=self.user, kind='POLICY', key='VAT_LED')
            GovernanceRevision.objects.create(record=record, number=1, author=self.user, status='PROPOSED_UNVERIFIED',
                content=self.policy(), reason='No audit', sha256='a'*64)

    def test_concurrent_proposal_edit_one_winner(self):
        p = self.proposal().data; barrier = Barrier(2)
        def worker():
            connections.close_all()
            try:
                actor = User.objects.get(pk=self.user.pk); barrier.wait()
                try:
                    governance.command(actor=actor, kind='POLICY', data=self.policy(), reason='Synthetic edit', key=str(uuid.uuid4()), request_id=uuid.uuid4(), pk=p['id'], version=1)
                    return 200
                except Exception as e: return getattr(e, 'status_code', str(e))
            finally: connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool: results = list(pool.map(lambda _: worker(), range(2)))
        self.assertEqual(sorted(results), [200, 412])

    def test_multicomponent_costing_round_once_and_markup_margin(self):
        data = self.fx.data(True); line = data['lines'][0]; c = line['costing']
        c['materials'] = [{**c['materials'][0], 'quantity': '1', 'price': '0.0025'}, {**c['materials'][0], 'quantity': '1', 'price': '0.0025'}]
        c['processes'] = [{'description': 'A', 'currency': 'UGX', 'amount': '0.0025'}, {'description': 'B', 'currency': 'UGX', 'amount': '0.0025'}]
        c['markup_percent'] = '25'; line.update(quantity='1', unit_price='0.02')
        r = self.fx.create('COSTING', data); self.assertEqual(r.status_code, 201, r.data)
        cost = r.data['snapshot']['estimate']['lines'][0]['costing']
        self.assertEqual(cost['estimated_production_cost'], '0.01')
        self.assertEqual(cost['gross_margin_percent'], '20.000000')
        self.assertEqual(cost['entered_gross_margin_percent_before_discount'], '50.000000')
        self.assertEqual(cost['loss_treatment'], 'Entered gross consumption; no automatic yield scaling')

    def test_micro_max_precision_large_and_invalid_amounts(self):
        data = self.fx.data(True); m = data['lines'][0]['costing']['materials'][0]
        m.update(quantity='0.000001', price='0.000001'); data['lines'][0]['costing']['processes'] = []
        data['lines'][0].update(quantity='0.000001', unit_price='0.000001')
        r = self.fx.create('COSTING', data); self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['snapshot']['estimate']['lines'][0]['costing']['estimated_production_cost'], '0.00')
        m.update(quantity='999999999999.999999', price='999999999999.999999'); data['lines'][0].update(quantity='1', unit_price='1')
        r = self.fx.create('COSTING', data); self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['snapshot']['estimate']['lines'][0]['costing']['material_cost'], '999999999999999998000000.00')
        data['lines'][0]['costing']['markup_percent'] = '999999999999.999999'
        self.assertEqual(self.fx.create('COSTING', data).status_code, 400)
        for bad in ('-1', 'NaN', 'Infinity', '1e3', '1000000000000', '0.0000001'):
            d = self.fx.data(True); d['lines'][0]['costing']['materials'][0]['price'] = bad
            self.assertEqual(self.fx.create('COSTING', d).status_code, 400)

    def test_zero_negative_mixed_process_unknown_fx_and_discount(self):
        for change in (lambda d: d['lines'][0]['costing']['materials'][0].update(quantity='0'),
                       lambda d: d['lines'][0]['costing']['processes'][0].update(amount='-1'),
                       lambda d: d['lines'][0]['costing']['processes'][0].update(currency='USD'),
                       lambda d: d['lines'][0]['costing'].update(exchange_rate='1'),
                       lambda d: d['lines'][0]['costing']['processes'][0].update(extra='x')):
            d = self.fx.data(True); change(d); self.assertEqual(self.fx.create('COSTING', d).status_code, 400)
        d = self.fx.data(); d.update(discount='3.02'); self.assertEqual(self.fx.create(data=d).data['snapshot']['estimate']['net_estimate'], '0.00')
        d['discount'] = '3.03'; self.assertEqual(self.fx.create(data=d).status_code, 400)

    def test_historical_link_and_equivalent_decimal_notation(self):
        cost = self.fx.create('COSTING').data; original = copy.deepcopy(cost['snapshot'])
        self.fx.variant.name = 'Changed product'; self.fx.variant.save()
        self.fx.material.name = 'Changed input'; self.fx.material.save()
        d = self.fx.data(); d['lines'][0].update(quantity='3.000000', costing_revision=cost['revision'])
        q = self.fx.create(data=d); self.assertEqual(q.status_code, 201, q.data)
        self.assertEqual(q.data['snapshot']['input']['lines'][0]['costing_snapshot']['source'], original)
        for field, value in [('currency', 'USD'), ('specifications', 'Changed spec'), ('quantity', '4')]:
            body = copy.deepcopy(d)
            if field == 'currency': body[field] = value
            else: body['lines'][0][field] = value
            self.assertEqual(self.fx.create(data=body).status_code, 400)

    def test_invalid_specification_reference_and_native_unit_labels(self):
        d = self.fx.data(); d['lines'][0]['variant'] = str(uuid.uuid4())
        self.assertEqual(self.fx.create(data=d).status_code, 404)
        model = ProductModel.objects.create(name='Synthetic specification', created_by=self.user, updated_by=self.user)
        revision = ProductModelRevision.objects.create(model=model, number=1, created_by=self.user, name='Unsealed', default_unit=self.fx.unit, recipe_mode='quantities')
        d = self.fx.data(); d['lines'][0]['model_revision'] = str(revision.pk)
        self.assertEqual(self.fx.create(data=d).status_code, 404)
        revision.default_unit = self.fx.ctr; revision.sealed = True; revision.save()
        self.assertEqual(self.fx.create(data=d).status_code, 400)
        alias = Unit.objects.create(name='Unapproved alias', code='KGS', dimension='mass', created_by=self.user, updated_by=self.user)
        variant = ProductVariant.objects.create(name='Synthetic alias variant', product=self.fx.variant.product, unit=alias, category='packing', created_by=self.user, updated_by=self.user)
        d = self.fx.data(True); d['lines'][0].update(variant=str(variant.pk), unit=str(alias.pk))
        r = self.fx.create('COSTING', d); self.assertEqual(r.status_code, 201, r.data)
        c = r.data['snapshot']['estimate']['lines'][0]['costing']; self.assertIsNone(c['cost_per_kg']); self.assertIsNone(c['cost_per_ctr'])

    def test_reference_lists_scope_and_marketing_selection(self):
        cost = self.fx.create('COSTING').data
        rows = self.client.get('/api/v1/commercial/references/costing-revisions/').data
        self.assertEqual(rows['count'], 1); self.assertEqual(rows['results'][0]['id'], cost['revision'])
        self.client.force_authenticate(self.fx.other)
        self.assertEqual(self.client.get('/api/v1/commercial/references/costing-revisions/').data['count'], 0)
        self.client.force_authenticate(self.user)
        employees = self.client.get('/api/v1/commercial/references/marketing-people/').data
        self.assertEqual(len(employees['results']), 1)
        d = self.fx.data(); d['marketing_person'] = str(self.fx.other.employee.pk)
        self.assertEqual(self.fx.create(data=d).status_code, 404)
        d['marketing_person'] = employees['results'][0]['id']; self.assertEqual(self.fx.create(data=d).status_code, 201)

    def test_audit_revision_link_reason_and_edit_rollback(self):
        doc = self.fx.create().data
        r = self.client.get('/api/v1/commercial/documents/'+doc['id']+'/history/').data['results'][0]
        self.assertEqual(r['audit']['revision'], r['id']); self.assertEqual(r['audit']['actor'], str(self.user.pk))
        event = AuditEvent.objects.get(pk=r['audit']['id']); self.assertEqual(event.reason, r['reason'])
        with patch('apps.core.commands.record_event', side_effect=RuntimeError('Synthetic audit failure')):
            self.assertEqual(self.fx.edit(doc).status_code, 500)
        self.assertEqual(CommercialDocument.objects.get(pk=doc['id']).version, 1)
        self.assertEqual(CommercialRevision.objects.filter(document_id=doc['id']).count(), 1)

    def test_database_refuses_authoritative_snapshot_and_forged_initial_state(self):
        with self.assertRaises(DatabaseError), synthetic_write():
            CommercialDocument.objects.create(owner=self.user, kind='SALES_ORDER', version=2, status='REVIEW')
        doc = self.fx.create().data
        forged = copy.deepcopy(doc['snapshot']); forged['estimate']['vat'] = '1.00'
        with self.assertRaises(DatabaseError), synthetic_write():
            head = CommercialDocument.objects.create(owner=self.user, kind='QUOTATION')
            CommercialRevision.objects.create(document=head, number=1, actor=self.user, status='DRAFT', reason='Forged fiscal value', snapshot=forged, sha256='a'*64)
        with self.assertRaises(DatabaseError), synthetic_write(), connection.cursor() as c:
            c.execute('UPDATE commercial_commercialrevision SET snapshot=%s WHERE id=%s', ['{}', doc['revision']])
