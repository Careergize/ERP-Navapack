import uuid
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
from django.test import TransactionTestCase, override_settings
from django.db import connection, connections, DatabaseError
from django.contrib.auth.models import Permission
from rest_framework.test import APIClient
from rest_framework.exceptions import ValidationError, PermissionDenied
from apps.core.api import CommandConflict, VersionConflict
from apps.core.models import AuditEvent
from apps.inventory.quality import command, snapshot
from apps.inventory.quality_models import *
from apps.inventory.ledger_models import LedgerEntry, LedgerTransaction, BalanceProjection
from apps.inventory.ledger import rebuild_projection
from apps.inventory.ledger_guard import synthetic_write
from tests import test_ledger


class QualityGateTests(TransactionTestCase):
    def test_default_disabled_api_and_services(self):
        from apps.accounts.models import User
        actor = User.objects.create_user('qc-gate@example.test', 'password')
        client = APIClient(); client.force_authenticate(actor)
        with override_settings(SYNTHETIC_LEDGER_ENABLED=False):
            self.assertFalse(client.get('/api/v1/inventory/quality/mode/').data['synthetic_enabled'])
            self.assertEqual(client.get('/api/v1/inventory/quality/inspections/').status_code,403)
            self.assertEqual(client.post('/api/v1/inventory/quality/inspections/',{},format='json').status_code,403)
            with self.assertRaises(PermissionDenied): command(actor=actor,action='release',data={},key='x',request_id=uuid.uuid4())


