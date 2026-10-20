import io
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connections, connection, IntegrityError, transaction
from django.test import TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient
from apps.accounts.models import User, Role, Membership, Employee, RoleAssignmentPolicy, RoleChangeRequest, EmployeeResetRequest
from apps.accounts.employee_services import ADMIN_CAPABILITIES, permission_digest
from apps.core.models import AuditEvent, IdempotencyRecord
from apps.masters.models import Department


class EmployeeAdministrationTests(TransactionTestCase):
    def setUp(self):
        self.assertEqual(connection.vendor, 'postgresql')
        self.admin = User.objects.create_user('master@example.com', 'a-long-test-password', name='Master', is_master_admin=True)
        self.admin.user_permissions.add(*Permission.objects.filter(content_type__app_label='accounts', codename__in=ADMIN_CAPABILITIES))
        self.department = Department.objects.create(name='Client department', created_by=self.admin, updated_by=self.admin)
        self.admin_employee = Employee.objects.create(user=self.admin, employee_id='ADMIN-1', department=self.department, designation='Administration', created_by=self.admin, updated_by=self.admin)
        self.reviewer = User.objects.create_user('reviewer@example.com', 'a-long-test-password', is_master_admin=True)
        self.reviewer.user_permissions.add(*Permission.objects.filter(content_type__app_label='accounts', codename__in=ADMIN_CAPABILITIES))
        self.client = APIClient()
        self.client.force_authenticate(self.admin)
        self.role = Role.objects.create(code='client-reviewed-role', name='Client role')
        self.business_permission = Permission.objects.get(content_type__app_label='masters', codename='view_customer')
        self.role.permissions.add(self.business_permission)
        self.admin.user_permissions.add(self.business_permission)
        self.reviewer.user_permissions.add(self.business_permission)

    def post(self, path, data=None, version=None, key=None, actor=None):
        client = self.client
        if actor:
            client = APIClient()
            client.force_authenticate(actor)
        headers = {'HTTP_IDEMPOTENCY_KEY': key or str(uuid.uuid4())}
        if version is not None:
            headers['HTTP_IF_MATCH'] = f'"{version}"'
        return client.post('/api/v1/' + path, data or {}, format='json', **headers)

    def employee(self, code='E-1', email='employee@example.com', **extra):
        response = self.post('employees/', {'employee_id': code, 'email': email, 'name': 'Employee', 'department': str(self.department.pk), 'designation': 'Client designation', **extra})
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def policy(self, independent=True):
        return RoleAssignmentPolicy.objects.create(role=self.role, requires_independent_approval=independent, permission_digest=permission_digest(self.role), configured_by=self.admin)

    def patch_employee(self, obj, data, actor=None):
        client = APIClient()
        client.force_authenticate(actor or self.admin)
        return client.patch(f"/api/v1/employees/{obj['id']}/", data, format='json', HTTP_IF_MATCH=f'"{obj["version"]}"', HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()))

    def test_trusted_master_admin_provisioning_only_technical_grants(self):
        with patch('apps.accounts.management.password_input.getpass.getpass', side_effect=['A-very-strong-passphrase-903!'] * 2):
            call_command('provision_master_admin', email='NEWADMIN@example.com', name='New Admin', employee_id='ADMIN-2', department=str(self.department.pk), designation='Client designation', stdout=io.StringIO())
        user = User.objects.get(email='newadmin@example.com')
        self.assertTrue(user.is_master_admin)
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_staff)
        self.assertTrue(user.check_password('A-very-strong-passphrase-903!'))
        self.assertEqual(set(user.get_all_permissions()), {'accounts.' + cap for cap in ADMIN_CAPABILITIES})
        self.assertEqual(user.employee.employee_id, 'ADMIN-2')
        self.assertTrue(AuditEvent.objects.filter(action='accounts.provision_master_admin', actor=user).exists())
        self.assertNotIn('A-very-strong-passphrase-903!', str(list(AuditEvent.objects.values())))

    def test_provisioning_rejects_weak_password_and_duplicate_identity(self):
        with patch('apps.accounts.management.password_input.getpass.getpass', side_effect=['short'] * 2), self.assertRaises(CommandError):
            call_command('provision_master_admin', email='weak@example.com', name='Weak', employee_id='W', department=str(self.department.pk), designation='D', stdout=io.StringIO())
        self.assertFalse(User.objects.filter(email='weak@example.com').exists())
        with patch('apps.accounts.management.password_input.getpass.getpass', side_effect=['A-very-strong-passphrase-903!'] * 2), self.assertRaises(CommandError):
            call_command('provision_master_admin', email='unique@example.com', name='Unique', employee_id='ADMIN-1', department=str(self.department.pk), designation='D', stdout=io.StringIO())
        self.assertFalse(User.objects.filter(email='unique@example.com').exists())

    def test_employee_creation_unique_ids_and_email(self):
        obj = self.employee()
        employee = Employee.objects.get(pk=obj['id'])
        self.assertFalse(employee.user.has_usable_password())
        self.assertTrue(obj['is_active'])
        self.assertEqual(obj['permissions'], [])
        self.assertFalse(obj['is_master_admin'])
        for employee_id, email in [('e-1', 'other@example.com'), ('E-2', 'EMPLOYEE@example.com')]:
            result = self.post('employees/', {'employee_id': employee_id, 'email': email, 'name': 'Other', 'designation': 'D', 'department': str(self.department.pk)})
            self.assertEqual(result.status_code, 400, result.data)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Employee.objects.create(user=self.reviewer, employee_id='e-1', designation='D', department=self.department, created_by=self.admin, updated_by=self.admin)

    def test_no_public_registration_and_unauthorized_management(self):
        anonymous = APIClient()
        self.assertEqual(anonymous.post('/api/v1/employees/', {}, format='json').status_code, 401)
        self.assertEqual(anonymous.post('/api/v1/auth/register/', {}, format='json').status_code, 404)
        superuser = User.objects.create_superuser('super@example.com', 'long-password')
        client = APIClient()
        client.force_authenticate(superuser)
        for path in ['employees/', 'roles/', 'admin/audit-events/']:
            self.assertEqual(client.get('/api/v1/' + path).status_code, 403)
        user = User.objects.create_user('capabilities@example.com', 'long-password')
        user.user_permissions.add(*Permission.objects.filter(content_type__app_label='accounts'))
        client.force_authenticate(user)
        self.assertEqual(client.get('/api/v1/employees/').status_code, 403)

    def test_master_admin_still_requires_action_capability(self):
        self.admin.user_permissions.remove(Permission.objects.get(content_type__app_label='accounts', codename='add_employee'))
        self.assertEqual(self.post('employees/', {}).status_code, 403)

    def test_client_cannot_set_privileges_password_roles_or_status(self):
        for field, value in [('is_master_admin', True), ('is_superuser', True), ('is_staff', True), ('password', 'new-pass'), ('roles', [str(self.role.pk)]), ('is_active', False), ('user', str(self.admin.pk))]:
            result = self.post('employees/', {'employee_id': 'BAD', 'name': 'Bad', 'email': 'bad@example.com', 'department': str(self.department.pk), 'designation': 'D', field: value})
            self.assertEqual(result.status_code, 400, result.data)
        self.assertFalse(User.objects.filter(email='bad@example.com').exists())

    def test_self_and_privileged_target_mutations_denied(self):
        own = {'id': str(self.admin_employee.pk), 'version': 1}
        self.assertEqual(self.patch_employee(own, {'name': 'Self'}).status_code, 403)
        self.assertEqual(self.post(f"employees/{own['id']}/deactivate/", version=1).status_code, 403)
        employee = self.employee()
        user = User.objects.get(pk=employee['user'])
        user.is_superuser = True
        user.save()
        self.assertEqual(self.patch_employee(employee, {'email': 'changed@example.com'}).status_code, 403)

    def test_editing_and_reporting_cycle_validation(self):
        first = self.employee()
        second = self.employee('E-2', 'second@example.com')
        response = self.patch_employee(first, {'name': 'Renamed', 'email': 'RENAMED@example.com', 'reporting_manager': second['id']})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['email'], 'renamed@example.com')
        cycle = self.patch_employee(second, {'reporting_manager': first['id']})
        self.assertEqual(cycle.status_code, 400, cycle.data)
        self.assertEqual(self.patch_employee(first, {'employee_id': 'changed'}).status_code, 412)
        self.assertEqual(self.patch_employee(response.data, {'employee_id': 'changed'}).status_code, 400)

    def test_directory_pagination_search_filters_and_role_visibility(self):
        self.employee()
        response = self.client.get('/api/v1/employees/?search=Employee&page_size=1&is_active=true')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response['Cache-Control'], 'no-store')
        roles = self.client.get('/api/v1/roles/')
        self.assertEqual(roles.status_code, 200)
        self.assertEqual(roles.data['results'][0]['permissions'], ['masters.view_customer'])
        self.assertIsNone(roles.data['results'][0]['assignment_policy'])

    def test_role_policy_is_explicit_and_does_not_grant_permissions(self):
        obj = self.employee()
        self.assertEqual(self.post(f"employees/{obj['id']}/role-assignments/", {'role': str(self.role.pk)}, version=1).status_code, 403)
        before = Membership.objects.count()
        call_command('configure_employee_role', operator=self.admin.pk, role=self.role.pk, independent_approval='yes', stdout=io.StringIO())
        self.assertTrue(RoleAssignmentPolicy.objects.get(role=self.role).requires_independent_approval)
        self.assertEqual(before, Membership.objects.count())
        self.assertTrue(AuditEvent.objects.filter(action='accounts.configure_role_policy').exists())

    def test_independent_assignment_approval_and_no_self_approval(self):
        self.policy(True)
        obj = self.employee()
        pending = self.post(f"employees/{obj['id']}/role-assignments/", {'role': str(self.role.pk)}, version=1)
        self.assertEqual(pending.status_code, 201, pending.data)
        self.assertEqual(pending.data['status'], 'pending')
        self.assertFalse(Membership.objects.filter(user_id=obj['user']).exists())
        url = f"employees/{obj['id']}/access-requests/{pending.data['id']}/approve/"
        self.assertEqual(self.post(url, version=2).status_code, 403)
        self.admin.is_superuser = True
        self.admin.save()
        self.assertEqual(self.post(url, version=2).status_code, 403)
        applied = self.post(url, version=2, actor=self.reviewer, key='approve-independent')
        self.assertEqual(applied.status_code, 200, applied.data)
        self.assertEqual(applied.data['approved_by'], str(self.reviewer.pk))
        self.assertTrue(Membership.objects.filter(user_id=obj['user'], role=self.role).exists())
        self.assertTrue(User.objects.get(pk=obj['user']).has_perm('masters.view_customer'))
        self.assertEqual(self.post(url, version=2, actor=self.reviewer, key='approve-independent').data, applied.data)

    def test_multiple_roles_and_audited_direct_removal(self):
        self.policy(False)
        obj = self.employee()
        assigned = self.post(f"employees/{obj['id']}/role-assignments/", {'role': str(self.role.pk)}, version=1, key='assign')
        self.assertEqual(assigned.status_code, 201, assigned.data)
        second = Role.objects.create(code='another-approved-role', name='Another')
        RoleAssignmentPolicy.objects.create(role=second, requires_independent_approval=False, permission_digest=permission_digest(second), configured_by=self.admin)
        result = self.post(f"employees/{obj['id']}/role-assignments/", {'role': str(second.pk)}, version=2)
        self.assertEqual(result.status_code, 201, result.data)
        self.assertEqual(Membership.objects.filter(user_id=obj['user']).count(), 2)
        response = self.client.delete(f"/api/v1/employees/{obj['id']}/role-assignments/{assigned.data['assignment_id']}/", format='json', HTTP_IF_MATCH='"3"', HTTP_IDEMPOTENCY_KEY='remove')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(Membership.objects.filter(user_id=obj['user']).count(), 1)
        self.assertFalse(User.objects.get(pk=obj['user']).has_perm('masters.view_customer'))
        self.assertTrue(AuditEvent.objects.filter(action='accounts.remove_role', entity_id=obj['id']).exists())

    def test_independent_removal_retains_access_until_approved(self):
        self.policy(False)
        obj = self.employee()
        assigned = self.post(f"employees/{obj['id']}/role-assignments/", {'role': str(self.role.pk)}, version=1).data
        policy = RoleAssignmentPolicy.objects.get(role=self.role)
        policy.requires_independent_approval = True
        policy.save()
        pending = self.client.delete(f"/api/v1/employees/{obj['id']}/role-assignments/{assigned['assignment_id']}/", HTTP_IF_MATCH='"2"', HTTP_IDEMPOTENCY_KEY='remove-pending')
        self.assertEqual(pending.status_code, 200, pending.data)
        self.assertTrue(Membership.objects.filter(user_id=obj['user'], role=self.role).exists())
        applied = self.post(f"employees/{obj['id']}/access-requests/{pending.data['id']}/approve/", version=3, actor=self.reviewer)
        self.assertEqual(applied.status_code, 200, applied.data)
        self.assertFalse(Membership.objects.filter(user_id=obj['user'], role=self.role).exists())

    def test_grant_ceiling_and_reserved_permissions(self):
        self.policy(False)
        obj = self.employee()
        self.admin.user_permissions.remove(self.business_permission)
        self.assertEqual(self.post(f"employees/{obj['id']}/role-assignments/", {'role': str(self.role.pk)}, version=1).status_code, 403)
        self.role.permissions.add(Permission.objects.get(content_type__app_label='accounts', codename='change_user'))
        policy = RoleAssignmentPolicy.objects.get(role=self.role)
        policy.permission_digest = permission_digest(self.role)
        policy.save()
        self.assertEqual(self.post(f"employees/{obj['id']}/role-assignments/", {'role': str(self.role.pk)}, version=1).status_code, 403)

    def test_changed_role_permissions_invalidate_pending_approval(self):
        self.policy(True)
        obj = self.employee()
        pending = self.post(f"employees/{obj['id']}/role-assignments/", {'role': str(self.role.pk)}, version=1).data
        self.role.permissions.clear()
        response = self.post(f"employees/{obj['id']}/access-requests/{pending['id']}/approve/", version=2, actor=self.reviewer)
        self.assertEqual(response.status_code, 403, response.data)
        self.assertFalse(Membership.objects.exists())
        cancelled = self.post(f"employees/{obj['id']}/access-requests/{pending['id']}/cancel/", version=2)
        self.assertEqual(cancelled.status_code, 200, cancelled.data)
        self.assertEqual(cancelled.data['status'], 'cancelled')

    def test_deactivation_blocks_access_and_refresh_even_after_reactivation(self):
        obj = self.employee()
        user = User.objects.get(pk=obj['user'])
        user.set_password('a-long-test-password')
        user.save()
        client = APIClient()
        login = client.post('/api/v1/auth/login/', {'email': user.email, 'password': 'a-long-test-password'}, format='json')
        self.assertEqual(login.status_code, 200, login.data)
        access, refresh = login.data['access'], login.data['refresh']
        response = self.post(f"employees/{obj['id']}/deactivate/", version=1)
        self.assertEqual(response.status_code, 200, response.data)
        client.credentials(HTTP_AUTHORIZATION='Bearer ' + access)
        self.assertEqual(client.get('/api/v1/auth/me/').status_code, 401)
        self.assertEqual(client.post('/api/v1/auth/refresh/', {'refresh': refresh}, format='json').status_code, 401)
        response = self.post(f"employees/{obj['id']}/activate/", version=2)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(client.get('/api/v1/auth/me/').status_code, 401)
        self.assertEqual(client.post('/api/v1/auth/login/', {'email': user.email, 'password': 'a-long-test-password'}, format='json').status_code, 401)

    def test_reset_initiation_and_independent_trusted_completion(self):
        obj = self.employee()
        reset = self.post(f"employees/{obj['id']}/password-reset/", version=1)
        self.assertEqual(reset.status_code, 201, reset.data)
        self.assertEqual(reset.data['status'], 'pending')
        self.assertNotIn('password', reset.data)
        self.assertNotIn('token', reset.data)
        options = {'operator': self.admin.pk, 'request': uuid.UUID(reset.data['id']), 'identity_verified': True, 'stdout': io.StringIO()}
        with patch('apps.accounts.management.password_input.getpass.getpass', side_effect=['A-very-strong-passphrase-903!'] * 2), self.assertRaises(CommandError):
            call_command('complete_employee_password_reset', **options)
        options['operator'] = self.reviewer.pk
        with patch('apps.accounts.management.password_input.getpass.getpass', side_effect=['A-very-strong-passphrase-903!'] * 2):
            call_command('complete_employee_password_reset', **options)
        user = User.objects.get(pk=obj['user'])
        self.assertTrue(user.check_password('A-very-strong-passphrase-903!'))
        self.assertEqual(EmployeeResetRequest.objects.get().status, 'completed')
        self.assertTrue(AuditEvent.objects.filter(action='accounts.employee_reset_completed', actor=self.reviewer).exists())

    def test_reset_and_activation_cannot_obtain_higher_access(self):
        obj = self.employee()
        Membership.objects.create(user_id=obj['user'], role=self.role)
        self.admin.user_permissions.remove(self.business_permission)
        self.assertEqual(self.post(f"employees/{obj['id']}/password-reset/", version=1).status_code, 403)
        self.assertEqual(self.patch_employee(obj, {'email': 'takeover@example.com'}).status_code, 403)
        deactivated = self.post(f"employees/{obj['id']}/deactivate/", version=1)
        self.assertEqual(deactivated.status_code, 200, deactivated.data)
        self.assertEqual(self.post(f"employees/{obj['id']}/activate/", version=2).status_code, 403)

    def test_reset_stale_employee_cannot_complete(self):
        obj = self.employee()
        reset = self.post(f"employees/{obj['id']}/password-reset/", version=1).data
        self.patch_employee({'id': obj['id'], 'version': 2}, {'designation': 'Changed'})
        with patch('apps.accounts.management.password_input.getpass.getpass', side_effect=['A-very-strong-passphrase-903!'] * 2), self.assertRaises(CommandError):
            call_command('complete_employee_password_reset', operator=self.reviewer.pk, request=uuid.UUID(reset['id']), identity_verified=True, stdout=io.StringIO())
        self.assertFalse(User.objects.get(pk=obj['user']).has_usable_password())

    def test_mutation_retry_and_authority_recheck(self):
        data = {'employee_id': 'E-1', 'email': 'e@example.com', 'name': 'E', 'department': str(self.department.pk), 'designation': 'D'}
        first = self.post('employees/', data, key='retry')
        again = self.post('employees/', data, key='retry')
        self.assertEqual(first.data, again.data)
        self.assertEqual(self.post('employees/', {**data, 'name': 'Other'}, key='retry').status_code, 409)
        self.admin.is_master_admin = False
        self.admin.save()
        self.assertEqual(self.post('employees/', data, key='retry').status_code, 403)

    def test_audit_failure_rolls_back_account_profile_and_membership(self):
        data = {'employee_id': 'ROLLBACK', 'name': 'Rollback', 'email': 'rollback@example.com', 'department': str(self.department.pk), 'designation': 'D'}
        with patch('apps.core.commands.record_event', side_effect=RuntimeError('injected')):
            response = self.post('employees/', data, key='rollback')
        self.assertEqual(response.status_code, 500)
        self.assertFalse(User.objects.filter(email='rollback@example.com').exists())
        self.assertFalse(Employee.objects.filter(employee_id='ROLLBACK').exists())
        self.assertFalse(IdempotencyRecord.objects.filter(key='rollback').exists())
        obj = self.employee()
        self.policy(False)
        with patch('apps.core.commands.record_event', side_effect=RuntimeError('injected')):
            response = self.post(f"employees/{obj['id']}/role-assignments/", {'role': str(self.role.pk)}, version=1)
        self.assertEqual(response.status_code, 500)
        self.assertFalse(Membership.objects.exists())
        self.assertFalse(RoleChangeRequest.objects.exists())

    def test_audit_directory_scope_and_object_assignment_scope(self):
        first = self.employee()
        second = self.employee('E-2', 'second@example.com')
        self.policy(False)
        assigned = self.post(f"employees/{first['id']}/role-assignments/", {'role': str(self.role.pk)}, version=1).data
        response = self.client.delete(f"/api/v1/employees/{second['id']}/role-assignments/{assigned['assignment_id']}/", HTTP_IF_MATCH='"1"', HTTP_IDEMPOTENCY_KEY='wrong-object')
        self.assertEqual(response.status_code, 404)
        events = self.client.get('/api/v1/admin/audit-events/', {'entity_id': first['id'], 'page_size': 1})
        self.assertEqual(events.status_code, 200)
        self.assertEqual(events.data['count'], 2)
        self.assertIsNotNone(events.data['next'])
        self.assertEqual(events.json()['results'][0]['actor'], str(self.admin.pk))

    def test_concurrent_role_approval_only_applies_once(self):
        self.policy(True)
        obj = self.employee()
        pending = self.post(f"employees/{obj['id']}/role-assignments/", {'role': str(self.role.pk)}, version=1).data
        barrier = Barrier(2)
        def worker(i):
            connections.close_all()
            try:
                reviewer = User.objects.get(pk=self.reviewer.pk)
                barrier.wait(timeout=10)
                return self.post(f"employees/{obj['id']}/access-requests/{pending['id']}/approve/", version=2, key='approve-' + str(i), actor=reviewer).status_code
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses = list(pool.map(worker, range(2)))
        self.assertEqual(sorted(statuses), [200, 412])
        self.assertEqual(Membership.objects.filter(user_id=obj['user']).count(), 1)

    def test_role_changes_apply_to_existing_jwt_and_inactive_removal(self):
        self.policy(False)
        obj = self.employee()
        user = User.objects.get(pk=obj['user'])
        user.set_password('a-long-test-password')
        user.save()
        client = APIClient()
        login = client.post('/api/v1/auth/login/', {'email': user.email, 'password': 'a-long-test-password'}, format='json')
        client.credentials(HTTP_AUTHORIZATION='Bearer ' + login.data['access'])
        assigned = self.post(f"employees/{obj['id']}/role-assignments/", {'role': str(self.role.pk)}, version=1).data
        self.assertIn('masters.view_customer', client.get('/api/v1/auth/me/').data['permissions'])
        removed = self.client.delete(f"/api/v1/employees/{obj['id']}/role-assignments/{assigned['assignment_id']}/", HTTP_IF_MATCH='"2"', HTTP_IDEMPOTENCY_KEY='remove-live')
        self.assertEqual(removed.status_code, 200, removed.data)
        self.assertNotIn('masters.view_customer', client.get('/api/v1/auth/me/').data['permissions'])
        assigned = self.post(f"employees/{obj['id']}/role-assignments/", {'role': str(self.role.pk)}, version=3).data
        self.assertEqual(self.post(f"employees/{obj['id']}/deactivate/", version=4).status_code, 200)
        removed = self.client.delete(f"/api/v1/employees/{obj['id']}/role-assignments/{assigned['assignment_id']}/", HTTP_IF_MATCH='"5"', HTTP_IDEMPOTENCY_KEY='remove-inactive')
        self.assertEqual(removed.status_code, 200, removed.data)
        self.assertFalse(Membership.objects.filter(user=user).exists())

    def test_database_rejects_self_approved_role_changes(self):
        obj = self.employee()
        with self.assertRaises(IntegrityError), transaction.atomic():
            RoleChangeRequest.objects.create(employee_id=obj['id'], role=self.role, operation='add',
                permission_digest=permission_digest(self.role), requires_independent_approval=True,
                requested_by=self.admin, approved_by=self.admin, status='applied', assignment_id=uuid.uuid4(), applied_at=timezone.now())

    def test_malformed_object_identities_return_safe_not_found(self):
        self.assertEqual(self.post('employees/invalid-uuid/activate/', version=1).status_code, 404)
        obj = self.employee()
        bad = '-' * 36
        response = self.client.delete(f"/api/v1/employees/{obj['id']}/role-assignments/{bad}/", HTTP_IF_MATCH='"1"', HTTP_IDEMPOTENCY_KEY='invalid-object')
        self.assertEqual(response.status_code, 404)

    def test_provisioning_audit_failure_is_atomic(self):
        with patch('apps.accounts.management.password_input.getpass.getpass', side_effect=['A-very-strong-passphrase-903!'] * 2), patch('apps.accounts.management.commands.provision_master_admin.record_event', side_effect=RuntimeError('injected')), self.assertRaises(RuntimeError):
            call_command('provision_master_admin', email='rolled-back@example.com', name='Rolled back', employee_id='ADMIN-X', department=str(self.department.pk), designation='D', stdout=io.StringIO())
        self.assertFalse(User.objects.filter(email='rolled-back@example.com').exists())
        self.assertFalse(Employee.objects.filter(employee_id='ADMIN-X').exists())
