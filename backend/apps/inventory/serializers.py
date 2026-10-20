from rest_framework import serializers
from django.db import models
from apps.masters.serializers import StrictSerializer
from .models import Warehouse, StorageLocation, StockIdentity


class ConfigurationSerializer(StrictSerializer):
    reason = serializers.CharField(write_only=True, max_length=1000)
    def validate(self, attrs):
        self.change_reason = attrs.pop('reason', None)
        if not self.change_reason:
            raise serializers.ValidationError({'reason':'A reason is required for every change.'})
        # Inventory provenance is source_reference, not the master's source_id.
        for field,value in list(attrs.items()):
            if isinstance(value,models.Model):
                value=type(value).objects.select_for_update().get(pk=value.pk)
                attrs[field]=value
                if hasattr(value,'is_active') and not value.is_active:
                    raise serializers.ValidationError({field:'Select an active reference.'})
        if 'code' in attrs:
            peers=self.Meta.model.objects.filter(code__iexact=attrs['code'])
            if self.instance: peers=peers.exclude(pk=self.instance.pk)
            if peers.exists(): raise serializers.ValidationError({'code':'Code already exists.'})
        if self.instance:
            if isinstance(self.instance, StockIdentity):
                for field in attrs:
                    if field != 'lifecycle' and attrs[field] != getattr(self.instance,field):
                        raise serializers.ValidationError({field:'Identity and provenance are immutable.'})
            if isinstance(self.instance, StorageLocation) and 'warehouse' in attrs and attrs['warehouse'].pk != self.instance.warehouse_id:
                raise serializers.ValidationError({'warehouse':'Warehouse identity is immutable.'})
        return attrs


class WarehouseSerializer(ConfigurationSerializer):
    custody_function = serializers.SerializerMethodField()
    def get_custody_function(self,obj):
        return 'STORES' if obj.custody_department_id else 'UNRESOLVED'
    class Meta:
        model = Warehouse
        fields = '__all__'
        read_only_fields = ['id','version','created_at','updated_at','created_by']
        validators = []


class LocationSerializer(ConfigurationSerializer):
    class Meta(WarehouseSerializer.Meta):
        model = StorageLocation
    def validate(self, attrs):
        attrs = super().validate(attrs)
        wh = attrs.get('warehouse',getattr(self.instance,'warehouse',None))
        parent = attrs.get('parent',getattr(self.instance,'parent',None))
        if not wh.is_active:
            raise serializers.ValidationError({'warehouse':'Warehouse is inactive.'})
        seen = {self.instance.pk} if self.instance else set()
        while parent:
            if parent.pk in seen or parent.warehouse_id != wh.pk:
                raise serializers.ValidationError({'parent':'Cycle or cross-warehouse parent.'})
            if not parent.is_active:
                raise serializers.ValidationError({'parent':'Parent is inactive.'})
            seen.add(parent.pk); parent = parent.parent
        return attrs


class IdentitySerializer(ConfigurationSerializer):
    operational_status = serializers.SerializerMethodField()
    def get_operational_status(self,obj):
        return 'UNAVAILABLE_PHASE_3A_NO_POSTING'
    class Meta(WarehouseSerializer.Meta):
        model = StockIdentity
        read_only_fields = WarehouseSerializer.Meta.read_only_fields + ['reference']
    def validate(self, attrs):
        attrs = super().validate(attrs)
        if self.instance:
            if self.instance.lifecycle == 'RETIRED' and attrs.get('lifecycle','RETIRED') != 'RETIRED':
                raise serializers.ValidationError({'lifecycle':'Retirement is terminal.'})
            return attrs
        wh = attrs['warehouse']; loc=attrs.get('location')
        if not wh.is_active or (loc and (loc.warehouse_id != wh.pk or not loc.is_active)):
            raise serializers.ValidationError({'location':'Use an active location in the selected active warehouse.'})
        items=[attrs.get(k) for k in ['material','variant','consumable'] if attrs.get(k)]
        if len(items)!=1 or items[0].unit_id != attrs['unit'].pk:
            raise serializers.ValidationError({'unit':'Exactly one existing item with its primary unit is required.'})
        own=attrs.get('ownership','UNRESOLVED'); customer=attrs.get('owner_customer'); supplier=attrs.get('owner_supplier')
        if (own=='CUSTOMER') != bool(customer) or (own=='SUPPLIER') != bool(supplier) or (own!='UNRESOLVED' and not attrs.get('ownership_evidence')):
            raise serializers.ValidationError({'ownership':'Exact owner shape and ownership evidence required.'})
        parent=attrs.get('parent')
        if parent:
            keys=['warehouse','material','variant','consumable','unit','ownership','owner_customer','owner_supplier','ownership_evidence']
            for k in keys:
                default='UNRESOLVED' if k=='ownership' else '' if k=='ownership_evidence' else None
                if attrs.get(k,default)!=getattr(parent,k):
                    raise serializers.ValidationError({'parent':'Parent must have the same item, warehouse, unit and ownership identity.'})
            if parent.lifecycle!='REGISTERED':
                raise serializers.ValidationError({'parent':'Parent is retired.'})
        return attrs
