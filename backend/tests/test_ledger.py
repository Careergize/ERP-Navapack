import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch
from django.conf import settings
from django.test import TransactionTestCase,override_settings
from django.db import connection,connections,transaction,DatabaseError,IntegrityError
from django.utils import timezone
from django.contrib.auth.models import Permission
from psycopg import sql
from rest_framework.exceptions import ValidationError,PermissionDenied
from rest_framework.test import APIClient
from apps.core.models import AuditEvent,AuditEvidence,IdempotencyRecord
from apps.core.commands import payload_hash
from apps.core.api import CommandConflict,VersionConflict,PreconditionRequired
from apps.accounts.models import User,Employee
from apps.inventory.models import Warehouse,StorageLocation,StockIdentity,WarehouseScope
from apps.inventory.ledger_models import (PostingPolicy,SourceEvent,LedgerApproval,LedgerTransaction,TransactionLine,LedgerEntry,BalanceProjection,OpeningCoverage)
from apps.inventory.ledger import post_transaction,key_for,custody_history,rebuild_projection,reversal_shape
from apps.inventory.ledger_guard import synthetic_write,require_synthetic_environment
from tests import test_inventory


class OperationalGateTests(TransactionTestCase):
    def test_default_disabled_for_any_internal_caller(self):
        with override_settings(SYNTHETIC_LEDGER_ENABLED=False):
            with self.assertRaises(PermissionDenied):post_transaction(actor=None,intent={},key='synthetic',request_id=uuid.uuid4())
            with self.assertRaises(PermissionDenied):rebuild_projection(actor=None,key='synthetic',request_id=uuid.uuid4())
            with self.assertRaises(PermissionDenied):custody_history(actor=None,stock_id=uuid.uuid4(),warehouse_id=uuid.uuid4())
    def test_settings_flag_alone_cannot_enable_a_database(self):
        with override_settings(SYNTHETIC_LEDGER_ENABLED=True,SYNTHETIC_LEDGER_DATABASE='test_phase3b_'+'0'*32,SYNTHETIC_LEDGER_NONCE=str(uuid.uuid4())):
            with self.assertRaises(PermissionDenied):require_synthetic_environment()
        with override_settings(SYNTHETIC_LEDGER_ENABLED=True,SETTINGS_MODULE='config.settings.production'):
            with self.assertRaises(PermissionDenied):require_synthetic_environment()


