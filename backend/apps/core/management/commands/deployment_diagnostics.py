from apps.core.demo import DEMO_SETTINGS_MODULES
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


class Command(BaseCommand):
    help = 'Read-only startup checks; never runs migrations or provisions grants.'

    def handle(self, **options):
        if MigrationExecutor(connection).migration_plan(MigrationExecutor(connection).loader.graph.leaf_nodes()):
            raise CommandError('Pending migrations; apply only through the separately approved migration procedure.')
        if settings.SETTINGS_MODULE in DEMO_SETTINGS_MODULES:
            from apps.core.demo import require_demo_environment
            try:
                require_demo_environment()
            except Exception:
                raise CommandError('DEMO boundary unavailable; verify approved database, stamp, expiry and restricted runtime role.')
        self.stdout.write('Database schema and selected environment are ready. No migration or seed executed.')
