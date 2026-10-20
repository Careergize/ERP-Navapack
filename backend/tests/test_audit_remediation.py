import json
import uuid
from unittest.mock import patch
from django.test import TransactionTestCase
from django.db import transaction,DatabaseError
from rest_framework.exceptions import ValidationError
from apps.core.audit import record_event,EVIDENCE_LIMIT
from apps.core.models import AuditEvent,AuditEvidence
from apps.accounts.models import Role,Membership
from apps.accounts.employee_views import AuditEventSerializer
from tests.test_inventory import InventoryFoundationTests


class AuditRemediationTests(TransactionTestCase):
    setUp=InventoryFoundationTests.setUp
    post=InventoryFoundationTests.post
    patch=InventoryFoundationTests.patch

    def test_multirole_large_changes_preserve_full_evidence_and_scoped_history(self):
        for index in range(20):
            role=Role.objects.create(code=f'synthetic-audit-{index}',name='Synthetic audit role')
            Membership.objects.create(user=self.actor,role=role)
        obj=self.post('warehouses',{'code':'L'*100,'name':'A'*240,'description':'A'*1000})
        self.assertEqual(obj.status_code,201,obj.data)
        changed=self.patch('warehouses',obj.data['id'],{'name':'B'*240,'description':'B'*1000})
        self.assertEqual(changed.status_code,200,changed.data)
        event=AuditEvent.objects.get(entity_id=obj.data['id'],source_version=2)
        self.assertLessEqual(len(json.dumps(event.summary).encode()),4000)
        self.assertTrue(event.summary['outcome']['detail_stored'])
        full=AuditEventSerializer(event).data['summary']
        self.assertEqual(full['outcome']['before']['description'],'A'*1000)
        self.assertEqual(full['outcome']['after']['description'],'B'*1000)
        self.assertEqual(len(full['outcome']['authority']['roles']),20)
        history=self.client.get('/api/v1/inventory/history/',{'entity_id':obj.data['id']})
        self.assertEqual(history.status_code,200)
        self.assertEqual(history.data['results'][0]['summary'],full)
        self.client.force_authenticate(self.maker)
        self.assertEqual(self.client.get('/api/v1/inventory/history/').status_code,403)

    def test_ordinary_authorization_wording_is_valid_for_multirole_employee(self):
        for index in range(3):
            role=Role.objects.create(code=f'synthetic-normal-{index}',name='Synthetic role')
            Membership.objects.create(user=self.actor,role=role)
        result=self.client.post('/api/v1/inventory/warehouses/',{'code':'SYN-REASON','name':'Synthetic','reason':'Authorization reviewed for warehouse configuration.'},format='json',HTTP_IDEMPOTENCY_KEY='normal-reason')
        self.assertEqual(result.status_code,201,result.data)
        self.assertEqual(AuditEvent.objects.get(entity_id=result.data['id']).reason,'Authorization reviewed for warehouse configuration.')

    def test_nested_secret_fields_and_actual_credentials_are_redacted(self):
        token='eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.abcdefghijklmnopqrstuvwxyz012345'
        event=record_event(actor=self.actor,action='test.safe',entity_type='test',entity_id='synthetic',request_id=uuid.uuid4(),
            reason='Authorization reviewed. password=hunter2\nAuthorization: Bearer '+token,
            summary={'outcome':{'password':'hunter2','headers':{'Authorization':'Bearer '+token},'access_token':token,'description':'JWT '+token,'normal':'Authorization review approved'}})
        stored=json.dumps(event.summary)+event.reason+json.dumps(event.evidence.payload)
        self.assertNotIn(token,stored);self.assertNotIn('hunter2',stored)
        self.assertIn('Authorization review approved',stored)
        self.assertEqual(event.summary['outcome']['password'],'[REDACTED]')

    def test_full_evidence_is_bounded_and_immutable(self):
        with self.assertRaises(ValidationError):
            record_event(actor=self.actor,action='test',entity_type='test',entity_id='synthetic',request_id=uuid.uuid4(),summary={'outcome':'A'*(EVIDENCE_LIMIT+1)})
        self.assertFalse(AuditEvent.objects.exists())
        event=record_event(actor=self.actor,action='test',entity_type='test',entity_id='synthetic',request_id=uuid.uuid4(),summary={'outcome':'safe'})
        with self.assertRaises(DatabaseError),transaction.atomic():
            with transaction.get_connection().cursor() as c:c.execute('UPDATE core_auditevidence SET sha256=sha256 WHERE id=%s',[event.evidence.pk])
        with self.assertRaises(ValueError):event.evidence.delete()

    def test_evidence_failure_rolls_back_event_and_business_change(self):
        from apps.inventory.models import Warehouse
        with patch('apps.core.audit.AuditEvidence.save',side_effect=RuntimeError('Synthetic unavailable evidence store')):
            result=self.post('warehouses',{'code':'ROLLBACK-DETAIL','name':'Synthetic'})
        self.assertEqual(result.status_code,500)
        self.assertFalse(Warehouse.objects.filter(code='ROLLBACK-DETAIL').exists())
        self.assertFalse(AuditEvent.objects.exists());self.assertFalse(AuditEvidence.objects.exists())
