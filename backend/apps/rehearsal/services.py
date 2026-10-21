"""Transactional rehearsal commands; deliberately no inventory/quality posting imports."""
import copy
from decimal import Decimal, localcontext
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from apps.core.commands import execute_command, lock_versioned, advance_version, payload_hash
from apps.core.api import CommandConflict
from apps.commercial.models import CommercialRevision
from apps.commercial.contracts import clean_reason, ExactDecimal
from apps.inventory.authorization import require_actor, require_scope
from apps.inventory.ledger_guard import posting_locks
from apps.core.demo import require_development_environment as require_synthetic_environment, development_write as synthetic_write
from apps.inventory.models import Warehouse
from .models import RehearsalJob, RehearsalRevision

CAP = 'rehearsal.use_simulation'
STAGES = ['EXTRUSION', 'PRINTING', 'SLITTING', 'MAKING', 'PACKING']
WATERMARK = 'DEVELOPMENT PREVIEW — NOT APPROVED FOR CUSTOMER ISSUE'


def authorize(actor):
    require_synthetic_environment()
    require_actor(actor, CAP)


def scoped(actor):
    authorize(actor)
    from apps.inventory.authorization import oversight, scopes
    rows = RehearsalJob.objects.filter(owner=actor)
    return rows if oversight(actor) else rows.filter(warehouse_id__in=scopes(actor).values('warehouse_id'))


def representation(job):
    snap = job.snapshot
    estimate = snap['source']['estimate']
    return {'id': str(job.pk), 'version': job.version, 'status': job.status,
        'sales_order_revision': str(job.sales_order_revision_id) if job.sales_order_revision_id else None,
        'costing_revision': str(job.costing_revision_id) if job.costing_revision_id else None,
        'purpose': 'SALES_ORDER' if job.sales_order_revision_id else 'PRODUCTION_FOR_STOCK', 'warehouse': str(job.warehouse_id),
        'simulation': True, 'operational_posting': False, 'snapshot': snap,
        'invoice_preview': {'watermark': WATERMARK, 'synthetic': True,
            'currency': snap['source']['input']['currency'], 'net_estimate': estimate['net_estimate'],
            'vat': None, 'led': None, 'payable_total': None,
            'available': job.status == 'DISPATCHED' and job.sales_order_revision_id is not None}}


def quantity(data, name, positive=False):
    value = ExactDecimal().run_validation(data.get(name))
    if positive and Decimal(value) <= 0:
        raise ValidationError({name: 'Positive quantity required.'})
    return value


def fields(data, allowed):
    if not isinstance(data, dict) or set(data) - set(allowed):
        raise ValidationError('Unknown command fields.')


def stage_for(snap, data):
    index = data.get('line')
    if isinstance(index, bool) or not isinstance(index, int):
        raise ValidationError('Integer source line required.')
    route = next((r for r in snap['routes'] if r['line'] == index), None)
    if route is None:
        raise ValidationError('Unknown source line.')
    stage = next((s for s in route['stages'] if s['name'] == data.get('stage')), None)
    if stage is None:
        raise ValidationError('Stage is outside the configured product route.')
    previous = route['stages'][:route['stages'].index(stage)]
    if any(s['status'] != 'COMPLETE' for s in previous):
        raise CommandConflict('Previous product stages are incomplete.')
    return stage, previous


def material_requirements(source):
    result = []
    for index, line in enumerate(source['input']['lines']):
        cost = line.get('costing')
        if cost is None and line.get('costing_snapshot'):
            candidates = line['costing_snapshot']['source']['input']['lines']
            matches = [item for item in candidates if all(str(item.get(key, '')) == str(line.get(key, ''))
                for key in ('variant', 'unit', 'quantity', 'specifications', 'customisation', 'model_revision'))]
            if len(matches) == 1: cost = matches[0].get('costing')
        for item in (cost or {}).get('materials', []):
            result.append({'line': index, 'material': str(item['material']), 'unit': str(item['unit']),
                'quantity': item['quantity'], 'estimated': True, 'basis': 'immutable costing draft; no reservation'})
    return result


