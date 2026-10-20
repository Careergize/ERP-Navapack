from decimal import Decimal
from django.db.models import Max
from rest_framework.generics import get_object_or_404
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.masters.serializers import StrictSerializer, serializer_for
from apps.masters.views import MasterViewSet, run_command, json_safe, audit
from apps.core.commands import expected_version, lock_versioned, advance_version
from .models import ProductModel, ProductModelRevision, RecipeLine, ProcessCostLine, ModelRouteStage


def line_serializer(model):
    class Meta:
        fields = '__all__'
        read_only_fields = ['id','version','created_at','updated_at','revision']
        validators = []
    Meta.model = model
    return type(model.__name__+'Serializer',(StrictSerializer,),{'Meta':Meta})


RecipeSerializer = line_serializer(RecipeLine)
RouteSerializer = line_serializer(ModelRouteStage)
class ProcessSerializer(StrictSerializer):
    # Null is a supported legacy spelling for an unlinked cost. Non-null UUIDs
    # cannot reference stages belonging to another (historical) revision.
    stage = serializers.PrimaryKeyRelatedField(queryset=ModelRouteStage.objects.all(), required=False, allow_null=True)
    source_stage_id = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = ProcessCostLine
        fields = ['id','version','created_at','updated_at','revision','source_id',
                  'name','basis','rate','quantity','unit','remarks','stage','source_stage_id']
        read_only_fields = ['id','version','created_at','updated_at','revision']
        validators = []

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if attrs.pop('stage', None) is not None:
            raise serializers.ValidationError({'stage':'Use source_stage_id within the new revision.'})
        return attrs



class RevisionSerializer(StrictSerializer):
    recipe = RecipeSerializer(many=True, required=False)
    routing = RouteSerializer(many=True, required=False)
    processes = ProcessSerializer(many=True, required=False)
    class Meta:
        model = ProductModelRevision
        fields = '__all__'
        read_only_fields = ['id','version','created_at','updated_at','model','number','created_by','sealed','reference_snapshot']
        # revision number is server-assigned under parent lock.
        validators = []

    def validate(self, attrs):
        attrs = super().validate(attrs)
        for key in ['batch_quantity','waste_percent','overheads','markup_percent','tax_percent']:
            value = attrs.get(key)
            if value is not None and (value < 0 or key in ['waste_percent','tax_percent'] and value > 100):
                raise serializers.ValidationError({key: 'Invalid nonnegative value or percentage.'})
        recipe, routing, processes = (attrs.get(k,[]) for k in ['recipe','routing','processes'])
        if len({x['material'].pk for x in recipe}) != len(recipe):
            raise serializers.ValidationError({'recipe':'Duplicate materials.'})
        for line in recipe:
            if line['unit'].pk != line['material'].unit_id:
                raise serializers.ValidationError({'recipe':'Use exact material unit; no implicit conversion.'})
            for key in ['quantity','price','percentage','exchange_rate']:
                if line.get(key) is not None and (line[key] < 0 or key == 'exchange_rate' and line[key] == 0):
                    raise serializers.ValidationError({'recipe':'Invalid quantity, price, percentage or exchange rate.'})
        if attrs['recipe_mode'] == 'percentages':
            if not recipe or sum((l.get('percentage') or Decimal(0) for l in recipe),Decimal(0)) != Decimal(100) or any((l.get('percentage') or 0) <= 0 for l in recipe):
                raise serializers.ValidationError({'recipe':'Positive percentages must total 100.'})
            if not attrs.get('batch_quantity') or not attrs.get('batch_unit'):
                raise serializers.ValidationError({'batch_quantity':'Percentage recipes require batch quantity and unit.'})
            if any(l['unit'].pk != attrs['batch_unit'].pk for l in recipe):
                raise serializers.ValidationError({'recipe':'Batch and recipe units must match; conversions require future explicit configuration.'})
        elif any(not l.get('quantity') or l['quantity'] <= 0 for l in recipe):
            raise serializers.ValidationError({'recipe':'Quantity recipes require positive quantities.'})
        if len({l['sequence'] for l in routing}) != len(routing) or any(l['sequence'] < 1 for l in routing):
            raise serializers.ValidationError({'routing':'Unique positive sequences required.'})
        ids = [l.get('source_id') for l in routing if l.get('source_id')]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError({'routing':'Duplicate source stage identity.'})
        for line in routing:
            if line.get('machine') and line['machine'].department_id != line['department'].pk:
                raise serializers.ValidationError({'routing':'Machine department mismatch.'})
            for key in ['expected_input','expected_output','planned_waste_percent']:
                if line.get(key) is not None and (line[key] < 0 or key == 'planned_waste_percent' and line[key] > 100):
                    raise serializers.ValidationError({'routing':'Invalid planned quantity or waste percentage.'})
        # Nested process stage references use source_stage_id, resolved after stage creation.
        for line in processes:
            if line.get('stage'):
                raise serializers.ValidationError({'processes':'Use source_stage_id to reference this new revision route.'})
            if any(line.get(k) is not None and line[k] < 0 for k in ['rate','quantity']):
                raise serializers.ValidationError({'processes':'Nonnegative rates and quantities required.'})
        return attrs




