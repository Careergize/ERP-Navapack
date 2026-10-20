import io
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection, connections, transaction, DatabaseError, IntegrityError
from django.test import TransactionTestCase
from rest_framework.test import APIClient
from apps.masters.models import Customer, Prospect, Unit, Material, Product, ProductVariant
from apps.specifications.models import ProductModelRevision, RecipeLine
from apps.imports.models import ImportBatch, ImportRow
from apps.imports.readers import read_source
from apps.core.models import AuditEvent, IdempotencyRecord
from rest_framework.exceptions import ValidationError


class Phase2Tests(TransactionTestCase):
    def setUp(self):
        self.assertEqual(connection.vendor,'postgresql')
        self.user=get_user_model().objects.create_superuser('phase2@example.com','long-password')
        self.client=APIClient(); self.client.force_authenticate(self.user)
        self.unit=Unit.objects.create(name='Kilogram',code='kg',dimension='mass',created_by=self.user,updated_by=self.user)

    def post(self,path,data,key=None,version=None,client=None,format='json'):
        headers={'HTTP_IDEMPOTENCY_KEY':key or str(uuid.uuid4())}
        if version is not None: headers['HTTP_IF_MATCH']=f'"{version}"'
        return (client or self.client).post('/api/v1/'+path,data,format=format,**headers)

    def customer(self,**extra):
        response=self.post('customers/',{'name':'Acme',**extra})
        self.assertEqual(response.status_code,201,response.data)
        return response.data

    def stage(self,content=b'ID,Name,Opening\nsrc-1,Client item,\n',kind='client',target='customers'):
        response=self.post('imports/',{'file':SimpleUploadedFile('client.csv',content,content_type='text/csv'), 'target':target,'source_system':'client-register','source_kind':kind,'source_attestation':'Provided client register for review'},format='multipart')
        self.assertEqual(response.status_code,201,response.data)
        return response.data

    def review(self,batch,action='create',**choice):
        rows=ImportRow.objects.filter(batch_id=batch['id'])
        response=self.post(f"imports/{batch['id']}/review/",{'mapping':{'source_id':'ID','name':'Name'},'decisions':{str(r.pk):{'action':action,**choice} for r in rows}},version=batch['version'])
        self.assertEqual(response.status_code,200,response.data)
        return response.data

    def test_master_create_update_and_audit(self):
        obj=self.customer(contact_person='Contact')
        response=self.client.patch(f"/api/v1/customers/{obj['id']}/",{'name':'Renamed','is_active':False},format='json',HTTP_IF_MATCH='"1"',HTTP_IDEMPOTENCY_KEY='edit')
        self.assertEqual(response.status_code,200,response.data)
        self.assertEqual(response.data['version'],2)
        self.assertEqual(response['ETag'],'"2"')
        self.assertEqual(AuditEvent.objects.filter(entity_id=obj['id']).count(),2)
        self.assertEqual(AuditEvent.objects.get(action='masters.change_customer').actor,self.user)

    def test_creation_retry_and_payload_conflict(self):
        first=self.post('customers/',{'name':'A'},key='retry')
        again=self.post('customers/',{'name':'A'},key='retry')
        self.assertEqual(first.data,again.data)
        self.assertEqual(Customer.objects.count(),1)
        self.assertEqual(self.post('customers/',{'name':'B'},key='retry').status_code,409)

    def test_names_not_unique_but_codes_and_sources_are(self):
        self.customer(code='C1',source_system='client',source_id='1')
        self.customer()
        self.assertEqual(self.post('customers/',{'name':'Other','code':'c1'}).status_code,400)
        self.assertEqual(self.post('customers/',{'name':'Other','source_system':'client','source_id':'1'}).status_code,400)
        with self.assertRaises(IntegrityError),transaction.atomic():
            Customer.objects.create(name='Direct',code='c1',created_by=self.user,updated_by=self.user)

    def test_source_pairs_and_server_fields(self):
        for payload in [{'source_id':'orphan'},{'created_by':str(self.user.pk)},{'opening_stock':'0'},{'name':'   '}]:
            self.assertEqual(self.post('customers/',{'name':'A',**payload}).status_code,400)

    def test_permissions_and_inactive_actor(self):
        user=get_user_model().objects.create_user('none@example.com','long-password')
        c=APIClient(); c.force_authenticate(user)
        self.assertEqual(self.post('customers/',{'name':'No'},client=c).status_code,403)
        self.assertEqual(c.get('/api/v1/customers/').status_code,403)
        user.user_permissions.add(Permission.objects.get(content_type__app_label='masters',codename='add_customer'))
        user=get_user_model().objects.get(pk=user.pk); c.force_authenticate(user)
        self.assertEqual(self.post('customers/',{'name':'Yes'},client=c).status_code,201)
        user.is_active=False; user.save(); c.force_authenticate(user)
        self.assertEqual(self.post('customers/',{'name':'No'},client=c).status_code,403)

    def test_missing_stale_precondition_and_no_delete(self):
        obj=self.customer()
        uri=f"/api/v1/customers/{obj['id']}/"
        self.assertEqual(self.client.patch(uri,{'name':'X'},format='json').status_code,428)
        self.assertEqual(self.client.patch(uri,{'name':'X'},format='json',HTTP_IF_MATCH='"2"',HTTP_IDEMPOTENCY_KEY='stale').status_code,412)
        self.assertEqual(self.client.delete(uri).status_code,403)

    def test_pagination_filter_search_ordering(self):
        self.customer(name='Zulu'); self.customer(name='Alpha',is_active=False)
        result=self.client.get('/api/v1/customers/?page_size=1&ordering=name')
        self.assertEqual(result.data['count'],2); self.assertIsNotNone(result.data['next'])
        self.assertEqual(result.data['results'][0]['name'],'Alpha')
        self.assertEqual(self.client.get('/api/v1/customers/?is_active=true&search=Zulu').data['count'],1)
        self.assertEqual(self.client.get('/api/v1/customers/?is_active=false').data['count'],1)

    def test_units_and_product_variant_separation(self):
        product=self.post('products/',{'name':'Generic bag','unit':str(self.unit.pk)})
        self.assertEqual(product.status_code,201,product.data)
        variant=self.post('finished-goods/',{'name':'Specific','product':product.data['id'],'unit':str(self.unit.pk),'category':'packing','pieces':20})
        self.assertEqual(variant.status_code,201,variant.data)
        self.assertNotEqual(product.data['id'],variant.data['id'])
        self.assertEqual(variant.data['product'],product.data['id'])
        self.unit.is_active=False; self.unit.save()
        self.assertEqual(self.post('raw-materials/',{'name':'Grade','unit':str(self.unit.pk),'category':'virgin'}).status_code,400)

    def test_negative_minimum_invalid_units_and_categories(self):
        for changes in [{'min_level':'-1'},{'unit':'unknown'},{'category':'invented'}]:
            self.assertEqual(self.post('raw-materials/',{'name':'Grade','unit':str(self.unit.pk),'category':'virgin',**changes}).status_code,400)

    def test_prospect_explicit_promotion_and_retry(self):
        customer=self.customer()
        prospect=self.post('prospects/',{'name':'Acme'}).data
        path=f"prospects/{prospect['id']}/promote/"
        self.assertEqual(self.post(path,{},version=1).status_code,400)
        result=self.post(path,{'existing_customer_id':customer['id']},version=1,key='promote')
        self.assertEqual(result.status_code,200,result.data)
        self.assertEqual(result.data['linked_customer'],customer['id'])
        self.assertEqual(self.post(path,{'existing_customer_id':customer['id']},version=1,key='promote').data,result.data)
        self.assertEqual(self.post(path,{'create_customer':True},version=2).status_code,409)
        self.assertEqual(Customer.objects.count(),1)

    def test_promotion_create_does_not_match_name(self):
        self.customer()
        prospect=self.post('prospects/',{'name':'Acme'}).data
        result=self.post(f"prospects/{prospect['id']}/promote/",{'create_customer':True},version=1)
        self.assertEqual(result.status_code,200,result.data)
        self.assertEqual(Customer.objects.count(),2)

    def revision(self,**extra):
        model=self.post('models/',{'name':'Custom model'})
        self.assertEqual(model.status_code,201,model.data)
        material=Material.objects.create(name='Client grade',category='virgin',unit=self.unit,created_by=self.user,updated_by=self.user)
        data={'name':'Model r1','default_unit':str(self.unit.pk),'recipe_mode':'quantities','recipe':[{'material':str(material.pk),'unit':str(self.unit.pk),'quantity':'10','cost_group':'material'}],**extra}
        result=self.post(f"models/{model.data['id']}/revisions/",data,version=1)
        return model,result

    def test_revision_atomic_creation_and_history(self):
        model,result=self.revision()
        self.assertEqual(result.status_code,201,result.data)
        self.assertEqual(result.data['number'],1); self.assertTrue(result.data['sealed'])
        again=self.post(f"models/{model.data['id']}/revisions/",{'name':'r2','default_unit':str(self.unit.pk),'recipe_mode':'quantities'},version=2)
        self.assertEqual(again.status_code,201,again.data)
        self.assertEqual(again.data['number'],2)
        listing=self.client.get(f"/api/v1/models/{model.data['id']}/revisions/")
        self.assertEqual(listing.data['count'],2)
        self.assertEqual(self.client.patch(f"/api/v1/model-revisions/{result.data['id']}/",{}).status_code,403)

    def test_database_revision_and_children_immutable(self):
        _,result=self.revision(); self.assertEqual(result.status_code,201,result.data)
        rev=ProductModelRevision.objects.get(pk=result.data['id'])
        for operation in [lambda: ProductModelRevision.objects.filter(pk=rev.pk).update(name='Changed'), lambda: RecipeLine.objects.filter(revision=rev).update(quantity=99),lambda: RecipeLine.objects.filter(revision=rev).delete(),lambda: RecipeLine.objects.create(revision=rev,material=Material.objects.first(),unit=self.unit,quantity=1,cost_group='material')]:
            with self.assertRaises(DatabaseError),transaction.atomic(): operation()

    def test_invalid_revision_rolls_back(self):
        _,result=self.revision(recipe_mode='percentages',batch_quantity='100',batch_unit=str(self.unit.pk))
        self.assertEqual(result.status_code,400,result.data)
        self.assertFalse(ProductModelRevision.objects.exists())
        self.assertFalse(RecipeLine.objects.exists())

    def test_audit_failure_rolls_back_master_and_retry(self):
        with patch('apps.core.commands.record_event',side_effect=RuntimeError('failure')):
            response=self.post('customers/',{'name':'Rollback'},key='rollback')
        self.assertEqual(response.status_code,500)
        self.assertFalse(Customer.objects.exists())
        self.assertFalse(IdempotencyRecord.objects.filter(key='rollback').exists())

    def test_import_review_apply_preserves_unknown_opening(self):
        batch=self.review(self.stage())
        self.assertEqual(batch['review'][0]['errors'],{},batch['review'])
        result=self.post(f"imports/{batch['id']}/approve/",{},version=batch['version'],key='apply')
        self.assertEqual(result.status_code,200,result.data)
        self.assertEqual(Customer.objects.get().source_id,'src-1')
        row=ImportRow.objects.get(); self.assertEqual(row.raw['Opening'],''); self.assertIsNotNone(row.result_id)
        self.assertEqual(self.post(f"imports/{batch['id']}/approve/",{},version=batch['version'],key='apply').data,result.data)
        self.assertEqual(Customer.objects.count(),1)
        self.assertEqual(AuditEvent.objects.filter(action='imports.approve_importbatch').count(),1)

    def test_duplicate_file_and_duplicate_source(self):
        batch=self.stage()
        response=self.post('imports/',{'file':SimpleUploadedFile('client.csv',b'ID,Name,Opening\nsrc-1,Client item,\n'),'target':'customers','source_system':'other','source_kind':'client','source_attestation':'client'},format='multipart')
        self.assertEqual(response.status_code,409,response.data)
        review=self.review(batch)
        self.assertEqual(self.post(f"imports/{batch['id']}/approve/",{},version=review['version']).status_code,200)
        second=self.review(self.stage(b'ID,Name\nsrc-1,Same source\n'))
        self.assertTrue(second['review'][0]['errors'])
        self.assertEqual(self.post(f"imports/{second['id']}/approve/",{},version=second['version']).status_code,400)

    def test_ambiguous_names_require_acknowledgment(self):
        self.customer(name='Client item')
        review=self.review(self.stage())
        self.assertIn('duplicates',review['review'][0]['errors'])
        self.assertEqual(self.post(f"imports/{review['id']}/approve/",{},version=review['version']).status_code,400)
        review=self.review(review,acknowledge_duplicates=True)
        self.assertEqual(review['review'][0]['errors'],{},review['review'])

    def test_import_demo_blocked_and_review_required(self):
        batch=self.stage(kind='demo')
        self.assertEqual(self.post(f"imports/{batch['id']}/approve/",{},version=1).status_code,409)
        batch=self.review(batch)
        self.assertEqual(self.post(f"imports/{batch['id']}/approve/",{},version=batch['version']).status_code,400)
        self.assertFalse(Customer.objects.exists())

    def test_invalid_columns_units_and_repeated_sources(self):
        batch=self.stage(b'ID,Name\nx,A\nx,B\n')
        review=self.review(batch)
        self.assertTrue(all(r['errors'] for r in review['review']))
        bad=self.post(f"imports/{batch['id']}/review/",{'mapping':{'source_id':'missing','name':'Name'}},version=review['version'])
        self.assertEqual(bad.status_code,200,bad.data)
        self.assertIn('columns',bad.data['review'][0]['errors'])

    def test_import_approval_rollback(self):
        batch=self.review(self.stage())
        with patch('apps.imports.views.record_event',side_effect=RuntimeError('injected')):
            response=self.post(f"imports/{batch['id']}/approve/",{},version=batch['version'],key='fail-apply')
        self.assertEqual(response.status_code,500)
        self.assertFalse(Customer.objects.exists()); self.assertIsNone(ImportRow.objects.get().result_id)
        self.assertEqual(ImportBatch.objects.get().status,'reviewed')

    def test_import_source_evidence_immutable(self):
        self.stage()
        with self.assertRaises(DatabaseError),transaction.atomic(): ImportRow.objects.all().update(raw={'changed':'bad'})
        with self.assertRaises(DatabaseError),transaction.atomic(): ImportBatch.objects.all().update(source_kind='demo')

    def test_reader_rejects_invalid_and_formula_sources(self):
        for data,name in [(b'A,A\n1,2','x.csv'),(b'bad','x.xls'),(b'not zip','x.xlsx')]:
            with self.assertRaises(ValidationError): read_source(data,name)

    def test_concurrent_import_approval_same_key(self):
        batch=self.review(self.stage()); barrier=Barrier(2)
        def worker():
            connections.close_all()
            try:
                user=get_user_model().objects.get(pk=self.user.pk)
                c=APIClient(); c.force_authenticate(user); barrier.wait(timeout=10)
                response=self.post(f"imports/{batch['id']}/approve/",{},version=batch['version'],key='concurrent',client=c)
                return response.status_code,response.data
            finally: connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(lambda _:worker(),range(2)))
        self.assertEqual([r[0] for r in results],[200,200],results)
        self.assertEqual(results[0][1],results[1][1]); self.assertEqual(Customer.objects.count(),1)

    def test_concurrent_import_approval_different_keys(self):
        batch=self.review(self.stage()); barrier=Barrier(2)
        def worker(i):
            connections.close_all()
            try:
                c=APIClient(); c.force_authenticate(get_user_model().objects.get(pk=self.user.pk)); barrier.wait(timeout=10)
                return self.post(f"imports/{batch['id']}/approve/",{},version=batch['version'],key=f'competing-{i}',client=c).status_code
            finally: connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(worker,range(2)))
        self.assertEqual(sorted(results),[200,412]); self.assertEqual(Customer.objects.count(),1)


    def test_configurable_route_and_process_linkage(self):
        dept=self.post('departments/',{'name':'Client department'}).data
        route={'source_id':'cut','name':'Client cutting','sequence':2,'required':True,'kind':'production','department':dept['id'],'input_unit':str(self.unit.pk),'output_unit':str(self.unit.pk),'waste_unit':str(self.unit.pk),'instructions':'Client instructions'}
        _,result=self.revision(routing=[route],processes=[{'name':'Cutting','basis':'per batch','unit':str(self.unit.pk),'source_stage_id':'cut','rate':'12.5'}])
        self.assertEqual(result.status_code,201,result.data)
        self.assertEqual(result.data['processes'][0]['stage'],result.data['routing'][0]['id'])
        self.assertEqual(result.data['routing'][0]['sequence'],2)
        self.assertEqual(result.data['reference_snapshot']['routing'][0]['department']['name'],'Client department')

    def test_import_update_stale_target_blocks_apply(self):
        customer=self.customer(source_system='client-register',source_id='src-1')
        batch=self.review(self.stage(),action='update',target_id=customer['id'],expected_version=1,acknowledge_duplicates=True)
        self.assertEqual(batch['review'][0]['errors'],{},batch['review'])
        response=self.client.patch(f"/api/v1/customers/{customer['id']}/",{'phone':'changed'},format='json',HTTP_IF_MATCH='"1"',HTTP_IDEMPOTENCY_KEY='change-target')
        self.assertEqual(response.status_code,200,response.data)
        response=self.post(f"imports/{batch['id']}/approve/",{},version=batch['version'])
        self.assertEqual(response.status_code,409,response.data)
        self.assertEqual(Customer.objects.get().name,'Acme')

    def test_import_approval_requires_target_capabilities(self):
        batch=self.review(self.stage())
        user=get_user_model().objects.create_user('importer@example.com','long-password')
        for codename,app in [('approve_importbatch','imports'),('view_customer','masters')]:
            user.user_permissions.add(Permission.objects.get(content_type__app_label=app,codename=codename))
        c=APIClient(); c.force_authenticate(user)
        response=self.post(f"imports/{batch['id']}/approve/",{},version=batch['version'],client=c)
        self.assertEqual(response.status_code,403)
        self.assertFalse(Customer.objects.exists())

    def test_xlsx_data_only_reader(self):
        buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,'w') as z:
            z.writestr('xl/workbook.xml','<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Client" r:id="r1"/></sheets></workbook>')
            z.writestr('xl/_rels/workbook.xml.rels','<Relationships><Relationship Id="r1" Target="worksheets/sheet1.xml"/></Relationships>')
            z.writestr('xl/worksheets/sheet1.xml','<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>ID</t></is></c></row><row r="3"><c r="A3" t="inlineStr"><is><t>client-3</t></is></c></row></sheetData></worksheet>')
        rows=read_source(buffer.getvalue(),'source.xlsx')
        self.assertEqual(rows,[{'sheet':'Client','row_number':3,'raw':{'ID':'client-3'}}])
        with zipfile.ZipFile(buffer,'a') as z:
            z.writestr('xl/worksheets/formula.xml','unused')
        # CSV leading zeros remain text source identifiers.
        self.assertEqual(read_source(b'ID\n0003\n','x.csv')[0]['raw']['ID'],'0003')

    def test_each_master_resource_create_and_update(self):
        unit=self.post('units/',{'name':'Piece','code':'pcs','dimension':'count'})
        self.assertEqual(unit.status_code,201,unit.data)
        dept=self.post('departments/',{'name':'D'}).data
        area=self.post('areas/',{'name':'A','department':dept['id']}).data
        product=self.post('products/',{'name':'P','unit':unit.data['id']}).data
        cases={
            'suppliers':{'name':'S','material_supplied':'Client description'},
            'prospects':{'name':'Prospect'},
            'finished-goods':{'name':'V','product':product['id'],'unit':unit.data['id'],'category':'packing'},
            'raw-materials':{'name':'M','unit':unit.data['id'],'category':'ink'},
            'consumables':{'name':'C','unit':unit.data['id'],'category':'local'},
            'machines':{'name':'Equipment','department':dept['id'],'area':area['id'],'type':'client equipment'},
        }
        for resource,data in cases.items():
            with self.subTest(resource=resource):
                result=self.post(resource+'/',data)
                self.assertEqual(result.status_code,201,result.data)
                response=self.client.patch(f"/api/v1/{resource}/{result.data['id']}/",{'is_active':False},format='json',HTTP_IF_MATCH='"1"',HTTP_IDEMPOTENCY_KEY=resource+'-inactive')
                self.assertEqual(response.status_code,200,response.data)
                self.assertFalse(response.data['is_active'])

    def test_import_invalid_unit_and_successful_explicit_update(self):
        batch=self.stage(b'ID,Name,Unit,Category\nm1,Client grade,not-configured,virgin\n',target='raw-materials')
        row=str(ImportRow.objects.get(batch_id=batch['id']).pk)
        result=self.post(f"imports/{batch['id']}/review/",{'mapping':{'source_id':'ID','name':'Name','unit':'Unit','category':'Category'},'decisions':{row:{'action':'create'}}},version=1)
        self.assertEqual(result.status_code,200,result.data)
        self.assertIn('fields',result.data['review'][0]['errors'])
        customer=self.customer(source_system='client-register',source_id='src-1')
        batch=self.review(self.stage(),action='update',target_id=customer['id'],expected_version=1,acknowledge_duplicates=True)
        result=self.post(f"imports/{batch['id']}/approve/",{},version=batch['version'])
        self.assertEqual(result.status_code,200,result.data)
        self.assertEqual(Customer.objects.get().name,'Client item')
        self.assertEqual(Customer.objects.get().version,2)
