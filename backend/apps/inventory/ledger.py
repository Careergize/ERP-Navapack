"""Internal synthetic ledger. All entry points fail closed outside a stamped test DB."""
import hashlib
import logging
import re
import uuid
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from django.db import connection,transaction,IntegrityError
from django.db.models import Sum,Max
from django.utils import timezone
from rest_framework.exceptions import ValidationError,PermissionDenied
from apps.core.commands import execute_command,payload_hash,advance_version
from apps.core.audit import sanitize
from apps.core.api import CommandConflict,VersionConflict,PreconditionRequired
from apps.accounts.permissions import require_independent_actor
from .models import StockIdentity,StorageLocation
from .ledger_models import (PostingPolicy,SourceEvent,LedgerApproval,LedgerTransaction,TransactionLine,
                            LedgerEntry,BalanceProjection,OpeningCoverage)
from .authorization import require_actor,require_scope,oversight,authority_snapshot
from .ledger_guard import require_synthetic_environment,synthetic_write,posting_locks

MAX_Q=Decimal('99999999999999.999999')
POST='inventory.post_synthetic_transaction'
APPROVE='inventory.approve_synthetic_transaction'
APPROVAL_KINDS={'ADJUSTMENT','CORRECTION','REVERSAL'}
security_logger=logging.getLogger('inventory.security')


def fail(message): raise ValidationError({'ledger':message})


def owner_key(stock):
    owner=stock.owner_customer_id or stock.owner_supplier_id or stock.ownership_evidence
    if stock.ownership=='UNRESOLVED' or not owner: fail('Unresolved ownership is unavailable.')
    return stock.ownership+':'+str(owner)


def key_for(stock,location,quality):
    value=f'{stock.pk}|{location.pk}|{stock.unit_id}|{owner_key(stock)}|{quality}'
    return hashlib.sha256(value.encode()).hexdigest()


def quantity(value,scale):
    if not isinstance(value,str) or not re.fullmatch(r'(0|[1-9][0-9]*)(\.[0-9]+)?',value):fail('Use an exact nonnegative decimal string.')
    if len(value)>32 or len(value.partition('.')[2])>scale:fail('Quantity exceeds the explicit synthetic precision policy.')
    result=Decimal(value)
    if result>MAX_Q:fail('Quantity exceeds storage envelope.')
    return result


def policy_for(pk,version):
    policy=PostingPolicy.objects.get(pk=pk)
    if not policy.synthetic or not policy.reference.startswith('synthetic:') or policy.version!=version:fail('Explicit current synthetic policy required.')
    if policy.digest!=payload_hash({'reference':policy.reference,'version':policy.version,'rules':policy.rules}):fail('Policy evidence changed.')
    rules=policy.rules
    if set(rules)!={'scale','released_receipts','closed_through','approval_kinds'}:fail('Unconfigured posting policy.')
    if type(rules['scale']) is not int or not 0<=rules['scale']<=6 or type(rules['released_receipts']) is not bool:fail('Invalid synthetic quantity/quality policy.')
    if not isinstance(rules['approval_kinds'],list) or not APPROVAL_KINDS.issubset(set(rules['approval_kinds'])):fail('Independent correction authority cannot be bypassed.')
    return policy


def event_time(value):
    try: result=datetime.fromisoformat(value)
    except (ValueError,TypeError):fail('Use an ISO datetime with timezone.')
    if timezone.is_naive(result):fail('Event timezone is required.')
    return result


def normalize_intent(intent):
    required={'kind','policy','policy_version','source_system','source_event','effective_at','reason','lines','expected_versions'}
    if not isinstance(intent,dict) or set(intent)-required-{'approval','reverses','related','quality_reference'} or required-set(intent):fail('Use the declared posting intent contract.')
    if not isinstance(intent['reason'],str) or not intent['reason'].strip() or len(intent['reason'])>1000:fail('A bounded reason is required.')
    for name,limit in [('source_system',120),('source_event',200)]:
        if not isinstance(intent[name],str) or not intent[name] or len(intent[name])>limit:fail('Source identity is required and bounded.')
    if not intent['source_system'].startswith('synthetic:'):fail('Only explicitly synthetic source events are accepted.')
    if intent['kind'] not in LedgerTransaction.KINDS:fail('Unknown transaction kind.')
    if not isinstance(intent['lines'],list) or not 1<=len(intent['lines'])<=50:fail('Use 1–50 bounded lines.')
    if not isinstance(intent['expected_versions'],dict):fail('Version map is required.')
    # Validated JSON canonicalization binds approval and idempotency to the exact request.
    payload_hash(intent)
    return intent


