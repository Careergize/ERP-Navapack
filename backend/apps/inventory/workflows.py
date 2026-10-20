"""Bounded operations staging; every entry point remains synthetic-only."""
import uuid
from decimal import Decimal
from django.db import connection, IntegrityError
from django.db.models import Sum
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied, ValidationError
from apps.accounts.models import User
from apps.accounts.permissions import require_independent_actor
from apps.core.commands import execute_command, advance_version, payload_hash
from apps.core.api import CommandConflict, VersionConflict
from apps.core.audit import sanitize
from .models import StockIdentity, StorageLocation
from .workflow_models import OperationRequest, OperationLine, OperationDecision, PhysicalSourceLine
from .ledger_models import PostingPolicy, LedgerTransaction, TransactionLine, LedgerApproval, BalanceProjection, OpeningCoverage
from .authorization import require_actor, require_scope, authority_snapshot
from .ledger_guard import require_synthetic_environment, synthetic_write, posting_locks
from .ledger import quantity, owner_key, key_for, post_transaction, policy_for, event_time

CAPS={v:'inventory.'+v+'_operation' for v in ['submit','verify','investigate','confirm','approve','record']}
CAPS['reject']=CAPS['approve']

class IssueUnavailable(CommandConflict):
    default_code='issue_unavailable'
    default_detail='Stock OUT is stale or unavailable. No issue has been posted; refresh and review.'

class ExactQuantityField(serializers.CharField):
    def to_internal_value(self,data):
        if not isinstance(data,str):raise ValidationError('Quantity must be an exact decimal string, never a JSON number.')
        return super().to_internal_value(data)

class LineInput(serializers.Serializer):
    stock=serializers.UUIDField()
    unit=serializers.UUIDField()
    location=serializers.UUIDField()
    destination=serializers.UUIDField(required=False)
    quantity=ExactQuantityField(max_length=32,trim_whitespace=False)
    source_line=serializers.UUIDField(required=False)
    quality=serializers.ChoiceField(choices=['HELD','RELEASED'],default='HELD')
    original_line=serializers.UUIDField(required=False)
    def to_internal_value(self,data):
        if set(data)-set(self.fields):raise ValidationError('Unknown line fields.')
        return super().to_internal_value(data)

class RequestInput(serializers.Serializer):
    kind=serializers.ChoiceField(choices=OperationRequest.KINDS)
    warehouse=serializers.UUIDField()
    source_system=serializers.CharField(max_length=120)
    source_event=serializers.CharField(max_length=200)
    source_reference=serializers.CharField(max_length=200)
    evidence_reference=serializers.CharField(max_length=200)
    counterparty_reference=serializers.CharField(max_length=200,required=False,default='')
    reason=serializers.CharField(max_length=1000)
    cutoff=serializers.DateTimeField(required=False)
    policy=serializers.UUIDField(required=False)
    related=serializers.UUIDField(required=False)
    count_session=serializers.UUIDField(required=False)
    lines=LineInput(many=True,allow_empty=False,max_length=25)
    def to_internal_value(self,data):
        if set(data)-set(self.fields):raise ValidationError('Unknown request fields.')
        return super().to_internal_value(data)
    def validate(self,attrs):
        if attrs['kind'] in ['COUNT','OPENING']:
            if 'cutoff' in attrs:raise ValidationError({'cutoff':'Custom/historical count cutoffs are unsupported. Omit cutoff for a server-timestamped current capture; historical reconciliation is deferred.'})
        elif 'cutoff' not in attrs:raise ValidationError({'cutoff':'Physical evidence timestamp is required.'})
        return attrs

class TransitionInput(serializers.Serializer):
    reason=serializers.CharField(max_length=1000)
    evidence_reference=serializers.CharField(max_length=200)
    recorder=serializers.UUIDField(required=False)
    def to_internal_value(self,data):
        if set(data)-set(self.fields):raise ValidationError('Unknown transition fields.')
        return super().to_internal_value(data)

def invalid(text):raise ValidationError({'operation':text})
def scope_request(actor,obj):
    require_scope(actor,obj.warehouse_id)
    if obj.destination_warehouse_id:require_scope(actor,obj.destination_warehouse_id)

def physical_source_snapshot(line):
    if line.source_line_id is None:return None
    source=line.source_line;document=source.document
    return {'document_id':str(document.pk),'namespace':document.namespace,'document_reference':document.reference,
            'occurrence_reference':source.occurrence_reference,'line_reference':source.line_reference}

