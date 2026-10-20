"""All data/action endpoints are isolated-test-only; status is safe outside it."""
import logging
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from apps.core.commands import expected_version
from apps.core.models import AuditEvent
from apps.accounts.employee_views import AuditEventSerializer
from .workflow_models import OperationRequest
from .workflows import submit_request, transition_request, snapshot
from .authorization import require_actor, oversight, scopes
from .ledger_guard import require_synthetic_environment

class OperationViewSet(viewsets.GenericViewSet):
    lookup_value_regex='[0-9a-fA-F-]{36}'
    queryset=OperationRequest.objects.none()
    filterset_fields=['kind','status','warehouse','related','count_session']
    search_fields=['source_reference','source_event']
    ordering=['-created_at','id']
    ordering_fields=['created_at','status']
    def initial(self,request,*args,**kwargs):
        super().initial(request,*args,**kwargs)
        if self.action=='mode':return
        require_synthetic_environment()
        require_actor(request.user,'inventory.view_operationrequest')
    def handle_exception(self,exc):
        if isinstance(exc,ObjectDoesNotExist):exc=ValidationError({'reference':'Unknown or incompatible workflow reference.'})
        if getattr(exc,'status_code',None) in [401,403]:
            actor=self.request.user
            logging.getLogger('inventory.security').warning('Inventory workflow authorization denied',extra={'actor_id':str(actor.pk) if actor.is_authenticated else None,'request_id':str(self.request.request_id),'action':'inventory.'+self.action,'outcome':'denied'})
        return super().handle_exception(exc)
    def get_queryset(self):
        qs=OperationRequest.objects.all()
        if oversight(self.request.user):return qs
        ids=scopes(self.request.user).filter(company_wide=False).values('warehouse_id')
        return qs.filter(warehouse_id__in=ids).filter(Q(destination_warehouse__isnull=True)|Q(destination_warehouse_id__in=ids))
    @action(detail=False,methods=['get'])
    def mode(self,request):
        try:require_synthetic_environment();enabled=True
        except PermissionDenied:enabled=False
        return Response({'synthetic_enabled':enabled,'operational_posting':False,'authority':'SYNTHETIC_POLICY_ONLY' if enabled else 'PENDING_CONFIGURATION','message':'Isolated synthetic workflows only. QC release and operational stock posting are unavailable.'})
    def list(self,request):
        page=self.paginate_queryset(self.filter_queryset(self.get_queryset()))
        return self.get_paginated_response([snapshot(obj) for obj in page])
    def retrieve(self,request,pk=None):
        result=snapshot(get_object_or_404(self.get_queryset(),pk=pk))
        response=Response(result);response['ETag']='"'+str(result['version'])+'"';return response
    def create(self,request):
        result,status,_=submit_request(actor=request.user,data=request.data,key=request.headers.get('Idempotency-Key'),request_id=request.request_id)
        response=Response(result,status=status);response['ETag']='"'+str(result['version'])+'"';return response
    @action(detail=True,methods=['post'],url_path='(?P<step>verify|investigate|confirm|approve|reject|record)')
    def transition(self,request,pk=None,step=None):
        get_object_or_404(self.get_queryset(),pk=pk)
        result,status,_=transition_request(actor=request.user,pk=pk,action=step,data=request.data,version=expected_version(request.headers.get('If-Match')),key=request.headers.get('Idempotency-Key'),request_id=request.request_id)
        response=Response(result,status=status);response['ETag']='"'+str(result['version'])+'"';return response
    @action(detail=True,methods=['get'])
    def history(self,request,pk=None):
        get_object_or_404(self.get_queryset(),pk=pk)
        require_actor(request.user,'inventory.view_operation_history')
        page=self.paginate_queryset(AuditEvent.objects.filter(entity_type='inventory.operationrequest',entity_id=str(pk)).order_by('-timestamp','id'))
        return self.get_paginated_response(AuditEventSerializer(page,many=True).data)