def transition(job, action, data):
    snap = copy.deepcopy(job.snapshot)
    now = timezone.now().isoformat()
    if action == 'review':
        fields(data, [])
        if job.status != 'DRAFT': raise CommandConflict('Draft review required.')
        job.status = 'REVIEWED'
    elif action == 'issue':
        fields(data, ['quantity', 'available_quantity'])
        if job.status != 'REVIEWED': raise CommandConflict('Synthetic review required before issue.')
        qty = quantity(data, 'quantity', True); available = quantity(data, 'available_quantity')
        if Decimal(qty) > Decimal(available): raise CommandConflict('Insufficient simulated material stock.')
        snap['material_issue'] = {'quantity': qty, 'available_quantity': available, 'at': now,
            'actor': 'synthetic:store-keeper', 'stock_posted': False,
            'basis': 'isolated scenario input; no physical evidence or stock reservation'}
        job.status = 'ISSUED'
    elif action in ('start', 'complete'):
        allowed = ['line', 'stage', 'remarks'] + (
            ['machine', 'operator', 'input_quantity'] if action == 'start' else ['output_quantity', 'waste', 'rejection'])
        fields(data, allowed)
        if job.status not in ('ISSUED', 'PRODUCTION'): raise CommandConflict('Synthetic material issue required.')
        stage, previous = stage_for(snap, data)
        if action == 'start':
            if stage['status'] != 'PENDING': raise CommandConflict('Stage already started.')
            for name in ('machine', 'operator'):
                if not isinstance(data.get(name), str) or not data[name].startswith('synthetic:') or len(data[name]) > 100:
                    raise ValidationError('Machine and operator must be explicit synthetic identities.')
            input_qty = quantity(data, 'input_quantity', True)
            if previous and Decimal(input_qty) > Decimal(previous[-1]['output_quantity']):
                raise CommandConflict('Stage input exceeds previous output.')
            stage.update(status='STARTED', started_at=now, machine=data['machine'], operator=data['operator'], input_quantity=input_qty)
        else:
            if stage['status'] != 'STARTED': raise CommandConflict('Start this stage first.')
            amounts = {name: quantity(data, name) for name in ('output_quantity', 'waste', 'rejection')}
            if sum(Decimal(v) for v in amounts.values()) != Decimal(stage['input_quantity']):
                raise ValidationError('Output + waste + rejection must equal stage input exactly.')
            if Decimal(amounts['output_quantity']) <= 0: raise ValidationError('Positive output required.')
            stage.update(amounts, status='COMPLETE', completed_at=now)
        if 'remarks' in data:
            if not isinstance(data['remarks'], str) or len(data['remarks']) > 500: raise ValidationError('Remarks exceed contract.')
            stage['remarks'] = data['remarks']
        job.status = 'PRODUCTION'
    elif action == 'qc':
        fields(data, ['outcome', 'remarks'])
        if job.status not in ('PRODUCTION', 'QC_FAILED'): raise CommandConflict('Completed production required.')
        if any(s['status'] != 'COMPLETE' for r in snap['routes'] for s in r['stages']):
            raise CommandConflict('All configured product stages must complete before QC.')
        if data.get('outcome') not in ('PASS', 'FAIL'): raise ValidationError('PASS or FAIL required.')
        remarks = data.get('remarks', '')
        if not isinstance(remarks, str) or len(remarks) > 500: raise ValidationError('Invalid QC remarks.')
        snap['qc'].append({'outcome': data['outcome'], 'remarks': remarks, 'at': now,
            'actor': 'synthetic:qc-inspector', 'operational_release': False,
            'reinspection': bool(snap['qc'])})
        job.status = 'QC_PASSED' if data['outcome'] == 'PASS' else 'QC_FAILED'
    elif action in ('finish', 'dispatch'):
        fields(data, [])
        if action == 'dispatch' and job.costing_revision_id:
            raise CommandConflict('Production-for-stock simulation ends at finished goods; no customer dispatch or invoice.')
        expected = 'QC_PASSED' if action == 'finish' else 'FINISHED'
        if job.status != expected: raise CommandConflict('QC pass and finished-goods progression required.')
        job.status = 'FINISHED' if action == 'finish' else 'DISPATCHED'
    elif action == 'recycle':
        fields(data, ['line', 'stage', 'classification', 'intake', 'recovered', 'rejected', 'disposed', 'unit', 'batch_reference'])
        stage, _ = stage_for(snap, data)
        if stage['status'] != 'COMPLETE':
            raise CommandConflict('Completed source-stage evidence is required.')
        source_line = snap['source']['input']['lines'][data['line']]
        if data.get('unit') != str(source_line['unit']):
            raise ValidationError('Use the exact source unit; conversion is unavailable.')
        classification = data.get('classification')
        if classification not in ('PROCESS_WASTE', 'REJECTED_OUTPUT'):
            raise ValidationError('Classify as PROCESS_WASTE or REJECTED_OUTPUT.')
        batch = data.get('batch_reference')
        if not isinstance(batch, str) or not batch.startswith('synthetic:') or len(batch) > 160:
            raise ValidationError('An explicit synthetic batch reference is required.')
        events = snap.setdefault('recycling', [])
        if any(e['batch_reference'] == batch for e in events):
            raise CommandConflict('Batch reference already recorded; use the original request key to retry.')
        amounts = {name: quantity(data, name, name == 'intake') for name in ('intake', 'recovered', 'rejected', 'disposed')}
        with localcontext() as context:
            context.prec = 60
            if sum(Decimal(amounts[k]) for k in ('recovered','rejected','disposed')) != Decimal(amounts['intake']):
                raise ValidationError('Recovered + rejected + disposed must equal intake exactly.')
            used = sum((Decimal(e['intake']) for e in events if e['line'] == data['line'] and e['stage'] == data['stage'] and e['classification'] == classification), Decimal(0))
            available = Decimal(stage['waste' if classification == 'PROCESS_WASTE' else 'rejection'])
            if used + Decimal(amounts['intake']) > available:
                raise CommandConflict('Intake exceeds remaining recorded source waste/rejection.')
        events.append({**amounts, 'line': data['line'], 'stage': data['stage'], 'unit': data['unit'],
            'classification': classification, 'batch_reference': batch, 'at': now,
            'source_job': str(job.pk), 'source_version': job.version, 'source_revision': str(job.revisions.get(number=job.version).pk),
            'available_stock_credit': False, 'simulation': True})
    else:
        raise ValidationError('Unknown simulation action.')
    snap['history'].append({'action': action, 'status': job.status, 'at': now,
        'synthetic_actor': 'synthetic:workflow', 'operational_authority': False})
    job.snapshot = snap


