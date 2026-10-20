import io
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connections, transaction, DatabaseError
from rest_framework.test import APIClient
from tests.test_employees import EmployeeAdministrationTests as BaseEmployeeTests
from apps.accounts.models import User, Role, Membership, RoleAssignmentPolicy, RoleCapabilityRevision
from apps.accounts.employee_services import permission_digest
from apps.core.models import AuditEvent


class RoleCapabilityTests(BaseEmployeeTests):
    def propose(self,role=None,codes=None,independent=True):
        role=role or self.role;role.refresh_from_db()
        response=self.post(f'roles/{role.pk}/capability-revisions/',{
            'permission_codes':codes if codes is not None else ['masters.view_customer'],
            'requires_independent_approval':independent},version=role.version)
        self.assertEqual(response.status_code,201,response.data)
        return response.data

    def approve(self,proposal,actor=None,key=None):
        return self.post(f"roles/{proposal['role']}/capability-revisions/{proposal['id']}/approve/",
            version=proposal['role_version'],actor=actor or self.reviewer,key=key)

    def test_create_role_has_no_implicit_business_grants(self):
        response=self.post('roles/',{'code':'new-role','name':'Client defined'})
        self.assertEqual(response.status_code,201,response.data)
        role=Role.objects.get(pk=response.data['id'])
        self.assertTrue(role.governed);self.assertIsNone(role.approved_revision_id)
        self.assertEqual(response.data['permissions'],[])
        self.assertEqual(self.post('roles/',{'code':'bad','name':'Bad','permissions':[]}).status_code,400)

    def test_independent_versioned_publication_updates_existing_members(self):
        employee=self.employee();worker=User.objects.get(pk=employee['user'])
        Membership.objects.create(user=worker,role=self.role)
        self.policy()
        proposal=self.propose(codes=[])
        self.assertTrue(User.objects.get(pk=worker.pk).has_perm('masters.view_customer'))
        self.assertEqual(self.approve(proposal,actor=self.admin).status_code,403)
        response=self.approve(proposal,key='publish')
        self.assertEqual(response.status_code,200,response.data)
        self.assertFalse(User.objects.get(pk=worker.pk).has_perm('masters.view_customer'))
        self.role.refresh_from_db();self.assertTrue(self.role.governed)
        self.assertEqual(str(self.role.approved_revision_id),proposal['id'])
        self.assertEqual(self.approve(proposal,key='publish').data,response.data)
        self.assertEqual(AuditEvent.objects.filter(action='accounts.approve_revision').count(),1)

    def test_existing_stale_legacy_policy_cannot_expand_access(self):
        worker=User.objects.create_user('worker@example.com')
        self.policy();Membership.objects.create(user=worker,role=self.role)
        self.role.permissions.add(Permission.objects.get(content_type__app_label='masters',codename='add_customer'))
        self.assertFalse(User.objects.get(pk=worker.pk).has_perm('masters.add_customer'))
        with self.assertRaises(CommandError):
            call_command('configure_employee_role',operator=self.admin.pk,role=self.role.pk,independent_approval='yes',stdout=io.StringIO())

    def test_governed_role_ignores_unreviewed_permission_edits(self):
        proposal=self.propose();self.assertEqual(self.approve(proposal).status_code,200)
        worker=User.objects.create_user('governed@example.com');Membership.objects.create(user=worker,role=self.role)
        self.role.permissions.add(Permission.objects.get(content_type__app_label='masters',codename='add_customer'))
        current=User.objects.get(pk=worker.pk)
        self.assertTrue(current.has_perm('masters.view_customer'))
        self.assertFalse(current.has_perm('masters.add_customer'))
        with self.assertRaises(CommandError):
            call_command('configure_employee_role',operator=self.admin.pk,role=self.role.pk,independent_approval='no',stdout=io.StringIO())

    def test_proposal_and_review_reject_holder_self_escalation(self):
        Membership.objects.create(user=self.admin,role=self.role)
        response=self.post(f'roles/{self.role.pk}/capability-revisions/',{'permission_codes':[],'requires_independent_approval':False},version=1)
        self.assertEqual(response.status_code,403)
        self.assertFalse(RoleCapabilityRevision.objects.exists())

    def test_membership_drift_requires_new_review(self):
        proposal=self.propose()
        worker=User.objects.create_user('newmember@example.com');Membership.objects.create(user=worker,role=self.role)
        response=self.approve(proposal)
        self.assertEqual(response.status_code,409,response.data)
        self.assertEqual(response.data['error']['code'],'stale_review')
        self.assertFalse(Role.objects.get(pk=self.role.pk).governed)
        cancel=self.post(f"roles/{self.role.pk}/capability-revisions/{proposal['id']}/cancel/",version=proposal['role_version'])
        self.assertEqual(cancel.status_code,200,cancel.data)
        self.assertEqual(self.approve(self.propose()).status_code,200)

    def test_permission_or_policy_drift_rejected(self):
        self.policy()
        proposal=self.propose()
        RoleAssignmentPolicy.objects.filter(role=self.role).update(requires_independent_approval=False)
        self.assertEqual(self.approve(proposal).status_code,409)

    def test_technical_unknown_and_above_ceiling_capabilities_denied(self):
        for codes,status in [(['accounts.manage_employee_roles'],403),(['masters.add_customer'],403),(['masters.unknown'],400)]:
            result=self.post(f'roles/{self.role.pk}/capability-revisions/',{'permission_codes':codes,'requires_independent_approval':True},version=1)
            self.assertEqual(result.status_code,status,result.data)
        self.assertFalse(RoleCapabilityRevision.objects.exists())

    def test_maker_revocation_or_reviewer_ceiling_blocks_approval(self):
        proposal=self.propose()
        self.admin.is_active=False;self.admin.save()
        self.assertEqual(self.approve(proposal).status_code,403)

    def test_no_master_admin_flag_or_missing_capability_denies_writes(self):
        ordinary=User.objects.create_user('ordinary@example.com')
        ordinary.user_permissions.set(self.admin.user_permissions.all())
        self.assertEqual(self.post('roles/',{'name':'No','code':'no'},actor=ordinary).status_code,403)
        self.reviewer.user_permissions.remove(Permission.objects.get(content_type__app_label='accounts',codename='manage_role_capabilities'))
        self.assertEqual(self.post('roles/',{'name':'No','code':'no'},actor=self.reviewer).status_code,403)

    def test_pending_employee_request_cannot_cross_capability_publication(self):
        employee=self.employee();self.policy()
        change=self.post(f"employees/{employee['id']}/role-assignments/",{'role':str(self.role.pk)},version=1)
        self.assertEqual(change.status_code,201,change.data)
        self.assertEqual(self.approve(self.propose(codes=[])).status_code,200)
        response=self.post(f"employees/{employee['id']}/access-requests/{change.data['id']}/approve/",version=2,actor=self.reviewer)
        self.assertEqual(response.status_code,409,response.data)
        self.assertFalse(Membership.objects.filter(user_id=employee['user']).exists())

    def test_approved_independence_cannot_be_lowered_outside_publication(self):
        proposal=self.propose(independent=True)
        self.assertEqual(self.approve(proposal).status_code,200)
        RoleAssignmentPolicy.objects.filter(role=self.role).update(requires_independent_approval=False)
        employee=self.employee()
        result=self.post(f"employees/{employee['id']}/role-assignments/",{'role':str(self.role.pk)},version=1)
        self.assertEqual(result.status_code,403,result.data)

    def test_existing_jwt_observes_capability_revocation(self):
        employee=self.employee();worker=User.objects.get(pk=employee['user'])
        worker.set_password('Synthetic-test-password-123!');worker.save()
        self.policy();Membership.objects.create(user=worker,role=self.role)
        client=APIClient()
        login=client.post('/api/v1/auth/login/',{'email':worker.email,'password':'Synthetic-test-password-123!'},format='json')
        self.assertEqual(login.status_code,200,login.data)
        client.credentials(HTTP_AUTHORIZATION='Bearer '+login.data['access'])
        self.assertEqual(client.get('/api/v1/customers/').status_code,200)
        self.assertEqual(self.approve(self.propose(codes=[])).status_code,200)
        self.assertEqual(client.get('/api/v1/customers/').status_code,403)

    def test_review_evidence_immutable_at_database_boundary(self):
        proposal=self.propose()
        with self.assertRaises(DatabaseError),transaction.atomic():
            RoleCapabilityRevision.objects.filter(pk=proposal['id']).update(permission_codes=[])
        self.assertEqual(self.approve(proposal).status_code,200)
        with self.assertRaises(DatabaseError),transaction.atomic():
            RoleCapabilityRevision.objects.filter(pk=proposal['id']).update(status='pending')

    def test_role_publication_audit_failure_rolls_back_every_change(self):
        proposal=self.propose()
        with patch('apps.core.commands.record_event',side_effect=RuntimeError('Synthetic failure')):
            response=self.approve(proposal)
        self.assertEqual(response.status_code,500)
        self.role.refresh_from_db();self.assertFalse(self.role.governed)
        self.assertEqual(RoleCapabilityRevision.objects.get().status,'pending')
        self.assertFalse(RoleAssignmentPolicy.objects.exists())

    def test_concurrent_approval_retry_publishes_once(self):
        proposal=self.propose();barrier=Barrier(2)
        def worker(_):
            try:
                actor=User.objects.get(pk=self.reviewer.pk);barrier.wait()
                return self.approve(proposal,actor=actor,key='concurrent-publish').status_code
            finally: connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(worker,range(2)))
        self.assertEqual(results,[200,200])
        self.assertEqual(AuditEvent.objects.filter(action='accounts.approve_revision').count(),1)

    def test_malformed_role_uuid_and_revision_uuid_are_404(self):
        result=self.post('roles/bad/capability-revisions/',{},version=1)
        self.assertEqual(result.status_code,404,result.data)
        result=self.post(f'roles/{self.role.pk}/capability-revisions/bad/approve/',{},version=1,actor=self.reviewer)
        self.assertEqual(result.status_code,404,result.data)

    def test_capability_catalog_exposes_only_delegable_held_definitions(self):
        response=self.client.get('/api/v1/roles/capability-catalog/')
        self.assertEqual(response.status_code,200,response.data)
        self.assertEqual([x['code'] for x in response.data['results']],['masters.view_customer'])

    def test_metadata_cannot_write_capabilities_or_protected_role_state(self):
        for payload in [{'permissions':[]},{'governed':False},{'approved_revision':None}]:
            result=self.client.patch(f'/api/v1/roles/{self.role.pk}/',payload,format='json',
                HTTP_IF_MATCH='"1"',HTTP_IDEMPOTENCY_KEY=uuid.uuid4().hex)
            self.assertEqual(result.status_code,400,result.data)
        self.assertEqual(self.post(f'roles/{self.role.pk}/capability-revisions/',{'permission_codes':[],'requires_independent_approval':True}).status_code,428)

    def test_privileged_member_roles_require_trusted_maintenance(self):
        Membership.objects.create(user=self.reviewer,role=self.role)
        response=self.post(f'roles/{self.role.pk}/capability-revisions/',{'permission_codes':[],'requires_independent_approval':True},version=1)
        self.assertEqual(response.status_code,403,response.data)

    def test_revision_scope_cannot_be_swapped_between_roles(self):
        proposal=self.propose()
        other=Role.objects.create(code='other-role',name='Other')
        result=self.post(f"roles/{other.pk}/capability-revisions/{proposal['id']}/approve/",version=1,actor=self.reviewer)
        self.assertEqual(result.status_code,404,result.data)
        self.assertEqual(RoleCapabilityRevision.objects.get().status,'pending')


for _name in list(vars(BaseEmployeeTests)):
    if _name.startswith('test_'): setattr(RoleCapabilityTests,_name,None)
del BaseEmployeeTests
