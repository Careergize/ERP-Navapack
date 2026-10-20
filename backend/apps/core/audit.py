"""Structured, bounded audit sanitization; never pass arbitrary request bodies."""
import hashlib
import json
import re
from django.db import transaction
from rest_framework.exceptions import ValidationError
from .models import AuditEvent, AuditEvidence

SAFE_SUMMARY_FIELDS = {'before_status', 'after_status', 'changed_fields', 'outcome'}
SUMMARY_LIMIT = 4000
EVIDENCE_LIMIT = 262144
SECRET_KEYS = {'password','passwordhash','passwd','accesstoken','refreshtoken','token','jwt',
               'authorization','authorizationheader','secret','signingkey','apikey','credential','credentials','cookie','setcookie'}
JWT = re.compile(r'\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b')
HEADER = re.compile(r'\b(?:authorization\s*:\s*)?(?:Bearer|Basic)\s+[A-Za-z0-9._~+/=-]+', re.I)
AUTH_HEADER = re.compile(r'\bauthorization\s*:\s*[^\r\n]+',re.I)
ASSIGNMENT = re.compile(r'\b(password|passwd|access[_ -]?token|refresh[_ -]?token|api[_ -]?key|secret|credential)\s*[:=]\s*(?:"[^"\r\n]*"|\'[^\'\r\n]*\'|[^\s,;]+)', re.I)


def sensitive_key(key):
    normalized = re.sub(r'[^a-z0-9]', '', key.lower())
    return normalized in SECRET_KEYS or normalized.endswith(('password','accesstoken','refreshtoken','signingkey','apikey'))


def sanitize(value, depth=0, budget=None):
    if budget is None: budget=[10000]
    budget[0]-=1
    if depth>16 or budget[0]<0:
        raise ValidationError({'audit':'Change evidence exceeds the supported structure limit.'})
    if isinstance(value,dict):
        if not all(isinstance(k,str) for k in value):
            raise ValidationError({'audit':'Evidence object keys must be strings.'})
        return {k: '[REDACTED]' if sensitive_key(k) else sanitize(v,depth+1,budget) for k,v in value.items()}
    if isinstance(value,list): return [sanitize(v,depth+1,budget) for v in value]
    if isinstance(value,str):
        return ASSIGNMENT.sub(lambda m:m.group(1)+'=[REDACTED]',AUTH_HEADER.sub('[REDACTED]',HEADER.sub('[REDACTED]',JWT.sub('[REDACTED]',value))))
    if value is None or isinstance(value,(bool,int,float)): return value
    raise ValidationError({'audit':'Use JSON-compatible controlled evidence values.'})


def encoded(value):
    try: return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')
    except (ValueError,TypeError): raise ValidationError({'audit':'Invalid evidence value.'})


def record_event(*, actor, action, entity_type, entity_id, request_id, summary=None, reason='', source_version=None):
    summary = summary or {}
    if not isinstance(summary,dict) or set(summary)-SAFE_SUMMARY_FIELDS:
        raise ValueError('Audit summary fields must be explicitly allowlisted.')
    if any(not isinstance(field,str) or sensitive_key(field) for field in summary.get('changed_fields',[])):
        raise ValueError('Sensitive field changes must not be recorded as ordinary business fields.')
    if not isinstance(reason,str) or len(reason)>1000:
        raise ValidationError({'reason':'Use at most 1000 characters.'})
    safe_summary,safe_reason=sanitize(summary),sanitize(reason)
    payload={'schema_version':1,'summary':safe_summary,'reason':safe_reason}
    raw=encoded(payload)
    if len(raw)>EVIDENCE_LIMIT:
        raise ValidationError({'audit':'Change exceeds the 256 KiB evidence limit; submit a smaller bounded change.'})
    evidence=AuditEvidence(payload=payload,sha256=hashlib.sha256(raw).hexdigest())
    if len(encoded(safe_summary))>SUMMARY_LIMIT:
        # Full values are preserved in the protected, scoped change record; never truncated.
        safe_summary={'outcome':{'detail_stored':True,'evidence_id':str(evidence.pk),'sha256':evidence.sha256}}
    with transaction.atomic():
        event=AuditEvent.objects.create(actor=actor,action=action,entity_type=entity_type,entity_id=str(entity_id),
            request_id=request_id,summary=safe_summary,reason=safe_reason,source_version=source_version)
        evidence.event=event; evidence.save()
        return event