def snapshot(obj):
    return {'id':str(obj.pk),'kind':obj.kind,'status':obj.status,'version':obj.version,'warehouse':str(obj.warehouse_id),
        'destination_warehouse':str(obj.destination_warehouse_id) if obj.destination_warehouse_id else None,
        'requested_by':str(obj.requested_by_id),'requested_at':obj.created_at.isoformat(),'cutoff':obj.cutoff.isoformat(),'cutoff_basis':obj.cutoff_basis,
        'stock_movement_posted':obj.ledger_transaction_id is not None,'physical_confirmation_is_posting':False,
        'policy':str(obj.policy_id) if obj.policy_id else None,'policy_evidence':{'version':obj.policy.version,'digest':obj.policy.digest} if obj.policy_id else None,'source_system':obj.source_system,'source_event':obj.source_event,
        'source_reference':obj.source_reference,'evidence_reference':obj.evidence_reference,'counterparty_reference':obj.counterparty_reference,
        'reason':obj.reason,'related':str(obj.related_id) if obj.related_id else None,'count_session':str(obj.count_session_id) if obj.count_session_id else None,
        'recording_employee':str(obj.recording_employee_id) if obj.recording_employee_id else None,
        'ledger_transaction':str(obj.ledger_transaction_id) if obj.ledger_transaction_id else None,
        'qc_status':'HELD_ON_RECEIPT_NO_RELEASE_WORKFLOW','posting_mode':'SYNTHETIC_ONLY',
        'lines':[{'id':str(l.pk),'stock':str(l.stock_id),'unit':str(l.unit_id),'location':str(l.location_id),
            'destination':str(l.destination_id) if l.destination_id else None,'quantity':str(l.quantity),'quality':l.quality,
            'baseline':str(l.baseline) if l.baseline is not None else None,'original_quantity':str(l.original_quantity) if l.original_quantity is not None else None,'difference':str(l.difference) if l.difference is not None else None,
            'original_line':str(l.original_line_id) if l.original_line_id else None,'source_line':str(l.source_line_id) if l.source_line_id else None,'source_identity':physical_source_snapshot(l),'balance_version':l.balance_version} for l in obj.lines.order_by('id')],
        'decisions':[{'id':str(d.pk),'action':d.action,'actor':str(d.actor_id),'from_status':d.from_status,'to_status':d.to_status,
            'reason':d.reason,'evidence_reference':d.evidence_reference,'timestamp':d.created_at.isoformat(),'version':d.version} for d in obj.decisions.order_by('version')]}

def audit(obj,actor,action,before,reason):
    return {'entity_type':'inventory.operationrequest','entity_id':obj.pk,'source_version':obj.version,'reason':reason,
        'summary':{'before_status':before['status'] if before else None,'after_status':obj.status,'outcome':{
            'before':before,'after':snapshot(obj),'authority':[authority_snapshot(actor,action,w) for w in sorted({str(obj.warehouse_id),str(obj.destination_warehouse_id or obj.warehouse_id)})]}}}

def opening_target(original,stock,location):
    row=original.lines.filter(stock=stock,to_location=location).first()
    if row is None or original.kind!='OPENING':invalid('Original opening line does not match identity/custody.')
    from .ledger_models import LedgerEntry
    extra=LedgerEntry.objects.filter(transaction__kind='CORRECTION',transaction__related=original,stock=stock,location=location).aggregate(value=Sum('delta'))['value'] or Decimal('0')
    return row.quantity+extra

def available(stock,location,quality):
    if not OpeningCoverage.objects.filter(stock=stock,location=location,status='KNOWN').exists():invalid('Opening coverage is unknown; it is not zero.')
    row=BalanceProjection.objects.filter(balance_key=key_for(stock,location,quality)).first()
    return (row.quantity,row.version) if row else (Decimal('0'),0)

