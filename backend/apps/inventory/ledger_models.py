"""Phase 3B immutable posting evidence and replaceable projections; no workflow APIs."""
import uuid
from django.conf import settings
from django.db import models
from apps.core.models import VersionedModel, AppendOnlyQuerySet
from apps.core.commands import payload_hash


class ImmutableRecord(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    created_at=models.DateTimeField(auto_now_add=True)
    objects=AppendOnlyQuerySet.as_manager()
    class Meta: abstract=True
    def save(self,*args,**kwargs):
        if not self._state.adding: raise ValueError('Posted evidence is immutable.')
        super().save(*args,**kwargs)
    def delete(self,*args,**kwargs): raise ValueError('Posted evidence is immutable.')


class PostingPolicy(ImmutableRecord):
    reference=models.CharField(max_length=200,unique=True)
    version=models.PositiveIntegerField(default=1)
    synthetic=models.BooleanField(default=True)
    rules=models.JSONField()
    digest=models.CharField(max_length=64,editable=False)
    class Meta:
        constraints=[models.CheckConstraint(condition=models.Q(synthetic=True,version__gte=1),name='policy_synthetic_only')]
    def save(self,*args,**kwargs):
        if self._state.adding:self.digest=payload_hash({'reference':self.reference,'version':self.version,'rules':self.rules})
        super().save(*args,**kwargs)


class SourceEvent(ImmutableRecord):
    system=models.CharField(max_length=120)
    event_key=models.CharField(max_length=200)
    intent_hash=models.CharField(max_length=64)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['system','event_key'],name='ledger_unique_physical_event')]


class LedgerApproval(ImmutableRecord):
    maker=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='+')
    approver=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='+')
    policy=models.ForeignKey(PostingPolicy,on_delete=models.PROTECT)
    intent_hash=models.CharField(max_length=64)
    reference=models.CharField(max_length=200)
    decision=models.CharField(max_length=10,choices=[('APPROVED','APPROVED'),('REJECTED','REJECTED')])
    class Meta:
        constraints=[models.CheckConstraint(condition=~models.Q(maker=models.F('approver')),name='ledger_approval_independent')]


class LedgerTransaction(ImmutableRecord):
    KINDS=['OPENING','IN','OUT','TRANSFER','RETURN','ADJUSTMENT','CORRECTION','REVERSAL','QUALITY']
    source=models.OneToOneField(SourceEvent,on_delete=models.PROTECT)
    policy=models.ForeignKey(PostingPolicy,on_delete=models.PROTECT)
    actor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    approval=models.OneToOneField(LedgerApproval,null=True,on_delete=models.PROTECT)
    kind=models.CharField(max_length=12,choices=[(k,k) for k in KINDS])
    version=models.PositiveIntegerField(default=1,editable=False)
    event_at=models.DateTimeField()
    reason=models.TextField()
    reverses=models.OneToOneField('self',null=True,on_delete=models.PROTECT,related_name='reversal')
    related=models.ForeignKey('self',null=True,on_delete=models.PROTECT,related_name='related_events')
    database_txid=models.BigIntegerField(default=0,editable=False)
    class Meta:
        permissions=[('post_synthetic_transaction','Execute synthetic ledger tests'),
                     ('approve_synthetic_transaction','Verify synthetic approval fixtures'),
                     ('view_synthetic_custody','Read scoped synthetic custody'),
                     ('rebuild_synthetic_projection','Rebuild synthetic projection')]
        constraints=[models.CheckConstraint(condition=models.Q(kind__in=['OPENING','IN','OUT','TRANSFER','RETURN','ADJUSTMENT','CORRECTION','REVERSAL','QUALITY'],version=1),name='ledger_known_posted_kind'),
                     models.CheckConstraint(condition=~models.Q(reverses=models.F('id')),name='ledger_not_self_reversal')]


