"""Explicit synthetic QC API; no Django Admin registration or posting command."""
import logging
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.serializers import UUIDField
from rest_framework.generics import get_object_or_404
from apps.core.commands import expected_version
from apps.core.models import AuditEvent
from apps.accounts.employee_views import AuditEventSerializer
from .authorization import require_actor, oversight, scopes
from .ledger_guard import require_synthetic_environment
from .quality import MODELS, snapshot, command
from .quality_models import PlanApproval, InspectionReview, QualityAuthorization, QualityPosting, QualityHold, NonconformanceAction


class QualityViewSet(viewsets.GenericViewSet):
    lookup_value_regex = '[0-9a-fA-F-]{36}'
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if self.action == 'mode': return
        require_synthetic_environment()
        require_actor(request.user, 'inventory.view_qc')

    def handle_exception(self, exc):
        if isinstance(exc, ObjectDoesNotExist): exc = ValidationError({'reference':'Unknown QC reference.'})
        if getattr(exc, 'status_code', None) in [401,403]:
            logging.getLogger('inventory.security').warning('QC authorization denied',extra={'actor_id':str(self.request.user.pk) if self.request.user.is_authenticated else None,'request_id':str(self.request.request_id),'action':'inventory.qc_'+self.action,'outcome':'denied'})
        return super().handle_exception(exc)

    def get_queryset(self):
        resource = self.kwargs.get('resource')
        if resource not in MODELS: raise ValidationError({'resource':'Unknown QC resource.'})
        qs = MODELS[resource].objects.order_by('-created_at','id')
        if resource == 'held-stock': qs = qs.filter(quality='HELD',quantity__gt=0)
        if resource != 'plans' and not oversight(self.request.user):
            field = 'inspection__location__warehouse_id' if resource == 'ncr' else 'location__warehouse_id'
            qs = qs.filter(**{field+'__in':scopes(self.request.user).values('warehouse_id')})
        if self.request.query_params.get('stock') and resource != 'plans':
            qs = qs.filter(**{('inspection__stock_id' if resource == 'ncr' else 'stock_id'):UUIDField().run_validation(self.request.query_params['stock'])})
        return qs

    @action(detail=False, methods=['get'])
    def mode(self, request):
        try: require_synthetic_environment(); enabled=True
        except PermissionDenied: enabled=False
        return Response({'synthetic_enabled':enabled,'operational_posting':False,
            'partial_pool_release':False,'disposition_available':False,
            'message':'Isolated synthetic QC only. Whole identified roots; indistinguishable partial quantities and rejected disposition remain unavailable.'})

    def list(self, request, resource=None):
        page = self.paginate_queryset(self.get_queryset())
        return self.get_paginated_response([snapshot(obj) for obj in page])

    def retrieve(self, request, resource=None, pk=None):
        result = snapshot(get_object_or_404(self.get_queryset(),pk=pk))
        response=Response(result); response['ETag']='"'+str(result['version'])+'"'; return response

    def create(self, request, resource=None):
        step={'plans':'plan','inspections':'inspect','holds':'hold','ncr':'ncr'}.get(resource)
        if not step: raise ValidationError('Unknown QC resource.')
        result,status,_=command(actor=request.user,action=step,data=request.data,key=request.headers.get('Idempotency-Key'),request_id=request.request_id)
        return Response(result,status=status)

    def transition(self, request, resource=None, pk=None, step=None):
        get_object_or_404(self.get_queryset(),pk=pk)
        if step not in {'plans':['publish'],'inspections':['review','release'],'ncr':['ncr_action'],'holds':[]}[resource]:
            raise ValidationError('Unsupported QC transition.')
        result,status,_=command(actor=request.user,action=step,data=request.data,pk=pk,
            version=expected_version(request.headers.get('If-Match')),key=request.headers.get('Idempotency-Key'),request_id=request.request_id)
        return Response(result,status=status)

    def history(self, request, resource=None, pk=None):
        obj=get_object_or_404(self.get_queryset(),pk=pk)
        require_actor(request.user,'inventory.view_qc_history')
        ids=[str(obj.pk)]
        if resource=='plans': ids += [str(v) for v in PlanApproval.objects.filter(plan=obj).values_list('id',flat=True)]
        if resource=='inspections':
            ids += [str(v) for v in InspectionReview.objects.filter(inspection=obj).values_list('id',flat=True)]
            ids += [str(v) for v in QualityAuthorization.objects.filter(review__inspection=obj).values_list('id',flat=True)]
            ids += [str(v) for v in QualityPosting.objects.filter(authorization__review__inspection=obj).values_list('transaction_id',flat=True)]
            ids += [str(v) for v in QualityHold.objects.filter(stock=obj.stock,location=obj.location).values_list('id',flat=True)]
        if resource=='ncr':
            ids += [str(obj.hold_id),str(obj.inspection_id)]
            ids += [str(v) for v in NonconformanceAction.objects.filter(ncr=obj).values_list('id',flat=True)]
        # QC reclassifications contain one custody only; never expose unrelated source ledgers.
        page=self.paginate_queryset(AuditEvent.objects.filter(entity_id__in=ids).order_by('-timestamp','id'))
        return self.get_paginated_response(AuditEventSerializer(page,many=True).data)
