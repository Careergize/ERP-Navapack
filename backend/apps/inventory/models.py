import uuid
from django.conf import settings
from django.db import models
from django.db.models.functions import Lower
from apps.core.models import VersionedModel


class Configuration(VersionedModel):
    code = models.CharField(max_length=100)
    name = models.CharField(max_length=240)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    class Meta(VersionedModel.Meta):
        abstract = True
        constraints = VersionedModel.Meta.constraints + [
            models.CheckConstraint(condition=~models.Q(code='') & ~models.Q(name=''), name='%(class)s_labels_required'),
            models.UniqueConstraint(Lower('code'), name='%(class)s_code_ci'),
        ]


class Warehouse(Configuration):
    description = models.CharField(max_length=1000, blank=True)
    custody_department = models.ForeignKey('masters.Department', null=True, blank=True, on_delete=models.PROTECT)
    # Null is unresolved accountability, never permission to post stock.
    class Meta(Configuration.Meta):
        permissions = [('configure_warehouses', 'Configure warehouses with approved company oversight scope'),
                       ('view_inventory_audit', 'Read warehouse-scoped inventory configuration history')]


class StorageLocation(Configuration):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT)
    classification = models.CharField(max_length=100, blank=True)
    # Labels are configurable; none assert the client's actual layout or QC release.
    class Meta(Configuration.Meta):
        constraints = Configuration.Meta.constraints + [
            models.CheckConstraint(condition=~models.Q(parent=models.F('id')), name='location_not_self_parent'),
        ]


class WarehouseScope(models.Model):
    """Immutable approved scope evidence; no public provisioning API in 3A.

    Deployment provisioning is gated pending governed scope publication/revocation.
    Expiry is mandatory so these are not irrevocable permanent grants.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    warehouse = models.ForeignKey(Warehouse, null=True, on_delete=models.PROTECT)
    company_wide = models.BooleanField(default=False)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    policy_reference = models.CharField(max_length=200)
    evidence_reference = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    class Meta:
        default_permissions = ('view',)
        constraints = [
            models.CheckConstraint(condition=(models.Q(company_wide=True, warehouse__isnull=True) | models.Q(company_wide=False, warehouse__isnull=False)), name='scope_exact_boundary'),
            models.CheckConstraint(condition=~models.Q(requested_by=models.F('approved_by')) & ~models.Q(user=models.F('approved_by')), name='scope_independent_approver'),
            models.CheckConstraint(condition=~models.Q(policy_reference='') & ~models.Q(evidence_reference=''), name='scope_evidence_required'),
        ]


class StockIdentity(VersionedModel):
    reference = models.CharField(max_length=45, unique=True, editable=False)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    location = models.ForeignKey(StorageLocation, null=True, blank=True, on_delete=models.PROTECT)
    material = models.ForeignKey('masters.Material', null=True, blank=True, on_delete=models.PROTECT)
    variant = models.ForeignKey('masters.ProductVariant', null=True, blank=True, on_delete=models.PROTECT)
    consumable = models.ForeignKey('masters.Consumable', null=True, blank=True, on_delete=models.PROTECT)
    unit = models.ForeignKey('masters.Unit', on_delete=models.PROTECT)
    kind = models.CharField(max_length=12, choices=[(v,v) for v in ['BATCH','ROLL','CONTAINER','PORTION']])
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT)
    ownership = models.CharField(max_length=12, default='UNRESOLVED', choices=[(v,v) for v in ['UNRESOLVED','COMPANY','CUSTOMER','SUPPLIER','OTHER']])
    owner_customer = models.ForeignKey('masters.Customer', null=True, blank=True, on_delete=models.PROTECT)
    owner_supplier = models.ForeignKey('masters.Supplier', null=True, blank=True, on_delete=models.PROTECT, related_name='+')
    ownership_evidence = models.CharField(max_length=200, blank=True)
    source_system = models.CharField(max_length=120)
    source_reference = models.CharField(max_length=200)
    source_document_reference = models.CharField(max_length=200, blank=True)
    supplier = models.ForeignKey('masters.Supplier', null=True, blank=True, on_delete=models.PROTECT, related_name='+')
    supplier_batch = models.CharField(max_length=200, blank=True)
    physical_reference = models.CharField(max_length=200, blank=True)
    lifecycle = models.CharField(max_length=12, default='REGISTERED', choices=[(v,v) for v in ['REGISTERED','RETIRED']])
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    class Meta(VersionedModel.Meta):
        constraints = VersionedModel.Meta.constraints + [
            models.CheckConstraint(condition=models.Q(kind__in=['BATCH','ROLL','CONTAINER','PORTION']), name='stock_known_kind'),
            models.CheckConstraint(condition=models.Q(lifecycle__in=['REGISTERED','RETIRED']), name='stock_known_lifecycle'),
            models.CheckConstraint(condition=(models.Q(material__isnull=False, variant__isnull=True, consumable__isnull=True) | models.Q(material__isnull=True, variant__isnull=False, consumable__isnull=True) | models.Q(material__isnull=True, variant__isnull=True, consumable__isnull=False)), name='stock_exact_item'),
            models.CheckConstraint(condition=~models.Q(reference='') & ~models.Q(source_system='') & ~models.Q(source_reference=''), name='stock_provenance_required'),
            models.UniqueConstraint(fields=['source_system','source_reference'], name='stock_source_unique'),
            models.CheckConstraint(condition=~models.Q(parent=models.F('id')), name='stock_not_self_parent'),
            models.CheckConstraint(condition=(models.Q(ownership='CUSTOMER', owner_customer__isnull=False, owner_supplier__isnull=True) | models.Q(ownership='SUPPLIER', owner_supplier__isnull=False, owner_customer__isnull=True) | models.Q(ownership__in=['UNRESOLVED','COMPANY','OTHER'], owner_customer__isnull=True, owner_supplier__isnull=True)), name='stock_owner_shape'),
            models.CheckConstraint(condition=models.Q(ownership='UNRESOLVED') | ~models.Q(ownership_evidence=''), name='stock_owner_evidence'),
        ]
    def save(self, *args, **kwargs):
        if self._state.adding:
            self.reference = 'STK-' + self.id.hex.upper()
        super().save(*args, **kwargs)

# Additive test-only ledger domain, kept separate from registration configuration.
from .ledger_models import (PostingPolicy, SourceEvent, LedgerApproval, LedgerTransaction,
                            TransactionLine, LedgerEntry, BalanceProjection, OpeningCoverage)

from .workflow_models import OperationRequest, OperationLine, OperationDecision  # noqa: E402,F401
from .workflow_models import PhysicalSourceDocument, PhysicalSourceLine  # noqa: E402,F401
