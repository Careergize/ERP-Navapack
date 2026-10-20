from django.conf import settings
from django.db import models
from apps.core.models import VersionedModel


class ImportBatch(VersionedModel):
    filename = models.CharField(max_length=240)
    digest = models.CharField(max_length=64, unique=True)
    source_system = models.CharField(max_length=120)
    source_kind = models.CharField(max_length=20, choices=[('client','Client source'),('demo','Demo or generated')])
    target = models.CharField(max_length=40, db_index=True)
    status = models.CharField(max_length=20, db_index=True, default='staged', choices=[(v,v) for v in ['staged','reviewed','applied']])
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name='+')
    approved_at = models.DateTimeField(null=True)
    mapping = models.JSONField(default=dict)
    review = models.JSONField(default=list)
    source_attestation = models.CharField(max_length=1000, blank=True)
    canonical_review = models.ForeignKey('ImportReview', null=True, on_delete=models.PROTECT, related_name='+')
    applied_plan = models.JSONField(null=True, editable=False)

    class Meta(VersionedModel.Meta):
        permissions = [('review_importbatch','Review import mappings'), ('approve_importbatch','Approve and apply master import')]


class ImportRow(VersionedModel):
    batch = models.ForeignKey(ImportBatch, on_delete=models.PROTECT, related_name='rows')
    sheet = models.CharField(max_length=200)
    row_number = models.PositiveIntegerField()
    raw = models.JSONField()
    result_id = models.UUIDField(null=True)

    class Meta(VersionedModel.Meta):
        constraints = VersionedModel.Meta.constraints + [models.UniqueConstraint(fields=['batch','sheet','row_number'], name='import_source_row')]


class ImportReview(models.Model):
    """Append-only canonical review; legacy batch.review remains a UI projection."""
    import uuid
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(ImportBatch, on_delete=models.PROTECT, related_name='review_history')
    plan = models.JSONField()
    plan_hash = models.CharField(max_length=64)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
