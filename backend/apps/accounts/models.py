import uuid
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin, Permission
from django.db import models
from django.db.models.functions import Lower


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError('Email is required.')
        user = self.model(email=email.strip().lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra):
        extra.setdefault('is_staff', True)
        extra.setdefault('is_superuser', True)
        if not extra['is_staff'] or not extra['is_superuser'] or not extra.get('is_active', True):
            raise ValueError('Superuser must be active, staff and superuser.')
        return self.create_user(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_master_admin = models.BooleanField(default=False, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    roles = models.ManyToManyField('Role', through='Membership', related_name='users')
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    objects = UserManager()

    class Meta:
        constraints = [models.UniqueConstraint(Lower('email'), name='accounts_user_email_ci_unique')]

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email


class Role(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    permissions = models.ManyToManyField(Permission, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    version = models.PositiveIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)
    governed = models.BooleanField(default=False, editable=False)
    approved_revision = models.ForeignKey('RoleCapabilityRevision', null=True, on_delete=models.PROTECT, related_name='+')

    class Meta:
        permissions = [('manage_role_capabilities','Propose role capability revisions'),
                       ('approve_role_capabilities','Independently approve role capability revisions')]


class Membership(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'role'], name='unique_user_role')]


from apps.core.models import VersionedModel


class Employee(VersionedModel):
    user = models.OneToOneField(User, on_delete=models.PROTECT, related_name='employee')
    employee_id = models.CharField(max_length=100)
    department = models.ForeignKey('masters.Department', on_delete=models.PROTECT)
    designation = models.CharField(max_length=200)
    reporting_manager = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT, related_name='reports')
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='+')
    updated_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='+')

    class Meta(VersionedModel.Meta):
        constraints = VersionedModel.Meta.constraints + [
            models.UniqueConstraint(Lower('employee_id'), name='employee_id_ci_unique'),
            models.CheckConstraint(condition=~models.Q(employee_id=''), name='employee_id_not_blank'),
            models.CheckConstraint(condition=~models.Q(designation=''), name='employee_designation_not_blank'),
            models.CheckConstraint(condition=~models.Q(reporting_manager=models.F('id')), name='employee_not_own_manager'),
        ]
        permissions = [
            ('manage_employee_status','Activate and deactivate ordinary employees'),
            ('manage_employee_roles','Request employee role changes'),
            ('approve_employee_roles','Independently approve employee role changes'),
            ('initiate_employee_reset','Initiate employee access reset'),
            ('view_admin_audit','View administrative audit history'),
        ]


class RoleAssignmentPolicy(VersionedModel):
    role = models.OneToOneField(Role, on_delete=models.PROTECT, related_name='assignment_policy')
    requires_independent_approval = models.BooleanField()
    permission_digest = models.CharField(max_length=64)
    configured_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='+')


class RoleChangeRequest(VersionedModel):
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name='access_requests')
    role = models.ForeignKey(Role, on_delete=models.PROTECT)
    operation = models.CharField(max_length=10, choices=[('add','add'),('remove','remove')])
    assignment_id = models.UUIDField(null=True)  # Retained even after membership removal.
    permission_digest = models.CharField(max_length=64)
    requires_independent_approval = models.BooleanField()
    requested_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='+')
    approved_by = models.ForeignKey(User, null=True, on_delete=models.PROTECT, related_name='+')
    status = models.CharField(max_length=10, default='pending', choices=[('pending','pending'),('applied','applied'),('cancelled','cancelled')])
    applied_at = models.DateTimeField(null=True)


class EmployeeResetRequest(VersionedModel):
    expected_employee_version = models.PositiveIntegerField()
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name='reset_requests')
    requested_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='+')
    completed_by = models.ForeignKey(User, null=True, on_delete=models.PROTECT, related_name='+')
    status = models.CharField(max_length=12, default='pending', choices=[('pending','pending'),('completed','completed'),('superseded','superseded')])
    completed_at = models.DateTimeField(null=True)


class RoleCapabilityRevision(VersionedModel):
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name='capability_revisions')
    permission_codes = models.JSONField()
    requires_independent_approval = models.BooleanField()
    expected_role_version = models.PositiveIntegerField()
    baseline = models.JSONField()
    requested_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='+')
    approved_by = models.ForeignKey(User, null=True, on_delete=models.PROTECT, related_name='+')
    status = models.CharField(max_length=12, default='pending', choices=[('pending','pending'),('applied','applied'),('cancelled','cancelled')])
    applied_at = models.DateTimeField(null=True)

    class Meta(VersionedModel.Meta):
        constraints = VersionedModel.Meta.constraints + [
            models.UniqueConstraint(fields=['role'], condition=models.Q(status='pending'), name='one_pending_capability_revision'),
            models.CheckConstraint(condition=~models.Q(status='applied', approved_by=models.F('requested_by')), name='independent_capability_approver'),
            models.CheckConstraint(condition=~models.Q(status='applied') | models.Q(approved_by__isnull=False, applied_at__isnull=False), name='capability_approval_evidence'),
        ]


# Invariants for approved changes supplement service checks for every database writer.
RoleChangeRequest._meta.constraints += [
    models.UniqueConstraint(fields=['employee','role'], condition=models.Q(status='pending'), name='one_pending_employee_role_change'),
    models.CheckConstraint(condition=~models.Q(status='applied', requires_independent_approval=True, approved_by=models.F('requested_by')), name='independent_role_approver'),
    models.CheckConstraint(condition=~models.Q(status='applied') | models.Q(approved_by__isnull=False, applied_at__isnull=False, assignment_id__isnull=False), name='applied_role_change_has_evidence'),
]
EmployeeResetRequest._meta.constraints += [
    models.UniqueConstraint(fields=['employee'], condition=models.Q(status='pending'), name='one_pending_employee_reset'),
    models.CheckConstraint(condition=models.Q(expected_employee_version__gte=1), name='reset_expected_version_positive'),
    models.CheckConstraint(condition=~models.Q(status='completed', completed_by=models.F('requested_by')), name='independent_reset_completer'),
    models.CheckConstraint(condition=~models.Q(status='completed') | models.Q(completed_by__isnull=False, completed_at__isnull=False), name='completed_reset_has_evidence'),
]
