"""Draft derivation with immutable source evidence; never commercial acceptance."""
from copy import deepcopy
from django.db import connection
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from apps.core.commands import execute_command, payload_hash
from apps.core.api import CommandConflict
from apps.core.demo import development_write as synthetic_write
from .contracts import DocumentInput, clean_reason
from .models import CommercialDocument, CommercialRevision
from . import services


def editable(serializer, raw):
    result = {}
    for name, field in serializer.fields.items():
        if name not in raw:
            continue
        value = raw[name]
        if isinstance(field, serializers.ListSerializer):
            value = [editable(field.child, row) for row in value]
        elif isinstance(field, serializers.Serializer):
            value = editable(field, value)
        result[name] = deepcopy(value)
    return result


def derive(*, actor, source_id, key, request_id, reason):
    reason = clean_reason(reason)
    payload = {'command': 'derive_draft', 'source_revision': str(source_id), 'reason': reason}
    def authorize():
        services.authorize(actor)
        # Match the existing commercial/catalog lock order before source row locks.
        with connection.cursor() as cursor:
            cursor.execute('SELECT pg_advisory_xact_lock(%s)', [70462027])
        get_object_or_404(CommercialRevision, pk=source_id, document__owner=actor)
    def operation():
        source = get_object_or_404(CommercialRevision.objects.select_related('document').select_for_update(),
                                   pk=source_id, document__owner=actor)
        target = {'COSTING': 'QUOTATION', 'QUOTATION': 'SALES_ORDER'}.get(source.document.kind)
        if target is None or source.status == 'CANCELLED' or source.document.status == 'CANCELLED':
            raise ValidationError('Derive only an uncancelled costing or quotation revision.')
        if source.number != source.document.version:
            raise CommandConflict('Source revision is stale. Reload the current draft before deriving.')
        data = editable(DocumentInput(), source.snapshot['input'])
        data.pop('quotation_revision', None)
        for line in data['lines']:
            if source.document.kind == 'COSTING':
                line.pop('costing', None)
                line['costing_revision'] = str(source.pk)
        snap = services.snapshot(actor, target, data)
        snap['synthetic_source'] = {'document': str(source.document_id), 'revision': str(source.pk),
            'number': source.number, 'kind': source.document.kind, 'sha256': source.sha256,
            'mapping': 'UNAPPROVED_DRAFT_DERIVATION', 'customer_acceptance': False,
            'operational': False}
        with synthetic_write():
            doc = CommercialDocument.objects.create(kind=target, owner=actor)
            revision = CommercialRevision.objects.create(document=doc, number=doc.version, actor=actor,
                status=doc.status, reason=reason, snapshot=snap, sha256=payload_hash(snap))
        return services.representation(doc), 201, {'entity_type': 'commercial.commercialdocument',
            'entity_id': doc.pk, 'source_version': doc.version, 'reason': reason,
            'summary': {'after_status': doc.status, 'changed_fields': ['revision'],
                        'outcome': {'revision': str(revision.pk), 'sha256': revision.sha256,
                                    'source_revision': str(source.pk)}}}
    return execute_command(actor=actor, scope='commercial-owner:'+str(actor.pk), action=services.CAPABILITY,
        key=key, payload=payload, request_id=request_id, authorize=authorize, operation=operation)
