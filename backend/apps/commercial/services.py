import json
from decimal import Decimal
from django.db import connection
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.generics import get_object_or_404
from rest_framework.renderers import JSONRenderer
from apps.accounts.models import Employee
from apps.accounts.backends import explicit_permission_codes
from apps.core.commands import execute_command, lock_versioned, advance_version, payload_hash
from apps.core.api import CommandConflict
from apps.inventory.authorization import require_actor, require_scope
from apps.core.demo import require_development_environment as require_synthetic_environment, development_write as synthetic_write
from apps.inventory.models import StockIdentity
from apps.masters.models import Customer, Prospect, ProductVariant, Material, Unit
from apps.specifications.models import ProductModelRevision
from .contracts import DocumentInput, estimate, clean_reason
from .models import CommercialDocument, CommercialRevision


CAPABILITY = 'commercial.use_foundation'


def authorize(actor):
    require_synthetic_environment()
    return require_actor(actor, CAPABILITY)


def scoped(actor):
    authorize(actor)
    return CommercialDocument.objects.filter(owner=actor)


def reference(model, pk, actor):
    permission = f'{model._meta.app_label}.view_{model._meta.model_name}'
    if permission not in explicit_permission_codes(actor):
        raise PermissionDenied('Explicit reference read capability required.')
    return get_object_or_404(model.objects.select_for_update(), pk=pk, is_active=True)


def snapshot(actor, kind, raw):
    serializer = DocumentInput(data=raw)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    party_kind = 'customer' if data.get('customer') else 'prospect' if data.get('prospect') else None
    if kind == 'SALES_ORDER' and party_kind != 'customer':
        raise ValidationError('Sales orders require an existing customer; promote prospects separately.')
    if kind == 'QUOTATION' and party_kind is None:
        raise ValidationError('Quotations require an existing customer or prospect.')
    party = reference(Customer if party_kind == 'customer' else Prospect, data[party_kind], actor) if party_kind else None
    if data.get('classification') and (party is None or (party.customer_type and data['classification'] != party.customer_type)):
        raise ValidationError('Classification conflicts with the customer master.')
    if data.get('marketing_person'):
        if 'accounts.view_employee' not in explicit_permission_codes(actor):
            raise PermissionDenied('Employee reference access required.')
        from .reference_views import marketing_people
        employee = get_object_or_404(marketing_people(actor).select_for_update(), pk=data['marketing_person'])
        data['marketing_snapshot'] = {'id': str(employee.pk), 'version': employee.version}
    if data.get('quotation_revision'):
        get_object_or_404(CommercialRevision, pk=data['quotation_revision'], document__owner=actor, document__kind='QUOTATION')
        # No approved quotation can be created under the v1 contract. Do not label
        # a draft quote as an agreed commercial commitment.
        raise CommandConflict('Approved quotation linkage is unavailable until authority policy is approved.')
    data['party_snapshot'] = {'id': str(party.pk), 'kind': party_kind, 'version': party.version,
                              'name': party.name, 'customer_type': party.customer_type,
                              'address': party.address, 'delivery_address': party.delivery_address} if party else None
    for line in data['lines']:
        variant = reference(ProductVariant, line['variant'], actor)
        unit = reference(Unit, line['unit'], actor)
        if variant.unit_id != unit.pk:
            raise ValidationError('Variant and line units must match exactly; no implicit conversion.')
        line['variant_snapshot'] = {'id': str(variant.pk), 'version': variant.version, 'name': variant.name,
                                     'size': variant.size, 'brand': variant.brand, 'packing_size': variant.packing_size}
        line['unit_snapshot'] = {'id': str(unit.pk), 'version': unit.version, 'code': unit.code, 'dimension': unit.dimension}
        if line.get('stock_identity'):
            require_actor(actor, 'inventory.view_stockidentity')
            stock = get_object_or_404(StockIdentity.objects.select_for_update(), pk=line['stock_identity'])
            require_scope(actor, stock.warehouse_id)
            if stock.variant_id != variant.pk or stock.unit_id != unit.pk:
                raise ValidationError('Stock identity must match the exact product variant and unit.')
            if stock.ownership not in ('COMPANY', 'CUSTOMER') or (stock.ownership == 'CUSTOMER' and (party is None or stock.owner_customer_id != party.pk)):
                raise ValidationError('Stock ownership is incompatible with this customer.')
            line['stock_reference_snapshot'] = {'id': str(stock.pk), 'version': stock.version,
                'warehouse': str(stock.warehouse_id), 'unit': str(stock.unit_id), 'reservation': False}
        if line.get('model_revision'):
            if 'specifications.view_productmodelrevision' not in explicit_permission_codes(actor):
                raise PermissionDenied('Specification revision access required.')
            model = get_object_or_404(ProductModelRevision.objects.select_for_update(), pk=line['model_revision'], sealed=True)
            if model.default_unit_id != unit.pk:
                raise ValidationError('Specification and line units differ.')
            line['model_snapshot'] = {'id': str(model.pk), 'number': model.number, 'name': model.name,
                                      'specifications': model.specifications, 'dimensions': model.dimensions}
        if kind == 'COSTING' and 'costing' not in line:
            raise ValidationError('Costing documents require explicit costing inputs on every line.')
        if kind != 'COSTING' and 'costing' in line:
            raise ValidationError('Use a separate versioned costing document and exact costing_revision reference.')
        if line.get('costing_revision'):
            if kind == 'COSTING':
                raise ValidationError('A costing cannot recursively reference another costing.')
            rev = get_object_or_404(CommercialRevision, pk=line['costing_revision'], document__owner=actor, document__kind='COSTING')
            candidates = rev.snapshot['input']['lines']
            matches = [v for v in candidates if Decimal(v['quantity']) == Decimal(line['quantity']) and all(str(v.get(k, '')) == str(line.get(k, '')) for k in
                       ('variant', 'unit', 'specifications', 'customisation', 'model_revision'))]
            if rev.snapshot['input']['currency'] != data['currency'] or len(matches) != 1:
                raise ValidationError('Costing snapshot must match exact source quantity, currency, unit and specification.')
            line['costing_snapshot'] = {'revision': str(rev.pk), 'sha256': rev.sha256, 'authoritative': False,
                                        'source': rev.snapshot}
        if 'costing' in line:
            for material in line['costing']['materials']:
                master = reference(Material, material['material'], actor)
                reference(Unit, material['unit'], actor)
                if master.unit_id != material['unit'] or material['unit'] != material['price_unit']:
                    raise ValidationError('Material unit and price unit must match its master.')
                material['master_snapshot'] = {'id': str(master.pk), 'version': master.version, 'name': master.name}
    totals = estimate(data)
    for line, result in zip(data['lines'], totals['lines']):
        if 'costing' in result:
            # A per-kg/ctr label needs an explicit exact unit code. No derived conversion.
            code = line['unit_snapshot']['code']
            result['costing']['cost_per_kg'] = result['costing']['cost_per_output_unit'] if code == 'kg' and line['unit_snapshot']['dimension'] == 'mass' else None
            result['costing']['cost_per_ctr'] = result['costing']['cost_per_output_unit'] if code == 'ctr' and line['unit_snapshot']['dimension'] == 'package' else None
    result = json.loads(JSONRenderer().render({'input': data, 'estimate': totals}))
    if len(json.dumps(result, ensure_ascii=False).encode()) > 262144:
        raise ValidationError('Commercial snapshot exceeds 256 KiB; reduce the draft size.')
    return result


