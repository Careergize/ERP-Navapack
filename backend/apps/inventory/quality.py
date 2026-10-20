"""Synthetic-only QC commands; no live authority or numeric criteria are seeded."""
import uuid
from datetime import datetime
from decimal import Decimal
from django.db import IntegrityError
from django.db.models import Max, Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError, PermissionDenied
from apps.core.commands import execute_command, payload_hash
from apps.core.audit import sanitize, record_event
from apps.core.api import CommandConflict, VersionConflict
from apps.accounts.permissions import require_independent_actor
from .authorization import require_actor, require_scope, authority_snapshot
from .ledger_guard import require_synthetic_environment, synthetic_write, posting_locks
from .ledger_models import BalanceProjection, LedgerEntry, PostingPolicy, OpeningCoverage
from .models import StockIdentity, StorageLocation
from .quality_models import (InspectionPlan, PlanApproval, Inspection, InspectionReview,
    QualityAuthorization, QualityPosting, QualityHold, Nonconformance, NonconformanceAction)
from .ledger import quantity, key_for, owner_key, post_transaction

MODELS = {'plans': InspectionPlan, 'inspections': Inspection, 'holds': QualityHold, 'held-stock': BalanceProjection, 'ncr': Nonconformance}
CAPS = {'plan': 'configure_qc', 'publish': 'approve_qc_plan', 'inspect': 'inspect_qc',
        'review': 'review_qc', 'release': 'release_qc', 'hold': 'hold_qc', 'ncr': 'manage_ncr', 'ncr_action': 'manage_ncr'}


def invalid(message):
    raise ValidationError({'quality': message})


def text(data, field, limit=200):
    value = data.get(field)
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        invalid(f'{field} must be nonblank text of at most {limit} characters.')
    return sanitize(value)


def ref(model, value):
    try:
        return model.objects.get(pk=uuid.UUID(str(value)))
    except (ValueError, TypeError, model.DoesNotExist):
        invalid('Unknown typed QC reference.')


def warehouse(obj):
    if isinstance(obj, InspectionPlan):
        return None  # Plans are company-wide controlled specifications, never custody evidence.
    return obj.inspection.location.warehouse_id if isinstance(obj, Nonconformance) else obj.location.warehouse_id


def snapshot(obj):
    data = {'id': str(obj.pk), 'created_at': obj.created_at.isoformat(), 'version': 1,
            'operational_posting': False, 'stock_released': False}
    for field in obj._meta.concrete_fields:
        if field.name in ['id', 'created_at']:
            continue
        value = getattr(obj, field.attname)
        data[field.name] = str(value) if isinstance(value, (uuid.UUID, Decimal)) else value.isoformat() if isinstance(value, datetime) else value
    if isinstance(obj, BalanceProjection):
        source = LedgerEntry.objects.filter(stock=obj.stock,location=obj.location,quality='HELD',delta__gt=0).order_by('-event_at','-created_at').first()
        data['inspection_source_entry'] = str(source.pk) if source else None
        data['source_kind'] = source.transaction.kind if source else None
        data['explicit_containment'] = QualityHold.objects.filter(stock=obj.stock).exists()
        data['whole_scope_supported'] = bool(source and source.delta == obj.quantity and source.transaction.kind in ['OPENING','IN','RETURN'] and not BalanceProjection.objects.filter(stock=obj.stock,quantity__gt=0).exclude(pk=obj.pk).exists())
    if isinstance(obj, Inspection):
        data['reference'] = 'QCI-' + obj.pk.hex.upper()
        data['unit'] = str(obj.stock.unit_id)
        review = InspectionReview.objects.filter(inspection=obj).first()
        data['review'] = snapshot(review) if review else None
        posting = QualityPosting.objects.filter(authorization__review__inspection=obj).first()
        data['ledger_transaction'] = str(posting.transaction_id) if posting else None
        data['stock_released'] = posting is not None
        data['accepted_quantity'] = str(obj.quantity) if review and review.decision == 'ACCEPT' else '0'
        data['rejected_quantity'] = str(obj.quantity) if review and review.decision == 'REJECT' else '0'
        data['pending_quantity'] = str(obj.quantity) if not review or review.decision == 'PENDING' else '0'
        held = BalanceProjection.objects.filter(stock=obj.stock,location=obj.location,quality='HELD').first()
        unchanged = held is not None and held.version == obj.balance_version and held.quantity == obj.quantity
        data['quantity_status_basis'] = 'INSPECTION_SNAPSHOT; release flag records a historical posting, not current availability'
        data['current_scope_unchanged'] = unchanged
        data['remaining_held_quantity'] = str(obj.quantity) if unchanged else None
    if isinstance(obj, InspectionPlan):
        approval = PlanApproval.objects.filter(plan=obj).first()
        data['approval'] = snapshot(approval) if approval else None
    if isinstance(obj, QualityAuthorization):
        posting = QualityPosting.objects.filter(authorization=obj).first()
        data['ledger_transaction'] = str(posting.transaction_id) if posting else None
        data['stock_released'] = posting is not None and obj.direction == 'RELEASE'
    if isinstance(obj, Nonconformance):
        data['reference'] = 'NCR-' + obj.pk.hex.upper()
        data['affected_stock'] = str(obj.hold.stock_id)
        data['affected_location'] = str(obj.hold.location_id)
        data['contained_quantity'] = str(obj.hold.quantity)
        data['unit'] = str(obj.hold.stock.unit_id)
        actions = list(obj.actions.order_by('version'))
        data['actions'] = [snapshot(row) for row in actions]
        data['version'] = 1 + len(actions)
        data['status'] = 'CLOSED' if actions and actions[-1].kind == 'CLOSE' else 'OPEN'
        data['hold_removed'] = False
    return data


