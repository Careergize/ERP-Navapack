from django.db.models import Count
from decimal import Decimal, localcontext
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.commercial.contracts import Strict
from apps.core.commands import expected_version
from . import services


class RouteInput(Strict):
    line = serializers.IntegerField(min_value=0)
    stages = serializers.ListField(child=serializers.ChoiceField(choices=services.STAGES), min_length=1, max_length=5)


class CreateInput(Strict):
    sales_order_revision = serializers.UUIDField(required=False)
    costing_revision = serializers.UUIDField(required=False)
    warehouse = serializers.UUIDField()
    routes = RouteInput(many=True)
    reason = serializers.CharField(max_length=500)

    def validate(self, attrs):
        if bool(attrs.get('sales_order_revision')) == bool(attrs.get('costing_revision')):
            raise serializers.ValidationError('Provide exactly one sales-order or production-for-stock costing revision.')
        return attrs


class CommandInput(Strict):
    action = serializers.ChoiceField(choices=['review', 'issue', 'start', 'complete', 'qc', 'finish', 'dispatch', 'recycle'])
    data = serializers.DictField(default=dict)
    reason = serializers.CharField(max_length=500)


class RehearsalViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    lookup_value_regex = '[0-9a-fA-F-]{36}'

    def get_queryset(self):
        return services.scoped(self.request.user)

    def list(self, request):
        page = self.paginate_queryset(self.get_queryset())
        return self.get_paginated_response([services.representation(j) for j in page])

    def retrieve(self, request, pk=None):
        result = services.representation(self.get_object())
        return Response(result, headers={'ETag': f'"{result["version"]}"'})

    def create(self, request):
        services.authorize(request.user)
        serializer = CreateInput(data=request.data); serializer.is_valid(raise_exception=True)
        values = dict(serializer.validated_data); reason = values.pop('reason')
        for name in ('sales_order_revision', 'costing_revision', 'warehouse'):
            if name in values: values[name] = str(values[name])
        return self.run(data=values, reason=reason)

    def run(self, **kwargs):
        result, status, replay = services.command(actor=self.request.user,
            key=self.request.headers.get('Idempotency-Key'), request_id=self.request.request_id, **kwargs)
        return Response(result, status=status, headers={'ETag': f'"{result["version"]}"'})

    @action(detail=True, methods=['post'], url_path='command')
    def execute(self, request, pk=None):
        self.get_object()
        serializer = CommandInput(data=request.data); serializer.is_valid(raise_exception=True)
        return self.run(pk=pk, version=expected_version(request.headers.get('If-Match')), **serializer.validated_data)

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        page = self.paginate_queryset(self.get_object().revisions.all())
        return self.get_paginated_response([{'id': str(r.pk), 'number': r.number, 'action': r.action,
            'actor': str(r.actor_id), 'at': r.created_at.isoformat(), 'reason': r.reason,
            'snapshot': r.snapshot, 'sha256': r.sha256} for r in page])

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        rows = self.get_queryset()
        from apps.commercial.models import CommercialDocument
        commercial = CommercialDocument.objects.filter(owner=request.user)
        from apps.accounts.backends import explicit_permission_codes
        from apps.masters.models import Customer, Prospect, Product, ProductVariant, Material, Consumable
        permissions = explicit_permission_codes(request.user)
        if 'commercial.use_foundation' not in permissions:
            commercial = commercial.none()
        parties = {name: model.objects.count() if f'masters.view_{name}' in permissions else None
                   for name, model in [('customer', Customer), ('prospect', Prospect)]}
        catalog = {name: model.objects.count() if f'masters.view_{name}' in permissions else None
                   for name, model in [('product', Product), ('productvariant', ProductVariant), ('material', Material), ('consumable', Consumable)]}
        summaries = {}
        if 'commercial.use_foundation' in permissions:
            for document in commercial.exclude(status='CANCELLED'):
                snapshot = document.revisions.get(number=document.version).snapshot
                values = snapshot['input']
                party = values.get('customer') or values.get('prospect') or 'unassigned'
                currency = values['currency']
                group = summaries.setdefault((party, currency, document.kind), {'party': str(party), 'currency': currency, 'kind': document.kind, 'documents': 0, 'net_estimate': Decimal(0), 'estimated_production_cost': Decimal(0)})
                group['documents'] += 1
                with localcontext() as context:
                    context.prec = 60
                    group['net_estimate'] += Decimal(snapshot['estimate']['net_estimate'])
                    costs = [line.get('costing', {}).get('estimated_production_cost') if line.get('costing') else None for line in snapshot['estimate']['lines']]
                    if group['estimated_production_cost'] is None or any(cost is None for cost in costs):
                        group['estimated_production_cost'] = None
                    else:
                        group['estimated_production_cost'] += sum((Decimal(cost) for cost in costs), Decimal(0))
        financial = []
        for value in summaries.values():
            cost = value['estimated_production_cost']
            with localcontext() as context:
                context.prec = 60
                margin = value['net_estimate'] - cost if cost is not None else None
            financial.append({**value, 'net_estimate': format(value['net_estimate'], 'f'),
                'estimated_production_cost': format(cost, 'f') if cost is not None else None,
                'estimated_margin': format(margin, 'f') if margin is not None else None, 'authoritative': False})
        estimates = {}
        for document in commercial.filter(kind='COSTING').exclude(status='CANCELLED'):
            snapshot = document.revisions.get(number=document.version).snapshot
            currency = snapshot['input']['currency']
            total = estimates.setdefault(currency, Decimal(0))
            with localcontext() as context:
                context.prec = 60
                estimates[currency] = total + sum((Decimal(line['costing']['estimated_production_cost'])
                    for line in snapshot['estimate']['lines'] if line.get('costing')), Decimal(0))
        stage_counts = {'PENDING': 0, 'STARTED': 0, 'COMPLETE': 0}
        units = {}
        recycling = {}
        for job in rows:
            for event in job.snapshot.get('recycling', []):
                group = recycling.setdefault(event['unit'], {'unit':event['unit'],'batches':0,'intake':Decimal(0),'recovered':Decimal(0),'rejected':Decimal(0),'disposed':Decimal(0)})
                group['batches'] += 1
                with localcontext() as context:
                    context.prec = 60
                    for key in ('intake','recovered','rejected','disposed'): group[key] += Decimal(event[key])
            for route in job.snapshot['routes']:
                line = job.snapshot['source']['input']['lines'][route['line']]
                unit = str(line['unit'])
                target = units.setdefault(unit, {'unit': unit, 'code': line['unit_snapshot']['code'],
                    'output_quantity': Decimal(0), 'waste': Decimal(0), 'rejection': Decimal(0)})
                for stage in route['stages']:
                    stage_counts[stage['status']] += 1
                    if stage['status'] == 'COMPLETE':
                        target['waste'] += Decimal(stage['waste'])
                        target['rejection'] += Decimal(stage['rejection'])
                if route['stages'][-1]['status'] == 'COMPLETE':
                    target['output_quantity'] += Decimal(route['stages'][-1]['output_quantity'])
        production = [{key: format(value, 'f') if isinstance(value, Decimal) else value
            for key, value in target.items()} for target in units.values()]
        notifications = [{'id':str(job.pk),'status':job.status,'kind':'SYNTHETIC_PRODUCTION',
            'href':'/job-cards/'+str(job.pk),'message':f'Synthetic Job Card {job.status.lower().replace("_", " ")}'}
            for job in rows.filter(status__in=['DRAFT','QC_FAILED','FINISHED']).order_by('-updated_at','id')[:20]]
        return Response({'simulation': True, 'operational_posting': False, 'jobs': rows.count(),
            'statuses': {r['status']: r['total'] for r in rows.values('status').annotate(total=Count('id'))},
            'stages': stage_counts, 'production_by_unit': production,
            'parties': parties, 'catalog': catalog, 'commercial_by_party': financial, 'notifications': notifications,
            'recycling_by_unit': [{key:format(value,'f') if isinstance(value,Decimal) else value for key,value in group.items()} for group in recycling.values()],
            'estimated_cost_by_currency': {k: format(v, 'f') for k, v in estimates.items()},
            'financial_payable': None, 'operational_available_stock': None,
            'commercial': {'counts': {r['kind']: r['total'] for r in commercial.values('kind').annotate(total=Count('id'))},
                'statuses': {r['status']: r['total'] for r in commercial.values('status').annotate(total=Count('id'))}}})
