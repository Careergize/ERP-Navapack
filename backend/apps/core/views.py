from django.db import connection, DatabaseError
from django.db.migrations.executor import MigrationExecutor
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from .api import error_body


class HealthView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({'status': 'ok'})


class ReadinessView(HealthView):
    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1 FROM accounts_user LIMIT 1')
            executor = MigrationExecutor(connection)
            if executor.migration_plan(executor.loader.graph.leaf_nodes()):
                return Response(error_body('not_ready', 'Service is not ready.', request.request_id), status=503)
            from django.conf import settings
            if settings.SETTINGS_MODULE in ('config.settings.demo', 'config.settings.render_demo') or getattr(settings, 'APP_ENV', None) == 'DEMO':
                from .demo import require_demo_environment
                require_demo_environment()
        except (DatabaseError, PermissionDenied):
            return Response(error_body('not_ready', 'Service is not ready.', request.request_id), status=503)
        return Response({'status': 'ready'})


class DemoStatusView(APIView):
    """Authenticated identity proof for release smoke tests; no secrets/DB DSN."""
    def get(self, request):
        from django.conf import settings
        from .demo import require_demo_environment
        from apps.inventory.authorization import require_actor
        require_demo_environment()
        require_actor(request.user, 'rehearsal.use_simulation')
        from apps.inventory.ledger_models import LedgerEntry, BalanceProjection
        from apps.inventory.quality_models import QualityAuthorization, QualityPosting
        empty = not any(model.objects.exists() for model in (LedgerEntry, BalanceProjection, QualityAuthorization, QualityPosting))
        return Response({'environment':'DEMO', 'instance':settings.DEMO_INSTANCE_ID,
            'operational_authority':False, 'operational_records_empty':empty})