def current_plan(plan):
    approval = PlanApproval.objects.filter(plan=plan, decision='APPROVED').first()
    latest = InspectionPlan.objects.filter(reference=plan.reference, planapproval__decision='APPROVED').aggregate(v=Max('revision'))['v']
    if not approval or latest != plan.revision:
        invalid('A current independently approved plan revision is required.')
    if not plan.criteria or not plan.specification_reference or not plan.sampling_reference:
        invalid('Missing approved criteria, specification or sampling reference; release is unavailable.')
    return approval


def criteria_schema(criteria):
    if not isinstance(criteria, list) or not 1 <= len(criteria) <= 30:
        invalid('Supply 1–30 explicit controlled criteria; no defaults are inferred.')
    seen = set()
    for rule in criteria:
        if not isinstance(rule, dict) or set(rule) != {'id', 'type', 'expected', 'reference'}:
            invalid('Each criterion requires id, type, expected and controlled reference.')
        ident = text(rule, 'id', 80)
        if ident in seen:
            invalid('Criterion IDs must be unique.')
        seen.add(ident)
        text(rule, 'reference')
        if rule['type'] == 'BOOLEAN':
            if type(rule['expected']) is not bool:
                invalid('Boolean polarity must be explicitly specified.')
        elif rule['type'] == 'EXACT_TEXT':
            text(rule, 'expected')
        elif rule['type'] == 'DECIMAL_RANGE':
            expected = rule['expected']
            if not isinstance(expected, dict) or set(expected) != {'min', 'max', 'unit', 'method'}:
                invalid('Numeric criteria require approved min/max/unit/method, never inferred limits.')
            if quantity(expected['min'], 6) > quantity(expected['max'], 6):
                invalid('Inverted explicit numeric criterion.')
            text(expected, 'unit'); text(expected, 'method')
        else:
            invalid('Unsupported criterion type.')


def results_pass(plan, observations):
    criteria_schema(plan.criteria)
    if not isinstance(observations, dict) or set(observations) != {r['id'] for r in plan.criteria}:
        invalid('Every controlled criterion needs an exact attributed result.')
    passed = True
    for rule in plan.criteria:
        value = observations[rule['id']]
        if rule['type'] == 'BOOLEAN':
            if type(value) is not bool:
                invalid('Boolean result required.')
            passed = passed and value == rule['expected']
        elif rule['type'] == 'EXACT_TEXT':
            if not isinstance(value, str) or len(value) > 200:
                invalid('Bounded text result required.')
            passed = passed and value == rule['expected']
        else:
            number = quantity(value, 6)
            passed = passed and Decimal(rule['expected']['min']) <= number <= Decimal(rule['expected']['max'])
    return passed


