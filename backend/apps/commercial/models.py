import uuid
from django.conf import settings
from django.db import models
from apps.core.models import VersionedModel, AppendOnlyQuerySet


class CommercialDocument(VersionedModel):
    kind = models.CharField(max_length=12, choices=[(v, v) for v in ('COSTING', 'QUOTATION', 'SALES_ORDER')])
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    status = models.CharField(max_length=12, default='DRAFT', choices=[(v, v) for v in ('DRAFT', 'REVIEW', 'CANCELLED')])

    class Meta(VersionedModel.Meta):
        permissions = [('use_foundation', 'Use synthetic commercial foundation')]
        constraints = VersionedModel.Meta.constraints + [
            models.CheckConstraint(condition=models.Q(kind__in=['COSTING', 'QUOTATION', 'SALES_ORDER']), name='commercial_kind'),
            models.CheckConstraint(condition=models.Q(status__in=['DRAFT', 'REVIEW', 'CANCELLED']), name='commercial_status'),
        ]


class CommercialRevision(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(CommercialDocument, on_delete=models.PROTECT, related_name='revisions')
    number = models.PositiveIntegerField()
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=12)
    reason = models.CharField(max_length=500)
    snapshot = models.JSONField()
    sha256 = models.CharField(max_length=64)
    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        ordering = ['number']
        constraints = [models.UniqueConstraint(fields=['document', 'number'], name='commercial_revision_number'),
                       models.CheckConstraint(condition=models.Q(number__gte=1), name='commercial_revision_positive')]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError('Commercial revisions are immutable.')
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError('Commercial revisions are immutable.')


class GovernanceRecord(VersionedModel):
    """Proposal identity only. Deliberately has no approval/activation fields."""
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    kind = models.CharField(max_length=8, choices=[('POLICY', 'Policy proposal'), ('DECISION', 'Unverified decision answer')])
    key = models.CharField(max_length=40)

    class Meta(VersionedModel.Meta):
        permissions = [('manage_proposals', 'Record synthetic unverified commercial proposals')]
        constraints = VersionedModel.Meta.constraints + [
            models.CheckConstraint(condition=models.Q(kind__in=['POLICY', 'DECISION']), name='governance_kind'),
            models.CheckConstraint(condition=~models.Q(key=''), name='governance_key_required'),
            models.UniqueConstraint(fields=['owner', 'key'], condition=models.Q(kind='DECISION'), name='one_owner_decision_record'),
        ]


class GovernanceRevision(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    record = models.ForeignKey(GovernanceRecord, on_delete=models.PROTECT, related_name='revisions')
    number = models.PositiveIntegerField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=24, choices=[(v, v) for v in ['PROPOSED_UNVERIFIED', 'PENDING_VERIFICATION']])
    content = models.JSONField()
    reason = models.CharField(max_length=500)
    sha256 = models.CharField(max_length=64)
    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        ordering = ['number']
        constraints = [models.UniqueConstraint(fields=['record', 'number'], name='governance_revision_number'),
            models.CheckConstraint(condition=models.Q(number__gte=1), name='governance_number_positive'),
            models.CheckConstraint(condition=models.Q(status__in=['PROPOSED_UNVERIFIED', 'PENDING_VERIFICATION']), name='governance_unverified_only')]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError('Governance evidence is immutable.')
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError('Governance evidence is immutable.')
