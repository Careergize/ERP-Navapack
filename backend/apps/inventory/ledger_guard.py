"""Fail closed for every caller outside an explicitly stamped disposable test run."""
import re
from contextlib import contextmanager
from django.conf import settings
from django.db import connection,transaction
from rest_framework.exceptions import PermissionDenied


def require_synthetic_environment():
    if (not getattr(settings,'SYNTHETIC_LEDGER_ENABLED',False)
        or settings.SETTINGS_MODULE!='config.settings.test'
        or connection.vendor!='postgresql'
        or connection.settings_dict['HOST'] not in {'127.0.0.1','localhost','::1'}):
        raise PermissionDenied('Operational posting is disabled. Synthetic test context required.')
    expected=getattr(settings,'SYNTHETIC_LEDGER_DATABASE','')
    nonce=getattr(settings,'SYNTHETIC_LEDGER_NONCE','')
    if not re.fullmatch(r'test_phase3b_[0-9a-f]{32}',expected) or not nonce:
        raise PermissionDenied('No verified disposable ledger environment.')
    with connection.cursor() as c:
        c.execute('SELECT current_database(),to_regclass(%s)',['public.navapack_synthetic_environment'])
        name,marker=c.fetchone()
        if name!=expected or marker is None: raise PermissionDenied('Synthetic database identity mismatch.')
        c.execute('SELECT nonce::text FROM public.navapack_synthetic_environment WHERE singleton')
        row=c.fetchone()
        if row is None or row[0]!=nonce: raise PermissionDenied('Synthetic database stamp mismatch.')
    return nonce


@contextmanager
def synthetic_write():
    nonce=require_synthetic_environment()
    with transaction.atomic():
        with connection.cursor() as c:c.execute("SELECT set_config('navapack.ledger_nonce',%s,true)",[nonce])
        yield


def posting_locks(rebuild=False):
    with connection.cursor() as c:
        for gate in (70462026,70462027,70462030):c.execute('SELECT pg_advisory_xact_lock_shared(%s)',[gate])
        c.execute('SELECT '+('pg_advisory_xact_lock' if rebuild else 'pg_advisory_xact_lock_shared')+'(%s)',[70462031])
