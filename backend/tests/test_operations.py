import uuid
from datetime import timedelta
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
from django.conf import settings
from django.test import TransactionTestCase,override_settings
from django.db import transaction,connection,connections,DatabaseError
from django.contrib.auth.models import Permission
from django.utils import timezone
from rest_framework.exceptions import ValidationError,PermissionDenied
from apps.accounts.models import Employee,User
from apps.inventory.models import WarehouseScope
from apps.inventory.workflow_models import OperationRequest,OperationLine,OperationDecision,PhysicalSourceDocument,PhysicalSourceLine
from apps.inventory.workflows import submit_request,transition_request,build_intent
from apps.inventory.ledger_guard import synthetic_write
from apps.inventory.ledger_models import LedgerTransaction,LedgerEntry,BalanceProjection,OpeningCoverage
from apps.core.models import AuditEvent,IdempotencyRecord
from apps.core.api import CommandConflict,VersionConflict
from tests import test_ledger

class WorkflowGateTests(TransactionTestCase):
 def test_default_disabled_services_api_and_database(self):
  from rest_framework.test import APIClient
  actor=User.objects.create_user('gate@example.test','password')
  client=APIClient();client.force_authenticate(actor)
  with override_settings(SYNTHETIC_LEDGER_ENABLED=False):
   self.assertFalse(client.get('/api/v1/inventory/operations/mode/').data['synthetic_enabled'])
   self.assertEqual(client.get('/api/v1/inventory/operations/').status_code,403)
   self.assertEqual(client.post('/api/v1/inventory/operations/',{},format='json').status_code,403)
   with self.assertRaises(PermissionDenied):submit_request(actor=actor,data={},key='blocked',request_id=uuid.uuid4())
   with self.assertRaises(PermissionDenied):transition_request(actor=actor,pk=uuid.uuid4(),action='record',data={},version=1,key='blocked',request_id=uuid.uuid4())

