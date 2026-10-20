import uuid
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from apps.accounts.models import User, Role, RoleAssignmentPolicy
from apps.accounts.employee_services import lock_administration, require_admin, permission_digest, permission_codes, RESERVED_APPS
from apps.core.audit import record_event
from apps.core.commands import advance_version


class Command(BaseCommand):
    help='Explicitly configure a role assignment policy without changing or granting role permissions.'
    def add_arguments(self,parser):
        parser.add_argument('--operator',required=True,type=uuid.UUID)
        parser.add_argument('--role',required=True,type=uuid.UUID)
        parser.add_argument('--independent-approval',required=True,choices=['yes','no'])

    def handle(self,*args,**options):
        from rest_framework.exceptions import APIException
        try:
            with transaction.atomic():
                lock_administration()
                actor=require_admin(User.objects.get(pk=options['operator']),'manage_employee_roles')
                role=Role.objects.select_for_update().get(pk=options['role'])
                if role.governed: raise CommandError('Governed roles require independently approved API revisions.')
                codes=permission_codes(role)
                if any(c.split('.')[0] in RESERVED_APPS for c in codes): raise CommandError('Technical administration capabilities cannot be delegated through roles.')
                if not set(codes).issubset(actor.get_all_permissions()): raise CommandError('Role exceeds operator delegation ceiling.')
                policy,created=RoleAssignmentPolicy.objects.get_or_create(role=role,defaults={'requires_independent_approval':options['independent_approval']=='yes','permission_digest':permission_digest(role),'configured_by':actor})
                if not created and (policy.permission_digest != permission_digest(role) or policy.requires_independent_approval != (options['independent_approval']=='yes')):
                    raise CommandError('Policy changes require an independently approved capability revision.')
                record_event(actor=actor,action='accounts.configure_role_policy',entity_type='accounts.roleassignmentpolicy',entity_id=policy.pk,
                    request_id=uuid.uuid4(),source_version=policy.version,summary={'changed_fields':['role_policy'],'outcome':{'role_id':str(role.pk),'permission_digest':policy.permission_digest,'independent_approval':policy.requires_independent_approval}})
        except (User.DoesNotExist,Role.DoesNotExist,APIException) as exc: raise CommandError('Active authorized operator and existing role required.') from exc
        self.stdout.write(self.style.SUCCESS('Role assignment policy recorded. No role memberships or capabilities granted.'))
