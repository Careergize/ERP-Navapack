from django.db import connection, DatabaseError
from django.db.migrations.executor import MigrationExecutor
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
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
        except DatabaseError:
            return Response(error_body('not_ready', 'Service is not ready.', request.request_id), status=503)
        return Response({'status': 'ready'})