def reversal_shape(original):
    lines=[]
    for line in original.lines.order_by('sequence'):
        base={'stock':str(line.stock_id),'unit':str(line.unit_id),'quantity':str(line.quantity),'original_line':str(line.pk)}
        if line.to_location_id:lines.append({**base,'from_location':str(line.to_location_id),'quality':line.quality})
        if line.from_location_id:lines.append({**base,'to_location':str(line.from_location_id),'quality':'HELD'})
    return lines


def canonical_lines(lines,scale):
    result=[]
    for line in lines:
        allowed={'stock','unit','quantity','from_location','to_location','quality','original_line'}
        if not isinstance(line,dict) or set(line)-allowed or not {'stock','unit','quantity'}.issubset(line):fail('Invalid line fields.')
        row={k:str(uuid.UUID(str(line[k]))) for k in ['stock','unit','from_location','to_location','original_line'] if line.get(k)}
        row.update(quantity=format(quantity(line['quantity'],scale).normalize(),'f'),quality=line.get('quality','HELD'))
        if row['quality'] not in ['HELD','RELEASED']:fail('Unknown quality partition.')
        result.append(row)
    return result


def post_transaction(*,actor,intent,key,request_id):
    require_synthetic_environment()
    intent=normalize_intent(intent)
    def authorize():
        require_synthetic_environment();posting_locks()
        require_actor(actor,POST)
        for line in intent['lines']:
            if not isinstance(line,dict):fail('Invalid line.')
            for endpoint in ['from_location','to_location']:
                if line.get(endpoint):
                    location=StorageLocation.objects.select_related('warehouse').get(pk=line[endpoint])
                    require_scope(actor,location.warehouse_id)
    def operation():
        with synthetic_write():
            policy=policy_for(intent['policy'],intent['policy_version']);kind=intent['kind']
            when=event_time(intent['effective_at'])
            if when>timezone.now() or when<=event_time(policy.rules['closed_through']):fail('Future or closed-period posting is unavailable.')
            subject={k:v for k,v in intent.items() if k!='approval'}
            source,created=SourceEvent.objects.get_or_create(system=intent['source_system'],event_key=intent['source_event'],defaults={'intent_hash':payload_hash(subject)})
            source=SourceEvent.objects.select_for_update().get(pk=source.pk)
            if not created:raise CommandConflict('This physical source event was already posted; it cannot be duplicated across users or retry keys.')
            related=None;original=None
            refs=sorted({str(uuid.UUID(str(intent[name]))) for name in ['related','reverses'] if intent.get(name)})
            locked={str(t.pk):t for t in LedgerTransaction.objects.select_for_update().filter(pk__in=refs).order_by('pk')}
            if len(locked)!=len(refs):fail('Unknown original transaction.')
            if intent.get('related'):related=locked[str(uuid.UUID(str(intent['related'])))]
            if kind=='REVERSAL':
                if not intent.get('reverses'):fail('Original transaction required.')
                original=locked[str(uuid.UUID(str(intent['reverses'])))]
                if original.kind in ['OPENING','REVERSAL'] or LedgerTransaction.objects.filter(reverses=original).exists():fail('Opening corrections, repeated reversals and reversal of reversal require a later governed workflow.')
                if original.related_events.filter(kind='RETURN',reversal__isnull=True).exists():fail('Reverse dependent returns first.')
            elif intent.get('reverses'):fail('Only reversals may reference a reversal target.')
            if kind=='RETURN' and (related is None or related.kind!='OUT' or LedgerTransaction.objects.filter(reverses=related).exists()):fail('A non-reversed original OUT is required.')
            if kind=='CORRECTION' and related is None:fail('A correction must identify the original transaction.')
            lines=canonical_lines(intent['lines'],policy.rules['scale'])
            if original and lines!=canonical_lines(reversal_shape(original),6):fail('A reversal must exactly compensate the original physical movements; restored stock is held.')
            ids=sorted({row['stock'] for row in lines})
            stocks={str(s.pk):s for s in StockIdentity.objects.select_for_update().filter(pk__in=ids).order_by('pk')}
            if len(stocks)!=len(ids):fail('Unknown stock identity.')
            for stock in stocks.values():
                if stock.lifecycle!='REGISTERED' or stock.parent_id or not stock.physical_reference or not stock.source_system.startswith('synthetic:'):fail('Only identified synthetic root lots may post; lineage cannot mint stock.')
                owner_key(stock)
                master=stock.material or stock.variant or stock.consumable
                if not master.is_active or not stock.unit.is_active:fail('Inactive stock item or unit.')
                latest=LedgerEntry.objects.filter(stock=stock).aggregate(value=Max('event_at'))['value']
                if latest and when<latest:fail('Backdated posting is unavailable; history must remain feasible.')
            parsed=[];accounts={};changes=defaultdict(lambda:Decimal('0'));openings={};returns=defaultdict(lambda:Decimal('0'))
            for sequence,row in enumerate(lines,1):
                stock=stocks[row['stock']];qty=Decimal(row['quantity']);quality=row['quality']
                if row['unit']!=str(stock.unit_id):fail('Incompatible primary unit; conversions are not inferred.')
                src=StorageLocation.objects.select_related('warehouse').get(pk=row['from_location']) if row.get('from_location') else None
                dst=StorageLocation.objects.select_related('warehouse').get(pk=row['to_location']) if row.get('to_location') else None
                if not (src or dst) or (src and dst and src.pk==dst.pk):fail('Distinct custody endpoints required.')
                if kind in ['OPENING','IN','RETURN'] and (src or not dst):fail('Receipt-like lines need destination only.')
                if kind=='OUT' and (not src or dst):fail('OUT needs source only.')
                if kind=='TRANSFER' and not (src and dst):fail('Transfer needs both endpoints.')
                if kind in ['ADJUSTMENT','CORRECTION'] and bool(src)==bool(dst):fail('A correction is one bounded compensating direction per line.')
                if qty==0 and kind!='OPENING':fail('Only explicit zero opening coverage can have a zero line.')
                if src and quality!='RELEASED' and kind not in ['TRANSFER','REVERSAL']:fail('QC-held stock is unavailable for use or OUT.')
                if dst and not src and quality=='RELEASED':
                    if kind not in ['OPENING','IN'] or not policy.rules['released_receipts'] or not str(intent.get('quality_reference','')).startswith('synthetic:'):fail('New stock defaults held; explicit synthetic QC evidence required for a released test receipt.')
                if kind=='RETURN':
                    if quality!='HELD' or not row.get('original_line'):fail('Returns need original-line identity and remain held.')
                    issue=TransactionLine.objects.get(pk=row['original_line'],transaction=related)
                    if issue.stock_id!=stock.pk or issue.from_location_id!=dst.pk:fail('Return does not match original issue.')
                    returned=TransactionLine.objects.filter(original_line=issue,transaction__kind='RETURN',transaction__reversal__isnull=True).aggregate(value=Sum('quantity'))['value'] or Decimal('0')
                    returns[issue.pk]+=qty
                    if returned+returns[issue.pk]>issue.quantity:fail('Return exceeds original outstanding issue.')
                if kind=='CORRECTION' and not related.lines.filter(stock=stock).exists():fail('Correction cannot change an unrelated identity.')
                for location,sign in [(src,-1),(dst,1)]:
                    if location is None:continue
                    if not location.is_active or not location.warehouse.is_active or location.warehouse.custody_department_id is None:fail('Unresolved or inactive physical custody.')
                    require_scope(actor,location.warehouse_id)
                    acct=key_for(stock,location,quality)
                    accounts[acct]=(stock,location,quality)
                    changes[acct]+=qty*sign
                    coverage_key=(str(stock.pk),str(location.pk))
                    if kind=='OPENING':
                        require_scope(actor,stock.warehouse_id)
                        if coverage_key in openings:fail('Opening coverage must be explicit once per identity/location.')
                        openings[coverage_key]=(stock,location,qty)
                    elif not OpeningCoverage.objects.filter(stock=stock,location=location,unit=stock.unit,owner_key=owner_key(stock),status='KNOWN').exists():fail('Opening coverage is unknown; it is not zero.')
                parsed.append((sequence,row,stock,src,dst,qty,quality))
            expected=intent['expected_versions']
            if set(expected)!=set(accounts):raise PreconditionRequired('Supply every exact custody-key version (0 for an absent key).')
            balances={};before={}
            for acct in sorted(accounts):
                stock,location,quality=accounts[acct]
                balance=BalanceProjection.objects.select_for_update().filter(balance_key=acct).first()
                current=balance.version if balance else 0
                if type(expected[acct]) is not int or expected[acct]!=current:raise VersionConflict()
                value=balance.quantity if balance else Decimal('0');after=value+changes[acct]
                if not 0<=after<=MAX_Q:fail('Insufficient stock or quantity overflow.')
                before[acct]={'quantity':str(value),'version':current}
                if balance is None:balance=BalanceProjection.objects.create(balance_key=acct,stock=stock,location=location,unit=stock.unit,owner_key=owner_key(stock),quality=quality)
                balances[acct]=balance
            for stock,location,qty in openings.values():
                if OpeningCoverage.objects.filter(stock=stock,location=location,status='KNOWN').exists():fail('Opening already established; correction is a separate governed workflow.')
            approval=None
            if kind in policy.rules['approval_kinds']:
                if not intent.get('approval'):raise PermissionDenied('Independent approval evidence is required.')
                approval=LedgerApproval.objects.get(pk=intent['approval'])
                subject={k:v for k,v in intent.items() if k!='approval'}
                if (approval.policy_id!=policy.pk or approval.maker_id!=actor.pk or approval.intent_hash!=payload_hash(subject)
                    or approval.decision!='APPROVED' or not approval.reference.startswith('synthetic:')):raise PermissionDenied('Approval does not bind the exact intent.')
                require_independent_actor(approval.approver,actor.pk);require_actor(approval.approver,APPROVE)
                for _,location,_ in accounts.values():require_scope(approval.approver,location.warehouse_id)
            header=LedgerTransaction.objects.create(source=source,policy=policy,actor=actor,kind=kind,event_at=when,reason=sanitize(intent['reason']),approval=approval,reverses=original,related=related)
            ordinal=0
            for sequence,row,stock,src,dst,qty,quality in parsed:
                line=TransactionLine.objects.create(transaction=header,sequence=sequence,stock=stock,unit=stock.unit,from_location=src,to_location=dst,quantity=qty,quality=quality,original_line_id=row.get('original_line'))
                if qty:
                    for location,sign in [(src,-1),(dst,1)]:
                        if location is None:continue
                        ordinal+=1
                        LedgerEntry.objects.create(transaction=header,line=line,sequence=ordinal,stock=stock,location=location,unit=stock.unit,owner_key=owner_key(stock),quality=quality,balance_key=key_for(stock,location,quality),delta=qty*sign,event_at=when)
            for stock,location,qty in openings.values():
                coverage,_=OpeningCoverage.objects.get_or_create(stock=stock,location=location,unit=stock.unit,owner_key=owner_key(stock))
                coverage.status='KNOWN';coverage.opening_quantity=qty;coverage.transaction=header
                advance_version(coverage,update_fields=['status','opening_quantity','transaction'])
            after={}
            for acct,balance in balances.items():
                balance.quantity+=changes[acct];balance.last_transaction=header
                advance_version(balance,update_fields=['quantity','last_transaction'])
                after[acct]={'quantity':str(balance.quantity),'version':balance.version}
            result={'id':str(header.pk),'version':header.version,'balances':after}
            audit={'entity_type':'inventory.ledgertransaction','entity_id':header.pk,'reason':intent['reason'],'source_version':1,
                'summary':{'outcome':{'status':'committed','source_event':str(source.pk),'policy':{'id':str(policy.pk),'version':policy.version,'digest':policy.digest},
                    'lines':lines,'before':before,'after':after,'approval':str(approval.pk) if approval else None,'reverses':str(original.pk) if original else None,
                    'actor_contexts':[authority_snapshot(actor,POST,warehouse) for warehouse in sorted({str(location.warehouse_id) for _,location,_ in accounts.values()})],
                    'approval_contexts':[authority_snapshot(approval.approver,APPROVE,warehouse) for warehouse in sorted({str(location.warehouse_id) for _,location,_ in accounts.values()})] if approval else [],
                    'approval_evidence':{'maker':str(approval.maker_id),'approver':str(approval.approver_id),'decision':approval.decision,'reference':approval.reference,'intent_hash':approval.intent_hash} if approval else None,
                    'effective_at':when.isoformat(),'kind':kind,'related':str(related.pk) if related else None,'source_identity':{'system':source.system,'event':source.event_key}}}}
            return result,201,audit
    try:
        return execute_command(actor=actor,scope='synthetic-ledger',action=POST,key=key,payload=intent,request_id=request_id,authorize=authorize,operation=operation)
    except IntegrityError as exc:raise CommandConflict('Source, approval, reversal or ledger integrity conflict.') from exc
    except PermissionDenied:
        security_logger.warning('Synthetic ledger authorization denied',extra={'actor_id':str(actor.pk),'request_id':str(request_id),'action':POST,'outcome':'denied'})
        raise