def command(*, actor, key, request_id, pk=None, version=None, action='create', data=None, reason=''):
    reason = clean_reason(reason)
    payload = {'id': str(pk) if pk else None, 'version': version, 'action': action, 'data': data, 'reason': reason}
    def check():
        authorize(actor)
        posting_locks()
        if pk:
            job = get_object_or_404(scoped(actor), pk=pk)
            require_scope(actor, job.warehouse_id)
        else:
            require_scope(actor, data.get('warehouse'))
    def operation():
        with synthetic_write():
            if pk:
                job = lock_versioned(RehearsalJob, pk, version)
                transition(job, action, data)
                advance_version(job, update_fields=['status', 'snapshot'])
            else:
                is_order = bool(data.get('sales_order_revision'))
                if is_order == bool(data.get('costing_revision')):
                    raise ValidationError('Exactly one immutable commercial source required.')
                source = get_object_or_404(CommercialRevision.objects.select_for_update(),
                    pk=data['sales_order_revision'] if is_order else data['costing_revision'],
                    document__owner=actor, document__kind='SALES_ORDER' if is_order else 'COSTING')
                if source.status == 'CANCELLED' or source.document.status == 'CANCELLED':
                    raise CommandConflict('Cancelled demand cannot start a simulation.')
                warehouse = get_object_or_404(Warehouse, pk=data['warehouse'], is_active=True)
                routes = data['routes']; count = len(source.snapshot['input']['lines'])
                if len(routes) != count or {r['line'] for r in routes} != set(range(count)):
                    raise ValidationError('Provide one product route per sales-order line.')
                for route in routes:
                    names = route['stages']
                    if not names or len(names) != len(set(names)) or any(n not in STAGES for n in names):
                        raise ValidationError('Use unique configured manufacturing stages.')
                    if names != sorted(names, key=STAGES.index): raise ValidationError('Manufacturing stages must follow route order.')
                snap = {'source': source.snapshot, 'source_sha256': source.sha256,
                    'source_kind': 'SALES_ORDER' if is_order else 'COSTING',
                    'material_requirements': material_requirements(source.snapshot),
                    'routes': [{'line': r['line'], 'stages': [{'name': n, 'status': 'PENDING'} for n in r['stages']]} for r in routes],
                    'material_issue': None, 'qc': [], 'history': [], 'authority': 'SIMULATION_ONLY'}
                job = RehearsalJob.objects.create(owner=actor, sales_order_revision=source if is_order else None,
                    costing_revision=None if is_order else source, warehouse=warehouse, snapshot=snap)
            evidence = {'status': job.status, 'state': job.snapshot}
            revision = RehearsalRevision.objects.create(job=job, number=job.version, actor=actor,
                action=action, reason=reason, snapshot=evidence, sha256=payload_hash(evidence))
            return representation(job), 200 if pk else 201, {'entity_type': 'rehearsal.rehearsaljob',
                'entity_id': job.pk, 'source_version': job.version, 'reason': reason,
                'summary': {'after_status': job.status, 'changed_fields': ['simulation_revision'],
                    'outcome': {'revision': str(revision.pk), 'sha256': revision.sha256}}}
    return execute_command(actor=actor, scope='rehearsal-owner:'+str(actor.pk), action=CAP,
        key=key, payload=payload, request_id=request_id, authorize=check, operation=operation)