def representation(document):
    revision = document.revisions.get(number=document.version)
    return {'id': str(document.pk), 'kind': document.kind, 'version': document.version, 'status': document.status,
            'revision': str(revision.pk), 'snapshot': revision.snapshot, 'sha256': revision.sha256}


def command(*, actor, key, request_id, kind=None, data=None, pk=None, version=None, transition=None, reason=''):
    # Semantic payload and version are hashed in full. Validation/lookup stays inside
    # the operation, allowing replay even when referenced masters later change.
    reason = clean_reason(reason)
    payload = {'kind': kind, 'data': data, 'id': str(pk) if pk else None, 'version': version,
               'transition': transition, 'reason': reason}
    def check():
        authorize(actor)
        # Share the existing catalog gate so master changes cannot race snapshots.
        with connection.cursor() as cursor:
            cursor.execute('SELECT pg_advisory_xact_lock(%s)', [70462027])
        if pk:
            get_object_or_404(CommercialDocument, pk=pk, owner=actor)
    def operation():
        with synthetic_write():
            if pk:
                doc = lock_versioned(CommercialDocument, pk, version)
                if transition:
                    allowed = {'submit': ('DRAFT', 'REVIEW'), 'reopen': ('REVIEW', 'DRAFT'),
                               'cancel': ('DRAFT', 'CANCELLED')}
                    if transition not in allowed:
                        raise CommandConflict('Approval, publication, confirmed amendments, PDF/email and fulfilment are unavailable.')
                    before, after = allowed[transition]
                    if doc.status != before:
                        raise CommandConflict('Invalid commercial transition.')
                    snap = doc.revisions.get(number=doc.version).snapshot
                    doc.status = after
                else:
                    if doc.status != 'DRAFT':
                        raise CommandConflict('Only drafts may be edited; reopen review first.')
                    snap = snapshot(actor, doc.kind, data)
                    # Retain immutable draft lineage through all later edits.
                    previous = doc.revisions.get(number=doc.version).snapshot
                    if 'synthetic_source' in previous:
                        snap['synthetic_source'] = previous['synthetic_source']
                advance_version(doc, update_fields=['status'])
            else:
                if kind not in ('COSTING', 'QUOTATION', 'SALES_ORDER'):
                    raise ValidationError('Unknown commercial document kind.')
                snap = snapshot(actor, kind, data)
                doc = CommercialDocument.objects.create(kind=kind, owner=actor)
            revision = CommercialRevision.objects.create(document=doc, number=doc.version, actor=actor, status=doc.status,
                                              reason=reason, snapshot=snap, sha256=payload_hash(snap))
            return representation(doc), 200 if pk else 201, {
                'entity_type': 'commercial.commercialdocument', 'entity_id': doc.pk, 'source_version': doc.version,
                'reason': reason,
                'summary': {'after_status': doc.status, 'changed_fields': ['revision'],
                            'outcome': {'revision': str(revision.pk), 'sha256': revision.sha256}}}
    return execute_command(actor=actor, scope='commercial-owner:'+str(actor.pk), action=CAPABILITY,
                           key=key, payload=payload, request_id=request_id, authorize=check, operation=operation)
