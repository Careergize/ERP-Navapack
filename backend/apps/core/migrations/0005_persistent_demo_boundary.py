"""Add a DEMO-only command branch; retain original synthetic trigger bodies verbatim."""
from importlib import import_module
from django.db import migrations

SCHEMA = r'''
CREATE TABLE core_demoboundary (
 singleton boolean PRIMARY KEY CHECK(singleton),
 environment text NOT NULL CHECK(environment='DEMO'),
 database_name text NOT NULL CHECK(database_name ~ '^navapack_demo_[a-z0-9_]{8,48}$'),
 instance_id uuid NOT NULL, secret_sha256 text NOT NULL CHECK(secret_sha256 ~ '^[0-9a-f]{64}$'),
 runtime_role text NOT NULL, expires_at timestamptz NOT NULL,
 approval_reference text NOT NULL CHECK(length(approval_reference)>0),
 backup_reference text NOT NULL CHECK(length(backup_reference)>0),
 created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE FUNCTION navapack_demo_context() RETURNS boolean AS $$
BEGIN
 IF current_database() !~ '^navapack_demo_[a-z0-9_]{8,48}$' THEN RETURN false; END IF;
 RETURN EXISTS (
  SELECT 1 FROM public.core_demoboundary b JOIN pg_roles r ON r.rolname=current_user
   JOIN pg_database d ON d.datname=current_database()
  WHERE b.singleton AND b.environment='DEMO' AND b.database_name=current_database()
   AND b.runtime_role=current_user AND b.expires_at>CURRENT_TIMESTAMP
   AND NOT (r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolbypassrls OR r.rolinherit OR d.datdba=r.oid)
   AND NOT EXISTS(SELECT 1 FROM pg_auth_members m WHERE m.member=r.oid)
   AND NOT EXISTS(SELECT 1 FROM pg_namespace n WHERE n.nspname='public' AND n.nspowner=r.oid)
   AND NOT EXISTS(SELECT 1 FROM pg_class t JOIN pg_namespace n ON n.oid=t.relnamespace WHERE n.nspname='public' AND t.relowner=r.oid)
   AND b.instance_id::text=current_setting('navapack.demo_instance',true)
   AND b.secret_sha256=encode(sha256(convert_to(current_setting('navapack.demo_nonce',true),'UTF8')),'hex')
 );
END;
$$ LANGUAGE plpgsql STABLE;
CREATE FUNCTION navapack_demo_boundary_immutable() RETURNS trigger AS $$
BEGIN RAISE EXCEPTION 'DEMO identity is immutable; provision a fresh database for reset/rotation' USING ERRCODE='23514'; END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER demo_boundary_immutable BEFORE UPDATE OR DELETE ON core_demoboundary
 FOR EACH ROW EXECUTE FUNCTION navapack_demo_boundary_immutable();
'''

SOURCES = [
 ('apps.commercial.migrations.0002_evidence_guards', 'navapack_commercial_guard'),
 ('apps.commercial.migrations.0004_proposal_and_revision_guards', 'navapack_governance_guard'),
 ('apps.rehearsal.migrations.0002_evidence_guards', 'navapack_rehearsal_guard'),
]


def definition(module, function, demo=False):
    sql = import_module(module).SQL
    start = sql.index('CREATE FUNCTION '+function+'()')
    end = sql.index('$$ LANGUAGE plpgsql;', start) + len('$$ LANGUAGE plpgsql;')
    body = sql[start:end].replace('CREATE FUNCTION ', 'CREATE OR REPLACE FUNCTION ', 1)
    if demo:
        begin = body.index('BEGIN')+len('BEGIN')
        stop = body.index(" IF TG_OP=", begin)
        original = body[begin:stop]
        body = body[:begin]+'\n IF NOT navapack_demo_context() THEN'+original+' END IF;\n'+body[stop:]
    return body


def forwards(apps, editor):
    editor.execute(SCHEMA)
    for module, name in SOURCES:
        editor.execute(definition(module, name, True))


def backwards(apps, editor):
    for module, name in SOURCES:
        editor.execute(definition(module, name))
    editor.execute('DROP FUNCTION navapack_demo_context(); DROP TABLE core_demoboundary; DROP FUNCTION navapack_demo_boundary_immutable();')


class Migration(migrations.Migration):
    dependencies = [('core', '0004_protect_audit_evidence'), ('commercial', '0004_proposal_and_revision_guards'),
                    ('rehearsal', '0004_stock_source_guard')]
    operations = [migrations.RunPython(forwards, backwards)]