def revalidate_issue(obj):
    """Point-in-time validation only: root locks match ledger order, no reservation."""
    lines=list(obj.lines.select_related('location__warehouse'))
    stocks={s.pk:s for s in StockIdentity.objects.select_for_update().filter(pk__in={l.stock_id for l in lines}).order_by('pk')}
    for row in lines:
        stock=stocks[row.stock_id];master=stock.material or stock.variant or stock.consumable
        if (stock.lifecycle!='REGISTERED' or row.quality!='RELEASED' or stock.parent_id or not stock.physical_reference
            or not master.is_active or not stock.unit.is_active or row.unit_id!=stock.unit_id
            or not row.location.is_active or not row.location.warehouse.is_active or row.location.warehouse.custody_department_id is None):
            raise IssueUnavailable('Stock OUT identity, unit, quality or custody is unavailable. No stock posted.')
        try:current,_=available(stock,row.location,'RELEASED')
        except ValidationError as exc:raise IssueUnavailable('Stock OUT opening coverage/ownership is unavailable. No stock posted.') from exc
        if row.quantity>current:raise IssueUnavailable('Insufficient eligible stock for Stock OUT. Refresh/review; no stock posted or reserved.')

def require_controlled_capture(obj):
    if obj.kind in ['IN','COUNT','OPENING']:
        if obj.lines.filter(source_line__isnull=True).exists():invalid('Legacy unbound physical evidence cannot proceed; submit a controlled source-line request.')
        if obj.kind in ['COUNT','OPENING'] and obj.cutoff_basis!='CURRENT_LOCKED':invalid('Historical/legacy counts cannot proceed; make a current locked capture.')

