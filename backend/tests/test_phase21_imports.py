"""Permanent adversarial regressions for exit-audit F1/F3/F5/F6/F7."""
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import patch
from django.db import transaction, DatabaseError, connections
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from tests.test_phase2 import Phase2Tests as BasePhase2Tests
from apps.accounts.models import User
from apps.masters.models import Customer, Product, ProductVariant, Department
from apps.imports.models import ImportBatch, ImportRow, ImportReview
from apps.core.models import AuditEvent


class ImportRemediationTests(BasePhase2Tests):
    def post(self,path,data=None,**kwargs):
        return super().post(path,data or {},**kwargs)

    # Only the regression methods below are discovered on this subclass.
    def mapped_review(self,batch,mapping):
        row=ImportRow.objects.get(batch_id=batch['id'])
        result=self.post(f"imports/{batch['id']}/review/",{'mapping':mapping,
            'decisions':{str(row.pk):{'action':'create'}}},version=batch['version'])
        self.assertEqual(result.status_code,200,result.data)
        self.assertEqual(result.data['review'][0]['errors'],{})
        return result.data

    def variant_review(self):
        product=self.post('products/',{'name':'Reviewed product','code':'P1','unit':str(self.unit.pk)}).data
        batch=self.stage(b'ID,Name,Product,Unit,Category\nv1,Variant,P1,kg,packing\n',target='finished-goods')
        return product,self.mapped_review(batch,{'source_id':'ID','name':'Name','product':'Product','unit':'Unit','category':'Category'})

    def test_reviewed_reference_cannot_rebind_after_code_reuse(self):
        product,batch=self.variant_review()
        changed=self.client.patch(f"/api/v1/products/{product['id']}/",{'code':'OLD'},format='json',HTTP_IF_MATCH='"1"',HTTP_IDEMPOTENCY_KEY='rename')
        self.assertEqual(changed.status_code,200,changed.data)
        self.post('products/',{'name':'Replacement','code':'P1','unit':str(self.unit.pk)})
        response=self.post(f"imports/{batch['id']}/approve/",version=batch['version'])
        self.assertEqual(response.status_code,409,response.data)
        self.assertEqual(response.data['error']['code'],'stale_review')
        self.assertFalse(ProductVariant.objects.exists())

    def test_reference_nonversioned_edit_invalidates_review(self):
        _,batch=self.variant_review()
        self.unit.name='Changed without version';self.unit.save(update_fields=['name'])
        response=self.post(f"imports/{batch['id']}/approve/",version=2)
        self.assertEqual(response.status_code,409,response.data)

    def test_new_duplicate_requires_rereview_even_with_prior_acknowledgment(self):
        self.customer(name='Client item')
        batch=self.review(self.stage(),acknowledge_duplicates=True)
        self.customer(name='Client item')
        response=self.post(f"imports/{batch['id']}/approve/",version=2)
        self.assertEqual(response.status_code,409,response.data)
        rer=self.review(batch,acknowledge_duplicates=True)
        result=self.post(f"imports/{batch['id']}/approve/",version=rer['version'])
        self.assertEqual(result.status_code,200,result.data)
        self.assertEqual(ImportReview.objects.count(),2)

    def test_all_within_batch_duplicate_candidates_are_visible(self):
        batch=self.review(self.stage(b'ID,Name\na,Same name\nb,Same name\nc,Same name\n'),acknowledge_duplicates=True)
        rows=batch['review']
        identities={r['row_id'] for r in rows}
        for row in rows:
            self.assertEqual({c['row_id'] for c in row['candidates']},identities-{row['row_id']})
            self.assertEqual(row['errors'],{})
        self.assertEqual(self.post(f"imports/{batch['id']}/approve/",version=2).status_code,200)

    def test_applied_plan_exact_review_history_and_retry(self):
        _,batch=self.variant_review()
        reviewed=ImportReview.objects.get(pk=batch['canonical_review'])
        applied=self.post(f"imports/{batch['id']}/approve/",version=2,key='apply-exact')
        self.assertEqual(applied.status_code,200,applied.data)
        plan=applied.data['applied_plan']
        self.assertEqual(plan['plan'],reviewed.plan)
        self.assertEqual(plan['plan_hash'],reviewed.plan_hash)
        variant=ProductVariant.objects.get()
        self.assertEqual(str(variant.product_id),reviewed.plan['rows'][0]['proposed']['product'])
        self.assertEqual(self.post(f"imports/{batch['id']}/approve/",version=2,key='apply-exact').data,applied.data)
        self.assertEqual(self.client.get(f"/api/v1/imports/{batch['id']}/reviews/").data['count'],1)

    def test_canonical_review_is_database_immutable(self):
        batch=self.review(self.stage())
        for operation in [lambda:ImportReview.objects.filter(pk=batch['canonical_review']).update(plan={}),
                          lambda:ImportReview.objects.filter(pk=batch['canonical_review']).delete()]:
            with self.assertRaises(DatabaseError),transaction.atomic(): operation()

    def test_user_uuid_reference_applies_and_user_change_requires_review(self):
        data=f'ID,Name,Manager\ndep-1,Imported department,{self.user.pk}\n'.encode()
        batch=self.mapped_review(self.stage(data,target='departments'),{'source_id':'ID','name':'Name','manager':'Manager'})
        self.assertEqual(batch['review'][0]['proposed']['manager'],str(self.user.pk))
        response=self.post(f"imports/{batch['id']}/approve/",version=2)
        self.assertEqual(response.status_code,200,response.data)
        self.assertEqual(Department.objects.get().manager_id,self.user.pk)

    def test_bad_user_reference_is_row_error(self):
        batch=self.stage(b'ID,Name,Manager\nd1,Department,not-a-uuid\n',target='departments')
        row=ImportRow.objects.get(batch_id=batch['id'])
        response=self.post(f"imports/{batch['id']}/review/",{'mapping':{'source_id':'ID','name':'Name','manager':'Manager'},'decisions':{str(row.pk):{'action':'create'}}},version=1)
        self.assertEqual(response.status_code,200,response.data)
        self.assertTrue(response.data['review'][0]['errors'])

    def test_user_status_change_invalidates_review(self):
        manager=User.objects.create_user('manager@example.com')
        batch=self.mapped_review(self.stage(f'ID,Name,Manager\ndep-1,Department,{manager.pk}\n'.encode(),target='departments'),
            {'source_id':'ID','name':'Name','manager':'Manager'})
        manager.is_active=False;manager.save()
        response=self.post(f"imports/{batch['id']}/approve/",version=2)
        self.assertEqual(response.status_code,409,response.data)
        self.assertFalse(Department.objects.exists())

    def test_legacy_review_requires_new_canonical_review(self):
        batch=self.review(self.stage())
        ImportBatch.objects.filter(pk=batch['id']).update(canonical_review=None)
        self.assertEqual(self.post(f"imports/{batch['id']}/approve/",version=2).status_code,409)

    def test_concurrent_reference_write_cannot_rebind_during_application(self):
        from apps.imports.views import canonical_plan
        product,batch=self.variant_review()
        checked=Event();release=Event();started=Event()
        def gated(*args,**kwargs):
            plan=canonical_plan(*args,**kwargs)
            checked.set()
            if not release.wait(10): raise RuntimeError('Test coordination timeout')
            return plan
        def approve():
            try:
                client=APIClient();client.force_authenticate(User.objects.get(pk=self.user.pk))
                return self.post(f"imports/{batch['id']}/approve/",version=2,client=client).status_code
            finally: connections.close_all()
        def rename():
            try:
                client=APIClient();client.force_authenticate(User.objects.get(pk=self.user.pk));started.set()
                return client.patch(f"/api/v1/products/{product['id']}/",{'code':'CHANGED'},format='json',HTTP_IF_MATCH='"1"',HTTP_IDEMPOTENCY_KEY='concurrent-rename').status_code
            finally: connections.close_all()
        with patch('apps.imports.views.canonical_plan',side_effect=gated),ThreadPoolExecutor(max_workers=2) as pool:
            approval=pool.submit(approve)
            try:
                self.assertTrue(checked.wait(10));change=pool.submit(rename)
                self.assertTrue(started.wait(10))
            finally: release.set()
            self.assertEqual(approval.result(),200)
            self.assertEqual(change.result(),200)
        self.assertEqual(str(ProductVariant.objects.get().product_id),product['id'])

    def test_apply_failure_rolls_back_plan_master_results_and_audit(self):
        batch=self.review(self.stage())
        before=AuditEvent.objects.count()
        with patch('apps.imports.views.record_event',side_effect=RuntimeError('Synthetic audit failure')):
            result=self.post(f"imports/{batch['id']}/approve/",version=2)
        self.assertEqual(result.status_code,500)
        self.assertFalse(Customer.objects.exists())
        stored=ImportBatch.objects.get();self.assertEqual(stored.status,'reviewed');self.assertIsNone(stored.applied_plan)
        self.assertIsNone(ImportRow.objects.get().result_id)
        self.assertEqual(AuditEvent.objects.count(),before)

    def test_nullable_process_stage_uses_explicit_schema(self):
        _,response=self.revision(processes=[{'name':'Fixed','basis':'fixed','unit':str(self.unit.pk),'stage':None,'rate':'0'}])
        self.assertEqual(response.status_code,201,response.data)
        self.assertIsNone(response.data['processes'][0]['stage'])
        _,bad=self.revision(processes=[{'name':'Fixed','basis':'fixed','unit':str(self.unit.pk),'stage':'bad-uuid'}])
        self.assertEqual(bad.status_code,400,bad.data)

    def test_malformed_resource_uuid_commands_use_error_envelope(self):
        for path in ['customers/not-a-uuid/','products/not-a-uuid/']:
            result=self.client.patch('/api/v1/'+path,{'name':'No'},format='json',HTTP_IF_MATCH='"1"',HTTP_IDEMPOTENCY_KEY=uuid.uuid4().hex)
            self.assertEqual(result.status_code,404,result.data)
            self.assertIn('request_id',result.data['error'])
        for path in ['imports/bad/review/','imports/bad/approve/','prospects/bad/promote/','models/bad/revisions/']:
            result=self.post(path,{'create_customer':True} if 'promote' in path else {},version=1)
            self.assertEqual(result.status_code,404,result.data)

    def test_auth_contract_email_and_plural_roles_remains_strict(self):
        client=APIClient()
        wrong=client.post('/api/v1/auth/login/',{'username':self.user.email,'password':'long-password'},format='json')
        self.assertEqual(wrong.status_code,400)
        right=client.post('/api/v1/auth/login/',{'email':self.user.email,'password':'long-password'},format='json')
        self.assertEqual(right.status_code,200,right.data)
        self.assertIn('roles',right.data['user']);self.assertIn('permissions',right.data['user'])
        self.assertNotIn('role',right.data['user'])


# Reuse fixture helpers, without running inherited baseline tests twice.
for _name in list(vars(BasePhase2Tests)):
    if _name.startswith('test_'):
        setattr(ImportRemediationTests,_name,None)
del BasePhase2Tests