def root_scope(stock, location, actor):
    require_scope(actor, location.warehouse_id)
    if (stock.parent_id or stock.lifecycle != 'REGISTERED' or not stock.physical_reference
        or not stock.source_system.startswith('synthetic:') or not location.is_active
        or not location.warehouse.is_active or not location.warehouse.custody_department_id):
        invalid('Active, physically identified synthetic root and accountable custody are required.')
    master = stock.material or stock.variant or stock.consumable
    if not master.is_active or not stock.unit.is_active:
        invalid('Inactive item or primary unit.')
    if StockIdentity.objects.filter(physical_reference=stock.physical_reference).exclude(pk=stock.pk).exists():
        invalid('Physical marking is ambiguous across registered identities; segregated quantity cannot be established.')
    if not OpeningCoverage.objects.filter(stock=stock, location=location, unit=stock.unit,
                                         owner_key=owner_key(stock), status='KNOWN').exists():
        invalid('Unknown opening coverage is unavailable.')


def whole_held(stock, location, qty, version, actor):
    root_scope(stock, location, actor)
    held = BalanceProjection.objects.filter(balance_key=key_for(stock, location, 'HELD')).first()
    others = BalanceProjection.objects.filter(stock=stock, quantity__gt=0).exclude(balance_key=key_for(stock, location, 'HELD'))
    if not held or held.quantity != qty or others.exists():
        invalid('Partial/ambiguous physical scopes are unsupported. Inspect a whole independently identified root at one custody location; approved portion segregation is pending.')
    if type(version) is not int or held.version != version:
        raise VersionConflict()
    return held


