import json
import uuid
from django.db import IntegrityError
from rest_framework.generics import get_object_or_404
from rest_framework import mixins, viewsets, serializers
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from apps.core.commands import execute_command, expected_version, advance_version
from apps.core.api import CommandConflict
from apps.core.models import AuditEvent
from .models import Employee, User, Role, Membership, RoleChangeRequest, EmployeeResetRequest
from .employee_services import lock_administration, require_admin, managed_employee, bump, request_role_change, apply_role_change, require_target_ceiling
from .employee_serializers import EmployeeInput, EmployeeSerializer, EmployeeFilter, RoleSerializer, RoleChangeSerializer, ResetRequestSerializer, StrictInput


def safe(value): return json.loads(JSONRenderer().render(value))


def access_outcome(change):
    return {'status':change.status,'change_id':str(change.pk),'role_id':str(change.role_id),
        'assignment_id':str(change.assignment_id) if change.assignment_id else None,
        'operation':change.operation,'independent_approval':change.requires_independent_approval}


def event(employee, fields, outcome='success'):
    return {'entity_type':'accounts.employee','entity_id':employee.pk,'source_version':employee.version,
        'summary':{'changed_fields':sorted(fields),'outcome':outcome}}


class MasterAdminPermission(BasePermission):
    def has_permission(self,request,view):
        if not request.user.is_authenticated: return False
        capability=view.action_capabilities.get(getattr(view,'action',''))
        if not capability: return False
        require_admin(request.user,capability)
        return True
    def has_object_permission(self,request,view,obj):
        # Explicit shared employee directory, only behind fresh Master Admin gate.
        require_admin(request.user,view.action_capabilities[view.action])
        return True


class AdminReadViewSet(mixins.ListModelMixin,mixins.RetrieveModelMixin,viewsets.GenericViewSet):
    permission_classes=[MasterAdminPermission]
    def finalize_response(self,request,response,*args,**kwargs):
        response=super().finalize_response(request,response,*args,**kwargs)
        response['Cache-Control']='no-store'
        return response