class OperationTests(TransactionTestCase):
 def setUp(self):
  test_ledger.SyntheticLedgerTests.setUp(self)
  Employee.objects.create(user=self.maker,department=self.department,employee_id='SYN-STORES',designation='Synthetic Stores',created_by=self.actor,updated_by=self.actor)
  self.maker.user_permissions.add(*Permission.objects.filter(content_type__app_label='inventory'))
  WarehouseScope.objects.create(user=self.maker,company_wide=True,requested_by=self.actor,approved_by=self.reviewer,policy_reference='synthetic:stores',evidence_reference='synthetic:scope',expires_at=timezone.now()+timedelta(hours=1))
 opening=test_ledger.SyntheticLedgerTests.opening
 submit=test_ledger.SyntheticLedgerTests.submit
 intent=test_ledger.SyntheticLedgerTests.intent
 versions=test_ledger.SyntheticLedgerTests.versions
 line=test_ledger.SyntheticLedgerTests.line
 balance=test_ledger.SyntheticLedgerTests.balance
 def body(self,kind,qty='2',quality='HELD',**extra):
  body={'kind':kind,'warehouse':str(self.wh.pk),'source_system':'synthetic:operation','source_event':str(uuid.uuid4()),'source_reference':'synthetic:delivery-document','evidence_reference':'synthetic:physical-evidence','counterparty_reference':'synthetic:physical-destination','reason':'Synthetic Authorization evidence.','policy':str(self.policy.pk),'lines':[{'stock':str(self.stock.pk),'unit':str(self.unit.pk),'location':str(self.loc.pk),'quantity':qty,'quality':quality}],**extra}
  if kind not in ['COUNT','OPENING']:body['cutoff']=timezone.now().isoformat()
  if kind in ['IN','COUNT','OPENING']:
   body['source_reference']='synthetic:'+('receipt' if kind=='IN' else 'count')+'-document'
   try:registered_quantity=Decimal(qty) if isinstance(qty,str) else Decimal('2')
   except Exception:registered_quantity=Decimal('2')
   if not registered_quantity.is_finite() or registered_quantity<0 or registered_quantity>=Decimal('100000000000000'):registered_quantity=Decimal('2')
   with synthetic_write():
    document,_=PhysicalSourceDocument.objects.get_or_create(namespace=body['source_system'],reference=body['source_reference'],defaults={'kind':'RECEIPT' if kind=='IN' else 'COUNT','warehouse':self.wh,'evidence_reference':'synthetic:registered-source','registered_by':self.reviewer})
    physical=PhysicalSourceLine.objects.create(document=document,occurrence_reference=body['source_event'],line_reference='1',stock=self.stock,location=self.loc,unit=self.unit,quantity=registered_quantity)
   body['lines'][0]['source_line']=str(physical.pk)
  return body
 def create(self,body,key=None):return submit_request(actor=self.actor,data=body,key=key or str(uuid.uuid4()),request_id=uuid.uuid4())[0]
 def step(self,obj,action,actor=None,**extra):
  return transition_request(actor=actor or self.maker,pk=obj['id'],action=action,data={'reason':'Synthetic '+action+' evidence','evidence_reference':'synthetic:'+action,**extra},version=obj['version'],key=str(uuid.uuid4()),request_id=uuid.uuid4())[0]
 def prepare(self,obj):
  obj=self.step(obj,'verify')
  if obj['kind'] in ['OPENING_CORRECTION','ADJUSTMENT']:obj=self.step(obj,'investigate')
  return self.step(obj,'confirm')
 def approve(self,obj):return self.step(obj,'approve',self.reviewer,recorder=str(self.actor.pk))
 def record(self,obj):return self.step(obj,'record',self.actor)

 def test_receipt_stages_do_not_release_or_post_until_recorded(self):
  self.opening('0',quality='HELD')
  obj=self.create(self.body('IN'));self.assertEqual(self.balance(quality='HELD'),0)
  obj=self.prepare(obj);self.assertEqual(obj['status'],'CONFIRMED');self.assertEqual(LedgerTransaction.objects.count(),1)
  obj=self.approve(obj);self.assertEqual(obj['status'],'APPROVED');obj=self.record(obj)
  self.assertEqual(obj['status'],'POSTED');self.assertEqual(self.balance(quality='HELD'),Decimal('2'));self.assertEqual(self.balance(),0)
  self.assertEqual(obj['recording_employee'],str(self.actor.pk));self.assertEqual(len(obj['decisions']),5)

 def test_receipt_unit_identity_and_no_automatic_qc_acceptance(self):
  body=self.body('IN',quality='RELEASED')
  with self.assertRaises(ValidationError):self.create(body)
  body=self.body('IN');body['lines'][0]['unit']=str(uuid.uuid4())
  with self.assertRaises(ValidationError):self.create(body)
  body=self.body('IN',qty='1.0000001')
  with self.assertRaises(ValidationError):self.create(body)

 def test_out_available_unknown_and_held(self):
  with self.assertRaises(ValidationError):self.create(self.body('OUT',quality='RELEASED'))
  self.opening('5',quality='HELD')
  with self.assertRaises(ValidationError):self.create(self.body('OUT',quality='HELD'))
  with self.assertRaises(ValidationError):self.create(self.body('OUT',quality='RELEASED'))

 def test_out_physical_confirmation_and_available_recheck(self):
  self.opening('5')
  obj=self.create(self.body('OUT',quality='RELEASED'));self.assertEqual(self.balance(),Decimal('5'))
  verified=self.step(obj,'verify')
  with self.assertRaises(ValidationError):self.approve(verified)
  obj=self.approve(self.step(verified,'confirm'))
  self.submit(self.intent('OUT',[self.line('4',src=self.loc)]))
  with self.assertRaises((ValidationError,VersionConflict)):self.record(obj)
  self.assertEqual(OperationRequest.objects.get(pk=obj['id']).status,'APPROVED');self.assertEqual(self.balance(),Decimal('1'))

 def test_opening_count_zero_unknown_and_immutable_original(self):
  obj=self.create(self.body('OPENING',qty='0'));self.assertFalse(OpeningCoverage.objects.exists())
  obj=self.record(self.approve(self.prepare(obj)));self.assertEqual(obj['status'],'POSTED')
  self.assertEqual(OpeningCoverage.objects.get().opening_quantity,0)
  with self.assertRaises(ValidationError):self.create(self.body('OPENING'))
  with self.assertRaises(DatabaseError),synthetic_write():
   with connection.cursor() as c:c.execute('UPDATE inventory_openingcoverage SET opening_quantity=5')

 def test_admin_correction_initiation_independent_post_and_history(self):
  opening=self.opening('10')
  obj=self.create(self.body('OPENING_CORRECTION',qty='12',quality='RELEASED',related=opening['id']))
  self.assertEqual(Decimal(obj['lines'][0]['baseline']),10);self.assertEqual(Decimal(obj['lines'][0]['difference']),2)
  obj=self.prepare(obj)
  with self.assertRaises(PermissionDenied):self.step(obj,'approve',self.actor,recorder=str(self.actor.pk))
  obj=self.record(self.approve(obj))
  self.assertEqual(OpeningCoverage.objects.get().opening_quantity,Decimal('10'));self.assertEqual(LedgerEntry.objects.get(transaction_id=opening['id']).delta,10)
  self.assertEqual(self.balance(quality='HELD'),Decimal('2'));self.assertEqual(obj['related'],opening['id'])
  next_request=self.create(self.body('OPENING_CORRECTION',qty='13',quality='RELEASED',related=opening['id']))
  self.assertEqual(Decimal(next_request['lines'][0]['baseline']),12)
  self.assertEqual(Decimal(next_request['lines'][0]['original_quantity']),10)
  events=AuditEvent.objects.filter(entity_type='inventory.operationrequest',entity_id=obj['id'])
  self.assertEqual(events.count(),6);self.assertTrue(all(e.evidence.payload for e in events))

 def test_correction_after_issue_cannot_create_negative_stock(self):
  opened=self.opening('10');self.submit(self.intent('OUT',[self.line('9',src=self.loc)]))
  obj=self.prepare(self.create(self.body('OPENING_CORRECTION',qty='5',quality='RELEASED',related=opened['id'])))
  obj=self.approve(obj)
  with self.assertRaises(ValidationError):self.record(obj)
  self.assertEqual(self.balance(),1)

 def test_held_opening_removal_capture_but_policy_gate_blocks_approval(self):
  opened=self.opening('10',quality='HELD')
  obj=self.prepare(self.create(self.body('OPENING_CORRECTION',qty='5',related=opened['id'])))
  with self.assertRaises(ValidationError):self.approve(obj)
  self.assertEqual(OperationRequest.objects.get(pk=obj['id']).status,'CONFIRMED')

 def test_no_policy_allows_capture_but_not_approval(self):
  body=self.body('OPENING');body.pop('policy')
  obj=self.prepare(self.create(body))
  with self.assertRaises(ValidationError):self.approve(obj)
  self.assertFalse(LedgerTransaction.objects.exists())

 def test_transfer_conservation_preserves_hold_and_registration(self):
  self.opening('8',quality='HELD');self.opening('0',loc=self.loc2,quality='HELD')
  body=self.body('TRANSFER',qty='3');body['lines'][0]['destination']=str(self.loc2.pk)
  obj=self.record(self.approve(self.prepare(self.create(body))))
  self.assertEqual(self.balance(quality='HELD'),5);self.assertEqual(self.balance(self.loc2,quality='HELD'),3)
  self.stock.refresh_from_db();self.assertEqual(self.stock.warehouse_id,self.wh.pk)
  self.assertEqual(LedgerEntry.objects.filter(transaction_id=obj['ledger_transaction']).aggregate(value=__import__('django.db.models',fromlist=['Sum']).Sum('delta'))['value'],0)

 def test_return_original_out_limit_and_hold(self):
  self.opening('8');out=self.submit(self.intent('OUT',[self.line('4',src=self.loc)]))[0]
  original=LedgerTransaction.objects.get(pk=out['id']).lines.get()
  body=self.body('RETURN',qty='3',related=out['id']);body['lines'][0]['original_line']=str(original.pk)
  obj=self.record(self.approve(self.prepare(self.create(body))))
  self.assertEqual(self.balance(quality='HELD'),3);self.assertEqual(obj['status'],'POSTED')
  body['source_event']=str(uuid.uuid4());body['lines'][0]['quantity']='2'
  with self.assertRaises(ValidationError):self.create(body)

 def test_count_variance_investigation_adjustment_and_stale_snapshot(self):
  self.opening('8')
  count=self.create(self.body('COUNT',qty='6',quality='RELEASED'))
  self.assertEqual(Decimal(count['lines'][0]['difference']),-2)
  with self.assertRaises(ValidationError):self.create(self.body('ADJUSTMENT',qty='6',quality='RELEASED',count_session=count['id']))
  count=self.step(self.step(count,'verify'),'investigate')
  adjustment=self.create(self.body('ADJUSTMENT',qty='6',quality='RELEASED',count_session=count['id']))
  adjustment=self.record(self.approve(self.prepare(adjustment)))
  self.assertEqual(self.balance(),6);self.assertEqual(adjustment['status'],'POSTED')
  with self.assertRaises(ValidationError):self.create(self.body('ADJUSTMENT',qty='6',quality='RELEASED',count_session=count['id']))

 def test_independent_stores_and_recorder_and_rejection_history(self):
  obj=self.create(self.body('OPENING'))
  with self.assertRaises(PermissionDenied):self.step(obj,'verify',self.actor)
  confirmed=self.prepare(obj)
  with self.assertRaises(PermissionDenied):self.step(confirmed,'approve',self.reviewer,recorder=str(self.maker.pk))
  rejected=self.step(confirmed,'reject',self.reviewer)
  self.assertEqual(rejected['status'],'REJECTED');self.assertFalse(LedgerTransaction.objects.exists())
  with self.assertRaises(ValidationError):self.step(rejected,'confirm')

 def test_atomic_audit_failure_and_no_duplicate_requests(self):
  body=self.body('OPENING')
  before=IdempotencyRecord.objects.count()
  with patch('apps.core.commands.record_event',side_effect=RuntimeError('Synthetic failure')):
   with self.assertRaises(RuntimeError):self.create(body,key='auditfail')
  self.assertFalse(OperationRequest.objects.exists());self.assertFalse(OperationDecision.objects.exists());self.assertEqual(before,IdempotencyRecord.objects.count())
  first=self.create(body,key='same');again=self.create(body,key='same');self.assertEqual(first,again)
  with self.assertRaises(CommandConflict):self.create(body,key='other')

 def test_posting_audit_failure_rolls_back_nested_ledger_and_workflow(self):
  obj=self.approve(self.prepare(self.create(self.body('OPENING'))))
  from apps.core.audit import record_event
  def fail_workflow(**kwargs):
   if kwargs['entity_type']=='inventory.operationrequest':raise RuntimeError('Synthetic workflow audit failure')
   return record_event(**kwargs)
  with patch('apps.core.commands.record_event',side_effect=fail_workflow):
   with self.assertRaises(RuntimeError):self.record(obj)
  self.assertFalse(LedgerTransaction.objects.exists());self.assertEqual(OperationRequest.objects.get(pk=obj['id']).status,'APPROVED')

 def test_concurrent_duplicate_requests_have_one_winner(self):
  body=self.body('OPENING');barrier=Barrier(2)
  def run():
   connections.close_all()
   try:
    actor=User.objects.get(pk=self.actor.pk);barrier.wait(timeout=10)
    try:submit_request(actor=actor,data=body,key=str(uuid.uuid4()),request_id=uuid.uuid4());return 'created'
    except CommandConflict:return 'blocked'
   finally:connections.close_all()
  with ThreadPoolExecutor(max_workers=2) as pool:
   results=[f.result(timeout=30) for f in [pool.submit(run),pool.submit(run)]]
  self.assertEqual(sorted(results),['blocked','created']);self.assertEqual(OperationRequest.objects.count(),1)

 def test_api_contract_scope_history_headers_and_disabled_record(self):
  self.assertTrue(self.client.get('/api/v1/inventory/operations/mode/').data['synthetic_enabled'])
  response=self.client.post('/api/v1/inventory/operations/',self.body('OPENING'),format='json',HTTP_IDEMPOTENCY_KEY='api-create')
  self.assertEqual(response.status_code,201,response.data);pk=response.data['id']
  self.assertEqual(self.client.get('/api/v1/inventory/operations/').data['count'],1)
  self.assertEqual(self.client.get(f'/api/v1/inventory/operations/{pk}/history/').data['count'],1)
  response=self.client.post(f'/api/v1/inventory/operations/{pk}/record/',{'reason':'Synthetic','evidence_reference':'synthetic:e'},format='json',HTTP_IDEMPOTENCY_KEY='record',HTTP_IF_MATCH='"1"')
  self.assertEqual(response.status_code,403)
  self.actor.user_permissions.clear()
  self.assertEqual(self.client.get('/api/v1/inventory/operations/').status_code,403)

 def test_crosswarehouse_scope_isolation(self):
  self.opening('3',quality='HELD');self.opening('0',loc=self.loc2,quality='HELD')
  body=self.body('TRANSFER');body['lines'][0]['destination']=str(self.loc2.pk)
  self.create(body)
  # Scope rows are immutable; a separate user receives only destination synthetic scope.
  outsider=User.objects.create_user('dest-workflow@example.test','password')
  Employee.objects.create(user=outsider,department=self.department,employee_id='SYN-DEST-W',designation='Synthetic destination',created_by=self.actor,updated_by=self.actor)
  outsider.user_permissions.add(*Permission.objects.filter(content_type__app_label='inventory'))
  WarehouseScope.objects.create(user=outsider,warehouse=self.wh2,requested_by=self.actor,approved_by=self.reviewer,policy_reference='synthetic:dest',evidence_reference='synthetic:e',expires_at=timezone.now()+timedelta(hours=1))
  self.client.force_authenticate(outsider)
  self.assertEqual(self.client.get('/api/v1/inventory/operations/').data['count'],0)

 def test_database_sealed_evidence_and_audit_guards(self):
  obj=self.create(self.body('OPENING'));line=OperationLine.objects.get()
  with self.assertRaises(ValueError):OperationLine.objects.filter(pk=line.pk).update(quantity=5)
  for statement in ['UPDATE inventory_operationline SET quantity=5','DELETE FROM inventory_operationdecision','UPDATE inventory_operationrequest SET reason=\'changed\'','DELETE FROM inventory_operationrequest']:
   with self.assertRaises(DatabaseError),synthetic_write():
    with connection.cursor() as c:c.execute(statement)
  with self.assertRaises(DatabaseError),synthetic_write():
   OperationLine.objects.create(request_id=obj['id'],stock=self.stock,unit=self.unit,location=self.loc2,quantity=1,quality='HELD')
  with self.assertRaises(DatabaseError),synthetic_write():
   OperationDecision.objects.create(request_id=obj['id'],version=999,actor=self.actor,action='forged',from_status='SUBMITTED',to_status='SUBMITTED',reason='Synthetic late forged evidence',evidence_reference='synthetic:e')
  with self.assertRaises(DatabaseError),transaction.atomic():
   with connection.cursor() as c:c.execute('UPDATE inventory_operationrequest SET version=version+1')

 def test_concurrent_workflow_records_cannot_double_issue(self):
  self.opening('10')
  requests=[self.approve(self.prepare(self.create(self.body('OUT',qty='7',quality='RELEASED')))) for _ in range(2)]
  barrier=Barrier(2)
  def run(obj):
   connections.close_all()
   try:
    actor=User.objects.get(pk=self.actor.pk);barrier.wait(timeout=10)
    try:
     transition_request(actor=actor,pk=obj['id'],action='record',data={'reason':'Synthetic concurrency','evidence_reference':'synthetic:issue'},version=obj['version'],key=str(uuid.uuid4()),request_id=uuid.uuid4())
     return 'posted'
    except (ValidationError,VersionConflict,CommandConflict):return 'blocked'
   finally:connections.close_all()
  with ThreadPoolExecutor(max_workers=2) as pool:
   futures=[pool.submit(run,obj) for obj in requests];results=[f.result(timeout=30) for f in futures]
  self.assertEqual(sorted(results),['blocked','posted']);self.assertEqual(self.balance(),3)
  self.assertEqual(OperationRequest.objects.filter(status='POSTED').count(),1)

 def test_correction_permission_not_admin_title_and_api_transition_retry(self):
  opened=self.opening()
  self.actor.is_staff=True;self.actor.save(update_fields=['is_staff'])
  permission=Permission.objects.get(content_type__app_label='inventory',codename='request_opening_correction')
  self.actor.user_permissions.remove(permission)
  with self.assertRaises(PermissionDenied):self.create(self.body('OPENING_CORRECTION',qty='12',quality='RELEASED',related=opened['id']))
  self.actor.user_permissions.add(permission)
  obj=self.create(self.body('OPENING_CORRECTION',qty='12',quality='RELEASED',related=opened['id']))
  self.client.force_authenticate(self.maker)
  body={'reason':'Synthetic Stores independent verification','evidence_reference':'synthetic:stores'}
  url=f'/api/v1/inventory/operations/{obj["id"]}/verify/'
  first=self.client.post(url,body,format='json',HTTP_IDEMPOTENCY_KEY='verify-retry',HTTP_IF_MATCH='"1"')
  again=self.client.post(url,body,format='json',HTTP_IDEMPOTENCY_KEY='verify-retry',HTTP_IF_MATCH='"1"')
  self.assertEqual(first.status_code,200,first.data);self.assertEqual(first.data,again.data)
  self.assertEqual(OperationDecision.objects.filter(request_id=obj['id'],action='verify').count(),1)

 def test_receipt_unknown_opening_capture_not_false_posting_and_missing_evidence(self):
  body=self.body('IN');body.pop('evidence_reference')
  with self.assertRaises(ValidationError):self.create(body)
  obj=self.approve(self.prepare(self.create(self.body('IN'))))
  with self.assertRaises(ValidationError):self.record(obj)
  self.assertFalse(LedgerTransaction.objects.exists());self.assertEqual(OperationRequest.objects.get(pk=obj['id']).status,'APPROVED')

 def test_positive_reconciliation_cannot_reuse_count_to_mint_held_stock(self):
  self.opening('8')
  count=self.step(self.step(self.create(self.body('COUNT',qty='10',quality='RELEASED')),'verify'),'investigate')
  body=self.body('ADJUSTMENT',qty='10',quality='RELEASED',count_session=count['id'])
  obj=self.record(self.approve(self.prepare(self.create(body))))
  self.assertEqual(self.balance(),8);self.assertEqual(self.balance(quality='HELD'),2)
  body['source_event']=str(uuid.uuid4())
  with self.assertRaises(ValidationError):self.create(body)
  self.assertEqual(OperationRequest.objects.filter(count_session_id=count['id'],status='POSTED').count(),1)
