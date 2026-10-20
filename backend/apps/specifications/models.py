from django.db import models
from apps.masters.models import Master, Unit, Material, Department, Machine
from apps.core.models import VersionedModel
from django.conf import settings


def amount(null=False):
    return models.DecimalField(max_digits=20, decimal_places=6, null=null, blank=null)


class ProductModel(Master):
    category = models.CharField(max_length=120, blank=True)


class ProductModelRevision(VersionedModel):
    model = models.ForeignKey(ProductModel, on_delete=models.PROTECT, related_name='revisions')
    number = models.PositiveIntegerField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    name = models.CharField(max_length=240)
    description = models.TextField(blank=True)
    specifications = models.TextField(blank=True)
    dimensions = models.CharField(max_length=240, blank=True)
    default_unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name='+')
    batch_unit = models.ForeignKey(Unit, null=True, blank=True, on_delete=models.PROTECT, related_name='+')
    batch_quantity = amount(True)
    recipe_mode = models.CharField(max_length=20, choices=[('quantities','quantities'),('percentages','percentages')])
    waste_percent = amount(True)
    overheads = amount(True)
    currency = models.CharField(max_length=3, choices=[('USD','USD'),('UGX','UGX')], blank=True)
    markup_percent = amount(True)
    tax_percent = amount(True)
    bill_of_materials = models.TextField(blank=True)
    legacy_stages = models.JSONField(default=list, blank=True)
    reference_snapshot = models.JSONField(default=dict, editable=False)
    sealed = models.BooleanField(default=False, editable=False)

    class Meta(VersionedModel.Meta):
        constraints = VersionedModel.Meta.constraints + [
            models.UniqueConstraint(fields=['model','number'], name='model_revision_number'),
            models.CheckConstraint(condition=models.Q(number__gt=0), name='revision_number_positive'),
        ]


class RevisionLine(VersionedModel):
    source_id = models.CharField(max_length=200, blank=True)
    class Meta(VersionedModel.Meta):
        abstract = True


class RecipeLine(RevisionLine):
    revision = models.ForeignKey(ProductModelRevision, on_delete=models.PROTECT, related_name='recipe')
    material = models.ForeignKey(Material, on_delete=models.PROTECT)
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name='+')
    quantity = amount(True)
    percentage = amount(True)
    currency = models.CharField(max_length=3, choices=[('USD','USD'),('UGX','UGX')], blank=True)
    price = amount(True)
    price_unit = models.ForeignKey(Unit, null=True, blank=True, on_delete=models.PROTECT, related_name='+')
    exchange_rate = amount(True)
    cost_group = models.CharField(max_length=10, choices=[('material','material'),('ink','ink')])

    class Meta(RevisionLine.Meta):
        constraints = RevisionLine.Meta.constraints + [models.UniqueConstraint(fields=['revision','material'], name='revision_distinct_material')]


class ModelRouteStage(RevisionLine):
    revision = models.ForeignKey(ProductModelRevision, on_delete=models.PROTECT, related_name='routing')
    name = models.CharField(max_length=240)
    sequence = models.PositiveIntegerField()
    required = models.BooleanField(default=True)
    kind = models.CharField(max_length=30, choices=[(v,v) for v in ['production','stock','quality','transfer','other']])
    department = models.ForeignKey(Department, on_delete=models.PROTECT)
    machine = models.ForeignKey(Machine, null=True, blank=True, on_delete=models.PROTECT)
    input_unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name='+')
    output_unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name='+')
    waste_unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name='+')
    expected_input = amount(True)
    expected_output = amount(True)
    planned_waste_percent = amount(True)
    remarks = models.TextField(blank=True)
    instructions = models.TextField(blank=True)
    legacy_stage = models.CharField(max_length=100, blank=True)
    checkpoint_template_ids = models.JSONField(default=list, blank=True)

    class Meta(RevisionLine.Meta):
        constraints = RevisionLine.Meta.constraints + [
            models.UniqueConstraint(fields=['revision','sequence'], name='revision_route_sequence'),
            models.CheckConstraint(condition=models.Q(sequence__gt=0), name='route_positive_sequence'),
            models.UniqueConstraint(fields=['revision','source_id'], condition=~models.Q(source_id=''), name='route_source_identity'),
        ]


class ProcessCostLine(RevisionLine):
    revision = models.ForeignKey(ProductModelRevision, on_delete=models.PROTECT, related_name='processes')
    stage = models.ForeignKey(ModelRouteStage, null=True, blank=True, on_delete=models.PROTECT)
    name = models.CharField(max_length=240)
    basis = models.CharField(max_length=20, choices=[(v,v) for v in ['per kg','per piece','per batch','fixed']])
    rate = amount(True)
    quantity = amount(True)
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT)
    remarks = models.TextField(blank=True)


# Database checks also protect direct ORM and SQL clients.
for _model in [ProductModelRevision, RecipeLine, ModelRouteStage, ProcessCostLine]:
    for _field in _model._meta.fields:
        if isinstance(_field, models.DecimalField):
            _condition = models.Q(**{_field.name + '__isnull': True}) | models.Q(**{_field.name + '__gte': 0})
            if 'percent' in _field.name:
                _condition &= models.Q(**{_field.name + '__isnull': True}) | models.Q(**{_field.name + '__lte': 100})
            _model._meta.constraints.append(models.CheckConstraint(condition=_condition, name=f'{_model._meta.model_name}_{_field.name}_range'))
