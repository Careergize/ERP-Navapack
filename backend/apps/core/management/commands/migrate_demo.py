from apps.core.demo import DEMO_SETTINGS_MODULES
"""Two-step reviewed migration entrypoint; no automatic use at server startup."""
import hashlib
import json
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--database', required=True)
        parser.add_argument('--apply-plan')
        parser.add_argument('--backup-reference')
        parser.add_argument('--approval-reference')

    def handle(self, **o):
        if settings.SETTINGS_MODULE not in DEMO_SETTINGS_MODULES or settings.APP_ENV != 'DEMO' or o['database'] != settings.DEMO_DATABASE_NAME:
            raise CommandError('Only an explicitly matched DEMO database is supported.')
        with connection.cursor() as cursor:
            cursor.execute('SELECT current_database()')
            if cursor.fetchone()[0] != o['database']:
                raise CommandError('Actual database mismatch.')
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        if any(backwards for _, backwards in plan):
            raise CommandError('Only forward migration plans are supported.')
        names = [m.app_label+'.'+m.name for m, _ in plan]
        digest = hashlib.sha256(json.dumps({'database': o['database'], 'plan': names}, sort_keys=True).encode()).hexdigest()
        self.stdout.write(json.dumps({'database': o['database'], 'forward_plan': names, 'plan_sha256': digest}))
        if o['apply_plan']:
            if o['apply_plan'] != digest or not o['backup_reference'] or not o['approval_reference']:
                raise CommandError('Reviewed exact plan hash, backup and approval references required.')
            call_command('migrate', interactive=False)
            self.stdout.write('Approved forward DEMO plan applied. Retain console record with backup/approval evidence.')