def submit_request(*,actor,data,key,request_id):
    require_synthetic_environment()
    serializer=RequestInput(data=data);serializer.is_valid(raise_exception=True);values=serializer.validated_data
    cap='inventory.request_opening_correction' if values['kind']=='OPENING_CORRECTION' else CAPS['submit']
    def authorize():
        posting_locks();require_actor(actor,cap);require_scope(actor,values['warehouse'])
        # The dedicated correction capability authorizes initiation via the existing login; no role-label bypass.
        for row in values['lines']:
            for field in ['location','destination']:
                if row.get(field):require_scope(actor,StorageLocation.objects.get(pk=row[field]).warehouse_id)
    def operation():
        with synthetic_write():
            if not values['source_system'].startswith('synthetic:'):invalid('Synthetic source identity required.')
            if values.get('cutoff') and values['cutoff']>timezone.now():invalid('Future physical cutoff is invalid.')
            policy=PostingPolicy.objects.get(pk=values['policy']) if values.get('policy') else None
            if policy:policy_for(policy.pk,policy.version)
            kind=values['kind'];related=LedgerTransaction.objects.get(pk=values['related']) if values.get('related') else None
            if kind=='OUT' and not values['counterparty_reference']:invalid('Physical issue destination/reference is required; no Sales Order or Job Card is fabricated.')
            if kind not in ['RETURN','OPENING_CORRECTION'] and related:invalid('Original transaction reference is only valid for returns/opening corrections.')
            if kind!='ADJUSTMENT' and values.get('count_session'):invalid('Count session is only valid for an adjustment.')
            if kind in ['OPENING_CORRECTION','RETURN'] and related is None:invalid('Original posted transaction required.')
            if related:
                for w in related.entries.values_list('location__warehouse_id',flat=True).distinct():require_scope(actor,w)
            count=None
            if kind=='ADJUSTMENT':
                if not values.get('count_session'):invalid('A completed investigated physical count is required.')
                count=OperationRequest.objects.select_for_update().get(pk=values['count_session'])
                scope_request(actor,count)
                if count.kind!='COUNT' or count.status!='INVESTIGATED' or count.warehouse_id!=values['warehouse']:invalid('Count is not investigated in this scope.')
                if count.cutoff_basis!='CURRENT_LOCKED':invalid('Legacy/historical counts require a fresh current capture.')
                if OperationRequest.objects.filter(count_session=count,status='POSTED').exists():invalid('This count already has a posted adjustment; recount before further correction.')
            ids=sorted({str(row['stock']) for row in values['lines']})
            stocks={str(s.pk):s for s in StockIdentity.objects.select_for_update().filter(pk__in=ids).order_by('pk')}
            if len(stocks)!=len(ids):invalid('Unknown stock identity.')
            if kind in ['COUNT','OPENING']:values['cutoff']=timezone.now()
            parsed=[];destination_warehouse=None
            for row in values['lines']:
                stock=stocks[str(row['stock'])];location=StorageLocation.objects.select_related('warehouse').get(pk=row['location'])
                dest=StorageLocation.objects.select_related('warehouse').get(pk=row['destination']) if row.get('destination') else None
                if location.warehouse_id!=values['warehouse']:invalid('Line is outside request warehouse.')
                if stock.lifecycle!='REGISTERED' or stock.parent_id or not stock.physical_reference or not stock.source_system.startswith('synthetic:'):invalid('Identified synthetic root stock required.')
                owner_key(stock)
                if row['unit']!=stock.unit_id:invalid('Exact primary unit required.')
                if not location.is_active or not location.warehouse.is_active:invalid('Inactive custody.')
                if kind=='TRANSFER':
                    if not dest or dest.pk==location.pk:invalid('Distinct transfer destination required.')
                    if destination_warehouse and destination_warehouse!=dest.warehouse_id:invalid('Use one destination warehouse per request.')
                    if not dest.is_active or not dest.warehouse.is_active:invalid('Inactive destination.')
                    destination_warehouse=dest.warehouse_id
                elif dest:invalid('Only transfers specify a destination.')
                qty=quantity(row['quantity'],policy.rules['scale'] if policy else 6);quality=row['quality']
                physical=None
                if kind in ['IN','COUNT','OPENING']:
                    if not row.get('source_line'):invalid('A pre-registered controlled physical document/occurrence/line is required; a random source-event UUID is insufficient.')
                    physical=PhysicalSourceLine.objects.select_related('document').get(pk=row['source_line'])
                    document=physical.document
                    if (document.namespace!=values['source_system'] or document.reference!=values['source_reference'] or document.warehouse_id!=values['warehouse']
                        or document.kind!=('RECEIPT' if kind=='IN' else 'COUNT') or physical.stock_id!=stock.pk or physical.location_id!=location.pk or physical.unit_id!=stock.unit_id or physical.quantity!=qty):
                        invalid('Physical document line does not match the source, event type, identity, custody, unit or quantity.')
                elif row.get('source_line'):invalid('Controlled physical source-line claims apply to receipts/counts/openings only.')
                if kind in ['IN','OPENING','RETURN'] and quality!='HELD':invalid('New stock/count openings start held; QC release is separate.')
                if kind=='OUT' and quality!='RELEASED':invalid('Held stock cannot issue.')
                if kind not in ['OPENING','OPENING_CORRECTION','COUNT','ADJUSTMENT'] and qty==0:invalid('Positive physical quantity required.')
                baseline=None;difference=None;version=0;original_line=None;original_quantity=None
                if kind in ['OUT','TRANSFER','COUNT','ADJUSTMENT']:
                    baseline,version=available(stock,location,quality)
                    if kind in ['OUT','TRANSFER'] and qty>baseline:invalid('Insufficient eligible stock.')
                    if kind in ['COUNT','ADJUSTMENT']:difference=qty-baseline
                if kind=='TRANSFER':available(stock,dest,quality)
                if kind=='OPENING':
                    require_scope(actor,stock.warehouse_id)
                    if OpeningCoverage.objects.filter(stock=stock,location=location,status='KNOWN').exists():invalid('Opening already posted; request correction instead.')
                if kind=='OPENING_CORRECTION':
                    baseline=opening_target(related,stock,location);difference=qty-baseline
                    if difference==0:invalid('Correction must change the opening target.')
                    original=related.lines.get(stock=stock,to_location=location)
                    original_quantity=original.quantity
                    if original.quality!=quality:invalid('Correction identifies the original opening quality partition.')
                if kind=='RETURN':
                    if related.kind!='OUT' or not row.get('original_line'):invalid('Return requires original OUT line.')
                    original_line=TransactionLine.objects.get(pk=row['original_line'],transaction=related,stock=stock,from_location=location)
                    returned=TransactionLine.objects.filter(original_line=original_line,transaction__kind='RETURN',transaction__reversal__isnull=True).aggregate(value=Sum('quantity'))['value'] or Decimal('0')
                    if qty>original_line.quantity-returned:invalid('Return exceeds remaining original issue.')
                elif row.get('original_line'):invalid('Original line is only accepted for returns.')
                if count:
                    counted=count.lines.filter(stock=stock,location=location,quality=quality).first()
                    if counted is None or counted.quantity!=qty or counted.baseline!=baseline or counted.balance_version!=version:invalid('Adjustment does not match the investigated current count.')
                parsed.append((row,stock,location,dest,qty,baseline,difference,version,original_line,original_quantity,physical))
            header={k:v for k,v in values.items() if k not in ['lines','policy','related','count_session']}
            header['warehouse_id']=header.pop('warehouse')
            header={k:sanitize(v) if isinstance(v,str) else v for k,v in header.items()}
            obj=OperationRequest.objects.create(**header,cutoff_basis='CURRENT_LOCKED' if kind in ['COUNT','OPENING'] else 'EVIDENCE_ONLY',policy=policy,related=related,count_session=count,requested_by=actor,destination_warehouse_id=destination_warehouse)
            for row,stock,location,dest,qty,baseline,difference,version,original_line,original_quantity,physical in parsed:
                OperationLine.objects.create(request=obj,stock=stock,unit=stock.unit,location=location,destination=dest,quantity=qty,quality=row['quality'],baseline=baseline,original_quantity=original_quantity,difference=difference,balance_version=version,original_line=original_line,source_line=physical)
            OperationDecision.objects.create(request=obj,version=1,actor=actor,action='submit',from_status='',to_status=obj.status,reason=obj.reason,evidence_reference=obj.evidence_reference)
            return snapshot(obj),201,audit(obj,actor,cap,None,obj.reason)
    try:return execute_command(actor=actor,scope='inventory-operations',action=cap,key=key,payload=data,request_id=request_id,authorize=authorize,operation=operation)
    except IntegrityError as exc:raise CommandConflict('Source event, controlled physical document line or distinct count identity is already claimed.') from exc