def command(*, actor, action, data, key, request_id, pk=None, version=None):
    require_synthetic_environment()
    if action not in CAPS or not isinstance(data, dict):
        invalid('Unknown QC command.')
    allowed = {
        'plan': {'reference','revision','applicability','material','variant','consumable','criteria','specification_reference','sampling_reference'},
        'publish': {'decision'}, 'inspect': {'plan','source_entry','operation','previous','quantity','balance_version','physical_evidence','observations'},
        'review': {'decision'}, 'release': {'policy','policy_version'}, 'hold': {'stock','location','policy','policy_version'},
        'ncr': {'inspection','hold','classification'}, 'ncr_action': {'kind','owner','target_at','reinspection'}}[action] | {'reason','evidence_reference'}
    if set(data) - allowed:
        invalid('Unknown fields in QC command.')
    reason = text(data, 'reason', 1000); evidence = text(data, 'evidence_reference')
    cap = 'inventory.' + ('close_ncr' if action == 'ncr_action' and data.get('kind') == 'CLOSE' else CAPS[action])
    def authorize():
        require_synthetic_environment(); posting_locks(); require_actor(actor, cap)
        # Serializes plan publication and QC state; roots are locked after this gate.
        from django.db import connection
        with connection.cursor() as c:
            c.execute('SELECT pg_advisory_xact_lock(%s)', [70462032])
        if pk:
            model = InspectionPlan if action == 'publish' else Nonconformance if action == 'ncr_action' else Inspection
            subject = ref(model, pk)
            wh = warehouse(subject)
            if wh: require_scope(actor, wh)
        if action in ['plan', 'publish']:
            require_scope(actor, None)
        if action == 'inspect':
            entry = ref(LedgerEntry, data.get('source_entry'))
            require_scope(actor, entry.location.warehouse_id)
        if action == 'hold': require_scope(actor, ref(StorageLocation, data.get('location')).warehouse_id)
        if action == 'ncr': require_scope(actor, ref(Inspection, data.get('inspection')).location.warehouse_id)
    def operation():
        with synthetic_write():
            obj = None; before = None; wh = None
            if pk and version != (snapshot(subject := ref(Nonconformance if action == 'ncr_action' else InspectionPlan if action == 'publish' else Inspection, pk))['version']):
                raise VersionConflict()
            if action == 'plan':
                if type(data.get('revision')) is not int or data['revision'] < 1:
                    invalid('Positive integer plan revision required.')
                if data.get('applicability') not in ['INCOMING','FINISHED','RETURN','PRODUCTION']:
                    invalid('Explicit plan applicability required.')
                criteria_schema(data.get('criteria'))
                item = {name: data.get(name) for name in ['material','variant','consumable']}
                if sum(bool(v) for v in item.values()) != 1:
                    invalid('Exactly one typed item identity is required.')
                from apps.masters.models import Material, ProductVariant, Consumable
                for name, model in [('material',Material),('variant',ProductVariant),('consumable',Consumable)]:
                    if item[name]: item[name] = ref(model,item[name]).pk
                obj = InspectionPlan.objects.create(reference=text(data,'reference',120), revision=data['revision'],
                    applicability=data['applicability'], **{name+'_id':value for name,value in item.items()}, criteria=sanitize(data['criteria']),
                    specification_reference=text(data,'specification_reference'), sampling_reference=text(data,'sampling_reference'),
                    author=actor, digest=payload_hash(data))
            elif action == 'publish':
                plan = ref(InspectionPlan, pk); require_independent_actor(actor, plan.author_id)
                if data.get('decision') not in ['APPROVED','REJECTED']: invalid('Explicit plan decision required.')
                if InspectionPlan.objects.filter(reference=plan.reference, revision__gt=plan.revision, planapproval__decision='APPROVED').exists():
                    invalid('Cannot publish a superseded revision.')
                obj = PlanApproval.objects.create(plan=plan,actor=actor,decision=data['decision'],reason=reason,evidence_reference=evidence)
            elif action == 'inspect':
                plan = ref(InspectionPlan, data.get('plan')); current_plan(plan)
                entry = ref(LedgerEntry, data.get('source_entry')); stock = StockIdentity.objects.select_for_update().get(pk=entry.stock_id)
                location = entry.location; wh = location.warehouse_id
                require_scope(actor, wh)
                if entry.delta <= 0 or entry.quality != 'HELD': invalid('A positive held inventory event is required.')
                if any(getattr(plan, x+'_id') != getattr(stock, x+'_id') for x in ['material','variant','consumable']): invalid('Plan item does not match stock identity.')
                event_kind = entry.transaction.kind
                if event_kind not in ['OPENING','IN','RETURN']:
                    invalid('QC requirement lineage after transfers/corrections/reversals is not yet approved; this source remains held, never relabeled as an incoming receipt.')
                expected = 'RETURN' if event_kind == 'RETURN' else 'FINISHED' if stock.variant_id else 'INCOMING'
                if plan.applicability != expected: invalid('Plan applicability does not match inventory event; production-stage execution is deferred.')
                qty = quantity(data.get('quantity'),6)
                latest = LedgerEntry.objects.filter(stock=stock, location=location, quality='HELD', delta__gt=0).order_by('-event_at','-created_at').first()
                if qty != entry.delta or latest.pk != entry.pk:
                    invalid('This slice requires one whole current held source event; mixed receipts or historical source substitution are unsupported.')
                whole_held(stock, location, qty, data.get('balance_version'), actor)
                results_pass(plan, data.get('observations'))
                previous = ref(Inspection,data['previous']) if data.get('previous') else None
                if previous and (previous.stock_id != stock.pk or previous.location_id != location.pk): invalid('Reinspection must preserve exact identity and custody.')
                if previous and not InspectionReview.objects.filter(inspection=previous).exists(): invalid('Review original inspection before reinspection.')
                if not previous and Inspection.objects.filter(source_entry=entry).exists(): invalid('Source already inspected; use an explicit reinspection link.')
                from .workflow_models import OperationRequest
                op = ref(OperationRequest,data['operation']) if data.get('operation') else None
                if op and (op.ledger_transaction_id != entry.transaction_id or op.warehouse_id != wh): invalid('Operation is not this receipt/return/opening event.')
                obj = Inspection.objects.create(plan=plan,source_entry=entry,operation=op,previous=previous,stock=stock,location=location,
                    quantity=qty,balance_version=data['balance_version'],physical_evidence=text(data,'physical_evidence'),
                    inspector=actor,observations=sanitize(data['observations']),reason=reason,evidence_reference=evidence)
            elif action in ['review','release']:
                inspection = ref(Inspection, pk); wh = inspection.location.warehouse_id
                stock = StockIdentity.objects.select_for_update().get(pk=inspection.stock_id)
                require_independent_actor(actor, inspection.inspector_id); require_scope(actor,wh); current_plan(inspection.plan)
                before = snapshot(inspection)
                whole_held(stock,inspection.location,inspection.quantity,inspection.balance_version,actor)
                if action == 'review':
                    if data.get('decision') not in ['ACCEPT','REJECT','PENDING']: invalid('Explicit quantity-scope decision required.')
                    if data['decision'] == 'ACCEPT' and not results_pass(inspection.plan,inspection.observations): invalid('Failed criteria cannot be accepted; concessions are unavailable.')
                    obj = InspectionReview.objects.create(inspection=inspection,actor=actor,decision=data['decision'],reason=reason,evidence_reference=evidence)
                    if obj.decision == 'REJECT':
                        hold = QualityHold.objects.create(stock=stock,location=inspection.location,quantity=inspection.quantity,actor=actor,reason=reason,evidence_reference=evidence)
                        record_event(actor=actor, action='inventory.qc_contain',entity_type='inventory.qualityhold',entity_id=hold.pk,
                            request_id=request_id,source_version=1,reason=reason,summary={'outcome':{'after':snapshot(hold),'inspection':str(inspection.pk),'review':str(obj.pk),'authority':authority_snapshot(actor,cap,wh)}})
                else:
                    if Inspection.objects.filter(previous=inspection).exists(): invalid('A later reinspection supersedes this release evidence.')
                    review = InspectionReview.objects.filter(inspection=inspection,decision='ACCEPT').first()
                    if not review: invalid('Independent accepted inspection is required before release.')
                    require_actor(review.actor,'inventory.review_qc'); require_scope(review.actor,wh)
                    if QualityHold.objects.filter(stock=stock).exists(): invalid('Unresolved explicit holds require a separately approved disposition path; inspection alone cannot clear them.')
                    obj = QualityAuthorization.objects.create(review=review,actor=actor,stock=stock,location=inspection.location,
                        quantity=inspection.quantity,direction='RELEASE',reason=reason,evidence_reference=evidence)
                    quality_post(actor,obj,data,key,request_id)
            elif action == 'hold':
                stock = ref(StockIdentity,data.get('stock')); stock = StockIdentity.objects.select_for_update().get(pk=stock.pk)
                location = ref(StorageLocation,data.get('location')); wh = location.warehouse_id; root_scope(stock,location,actor)
                # A permanent root-wide gate blocks transfers and use until a governed disposition is implemented.
                total = BalanceProjection.objects.filter(stock=stock,location=location).aggregate(q=Sum('quantity'))['q'] or Decimal('0')
                if total <= 0: invalid('No present quantity to contain; dispatched traceability requires a future escalation workflow.')
                released = BalanceProjection.objects.filter(balance_key=key_for(stock,location,'RELEASED')).first()
                authorization = None
                if released and released.quantity > 0:
                    authorization = QualityAuthorization.objects.create(actor=actor,stock=stock,location=location,quantity=released.quantity,direction='HOLD',reason=reason,evidence_reference=evidence)
                    quality_post(actor,authorization,data,key,request_id)
                obj = QualityHold.objects.create(stock=stock,location=location,quantity=total,actor=actor,authorization=authorization,reason=reason,evidence_reference=evidence)
            elif action == 'ncr':
                inspection = ref(Inspection,data.get('inspection')); hold = ref(QualityHold,data.get('hold')); wh = inspection.location.warehouse_id
                require_scope(actor,wh)
                if hold.stock_id != inspection.stock_id or hold.location_id != inspection.location_id: invalid('NCR containment must match exact inspected custody.')
                obj = Nonconformance.objects.create(inspection=inspection,hold=hold,actor=actor,classification=text(data,'classification',120),reason=reason,evidence_reference=evidence)
            else:
                ncr = Nonconformance.objects.select_for_update().get(pk=pk); wh = warehouse(ncr); require_scope(actor,wh)
                before = snapshot(ncr); actions = list(ncr.actions.order_by('version')); kinds = {a.kind for a in actions}
                if len(actions) >= 100: invalid('This bounded evidence aggregate supports at most 100 NCR actions.')
                kind = data.get('kind')
                if before['status'] == 'CLOSED' or kind not in ['INVESTIGATE','CORRECTIVE','PREVENTIVE','VERIFY','CLOSE']: invalid('Unsupported or closed NCR transition.')
                if kind in ['CORRECTIVE','PREVENTIVE'] and 'INVESTIGATE' not in kinds: invalid('Investigation is required before action evidence.')
                if kind in ['VERIFY','CLOSE']:
                    if not {'INVESTIGATE','CORRECTIVE','PREVENTIVE'}.issubset(kinds): invalid('Investigation and corrective/preventive evidence required.')
                    for maker in {ncr.actor_id} | {a.actor_id for a in actions if a.kind in ['CORRECTIVE','PREVENTIVE']} | {a.owner_id for a in actions if a.owner_id}:
                        require_independent_actor(actor,maker)
                if kind == 'CLOSE' and 'VERIFY' not in kinds: invalid('Independent effectiveness evidence required before closure.')
                owner = None; target = None; reinspection = None
                if kind in ['CORRECTIVE','PREVENTIVE']:
                    from apps.accounts.models import User, Employee
                    from .ledger import event_time
                    owner = ref(User,data.get('owner'))
                    if not owner.is_active or not Employee.objects.filter(user=owner).exists(): invalid('Active employee action owner required.')
                    require_scope(owner,wh); target = event_time(data.get('target_at'))
                if kind == 'VERIFY':
                    reinspection = ref(Inspection,data.get('reinspection'))
                    ancestor = reinspection
                    while ancestor.previous_id and ancestor.previous_id != ncr.inspection_id:
                        ancestor = ancestor.previous
                    if (ancestor.previous_id != ncr.inspection_id or reinspection.stock_id != ncr.inspection.stock_id
                        or reinspection.location_id != ncr.inspection.location_id
                        or not InspectionReview.objects.filter(inspection=reinspection,decision='ACCEPT').exists()):
                        invalid('Independent effectiveness must reference an accepted linked reinspection of the exact affected stock.')
                    current_plan(reinspection.plan)
                obj = NonconformanceAction.objects.create(ncr=ncr,version=version+1,kind=kind,actor=actor,reason=reason,evidence_reference=evidence,owner=owner,target_at=target,reinspection=reinspection)
            result = snapshot(obj)
            result['warehouse'] = str(wh) if wh else None
            entity = 'inventory.'+obj._meta.model_name
            qc_inspection = obj if isinstance(obj,Inspection) else obj.inspection if isinstance(obj,(InspectionReview,Nonconformance)) else obj.review.inspection if isinstance(obj,QualityAuthorization) and obj.review_id else None
            plan_evidence = obj if isinstance(obj,InspectionPlan) else obj.plan if isinstance(obj,PlanApproval) else qc_inspection.plan if qc_inspection else None
            return result,201,{'entity_type':entity,'entity_id':obj.pk,'source_version':1,'reason':reason,
                'summary':{'outcome':{'before':before,'after':result,'authority':authority_snapshot(actor,cap,wh),'decision':action,'evidence_reference':evidence,
                    'plan_evidence':{'id':str(plan_evidence.pk),'revision':plan_evidence.revision,'digest':plan_evidence.digest} if plan_evidence else None}}}
    try:
        return execute_command(actor=actor,scope='synthetic-qc',action='inventory.qc_'+action,key=key,
            payload={'data':data,'id':str(pk) if pk else None,'version':version},request_id=request_id,authorize=authorize,operation=operation)
    except IntegrityError as exc:
        raise CommandConflict('QC evidence, revision or source was already claimed.') from exc
    except PermissionDenied:
        import logging
        logging.getLogger('inventory.security').warning('QC command authorization denied',extra={'actor_id':str(actor.pk),'request_id':str(request_id),'action':'inventory.qc_'+action,'outcome':'denied'})
        raise


