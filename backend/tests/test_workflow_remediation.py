import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from decimal import Decimal
from unittest.mock import patch
from django.test import TransactionTestCase
from django.db import connection,connections,transaction,DatabaseError
from django.utils import timezone
from apps.accounts.models import User
from apps.core.models import AuditEvent
from apps.core.api import CommandConflict
from apps.inventory.workflow_models import OperationRequest,OperationLine,PhysicalSourceDocument,PhysicalSourceLine
from apps.inventory.ledger_models import LedgerTransaction
from apps.inventory.ledger_guard import synthetic_write
from apps.inventory.workflows import submit_request,require_controlled_capture
from tests import test_operations

class WorkflowRemediationTests(TransactionTestCase):
 setUp=test_operations.OperationTests.setUp
 body=test_operations.OperationTests.body
 create=test_operations.OperationTests.create
 step=test_operations.OperationTests.step
 prepare=test_operations.OperationTests.prepare
 approve=test_operations.OperationTests.approve
 record=test_operations.OperationTests.record
 opening=test_operations.OperationTests.opening
 submit=test_operations.OperationTests.submit
 intent=test_operations.OperationTests.intent
 versions=test_operations.OperationTests.versions
 line=test_operations.OperationTests.line
 balance=test_operations.OperationTests.balance
 def api_create(self,body,key=None):
  return self.client.post('/api/v1/inventory/operations/',body,format='json',HTTP_IDEMPOTENCY_KEY=key or str(uuid.uuid4()))

 def test_quantity_raw_numeric_types_and_invalid_strings_rejected_before_coercion(self):
  for value in [1,1.5,0,-1,1e2,1e20,True,None,'1e2','1E+2','1.0000001','-1','-0',' 1','1 ','NaN','Infinity']:
   with self.subTest(quantity=value):
    body=self.body('OPENING');body['lines'][0]['quantity']=value
    response=self.api_create(body)
    self.assertEqual(response.status_code,400,response.data)
  self.assertFalse(OperationRequest.objects.exists())

 def test_valid_decimal_strings_zero_and_operation_specific_zero_rule(self):
  for value in ['0','0.000001','1','123.450000']:
   with self.subTest(quantity=value):
    response=self.api_create(self.body('OPENING',qty=value))
    self.assertEqual(response.status_code,201,response.data)
    self.assertEqual(Decimal(response.data['lines'][0]['quantity']),Decimal(value))
  response=self.api_create(self.body('IN',qty='0'))
  self.assertEqual(response.status_code,400)

 def blocked_stage(self,stage):
  self.opening('5');obj=self.create(self.body('OUT',qty='2',quality='RELEASED'))
  if stage in ['confirm','approve']:obj=self.step(obj,'verify')
  if stage=='approve':obj=self.step(obj,'confirm')
  self.submit(self.intent('OUT',[self.line('4',src=self.loc)]))
  before_events=AuditEvent.objects.filter(entity_id=obj['id']).count()
  self.client.force_authenticate(self.reviewer if stage=='approve' else self.maker)
  data={'reason':'Synthetic feasibility review','evidence_reference':'synthetic:physical'}
  if stage=='approve':data['recorder']=str(self.actor.pk)
  response=self.client.post(f'/api/v1/inventory/operations/{obj["id"]}/{stage}/',data,format='json',HTTP_IDEMPOTENCY_KEY='blocked-stage',HTTP_IF_MATCH='"'+str(obj['version'])+'"')
  self.assertEqual(response.status_code,409,response.data)
  self.assertEqual(response.data['error']['code'],'issue_unavailable')
  self.assertEqual(OperationRequest.objects.get(pk=obj['id']).status,obj['status'])
  self.assertEqual(AuditEvent.objects.filter(entity_id=obj['id']).count(),before_events)
  self.assertEqual(self.balance(),1)
 def test_verification_rechecks_live_eligible_stock(self):self.blocked_stage('verify')
 def test_confirmation_rechecks_live_eligible_stock(self):self.blocked_stage('confirm')
 def test_approval_rechecks_live_eligible_stock(self):self.blocked_stage('approve')

 def test_valid_confirmation_approval_are_evidence_only_without_reservation_or_posting(self):
  self.opening('5');obj=self.approve(self.prepare(self.create(self.body('OUT',qty='2',quality='RELEASED'))))
  self.assertFalse(obj['stock_movement_posted']);self.assertFalse(obj['physical_confirmation_is_posting'])
  self.assertEqual(self.balance(),5);self.assertEqual(LedgerTransaction.objects.count(),1)
  self.assertTrue(self.record(obj)['stock_movement_posted'])

 def test_current_count_cutoff_is_server_generated_and_custom_cutoffs_rejected(self):
  self.opening('5')
  for kind in ['COUNT','OPENING']:
   for cutoff in ['2000-01-01T00:00:00Z',timezone.now().isoformat(),'2999-01-01T00:00:00Z']:
    body=self.body(kind,qty='5',quality='RELEASED' if kind=='COUNT' else 'HELD');body['cutoff']=cutoff
    response=self.api_create(body);self.assertEqual(response.status_code,400,response.data)
    self.assertIn('cutoff',response.data['error']['fields'])
  before=timezone.now();obj=self.create(self.body('COUNT',qty='5',quality='RELEASED'));after=timezone.now()
  stored=OperationRequest.objects.get(pk=obj['id'])
  self.assertEqual(obj['cutoff_basis'],'CURRENT_LOCKED');self.assertLessEqual(before,stored.cutoff);self.assertLessEqual(stored.cutoff,after)
  with self.assertRaises(DatabaseError),synthetic_write():
   with connection.cursor() as c:c.execute("UPDATE inventory_operationrequest SET cutoff_basis='LEGACY_UNVERIFIED',version=version+1 WHERE id=%s",[stored.pk])

 def test_same_controlled_line_blocks_new_random_event_and_different_actor(self):
  body=self.body('IN');first=self.create(body)
  body['source_event']=str(uuid.uuid4());self.client.force_authenticate(self.reviewer)
  response=self.api_create(body)
  self.assertEqual(response.status_code,409,response.data);self.assertEqual(OperationRequest.objects.count(),1)
  self.assertEqual(OperationLine.objects.get(request_id=first['id']).source_line_id,uuid.UUID(body['lines'][0]['source_line']))

 def test_repeated_deliveries_same_document_are_allowed_with_distinct_occurrences(self):
  first=self.body('IN');second=self.body('IN')
  self.assertEqual(first['source_reference'],second['source_reference'])
  self.create(first);self.create(second)
  self.assertEqual(OperationRequest.objects.count(),2)
  self.assertEqual(PhysicalSourceDocument.objects.filter(kind='RECEIPT').count(),1)
  line=PhysicalSourceLine.objects.get(pk=first['lines'][0]['source_line'])
  with self.assertRaises(DatabaseError),synthetic_write():
   PhysicalSourceLine.objects.create(document=line.document,occurrence_reference=line.occurrence_reference,line_reference=line.line_reference,stock=line.stock,location=line.location,unit=line.unit,quantity=line.quantity)

 def test_count_line_duplicate_claim_and_missing_or_mismatched_registration_rejected(self):
  self.opening('5');body=self.body('COUNT',qty='5',quality='RELEASED');self.create(body)
  body['source_event']=str(uuid.uuid4());self.assertEqual(self.api_create(body).status_code,409)
  for mutation in ['missing','quantity','location','document']:
   body=self.body('IN')
   if mutation=='missing':body['lines'][0].pop('source_line')
   if mutation=='quantity':body['lines'][0]['quantity']='3'
   if mutation=='location':body['lines'][0]['location']=str(self.loc2.pk)
   if mutation=='document':body['source_reference']='synthetic:other-document'
   self.assertEqual(self.api_create(body).status_code,400)

 def test_source_registry_is_append_only_and_service_context_required(self):
  body=self.body('IN');line=PhysicalSourceLine.objects.get(pk=body['lines'][0]['source_line'])
  for table,pk in [('physicalsourcedocument',line.document_id),('physicalsourceline',line.pk)]:
   with self.assertRaises(DatabaseError),synthetic_write():
    with connection.cursor() as c:c.execute(f'UPDATE inventory_{table} SET id=id WHERE id=%s',[pk])
  with self.assertRaises(DatabaseError),transaction.atomic():
   PhysicalSourceDocument.objects.create(namespace='synthetic:no-service',reference='blocked',kind='RECEIPT',warehouse=self.wh,evidence_reference='synthetic:e',registered_by=self.actor)

 def test_duplicate_source_claim_is_concurrency_safe(self):
  body=self.body('IN');barrier=Barrier(2)
  def run():
   connections.close_all()
   try:
    actor=User.objects.get(pk=self.actor.pk);payload={**body,'source_event':str(uuid.uuid4())};barrier.wait(timeout=10)
    try:submit_request(actor=actor,data=payload,key=str(uuid.uuid4()),request_id=uuid.uuid4());return 'created'
    except CommandConflict:return 'blocked'
   finally:connections.close_all()
  with ThreadPoolExecutor(max_workers=2) as pool:
   futures=[pool.submit(run),pool.submit(run)];results=[f.result(timeout=30) for f in futures]
  self.assertEqual(sorted(results),['blocked','created'])
  self.assertEqual(OperationRequest.objects.count(),1)

 def test_failed_audit_does_not_consume_physical_source_line(self):
  body=self.body('IN')
  with patch('apps.core.commands.record_event',side_effect=RuntimeError('Synthetic audit failure')):
   with self.assertRaises(RuntimeError):self.create(body)
  self.assertFalse(OperationLine.objects.filter(source_line_id=body['lines'][0]['source_line']).exists())
  self.assertEqual(self.api_create(body).status_code,201)

 def test_legacy_count_basis_is_not_silently_treated_as_current(self):
  from rest_framework.exceptions import ValidationError
  obj=self.create(self.body('OPENING'))
  stored=OperationRequest.objects.get(pk=obj['id']);stored.cutoff_basis='LEGACY_UNVERIFIED'
  with self.assertRaises(ValidationError):require_controlled_capture(stored)
