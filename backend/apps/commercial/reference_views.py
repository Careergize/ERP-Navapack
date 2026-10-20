from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.accounts.models import Employee
from apps.inventory.authorization import require_actor
from . import services
from .models import CommercialRevision


def marketing_people(actor):
    current = require_actor(actor, 'accounts.view_employee')
    rows = Employee.objects.filter(user__is_active=True).select_related('user')
    # Preserve the existing full-directory Master Admin boundary. Ordinary
    # employees can reference themselves, without exposing the HR directory.
    return rows if current.is_master_admin else rows.filter(user=current)


class CommercialReferenceViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='marketing-people')
    def marketing(self, request):
        services.authorize(request.user)
        page = self.paginate_queryset(marketing_people(request.user).order_by('employee_id', 'id'))
        return self.get_paginated_response([{'id': str(r.pk), 'version': r.version,
            'name': r.user.name or r.employee_id, 'employee_id': r.employee_id} for r in page])

    @action(detail=False, methods=['get'], url_path='costing-revisions')
    def costings(self, request):
        services.authorize(request.user)
        page = self.paginate_queryset(CommercialRevision.objects.filter(document__owner=request.user,
            document__kind='COSTING').order_by('-created_at', 'id'))
        return self.get_paginated_response([{'id': str(r.pk), 'number': r.number, 'document': str(r.document_id),
            'status': r.status, 'currency': r.snapshot['input']['currency'],
            'lines': [{k: l.get(k) for k in ('variant', 'unit', 'quantity', 'specifications', 'customisation',
                      'model_revision', 'variant_snapshot', 'unit_snapshot')} for l in r.snapshot['input']['lines']],
            'authority': False} for r in page])
