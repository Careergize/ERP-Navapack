import logging
import django_filters
from django.db import IntegrityError
from django.db.models import Q
from rest_framework import mixins, viewsets, serializers
from rest_framework.response import Response
from rest_framework.generics import get_object_or_404
from rest_framework.exceptions import ValidationError
from apps.core.commands import execute_command, expected_version, lock_versioned, advance_version
from apps.masters.views import json_safe
from apps.accounts.employee_services import lock_administration
from apps.core.models import AuditEvent
from apps.accounts.employee_views import AuditEventSerializer
from .models import Warehouse, StorageLocation, StockIdentity
from .serializers import WarehouseSerializer, LocationSerializer, IdentitySerializer
from .authorization import require_actor, require_scope, oversight, scopes, lock_configuration, authority_snapshot


class ConfigurationViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    ordering = ['code','id']
    ordering_fields = ['code','created_at']
    search_fields = ['code','name']
    def handle_exception(self,exc):
        if getattr(exc,'status_code',None) in [401,403]:
            actor=self.request.user
            logging.getLogger('inventory.security').warning('Inventory authorization denied',extra={
                'request_id':str(self.request.request_id),'actor_id':str(actor.pk) if actor.is_authenticated else None,
                'action':self.capability(self.action in ['create','partial_update']),'outcome':'denied'})
        return super().handle_exception(exc)
    def capability(self,write=False):
        model=self.queryset.model
        if write and model is Warehouse:
            return 'inventory.configure_warehouses'
        return f'inventory.{"add" if self.action=="create" else "change" if write else "view"}_{model._meta.model_name}'
    def initial(self,request,*args,**kwargs):
        super().initial(request,*args,**kwargs)
        require_actor(request.user,self.capability(self.action in ['create','partial_update']))
    def get_queryset(self):
        qs=super().get_queryset()
        actor=self.request.user
        if oversight(actor): return qs
        ids=scopes(actor).filter(company_wide=False).values('warehouse_id')
        return qs.filter(pk__in=ids) if qs.model is Warehouse else qs.filter(warehouse_id__in=ids)
    def retrieve(self,request,*args,**kwargs):
        response=super().retrieve(request,*args,**kwargs)
        response['ETag']=f'"{response.data["version"]}"'
        return response
    def create(self,request): return self.write(request)
    def partial_update(self,request,pk=None): return self.write(request,pk)
    def write(self,request,pk=None):
        version=expected_version(request.headers.get('If-Match')) if pk else None
        actor=request.user
        def authorize():
            lock_administration()
            lock_configuration()
            require_actor(actor,self.capability(True))
            if self.queryset.model is Warehouse and pk is None:
                require_scope(actor)
            else:
                if pk:
                    obj=get_object_or_404(self.get_queryset(),pk=pk)
                    wh_id=obj.pk if isinstance(obj,Warehouse) else obj.warehouse_id
                else: wh_id=request.data.get('warehouse')
                if wh_id is not None: wh_id=serializers.UUIDField().run_validation(wh_id)
                require_scope(actor,wh_id)
        def operation():
            obj=lock_versioned(self.queryset.model,pk,version) if pk else None
            before=json_safe(self.get_serializer(obj).data) if obj else None
            serializer=self.get_serializer(obj,data=request.data,partial=bool(pk)); serializer.is_valid(raise_exception=True)
            if obj is None: obj=serializer.save(created_by=actor)
            else:
                obj=serializer.save()
                advance_version(obj,update_fields=[])
            after=json_safe(self.get_serializer(obj).data)
            return after,200 if pk else 201,{'entity_type':obj._meta.label_lower,'entity_id':obj.pk,'source_version':obj.version,
                'reason':serializer.change_reason,'summary':{'changed_fields':sorted(serializer.validated_data),'outcome':{
                    'status':'committed','before':before,'after':after,'authority':authority_snapshot(actor,self.capability(True),obj.pk if isinstance(obj,Warehouse) else obj.warehouse_id)}}}
        try:
            result,status,_=execute_command(actor=actor,scope='inventory-configuration',action=self.capability(True),key=request.headers.get('Idempotency-Key'),
                payload={'entity':self.queryset.model._meta.label_lower,'id':pk,'version':version,'data':request.data},request_id=request.request_id,authorize=authorize,operation=operation)
        except IntegrityError: raise ValidationError({'identity':'Identity, hierarchy, lifecycle or uniqueness constraint rejected the change.'})
        response=Response(result,status=status); response['ETag']=f'"{result["version"]}"'; return response