def quality_post(actor, authorization, data, key, request_id):
    policy = ref(PostingPolicy,data.get('policy'))
    if type(data.get('policy_version')) is not int or data['policy_version'] != policy.version:
        invalid('Exact current synthetic posting policy version required.')
    stock = authorization.stock; location = authorization.location
    src, dst = ('HELD','RELEASED') if authorization.direction == 'RELEASE' else ('RELEASED','HELD')
    lines = [{'stock':str(stock.pk),'unit':str(stock.unit_id),'quantity':str(authorization.quantity),'quality':src,'from_location':str(location.pk)},
             {'stock':str(stock.pk),'unit':str(stock.unit_id),'quantity':str(authorization.quantity),'quality':dst,'to_location':str(location.pk)}]
    versions = {}
    for q in [src,dst]:
        row = BalanceProjection.objects.filter(balance_key=key_for(stock,location,q)).first()
        versions[key_for(stock,location,q)] = row.version if row else 0
    intent = {'kind':'QUALITY','policy':str(policy.pk),'policy_version':data['policy_version'],
        'source_system':'synthetic:qc','source_event':str(authorization.pk),'effective_at':timezone.now().isoformat(),
        'reason':authorization.reason,'lines':lines,'expected_versions':versions,'quality_authorization':str(authorization.pk)}
    return post_transaction(actor=actor,intent=intent,key='qc-'+str(authorization.pk),request_id=request_id)


