"""Synthetic QC evidence. Registration identity and physical quantities stay separate."""
from django.conf import settings
from django.db import models
from .ledger_models import ImmutableRecord


class InspectionPlan(ImmutableRecord):
    reference = models.CharField(max_length=120)
    revision = models.PositiveIntegerField()
    applicability = models.CharField(max_length=12, choices=[(x, x) for x in ['INCOMING', 'FINISHED', 'RETURN', 'PRODUCTION']])
    material = models.ForeignKey('masters.Material', null=True, on_delete=models.PROTECT)
    variant = models.ForeignKey('masters.ProductVariant', null=True, on_delete=models.PROTECT)
    consumable = models.ForeignKey('masters.Consumable', null=True, on_delete=models.PROTECT)
    criteria = models.JSONField()
    specification_reference = models.CharField(max_length=200)
    sampling_reference = models.CharField(max_length=200)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    digest = models.CharField(max_length=64)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['reference', 'revision'], name='qc_plan_revision'),
            models.CheckConstraint(condition=models.Q(revision__gte=1), name='qc_plan_positive_revision'),
            models.CheckConstraint(condition=(models.Q(material__isnull=False, variant__isnull=True, consumable__isnull=True) | models.Q(material__isnull=True, variant__isnull=False, consumable__isnull=True) | models.Q(material__isnull=True, variant__isnull=True, consumable__isnull=False)), name='qc_plan_typed_item')]
        permissions = [(x, x.replace('_', ' ')) for x in ['configure_qc', 'approve_qc_plan', 'inspect_qc', 'review_qc', 'release_qc', 'hold_qc', 'manage_ncr', 'close_ncr', 'view_qc', 'view_qc_history']]


class PlanApproval(ImmutableRecord):
    plan = models.OneToOneField(InspectionPlan, on_delete=models.PROTECT)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    decision = models.CharField(max_length=8, choices=[('APPROVED', 'APPROVED'), ('REJECTED', 'REJECTED')])
    reason = models.CharField(max_length=1000)
    evidence_reference = models.CharField(max_length=200)


class Inspection(ImmutableRecord):
    plan = models.ForeignKey(InspectionPlan, on_delete=models.PROTECT)
    source_entry = models.ForeignKey('inventory.LedgerEntry', on_delete=models.PROTECT)
    operation = models.ForeignKey('inventory.OperationRequest', null=True, on_delete=models.PROTECT)
    previous = models.OneToOneField('self', null=True, on_delete=models.PROTECT, related_name='reinspection')
    stock = models.ForeignKey('inventory.StockIdentity', on_delete=models.PROTECT)
    location = models.ForeignKey('inventory.StorageLocation', on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=20, decimal_places=6)
    balance_version = models.PositiveIntegerField()
    physical_evidence = models.CharField(max_length=200)
    inspector = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    observations = models.JSONField()
    reason = models.CharField(max_length=1000)
    evidence_reference = models.CharField(max_length=200)
    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(quantity__gt=0), name='qc_inspection_positive')]


class InspectionReview(ImmutableRecord):
    inspection = models.OneToOneField(Inspection, on_delete=models.PROTECT, related_name='review')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    decision = models.CharField(max_length=8, choices=[(x, x) for x in ['ACCEPT', 'REJECT', 'PENDING']])
    reason = models.CharField(max_length=1000)
    evidence_reference = models.CharField(max_length=200)


class QualityAuthorization(ImmutableRecord):
    """Sealed authority for one conserved quality transition, never physical Stock IN."""
    review = models.OneToOneField(InspectionReview, null=True, on_delete=models.PROTECT)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    stock = models.ForeignKey('inventory.StockIdentity', on_delete=models.PROTECT)
    location = models.ForeignKey('inventory.StorageLocation', on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=20, decimal_places=6)
    direction = models.CharField(max_length=8, choices=[('RELEASE', 'RELEASE'), ('HOLD', 'HOLD')])
    reason = models.CharField(max_length=1000)
    evidence_reference = models.CharField(max_length=200)
    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(quantity__gt=0), name='qc_transition_positive'),
            models.CheckConstraint(condition=models.Q(direction='HOLD', review__isnull=True) | models.Q(direction='RELEASE', review__isnull=False), name='qc_transition_review')]


class QualityPosting(ImmutableRecord):
    authorization = models.OneToOneField(QualityAuthorization, on_delete=models.PROTECT)
    transaction = models.OneToOneField('inventory.LedgerTransaction', on_delete=models.PROTECT)


class QualityHold(ImmutableRecord):
    stock = models.ForeignKey('inventory.StockIdentity', on_delete=models.PROTECT)
    location = models.ForeignKey('inventory.StorageLocation', on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=20, decimal_places=6)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    authorization = models.OneToOneField(QualityAuthorization, null=True, on_delete=models.PROTECT)
    reason = models.CharField(max_length=1000)
    evidence_reference = models.CharField(max_length=200)
    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(quantity__gt=0), name='qc_hold_positive')]


class Nonconformance(ImmutableRecord):
    inspection = models.ForeignKey(Inspection, on_delete=models.PROTECT)
    hold = models.ForeignKey(QualityHold, on_delete=models.PROTECT)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    classification = models.CharField(max_length=120)
    reason = models.CharField(max_length=1000)
    evidence_reference = models.CharField(max_length=200)


class NonconformanceAction(ImmutableRecord):
    ncr = models.ForeignKey(Nonconformance, on_delete=models.PROTECT, related_name='actions')
    version = models.PositiveIntegerField()
    kind = models.CharField(max_length=12, choices=[(x, x) for x in ['INVESTIGATE', 'CORRECTIVE', 'PREVENTIVE', 'VERIFY', 'CLOSE']])
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    reason = models.CharField(max_length=1000)
    evidence_reference = models.CharField(max_length=200)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name='+')
    target_at = models.DateTimeField(null=True)
    reinspection = models.ForeignKey(Inspection, null=True, on_delete=models.PROTECT)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['ncr', 'version'], name='qc_ncr_action_version')]
