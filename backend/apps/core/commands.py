import hashlib
import json
import re
from django.db import transaction
from rest_framework.exceptions import ValidationError, PermissionDenied
from .api import CommandConflict, PreconditionRequired, VersionConflict
from .audit import record_event
from .models import IdempotencyRecord


def payload_hash(payload):
    """Call with validated JSON values; decimal quantities must already be strings."""
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def expected_version(if_match):
    if if_match is None:
        raise PreconditionRequired()
    if not re.fullmatch(r'"[1-9][0-9]*"', if_match):
        raise ValidationError({'If-Match': ['Use a quoted positive integer version.']})
    return int(if_match[1:-1])


def lock_versioned(model, pk, version):
    """Must be inside execute_command's transaction, after permission scoping."""
    if not transaction.get_connection().in_atomic_block:
        raise RuntimeError('Version checks require an atomic command.')
    obj = model.objects.select_for_update().get(pk=pk)
    if obj.version != version:
        raise VersionConflict()
    return obj


def advance_version(obj, *, update_fields):
    obj.version += 1
    obj.save(update_fields=[*update_fields, 'version', 'updated_at'])


def execute_command(*, actor, scope, action, key, payload, request_id, authorize, operation):
    """authorize() runs on replay too. operation() returns (safe_result, status, audit_kwargs).

    Include resource IDs and version preconditions in payload. Scope is resolved by
    the server (future company + aggregate), never copied unchecked from a client.
    No external effects inside callbacks; enqueue only after commit.
    """
    if not actor.is_authenticated or not actor.is_active:
        raise PermissionDenied()
    if not isinstance(key, str) or not key or len(key) > 200 or any(not 33 <= ord(c) <= 126 for c in key):
        raise ValidationError({'Idempotency-Key': ['Use 1-200 printable ASCII characters without spaces.']})
    digest = payload_hash(payload)
    with transaction.atomic():
        authorize()
        record, _ = IdempotencyRecord.objects.get_or_create(
            actor=actor, scope=scope, action=action, key=key,
            defaults={'payload_hash': digest})
        record = IdempotencyRecord.objects.select_for_update().get(pk=record.pk)
        if record.payload_hash != digest:
            raise CommandConflict()
        if record.result is not None:
            return record.result, record.response_status, True
        result, status, audit = operation()
        if not isinstance(status, int) or not 200 <= status < 300:
            raise ValueError('Only successful commands may be retained.')
        # Result must be a JSON object, safe to retain and replay; no credentials.
        if not isinstance(result, dict):
            raise TypeError('Command result must be an object.')
        json.dumps(result, allow_nan=False)
        record_event(actor=actor, action=action, request_id=request_id, **audit)
        record.result, record.response_status = result, status
        record.save(update_fields=['result', 'response_status'])
        return result, status, False
