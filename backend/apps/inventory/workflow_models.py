"""Sealed synthetic operations; no operational authority provisioning."""
from django.conf import settings
from django.db import models
from apps.core.models import VersionedModel
from .ledger_models import ImmutableRecord


class OperationRequest(VersionedModel):
    KINDS=['IN','OUT','OPENING','OPENING_CORRECTION','TRANSFER','RETURN','COUNT','ADJUSTMENT']
    STATES=['SUBMITTED','VERIFIED','INVESTIGATED','CONFIRMED','APPROVED','REJECTED','POSTED']
    kind=models.CharField(max_length=24,choices=[(v,v) for v in KINDS])
    status=models.CharField(max_length=16,default='SUBMITTED',choices=[(v,v) for v in STATES])
    submission_txid=models.BigIntegerField(default=0,editable=False)
    mutation_txid=models.BigIntegerField(default=0,editable=False)
    warehouse=models.ForeignKey('inventory.Warehouse',on_delete=models.PROTECT,related_name='+')
    destination_warehouse=models.ForeignKey('inventory.Warehouse',null=True,on_delete=models.PROTECT,related_name='+')
    requested_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='+')
    policy=models.ForeignKey('inventory.PostingPolicy',null=True,on_delete=models.PROTECT)
    source_system=models.CharField(max_length=120)
    source_event=models.CharField(max_length=200)
    source_reference=models.CharField(max_length=200)
    evidence_reference=models.CharField(max_length=200)
    counterparty_reference=models.CharField(max_length=200,blank=True)
    reason=models.CharField(max_length=1000)
    cutoff=models.DateTimeField()
    cutoff_basis=models.CharField(max_length=24,default='LEGACY_UNVERIFIED',choices=[(v,v) for v in ['LEGACY_UNVERIFIED','CURRENT_LOCKED','EVIDENCE_ONLY']])
    related=models.ForeignKey('inventory.LedgerTransaction',null=True,on_delete=models.PROTECT,related_name='+')
    count_session=models.ForeignKey('self',null=True,on_delete=models.PROTECT,related_name='+')
    recording_employee=models.ForeignKey(settings.AUTH_USER_MODEL,null=True,on_delete=models.PROTECT,related_name='+')
    sealed_intent=models.JSONField(null=True)
    ledger_transaction=models.OneToOneField('inventory.LedgerTransaction',null=True,on_delete=models.PROTECT,related_name='+')
    class Meta(VersionedModel.Meta):
        default_permissions=('view',)
        permissions=[('submit_operation','Submit synthetic inventory evidence'),('request_opening_correction','Initiate opening corrections'),
                     ('verify_operation','Verify Stores evidence'),('investigate_operation','Investigate stock variance'),
                     ('confirm_operation','Confirm physical movement'),('approve_operation','Independently review operation'),
                     ('record_operation','Record authorized stock operation'),('view_operation_history','Read scoped operation audit')]
        constraints=VersionedModel.Meta.constraints+[
            models.UniqueConstraint(fields=['source_system','source_event'],name='operation_unique_source'),
            models.UniqueConstraint(fields=['count_session'],condition=models.Q(kind='ADJUSTMENT',status='POSTED'),name='operation_count_adjust_once'),
            models.CheckConstraint(condition=models.Q(kind__in=['IN','OUT','OPENING','OPENING_CORRECTION','TRANSFER','RETURN','COUNT','ADJUSTMENT']),name='operation_known_kind'),
            models.CheckConstraint(condition=models.Q(status__in=['SUBMITTED','VERIFIED','INVESTIGATED','CONFIRMED','APPROVED','REJECTED','POSTED']),name='operation_known_status'),
            models.CheckConstraint(condition=(models.Q(status='POSTED',ledger_transaction__isnull=False)|(~models.Q(status='POSTED')&models.Q(ledger_transaction__isnull=True))),name='operation_post_reference')]


