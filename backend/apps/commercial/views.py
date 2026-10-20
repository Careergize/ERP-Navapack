from rest_framework import viewsets, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import get_object_or_404
from apps.core.commands import expected_version
from apps.core.models import AuditEvent
from .contracts import Strict
from . import services


class CreateInput(Strict):
    kind = serializers.ChoiceField(choices=['COSTING', 'QUOTATION', 'SALES_ORDER'])
    data = serializers.DictField()
    reason = serializers.CharField(max_length=500)


class EditInput(Strict):
    data = serializers.DictField()
    reason = serializers.CharField(max_length=500)


class TransitionInput(Strict):
    transition = serializers.CharField(max_length=30)
    reason = serializers.CharField(max_length=500)


class DeriveInput(Strict):
    source_revision = serializers.UUIDField()
    reason = serializers.CharField(max_length=500)


class CommercialViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    lookup_value_regex = '[0-9a-fA-F-]{36}'

    def get_queryset(self):
        return services.scoped(self.request.user)

    def list(self, request):
        page = self.paginate_queryset(self.get_queryset())
        return self.get_paginated_response([services.representation(doc) for doc in page])

    def retrieve(self, request, pk=None):
        result = services.representation(self.get_object())
        return Response(result, headers={'ETag': f'"{result["version"]}"'})

    def run(self, serializer, **kwargs):
        services.authorize(self.request.user)
        serializer.is_valid(raise_exception=True)
        result, status, replay = services.command(actor=self.request.user,
            key=self.request.headers.get('Idempotency-Key'), request_id=self.request.request_id,
            **serializer.validated_data, **kwargs)
        return Response(result, status=status, headers={'ETag': f'"{result["version"]}"'})

    def create(self, request):
        return self.run(CreateInput(data=request.data))

    @action(detail=True, methods=['post'])
    def derive(self, request, pk=None):
        from .handoffs import derive
        doc = self.get_object()
        serializer = DeriveInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Pin the exact selected revision. Later source edits cannot rebind retries.
        source = get_object_or_404(doc.revisions, pk=serializer.validated_data['source_revision'])
        result, status, _ = derive(actor=request.user, source_id=source.pk,
            key=request.headers.get('Idempotency-Key'), request_id=request.request_id,
            reason=serializer.validated_data['reason'])
        return Response(result, status=status, headers={'ETag': f'"{result["version"]}"'})

    def partial_update(self, request, pk=None):
        self.get_object()
        return self.run(EditInput(data=request.data), pk=pk, version=expected_version(request.headers.get('If-Match')))

    @action(detail=True, methods=['post'])
    def transition(self, request, pk=None):
        self.get_object()
        return self.run(TransitionInput(data=request.data), pk=pk, version=expected_version(request.headers.get('If-Match')))

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        doc = self.get_object()
        rows = doc.revisions.all()
        page = self.paginate_queryset(rows)
        events = {e.source_version: {'id': str(e.pk), 'actor': str(e.actor_id), 'at': e.timestamp.isoformat(),
            'request_id': str(e.request_id), 'revision': e.summary.get('outcome', {}).get('revision') if isinstance(e.summary.get('outcome'), dict) else None}
            for e in AuditEvent.objects.filter(entity_type='commercial.commercialdocument', entity_id=str(doc.pk), source_version__in=[r.number for r in page])}
        return self.get_paginated_response([{'id': str(r.pk), 'number': r.number, 'actor': str(r.actor_id),
            'at': r.created_at.isoformat(), 'status': r.status, 'reason': r.reason,
            'sha256': r.sha256, 'snapshot': r.snapshot, 'audit': events.get(r.number)} for r in page])