class SyntheticLedgerTests(TransactionTestCase):
    def setUp(self):
        if not getattr(settings,'SYNTHETIC_LEDGER_ENABLED',False):self.skipTest('Requires scripts/test_isolated.py --synthetic-ledger')
        require_synthetic_environment()
        test_inventory.InventoryFoundationTests.setUp(self)
        self.wh.custody_department=self.department;self.wh.save(update_fields=['custody_department'])
        self.loc=StorageLocation.objects.create(warehouse=self.wh,code='SYN-LOC',name='Synthetic custody',created_by=self.actor)
        self.wh2=Warehouse.objects.create(code='SYN-OTHER',name='Synthetic destination',custody_department=self.department,created_by=self.actor)
        self.loc2=StorageLocation.objects.create(warehouse=self.wh2,code='SYN-LOC2',name='Synthetic destination',created_by=self.actor)
        self.stock=StockIdentity.objects.create(warehouse=self.wh,location=self.loc,material=self.material,unit=self.unit,kind='BATCH',ownership='COMPANY',ownership_evidence='synthetic:company',source_system='synthetic:ledger',source_reference='root',source_document_reference='SYN-PRIVATE-SOURCE',physical_reference='SYN-PHYSICAL',created_by=self.actor)
        Employee.objects.create(user=self.reviewer,department=self.department,employee_id='SYN-REVIEWER',designation='Synthetic independent reviewer',created_by=self.actor,updated_by=self.actor)
        self.reviewer.user_permissions.add(*Permission.objects.filter(content_type__app_label='inventory'))
        WarehouseScope.objects.create(user=self.reviewer,company_wide=True,requested_by=self.maker,approved_by=self.actor,policy_reference='synthetic:scope',evidence_reference='synthetic:scope-evidence',expires_at=timezone.now()+timedelta(hours=1))
        with synthetic_write():
            self.policy=PostingPolicy.objects.create(reference='synthetic:ledger-policy',rules={'scale':6,'released_receipts':True,'closed_through':'2000-01-01T00:00:00+00:00','approval_kinds':['ADJUSTMENT','CORRECTION','REVERSAL']})

    def line(self,quantity='10',quality='RELEASED',src=None,dst=None,stock=None):
        stock=stock or self.stock
        line={'stock':str(stock.pk),'unit':str(stock.unit_id),'quantity':quantity,'quality':quality}
        if src:line['from_location']=str(src.pk)
        if dst:line['to_location']=str(dst.pk)
        return line
    def versions(self,lines):
        result={}
        for line in lines:
            stock=StockIdentity.objects.get(pk=line['stock'])
            for endpoint in ['from_location','to_location']:
                if line.get(endpoint):
                    loc=StorageLocation.objects.get(pk=line[endpoint]);acct=key_for(stock,loc,line.get('quality','HELD'))
                    row=BalanceProjection.objects.filter(balance_key=acct).first();result[acct]=row.version if row else 0
        return result
    def intent(self,kind,lines,**extra):
        return {'kind':kind,'policy':str(self.policy.pk),'policy_version':1,'source_system':'synthetic:test','source_event':str(uuid.uuid4()),'effective_at':timezone.now().isoformat(),'reason':'Synthetic manufacturing ledger test.','lines':lines,'expected_versions':self.versions(lines),'quality_reference':'synthetic:qc-fixture',**extra}
    def submit(self,intent,actor=None,key=None):
        return post_transaction(actor=actor or self.actor,intent=intent,key=key or str(uuid.uuid4()),request_id=uuid.uuid4())
    def opening(self,qty='10',loc=None,quality='RELEASED'):
        return self.submit(self.intent('OPENING',[self.line(qty,quality,dst=loc or self.loc)]))[0]
    def balance(self,loc=None,quality='RELEASED',stock=None):
        row=BalanceProjection.objects.filter(balance_key=key_for(stock or self.stock,loc or self.loc,quality)).first()
        return row.quantity if row else Decimal('0')
    def approve(self,intent,maker=None,approver=None,decision='APPROVED'):
        with synthetic_write():
            approval=LedgerApproval.objects.create(maker=maker or self.actor,approver=approver or self.reviewer,policy=self.policy,intent_hash=payload_hash({k:v for k,v in intent.items() if k!='approval'}),reference='synthetic:approved-fixture',decision=decision)
        intent['approval']=str(approval.pk)
        return intent

    def test_opening_receipt_issue_audit_and_idempotency(self):
        intent=self.intent('OPENING',[self.line(dst=self.loc)])
        first=self.submit(intent,key='repeat');again=self.submit(intent,key='repeat')
        self.assertEqual(first[:2],again[:2]);self.assertTrue(again[2]);self.assertEqual(LedgerTransaction.objects.count(),1)
        event=AuditEvent.objects.get(entity_id=first[0]['id']);self.assertEqual(event.actor_id,self.actor.pk)
        self.assertEqual(event.evidence.payload['summary']['outcome']['policy']['id'],str(self.policy.pk))
        evidence=event.evidence.payload['summary']['outcome']
        self.assertEqual(evidence['kind'],'OPENING')
        self.assertEqual(evidence['source_identity']['event'],intent['source_event'])
        self.assertEqual(evidence['actor_contexts'][0]['employee_id'],str(self.actor.employee.pk))
        issue=self.submit(self.intent('OUT',[self.line('4',src=self.loc)]))[0]
        self.assertEqual(self.balance(),Decimal('6'))
        self.assertEqual(LedgerEntry.objects.get(transaction_id=issue['id']).delta,Decimal('-4'))
        self.assertEqual(OpeningCoverage.objects.get().status,'KNOWN')

    def test_cross_actor_duplicate_source_is_rejected(self):
        intent=self.intent('OPENING',[self.line(dst=self.loc)])
        self.submit(intent,key='first')
        with self.assertRaises(CommandConflict):self.submit(intent,actor=self.reviewer,key='other-actor')
        with self.assertRaises(CommandConflict):self.submit(intent,key='other-key')
        self.assertEqual(SourceEvent.objects.count(),1);self.assertEqual(self.balance(),Decimal('10'))

    def test_unknown_coverage_and_explicit_zero(self):
        with self.assertRaises(ValidationError):self.submit(self.intent('IN',[self.line('3','HELD',dst=self.loc)]))
        self.assertFalse(LedgerTransaction.objects.exists())
        self.opening('0',quality='HELD');self.assertEqual(LedgerEntry.objects.count(),0)
        self.submit(self.intent('IN',[self.line('3','HELD',dst=self.loc)]))
        self.assertEqual(self.balance(quality='HELD'),Decimal('3'))
        with self.assertRaises(ValidationError):self.opening('5')

    def test_held_issue_and_insufficient_stock_are_rejected(self):
        self.opening('10',quality='HELD')
        with self.assertRaises(ValidationError):self.submit(self.intent('OUT',[self.line('1','HELD',src=self.loc)]))
        with self.assertRaises(ValidationError):self.submit(self.intent('OUT',[self.line('1','RELEASED',src=self.loc)]))
        self.assertEqual(self.balance(quality='HELD'),Decimal('10'));self.assertEqual(LedgerTransaction.objects.count(),1)

    def test_units_scale_and_no_inferred_conversion(self):
        self.opening()
        for amount in ['1.0000001',1.5,'-1','1e2','100000000000000']:
            with self.assertRaises(ValidationError):self.submit(self.intent('OUT',[self.line(amount,src=self.loc)]))
        line=self.line('1',src=self.loc);line['unit']=str(uuid.uuid4())
        with self.assertRaises(ValidationError):self.submit(self.intent('OUT',[line]))
        self.assertEqual(self.balance(),Decimal('10'))

    def test_concurrent_issue_has_one_winner_and_no_partial_residue(self):
        self.opening()
        when=timezone.now().isoformat()
        intents=[self.intent('OUT',[self.line('7',src=self.loc)],effective_at=when) for _ in range(2)]
        barrier=Barrier(2)
        def worker(intent):
            connections.close_all()
            try:
                actor=User.objects.get(pk=self.actor.pk);barrier.wait(timeout=10)
                try:self.submit(intent,actor=actor);return 'posted'
                except (ValidationError,VersionConflict):return 'blocked'
            finally:connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(worker,i) for i in intents];results=[f.result(timeout=30) for f in futures]
        self.assertEqual(sorted(results),['blocked','posted']);self.assertEqual(self.balance(),Decimal('3'))
        self.assertEqual(LedgerTransaction.objects.count(),2);self.assertEqual(SourceEvent.objects.count(),2)
        self.assertEqual(AuditEvent.objects.filter(entity_type='inventory.ledgertransaction').count(),2)

    def test_transfer_conservation_registration_unchanged_and_destination_history(self):
        self.opening();self.opening('0',loc=self.loc2,quality='HELD')
        self.submit(self.intent('TRANSFER',[self.line('4',src=self.loc,dst=self.loc2)]))
        self.assertEqual(self.balance()+self.balance(self.loc2),Decimal('10'))
        self.stock.refresh_from_db();self.assertEqual(self.stock.warehouse_id,self.wh.pk);self.assertEqual(self.stock.location_id,self.loc.pk)
        Employee.objects.create(user=self.maker,department=self.department,employee_id='SYN-DEST',designation='Synthetic destination',created_by=self.actor,updated_by=self.actor)
        self.maker.user_permissions.add(*Permission.objects.filter(content_type__app_label='inventory',codename__in=['view_synthetic_custody','view_stockidentity','post_synthetic_transaction']))
        WarehouseScope.objects.create(user=self.maker,warehouse=self.wh2,requested_by=self.actor,approved_by=self.reviewer,policy_reference='synthetic:dest',evidence_reference='synthetic:dest',expires_at=timezone.now()+timedelta(hours=1))
        view=custody_history(actor=self.maker,stock_id=self.stock.pk,warehouse_id=self.wh2.pk)
        self.assertEqual(view['identity']['reference'],self.stock.reference)
        self.assertNotIn('SYN-PRIVATE-SOURCE',str(view));self.assertNotIn(str(self.loc.pk),str(view))
        with self.assertRaises(PermissionDenied):custody_history(actor=self.maker,stock_id=self.stock.pk,warehouse_id=self.wh.pk)
        client=APIClient();client.force_authenticate(self.maker)
        self.assertEqual(client.get(f'/api/v1/inventory/identities/{self.stock.pk}/').status_code,404)
        self.submit(self.intent('OUT',[self.line('1',src=self.loc2)]),actor=self.maker)
        self.assertEqual(self.balance(self.loc2),Decimal('3'))

    def test_unresolved_owner_custody_and_lineage_are_unavailable(self):
        child=StockIdentity.objects.create(warehouse=self.wh,material=self.material,unit=self.unit,kind='PORTION',parent=self.stock,ownership='COMPANY',ownership_evidence='synthetic:company',source_system='synthetic:ledger',source_reference='child',physical_reference='SYN-CHILD',created_by=self.actor)
        with self.assertRaises(ValidationError):self.submit(self.intent('OPENING',[self.line(stock=child,dst=self.loc)]))
        unresolved=StockIdentity.objects.create(warehouse=self.wh,material=self.material,unit=self.unit,kind='BATCH',source_system='synthetic:ledger',source_reference='unknown',physical_reference='SYN-UNKNOWN',created_by=self.actor)
        with self.assertRaises(ValidationError):self.submit(self.intent('OPENING',[self.line(stock=unresolved,dst=self.loc)]))
        self.wh2.custody_department=None;self.wh2.save(update_fields=['custody_department'])
        with self.assertRaises(ValidationError):self.opening(loc=self.loc2)

    def test_compensating_reversal_requires_independent_approval_and_restores_held(self):
        self.opening()
        out=self.submit(self.intent('OUT',[self.line('4',src=self.loc)]))[0]
        original=LedgerTransaction.objects.get(pk=out['id']);shape=reversal_shape(original)
        intent=self.intent('REVERSAL',shape,reverses=str(original.pk))
        with self.assertRaises(PermissionDenied):self.submit(intent)
        self.approve(intent);result=self.submit(intent)[0]
        self.assertEqual(self.balance(),Decimal('6'));self.assertEqual(self.balance(quality='HELD'),Decimal('4'))
        self.assertEqual(LedgerTransaction.objects.get(pk=result['id']).reverses_id,original.pk)
        self.assertEqual(original.entries.get().delta,Decimal('-4'))
        evidence=AuditEvent.objects.get(entity_id=result['id']).evidence.payload['summary']['outcome']
        self.assertEqual(evidence['approval_evidence']['approver'],str(self.reviewer.pk))
        self.assertEqual(evidence['approval_evidence']['decision'],'APPROVED')
        self.assertTrue(evidence['approval_contexts'])
        with self.assertRaises(ValidationError):self.submit(self.approve(self.intent('REVERSAL',shape,reverses=str(original.pk))))

    def test_reversal_cannot_remove_already_consumed_receipt(self):
        self.opening('0',quality='HELD')
        receipt=self.submit(self.intent('IN',[self.line('5',dst=self.loc)]))[0]
        self.submit(self.intent('OUT',[self.line('4',src=self.loc)]))
        original=LedgerTransaction.objects.get(pk=receipt['id'])
        with self.assertRaises(ValidationError):self.submit(self.approve(self.intent('REVERSAL',reversal_shape(original),reverses=str(original.pk))))
        self.assertEqual(self.balance(),Decimal('1'))

    def test_return_is_bounded_by_original_issue_and_held(self):
        self.opening();issue=self.submit(self.intent('OUT',[self.line('4',src=self.loc)]))[0]
        original=TransactionLine.objects.get(transaction_id=issue['id'])
        line=self.line('3','HELD',dst=self.loc);line['original_line']=str(original.pk)
        self.submit(self.intent('RETURN',[line],related=issue['id']))
        self.assertEqual(self.balance(quality='HELD'),Decimal('3'))
        line['quantity']='2'
        with self.assertRaises(ValidationError):self.submit(self.intent('RETURN',[line],related=issue['id']))

    def test_correction_preserves_original_and_requires_current_feasibility(self):
        opened=self.opening()
        self.submit(self.intent('OUT',[self.line('7',src=self.loc)]))
        invalid=self.approve(self.intent('CORRECTION',[self.line('4',src=self.loc)],related=opened['id']))
        with self.assertRaises(ValidationError):self.submit(invalid)
        valid=self.approve(self.intent('CORRECTION',[self.line('2',src=self.loc)],related=opened['id']))
        corrected=self.submit(valid)[0]
        self.assertEqual(self.balance(),Decimal('1'))
        self.assertEqual(LedgerEntry.objects.get(transaction_id=opened['id']).delta,Decimal('10'))
        self.assertEqual(LedgerTransaction.objects.get(pk=corrected['id']).related_id,uuid.UUID(opened['id']))
        self.assertEqual(OpeningCoverage.objects.get().opening_quantity,Decimal('10'))
        positive=self.approve(self.intent('ADJUSTMENT',[self.line('2','HELD',dst=self.loc)]))
        self.submit(positive)
        self.assertEqual(self.balance(quality='HELD'),Decimal('2'))

    def test_transfer_reversal_conserves_custody_without_restoring_qc_release(self):
        self.opening();self.opening('0',loc=self.loc2,quality='HELD')
        transfer=self.submit(self.intent('TRANSFER',[self.line('4',src=self.loc,dst=self.loc2)]))[0]
        original=LedgerTransaction.objects.get(pk=transfer['id'])
        intent=self.approve(self.intent('REVERSAL',reversal_shape(original),reverses=transfer['id']))
        self.submit(intent)
        self.assertEqual(self.balance(),Decimal('6'))
        self.assertEqual(self.balance(quality='HELD'),Decimal('4'))
        self.assertEqual(self.balance(loc=self.loc2),0)
        self.assertEqual(sum(BalanceProjection.objects.values_list('quantity',flat=True)),Decimal('10'))

    def test_approval_rejection_content_binding_and_no_self_approval(self):
        self.opening()
        intent=self.intent('ADJUSTMENT',[self.line('1','HELD',dst=self.loc)])
        self.approve(intent,decision='REJECTED')
        with self.assertRaises(PermissionDenied):self.submit(intent)
        intent=self.approve(self.intent('ADJUSTMENT',[self.line('1','HELD',dst=self.loc)]));intent['lines'][0]['quantity']='2'
        with self.assertRaises(PermissionDenied):self.submit(intent)
        with self.assertRaises(DatabaseError),synthetic_write():
            LedgerApproval.objects.create(maker=self.actor,approver=self.actor,policy=self.policy,intent_hash='0'*64,reference='synthetic:self',decision='APPROVED')

    def test_backdate_closed_policy_and_projection_versions(self):
        opened=self.opening();when=LedgerTransaction.objects.get(pk=opened['id']).event_at
        with self.assertRaises(ValidationError):self.submit(self.intent('IN',[self.line('1','HELD',dst=self.loc)],effective_at=(when-timedelta(seconds=1)).isoformat()))
        with self.assertRaises(ValidationError):self.submit(self.intent('IN',[self.line('1','HELD',dst=self.loc)],effective_at='1999-01-01T00:00:00+00:00'))
        intent=self.intent('OUT',[self.line('1',src=self.loc)]);intent['expected_versions']={}
        with self.assertRaises(PreconditionRequired):self.submit(intent)
        intent=self.intent('OUT',[self.line('1',src=self.loc)]);intent['expected_versions']={k:0 for k in intent['expected_versions']}
        with self.assertRaises(VersionConflict):self.submit(intent)

    def test_audit_failure_rolls_back_ledger_source_coverage_and_projection(self):
        before=IdempotencyRecord.objects.count()
        with patch('apps.core.commands.record_event',side_effect=RuntimeError('Synthetic audit failure')):
            with self.assertRaises(RuntimeError):self.opening()
        for model in [LedgerTransaction,TransactionLine,LedgerEntry,SourceEvent,BalanceProjection,OpeningCoverage]:self.assertFalse(model.objects.exists())
        self.assertEqual(IdempotencyRecord.objects.count(),before)

    def test_projection_rebuild_from_entries_and_explicit_zero(self):
        self.opening();self.opening('0',loc=self.loc2,quality='HELD')
        row=BalanceProjection.objects.get(balance_key=key_for(self.stock,self.loc,'RELEASED'))
        with synthetic_write():
            with connection.cursor() as c:c.execute("SELECT set_config('navapack.ledger_rebuild','on',true)")
            BalanceProjection.objects.filter(pk=row.pk).update(quantity=Decimal('999'),version=row.version+1)
        result=rebuild_projection(actor=self.actor,key='rebuild',request_id=uuid.uuid4())
        self.assertEqual(result[0]['rebuilt_keys'],2);self.assertEqual(self.balance(),Decimal('10'))
        self.assertEqual(BalanceProjection.objects.get(location=self.loc2).quantity,0)
        self.assertEqual(AuditEvent.objects.filter(action='inventory.rebuild_synthetic_projection').count(),1)
        event=AuditEvent.objects.get(action='inventory.rebuild_synthetic_projection')
        changes=event.evidence.payload['summary']['outcome']['changes']
        restored=next(change for change in changes if change['key']==row.balance_key)
        self.assertEqual(Decimal(restored['before']['quantity']),Decimal('999'))
        self.assertEqual(Decimal(restored['after']['quantity']),Decimal('10'))

    def test_database_append_only_late_entries_and_atomic_audit_constraint(self):
        opened=self.opening();head=LedgerTransaction.objects.get(pk=opened['id']);entry=LedgerEntry.objects.get();line=head.lines.get()
        with self.assertRaises(ValueError):LedgerEntry.objects.filter(pk=entry.pk).update(delta=1)
        for table,pk in [('ledgertransaction',head.pk),('transactionline',line.pk),('ledgerentry',entry.pk),('sourceevent',head.source_id),('postingpolicy',self.policy.pk)]:
            for operation in ['UPDATE','DELETE']:
                with self.assertRaises(DatabaseError),synthetic_write():
                    with connection.cursor() as c:
                        if operation=='UPDATE':c.execute(f'UPDATE inventory_{table} SET id=id WHERE id=%s',[pk])
                        else:c.execute(f'DELETE FROM inventory_{table} WHERE id=%s',[pk])
        with self.assertRaises(DatabaseError),synthetic_write():
            LedgerEntry.objects.create(transaction=head,line=line,sequence=2,stock=self.stock,location=self.loc,unit=self.unit,owner_key='COMPANY:synthetic:company',quality='RELEASED',balance_key=entry.balance_key,delta=1,event_at=head.event_at)
        with self.assertRaises(DatabaseError),synthetic_write():
            source=SourceEvent.objects.create(system='synthetic:raw',event_key='orphan',intent_hash='0'*64)
            LedgerTransaction.objects.create(source=source,policy=self.policy,actor=self.actor,kind='IN',event_at=timezone.now(),reason='Synthetic missing lines and audit')
        self.assertEqual(LedgerTransaction.objects.count(),1)

    def test_unauthorized_scope_replay_and_default_no_public_post_routes(self):
        intent=self.intent('OPENING',[self.line(dst=self.loc)])
        self.submit(intent,key='authorized')
        self.actor.user_permissions.clear()
        with self.assertRaises(PermissionDenied):self.submit(intent,key='authorized')
        client=APIClient();client.force_authenticate(self.reviewer)
        for endpoint in ['post','ledger','transactions','opening','receipts','issues']:
            self.assertEqual(client.post('/api/v1/inventory/'+endpoint+'/',{},format='json').status_code,404)
        with self.assertRaises(DatabaseError),transaction.atomic():
            SourceEvent.objects.create(system='synthetic:no-service',event_key='blocked',intent_hash='0'*64)

    def test_custody_deactivation_and_retirement_cannot_hide_onhand_stock(self):
        self.opening();self.opening('0',loc=self.loc2,quality='HELD')
        self.submit(self.intent('TRANSFER',[self.line('10',src=self.loc,dst=self.loc2)]))
        for table,pk,update in [('warehouse',self.wh2.pk,'is_active=false'),('storagelocation',self.loc2.pk,'is_active=false'),('stockidentity',self.stock.pk,"lifecycle='RETIRED'")]:
            with self.assertRaises(DatabaseError),transaction.atomic():
                with connection.cursor() as c:c.execute(f'UPDATE inventory_{table} SET {update} WHERE id=%s',[pk])

    def test_restricted_nonowner_role_can_post_but_cannot_modify_history_or_ddl(self):
        self.opening()
        intent=self.intent('IN',[self.line('1','HELD',dst=self.loc)])
        role='phase3b_runtime_'+uuid.uuid4().hex
        with transaction.atomic():
            with connection.cursor() as c:
                c.execute(sql.SQL('CREATE ROLE {} NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE').format(sql.Identifier(role)))
                c.execute('REVOKE CREATE ON SCHEMA public FROM PUBLIC')
                c.execute(sql.SQL('GRANT USAGE ON SCHEMA public TO {}').format(sql.Identifier(role)))
                c.execute(sql.SQL('GRANT SELECT ON ALL TABLES IN SCHEMA public TO {}').format(sql.Identifier(role)))
                for table in ['inventory_sourceevent','inventory_ledgertransaction','inventory_transactionline','inventory_ledgerentry','inventory_balanceprojection','core_auditevent','core_auditevidence','core_idempotencyrecord']:
                    c.execute(sql.SQL('GRANT INSERT ON {} TO {}').format(sql.Identifier(table),sql.Identifier(role)))
                for table in ['inventory_stockidentity','inventory_sourceevent']:
                    c.execute(sql.SQL('GRANT UPDATE(id) ON {} TO {}').format(sql.Identifier(table),sql.Identifier(role)))
                for table in ['inventory_balanceprojection','core_idempotencyrecord']:
                    c.execute(sql.SQL('GRANT UPDATE ON {} TO {}').format(sql.Identifier(table),sql.Identifier(role)))
                c.execute(sql.SQL('SET LOCAL ROLE {}').format(sql.Identifier(role)))
            try:
                result=self.submit(intent);self.assertEqual(result[1],201)
                with connection.cursor() as c:c.execute('SET CONSTRAINTS ALL IMMEDIATE')
                for statement in ['UPDATE inventory_ledgerentry SET delta=1','DELETE FROM inventory_ledgerentry','TRUNCATE inventory_ledgerentry','ALTER TABLE inventory_ledgerentry DISABLE TRIGGER ALL','CREATE TABLE public.synthetic_forbidden (id int)','TRUNCATE core_auditevent']:
                    with self.assertRaises(DatabaseError),transaction.atomic():
                        with connection.cursor() as c:c.execute(statement)
            finally:
                with connection.cursor() as c:c.execute('RESET ROLE')
                transaction.set_rollback(True)
