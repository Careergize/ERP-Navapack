import json
from django.db import IntegrityError, connection
from rest_framework.generics import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, viewsets, serializers
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from apps.accounts.permissions import ActionPermission
from apps.core.commands import execute_command, expected_version, lock_versioned, advance_version
from apps.core.api import CommandConflict
from .serializers import serializer_for
from .models import Customer, Prospect


def json_safe(value):
    return json.loads(JSONRenderer().render(value))


def require_capability(actor, capability):
    if not actor.is_authenticated or not actor.is_active or not actor.has_perm(capability):
        raise PermissionDenied()


def audit(obj, fields=()):
    return {'entity_type': obj._meta.label_lower, 'entity_id': obj.pk,
            'source_version': obj.version, 'summary': {'changed_fields': sorted(fields), 'outcome': 'success'}}


def run_command(view, payload, operation, capability=None):
    permission = capability or view.action_permissions[view.action]
    def authorize():
        # Shared catalog lock prevents candidate phantoms between review validation
        # and application. All HTTP catalog/specification writes use this gate.
        with connection.cursor() as cursor:
            cursor.execute('SELECT pg_advisory_xact_lock(%s)', [70462027])
        require_capability(view.request.user, permission)
    try:
        result, status, _ = execute_command(actor=view.request.user, scope='global-masters',
            action=permission, key=view.request.headers.get('Idempotency-Key'), payload=json_safe(payload),
            request_id=view.request.request_id, authorize=authorize, operation=operation)
    except IntegrityError:
        raise ValidationError({'identity': 'A unique identity or constraint conflicts with existing data.'})
    response = Response(result, status=status)
    if status == 201 and view.action == 'create':
        response['Location'] = view.request.path + str(result['id']) + '/'
    if 'version' in result:
        response['ETag'] = f'"{result["version"]}"'
    return response


class MasterViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [ActionPermission]
    search_fields = ['name','code','source_id']
    ordering_fields = ['name','code','created_at','updated_at']
    ordering = ['-created_at','id']
    filterset_fields = ['is_active','source_system']

    @staticmethod
    def object_scope(actor, obj):
        # Explicit single shared master catalog. No inferred department/tenant policy.
        return actor.is_active and actor.has_perm(f'{obj._meta.app_label}.view_{obj._meta.model_name}')

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        response['ETag'] = f'"{response.data["version"]}"'
        return response

    def create(self, request):
        def operation():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            obj = serializer.save(created_by=request.user, updated_by=request.user)
            return json_safe(self.get_serializer(obj).data), 201, audit(obj, serializer.validated_data)
        return run_command(self, {'resource': self.queryset.model._meta.label_lower, 'data': request.data}, operation)

    def partial_update(self, request, pk=None):
        version = expected_version(request.headers.get('If-Match'))
        def operation():
            # Global shared scope, explicit write capability; do not require read grant to write.
            get_object_or_404(self.queryset, pk=pk)
            obj = lock_versioned(self.queryset.model, pk, version)
            serializer = self.get_serializer(obj, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save(updated_by=request.user)
            advance_version(obj, update_fields=['updated_by'])
            return json_safe(self.get_serializer(obj).data), 200, audit(obj, serializer.validated_data)
        return run_command(self, {'id': pk, 'version': version, 'data': request.data}, operation)


class PromotionSerializer(serializers.Serializer):
    existing_customer_id = serializers.UUIDField(required=False)
    create_customer = serializers.BooleanField(default=False)
    def validate(self, attrs):
        if set(self.initial_data) - set(self.fields):
            raise ValidationError('Unknown promotion fields.')
        if bool(attrs.get('existing_customer_id')) == attrs['create_customer']:
            raise ValidationError('Select an existing_customer_id OR create_customer=true.')
        return attrs


class ProspectViewSet(MasterViewSet):
    @action(detail=True, methods=['post'])
    def promote(self, request, pk=None):
        version = expected_version(request.headers.get('If-Match'))
        def operation():
            get_object_or_404(Prospect, pk=pk)
            prospect = lock_versioned(Prospect, pk, version)
            s = PromotionSerializer(data=request.data); s.is_valid(raise_exception=True)
            data = s.validated_data
            if not prospect.is_active:
                raise ValidationError('Inactive prospect cannot be promoted.')
            if prospect.linked_customer_id:
                raise CommandConflict('Prospect already promoted; use original retry key or read linkage.')
            if data.get('existing_customer_id'):
                require_capability(request.user, 'masters.view_customer')
                customer = get_object_or_404(Customer.objects.select_for_update(), pk=data['existing_customer_id'], is_active=True)
            else:
                require_capability(request.user, 'masters.add_customer')
                fields = ['name','contact_person','phone','email','address','delivery_address','tin','customer_type']
                customer = Customer.objects.create(**{f: getattr(prospect,f) for f in fields}, created_by=request.user, updated_by=request.user)
                from apps.core.audit import record_event
                record_event(actor=request.user, action='masters.add_customer', request_id=request.request_id, **audit(customer, fields))
            prospect.linked_customer = customer
            prospect.promoted_by = request.user; prospect.promoted_at = timezone.now(); prospect.updated_by = request.user
            advance_version(prospect, update_fields=['linked_customer','promoted_by','promoted_at','updated_by'])
            return json_safe(self.get_serializer(prospect).data), 200, audit(prospect, ['linked_customer'])
        # Additional grants rechecked on replay as well.
        s = PromotionSerializer(data=request.data); s.is_valid(raise_exception=True)
        require_capability(request.user, 'masters.add_customer' if s.validated_data['create_customer'] else 'masters.view_customer')
        return run_command(self, {'id':pk,'version':version,'data':request.data}, operation)


def master_view(model, base=MasterViewSet):
    label = model._meta.model_name
    app = model._meta.app_label
    perms = {a: f'{app}.{verb}_{label}' for a,verb in [('list','view'),('retrieve','view'),('create','add'),('partial_update','change')]}
    if model is Prospect: perms['promote'] = 'masters.promote_prospect'
    filters = ['is_active','source_system'] + [f for f in ['category','unit','product','department','area','family','linked_customer'] if any(x.name == f for x in model._meta.fields)]
    return type(model.__name__+'ViewSet', (base,), {'queryset':model.objects.all(), 'serializer_class':serializer_for(model), 'action_permissions':perms, 'filterset_fields':filters})
