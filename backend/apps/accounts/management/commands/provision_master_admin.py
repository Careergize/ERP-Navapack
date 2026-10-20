import uuid
from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from apps.accounts.models import User, Employee
from apps.accounts.employee_serializers import EmployeeInput
from apps.accounts.employee_services import ADMIN_CAPABILITIES, lock_administration
from apps.accounts.management.password_input import read_validated_password
from apps.core.audit import record_event


class Command(BaseCommand):
    help='Create a Master Admin with explicitly entered identity, validated password and technical administration capabilities only.'
    def add_arguments(self,parser):
        for field in ['email','name','employee-id','department','designation']:
            parser.add_argument('--'+field,required=True)

    def handle(self,*args,**options):
        candidate=User(email=options['email'].strip().lower(),name=options['name'])
        raw=read_validated_password(candidate)
        try:
            with transaction.atomic():
                lock_administration()
                data={k:options[k] for k in ['email','name','employee_id','department','designation']}
                s=EmployeeInput(data=data);s.is_valid(raise_exception=True)
                values=dict(s.validated_data)
                user=User.objects.create_user(email=values.pop('email'),name=values.pop('name'),password=raw,is_master_admin=True)
                employee=Employee.objects.create(user=user,created_by=user,updated_by=user,**values)
                caps=Permission.objects.filter(content_type__app_label='accounts',codename__in=ADMIN_CAPABILITIES)
                if caps.count()!=len(ADMIN_CAPABILITIES): raise CommandError('Apply accounts migrations before provisioning.')
                user.user_permissions.add(*caps)
                record_event(actor=user,action='accounts.provision_master_admin',entity_type='accounts.employee',entity_id=employee.pk,
                    request_id=uuid.uuid4(),summary={'changed_fields':['account','profile','access'],'outcome':'trusted_command'})
        except (IntegrityError,ValidationError) as exc:
            raise CommandError('Employee ID or email is invalid or already provisioned.') from exc
        except Exception as exc:
            from rest_framework.exceptions import ValidationError as APIValidationError
            if isinstance(exc,APIValidationError): raise CommandError(str(exc.detail)) from exc
            raise
        self.stdout.write(self.style.SUCCESS(f'Master Admin provisioned: employee UUID {employee.pk}. No business permissions granted.'))
