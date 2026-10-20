"""Persistent DEMO gate on generated PostgreSQL clones and a non-owner runtime role."""
import copy
import hashlib
import io
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import tempfile
import uuid
from unittest.mock import patch
from contextlib import redirect_stdout
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from django.conf import settings
from django.core.management import call_command
from django.db import connection, connections, DatabaseError, transaction
from django.test import TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework.exceptions import PermissionDenied
import psycopg
from psycopg import sql


class PersistentDemoTests(TransactionTestCase):
    demo_settings_module = "config.settings.demo"
    def test_persistent_clone_full_seed_relogin_gate_isolation_backup_and_restore(self):
        from apps.inventory.ledger_guard import require_synthetic_environment
        require_synthetic_environment()
        saved = copy.deepcopy(connection.settings_dict)
        name = 'navapack_demo_clone_'+uuid.uuid4().hex
        restored = 'navapack_demo_restore_'+uuid.uuid4().hex
        role = 'demo_runtime_'+uuid.uuid4().hex[:16]
        password = secrets.token_urlsafe(32)
        secret = secrets.token_hex(32)
        instance = str(uuid.uuid4())
        params = {k: saved[v] for k, v in [('host','HOST'),('port','PORT'),('user','USER'),('password','PASSWORD')]}
        params['sslmode'] = saved['OPTIONS'].get('sslmode', 'prefer')
        connection.close()
        created = []
        try:
            with psycopg.connect(dbname='postgres', autocommit=True, **params) as admin:
                admin.execute(sql.SQL('CREATE DATABASE {} TEMPLATE {}').format(sql.Identifier(name), sql.Identifier(saved['NAME'])))
                created.append(name)
                admin.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS').format(sql.Identifier(role), sql.Literal(password)))
            connection.settings_dict.update(NAME=name)
            connection.close()
            with override_settings(SETTINGS_MODULE=self.demo_settings_module, APP_ENV='DEMO', DEMO_DATABASE_NAME=name,
                                   DEMO_INSTANCE_ID=instance, DEMO_EXECUTION_SECRET=secret):
                with self.assertRaises(PermissionDenied):
                    require_synthetic_environment()
                import json
                from django.core.management.base import CommandError
                plan_output=io.StringIO()
                call_command('migrate_demo',database=name,stdout=plan_output)
                reviewed=json.loads(plan_output.getvalue().splitlines()[0])
                with self.assertRaises(CommandError):
                    call_command('migrate_demo',database=name,apply_plan='0'*64,backup_reference='synthetic:backup',
                        approval_reference='synthetic:approval',stdout=io.StringIO())
                call_command('migrate_demo',database=name,apply_plan=reviewed['plan_sha256'],backup_reference='synthetic:backup',
                    approval_reference='synthetic:approval',stdout=io.StringIO())
                call_command('approve_demo_boundary', database=name, instance=instance, runtime_role=role,
                    approval_reference='synthetic:approved-clone', backup_reference='synthetic:empty-clone', days=1, stdout=io.StringIO())
                with self.assertRaises(DatabaseError), transaction.atomic(), connection.cursor() as cursor:
                    cursor.execute("UPDATE core_demoboundary SET expires_at=CURRENT_TIMESTAMP")
                psql = shutil.which('psql') or 'C:/Program Files/PostgreSQL/16/bin/psql.exe'
                pg_dump = shutil.which('pg_dump') or 'C:/Program Files/PostgreSQL/16/bin/pg_dump.exe'
                pg_restore = shutil.which('pg_restore') or 'C:/Program Files/PostgreSQL/16/bin/pg_restore.exe'
                env = dict(os.environ, PGHOST=str(params['host']), PGPORT=str(params['port']), PGUSER=params['user'],
                           PGPASSWORD=params['password'], PGDATABASE=name, PGSSLMODE=params['sslmode'])
                granted = subprocess.run([psql, '-X', '-v', 'ON_ERROR_STOP=1', '-v', f'demo_database={name}',
                    '-v', f'demo_runtime_role={role}', '-f', 'scripts/demo_runtime_grants.sql'], env=env, capture_output=True, text=True)
                self.assertEqual(granted.returncode, 0, granted.stderr)
                with tempfile.TemporaryDirectory(dir=Path('.local')) as folder:
                    maker_password, reviewer_password = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
                    maker_file, reviewer_file = Path(folder)/'maker', Path(folder)/'reviewer'
                    maker_file.write_text(maker_password); reviewer_file.write_text(reviewer_password)
                    args = dict(database=name, generation='acceptance', maker_password_file=str(maker_file),
                        reviewer_password_file=str(reviewer_file), approval_reference='synthetic:seed-approval', stdout=io.StringIO())
                    call_command('seed_demo', **args)
                    call_command('seed_demo', **args)  # Repeat does not overwrite/reset users or history.
                    connection.close()
                    connection.settings_dict.update(USER=role, PASSWORD=password)
                    from apps.core.demo import require_demo_environment, development_write
                    self.assertEqual(require_demo_environment(), secret)
                    with override_settings(SETTINGS_MODULE=self.demo_settings_module, DEMO_EXECUTION_SECRET='x'*64), self.assertRaises(PermissionDenied):
                        require_demo_environment()
                    with override_settings(SETTINGS_MODULE=self.demo_settings_module, DEMO_DATABASE_NAME='navapack_demo_wrongtarget'), self.assertRaises(PermissionDenied):
                        require_demo_environment()
                    client = APIClient()
                    login = client.post('/api/v1/auth/login/', {'email':'demo-maker+acceptance@example.invalid', 'password':maker_password}, format='json')
                    self.assertEqual(login.status_code, 200, login.data)
                    client.credentials(HTTP_AUTHORIZATION='Bearer '+login.data['access'])
                    jobs = client.get('/api/v1/rehearsal/jobs/'); self.assertEqual(jobs.status_code, 200, jobs.data)
                    self.assertEqual(jobs.data['count'], 3)
                    dispatched = next(j for j in jobs.data['results'] if j['status']=='DISPATCHED')
                    self.assertFalse(dispatched['operational_posting'])
                    self.assertIsNone(dispatched['invoice_preview']['payable_total'])
                    with self.assertRaises(DatabaseError) as denied:
                        with transaction.atomic(), connection.cursor() as cursor:
                            cursor.execute("SELECT set_config('navapack.demo_nonce',%s,true),set_config('navapack.demo_instance',%s,true)",['wrong',instance])
                            cursor.execute('UPDATE rehearsal_rehearsaljob SET version=version+1 WHERE id=%s',[dispatched['id']])
                    self.assertEqual(denied.exception.__cause__.sqlstate,'42501')
                    for _ in range(2):
                        connection.close()  # New PostgreSQL connection; no in-memory state.
                        self.assertEqual(client.get('/api/v1/rehearsal/jobs/'+dispatched['id']+'/').data['version'], dispatched['version'])
                    again = client.post('/api/v1/auth/login/', {'email':'demo-maker+acceptance@example.invalid', 'password':maker_password}, format='json')
                    self.assertEqual(again.status_code, 200)
                    client.credentials(HTTP_AUTHORIZATION='Bearer '+again.data['access'])
                    self.assertEqual(client.get('/api/v1/rehearsal/jobs/dashboard/').data['jobs'], 3)
                    self.assertEqual(client.get('/api/v1/demo/status/').data, {'environment':'DEMO','instance':instance,
                        'operational_authority':False,'operational_records_empty':True})
                    self.assertEqual(client.get('/api/v1/ready/').status_code, 200)
                    interactive = next(j for j in jobs.data['results'] if j['status']=='DRAFT' and j['sales_order_revision'])
                    barrier = Barrier(2)
                    def review():
                        peer = APIClient(); peer.credentials(HTTP_AUTHORIZATION='Bearer '+again.data['access'])
                        barrier.wait()
                        try:
                            return peer.post('/api/v1/rehearsal/jobs/'+interactive['id']+'/command/',
                                {'action':'review','data':{},'reason':'Synthetic concurrent demo edit'},format='json',
                                HTTP_IF_MATCH=f'"{interactive["version"]}"', HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4())).status_code
                        finally:
                            connections.close_all()
                    with ThreadPoolExecutor(max_workers=2) as pool:
                        outcomes = list(pool.map(lambda _: review(), range(2)))
                    self.assertEqual(sorted(outcomes), [200,412])
                    with override_settings(SETTINGS_MODULE=self.demo_settings_module, DEMO_EXECUTION_SECRET='x'*64):
                        self.assertEqual(settings.SETTINGS_MODULE, self.demo_settings_module)
                        with self.assertRaises(PermissionDenied): require_demo_environment()
                        self.assertEqual(client.get('/api/v1/ready/').status_code, 503)
                    with self.assertRaises(PermissionDenied): require_synthetic_environment()
                    from apps.inventory.ledger_models import LedgerEntry, BalanceProjection
                    from apps.inventory.quality_models import QualityPosting, QualityAuthorization
                    for model in (LedgerEntry, BalanceProjection, QualityPosting, QualityAuthorization):
                        self.assertEqual(model.objects.count(), 0)
                    with self.assertRaises(DatabaseError), transaction.atomic(), connection.cursor() as c:
                        c.execute("INSERT INTO core_demoboundary SELECT * FROM core_demoboundary")
                    with self.assertRaises(DatabaseError), transaction.atomic(), connection.cursor() as c:
                        c.execute(sql.SQL('SET LOCAL ROLE {}').format(sql.Identifier(saved['USER'])))
                    with self.assertRaises(DatabaseError), transaction.atomic(), development_write(), connection.cursor() as c:
                        c.execute('DELETE FROM commercial_commercialrevision')
                    backup = str(Path(folder)/'demo.dump')
                    # Exercise the actual protected exporter under runtime credentials.
                    from scripts import demo_backup
                    with patch('sys.argv',['demo_backup','--database',name,'--output',backup,'--pg-dump',pg_dump]), redirect_stdout(io.StringIO()):
                        demo_backup.main()
                    self.assertEqual(__import__('json').loads(Path(backup+'.json').read_text())['source_database'],name)
                    connection.close(); connection.settings_dict.update(USER=saved['USER'], PASSWORD=saved['PASSWORD'])
                    with psycopg.connect(dbname='postgres', autocommit=True, **params) as admin:
                        admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(restored))); created.append(restored)
                    restore = subprocess.run([pg_restore,'--exit-on-error','--no-owner','--no-privileges','--dbname',restored,backup], env=env, capture_output=True)
                    self.assertEqual(restore.returncode, 0, restore.stderr.decode())
                    with psycopg.connect(dbname=restored, **params) as recovered:
                        self.assertEqual(recovered.execute('SELECT count(*) FROM rehearsal_rehearsaljob').fetchone()[0], 3)
                        self.assertEqual(recovered.execute("SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal AND tgenabled<>'O'").fetchone()[0],0)
                        self.assertFalse(recovered.execute('SELECT navapack_demo_context()').fetchone()[0])
                    self.assertTrue(hashlib.sha256(Path(backup).read_bytes()).hexdigest())
                    call_command('seed_demo', **dict(args,generation='reset',retire_previous_generations=True))
                    from django.contrib.auth import get_user_model
                    self.assertFalse(get_user_model().objects.get(email='demo-maker+acceptance@example.invalid').is_active)
                    self.assertTrue(get_user_model().objects.get(email='demo-maker+reset@example.invalid').is_active)
                    from apps.rehearsal.models import RehearsalJob
                    self.assertEqual(RehearsalJob.objects.count(),6)  # Old history preserved, not deleted.
                    connection.close(); connection.settings_dict.update(USER=role,PASSWORD=password)
                    self.assertEqual(client.get('/api/v1/rehearsal/jobs/').status_code,401)
        finally:
            connections.close_all()
            connection.settings_dict.clear(); connection.settings_dict.update(saved)
            with psycopg.connect(dbname='postgres', autocommit=True, **params) as admin:
                for database in reversed(created):
                    assert database.startswith(('navapack_demo_clone_', 'navapack_demo_restore_'))
                    admin.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(database)))
                admin.execute(sql.SQL('DROP ROLE IF EXISTS {}').format(sql.Identifier(role)))
