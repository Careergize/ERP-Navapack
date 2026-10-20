import uuid
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from apps.accounts.models import User, Employee, EmployeeResetRequest
from apps.accounts.employee_services import lock_administration, require_admin, managed_employee, require_target_ceiling, bump
from apps.accounts.permissions import require_independent_actor
from apps.accounts.management.password_input import read_validated_password
from apps.core.commands import advance_version
from apps.core.audit import record_event


class Command(BaseCommand):
    help='Independently complete a pending employee reset after trusted offline identity verification. Never outputs a password or sends email.'
    def add_arguments(self,parser):
        parser.add_argument('--operator',required=True,type=uuid.UUID)
        parser.add_argument('--request',required=True,type=uuid.UUID)
        parser.add_argument('--identity-verified',required=True,action='store_true')

    def handle(self,*args,**options):
        from rest_framework.exceptions import APIException
        from django.http import Http404
        if not options['identity_verified']:
            raise CommandError('Offline identity verification must be explicitly confirmed.')
        try:
            # Prompt before locks; all state and authorization rechecked afterward.
            pending=EmployeeResetRequest.objects.select_related('employee__user').get(pk=options['request'])
            raw=read_validated_password(pending.employee.user)
            with transaction.atomic():
                lock_administration()
                actor=require_admin(User.objects.get(pk=options['operator']),'initiate_employee_reset')
                pending=EmployeeResetRequest.objects.select_for_update().get(pk=options['request'])
                if pending.status!='pending': raise CommandError('Reset is not pending.')
                maker=require_admin(User.objects.get(pk=pending.requested_by_id),'initiate_employee_reset')
                require_independent_actor(actor,maker.pk)
                employee=managed_employee(actor,pending.employee_id,pending.expected_employee_version)
                if not employee.user.is_active: raise CommandError('Employee is inactive.')
                require_target_ceiling(actor,employee);require_target_ceiling(maker,employee)
                # Validate against current identity as well, after acquiring locks.
                from django.contrib.auth.password_validation import validate_password
                from django.core.exceptions import ValidationError
                try: validate_password(raw,user=employee.user)
                except ValidationError as exc: raise CommandError('; '.join(exc.messages))
                employee.user.set_password(raw);employee.user.save(update_fields=['password','updated_at']);bump(employee,actor)
                pending.status='completed';pending.completed_by=actor;pending.completed_at=timezone.now()
                advance_version(pending,update_fields=['status','completed_by','completed_at'])
                record_event(actor=actor,action='accounts.employee_reset_completed',entity_type='accounts.employee',entity_id=employee.pk,
                    request_id=uuid.uuid4(),source_version=employee.version,summary={'changed_fields':['access'],'outcome':'completed:'+str(pending.pk)})
        except (User.DoesNotExist,EmployeeResetRequest.DoesNotExist,APIException,Http404) as exc: raise CommandError('Reset denied: missing, stale, unauthorized or not independent.') from exc
        self.stdout.write(self.style.SUCCESS('Employee access reset completed. Existing JWTs are invalidated by the changed fingerprint.'))