def custody_history(*,actor,stock_id,warehouse_id):
    require_synthetic_environment();require_actor(actor,'inventory.view_synthetic_custody');require_scope(actor,warehouse_id)
    entries=LedgerEntry.objects.filter(stock_id=stock_id,location__warehouse_id=warehouse_id).select_related('stock','location').order_by('event_at','transaction_id','sequence')
    stock=StockIdentity.objects.get(pk=stock_id)
    if not entries.exists():raise PermissionDenied('No permitted custody evidence for this identity.')
    return {'identity':{'id':str(stock.pk),'reference':stock.reference,'unit':str(stock.unit_id)},
        'entries':[{'transaction':str(e.transaction_id),'location':str(e.location_id),'delta':str(e.delta),'quality':e.quality,'event_at':e.event_at.isoformat()} for e in entries]}


def rebuild_projection(*,actor,key,request_id):
    require_synthetic_environment()
    def authorize():
        posting_locks(rebuild=True);require_actor(actor,'inventory.rebuild_synthetic_projection')
        if not oversight(actor):raise PermissionDenied('Explicit company-wide scope required for rebuild.')
    def operation():
        with synthetic_write():
            totals=defaultdict(lambda:Decimal('0'));metadata={};last={}
            previous={row.balance_key:{'quantity':str(row.quantity),'version':row.version,'last_transaction':str(row.last_transaction_id) if row.last_transaction_id else None}
                      for row in BalanceProjection.objects.all()}
            for entry in LedgerEntry.objects.select_related('stock','location').order_by('transaction__created_at','transaction_id','sequence'):
                totals[entry.balance_key]+=entry.delta;metadata[entry.balance_key]=(entry.stock,entry.location,entry.quality);last[entry.balance_key]=entry.transaction_id
            for line in TransactionLine.objects.filter(quantity=0).select_related('stock','to_location').order_by('transaction__created_at','transaction_id','sequence'):
                acct=key_for(line.stock,line.to_location,line.quality);metadata.setdefault(acct,(line.stock,line.to_location,line.quality));last.setdefault(acct,line.transaction_id)
            with connection.cursor() as c:c.execute("SELECT set_config('navapack.ledger_rebuild','on',true)")
            BalanceProjection.objects.exclude(balance_key__in=list(metadata)).delete()
            changed=[]
            for acct in sorted(set(previous)-set(metadata)):changed.append({'key':acct,'before':previous[acct],'after':None})
            for acct,(stock,location,quality) in sorted(metadata.items()):
                if totals[acct]<0:fail('Immutable ledger has invalid negative history.')
                balance,_=BalanceProjection.objects.get_or_create(balance_key=acct,defaults={'stock':stock,'location':location,'unit':stock.unit,'owner_key':owner_key(stock),'quality':quality})
                balance.quantity=totals[acct];balance.last_transaction_id=last.get(acct)
                advance_version(balance,update_fields=['quantity','last_transaction'])
                after={'quantity':str(balance.quantity),'version':balance.version,'last_transaction':str(balance.last_transaction_id) if balance.last_transaction_id else None}
                changed.append({'key':acct,'before':previous.get(acct),'after':after})
            return {'rebuilt_keys':len(metadata)},200,{'entity_type':'inventory.projectionrebuild','entity_id':request_id,'reason':'Synthetic projection rebuild from immutable ledger.',
                'summary':{'outcome':{'keys':len(metadata),'changes':changed,'actor_context':authority_snapshot(actor,'inventory.rebuild_synthetic_projection',None)}}}
    return execute_command(actor=actor,scope='synthetic-ledger',action='inventory.rebuild_synthetic_projection',key=key,payload={'operation':'rebuild'},request_id=request_id,authorize=authorize,operation=operation)
