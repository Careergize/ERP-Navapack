import django_filters
from rest_framework import serializers
from .models import Employee, User, Role, Membership, RoleChangeRequest, EmployeeResetRequest
from .employee_services import permission_codes
from apps.masters.models import Department


class StrictInput(serializers.Serializer):
    def to_internal_value(self, data):
        unknown=set(data)-set(self.fields)
        if unknown: raise serializers.ValidationError({k:'Unknown or server-managed field.' for k in unknown})
        return super().to_internal_value(data)


class EmployeeInput(StrictInput):
    employee_id = serializers.CharField(max_length=100)
    name = serializers.CharField(max_length=200)
    email = serializers.EmailField(max_length=254)
    department = serializers.PrimaryKeyRelatedField(queryset=Department.objects.all())
    designation = serializers.CharField(max_length=200)
    reporting_manager = serializers.PrimaryKeyRelatedField(queryset=Employee.objects.all(), required=False, allow_null=True)

    def validate(self, data):
        employee=self.context.get('employee')
        if employee and 'employee_id' in data and data['employee_id'] != employee.employee_id:
            raise serializers.ValidationError({'employee_id':'Employee ID is immutable.'})
        if 'email' in data:
            data['email']=data['email'].strip().lower()
            peers=User.objects.filter(email__iexact=data['email'])
            if employee: peers=peers.exclude(pk=employee.user_id)
            if peers.exists(): raise serializers.ValidationError({'email':'Email already exists.'})
        if 'employee_id' in data:
            peers=Employee.objects.filter(employee_id__iexact=data['employee_id'])
            if employee: peers=peers.exclude(pk=employee.pk)
            if peers.exists(): raise serializers.ValidationError({'employee_id':'Employee ID already exists.'})
        if 'department' in data:
            department=Department.objects.select_for_update().get(pk=data['department'].pk)
            if not department.is_active: raise serializers.ValidationError({'department':'Select an active department.'})
            data['department']=department
        manager=data.get('reporting_manager')
        if manager:
            if not manager.user.is_active: raise serializers.ValidationError({'reporting_manager':'Select an active employee.'})
            seen=set()
            while manager:
                if manager.pk in seen or employee and manager.pk == employee.pk:
                    raise serializers.ValidationError({'reporting_manager':'Reporting chains cannot contain cycles.'})
                seen.add(manager.pk); manager=manager.reporting_manager
        return data


class RoleChangeSerializer(serializers.ModelSerializer):
    class Meta:
        model=RoleChangeRequest
        fields=['id','version','employee','role','operation','assignment_id','status','requires_independent_approval','requested_by','approved_by','created_at','applied_at']


class ResetRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model=EmployeeResetRequest
        fields=['id','status','requested_by','completed_by','created_at','completed_at']


class EmployeeSerializer(serializers.ModelSerializer):
    name=serializers.CharField(source='user.name')
    email=serializers.EmailField(source='user.email')
    is_active=serializers.BooleanField(source='user.is_active')
    is_master_admin=serializers.BooleanField(source='user.is_master_admin')
    role_assignments=serializers.SerializerMethodField()
    permissions=serializers.SerializerMethodField()
    pending_access_requests=serializers.SerializerMethodField()
    reset_requests=ResetRequestSerializer(many=True,read_only=True)
    class Meta:
        model=Employee
        fields=['id','version','user','employee_id','name','email','department','designation','is_active','is_master_admin','reporting_manager','role_assignments','permissions','pending_access_requests','reset_requests','created_at','updated_at','created_by','updated_by']

    def get_role_assignments(self,obj):
        return [{'id':str(m.pk),'role':str(m.role_id),'code':m.role.code,'created_at':m.created_at} for m in Membership.objects.filter(user=obj.user).select_related('role').order_by('created_at','id')]
    def get_permissions(self,obj):
        return sorted(obj.user.get_all_permissions())
    def get_pending_access_requests(self,obj):
        return RoleChangeSerializer(obj.access_requests.filter(status='pending').order_by('created_at','id'),many=True).data


class RoleSerializer(serializers.ModelSerializer):
    permissions=serializers.SerializerMethodField()
    assignment_policy=serializers.SerializerMethodField()
    class Meta:
        model=Role
        fields=['id','code','name','version','governed','approved_revision','permissions','assignment_policy','created_at','updated_at']
    def get_permissions(self,obj): return permission_codes(obj)
    def get_assignment_policy(self,obj):
        from .models import RoleAssignmentPolicy
        from .employee_services import permission_digest
        policy=RoleAssignmentPolicy.objects.filter(role=obj).first()
        if not policy: return None
        return {'version':policy.version,'requires_independent_approval':policy.requires_independent_approval,'current':policy.permission_digest==permission_digest(obj)}


class EmployeeFilter(django_filters.FilterSet):
    is_active=django_filters.BooleanFilter(field_name='user__is_active')
    class Meta:
        model=Employee
        fields=['is_active','department','reporting_manager','employee_id']
