import re
from .models import AuditEvent

SAFE_SUMMARY_FIELDS = {'before_status', 'after_status', 'changed_fields', 'outcome'}
SENSITIVE = re.compile(r'password|token|secret|authorization|credential|cookie', re.I)


def record_event(*, actor, action, entity_type, entity_id, request_id, summary=None, reason='', source_version=None):
    """Only controlled status summaries; never pass request bodies or user-entered secrets."""
    summary = summary or {}
    if set(summary) - SAFE_SUMMARY_FIELDS:
        raise ValueError('Audit summary fields must be explicitly allowlisted.')
    if SENSITIVE.search(str(summary)) or SENSITIVE.search(reason):
        raise ValueError('Sensitive audit content is prohibited.')
    if len(reason) > 1000 or len(str(summary)) > 4000:
        raise ValueError('Audit content exceeds safe size.')
    return AuditEvent.objects.create(actor=actor, action=action, entity_type=entity_type,
        entity_id=str(entity_id), request_id=request_id, summary=summary,
        reason=reason, source_version=source_version)