class TransactionLine(ImmutableRecord):
    transaction=models.ForeignKey(LedgerTransaction,on_delete=models.PROTECT,related_name='lines')
    sequence=models.PositiveIntegerField()
    stock=models.ForeignKey('inventory.StockIdentity',on_delete=models.PROTECT)
    unit=models.ForeignKey('masters.Unit',on_delete=models.PROTECT)
    from_location=models.ForeignKey('inventory.StorageLocation',null=True,on_delete=models.PROTECT,related_name='+')
    to_location=models.ForeignKey('inventory.StorageLocation',null=True,on_delete=models.PROTECT,related_name='+')
    quantity=models.DecimalField(max_digits=20,decimal_places=6)
    quality=models.CharField(max_length=10,choices=[('HELD','HELD'),('RELEASED','RELEASED')])
    original_line=models.ForeignKey('self',null=True,on_delete=models.PROTECT)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['transaction','sequence'],name='ledger_line_sequence'),
                     models.CheckConstraint(condition=models.Q(quantity__gte=0,sequence__gte=1),name='ledger_line_nonnegative'),
                     models.CheckConstraint(condition=models.Q(from_location__isnull=False)|models.Q(to_location__isnull=False),name='ledger_line_endpoint'),
                     models.CheckConstraint(condition=~models.Q(from_location=models.F('to_location')),name='ledger_line_distinct_endpoints'),
                     models.CheckConstraint(condition=models.Q(quality__in=['HELD','RELEASED']),name='ledger_line_quality')]


class LedgerEntry(ImmutableRecord):
    transaction=models.ForeignKey(LedgerTransaction,on_delete=models.PROTECT,related_name='entries')
    line=models.ForeignKey(TransactionLine,on_delete=models.PROTECT)
    sequence=models.PositiveIntegerField()
    stock=models.ForeignKey('inventory.StockIdentity',on_delete=models.PROTECT)
    location=models.ForeignKey('inventory.StorageLocation',on_delete=models.PROTECT)
    unit=models.ForeignKey('masters.Unit',on_delete=models.PROTECT)
    owner_key=models.CharField(max_length=300)
    quality=models.CharField(max_length=10)
    balance_key=models.CharField(max_length=64,db_index=True)
    delta=models.DecimalField(max_digits=20,decimal_places=6)
    event_at=models.DateTimeField()
    class Meta:
        constraints=[models.UniqueConstraint(fields=['transaction','sequence'],name='ledger_entry_sequence'),
                     models.CheckConstraint(condition=~models.Q(delta=0),name='ledger_entry_nonzero'),
                     models.CheckConstraint(condition=models.Q(quality__in=['HELD','RELEASED']),name='ledger_entry_quality')]
        indexes=[models.Index(fields=['stock','location','event_at'])]


class BalanceProjection(VersionedModel):
    balance_key=models.CharField(max_length=64,unique=True)
    stock=models.ForeignKey('inventory.StockIdentity',on_delete=models.PROTECT)
    location=models.ForeignKey('inventory.StorageLocation',on_delete=models.PROTECT)
    unit=models.ForeignKey('masters.Unit',on_delete=models.PROTECT)
    owner_key=models.CharField(max_length=300)
    quality=models.CharField(max_length=10)
    quantity=models.DecimalField(max_digits=20,decimal_places=6,default=0)
    last_transaction=models.ForeignKey(LedgerTransaction,null=True,on_delete=models.PROTECT)
    class Meta(VersionedModel.Meta):
        constraints=VersionedModel.Meta.constraints+[
            models.UniqueConstraint(fields=['stock','location','unit','owner_key','quality'],name='ledger_balance_exact_key'),
            models.CheckConstraint(condition=models.Q(quantity__gte=0),name='ledger_balance_nonnegative'),
            models.CheckConstraint(condition=models.Q(quality__in=['HELD','RELEASED']),name='ledger_balance_quality')]


class OpeningCoverage(VersionedModel):
    stock=models.ForeignKey('inventory.StockIdentity',on_delete=models.PROTECT)
    location=models.ForeignKey('inventory.StorageLocation',on_delete=models.PROTECT)
    unit=models.ForeignKey('masters.Unit',on_delete=models.PROTECT)
    owner_key=models.CharField(max_length=300)
    status=models.CharField(max_length=10,default='UNKNOWN',choices=[('UNKNOWN','UNKNOWN'),('KNOWN','KNOWN')])
    opening_quantity=models.DecimalField(max_digits=20,decimal_places=6,null=True)
    transaction=models.ForeignKey(LedgerTransaction,null=True,on_delete=models.PROTECT)
    class Meta(VersionedModel.Meta):
        constraints=VersionedModel.Meta.constraints+[
            models.UniqueConstraint(fields=['stock','location','unit','owner_key'],name='ledger_opening_scope'),
            models.CheckConstraint(condition=(models.Q(status='UNKNOWN',opening_quantity__isnull=True,transaction__isnull=True)|models.Q(status='KNOWN',opening_quantity__gte=0,opening_quantity__isnull=False,transaction__isnull=False)),name='ledger_coverage_explicit')]
