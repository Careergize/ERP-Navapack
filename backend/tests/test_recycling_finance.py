import copy
import uuid
from django.contrib.auth.models import Permission
from django.test import TransactionTestCase
from apps.inventory.ledger_models import LedgerEntry, LedgerTransaction, BalanceProjection
from apps.rehearsal.models import RehearsalRevision
from tests import test_rehearsal


class RecyclingFinanceTests(TransactionTestCase):
    data = test_rehearsal.RehearsalTests.data
    create = test_rehearsal.RehearsalTests.create
    job = test_rehearsal.RehearsalTests.job
    step = test_rehearsal.RehearsalTests.step

    def setUp(self):
        test_rehearsal.RehearsalTests.setUp(self)

    def completed_stage(self):
        job = self.job().data
        for action, data in [('review',{}),('issue',{'quantity':'10','available_quantity':'10'}),
            ('start',{'line':0,'stage':'PACKING','machine':'synthetic:packing','operator':'synthetic:operator','input_quantity':'10'}),
            ('complete',{'output_quantity':'7','waste':'2','rejection':'1','line':0,'stage':'PACKING'})]:
            response = self.step(job,action,data)
            self.assertEqual(response.status_code,200,response.data)
            job = response.data
        return job

    def batch(self, **extra):
        return {'line':0,'stage':'PACKING','unit':str(self.unit.pk),'classification':'PROCESS_WASTE',
            'intake':'1.500001','recovered':'1.000001','rejected':'0.25','disposed':'0.25',
            'batch_reference':'synthetic:recycle-one',**extra}

    def test_exact_recycling_persists_replays_and_never_credits_stock(self):
        before=[m.objects.count() for m in (LedgerEntry,LedgerTransaction,BalanceProjection)]
        job=self.completed_stage(); old=copy.deepcopy(job['snapshot']); key=str(uuid.uuid4())
        result=self.step(job,'recycle',self.batch(),key=key)
        self.assertEqual(result.status_code,200,result.data)
        self.assertEqual(result.data['status'],job['status'])
        event=result.data['snapshot']['recycling'][0]
        self.assertEqual(event['recovered'],'1.000001')
        self.assertFalse(event['available_stock_credit'])
        self.assertEqual(self.step(job,'recycle',self.batch(),key=key).data,result.data)
        self.assertEqual(self.step(job,'recycle',self.batch()).status_code,412)
        reread=self.client.get(f"/api/v1/rehearsal/jobs/{job['id']}/")
        self.assertEqual(reread.data['snapshot']['recycling'],result.data['snapshot']['recycling'])
        self.assertEqual(RehearsalRevision.objects.get(job_id=job['id'],number=job['version']).snapshot['state'],old)
        self.assertEqual([m.objects.count() for m in (LedgerEntry,LedgerTransaction,BalanceProjection)],before)
        report=self.client.get('/api/v1/rehearsal/jobs/dashboard/').data
        self.assertEqual(report['recycling_by_unit'][0]['intake'],'1.500001')
        self.assertEqual(report['recycling_by_unit'][0]['recovered'],'1.000001')

    def test_recycling_rejects_overallocation_conversion_unbalanced_and_duplicate_batch(self):
        job=self.completed_stage()
        self.assertEqual(self.step(job,'recycle',self.batch(unit=str(self.ctr.pk))).status_code,400)
        self.assertEqual(self.step(job,'recycle',self.batch(recovered='0')).status_code,400)
        self.assertEqual(self.step(job,'recycle',self.batch(intake='3',recovered='2.5')).status_code,409)
        result=self.step(job,'recycle',self.batch());self.assertEqual(result.status_code,200,result.data)
        self.assertEqual(self.step(result.data,'recycle',self.batch()).status_code,409)
        self.assertEqual(self.step(result.data,'recycle',self.batch(batch_reference='synthetic:two')).status_code,409)

    def test_recycling_requires_completed_source_and_owner_scope(self):
        job=self.job().data
        self.assertEqual(self.step(job,'recycle',self.batch()).status_code,409)
        self.client.force_authenticate(self.other)
        self.other.user_permissions.add(Permission.objects.get(content_type__app_label='rehearsal',codename='use_simulation'))
        self.assertEqual(self.step(job,'recycle',self.batch()).status_code,404)

    def test_reports_keep_kinds_currencies_permissions_and_cancelled_drafts_separate(self):
        costing=self.create('COSTING');self.assertEqual(costing.status_code,201,costing.data)
        self.create('QUOTATION')
        self.create('SALES_ORDER')
        rows=self.client.get('/api/v1/commercial/documents/',{'kind':'COSTING'})
        self.assertEqual(rows.data['count'],1)
        self.assertTrue(all(r['kind']=='COSTING' for r in rows.data['results']))
        self.assertEqual(self.client.get('/api/v1/commercial/documents/',{'kind':'invented'}).status_code,400)
        report=self.client.get('/api/v1/rehearsal/jobs/dashboard/')
        self.assertEqual(report.status_code,200,report.data)
        summaries=report.data['commercial_by_party']
        self.assertEqual({r['kind'] for r in summaries},{'COSTING','QUOTATION','SALES_ORDER'})
        self.assertTrue(all(r['currency']=='UGX' and not r['authoritative'] for r in summaries))
        self.assertIsNone(report.data['financial_payable'])
        self.assertIsNone(report.data['operational_available_stock'])
        costing_summary=next(r for r in summaries if r['kind']=='COSTING')
        self.assertEqual(costing_summary['estimated_production_cost'],'4.02')
        self.assertEqual(costing_summary['estimated_margin'],'-1.00')
        self.assertTrue(all(r['estimated_margin'] is None for r in summaries if r['kind']!='COSTING'))
        notifications=report.data['notifications']
        self.assertTrue(all(r['kind']=='SYNTHETIC_PRODUCTION' for r in notifications))

    def test_month_filter_validation_and_empty_month_preserve_scope(self):
        self.user.user_permissions.add(Permission.objects.get(content_type__app_label='inventory',codename='view_synthetic_custody'))
        response=self.client.get('/api/v1/inventory/custody/movements/',{'month':'2026-99'})
        self.assertEqual(response.status_code,400,response.data)
        response=self.client.get('/api/v1/inventory/custody/movements/',{'month':'2026-10','item_type':'variant'})
        self.assertEqual(response.status_code,200,response.data)
        self.assertEqual(response.data['count'],0)