class WarehouseViewSet(ConfigurationViewSet):
    queryset=Warehouse.objects.all(); serializer_class=WarehouseSerializer
    filterset_fields=['is_active']


class LocationViewSet(ConfigurationViewSet):
    queryset=StorageLocation.objects.all(); serializer_class=LocationSerializer
    filterset_fields=['warehouse','parent','is_active','classification']


class IdentityViewSet(ConfigurationViewSet):
    queryset=StockIdentity.objects.all(); serializer_class=IdentitySerializer
    search_fields=['reference','source_system','source_reference','supplier_batch','physical_reference']
    ordering=['reference','id']; ordering_fields=['reference','created_at']
    filterset_fields=['warehouse','location','kind','ownership','lifecycle','parent']


class InventoryAuditFilter(django_filters.FilterSet):
    date_from=django_filters.IsoDateTimeFilter(field_name='timestamp',lookup_expr='gte')
    date_to=django_filters.IsoDateTimeFilter(field_name='timestamp',lookup_expr='lte')
    class Meta:
        model=AuditEvent
        fields=['actor','action','entity_type','entity_id','request_id']


class InventoryAuditViewSet(mixins.ListModelMixin,mixins.RetrieveModelMixin,viewsets.GenericViewSet):
    queryset=AuditEvent.objects.none()
    serializer_class=AuditEventSerializer
    filterset_class=InventoryAuditFilter
    ordering=['-timestamp','id']; ordering_fields=['timestamp','action']
    def handle_exception(self,exc):
        if getattr(exc,'status_code',None) in [401,403]:
            actor=self.request.user
            logging.getLogger('inventory.security').warning('Inventory history authorization denied',extra={
                'request_id':str(self.request.request_id),'actor_id':str(actor.pk) if actor.is_authenticated else None,
                'action':'inventory.view_inventory_audit','outcome':'denied'})
        return super().handle_exception(exc)
    def initial(self,request,*args,**kwargs):
        super().initial(request,*args,**kwargs)
        require_actor(request.user,'inventory.view_inventory_audit')
    def get_queryset(self):
        from .authorization import effective_codes
        actor=self.request.user; codes=effective_codes(actor)
        condition=Q(pk__in=[])
        wh_ids=None if oversight(actor) else scopes(actor).filter(company_wide=False).values('warehouse_id')
        warehouse=self.request.query_params.get('warehouse')
        if warehouse: warehouse=serializers.UUIDField().run_validation(warehouse)
        for model in [Warehouse,StorageLocation,StockIdentity]:
            if f'inventory.view_{model._meta.model_name}' not in codes: continue
            qs=model.objects.all()
            if wh_ids is not None: qs=qs.filter(pk__in=wh_ids) if model is Warehouse else qs.filter(warehouse_id__in=wh_ids)
            if warehouse: qs=qs.filter(pk=warehouse) if model is Warehouse else qs.filter(warehouse_id=warehouse)
            # Audit entity_id is text whereas domain primary keys are UUID.
            from django.db.models.functions import Cast
            from django.db.models import CharField
            condition |= Q(entity_type=model._meta.label_lower,entity_id__in=qs.annotate(audit_id=Cast('pk',output_field=CharField())).values('audit_id'))
        return AuditEvent.objects.filter(condition)