class EmployeeViewSet(AdminReadViewSet):
    queryset=Employee.objects.select_related('user','department','reporting_manager').all()
    serializer_class=EmployeeSerializer
    filterset_class=EmployeeFilter
    search_fields=['employee_id','user__name','user__email','designation']
    ordering_fields=['employee_id','user__name','created_at','updated_at']
    ordering=['-created_at','id']
    action_capabilities={
        'list':'view_employee','retrieve':'view_employee','create':'add_employee','partial_update':'change_employee',
        'activate':'manage_employee_status','deactivate':'manage_employee_status','password_reset':'initiate_employee_reset',
        'role_assignments':'manage_employee_roles','remove_role':'manage_employee_roles','approve_access':'approve_employee_roles',
        'cancel_access':'manage_employee_roles',
    }

    def command(self,request,operation,pk=None,extra=None):
        from rest_framework.exceptions import NotFound
        for identity in ([pk] if pk else []) + list((extra or {}).values()):
            try:
                uuid.UUID(str(identity))
            except (ValueError, TypeError, AttributeError):
                raise NotFound()
        version=expected_version(request.headers.get('If-Match')) if pk else None
        payload={'employee':pk,'version':version,'data':request.data,**(extra or {})}
        capability=self.action_capabilities[self.action]
        def authorize():
            lock_administration()
            actor=require_admin(request.user,capability)
            if pk:
                employee=get_object_or_404(Employee.objects.select_related('user'),pk=pk)
                if employee.user_id==actor.pk or employee.user.is_master_admin or employee.user.is_superuser or employee.user.is_staff:
                    from rest_framework.exceptions import PermissionDenied
                    raise PermissionDenied('Self and privileged-account changes require trusted tooling.')
            return actor
        def perform():
            actor=require_admin(request.user,capability)
            employee=managed_employee(actor,pk,version) if pk else None
            return operation(actor,employee)
        try:
            result,status,_=execute_command(actor=request.user,scope='employee-administration',action='accounts.'+self.action,
                key=request.headers.get('Idempotency-Key'),payload=safe(payload),request_id=request.request_id,authorize=authorize,operation=perform)
        except IntegrityError:
            raise serializers.ValidationError({'identity':'An employee ID, email or membership conflicts with existing data.'})
        response=Response(result,status=status)
        response['ETag']=f'"{result.get("employee_version",result.get("version",1))}"'
        if status==201 and self.action=='create': response['Location']=request.path+result['id']+'/'
        return response

    def retrieve(self,request,*args,**kwargs):
        response=super().retrieve(request,*args,**kwargs)
        response['ETag']=f'"{response.data["version"]}"'
        return response

    def create(self,request):
        def operation(actor,_):
            s=EmployeeInput(data=request.data);s.is_valid(raise_exception=True)
            data=dict(s.validated_data)
            user=User.objects.create_user(email=data.pop('email'),name=data.pop('name'))
            employee=Employee.objects.create(user=user,created_by=actor,updated_by=actor,**data)
            return safe(EmployeeSerializer(employee).data),201,event(employee,['account','profile'])
        return self.command(request,operation)

    def partial_update(self,request,pk=None):
        def operation(actor,employee):
            s=EmployeeInput(data=request.data,partial=True,context={'employee':employee});s.is_valid(raise_exception=True)
            data=dict(s.validated_data)
            if 'email' in data: require_target_ceiling(actor,employee)
            for field in ['name','email']:
                if field in data: setattr(employee.user,field,data.pop(field))
            employee.user.save(update_fields=['name','email','updated_at'])
            for field,value in data.items(): setattr(employee,field,value)
            employee.save()
            bump(employee,actor)
            return safe(EmployeeSerializer(employee).data),200,event(employee,s.validated_data.keys())
        return self.command(request,operation,pk)

    def status_command(self,request,pk,active):
        if request.data: raise serializers.ValidationError('Status commands require an empty body.')
        def operation(actor,employee):
            if employee.user.is_active==active: raise CommandConflict('Employee already has this status.')
            if active: require_target_ceiling(actor,employee)
            employee.user.is_active=active
            if not active:
                # Password fingerprint invalidates prior JWTs even after reactivation.
                employee.user.set_unusable_password()
            employee.user.save(update_fields=['is_active','password','updated_at'])
            bump(employee,actor)
            return safe(EmployeeSerializer(employee).data),200,event(employee,['is_active','access'],'activated' if active else 'deactivated')
        return self.command(request,operation,pk)

    @action(detail=True,methods=['post'])
    def activate(self,request,pk=None): return self.status_command(request,pk,True)

    @action(detail=True,methods=['post'])
    def deactivate(self,request,pk=None): return self.status_command(request,pk,False)

    @action(detail=True,methods=['post'],url_path='password-reset')
    def password_reset(self,request,pk=None):
        if request.data: raise serializers.ValidationError('Reset initiation requires an empty body.')
        def operation(actor,employee):
            if not employee.user.is_active: raise serializers.ValidationError('Activate the employee before requesting an access reset.')
            require_target_ceiling(actor,employee)
            employee.reset_requests.filter(status='pending').update(status='superseded')
            reset=EmployeeResetRequest.objects.create(employee=employee,requested_by=actor,expected_employee_version=employee.version+1)
            bump(employee,actor)
            result=safe(ResetRequestSerializer(reset).data);result['employee_version']=employee.version
            return result,201,event(employee,['access'],'reset_requested:'+str(reset.pk))
        return self.command(request,operation,pk)

    @action(detail=True,methods=['post'],url_path='role-assignments')
    def role_assignments(self,request,pk=None):
        class Input(StrictInput): role=serializers.UUIDField()
        s=Input(data=request.data);s.is_valid(raise_exception=True)
        def operation(actor,employee):
            change=request_role_change(actor,employee,s.validated_data['role'],'add')
            result=safe(RoleChangeSerializer(change).data);result['employee_version']=employee.version
            return result,201,event(employee,['roles'],access_outcome(change))
        return self.command(request,operation,pk)

    @action(detail=True,methods=['delete'],url_path=r'role-assignments/(?P<assignment_id>[0-9a-fA-F-]{36})')
    def remove_role(self,request,pk=None,assignment_id=None):
        if request.data: raise serializers.ValidationError('Removal requires an empty body.')
        def operation(actor,employee):
            membership=get_object_or_404(Membership,user=employee.user,pk=assignment_id)
            change=request_role_change(actor,employee,membership.role_id,'remove',membership.pk)
            result=safe(RoleChangeSerializer(change).data);result['employee_version']=employee.version
            return result,200,event(employee,['roles'],access_outcome(change))
        return self.command(request,operation,pk,{'assignment_id':assignment_id})

    @action(detail=True,methods=['post'],url_path=r'access-requests/(?P<change_id>[0-9a-fA-F-]{36})/approve')
    def approve_access(self,request,pk=None,change_id=None):
        if request.data: raise serializers.ValidationError('Approval requires an empty body.')
        def operation(actor,employee):
            change=get_object_or_404(RoleChangeRequest.objects.select_for_update(),pk=change_id,employee=employee)
            apply_role_change(actor,employee,change);bump(employee,actor)
            result=safe(RoleChangeSerializer(change).data);result['employee_version']=employee.version
            return result,200,event(employee,['roles'],access_outcome(change))
        return self.command(request,operation,pk,{'change_id':change_id})

    @action(detail=True,methods=['post'],url_path=r'access-requests/(?P<change_id>[0-9a-fA-F-]{36})/cancel')
    def cancel_access(self,request,pk=None,change_id=None):
        if request.data: raise serializers.ValidationError('Cancellation requires an empty body.')
        def operation(actor,employee):
            change=get_object_or_404(RoleChangeRequest.objects.select_for_update(),pk=change_id,employee=employee,status='pending')
            change.status='cancelled';advance_version(change,update_fields=['status']);bump(employee,actor)
            result=safe(RoleChangeSerializer(change).data);result['employee_version']=employee.version
            return result,200,event(employee,['roles'],access_outcome(change))
        return self.command(request,operation,pk,{'change_id':change_id})


class AuditEventSerializer(serializers.ModelSerializer):
    class Meta:
        model=AuditEvent
        fields=['id','actor','action','entity_type','entity_id','timestamp','request_id','summary','reason','source_version']


class AdminAuditViewSet(AdminReadViewSet):
    queryset=AuditEvent.objects.all()
    serializer_class=AuditEventSerializer
    action_capabilities={'list':'view_admin_audit','retrieve':'view_admin_audit'}
    filterset_fields=['actor','action','entity_type','entity_id','request_id']
    search_fields=[]
    ordering_fields=['timestamp','action']
    ordering=['-timestamp','id']