def build_intent(obj):
    if obj.policy is None:invalid('Independent posting policy authority is not configured.')
    policy_for(obj.policy_id,obj.policy.version)
    if obj.kind=='ADJUSTMENT' and OperationRequest.objects.filter(count_session_id=obj.count_session_id,status='POSTED').exists():invalid('This count already has a posted adjustment.')
    lines=[];versions={};kind={'OPENING_CORRECTION':'CORRECTION'}.get(obj.kind,obj.kind)
    if kind=='COUNT':invalid('A count never posts stock; investigate then request an adjustment.')
    for row in obj.lines.select_related('stock','location','destination'):
        qty=row.quantity;src=None;dst=None;quality=row.quality
        if obj.kind=='OPENING_CORRECTION':
            if opening_target(obj.related,row.stock,row.location)!=row.baseline:invalid('Opening target changed; submit a fresh correction.')
            qty=abs(row.difference)
            if row.difference<0:
                if row.quality!='RELEASED':invalid('Removal of held opening stock requires a later approved ledger policy; request remains captured.')
                src=row.location
            else:dst=row.location;quality='HELD'
        elif kind=='ADJUSTMENT':
            current,version=available(row.stock,row.location,row.quality)
            if current!=row.baseline or version!=row.balance_version:invalid('Count snapshot is stale; recount and investigate.')
            qty=abs(row.difference)
            if qty==0:continue
            if row.difference<0:src=row.location
            else:dst=row.location;quality='HELD'
        elif kind in ['IN','OPENING','RETURN']:dst=row.location
        else:src=row.location;dst=row.destination
        line={'stock':str(row.stock_id),'unit':str(row.unit_id),'quantity':format(qty,'f'),'quality':quality}
        for name,loc in [('from_location',src),('to_location',dst)]:
            if loc:
                line[name]=str(loc.pk);acct=key_for(row.stock,loc,quality)
                balance=BalanceProjection.objects.filter(balance_key=acct).first();versions[acct]=balance.version if balance else 0
        if row.original_line_id:line['original_line']=str(row.original_line_id)
        lines.append(line)
    if not lines:invalid('No nonzero investigated variance to post.')
    confirmed=obj.decisions.get(action='confirm')
    intent={'kind':kind,'policy':str(obj.policy_id),'policy_version':obj.policy.version,'source_system':obj.source_system,
        'source_event':obj.source_event,'effective_at':confirmed.created_at.isoformat(),'reason':obj.reason,'lines':lines,'expected_versions':versions}
    if obj.related_id:intent['related']=str(obj.related_id)
    return intent


