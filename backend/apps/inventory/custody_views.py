"""Synthetic-only custody observations, never registration provenance or posting."""
import logging
from datetime import datetime, timezone as datetime_timezone
from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.generics import get_object_or_404
from .authorization import require_actor, require_scope, oversight, scopes
from .ledger_guard import require_synthetic_environment, posting_locks
from .ledger_models import BalanceProjection, LedgerEntry, OpeningCoverage
from .quality_models import QualityHold
from .models import StockIdentity, StorageLocation
from .ledger import key_for, owner_key


class CustodyViewSet(viewsets.GenericViewSet):
    """Each amount belongs to one exact item/unit/location/quality; no summed totals."""
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        require_synthetic_environment()
        require_actor(request.user, 'inventory.view_synthetic_custody')

    def handle_exception(self, exc):
        if getattr(exc, 'status_code', None) in [401,403]:
            logging.getLogger('inventory.security').warning('Custody read denied', extra={
                'actor_id':str(self.request.user.pk) if self.request.user.is_authenticated else None,
                'request_id':str(self.request.request_id),'action':'inventory.read_custody','outcome':'denied'})
        return super().handle_exception(exc)

    def filtered(self, model):
        qs = model.objects.select_related('stock','stock__unit','location__warehouse').all()
        if not oversight(self.request.user):
            qs = qs.filter(location__warehouse_id__in=scopes(self.request.user).values('warehouse_id'))
        for param, field in [('warehouse','location__warehouse_id'),('location','location_id'),('stock','stock_id')]:
            if param in self.request.query_params:
                qs = qs.filter(**{field:serializers.UUIDField().run_validation(self.request.query_params[param])})
        item = self.request.query_params.get('item_type')
        if item:
            if item not in ['material','variant','consumable']:
                raise serializers.ValidationError({'item_type':'Choose material, variant or consumable.'})
            qs = qs.filter(**{'stock__'+item+'__isnull':False})
        return qs

    @staticmethod
    def identity(row):
        # Registration warehouse/source/supplier/owner evidence remains separately authorized.
        return {'stock':str(row.stock_id),'reference':row.stock.reference,'unit':str(row.unit_id),
                'warehouse':str(row.location.warehouse_id),'location':str(row.location_id)}

    @action(detail=False,methods=['get'])
    def balances(self, request):
        page = self.paginate_queryset(self.filtered(BalanceProjection).order_by('stock_id','location_id','quality','id'))
        return self.get_paginated_response([{**self.identity(row),'id':str(row.pk),'version':row.version,
            'quality':row.quality,'quantity':str(row.quantity),'ownership':row.stock.ownership,
            'explicit_containment':QualityHold.objects.filter(stock=row.stock).exists(),
            'availability_not_asserted':True,'operational_posting':False} for row in page])

    @action(detail=False,methods=['get'])
    def movements(self, request):
        rows = self.filtered(LedgerEntry).select_related('transaction')
        month = request.query_params.get('month')
        if month:
            try:
                start = datetime.strptime(month, '%Y-%m').replace(tzinfo=datetime_timezone.utc)
                if start.strftime('%Y-%m') != month or start.year >= 9999:
                    raise ValueError()
                end = start.replace(year=start.year+1, month=1) if start.month == 12 else start.replace(month=start.month+1)
            except ValueError:
                raise serializers.ValidationError({'month':'Use a valid YYYY-MM month before year 9999.'})
            rows = rows.filter(event_at__gte=start,event_at__lt=end)
        page = self.paginate_queryset(rows.order_by('-event_at','transaction_id','sequence'))
        return self.get_paginated_response([{**self.identity(row),'id':str(row.pk),'transaction':str(row.transaction_id),
            'kind':row.transaction.kind,'quality':row.quality,'delta':str(row.delta),'event_at':row.event_at.isoformat(),
            'operational_posting':False} for row in page])

    @action(detail=False,methods=['get'])
    def scope(self, request):
        stock_id = serializers.UUIDField().run_validation(request.query_params.get('stock'))
        location_id = serializers.UUIDField().run_validation(request.query_params.get('location'))
        with transaction.atomic():
            posting_locks()
            location = get_object_or_404(StorageLocation.objects.select_related('warehouse'),pk=location_id)
            require_scope(request.user,location.warehouse_id)
            stock = get_object_or_404(StockIdentity.objects.select_for_update(),pk=stock_id)
            local_history = LedgerEntry.objects.filter(stock=stock,location__warehouse=location.warehouse).exists()
            if not local_history and stock.warehouse_id != location.warehouse_id:
                # Knowing an arbitrary foreign lot UUID must not expose its registration.
                from rest_framework.exceptions import NotFound
                raise NotFound()
            owner = None if stock.ownership == 'UNRESOLVED' else owner_key(stock)
            coverage = OpeningCoverage.objects.filter(stock=stock,location=location,unit=stock.unit,owner_key=owner,status='KNOWN').first() if owner else None
            partitions = {}
            for quality in ['HELD','RELEASED']:
                row = BalanceProjection.objects.filter(stock=stock,location=location,unit=stock.unit,quality=quality).first() if coverage else None
                partitions[quality] = {'quantity':str(row.quantity) if row else '0' if coverage else None,
                                       'version':row.version if row else 0 if coverage else None}
            return Response({'stock':str(stock.pk),'reference':stock.reference,'unit':str(stock.unit_id),
                'location':str(location.pk),'warehouse':str(location.warehouse_id),
                'opening_status':'KNOWN' if coverage else 'UNKNOWN','partitions':partitions,
                'explicit_containment':QualityHold.objects.filter(stock=stock).exists(),
                'observed_at':timezone.now().isoformat(),'availability_not_asserted':True,'operational_posting':False})
