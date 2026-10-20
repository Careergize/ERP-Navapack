"""Combined inventory/QC acceptance with real JWT authentication and PostgreSQL."""
import uuid
from datetime import timedelta
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from django.test import TransactionTestCase, override_settings
from django.db import connections
from django.utils import timezone
from django.contrib.auth.models import Permission
from rest_framework.test import APIClient
from apps.accounts.models import User, Employee
from apps.inventory.models import StockIdentity, WarehouseScope
from apps.inventory.workflow_models import PhysicalSourceDocument, PhysicalSourceLine, OperationRequest
from apps.inventory.ledger_models import BalanceProjection, LedgerEntry, LedgerTransaction
from apps.inventory.quality_models import QualityHold, Inspection, Nonconformance
from apps.inventory.ledger_guard import synthetic_write
from tests import test_operations


class Phase3EAcceptanceTests(TransactionTestCase):
    def initialize(self, authenticate=True):
        test_operations.OperationTests.setUp(self)
        self.clients = {}
        if authenticate:
            for name, actor in [('recorder',self.actor),('stores',self.maker),('reviewer',self.reviewer)]:
                self.clients[name] = self.login(actor)

    def setUp(self): self.initialize()

    def login(self, actor):
        client=APIClient()
        result=client.post('/api/v1/auth/login/',{'email':actor.email,'password':'password'},format='json')
        self.assertEqual(result.status_code,200,'Synthetic JWT login failed.')
        client.credentials(HTTP_AUTHORIZATION='Bearer '+result.data['access'])
        return client

    def api(self, path, data, who='recorder', version=None, key=None, expected=(200,201)):
        headers={'HTTP_IDEMPOTENCY_KEY':key or str(uuid.uuid4())}
        if version is not None: headers['HTTP_IF_MATCH']='"'+str(version)+'"'
        response=self.clients[who].post('/api/v1/inventory/'+path,data,format='json',**headers)
        self.assertIn(response.status_code,expected,response.data)
        return response.data

    def body(self, kind, qty='10', location=None, quality='HELD', **extra):
        location=location or self.loc
        event=str(uuid.uuid4()); reference='synthetic:e2e-'+('receipts' if kind=='IN' else 'counts')
        line={'stock':str(self.stock.pk),'location':str(location.pk),'unit':str(self.unit.pk),'quantity':qty,'quality':quality}
        if kind in ['IN','OPENING','COUNT']:
            with synthetic_write():
                doc,_=PhysicalSourceDocument.objects.get_or_create(namespace='synthetic:phase3e',reference=reference+'-'+str(location.warehouse_id),defaults={'kind':'RECEIPT' if kind=='IN' else 'COUNT','warehouse':location.warehouse,'evidence_reference':'synthetic:registered-evidence','registered_by':self.reviewer})
                physical=PhysicalSourceLine.objects.create(document=doc,occurrence_reference=event,line_reference='1',stock=self.stock,location=location,unit=self.unit,quantity=Decimal(qty))
            line['source_line']=str(physical.pk); reference=doc.reference
        data={'kind':kind,'warehouse':str(location.warehouse_id),'source_system':'synthetic:phase3e','source_event':event,'source_reference':reference,
              'evidence_reference':'synthetic:physical-evidence','counterparty_reference':'synthetic:receiver','reason':'Synthetic end-to-end evidence.',
              'policy':str(self.policy.pk),'lines':[line],**extra}
        if kind not in ['OPENING','COUNT']:data['cutoff']=timezone.now().isoformat()
        return data

    def create_operation(self, body, **kwargs):return self.api('operations/',body,**kwargs)

    def step(self, obj, step, who='stores', **kwargs):
        data={'reason':'Synthetic '+step,'evidence_reference':'synthetic:'+step}
        if step=='approve':data['recorder']=str(self.actor.pk)
        return self.api('operations/'+obj['id']+'/'+step+'/',data,who,version=obj['version'],**kwargs)

    def prepared(self, obj):
        obj=self.step(obj,'verify')
        if obj['kind'] in ['COUNT','ADJUSTMENT','OPENING_CORRECTION']:obj=self.step(obj,'investigate')
        return obj if obj['kind']=='COUNT' else self.step(obj,'confirm')

    def posted(self, body):
        obj=self.prepared(self.create_operation(body));obj=self.step(obj,'approve','reviewer')
        return self.step(obj,'record','recorder')

    def plan(self, revision=1, reference=None, applicability='INCOMING'):
        data={'reference':reference or 'synthetic:e2e-'+uuid.uuid4().hex,'revision':revision,'applicability':applicability,
            'material':str(self.material.pk),'criteria':[{'id':'identity','type':'BOOLEAN','expected':True,'reference':'synthetic:requirement'}],
            'specification_reference':'synthetic:specification-v1','sampling_reference':'synthetic:sampling-v1',
            'reason':'Synthetic plan evidence','evidence_reference':'synthetic:plan'}
        obj=self.api('quality/plans/',data)
        self.api('quality/plans/'+obj['id']+'/publish/',{'decision':'APPROVED','reason':'Synthetic independent publication','evidence_reference':'synthetic:publication'},'reviewer',version=1)
        return obj

    def inspect(self, operation, plan, passed=True, previous=None):
        entry=LedgerEntry.objects.get(transaction_id=operation['ledger_transaction'],delta__gt=0)
        held=BalanceProjection.objects.get(stock=entry.stock,location=entry.location,quality='HELD')
        data={'plan':plan['id'],'source_entry':str(entry.pk),'operation':operation['id'],'quantity':str(held.quantity),
            'balance_version':held.version,'physical_evidence':'synthetic:whole-marked-root','observations':{'identity':passed},
            'reason':'Synthetic inspection evidence','evidence_reference':'synthetic:inspection'}
        if previous:data['previous']=previous['id']
        return self.api('quality/inspections/',data)

    def review(self, inspection, decision='ACCEPT'):
        return self.api('quality/inspections/'+inspection['id']+'/review/',{'decision':decision,'reason':'Synthetic independent review','evidence_reference':'synthetic:review'},'reviewer',version=1)

    def release(self, inspection, **kwargs):
        return self.api('quality/inspections/'+inspection['id']+'/release/',{'policy':str(self.policy.pk),'policy_version':1,'reason':'Synthetic independent release','evidence_reference':'synthetic:release'},'reviewer',version=1,**kwargs)

    def custody_state(self, stock=None, location=None, who='recorder'):
        result=self.clients[who].get('/api/v1/inventory/custody/scope/',{'stock':str((stock or self.stock).pk),'location':str((location or self.loc).pk)})
        self.assertEqual(result.status_code,200,result.data);return result.data

    def incoming(self, qty='10'):
        opening=self.posted(self.body('OPENING','0'))
        receipt=self.posted(self.body('IN',qty))
        return opening,receipt

    def ready(self):
        _,receipt=self.incoming();plan=self.plan();inspected=self.inspect(receipt,plan)
        self.review(inspected);self.release(inspected)
        return receipt,plan,inspected

    def test_a_receipt_held_inspection_release_actual_issue_and_history(self):
        _,receipt=self.incoming()
        self.assertEqual(Decimal(self.custody_state()['partitions']['HELD']['quantity']),10)
        plan=self.plan();inspected=self.inspect(receipt,plan);self.review(inspected)
        self.assertEqual(Decimal(self.custody_state()['partitions']['RELEASED']['quantity']),0)
        self.release(inspected)
        issue=self.posted(self.body('OUT','3',quality='RELEASED'))
        self.assertTrue(issue['stock_movement_posted']);self.assertEqual(Decimal(self.custody_state()['partitions']['RELEASED']['quantity']),7)
        movement=self.clients['recorder'].get('/api/v1/inventory/custody/movements/').data
        self.assertIn(issue['ledger_transaction'],[r['transaction'] for r in movement['results']])
        history=self.clients['recorder'].get('/api/v1/inventory/quality/inspections/'+inspected['id']+'/history/').data
        self.assertIn('inventory.qc_release',[r['action'] for r in history['results']])

    def test_b_failed_inspection_ncr_capa_reinspection_never_auto_releases(self):
        _,receipt=self.incoming();plan=self.plan();inspected=self.inspect(receipt,plan,False);self.review(inspected,'REJECT')
        hold=QualityHold.objects.get(stock=self.stock)
        ncr=self.api('quality/ncr/',{'inspection':inspected['id'],'hold':str(hold.pk),'classification':'synthetic:identity','reason':'Synthetic nonconformity','evidence_reference':'synthetic:containment'})
        version=1
        for kind in ['INVESTIGATE','CORRECTIVE','PREVENTIVE']:
            body={'kind':kind,'reason':'Synthetic '+kind,'evidence_reference':'synthetic:'+kind}
            if kind!='INVESTIGATE':body.update(owner=str(self.actor.pk),target_at=(timezone.now()+timedelta(days=1)).isoformat())
            self.api('quality/ncr/'+ncr['id']+'/ncr_action/',body,version=version);version+=1
        again=self.inspect(receipt,plan,True,inspected);self.review(again)
        self.api('quality/ncr/'+ncr['id']+'/ncr_action/',{'kind':'VERIFY','reinspection':again['id'],'reason':'Synthetic effectiveness evidence','evidence_reference':'synthetic:effectiveness'},'reviewer',version=version)
        self.api('quality/ncr/'+ncr['id']+'/ncr_action/',{'kind':'CLOSE','reason':'Synthetic independent closure','evidence_reference':'synthetic:closure'},'reviewer',version=version+1)
        self.release(again,expected=(400,))
        self.assertEqual(Decimal(self.custody_state()['partitions']['HELD']['quantity']),10)
        self.assertEqual(self.clients['recorder'].get('/api/v1/inventory/quality/ncr/'+ncr['id']+'/').data['status'],'CLOSED')

    def test_c_opening_remains_held_until_independent_qc(self):
        opening=self.posted(self.body('OPENING'))
        plan=self.plan();inspected=self.inspect(opening,plan)
        self.api('quality/inspections/'+inspected['id']+'/review/',{'decision':'ACCEPT','reason':'Synthetic own review','evidence_reference':'synthetic:own'},version=1,expected=(403,))
        self.review(inspected);self.release(inspected)
        self.assertEqual(Decimal(self.custody_state()['partitions']['RELEASED']['quantity']),10)

    def test_d_held_transfer_preserves_identity_quality_and_clearance_gate(self):
        self.posted(self.body('OPENING'));self.posted(self.body('OPENING','0',location=self.loc2))
        body=self.body('TRANSFER','10');body['lines'][0]['destination']=str(self.loc2.pk)
        transfer=self.posted(body)
        self.assertEqual(Decimal(self.custody_state(location=self.loc2)['partitions']['HELD']['quantity']),10)
        stock=StockIdentity.objects.get(pk=self.stock.pk);self.assertEqual(stock.warehouse_id,self.wh.pk)
        plan=self.plan()
        self.inspect_blocked_transfer(transfer,plan)

    def inspect_blocked_transfer(self, obj, plan):
        entry=LedgerEntry.objects.get(transaction_id=obj['ledger_transaction'],delta__gt=0)
        balance=BalanceProjection.objects.get(stock=self.stock,location=entry.location,quality='HELD')
        self.api('quality/inspections/',{'plan':plan['id'],'source_entry':str(entry.pk),'quantity':str(balance.quantity),'balance_version':balance.version,'physical_evidence':'synthetic:mark','observations':{'identity':True},'reason':'Synthetic transferred scope','evidence_reference':'synthetic:transfer'},expected=(400,))

    def test_e_concurrent_authorized_out_records_cannot_over_issue(self):
        self.ready()
        requests=[self.step(self.prepared(self.create_operation(self.body('OUT','7',quality='RELEASED'))),'approve','reviewer') for _ in range(2)]
        barrier=Barrier(2);credentials=dict(self.clients['recorder']._credentials)
        def record(obj):
            connections.close_all();client=APIClient();client.credentials(**credentials)
            try:
                barrier.wait(timeout=15)
                return client.post('/api/v1/inventory/operations/'+obj['id']+'/record/',{'reason':'Synthetic physical issue','evidence_reference':'synthetic:issue'},format='json',HTTP_IF_MATCH='"'+str(obj['version'])+'"',HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4())).status_code
            finally:connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:statuses=list(pool.map(record,requests))
        self.assertEqual(sum(s==200 for s in statuses),1);self.assertTrue(all(s in [200,400,409,412] for s in statuses))
        self.assertEqual(Decimal(self.custody_state()['partitions']['RELEASED']['quantity']),3)

    def test_f_receipt_approval_release_retries_and_cross_actor_duplicates(self):
        self.posted(self.body('OPENING','0'));body=self.body('IN')
        request=self.create_operation(body,key='receipt-retry');same=self.create_operation(body,key='receipt-retry');self.assertEqual(request,same)
        self.create_operation(body,who='stores',expected=(409,))
        request=self.prepared(request);approved=self.step(request,'approve','reviewer',key='approve-retry')
        self.assertEqual(approved,self.step(request,'approve','reviewer',key='approve-retry'))
        receipt=self.step(approved,'record','recorder');plan=self.plan();inspected=self.inspect(receipt,plan);self.review(inspected)
        first=self.release(inspected,key='release-retry');self.assertEqual(first,self.release(inspected,key='release-retry'))
        self.release(inspected,expected=(400,409,412))
        self.assertEqual(Decimal(self.custody_state()['partitions']['RELEASED']['quantity']),10)

    def test_g_scoped_reads_writes_and_foreign_source_evidence(self):
        self.ready();outsider=User.objects.create_user('scoped@example.test','password')
        Employee.objects.create(user=outsider,department=self.department,employee_id='SYN-E2E-SCOPED',designation='Synthetic scoped reader',created_by=self.actor,updated_by=self.actor)
        outsider.user_permissions.add(*Permission.objects.filter(content_type__app_label='inventory',codename__startswith='view_'))
        WarehouseScope.objects.create(user=outsider,warehouse=self.wh2,requested_by=self.actor,approved_by=self.reviewer,policy_reference='synthetic:scope',evidence_reference='synthetic:scope',expires_at=timezone.now()+timedelta(hours=1))
        client=self.login(outsider)
        for path in ['operations/','quality/inspections/','custody/balances/','custody/movements/']:
            result=client.get('/api/v1/inventory/'+path)
            self.assertEqual(result.status_code,200);self.assertEqual(result.data['count'],0)
            self.assertNotIn('SYN-PRIVATE-SOURCE',str(result.data))
        self.assertEqual(client.get('/api/v1/inventory/custody/scope/',{'stock':str(self.stock.pk),'location':str(self.loc.pk)}).status_code,403)
        self.assertEqual(client.get('/api/v1/inventory/custody/scope/',{'stock':str(self.stock.pk),'location':str(self.loc2.pk)}).status_code,404)
        self.assertEqual(client.post('/api/v1/inventory/warehouses/',{},format='json').status_code,403)

    def test_h_stale_versions_balances_and_superseded_plans(self):
        self.posted(self.body('OPENING','0'));request=self.create_operation(self.body('IN'))
        verified=self.step(request,'verify');self.step(request,'confirm',expected=(412,))
        receipt=self.step(self.step(self.step(verified,'confirm'),'approve','reviewer'),'record','recorder')
        plan=self.plan();inspected=self.inspect(receipt,plan);self.review(inspected)
        self.plan(revision=2,reference=plan['reference']);self.release(inspected,expected=(400,))
        # A fresh current inspection is still stale once held custody changes.
        current=self.clients['recorder'].get('/api/v1/inventory/quality/plans/').data['results'][0]
        again=self.inspect(receipt,current,previous=inspected);self.review(again)
        self.posted(self.body('OPENING','0',location=self.loc2));body=self.body('TRANSFER','1');body['lines'][0]['destination']=str(self.loc2.pk);self.posted(body)
        self.release(again,expected=(400,412))

    def test_i_unknown_coverage_partial_disposition_and_default_disabled(self):
        state=self.custody_state();self.assertEqual(state['opening_status'],'UNKNOWN');self.assertIsNone(state['partitions']['HELD']['quantity'])
        self.create_operation(self.body('OUT','1',quality='RELEASED'),expected=(400,))
        _,receipt=self.incoming();plan=self.plan();entry=LedgerEntry.objects.get(transaction_id=receipt['ledger_transaction'])
        balance=BalanceProjection.objects.get(stock=self.stock,quality='HELD')
        self.api('quality/inspections/',{'plan':plan['id'],'source_entry':str(entry.pk),'quantity':'7','balance_version':balance.version,'physical_evidence':'synthetic:indistinguishable','observations':{'identity':True},'reason':'Synthetic partial attempt','evidence_reference':'synthetic:partial'},expected=(400,))
        mode=self.clients['recorder'].get('/api/v1/inventory/quality/mode/').data
        self.assertFalse(mode['partial_pool_release']);self.assertFalse(mode['disposition_available']);self.assertFalse(mode['operational_posting'])
        with override_settings(SYNTHETIC_LEDGER_ENABLED=False):
            self.assertEqual(self.clients['recorder'].get('/api/v1/inventory/custody/balances/').status_code,403)
            self.assertFalse(self.clients['recorder'].get('/api/v1/inventory/quality/mode/').data['synthetic_enabled'])

    def test_j_config_identity_and_independent_opening_correction(self):
        warehouse=self.api('warehouses/',{'code':'E2E-NEW','name':'Synthetic configured warehouse','custody_department':str(self.department.pk),'reason':'Synthetic configuration'})
        location=self.api('locations/',{'warehouse':warehouse['id'],'code':'E2E-LOCATION','name':'Synthetic location','reason':'Synthetic configuration'})
        identity=self.api('identities/',{'warehouse':warehouse['id'],'location':location['id'],'material':str(self.material.pk),'unit':str(self.unit.pk),'kind':'BATCH','ownership':'UNRESOLVED','source_system':'synthetic:e2e-identity','source_reference':str(uuid.uuid4()),'reason':'Synthetic identity registration'})
        self.assertTrue(identity['reference'].startswith('STK-'));self.assertFalse(BalanceProjection.objects.filter(stock_id=identity['id']).exists())
        opening=self.posted(self.body('OPENING'))
        correction=self.prepared(self.create_operation(self.body('OPENING_CORRECTION','12',related=opening['ledger_transaction'])))
        self.step(correction,'approve','recorder',expected=(403,))
        # Existing held-removal restrictions remain; positive compensation is independently approved.
        corrected=self.step(self.step(correction,'approve','reviewer'),'record','recorder')
        self.assertTrue(corrected['stock_movement_posted']);self.assertEqual(Decimal(corrected['lines'][0]['original_quantity']),10)
        self.assertEqual(Decimal(self.custody_state()['partitions']['HELD']['quantity']),12)

    def test_k_return_reconciliation_and_authorized_adjustment(self):
        self.ready();issue=self.posted(self.body('OUT','3',quality='RELEASED'))
        original=LedgerTransaction.objects.get(pk=issue['ledger_transaction']).lines.get()
        body=self.body('RETURN','2',related=issue['ledger_transaction']);body['lines'][0]['original_line']=str(original.pk)
        returned=self.posted(body)
        self.assertTrue(returned['stock_movement_posted']);self.assertEqual(Decimal(self.custody_state()['partitions']['HELD']['quantity']),2)
        count=self.prepared(self.create_operation(self.body('COUNT','8',quality='RELEASED')))
        self.assertEqual(Decimal(count['lines'][0]['difference']),1)
        adjusted=self.posted(self.body('ADJUSTMENT','8',quality='RELEASED',count_session=count['id']))
        self.assertTrue(adjusted['stock_movement_posted'])
        self.assertEqual(Decimal(self.custody_state()['partitions']['RELEASED']['quantity']),7)
        self.assertEqual(Decimal(self.custody_state()['partitions']['HELD']['quantity']),3)
