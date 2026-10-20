from django.conf import settings
from django.db import models
from django.db.models.functions import Lower
from apps.core.models import VersionedModel


class Master(VersionedModel):
    name = models.CharField(max_length=240, db_index=True)
    code = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    source_system = models.CharField(max_length=120, blank=True)
    source_id = models.CharField(max_length=200, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')

    class Meta(VersionedModel.Meta):
        abstract = True
        constraints = VersionedModel.Meta.constraints + [
            models.UniqueConstraint(Lower('code'), condition=~models.Q(code=''), name='%(app_label)s_%(class)s_code_ci'),
            models.UniqueConstraint(fields=['source_system', 'source_id'], condition=~models.Q(source_id=''), name='%(app_label)s_%(class)s_source'),
            models.CheckConstraint(condition=(models.Q(source_id='', source_system='') | (~models.Q(source_id='') & ~models.Q(source_system=''))), name='%(app_label)s_%(class)s_source_pair'),
            models.CheckConstraint(condition=~models.Q(name=''), name='%(app_label)s_%(class)s_name'),
        ]


class Party(Master):
    contact_person = models.CharField(max_length=240, blank=True)
    phone = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    delivery_address = models.TextField(blank=True)
    tin = models.CharField(max_length=100, blank=True)
    customer_type = models.CharField(max_length=3, choices=[('B2B','B2B'),('B2C','B2C')], blank=True)

    class Meta(Master.Meta):
        abstract = True


class Customer(Party):
    pass


class Prospect(Party):
    linked_customer = models.ForeignKey(Customer, null=True, blank=True, on_delete=models.PROTECT, related_name='prospects')
    promoted_at = models.DateTimeField(null=True, editable=False)
    promoted_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name='+', editable=False)

    class Meta(Party.Meta):
        permissions = [('promote_prospect', 'Promote or link prospect')]


class Supplier(Master):
    material_supplied = models.TextField(blank=True)
    phone = models.CharField(max_length=100, blank=True)


class Department(Master):
    assigned_production_manager = models.CharField(max_length=240, blank=True)
    manager = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name='+')


class Unit(Master):
    dimension = models.CharField(max_length=30, choices=[(v,v) for v in ['mass','volume','count','package','length','other']])
    # No aliases or conversion ratios inferred from labels.


class Product(Master):
    category = models.CharField(max_length=120, blank=True, db_index=True)
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT)


class ProductVariant(Master):
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='variants')
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT)
    category = models.CharField(max_length=20, db_index=True, choices=[(v,v) for v in ['carrier-bags','flat-bags','packing']])
    subgroup = models.CharField(max_length=240, blank=True)
    customer = models.CharField(max_length=240, blank=True)
    item_details = models.TextField(blank=True)
    size = models.CharField(max_length=240, blank=True)
    brand = models.CharField(max_length=240, blank=True)
    packing_size = models.CharField(max_length=240, blank=True)
    pieces = models.PositiveIntegerField(null=True, blank=True)
    source_sheet = models.CharField(max_length=200, blank=True)
    source_row = models.PositiveIntegerField(null=True, blank=True)
    source_customer = models.CharField(max_length=240, blank=True)
    customer_inherited = models.BooleanField(default=False)
    source_unit = models.CharField(max_length=100, blank=True)
    data_notes = models.JSONField(default=list, blank=True)

    class Meta(Master.Meta):
        constraints = Master.Meta.constraints + [models.CheckConstraint(condition=models.Q(pieces__isnull=True) | models.Q(pieces__gt=0), name='variant_positive_pieces')]


class Material(Master):
    family = models.CharField(max_length=240, blank=True, db_index=True)
    category = models.CharField(max_length=20, db_index=True, choices=[(v,v) for v in ['virgin','recycled','ink']])
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT)
    min_level = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)

    class Meta(Master.Meta):
        constraints = Master.Meta.constraints + [models.CheckConstraint(condition=models.Q(min_level__isnull=True) | models.Q(min_level__gte=0), name='material_min_nonnegative')]


class Consumable(Master):
    category = models.CharField(max_length=20, db_index=True, choices=[('imported','Imported Spare'),('local','Local Spare')])
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT)
    min_level = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)

    class Meta(Master.Meta):
        constraints = Master.Meta.constraints + [models.CheckConstraint(condition=models.Q(min_level__isnull=True) | models.Q(min_level__gte=0), name='consumable_min_nonnegative')]


class Area(Master):
    department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.PROTECT)
    description = models.TextField(blank=True)


class Machine(Master):
    department = models.ForeignKey(Department, on_delete=models.PROTECT)
    area = models.ForeignKey(Area, null=True, blank=True, on_delete=models.PROTECT)
    type = models.CharField(max_length=100)  # Client-configured equipment classification.
