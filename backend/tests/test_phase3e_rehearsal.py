"""Disposable populated upgrade and backup recovery; never application migration."""
import hashlib
import json
import os
import re
import subprocess
import uuid
from pathlib import Path
import psycopg
from psycopg import sql
from django.conf import settings
from django.test import TransactionTestCase
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from apps.inventory.ledger_guard import require_synthetic_environment
from tests import test_quality


class Phase3ERehearsalTests(TransactionTestCase):
    def test_populated_twenty_migration_upgrade_and_independent_restore(self):
        if not getattr(settings,'SYNTHETIC_LEDGER_ENABLED',False):
            self.skipTest('Use scripts/test_isolated.py --synthetic-ledger.')
        require_synthetic_environment()
        original=connection.settings_dict['NAME']
        self.assertRegex(original,r'^test_phase3b_[0-9a-f]{32}$')
        checkpoint=[('accounts','0003_employeeresetrequest_one_pending_employee_reset_and_more'),
                    ('core','0002_audit_append_only'),('imports','0004_alter_importbatch_status_alter_importbatch_target'),('inventory',None)]
        executor=MigrationExecutor(connection)
        executor.migrate(checkpoint)
        # Only this verified disposable database is downgraded; no posted rows exist yet.
        require_synthetic_environment()
        executor=MigrationExecutor(connection)
        plan=executor.migration_plan(executor.loader.graph.leaf_nodes())
        # Retain the exact Phase 3 twenty-migration assertion while accounting
        # explicitly for the additive commercial guard's core dependency.
        self.assertEqual(len([p for p, _ in plan if p.app_label != 'commercial']),20)
        self.assertEqual([(p.app_label, p.name) for p, _ in plan if p.app_label == 'commercial'],
                         [('commercial', '0002_evidence_guards'),
                          ('commercial', '0003_governancerecord_governancerevision_and_more'),
                          ('commercial', '0004_proposal_and_revision_guards')])
        self.assertTrue(all(not backwards for _,backwards in plan))
        historical=executor.loader.project_state([p for p in checkpoint if p[1] is not None]+[
            ('masters','0002_alter_area_name_alter_consumable_category_and_more'),('specifications','0005_alter_productmodel_name')]).apps
        user=historical.get_model('accounts','User').objects.create(email='synthetic-upgrade@example.test',name='Synthetic legacy identity',password='unusable-synthetic-only')
        unit=historical.get_model('masters','Unit').objects.create(code='UPGRADE-KG',name='Synthetic legacy unit',dimension='mass',created_by_id=user.pk,updated_by_id=user.pk)
        material=historical.get_model('masters','Material').objects.create(code='UPGRADE-M',name='Synthetic legacy material',category='virgin',unit_id=unit.pk,created_by_id=user.pk,updated_by_id=user.pk)
        event=historical.get_model('core','AuditEvent').objects.create(actor_id=user.pk,request_id=uuid.uuid4(),action='phase3e.legacy_checkpoint',entity_type='masters.material',entity_id=str(material.pk),source_version=1,reason='Synthetic prior audit preserved',summary={'outcome':{'status':'legacy evidence'}})
        ids={'user':str(user.pk),'unit':str(unit.pk),'material':str(material.pk),'audit':str(event.pk)}
        executor.migrate(executor.loader.graph.leaf_nodes())
        self.assertFalse(MigrationExecutor(connection).migration_plan(MigrationExecutor(connection).loader.graph.leaf_nodes()))
        from apps.accounts.models import User
        from apps.masters.models import Material
        from apps.core.models import AuditEvent,AuditEvidence
        self.assertEqual(User.objects.get(pk=user.pk).email,user.email)
        self.assertEqual(Material.objects.get(pk=material.pk).unit_id,unit.pk)
        self.assertEqual(AuditEvent.objects.get(pk=event.pk).summary,{'outcome':{'status':'legacy evidence'}})
        self.assertFalse(AuditEvidence.objects.filter(event_id=event.pk).exists())
        # Populate actual sealed QC/ledger evidence before the recovery snapshot.
        fixture=test_quality.QualityTests()
        fixture.setUp()
        inspection=fixture.accepted();fixture.release(inspection)
        folder=Path('.local/phase3e/recovery').resolve();folder.mkdir(parents=True,exist_ok=True)
        token=uuid.uuid4().hex;dump=folder/(token+'.dump')
        binary=Path('C:/Program Files/PostgreSQL/16/bin')
        self.assertTrue((binary/'pg_dump.exe').is_file(),'PostgreSQL16 client tools required for rehearsal.')
        config=connection.settings_dict
        env={**os.environ,'PGHOST':config['HOST'],'PGPORT':str(config['PORT']),'PGUSER':config['USER'],
             'PGPASSWORD':config['PASSWORD'],'PGSSLMODE':config.get('OPTIONS',{}).get('sslmode','prefer')}
        tables=['accounts_user','masters_unit','masters_material','core_auditevent','core_auditevidence',
                'inventory_ledgertransaction','inventory_ledgerentry','inventory_balanceprojection',
                'inventory_inspection','inventory_inspectionreview','inventory_qualityauthorization','inventory_qualityposting']
        def fingerprints(cursor):
            # row_to_json renders timestamptz using the session zone; compare UTC semantics.
            cursor.execute("SET TIME ZONE 'UTC'")
            result={}
            for table in tables:
                cursor.execute(sql.SQL('SELECT row_to_json(t)::text FROM {} t ORDER BY id').format(sql.Identifier(table)))
                rows=[r[0] for r in cursor.fetchall()]
                result[table]={'rows':len(rows),'sha256':hashlib.sha256('\n'.join(rows).encode()).hexdigest()}
            return result
        with connection.cursor() as cursor:expected=fingerprints(cursor)
        subprocess.run([str(binary/'pg_dump.exe'),'--format=custom','--no-owner','--no-privileges','--file',str(dump),'--dbname',original],env=env,check=True,capture_output=True)
        restored='test_phase3b_'+uuid.uuid4().hex;created=False
        params={'host':config['HOST'],'port':config['PORT'],'user':config['USER'],'password':config['PASSWORD'],
                'sslmode':config.get('OPTIONS',{}).get('sslmode','prefer')}
        try:
            with psycopg.connect(dbname='postgres',autocommit=True,**params) as admin:
                with admin.cursor() as cursor:
                    cursor.execute('SELECT 1 FROM pg_database WHERE datname=%s',[restored])
                    self.assertIsNone(cursor.fetchone(),'Refusing to reuse a recovery database.')
                    cursor.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(restored)));created=True
            subprocess.run([str(binary/'pg_restore.exe'),'--exit-on-error','--no-owner','--no-privileges','--dbname',restored,str(dump)],env=env,check=True,capture_output=True)
            with psycopg.connect(dbname=restored,autocommit=True,**params) as recovered:
                with recovered.cursor() as cursor:
                    self.assertEqual(fingerprints(cursor),expected)
                    cursor.execute("SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal AND tgenabled<>'O'")
                    self.assertEqual(cursor.fetchone()[0],0)
                    with self.assertRaises(psycopg.Error):cursor.execute('DELETE FROM inventory_ledgerentry')
                    self.assertEqual(fingerprints(cursor),expected)
            result={'source_database':original,'restored_database':restored,'applied_upgrade':[m.app_label+'.'+m.name for m,_ in plan],
                    'preserved_legacy_ids':ids,'recovered_fingerprints':expected,'backup_sha256':hashlib.sha256(dump.read_bytes()).hexdigest(),
                    'backup_path':str(dump),'all_triggers_enabled':True,'restored_writes_without_nonce_rejected':True}
            (folder/(token+'.json')).write_text(json.dumps(result,indent=2))
            print('REHEARSAL_RESULT='+json.dumps(result),flush=True)
        finally:
            if created:
                if not re.fullmatch(r'test_phase3b_[0-9a-f]{32}',restored):raise RuntimeError('Unsafe recovery cleanup target.')
                with psycopg.connect(dbname='postgres',autocommit=True,**params) as admin:
                    with admin.cursor() as cursor:cursor.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(restored)))
