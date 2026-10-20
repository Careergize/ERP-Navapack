import uuid
from datetime import timedelta
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from django.test import TransactionTestCase
from django.db import connection, connections, transaction, DatabaseError
from django.utils import timezone
from django.contrib.auth.models import Permission
from rest_framework.test import APIClient
from apps.accounts.models import User, Employee
from apps.masters.models import Unit, Material, Department
from apps.inventory.models import Warehouse, StorageLocation, StockIdentity, WarehouseScope
from apps.core.models import AuditEvent, IdempotencyRecord


class InventoryFoundationTests(TransactionTestCase):
    def setUp(self):
        self.assertEqual(connection.vendor,'postgresql')
        self.actor=User.objects.create_user('inventory@example.test','password')
        self.maker=User.objects.create_user('maker@example.test','password')
        self.reviewer=User.objects.create_user('reviewer@example.test','password')
        self.department=Department.objects.create(code='SYN-D',name='Synthetic',created_by=self.actor,updated_by=self.actor)
        Employee.objects.create(user=self.actor,department=self.department,employee_id='SYN-1',designation='Synthetic tester',created_by=self.actor,updated_by=self.actor)
        self.actor.user_permissions.add(*Permission.objects.filter(content_type__app_label='inventory'))
        self.scope=WarehouseScope.objects.create(user=self.actor,company_wide=True,requested_by=self.maker,approved_by=self.reviewer,policy_reference='synthetic-policy',evidence_reference='synthetic-evidence',expires_at=timezone.now()+timedelta(hours=1))
        self.client=APIClient(); self.client.force_authenticate(self.actor)
        self.wh=Warehouse.objects.create(code='SYN',name='Synthetic',created_by=self.actor)
        self.unit=Unit.objects.create(code='SYN-KG',name='Synthetic unit',dimension='mass',created_by=self.actor,updated_by=self.actor)
        self.material=Material.objects.create(code='SYN-M',name='Synthetic material',category='virgin',unit=self.unit,created_by=self.actor,updated_by=self.actor)
    def post(self,resource,data,key=None):
        return self.client.post('/api/v1/inventory/'+resource+'/',{**data,'reason':'Synthetic test'},format='json',HTTP_IDEMPOTENCY_KEY=key or str(uuid.uuid4()))
    def patch(self,resource,obj,data,version=1):
        return self.client.patch(f'/api/v1/inventory/{resource}/{obj}/',{**data,'reason':'Synthetic test'},format='json',HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),HTTP_IF_MATCH=f'"{version}"')
    def identity(self,**extra):
        return self.post('identities',{'warehouse':str(self.wh.pk),'material':str(self.material.pk),'unit':str(self.unit.pk),'kind':'BATCH','source_system':'synthetic','source_reference':str(uuid.uuid4()),**extra})
    def test_warehouse_uuid_idempotency_audit_and_stale_version(self):
        data={'code':'SYN-2','name':'Synthetic 2'}
        first=self.post('warehouses',data,'same'); again=self.post('warehouses',data,'same')
        self.assertEqual(first.status_code,201,first.data); self.assertEqual(first.data,again.data)
        uuid.UUID(first.data['id'])
        self.assertEqual(AuditEvent.objects.filter(entity_id=first.data['id']).count(),1)
        changed=self.patch('warehouses',first.data['id'],{'name':'Changed'})
        self.assertEqual(changed.status_code,200,changed.data)
        self.assertEqual(self.patch('warehouses',first.data['id'],{'name':'Stale'}).status_code,412)
        event=AuditEvent.objects.get(entity_id=first.data['id'],source_version=2)
        self.assertEqual(event.actor_id,self.actor.pk)
        self.assertEqual(event.summary['outcome']['before']['name'],'Synthetic 2')
        self.assertEqual(event.summary['outcome']['after']['name'],'Changed')
        self.assertIn('employee_id',event.summary['outcome']['authority'])
        self.assertEqual(self.post('warehouses',{'code':'syn-2','name':'Duplicate'}).status_code,400)
    def test_scope_isolation_and_no_admin_or_superuser_bypass(self):
        outsider=User.objects.create_superuser('outsider@example.test','password')
        Employee.objects.create(user=outsider,department=self.department,employee_id='SYN-ADMIN',designation='Synthetic admin',created_by=self.actor,updated_by=self.actor)
        outsider.is_master_admin=True;outsider.save(update_fields=['is_master_admin'])
        from apps.accounts.serializers import UserSerializer
        self.assertFalse(any(p.startswith('inventory.') for p in UserSerializer(outsider).data['permissions']))
        self.client.force_authenticate(outsider)
        self.assertEqual(self.client.get('/api/v1/inventory/warehouses/').status_code,403)
        self.client.force_authenticate(self.maker)
        Employee.objects.create(user=self.maker,department=self.department,employee_id='SYN-2',designation='Synthetic',created_by=self.actor,updated_by=self.actor)
        self.maker.user_permissions.add(*Permission.objects.filter(content_type__app_label='inventory'))
        WarehouseScope.objects.create(user=self.maker,warehouse=self.wh,requested_by=self.actor,approved_by=self.reviewer,policy_reference='synthetic',evidence_reference='synthetic',expires_at=timezone.now()+timedelta(hours=1))
        other=Warehouse.objects.create(code='OTHER',name='Other synthetic',created_by=self.actor)
        r=self.client.get('/api/v1/inventory/warehouses/')
        self.assertEqual([x['id'] for x in r.data['results']],[str(self.wh.pk)])
        self.assertEqual(self.client.get(f'/api/v1/inventory/warehouses/{other.pk}/').status_code,404)
        self.assertEqual(self.post('warehouses',{'code':'DENIED','name':'Denied'}).status_code,403)
        self.assertEqual(self.post('locations',{'warehouse':str(other.pk),'code':'BAD','name':'Denied'}).status_code,403)
    def test_location_hierarchy_and_database_guards(self):
        a=self.post('locations',{'warehouse':str(self.wh.pk),'code':'A','name':'A'})
        self.assertEqual(a.status_code,201,a.data)
        b=self.post('locations',{'warehouse':str(self.wh.pk),'code':'B','name':'B','parent':a.data['id']})
        self.assertEqual(b.status_code,201,b.data)
        self.assertEqual(self.patch('locations',a.data['id'],{'parent':b.data['id']}).status_code,400)
        other=Warehouse.objects.create(code='OTHER',name='Other',created_by=self.actor)
        self.assertEqual(self.post('locations',{'warehouse':str(other.pk),'code':'C','name':'C','parent':a.data['id']}).status_code,400)
        with self.assertRaises(DatabaseError),transaction.atomic():
            StorageLocation.objects.filter(pk=a.data['id']).update(parent_id=b.data['id'])
        with self.assertRaises(DatabaseError),transaction.atomic():
            StorageLocation.objects.filter(pk=a.data['id']).update(warehouse=other)
    def test_identity_uuid_immutable_source_and_parent(self):
        a=self.identity(); self.assertEqual(a.status_code,201,a.data)
        self.assertEqual(a.data['reference'],'STK-'+uuid.UUID(a.data['id']).hex.upper())
        self.assertEqual(a.data['operational_status'],'UNAVAILABLE_PHASE_3A_NO_POSTING')
        b=self.identity(kind='PORTION',parent=a.data['id'],physical_reference='SYN-LABEL')
        self.assertEqual(b.status_code,201,b.data)
        self.assertEqual(self.identity(parent=a.data['id'],unit=str(uuid.uuid4())).status_code,400)
        self.assertEqual(self.identity(reference='CALLER').status_code,400)
        self.assertEqual(self.identity(source_reference=a.data['source_reference']).status_code,400)
        self.assertEqual(self.patch('identities',a.data['id'],{'source_reference':'changed'}).status_code,400)
        with self.assertRaises(DatabaseError),transaction.atomic():
            StockIdentity.objects.filter(pk=a.data['id']).update(reference='FORGED')
        with self.assertRaises(DatabaseError),transaction.atomic():
            StockIdentity.objects.filter(pk=a.data['id']).update(id=uuid.uuid4())
        self.assertEqual(self.patch('identities',a.data['id'],{'lifecycle':'RETIRED'}).status_code,200)
        self.assertEqual(self.patch('identities',a.data['id'],{'lifecycle':'REGISTERED'},2).status_code,400)
    def test_audit_failure_rolls_back_command_and_configuration(self):
        before=IdempotencyRecord.objects.count()
        with patch('apps.core.commands.record_event',side_effect=RuntimeError('synthetic failure')):
            r=self.post('warehouses',{'code':'ROLLBACK','name':'Rollback'})
        self.assertEqual(r.status_code,500)
        self.assertFalse(Warehouse.objects.filter(code='ROLLBACK').exists())
        self.assertEqual(IdempotencyRecord.objects.count(),before)
    def test_inactive_delete_and_operational_routes_unavailable(self):
        self.assertEqual(self.patch('warehouses',self.wh.pk,{'is_active':False}).status_code,200)
        self.assertEqual(self.identity().status_code,400)
        self.assertEqual(self.post('locations',{'warehouse':str(self.wh.pk),'code':'INACTIVE','name':'Inactive'}).status_code,400)
        self.assertEqual(self.client.delete(f'/api/v1/inventory/warehouses/{self.wh.pk}/').status_code,405)
        with self.assertRaises(DatabaseError),transaction.atomic(): self.wh.delete()
        for route in ['receipts','issues','opening-corrections','transfers','releases']:
            self.assertEqual(self.post(route,{}).status_code,404)
    def test_owner_shape_and_same_supplier_batch_are_not_unique(self):
        self.assertEqual(self.identity(ownership='CUSTOMER').status_code,400)
        self.assertEqual(self.identity(ownership='COMPANY').status_code,400)
        for _ in range(2): self.assertEqual(self.identity(supplier_batch='SUPPLIER-REUSED').status_code,201)
    def test_scope_evidence_independence_and_immutability(self):
        with self.assertRaises(DatabaseError),transaction.atomic():
            WarehouseScope.objects.create(user=self.actor,company_wide=True,requested_by=self.actor,approved_by=self.actor,policy_reference='synthetic',evidence_reference='synthetic',expires_at=timezone.now()+timedelta(hours=1))
        with self.assertRaises(DatabaseError),transaction.atomic():
            WarehouseScope.objects.filter(pk=self.scope.pk).update(policy_reference='forged')

    def test_authenticated_jwt_contract_and_no_scope_or_capability_shortcuts(self):
        client=APIClient()
        self.assertEqual(client.get('/api/v1/inventory/warehouses/').status_code,401)
        login=client.post('/api/v1/auth/login/',{'email':self.actor.email,'password':'password'},format='json')
        self.assertEqual(login.status_code,200,login.data)
        self.assertIsInstance(login.data['user']['roles'],list)
        client.credentials(HTTP_AUTHORIZATION='Bearer '+login.data['access'])
        self.assertEqual(client.get('/api/v1/inventory/warehouses/').data['count'],1)
        self.actor.user_permissions.clear()
        self.assertEqual(client.get('/api/v1/inventory/warehouses/').status_code,403)
        self.actor.user_permissions.add(*Permission.objects.filter(content_type__app_label='inventory'))
        self.actor.is_active=False;self.actor.save(update_fields=['is_active'])
        self.assertEqual(client.get('/api/v1/inventory/warehouses/').status_code,401)

    def test_preconditions_and_expired_scope_replay_denied(self):
        first=self.post('warehouses',{'code':'REPLAY','name':'Replay'},'scope-replay')
        self.assertEqual(first.status_code,201)
        r=self.client.patch(f'/api/v1/inventory/warehouses/{self.wh.pk}/',{'name':'Changed','reason':'Synthetic'},format='json',HTTP_IDEMPOTENCY_KEY='missing')
        self.assertEqual(r.status_code,428)
        future=timezone.now()+timedelta(hours=2)
        with patch('apps.inventory.authorization.timezone.now',return_value=future):
            self.assertEqual(self.client.get('/api/v1/inventory/warehouses/').data['count'],0)
            self.assertEqual(self.post('warehouses',{'code':'REPLAY','name':'Replay'},'scope-replay').status_code,403)
        self.assertEqual(self.post('locations',{'warehouse':'malformed','code':'BAD','name':'Bad'}).status_code,400)

    def test_parent_database_integrity_and_active_dependents(self):
        a=self.identity();self.assertEqual(a.status_code,201,a.data)
        self.assertEqual(self.patch('warehouses',self.wh.pk,{'is_active':False}).status_code,400)
        other=Warehouse.objects.create(code='OTHER',name='Other',created_by=self.actor)
        self.assertEqual(self.identity(warehouse=str(other.pk),parent=a.data['id']).status_code,400)
        with self.assertRaises(DatabaseError),transaction.atomic():
            StockIdentity.objects.create(warehouse=other,material=self.material,unit=self.unit,kind='PORTION',parent_id=a.data['id'],source_system='synthetic',source_reference='invalid-parent',created_by=self.actor)

    def test_concurrent_hierarchy_changes_cannot_create_cycle(self):
        a=StorageLocation.objects.create(warehouse=self.wh,code='A',name='A',created_by=self.actor)
        b=StorageLocation.objects.create(warehouse=self.wh,code='B',name='B',created_by=self.actor)
        barrier=Barrier(2)
        def worker(child,parent):
            connections.close_all()
            try:
                client=APIClient();client.force_authenticate(User.objects.get(pk=self.actor.pk))
                barrier.wait(timeout=10)
                r=client.patch(f'/api/v1/inventory/locations/{child}/',{'parent':str(parent),'reason':'Synthetic race'},format='json',HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),HTTP_IF_MATCH='"1"')
                return r.status_code
            finally: connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(worker,a.pk,b.pk),pool.submit(worker,b.pk,a.pk)]
            results=[f.result(timeout=30) for f in futures]
        self.assertEqual(sorted(results),[200,400])
        a.refresh_from_db();b.refresh_from_db()
        self.assertFalse(a.parent_id==b.pk and b.parent_id==a.pk)

    def test_audit_history_requires_capability_and_exact_warehouse_scope(self):
        event=self.post('warehouses',{'code':'VISIBLE','name':'Visible'})
        self.assertEqual(event.status_code,201,event.data)
        history=self.client.get('/api/v1/inventory/history/',{'entity_id':event.data['id']})
        self.assertEqual(history.status_code,200,history.data)
        self.assertEqual(history.data['count'],1)
        self.assertEqual(self.client.get('/api/v1/inventory/history/',{'warehouse':str(self.wh.pk)}).data['count'],0)
        self.maker.user_permissions.add(*Permission.objects.filter(content_type__app_label='inventory'))
        Employee.objects.create(user=self.maker,department=self.department,employee_id='SYN-SCOPED',designation='Synthetic',created_by=self.actor,updated_by=self.actor)
        WarehouseScope.objects.create(user=self.maker,warehouse=self.wh,requested_by=self.actor,approved_by=self.reviewer,policy_reference='synthetic',evidence_reference='synthetic',expires_at=timezone.now()+timedelta(hours=1))
        self.client.force_authenticate(self.maker)
        self.assertEqual(self.client.get('/api/v1/inventory/history/').data['count'],0)
        self.assertEqual(self.client.get(f"/api/v1/inventory/history/{history.data['results'][0]['id']}/").status_code,404)
        self.client.force_authenticate(self.actor)
        self.actor.user_permissions.remove(Permission.objects.get(content_type__app_label='inventory',codename='view_inventory_audit'))
        self.assertEqual(self.client.get('/api/v1/inventory/history/').status_code,403)