class OperationLine(ImmutableRecord):
    request=models.ForeignKey(OperationRequest,on_delete=models.PROTECT,related_name='lines')
    stock=models.ForeignKey('inventory.StockIdentity',on_delete=models.PROTECT)
    unit=models.ForeignKey('masters.Unit',on_delete=models.PROTECT)
    location=models.ForeignKey('inventory.StorageLocation',on_delete=models.PROTECT,related_name='+')
    destination=models.ForeignKey('inventory.StorageLocation',null=True,on_delete=models.PROTECT,related_name='+')
    quantity=models.DecimalField(max_digits=20,decimal_places=6)
    quality=models.CharField(max_length=10)
    original_line=models.ForeignKey('inventory.TransactionLine',null=True,on_delete=models.PROTECT)
    baseline=models.DecimalField(max_digits=20,decimal_places=6,null=True)
    original_quantity=models.DecimalField(max_digits=20,decimal_places=6,null=True)
    difference=models.DecimalField(max_digits=20,decimal_places=6,null=True)
    balance_version=models.PositiveIntegerField(default=0)
    source_line=models.OneToOneField('inventory.PhysicalSourceLine',null=True,on_delete=models.PROTECT,related_name='claim')
    class Meta:
        constraints=[models.UniqueConstraint(fields=['request','stock','location','quality'],name='operation_distinct_count_key'),
                     models.CheckConstraint(condition=models.Q(quantity__gte=0),name='operation_quantity_nonnegative'),
                     models.CheckConstraint(condition=models.Q(quality__in=['HELD','RELEASED']),name='operation_quality')]


class OperationDecision(ImmutableRecord):
    request=models.ForeignKey(OperationRequest,on_delete=models.PROTECT,related_name='decisions')
    version=models.PositiveIntegerField()
    actor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    action=models.CharField(max_length=24)
    from_status=models.CharField(max_length=16)
    to_status=models.CharField(max_length=16)
    reason=models.CharField(max_length=1000)
    evidence_reference=models.CharField(max_length=200)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['request','version'],name='operation_decision_revision')]


class PhysicalSourceDocument(ImmutableRecord):
    """Fixture-only controlled registry, never registered by a request/random UUID."""
    namespace=models.CharField(max_length=120)
    reference=models.CharField(max_length=200)
    kind=models.CharField(max_length=10,choices=[('RECEIPT','RECEIPT'),('COUNT','COUNT')])
    warehouse=models.ForeignKey('inventory.Warehouse',on_delete=models.PROTECT)
    evidence_reference=models.CharField(max_length=200)
    registered_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    class Meta:
        default_permissions=('view',)
        constraints=[models.UniqueConstraint(fields=['namespace','reference'],name='physical_document_identity'),
            models.CheckConstraint(condition=models.Q(namespace__startswith='synthetic:')&~models.Q(reference='')&models.Q(kind__in=['RECEIPT','COUNT']),name='physical_document_synthetic')]


class PhysicalSourceLine(ImmutableRecord):
    document=models.ForeignKey(PhysicalSourceDocument,on_delete=models.PROTECT)
    occurrence_reference=models.CharField(max_length=200)
    line_reference=models.CharField(max_length=100)
    stock=models.ForeignKey('inventory.StockIdentity',on_delete=models.PROTECT)
    location=models.ForeignKey('inventory.StorageLocation',on_delete=models.PROTECT)
    unit=models.ForeignKey('masters.Unit',on_delete=models.PROTECT)
    quantity=models.DecimalField(max_digits=20,decimal_places=6)
    class Meta:
        default_permissions=('view',)
        constraints=[models.UniqueConstraint(fields=['document','occurrence_reference','line_reference'],name='physical_document_occurrence_line'),
            models.CheckConstraint(condition=models.Q(quantity__gte=0)&~models.Q(occurrence_reference='')&~models.Q(line_reference=''),name='physical_line_identified')]
