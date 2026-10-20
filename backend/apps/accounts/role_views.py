"""Governed capability publication. No business capabilities are seeded here."""
from django.contrib.auth.models import Permission
from django.db import IntegrityError
from django.utils import timezone
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from apps.core.commands import execute_command, expected_version, lock_versioned, advance_version, payload_hash
from apps.core.api import CommandConflict, StaleReview
from .models import Role, Membership, RoleAssignmentPolicy, RoleCapabilityRevision
from .employee_services import (lock_administration, require_admin, RESERVED_APPS,
    permission_digest, raw_permission_codes, permission_codes)
from .employee_views import AdminReadViewSet, safe
from .employee_serializers import RoleSerializer, StrictInput


class RoleInput(StrictInput):
    code = serializers.SlugField(max_length=50)
    name = serializers.CharField(max_length=100)


class RevisionInput(StrictInput):
    permission_codes = serializers.ListField(child=serializers.CharField(max_length=200), allow_empty=True)
    requires_independent_approval = serializers.BooleanField()

    def validate_permission_codes(self, codes):
        if len(codes) != len(set(codes)):
            raise ValidationError('Duplicate capabilities.')
        return sorted(codes)


class RevisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoleCapabilityRevision
        fields = '__all__'


def baseline(role):
    policy = RoleAssignmentPolicy.objects.filter(role=role).first()
    # Snapshot the exact affected membership set and relevant account status.
    members = [{'id':str(m.pk),'user':str(m.user_id),'active':m.user.is_active,
                'master_admin':m.user.is_master_admin,'staff':m.user.is_staff,'superuser':m.user.is_superuser}
               for m in Membership.objects.filter(role=role).select_related('user').order_by('id')]
    return {'raw_digest':payload_hash(raw_permission_codes(role)),
            'approved_revision':str(role.approved_revision_id) if role.approved_revision_id else None,
            'policy':None if policy is None else {'version':policy.version,'digest':policy.permission_digest,
                'independent':policy.requires_independent_approval},'members':members}


def verify_ceiling(actor, codes):
    definitions = {f'{app}.{code}':pk for app,code,pk in Permission.objects.values_list('content_type__app_label','codename','pk')}
    if any(c not in definitions for c in codes):
        raise ValidationError({'permission_codes':'Unknown capability.'})
    if any(c.split('.')[0] in RESERVED_APPS for c in codes):
        raise PermissionDenied('Technical administration capabilities require trusted provisioning.')
    if not set(codes).issubset(actor.get_all_permissions()):
        raise PermissionDenied('Capabilities exceed your delegation ceiling.')
    return [definitions[c] for c in codes]


def protect_members(actor, role):
    if Membership.objects.filter(role=role, user=actor).exists():
        raise PermissionDenied('You cannot change capabilities of a role you hold.')
    members = Membership.objects.filter(role=role).select_related('user')
    if any(m.user.is_master_admin or m.user.is_staff or m.user.is_superuser for m in members):
        raise PermissionDenied('Privileged-account roles require trusted maintenance.')


def evidence(role, revision=None):
    return {'entity_type':'accounts.role','entity_id':role.pk,'source_version':role.version,
            'summary':{'changed_fields':['role_definition'], 'outcome':{
                'revision_id':str(revision.pk) if revision else None,
                'state':revision.status if revision else 'created'}}}


