from rest_framework import viewsets, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.core.commands import expected_version
from .contracts import Strict
from . import governance, services
from .models import GovernanceRecord
from .decision_catalog import DECISIONS, POLICY_TYPES
from apps.accounts.backends import explicit_permission_codes


class ProposalCommand(Strict):
    data = serializers.DictField()
    reason = serializers.CharField(max_length=500)


class GovernanceViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    lookup_value_regex = '[0-9a-fA-F-]{36}'
    kind = 'POLICY'

    def get_queryset(self):
        governance.authorize(self.request.user)
        return GovernanceRecord.objects.filter(owner=self.request.user, kind=self.kind)

    def list(self, request):
        page = self.paginate_queryset(self.get_queryset())
        return self.get_paginated_response([governance.representation(r) for r in page])

    def retrieve(self, request, pk=None):
        value = governance.representation(self.get_object())
        return Response(value, headers={'ETag': f'"{value["version"]}"'})

    def run(self, request, **kwargs):
        governance.authorize(request.user)
        s = ProposalCommand(data=request.data); s.is_valid(raise_exception=True)
        value, status, _ = governance.command(actor=request.user, kind=self.kind, **s.validated_data,
            key=request.headers.get('Idempotency-Key'), request_id=request.request_id, **kwargs)
        return Response(value, status=status, headers={'ETag': f'"{value["version"]}"'})

    def create(self, request): return self.run(request)

    def partial_update(self, request, pk=None):
        self.get_object()
        return self.run(request, pk=pk, version=expected_version(request.headers.get('If-Match')))

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        page = self.paginate_queryset(self.get_object().revisions.all())
        return self.get_paginated_response([{'id': str(r.pk), 'number': r.number, 'author': str(r.author_id),
            'created_at': r.created_at.isoformat(), 'reason': r.reason, 'status': r.status, 'content': r.content,
            'sha256': r.sha256, 'review_performed': False, 'authority': False} for r in page])


class DecisionSubmissionViewSet(GovernanceViewSet):
    kind = 'DECISION'


class DecisionRegistryViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        services.authorize(request.user)
        own = {r.key: governance.representation(r) for r in GovernanceRecord.objects.filter(owner=request.user, kind='DECISION')} if governance.CAPABILITY in explicit_permission_codes(request.user) else {}
        return Response({'catalog_version': 'phase4b-v1', 'policy_types': POLICY_TYPES, 'authority': False,
            'results': [{'decision_id': code, 'baseline_status': entry.get('baseline_status', 'OPEN'),
                'status': 'PENDING_VERIFICATION' if code in own else entry.get('baseline_status', 'OPEN'),
                'latest_submission': own.get(code), 'review_history_count': own[code]['version'] if code in own else 0,
                'review_performed': False,
                'conflicting_evidence': [], **entry, 'source': 'docs/phase4-planning/PHASE_4_CLIENT_DECISIONS.md',
                'answer_effect': 'PENDING_VERIFICATION only; independent verification unavailable'} for code, entry in DECISIONS.items()]})