class QualityTests(TransactionTestCase):
    def setUp(self):
        test_ledger.SyntheticLedgerTests.setUp(self)
        self.plan = self.run_qc('plan',reference='synthetic:incoming',revision=1,applicability='INCOMING',material=str(self.material.pk),
            criteria=[{'id':'identity','type':'BOOLEAN','expected':True,'reference':'synthetic:requirement-v1'}],
            specification_reference='synthetic:spec-v1',sampling_reference='synthetic:approved-sampling-v1')
        self.run_qc('publish',pk=self.plan['id'],actor=self.reviewer,decision='APPROVED')
    line = test_ledger.SyntheticLedgerTests.line
    intent = test_ledger.SyntheticLedgerTests.intent
    versions = test_ledger.SyntheticLedgerTests.versions
    opening = test_ledger.SyntheticLedgerTests.opening
    balance = test_ledger.SyntheticLedgerTests.balance
    submit = test_ledger.SyntheticLedgerTests.submit
    approve = test_ledger.SyntheticLedgerTests.approve
    def run_qc(self,action,pk=None,actor=None,version=1,key=None,**data):
        return command(actor=actor or self.actor,action=action,pk=pk,version=version,
            data={'reason':'Synthetic Authorization for quality evidence.','evidence_reference':'synthetic:evidence',**data},
            key=key or str(uuid.uuid4()),request_id=uuid.uuid4())[0]
    def inspect(self,quantity='10',source=None,**extra):
        if source is None:
            self.opening(quantity,quality='HELD')
            source=LedgerEntry.objects.get(stock=self.stock)
        held=BalanceProjection.objects.get(stock=self.stock,location=source.location,quality='HELD')
        return self.run_qc('inspect',plan=self.plan['id'],source_entry=str(source.pk),quantity=quantity,balance_version=held.version,
            physical_evidence='synthetic:whole-marked-container',observations={'identity':True},**extra)
    def accepted(self):
        inspected=self.inspect()
        self.run_qc('review',pk=inspected['id'],actor=self.reviewer,decision='ACCEPT')
        return inspected
    def release(self,inspected,actor=None,**data):
        return self.run_qc('release',pk=inspected['id'],actor=actor or self.reviewer,policy=str(self.policy.pk),policy_version=1,**data)

    def test_held_inspection_acceptance_is_not_release(self):
        inspected=self.accepted()
        self.assertEqual(self.balance(quality='HELD'),10);self.assertEqual(self.balance(),0)
        state=snapshot(Inspection.objects.get(pk=inspected['id']))
        self.assertEqual(Decimal(state['accepted_quantity']),10);self.assertFalse(state['stock_released'])
        with self.assertRaises(ValidationError): self.submit(self.intent('OUT',[self.line('1',src=self.loc)]))

    def test_release_conservation_projection_rebuild_and_audit(self):
        inspected=self.accepted();result=self.release(inspected)
        self.assertTrue(result['stock_released']);self.assertEqual(self.balance(),10);self.assertEqual(self.balance(quality='HELD'),0)
        entries=LedgerEntry.objects.filter(transaction_id=result['ledger_transaction'])
        self.assertEqual(entries.count(),2);self.assertEqual(sum(e.delta for e in entries),0)
        event=AuditEvent.objects.get(entity_id=result['id']);self.assertEqual(event.actor_id,self.reviewer.pk)
        self.assertEqual(event.evidence.payload['summary']['outcome']['before']['inspector'],str(self.actor.pk))
        rebuild_projection(actor=self.actor,key='rebuild-qc',request_id=uuid.uuid4());self.assertEqual(self.balance(),10)
        self.submit(self.intent('OUT',[self.line('2',src=self.loc)]));self.assertEqual(self.balance(),8)

    def test_plan_missing_criteria_and_independent_publication(self):
        with self.assertRaises(PermissionDenied): self.run_qc('publish',pk=self.plan['id'],decision='APPROVED')
        with self.assertRaises(ValidationError): self.run_qc('plan',reference='synthetic:missing',revision=1,applicability='INCOMING',material=str(self.material.pk),criteria=[],specification_reference='x',sampling_reference='x')

    def test_no_self_review_or_release_even_admin(self):
        inspected=self.inspect()
        self.actor.is_superuser=True;self.actor.save(update_fields=['is_superuser'])
        with self.assertRaises(PermissionDenied): self.run_qc('review',pk=inspected['id'],decision='ACCEPT')
        self.run_qc('review',pk=inspected['id'],actor=self.reviewer,decision='ACCEPT')
        with self.assertRaises(PermissionDenied): self.release(inspected,actor=self.actor)

    def test_failed_criteria_cannot_accept(self):
        self.opening('10',quality='HELD');source=LedgerEntry.objects.get(stock=self.stock)
        held=BalanceProjection.objects.get(stock=self.stock)
        inspected=self.run_qc('inspect',plan=self.plan['id'],source_entry=str(source.pk),quantity='10',balance_version=held.version,physical_evidence='synthetic:mark',observations={'identity':False})
        with self.assertRaises(ValidationError): self.run_qc('review',pk=inspected['id'],actor=self.reviewer,decision='ACCEPT')

    def test_partial_indistinguishable_scope_rejected(self):
        self.opening('100',quality='HELD');source=LedgerEntry.objects.get(stock=self.stock)
        with self.assertRaises(ValidationError): self.inspect('70',source)
        self.assertEqual(self.balance(quality='HELD'),100);self.assertFalse(Inspection.objects.exists())

    def test_rejected_and_pending_remain_held(self):
        inspected=self.inspect();self.run_qc('review',pk=inspected['id'],actor=self.reviewer,decision='REJECT')
        self.assertTrue(QualityHold.objects.exists())
        client=APIClient();client.force_authenticate(self.actor)
        events=client.get(f"/api/v1/inventory/quality/inspections/{inspected['id']}/history/").data['results']
        self.assertIn('inventory.qc_contain',[event['action'] for event in events])
        with self.assertRaises(ValidationError):self.release(inspected)
        self.assertEqual(self.balance(quality='HELD'),10)
        source=LedgerEntry.objects.get(stock=self.stock)
        again=self.inspect('10',source,previous=inspected['id'])
        self.run_qc('review',pk=again['id'],actor=self.reviewer,decision='PENDING')
        state=snapshot(Inspection.objects.get(pk=again['id']))
        self.assertEqual(Decimal(state['pending_quantity']),10)

    def test_duplicate_release_and_retry(self):
        inspected=self.accepted()
        data={'reason':'Synthetic release','evidence_reference':'synthetic:evidence','policy':str(self.policy.pk),'policy_version':1}
        args=dict(actor=self.reviewer,action='release',pk=inspected['id'],version=1,data=data,key='same-release',request_id=uuid.uuid4())
        first=command(**args);second=command(**args)
        self.assertEqual(first[:2],second[:2]);self.assertTrue(second[2])
        with self.assertRaises((ValidationError,CommandConflict,VersionConflict)):self.release(inspected)
        self.assertEqual(QualityPosting.objects.count(),1)

    def test_concurrent_release_only_once(self):
        inspected=self.accepted();barrier=Barrier(2)
        def attempt(_):
            connections.close_all()
            try:
                barrier.wait(timeout=10)
                self.release(inspected);return 'posted'
            except (ValidationError,CommandConflict,VersionConflict):return 'blocked'
            finally:connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(attempt,range(2)))
        self.assertEqual(sorted(results),['blocked','posted']);self.assertEqual(self.balance(),10)

    def test_hold_reblocks_released_stock_and_no_generic_reversal(self):
        inspected=self.accepted();released=self.release(inspected)
        self.run_qc('hold',stock=str(self.stock.pk),location=str(self.loc.pk),policy=str(self.policy.pk),policy_version=1)
        self.assertEqual(self.balance(),0);self.assertEqual(self.balance(quality='HELD'),10)
        with self.assertRaises(ValidationError):self.submit(self.intent('TRANSFER',[self.line('1',quality='HELD',src=self.loc,dst=self.loc2)]))
        original=LedgerTransaction.objects.get(pk=released['ledger_transaction'])
        from apps.inventory.ledger import reversal_shape
        with self.assertRaises(ValidationError):self.submit(self.approve(self.intent('REVERSAL',reversal_shape(original),reverses=str(original.pk))))

    def test_new_hold_blocks_existing_accepted_inspection(self):
        inspected=self.accepted()
        self.run_qc('hold',stock=str(self.stock.pk),location=str(self.loc.pk))
        with self.assertRaises(ValidationError):self.release(inspected)

    def test_transfer_default_hold_preservation_and_stale_inspection(self):
        inspected=self.accepted()
        self.opening('0',loc=self.loc2,quality='HELD')
        self.submit(self.intent('TRANSFER',[self.line('2',quality='HELD',src=self.loc,dst=self.loc2)]))
        self.assertEqual(self.balance(self.loc2,quality='HELD'),2)
        with self.assertRaises(ValidationError):self.release(inspected)

    def test_new_plan_revision_stales_prior_inspection(self):
        inspected=self.accepted()
        body={k:self.plan[k] for k in ['reference','applicability','material','criteria','specification_reference','sampling_reference']};body['revision']=2
        newer=self.run_qc('plan',**body);self.run_qc('publish',pk=newer['id'],actor=self.reviewer,decision='APPROVED')
        with self.assertRaises(ValidationError):self.release(inspected)

    def test_audit_failure_rolls_back_qc_and_ledger(self):
        inspected=self.accepted();count=LedgerTransaction.objects.count()
        import apps.core.commands as commands
        real=commands.record_event
        def failing(**kwargs):
            if kwargs['action']=='inventory.qc_release':raise RuntimeError('Synthetic audit failure')
            return real(**kwargs)
        with patch('apps.core.commands.record_event',side_effect=failing):
            with self.assertRaises(RuntimeError):self.release(inspected)
        self.assertEqual(LedgerTransaction.objects.count(),count);self.assertFalse(QualityAuthorization.objects.exists());self.assertEqual(self.balance(),0)

    def test_append_only_and_no_nonce_writes(self):
        with self.assertRaises(DatabaseError),synthetic_write():
            with connection.cursor() as c:c.execute('UPDATE inventory_inspectionplan SET revision=99')
        with self.assertRaises(DatabaseError):
            with connection.cursor() as c:c.execute('DELETE FROM inventory_inspectionplan')

    def test_ncr_independent_closure_does_not_release(self):
        inspected=self.inspect();self.run_qc('review',pk=inspected['id'],actor=self.reviewer,decision='REJECT')
        ncr=self.run_qc('ncr',inspection=inspected['id'],hold=str(QualityHold.objects.get().pk),classification='synthetic:identity')
        with self.assertRaises(ValidationError):self.run_qc('ncr_action',pk=ncr['id'],kind='CORRECTIVE')
        from django.utils import timezone
        from datetime import timedelta
        for version,kind in enumerate(['INVESTIGATE','CORRECTIVE','PREVENTIVE'],1):
            extra={'owner':str(self.actor.pk),'target_at':(timezone.now()+timedelta(days=1)).isoformat()} if kind!='INVESTIGATE' else {}
            self.run_qc('ncr_action',pk=ncr['id'],version=version,kind=kind,**extra)
        with self.assertRaises(PermissionDenied):self.run_qc('ncr_action',pk=ncr['id'],version=4,kind='VERIFY')
        again=self.inspect('10',LedgerEntry.objects.get(stock=self.stock),previous=inspected['id'])
        self.run_qc('review',pk=again['id'],actor=self.reviewer,decision='ACCEPT')
        self.run_qc('ncr_action',pk=ncr['id'],version=4,kind='VERIFY',actor=self.reviewer,reinspection=again['id'])
        self.run_qc('ncr_action',pk=ncr['id'],version=5,kind='CLOSE',actor=self.reviewer)
        self.assertEqual(snapshot(Nonconformance.objects.get(pk=ncr['id']))['status'],'CLOSED')
        self.assertTrue(QualityHold.objects.exists());self.assertEqual(self.balance(),0)

    def test_api_permission_scope_history_and_decimal_boundary(self):
        client=APIClient();client.force_authenticate(self.actor)
        self.assertEqual(client.get('/api/v1/inventory/quality/plans/').status_code,200)
        inspected=self.inspect()
        self.assertEqual(client.get(f"/api/v1/inventory/quality/inspections/{inspected['id']}/history/").status_code,200)
        self.actor.user_permissions.remove(Permission.objects.get(codename='inspect_qc'))
        with self.assertRaises(PermissionDenied):self.inspect('10',LedgerEntry.objects.get(stock=self.stock),previous=inspected['id'])
        from apps.inventory.models import WarehouseScope
        # Immutable grants are preserved: use a different employee scoped to another warehouse.
        from apps.accounts.models import Employee
        from django.utils import timezone
        from datetime import timedelta
        Employee.objects.create(user=self.maker,department=self.department,employee_id='SYN-QC-OTHER',designation='Synthetic reader',created_by=self.actor,updated_by=self.actor)
        self.maker.user_permissions.add(*Permission.objects.filter(codename__in=['view_qc','view_qc_history']))
        WarehouseScope.objects.create(user=self.maker,warehouse=self.wh2,requested_by=self.actor,approved_by=self.reviewer,policy_reference='synthetic:reader',evidence_reference='synthetic:reader',expires_at=timezone.now()+timedelta(hours=1))
        client.force_authenticate(self.maker)
        self.assertEqual(client.get('/api/v1/inventory/quality/inspections/').data['count'],0)
        self.assertEqual(client.get(f"/api/v1/inventory/quality/inspections/{inspected['id']}/history/").status_code,404)

    def test_exact_quantity_invalid_inputs(self):
        self.opening('10',quality='HELD');source=LedgerEntry.objects.get(stock=self.stock)
        for value in [10,10.0,'1e1','10.0000001','-1','0']:
            with self.subTest(value=value),self.assertRaises(ValidationError):self.inspect(value,source)

    def test_return_requires_return_plan_and_remains_held(self):
        self.opening('10');out=self.submit(self.intent('OUT',[self.line('2',src=self.loc)]))[0]
        original=LedgerTransaction.objects.get(pk=out['id']).lines.get()
        self.submit(self.intent('RETURN',[{**self.line('2',quality='HELD',dst=self.loc),'original_line':str(original.pk)}],related=out['id']))
        source=LedgerEntry.objects.filter(stock=self.stock,quality='HELD').get()
        with self.assertRaises(ValidationError):self.inspect('2',source)
        self.assertEqual(self.balance(quality='HELD'),2)

    def test_partial_group_of_existing_independently_marked_roots_conserves_100(self):
        from apps.inventory.models import StockIdentity
        roots=[]
        for amount,decision in [('70','ACCEPT'),('20','REJECT'),('10','PENDING')]:
            self.stock=StockIdentity.objects.create(warehouse=self.wh,location=self.loc,material=self.material,unit=self.unit,kind='BATCH',ownership='COMPANY',ownership_evidence='synthetic:company',source_system='synthetic:qc-group',source_reference=amount,physical_reference='SYN-SEPARATE-'+amount,created_by=self.actor)
            inspected=self.inspect(amount);self.run_qc('review',pk=inspected['id'],actor=self.reviewer,decision=decision)
            if decision=='ACCEPT':self.release(inspected)
            roots.append(self.stock.pk)
        rows=BalanceProjection.objects.filter(stock_id__in=roots)
        self.assertEqual(sum(row.quantity for row in rows),100)
        self.assertEqual(sum(row.quantity for row in rows if row.quality=='RELEASED'),70)
        self.assertEqual(sum(row.quantity for row in rows if row.quality=='HELD'),30)
        self.assertFalse(StockIdentity.objects.filter(parent__isnull=False).exists())

    def test_return_whole_root_inspection_and_release(self):
        self.opening('10');out=self.submit(self.intent('OUT',[self.line('10',src=self.loc)]))[0]
        original=LedgerTransaction.objects.get(pk=out['id']).lines.get()
        self.submit(self.intent('RETURN',[{**self.line('10',quality='HELD',dst=self.loc),'original_line':str(original.pk)}],related=out['id']))
        body={k:self.plan[k] for k in ['reference','material','criteria','specification_reference','sampling_reference']}
        body.update(reference='synthetic:return',revision=1,applicability='RETURN')
        self.plan=self.run_qc('plan',**body);self.run_qc('publish',pk=self.plan['id'],actor=self.reviewer,decision='APPROVED')
        inspected=self.inspect('10',LedgerEntry.objects.get(stock=self.stock,quality='HELD'))
        self.run_qc('review',pk=inspected['id'],actor=self.reviewer,decision='ACCEPT');self.release(inspected)
        self.assertEqual(self.balance(),10);self.assertEqual(self.balance(quality='HELD'),0)

    def test_no_generic_quality_intent_or_orphan_authorization(self):
        self.opening('10',quality='HELD')
        lines=[self.line('10',quality='HELD',src=self.loc),self.line('10',dst=self.loc)]
        with self.assertRaises(ValidationError):self.submit(self.intent('QUALITY',lines))
        with self.assertRaises(DatabaseError),synthetic_write():
            QualityAuthorization.objects.create(actor=self.reviewer,stock=self.stock,location=self.loc,quantity=10,direction='HOLD',reason='synthetic:orphan',evidence_reference='synthetic:orphan')
        self.assertFalse(QualityAuthorization.objects.exists())

    def test_plan_and_review_require_atomic_audit_in_database(self):
        with self.assertRaises(DatabaseError),synthetic_write():
            InspectionPlan.objects.create(reference='synthetic:orphan',revision=1,applicability='INCOMING',material=self.material,criteria=[],specification_reference='x',sampling_reference='x',author=self.actor,digest='0'*64)

    def test_hold_concurrent_with_release_leaves_no_released_stock(self):
        inspected=self.accepted();barrier=Barrier(2)
        def attempt(action):
            connections.close_all()
            try:
                barrier.wait(timeout=10)
                if action=='hold':self.run_qc('hold',actor=self.reviewer,stock=str(self.stock.pk),location=str(self.loc.pk),policy=str(self.policy.pk),policy_version=1)
                else:self.release(inspected)
                return action
            except (ValidationError,CommandConflict,VersionConflict):return 'blocked'
            finally:connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(attempt,['hold','release']))
        self.assertIn('hold',results);self.assertEqual(self.balance(),0);self.assertEqual(self.balance(quality='HELD'),10)

    def test_revoked_release_capability_even_for_superuser(self):
        inspected=self.accepted();self.reviewer.user_permissions.remove(Permission.objects.get(codename='release_qc'))
        self.reviewer.is_superuser=True;self.reviewer.save(update_fields=['is_superuser'])
        with self.assertRaises(PermissionDenied):self.release(inspected)

    def test_restricted_runtime_role_quality_post_and_history_protection(self):
        from django.db import transaction
        from psycopg import sql
        inspected=self.accepted();role='phase3d_runtime_'+uuid.uuid4().hex
        with transaction.atomic():
            with connection.cursor() as c:
                c.execute(sql.SQL('CREATE ROLE {} NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE').format(sql.Identifier(role)))
                c.execute('REVOKE CREATE ON SCHEMA public FROM PUBLIC')
                c.execute(sql.SQL('GRANT USAGE ON SCHEMA public TO {}').format(sql.Identifier(role)))
                c.execute(sql.SQL('GRANT SELECT ON ALL TABLES IN SCHEMA public TO {}').format(sql.Identifier(role)))
                for table in ['inventory_qualityauthorization','inventory_qualityposting','inventory_sourceevent','inventory_ledgertransaction','inventory_transactionline','inventory_ledgerentry','inventory_balanceprojection','core_auditevent','core_auditevidence','core_idempotencyrecord']:
                    c.execute(sql.SQL('GRANT INSERT ON {} TO {}').format(sql.Identifier(table),sql.Identifier(role)))
                for table in ['inventory_stockidentity','inventory_sourceevent']:
                    c.execute(sql.SQL('GRANT UPDATE(id) ON {} TO {}').format(sql.Identifier(table),sql.Identifier(role)))
                for table in ['inventory_balanceprojection','core_idempotencyrecord']:
                    c.execute(sql.SQL('GRANT UPDATE ON {} TO {}').format(sql.Identifier(table),sql.Identifier(role)))
                c.execute(sql.SQL('SET LOCAL ROLE {}').format(sql.Identifier(role)))
            try:
                self.release(inspected)
                with connection.cursor() as c:c.execute('SET CONSTRAINTS ALL IMMEDIATE')
                for statement in ['UPDATE inventory_inspection SET quantity=1','DELETE FROM inventory_qualityauthorization','TRUNCATE inventory_qualityposting','ALTER TABLE inventory_qualityposting DISABLE TRIGGER ALL']:
                    with self.assertRaises(DatabaseError),transaction.atomic():
                        with connection.cursor() as c:c.execute(statement)
            finally:
                with connection.cursor() as c:c.execute('RESET ROLE')
                transaction.set_rollback(True)

    def test_plain_service_cannot_receive_or_open_released_stock(self):
        from apps.inventory.ledger import post_transaction
        for kind in ['OPENING','IN']:
            with self.subTest(kind=kind),self.assertRaises(ValidationError):
                post_transaction(actor=self.actor,intent=self.intent(kind,[self.line('10',dst=self.loc)]),key=str(uuid.uuid4()),request_id=uuid.uuid4())
        self.assertFalse(LedgerTransaction.objects.exists())

    def test_inspection_api_rejects_raw_numeric_quantities(self):
        self.opening('10',quality='HELD');entry=LedgerEntry.objects.get(stock=self.stock)
        held=BalanceProjection.objects.get(stock=self.stock)
        body={'plan':self.plan['id'],'source_entry':str(entry.pk),'balance_version':held.version,'physical_evidence':'synthetic:mark','observations':{'identity':True},'reason':'Synthetic inspection','evidence_reference':'synthetic:evidence'}
        client=APIClient();client.force_authenticate(self.actor)
        for value in [10,10.0,1e1,'1e1','10.0000001','0','-1']:
            with self.subTest(value=value):
                response=client.post('/api/v1/inventory/quality/inspections/',{**body,'quantity':value},format='json',HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()))
                self.assertEqual(response.status_code,400)
        response=client.post('/api/v1/inventory/quality/inspections/',{**body,'quantity':'10'},format='json',HTTP_IDEMPOTENCY_KEY='valid-qc')
        self.assertEqual(response.status_code,201)

    def test_transferred_held_source_cannot_lose_inspection_applicability(self):
        self.opening('10',quality='HELD');self.opening('0',loc=self.loc2,quality='HELD')
        self.submit(self.intent('TRANSFER',[self.line('10',quality='HELD',src=self.loc,dst=self.loc2)]))
        source=LedgerEntry.objects.get(stock=self.stock,location=self.loc2,delta__gt=0)
        with self.assertRaises(ValidationError):self.inspect('10',source)
        client=APIClient();client.force_authenticate(self.actor)
        rows=client.get('/api/v1/inventory/quality/held-stock/').data['results']
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['inspection_source_entry'],str(source.pk))
        self.assertFalse(rows[0]['whole_scope_supported']);self.assertEqual(self.balance(self.loc2,quality='HELD'),10)

    def test_phase3c_receipt_links_to_qc_without_automatic_release(self):
        from apps.accounts.models import Employee
        from apps.inventory.models import WarehouseScope
        from apps.inventory.workflow_models import PhysicalSourceDocument,PhysicalSourceLine
        from apps.inventory.workflows import submit_request,transition_request
        from django.utils import timezone
        from datetime import timedelta
        self.opening('0',quality='HELD')
        Employee.objects.create(user=self.maker,department=self.department,employee_id='SYN-QC-STORES',designation='Synthetic Stores',created_by=self.actor,updated_by=self.actor)
        self.maker.user_permissions.add(*Permission.objects.filter(content_type__app_label='inventory'))
        WarehouseScope.objects.create(user=self.maker,company_wide=True,requested_by=self.actor,approved_by=self.reviewer,policy_reference='synthetic:stores',evidence_reference='synthetic:stores',expires_at=timezone.now()+timedelta(hours=1))
        with synthetic_write():
            doc=PhysicalSourceDocument.objects.create(namespace='synthetic:qc-receipt',reference='synthetic:delivery',kind='RECEIPT',warehouse=self.wh,evidence_reference='synthetic:delivery',registered_by=self.reviewer)
            source=PhysicalSourceLine.objects.create(document=doc,occurrence_reference='delivery-1',line_reference='1',stock=self.stock,location=self.loc,unit=self.unit,quantity=10)
        body={'kind':'IN','warehouse':str(self.wh.pk),'source_system':doc.namespace,'source_reference':doc.reference,'source_event':'synthetic:receipt-1','cutoff':timezone.now().isoformat(),'reason':'Synthetic receipt','evidence_reference':'synthetic:physical-receipt','policy':str(self.policy.pk),'lines':[{'source_line':str(source.pk),'stock':str(self.stock.pk),'location':str(self.loc.pk),'unit':str(self.unit.pk),'quantity':'10','quality':'HELD'}]}
        obj=submit_request(actor=self.actor,data=body,key='qc-receipt',request_id=uuid.uuid4())[0]
        for step,actor in [('verify',self.maker),('confirm',self.maker),('approve',self.reviewer),('record',self.actor)]:
            data={'reason':'Synthetic '+step,'evidence_reference':'synthetic:'+step}
            if step=='approve':data['recorder']=str(self.actor.pk)
            obj=transition_request(actor=actor,pk=obj['id'],action=step,data=data,version=obj['version'],key=step,request_id=uuid.uuid4())[0]
        self.assertEqual(self.balance(),0);self.assertEqual(self.balance(quality='HELD'),10)
        entry=LedgerEntry.objects.get(transaction_id=obj['ledger_transaction'])
        inspected=self.inspect('10',entry,operation=obj['id'])
        self.run_qc('review',pk=inspected['id'],actor=self.reviewer,decision='ACCEPT');self.release(inspected)
        self.assertEqual(self.balance(),10);self.assertEqual(Inspection.objects.get(pk=inspected['id']).operation_id,uuid.UUID(obj['id']))
