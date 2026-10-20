"""Isolated workflow evidence. These models never represent stock or approvals."""
import uuid
from django.conf import settings
from django.db import models
from apps.core.models import VersionedModel, AppendOnlyQuerySet


class RehearsalJob(VersionedModel):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    sales_order_revision = models.ForeignKey('commercial.CommercialRevision', null=True, on_delete=models.PROTECT, related_name='+')
    costing_revision = models.ForeignKey('commercial.CommercialRevision', null=True, on_delete=models.PROTECT, related_name='+')
    warehouse = models.ForeignKey('inventory.Warehouse', on_delete=models.PROTECT)
    status = models.CharField(max_length=24, default='DRAFT')
    snapshot = models.JSONField()

    class Meta(VersionedModel.Meta):
        permissions = [('use_simulation', 'Execute isolated ERP workflow simulations')]
        constraints = VersionedModel.Meta.constraints + [models.CheckConstraint(
            condition=(models.Q(sales_order_revision__isnull=False, costing_revision__isnull=True)
                | models.Q(sales_order_revision__isnull=True, costing_revision__isnull=False)),
            name='rehearsal_exact_source')]


class RehearsalRevision(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(RehearsalJob, on_delete=models.PROTECT, related_name='revisions')
    number = models.PositiveIntegerField()
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=24)
    reason = models.CharField(max_length=500)
    snapshot = models.JSONField()
    sha256 = models.CharField(max_length=64)
    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        ordering = ['number']
        constraints = [models.UniqueConstraint(fields=['job', 'number'], name='rehearsal_revision_unique')]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError('Simulation history is immutable.')
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError('Simulation history is immutable.')