def transition_request(*,actor,pk,action,data,version,key,request_id):
    require_synthetic_environment()
    if action not in CAPS or action=='submit':invalid('Unknown transition.')
    serializer=TransitionInput(data=data);serializer.is_valid(raise_exception=True);values=serializer.validated_data
    if action!='approve' and values.get('recorder'):invalid('Recorder is selected only in the independent approval.')
    cap=CAPS[action]
    def authorize():
        posting_locks();require_actor(actor,cap)
        scope_request(actor,OperationRequest.objects.get(pk=pk))
    def operation():
        with synthetic_write():
            obj=OperationRequest.objects.select_for_update().get(pk=pk);scope_request(actor,obj)
            if obj.version!=version:raise VersionConflict()
            before=snapshot(obj)
            if obj.status in ['REJECTED','POSTED']:invalid('Terminal requests cannot change.')
            if action!='reject':require_controlled_capture(obj)
            if obj.kind=='OUT' and action in ['verify','confirm','approve']:revalidate_issue(obj)
            reason=sanitize(values['reason']);evidence=sanitize(values['evidence_reference'])
            if action=='verify':
                if obj.status!='SUBMITTED':invalid('Only submitted evidence can be verified.')
                require_independent_actor(actor,obj.requested_by_id);obj.status='VERIFIED'
            elif action=='investigate':
                if obj.kind not in ['COUNT','ADJUSTMENT','OPENING_CORRECTION'] or obj.status!='VERIFIED':invalid('Verify discrepancy evidence before investigation.')
                obj.status='INVESTIGATED'
            elif action=='confirm':
                if obj.kind=='COUNT':invalid('Counts are reconciled/investigated; they do not confirm stock movement.')
                required='INVESTIGATED' if obj.kind in ['ADJUSTMENT','OPENING_CORRECTION'] else 'VERIFIED'
                if obj.status!=required:invalid('Evidence/investigation stage is incomplete.')
                obj.status='CONFIRMED'
            elif action in ['approve','reject']:
                for maker in {obj.requested_by_id,*obj.decisions.filter(action__in=['verify','investigate','confirm']).values_list('actor_id',flat=True)}:require_independent_actor(actor,maker)
                if action=='reject':obj.status='REJECTED'
                else:
                    if obj.status!='CONFIRMED':invalid('Physical confirmation is required before independent approval.')
                    if not values.get('recorder'):invalid('Select the authorized recording employee.')
                    recorder=User.objects.get(pk=values['recorder']);require_independent_actor(actor,recorder.pk)
                    require_actor(recorder,CAPS['record']);require_actor(recorder,'inventory.post_synthetic_transaction');scope_request(recorder,obj)
                    for executor in obj.decisions.filter(action__in=['verify','investigate','confirm']).values_list('actor_id',flat=True):require_independent_actor(recorder,executor)
                    intent=build_intent(obj)
                    if intent['kind'] in obj.policy.rules['approval_kinds']:
                        require_actor(actor,'inventory.approve_synthetic_transaction')
                        approval=LedgerApproval.objects.create(maker=recorder,approver=actor,policy=obj.policy,intent_hash=payload_hash(intent),reference='synthetic:operation:'+str(obj.pk),decision='APPROVED')
                        intent['approval']=str(approval.pk)
                    obj.recording_employee=recorder;obj.sealed_intent=intent;obj.status='APPROVED'
            elif action=='record':
                if obj.status!='APPROVED' or obj.recording_employee_id!=actor.pk:raise PermissionDenied('Only the independently selected recording employee may record.')
                # Revalidate review authority, segregation and scope at execution time.
                reviewer=obj.decisions.get(action='approve').actor
                require_actor(reviewer,CAPS['approve']);scope_request(reviewer,obj);require_independent_actor(reviewer,actor.pk)
                result,_,_=post_transaction(actor=actor,intent=obj.sealed_intent,key='operation:'+str(obj.pk),request_id=request_id)
                obj.ledger_transaction_id=result['id'];obj.status='POSTED'
            advance_version(obj,update_fields=['status','recording_employee','sealed_intent','ledger_transaction'])
            OperationDecision.objects.create(request=obj,version=obj.version,actor=actor,action=action,from_status=before['status'],to_status=obj.status,reason=reason,evidence_reference=evidence)
            return snapshot(obj),200,audit(obj,actor,cap,before,reason)
    try:return execute_command(actor=actor,scope='inventory-operations',action=cap,key=key,payload={'id':str(pk),'action':action,'version':version,'data':data},request_id=request_id,authorize=authorize,operation=operation)
    except IntegrityError as exc:raise CommandConflict('Workflow evidence, count consumption or ledger integrity conflict.') from exc
