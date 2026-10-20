"""Independent persistent DEMO boundary. Never authorizes inventory ledger writes."""
import hashlib
import re
from contextlib import contextmanager
from django.conf import settings
from django.db import connection, transaction
from rest_framework.exceptions import PermissionDenied
from apps.inventory.ledger_guard import require_synthetic_environment, synthetic_write


def require_demo_environment():
    if (settings.SETTINGS_MODULE != 'config.settings.demo'
            or getattr(settings, 'APP_ENV', None) != 'DEMO'
            or connection.vendor != 'postgresql'):
        raise PermissionDenied('An explicitly approved DEMO environment is required.')
    name = getattr(settings, 'DEMO_DATABASE_NAME', '')
    nonce = getattr(settings, 'DEMO_EXECUTION_SECRET', '')
    instance = getattr(settings, 'DEMO_INSTANCE_ID', '')
    if not re.fullmatch(r'navapack_demo_[a-z0-9_]{8,48}', name) or len(nonce) < 64 or not instance:
        raise PermissionDenied('DEMO identity is not configured.')
    with connection.cursor() as cursor:
        cursor.execute('''SELECT b.secret_sha256, b.instance_id::text, b.runtime_role,
            b.database_name, b.expires_at > CURRENT_TIMESTAMP,
            r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolbypassrls OR r.rolinherit OR d.datdba=r.oid
             OR EXISTS(SELECT 1 FROM pg_auth_members m WHERE m.member=r.oid)
             OR EXISTS(SELECT 1 FROM pg_namespace n WHERE n.nspname='public' AND n.nspowner=r.oid)
             OR EXISTS(SELECT 1 FROM pg_class t JOIN pg_namespace n ON n.oid=t.relnamespace WHERE n.nspname='public' AND t.relowner=r.oid),
            current_database(), current_user
            FROM core_demoboundary b CROSS JOIN pg_roles r CROSS JOIN pg_database d
            WHERE b.singleton AND r.rolname=current_user AND d.datname=current_database()''')
        row = cursor.fetchone()
    if (not row or row[:4] != (hashlib.sha256(nonce.encode()).hexdigest(), str(instance), row[7], name)
            or not row[4] or row[5] or row[6] != name):
        raise PermissionDenied('DEMO stamp, runtime role, expiry or database identity mismatch.')
    return nonce


def require_development_environment():
    if settings.SETTINGS_MODULE == 'config.settings.demo':
        return require_demo_environment()
    return require_synthetic_environment()


@contextmanager
def development_write():
    if settings.SETTINGS_MODULE != 'config.settings.demo':
        with synthetic_write():
            yield
        return
    nonce = require_demo_environment()
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('navapack.demo_nonce',%s,true), set_config('navapack.demo_instance',%s,true)",
                           [nonce, str(settings.DEMO_INSTANCE_ID)])
        yield
