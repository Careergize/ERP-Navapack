from django.db import models
from rest_framework import serializers
from . import models as m


class StrictSerializer(serializers.ModelSerializer):
    def to_internal_value(self, data):
        unknown = set(data) - set(self.fields)
        protected = {k for k in data if k in self.fields and self.fields[k].read_only}
        if unknown or protected:
            raise serializers.ValidationError({k: 'Unknown or server-managed field.' for k in unknown | protected})
        return super().to_internal_value(data)

    def validate(self, attrs):
        instance = self.instance
        for field, value in attrs.items():
            if isinstance(value, models.Model):
                # Caller runs validation inside command transaction. Lock references so
                # deactivation cannot race acceptance of a new reference.
                value = type(value).objects.select_for_update().get(pk=value.pk)
                attrs[field] = value
                if hasattr(value, 'is_active') and not value.is_active and (not instance or getattr(instance, field + '_id', None) != value.pk):
                    raise serializers.ValidationError({field: 'Select an active reference.'})
        source_system = attrs.get('source_system', getattr(instance, 'source_system', ''))
        source_id = attrs.get('source_id', getattr(instance, 'source_id', ''))
        if hasattr(self.Meta.model, 'source_system') and bool(source_system) != bool(source_id):
            raise serializers.ValidationError({'source_id': 'Supply both source_system and source_id.'})
        if instance and ('source_id' in attrs or 'source_system' in attrs):
            if source_id != instance.source_id or source_system != instance.source_system:
                raise serializers.ValidationError({'source_id': 'Source identity is immutable.'})
        if 'data_notes' in attrs and (not isinstance(attrs['data_notes'],list) or not all(isinstance(x,str) for x in attrs['data_notes'])):
            raise serializers.ValidationError({'data_notes':'Use a list of text notes.'})
        if 'min_level' in attrs and attrs['min_level'] is not None and attrs['min_level'] < 0:
            raise serializers.ValidationError({'min_level': 'Must be nonnegative.'})
        if 'pieces' in attrs and attrs['pieces'] is not None and attrs['pieces'] < 1:
            raise serializers.ValidationError({'pieces': 'Must be positive.'})
        if isinstance(instance, m.Unit) and any(k in attrs and attrs[k] != getattr(instance,k) for k in ['code','dimension']):
            raise serializers.ValidationError({'unit': 'Create a new unit identity to change code or dimension.'})
        if isinstance(instance, (m.Product,m.ProductVariant,m.Material,m.Consumable)) and 'unit' in attrs and attrs['unit'].pk != instance.unit_id:
            raise serializers.ValidationError({'unit': 'Unit identity is immutable; create a new master.'})
        if isinstance(instance, m.ProductVariant) and 'product' in attrs and attrs['product'].pk != instance.product_id:
            raise serializers.ValidationError({'product':'Variant parent identity is immutable.'})
        department = attrs.get('department', getattr(instance, 'department', None))
        area = attrs.get('area', getattr(instance, 'area', None))
        if area and area.department_id and department and area.department_id != department.pk:
            raise serializers.ValidationError({'area': 'Area belongs to another department.'})
        if hasattr(self.Meta.model, 'source_system'):
            peers = self.Meta.model.objects.all()
            if instance: peers = peers.exclude(pk=instance.pk)
            if source_id and peers.filter(source_system=source_system, source_id=source_id).exists():
                raise serializers.ValidationError({'source_id': 'Source identity already exists.'})
            code = attrs.get('code', getattr(instance,'code',''))
            if code and peers.filter(code__iexact=code).exists():
                raise serializers.ValidationError({'code': 'Code already exists.'})
        return attrs


def serializer_for(model):
    readonly = ['id','version','created_at','updated_at','created_by','updated_by','linked_customer','promoted_at','promoted_by']
    meta = type('Meta', (), {'model': model, 'fields': '__all__', 'read_only_fields': readonly, 'validators': []})
    return type(model.__name__ + 'Serializer', (StrictSerializer,), {'Meta': meta})


RESOURCES = {
    'customers': m.Customer, 'prospects': m.Prospect, 'suppliers': m.Supplier,
    'departments': m.Department, 'units': m.Unit, 'products': m.Product,
    'finished-goods': m.ProductVariant, 'raw-materials': m.Material,
    'consumables': m.Consumable, 'machines': m.Machine, 'areas': m.Area,
}