class RoleViewSet(AdminReadViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    search_fields = ['code','name']
    ordering_fields = ['code','name','created_at','updated_at']
    ordering = ['code','id']
    filterset_fields = ['code','governed']
    action_capabilities = {'list':'view_role','retrieve':'view_role','create':'manage_role_capabilities',
        'partial_update':'manage_role_capabilities','capability_revisions':'manage_role_capabilities',
        'capability_catalog':'manage_role_capabilities',
        'approve_revision':'approve_role_capabilities','cancel_revision':'manage_role_capabilities'}

    def command(self, request, operation, pk=None, revision_id=None):
        version = expected_version(request.headers.get('If-Match')) if pk else None
        capability = self.action_capabilities[self.action]
        def authorize():
            lock_administration()
            require_admin(request.user, capability)
            if pk:
                role = get_object_or_404(Role, pk=pk)
                protect_members(request.user, role)
        def perform():
            actor = require_admin(request.user, capability)
            role = lock_versioned(Role, pk, version) if pk else None
            return operation(actor,role)
        try:
            result,status,_ = execute_command(actor=request.user,scope='role-administration',
                action='accounts.'+self.action,key=request.headers.get('Idempotency-Key'),
                payload=safe({'role':pk,'revision':revision_id,'version':version,'data':request.data}),
                request_id=request.request_id,authorize=authorize,operation=perform)
        except IntegrityError:
            raise ValidationError('Role code or pending revision conflicts with existing data.')
        response = Response(result,status=status)
        response['ETag'] = f'"{result.get("role_version",result.get("version",1))}"'
        return response

    def retrieve(self,request,*args,**kwargs):
        response=super().retrieve(request,*args,**kwargs)
        response['ETag']=f'"{response.data["version"]}"'
        return response

    def create(self,request):
        def operation(actor,_):
            data=RoleInput(data=request.data); data.is_valid(raise_exception=True)
            role=Role.objects.create(governed=True,**data.validated_data)
            return safe(RoleSerializer(role).data),201,evidence(role)
        return self.command(request,operation)

    @action(detail=False,methods=['get'],url_path='capability-catalog')
    def capability_catalog(self,request):
        actor=require_admin(request.user,'manage_role_capabilities')
        held=actor.get_all_permissions()
        definitions=[{'code':f'{p.content_type.app_label}.{p.codename}','name':p.name}
            for p in Permission.objects.select_related('content_type').exclude(content_type__app_label__in=RESERVED_APPS).order_by('content_type__app_label','codename')
            if f'{p.content_type.app_label}.{p.codename}' in held]
        return self.get_paginated_response(self.paginate_queryset(definitions))

    def partial_update(self,request,pk=None):
        def operation(actor,role):
            data=RoleInput(data=request.data,partial=True);data.is_valid(raise_exception=True)
            if role.capability_revisions.filter(status='pending').exists():
                raise CommandConflict('Cancel pending capability review before editing role metadata.')
            for field,value in data.validated_data.items(): setattr(role,field,value)
            advance_version(role,update_fields=list(data.validated_data))
            return safe(RoleSerializer(role).data),200,evidence(role)
        return self.command(request,operation,pk)

    @action(detail=True,methods=['get','post'],url_path='capability-revisions')
    def capability_revisions(self,request,pk=None):
        if request.method=='GET':
            role=self.get_object()
            page=self.paginate_queryset(role.capability_revisions.order_by('-created_at','id'))
            return self.get_paginated_response(RevisionSerializer(page,many=True).data)
        def operation(actor,role):
            data=RevisionInput(data=request.data);data.is_valid(raise_exception=True)
            verify_ceiling(actor,permission_codes(role))
            verify_ceiling(actor,data.validated_data['permission_codes'])
            if role.capability_revisions.filter(status='pending').exists():
                raise CommandConflict('Cancel the pending revision before proposing another.')
            state=baseline(role)
            advance_version(role,update_fields=[])
            revision=RoleCapabilityRevision.objects.create(role=role,baseline=state,
                requested_by=actor,expected_role_version=role.version,**data.validated_data)
            result=safe(RevisionSerializer(revision).data);result['role_version']=role.version
            return result,201,evidence(role,revision)
        return self.command(request,operation,pk)

    @action(detail=True,methods=['post'],url_path=r'capability-revisions/(?P<revision_id>[^/.]+)/approve')
    def approve_revision(self,request,pk=None,revision_id=None):
        if request.data: raise ValidationError('Approval requires an empty body.')
        def operation(actor,role):
            revision=get_object_or_404(RoleCapabilityRevision.objects.select_for_update(),pk=revision_id,role=role,status='pending')
            if actor.pk==revision.requested_by_id:
                raise PermissionDenied('Independent capability approval is required.')
            maker=require_admin(revision.requested_by,'manage_role_capabilities')
            protect_members(maker,role)
            verify_ceiling(maker,revision.permission_codes)
            verify_ceiling(maker,permission_codes(role))
            verify_ceiling(actor,permission_codes(role))
            ids=verify_ceiling(actor,revision.permission_codes)
            if role.version!=revision.expected_role_version or baseline(role)!=revision.baseline:
                raise StaleReview('Role policy or affected memberships changed; cancel and re-review.')
            revision.status='applied';revision.approved_by=actor;revision.applied_at=timezone.now()
            advance_version(revision,update_fields=['status','approved_by','applied_at'])
            role.permissions.set(ids)
            role.governed=True;role.approved_revision=revision
            advance_version(role,update_fields=['governed','approved_revision'])
            policy,created=RoleAssignmentPolicy.objects.get_or_create(role=role,defaults={
                'requires_independent_approval':revision.requires_independent_approval,
                'permission_digest':permission_digest(role),'configured_by':actor})
            if not created:
                policy.requires_independent_approval=revision.requires_independent_approval
                policy.permission_digest=permission_digest(role);policy.configured_by=actor
                advance_version(policy,update_fields=['requires_independent_approval','permission_digest','configured_by'])
            result=safe(RevisionSerializer(revision).data);result['role_version']=role.version
            return result,200,evidence(role,revision)
        return self.command(request,operation,pk,revision_id)

    @action(detail=True,methods=['post'],url_path=r'capability-revisions/(?P<revision_id>[^/.]+)/cancel')
    def cancel_revision(self,request,pk=None,revision_id=None):
        if request.data: raise ValidationError('Cancellation requires an empty body.')
        def operation(actor,role):
            revision=get_object_or_404(RoleCapabilityRevision.objects.select_for_update(),pk=revision_id,role=role,status='pending')
            revision.status='cancelled';advance_version(revision,update_fields=['status'])
            advance_version(role,update_fields=[])
            result=safe(RevisionSerializer(revision).data);result['role_version']=role.version
            return result,200,evidence(role,revision)
        return self.command(request,operation,pk,revision_id)
