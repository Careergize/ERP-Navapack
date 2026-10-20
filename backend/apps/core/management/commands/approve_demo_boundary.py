from apps.core.demo import DEMO_SETTINGS_MODULES
"""Trusted operator command; never invoked by startup or deployment build."""
import hashlib
from datetime import timedelta
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone


class Command(BaseCommand):
    help = 'Stamp a separately approved empty dedicated DEMO database using its migration-owner connection.'

    def add_arguments(self, parser):
        parser.add_argument('--database', required=True)
        parser.add_argument('--instance', required=True)
        parser.add_argument('--runtime-role', required=True)
        parser.add_argument('--approval-reference', required=True)
        parser.add_argument('--backup-reference', required=True)
        parser.add_argument('--days', type=int, default=30)

    def handle(self, **o):
        if (settings.SETTINGS_MODULE not in DEMO_SETTINGS_MODULES or settings.APP_ENV != 'DEMO'
                or o['database'] != settings.DEMO_DATABASE_NAME or o['instance'] != settings.DEMO_INSTANCE_ID
                or not 1 <= o['days'] <= 90):
            raise CommandError('Explicit matching DEMO identity and duration (1–90 days) required.')
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute('SELECT current_database(),current_user')
            database, owner = cursor.fetchone()
            if database != o['database'] or owner == o['runtime_role']:
                raise CommandError('Use the approved migration owner, distinct from runtime.')
            cursor.execute('''SELECT rolsuper OR rolcreatedb OR rolcreaterole OR rolbypassrls OR rolinherit
                OR EXISTS(SELECT 1 FROM pg_auth_members WHERE member=r.oid)
                OR EXISTS(SELECT 1 FROM pg_database WHERE datname=current_database() AND datdba=r.oid)
                FROM pg_roles r WHERE rolname=%s''', [o['runtime_role']])
            role = cursor.fetchone()
            if role is None or role[0]:
                raise CommandError('Runtime role must exist and have no administrative capabilities.')
            cursor.execute('SELECT 1 FROM core_demoboundary')
            if cursor.fetchone():
                raise CommandError('Identity already stamped; no overwrite/reset. Provision a fresh reviewed database.')
            for table in ('accounts_user', 'inventory_ledgerentry', 'inventory_inspection', 'commercial_commercialdocument', 'rehearsal_rehearsaljob'):
                from psycopg import sql
                cursor.execute(sql.SQL('SELECT count(*) FROM {}').format(sql.Identifier(table)))
                if cursor.fetchone()[0]:
                    raise CommandError('Initial stamping requires an empty application dataset.')
            cursor.execute('''INSERT INTO core_demoboundary
                (singleton,environment,database_name,instance_id,secret_sha256,runtime_role,expires_at,approval_reference,backup_reference)
                VALUES (true,'DEMO',%s,%s,%s,%s,%s,%s,%s)''',
                [database, settings.DEMO_INSTANCE_ID, hashlib.sha256(settings.DEMO_EXECUTION_SECRET.encode()).hexdigest(),
                 o['runtime_role'], timezone.now()+timedelta(days=o['days']), o['approval_reference'], o['backup_reference']])
        self.stdout.write('DEMO identity stamped. No users, stock, policies or runtime grants provisioned.')
