import json
from django.db import connection
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.renderers import JSONRenderer
from apps.core.commands import execute_command, lock_versioned, advance_version, payload_hash
from apps.inventory.authorization import require_actor
from apps.core.demo import development_write as synthetic_write
from .contracts import Strict, clean_reason
from .services import authorize as authorize_commercial
from .models import GovernanceRecord, GovernanceRevision
from .decision_catalog import POLICY_TYPES, DECISIONS

CAPABILITY = 'commercial.manage_proposals'


class Evidence(Strict):
    reference = serializers.CharField(max_length=500)
    description = serializers.CharField(max_length=1000)


class PolicyInput(Strict):
    policy_type = serializers.ChoiceField(choices=POLICY_TYPES)
    title = serializers.CharField(max_length=240)
    draft_payload = serializers.DictField()
    evidence = Evidence(many=True, allow_empty=False, max_length=20)
    proposed_effective_date = serializers.DateField(required=False, allow_null=True)


class DecisionInput(Strict):
    decision_id = serializers.ChoiceField(choices=list(DECISIONS))
    answer = serializers.CharField(max_length=8000)
    evidence = Evidence(many=True, allow_empty=False, max_length=20)
    linked_policy_revision = serializers.UUIDField(required=False, allow_null=True)


def bounded(value, depth=0):
    if depth > 8:
        raise ValidationError('Proposal content exceeds the nesting limit.')
    if isinstance(value, dict):
        if len(value) > 100 or any(not isinstance(k, str) or len(k) > 200 for k in value):
            raise ValidationError('Proposal objects require at most 100 bounded string keys.')
        for item in value.values(): bounded(item, depth+1)
    elif isinstance(value, list):
        if len(value) > 100: raise ValidationError('Proposal arrays allow at most 100 items.')
        for item in value: bounded(item, depth+1)
    elif isinstance(value, str) and len(value) > 8000:
        raise ValidationError('Proposal string exceeds 8000 characters.')


def authorize(actor):
    authorize_commercial(actor)
    return require_actor(actor, CAPABILITY)


def representation(record):
    rev = record.revisions.get(number=record.version)
    return {'id': str(record.pk), 'kind': record.kind, 'key': record.key, 'version': record.version,
        'revision': str(rev.pk), 'status': rev.status, 'content': rev.content, 'sha256': rev.sha256,
        'author': str(rev.author_id), 'created_at': rev.created_at.isoformat(), 'reason': rev.reason,
        'approved': False, 'active': False, 'authority': False}


def command(*, actor, kind, data, reason, key, request_id, pk=None, version=None):
    if kind not in ('POLICY', 'DECISION'):
        raise ValidationError('Unknown proposal kind.')
    reason = clean_reason(reason)
    def check():
        authorize(actor)
        with connection.cursor() as c: c.execute('SELECT pg_advisory_xact_lock(%s)', [70462027])
        if pk: get_object_or_404(GovernanceRecord, pk=pk, owner=actor, kind=kind)
    def operation():
        with synthetic_write():
            s = (PolicyInput if kind == 'POLICY' else DecisionInput)(data=data)
            s.is_valid(raise_exception=True)
            content = json.loads(JSONRenderer().render(s.validated_data))
            bounded(content)
            if len(json.dumps(content, ensure_ascii=False, allow_nan=False).encode()) > 32768:
                raise ValidationError('Proposal content exceeds 32 KiB.')
            stable_key = content['policy_type' if kind == 'POLICY' else 'decision_id']
            if content.get('linked_policy_revision'):
                linked = get_object_or_404(GovernanceRevision, pk=content['linked_policy_revision'], record__owner=actor, record__kind='POLICY')
                content['linked_policy_snapshot'] = {'revision': str(linked.pk), 'sha256': linked.sha256, 'content': linked.content, 'authority': False}
            if len(json.dumps(content, ensure_ascii=False, allow_nan=False).encode()) > 65536:
                raise ValidationError('Linked proposal evidence exceeds 64 KiB.')
            if pk:
                record = lock_versioned(GovernanceRecord, pk, version)
                if record.key != stable_key: raise ValidationError('Proposal type/decision identity is immutable.')
                advance_version(record, update_fields=[])
            else:
                if kind == 'DECISION' and GovernanceRecord.objects.filter(owner=actor, kind=kind, key=stable_key).exists():
                    raise ValidationError('Decision answer already exists; revise its exact record with If-Match.')
                record = GovernanceRecord.objects.create(owner=actor, kind=kind, key=stable_key)
            rev = GovernanceRevision.objects.create(record=record, number=record.version, author=actor, reason=reason,
                status='PROPOSED_UNVERIFIED' if kind == 'POLICY' else 'PENDING_VERIFICATION', content=content, sha256=payload_hash(content))
            return representation(record), 200 if pk else 201, {'entity_type': 'commercial.governancerecord',
                'entity_id': record.pk, 'source_version': rev.number,
                'reason': reason,
                'summary': {'changed_fields': ['revision'], 'after_status': rev.status,
                            'outcome': {'revision': str(rev.pk), 'sha256': rev.sha256, 'authority': False}}}
    return execute_command(actor=actor, scope='commercial-proposals:'+str(actor.pk), action=CAPABILITY,
        key=key, payload={'kind': kind, 'data': data, 'reason': reason, 'id': str(pk) if pk else None, 'version': version},
        request_id=request_id, authorize=check, operation=operation)