def validate_quality_intent(actor, intent, lines):
    """Called by the authoritative ledger under root locks, not a bypass posting service."""
    auth = ref(QualityAuthorization,intent.get('quality_authorization'))
    if auth.actor_id != actor.pk or QualityPosting.objects.filter(authorization=auth).exists(): invalid('QC authorization is actor-bound and single-use.')
    require_actor(actor,'inventory.release_qc' if auth.direction == 'RELEASE' else 'inventory.hold_qc')
    root_scope(auth.stock,auth.location,actor)
    src,dst = ('HELD','RELEASED') if auth.direction == 'RELEASE' else ('RELEASED','HELD')
    expected = [{'stock':str(auth.stock_id),'unit':str(auth.stock.unit_id),'quantity':format(auth.quantity.normalize(),'f'),'quality':src,'from_location':str(auth.location_id)},
                {'stock':str(auth.stock_id),'unit':str(auth.stock.unit_id),'quantity':format(auth.quantity.normalize(),'f'),'quality':dst,'to_location':str(auth.location_id)}]
    if lines != expected or intent['source_system'] != 'synthetic:qc' or intent['source_event'] != str(auth.pk): invalid('QC transition must conserve exact identity, custody, unit, ownership and quantity.')
    if auth.direction == 'RELEASE':
        review = auth.review; inspection = review.inspection
        if Inspection.objects.filter(previous=inspection).exists(): invalid('Later reinspection supersedes this release evidence.')
        require_independent_actor(actor,inspection.inspector_id); require_actor(review.actor,'inventory.review_qc'); require_scope(review.actor,auth.location.warehouse_id)
        current_plan(inspection.plan)
        if review.decision != 'ACCEPT' or not results_pass(inspection.plan,inspection.observations): invalid('Accepted current inspection criteria required.')
        whole_held(auth.stock,auth.location,auth.quantity,inspection.balance_version,actor)
        if QualityHold.objects.filter(stock=auth.stock).exists(): invalid('Explicit hold/disposition is unresolved.')
    return auth