class ProductModelViewSet(MasterViewSet):
    @action(detail=True, methods=['get','post'])
    def revisions(self, request, pk=None):
        if request.method == 'GET':
            get_object_or_404(ProductModel, pk=pk)
            rows = ProductModelRevision.objects.filter(model_id=pk, sealed=True).order_by('-number','id')
            page = self.paginate_queryset(rows)
            return self.get_paginated_response(RevisionSerializer(page, many=True).data)
        version = expected_version(request.headers.get('If-Match'))
        def operation():
            get_object_or_404(ProductModel, pk=pk)
            model = lock_versioned(ProductModel, pk, version)
            if not model.is_active:
                raise serializers.ValidationError('Cannot revise inactive model.')
            serializer = RevisionSerializer(data=request.data); serializer.is_valid(raise_exception=True)
            data = serializer.validated_data
            recipe, routing, processes = (data.pop(k,[]) for k in ['recipe','routing','processes'])
            number = (model.revisions.aggregate(n=Max('number'))['n'] or 0) + 1
            # Freeze reference labels/units as evidence alongside stable protected FKs.
            snapshot = {}
            for group, lines in [('revision',[data]),('recipe',recipe),('routing',routing),('processes',processes)]:
                snapshot[group] = [{k: {'id':str(v.pk),'name':getattr(v,'name',''),'code':getattr(v,'code','')} for k,v in line.items() if hasattr(v,'_meta')} for line in lines]
            revision = ProductModelRevision.objects.create(model=model, number=number, created_by=request.user, reference_snapshot=snapshot, **data)
            for line in recipe: RecipeLine.objects.create(revision=revision, **line)
            routes = {}
            for line in routing:
                stage = ModelRouteStage.objects.create(revision=revision, **line)
                if stage.source_id: routes[stage.source_id] = stage
            for line in processes:
                source = line.pop('source_stage_id','')
                if source and source not in routes:
                    raise serializers.ValidationError({'processes':'Unknown source_stage_id in this revision.'})
                ProcessCostLine.objects.create(revision=revision, stage=routes.get(source), **line)
            revision.sealed = True; revision.save(update_fields=['sealed'])
            model.updated_by = request.user
            advance_version(model, update_fields=['updated_by'])
            result = json_safe(RevisionSerializer(revision).data)
            result['model_version'] = model.version
            return result, 201, audit(revision,['revision'])
        return run_command(self, {'model':pk,'version':version,'data':request.data}, operation)

    def get_permissions(self):
        if self.action == 'revisions':
            self.action_permissions = {**self.action_permissions, 'revisions': 'specifications.view_productmodelrevision' if self.request.method == 'GET' else 'specifications.add_productmodelrevision'}
        return super().get_permissions()


class RevisionViewSet(MasterViewSet):
    http_method_names = ['get','head','options']
    queryset = ProductModelRevision.objects.filter(sealed=True)
    serializer_class = RevisionSerializer
    action_permissions = {'list':'specifications.view_productmodelrevision','retrieve':'specifications.view_productmodelrevision'}
    filterset_fields = ['model','number']
    search_fields = ['name','description','specifications']
    ordering_fields = ['created_at','number']
