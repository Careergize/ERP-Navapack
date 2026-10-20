import hashlib
import uuid
from decimal import Decimal
from datetime import date, datetime
from pathlib import PurePath
from django.db import models
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.generics import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from apps.accounts.permissions import ActionPermission
from apps.core.commands import expected_version, lock_versioned, advance_version, payload_hash
from apps.core.api import CommandConflict, StaleReview
from apps.core.audit import record_event
from apps.masters.views import run_command, json_safe, audit, require_capability
from apps.masters.serializers import RESOURCES, serializer_for
from .models import ImportBatch, ImportRow, ImportReview
from .readers import read_source, MAX_BYTES


class ImportRowSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportRow
        fields = ['id','sheet','row_number','raw','result_id']


class BatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportBatch
        fields = '__all__'
        read_only_fields = []


def preview(batch, mapping, decisions, actor):
    target = RESOURCES[batch.target]
    if not isinstance(mapping,dict) or not all(isinstance(k,str) and isinstance(v,str) for k,v in mapping.items()):
        raise ValidationError({'mapping':'Map API field names to source column headers.'})
    if not isinstance(decisions,dict): raise ValidationError({'decisions':'Expected row UUID to explicit decision mapping.'})
    rows = list(batch.rows.order_by('sheet','row_number'))
    if set(decisions) - {str(r.pk) for r in rows}: raise ValidationError({'decisions':'Unknown row UUID.'})
    serializer_class = serializer_for(target)
    sample = serializer_class()
    writable = {k for k,f in sample.fields.items() if not f.read_only} - {'source_system'}
    if set(mapping) - writable or 'source_id' not in mapping:
        raise ValidationError({'mapping':'Only writable API fields allowed; source_id mapping required.'})
    results=[]; seen={}; seen_codes={}; seen_names={}
    for row in rows:
        decision = decisions.get(str(row.pk),{})
        if not isinstance(decision,dict) or set(decision)-{'action','target_id','expected_version','acknowledge_duplicates'}:
            raise ValidationError({'decisions':'Unknown decision fields.'})
        item={'row_id':str(row.pk),'sheet':row.sheet,'row_number':row.row_number,'decision':decision,'proposed':{},'errors':{},'candidates':[]}
        results.append(item)
        if decision.get('action') == 'skip': continue
        if decision.get('action') not in ['create','update']:
            item['errors']['decision']='Choose create, update or skip.'
        missing = [v for v in mapping.values() if v not in row.raw]
        if missing:
            item['errors']['columns']=missing; continue
        data = {k:row.raw[v] for k,v in mapping.items()}
        data['source_system']=batch.source_system
        # Nullable cells remain null, never zero. Source observations not mapped
        # to a master remain in immutable raw evidence, including opening balances.
        for k,v in list(data.items()):
            if v == '' and sample.fields[k].allow_null: data[k]=None
            field = target._meta.get_field(k)
            if isinstance(field,models.ForeignKey) and v:
                related = field.remote_field.model
                try:
                    ref = related.objects.select_for_update().filter(pk=uuid.UUID(str(v))).first()
                except (ValueError, TypeError, DjangoValidationError):
                    ref = None
                if ref is None and any(f.name == 'code' for f in related._meta.fields):
                    ref = related.objects.select_for_update().filter(code__iexact=str(v)).first()
                if ref is not None:
                    data[k] = str(ref.pk)
        item['proposed']=data
        instance=None
        if decision.get('action') == 'update':
            try:
                instance=target.objects.select_for_update().filter(pk=decision.get('target_id')).first()
            except (ValueError,TypeError,DjangoValidationError): pass
            if instance is None:
                item['errors']['target_id']='Select explicit existing UUID.'
            elif type(decision.get('expected_version')) is not int or decision['expected_version'] != instance.version:
                item['errors']['expected_version']='Current integer version required.'
        s=serializer_class(instance,data=data,partial=instance is not None)
        if not s.is_valid(): item['errors']['fields']=json_safe(s.errors)
        else:
            item['proposed'] = canonical(s.validated_data)
            item['references'] = [reference(k, v) for k,v in s.validated_data.items() if isinstance(v, models.Model)]

        candidates = target.objects.filter(models.Q(name__iexact=data.get('name','')) | models.Q(source_system=batch.source_system,source_id=data.get('source_id','')))
        if data.get('code'): candidates = target.objects.filter(models.Q(pk__in=candidates.values('pk')) | models.Q(code__iexact=data['code']))
        item['candidates']=[{'id':str(o.pk),'name':o.name,'version':o.version,'source_id':o.source_id,'state_hash':reference('candidate',o)['state_hash']} for o in candidates.select_for_update().order_by('id')]
        if item['candidates'] and not decision.get('acknowledge_duplicates') is True:
            item['errors']['duplicates']='Explicit acknowledge_duplicates=true required; candidates are never auto-merged.'
        name = str(data.get('name','')).strip().casefold()
        if name:
            peers=seen_names.setdefault(name,[])
            for previous in peers:
                for candidate in [previous,item]:
                    if candidate['decision'].get('acknowledge_duplicates') is not True:
                        candidate['errors']['duplicates']='Duplicate name within batch; explicitly acknowledge each candidate.'
                item['candidates'].append({'row_id':previous['row_id'],'name':data.get('name','')})
                previous['candidates'].append({'row_id':item['row_id'],'name':data.get('name','')})
            peers.append(item)
        code = str(data.get('code','')).strip().casefold()
        if code and code in seen_codes:
            item['errors']['code'] = 'Repeated unique code within batch.'
            seen_codes[code]['errors']['code'] = 'Repeated unique code within batch.'
        elif code: seen_codes[code] = item
        identity=data.get('source_id')
        if not identity:
            item['errors']['source_id']='Nonblank source identifier required.'
        elif identity in seen:
            item['errors']['source_id']='Repeated source identity within this batch.'
            seen[identity]['errors']['source_id']='Repeated source identity within this batch.'
        else: seen[identity]=item
    return results


def canonical(value):
    if isinstance(value, models.Model): return str(value.pk)
    if isinstance(value, (Decimal, uuid.UUID)): return str(value)
    if isinstance(value, (date, datetime)): return value.isoformat()
    if isinstance(value, dict): return {k:canonical(v) for k,v in value.items()}
    if isinstance(value, (list, tuple)): return [canonical(v) for v in value]
    return value


def reference(field, obj):
    # Digest all concrete fields to catch out-of-band edits which omit a version
    # increment. Store only a digest, never User password fingerprints or PII.
    state = {f.attname:canonical(getattr(obj,f.attname)) for f in obj._meta.concrete_fields}
    return {'field':field,'model':obj._meta.label_lower,'id':str(obj.pk),
            'version':getattr(obj,'version',None),'state_hash':payload_hash(state)}


def canonical_plan(batch, mapping, decisions, actor):
    return {'schema_version':1,'source_digest':batch.digest,'source_system':batch.source_system,
            'target':batch.target,'mapping':mapping,'rows':preview(batch,mapping,decisions,actor)}


class ImportViewSet(mixins.ListModelMixin,mixins.RetrieveModelMixin,viewsets.GenericViewSet):
    queryset = ImportBatch.objects.all()
    serializer_class = BatchSerializer
    permission_classes = [ActionPermission]
    action_permissions = {'list':'imports.view_importbatch','retrieve':'imports.view_importbatch','rows':'imports.view_importbatch',
        'reviews':'imports.view_importbatch','create':'imports.add_importbatch','review':'imports.review_importbatch','approve':'imports.approve_importbatch'}
    filterset_fields = ['status','target','source_system','source_kind']
    search_fields = ['filename','source_system']
    ordering_fields = ['created_at','updated_at','filename']
    ordering = ['-created_at','id']
    @staticmethod
    def object_scope(actor,obj):
        return actor.is_active and actor.has_perm('imports.view_importbatch')

    def retrieve(self,request,*args,**kwargs):
        response=super().retrieve(request,*args,**kwargs)
        response['ETag']=f'"{response.data["version"]}"'
        return response

    def create(self,request):
        if set(request.data)-{'file','source_system','source_kind','target','source_attestation'}:
            raise ValidationError('Unknown staging fields.')
        upload=request.FILES.get('file')
        if not upload or upload.size>MAX_BYTES: raise ValidationError({'file':'Provide a CSV/XLSX file up to 5 MiB.'})
        target=request.data.get('target')
        source_system=request.data.get('source_system','').strip()
        kind=request.data.get('source_kind')
        attestation=request.data.get('source_attestation','').strip()
        if target not in RESOURCES or not source_system or len(source_system)>120 or kind not in ['client','demo'] or not attestation or len(attestation)>1000:
            raise ValidationError('Provide target, source_system, source_kind and a source_attestation (max 1000 characters).')
        content=upload.read(MAX_BYTES+1)
        digest=hashlib.sha256(content).hexdigest()
        filename=PurePath(upload.name.replace('\\','/')).name[:240]
        def operation():
            if ImportBatch.objects.filter(digest=digest).exists():
                raise CommandConflict('These source bytes were already staged. Review the existing batch.')
            rows=read_source(content,filename)
            batch=ImportBatch.objects.create(filename=filename,digest=digest,target=target,source_system=source_system,source_kind=kind,source_attestation=attestation,created_by=request.user)
            ImportRow.objects.bulk_create([ImportRow(batch=batch,**r) for r in rows])
            return json_safe(BatchSerializer(batch).data),201,audit(batch,['staged'])
        return run_command(self,{'digest':digest,'filename':filename,'target':target,'source_system':source_system,'source_kind':kind,'source_attestation':attestation},operation)

    @action(detail=True,methods=['get'])
    def rows(self,request,pk=None):
        batch=self.get_object()
        page=self.paginate_queryset(batch.rows.order_by('sheet','row_number'))
        return self.get_paginated_response(ImportRowSerializer(page,many=True).data)

    @action(detail=True,methods=['get'])
    def reviews(self,request,pk=None):
        batch=self.get_object()
        rows=batch.review_history.order_by('-created_at','id')
        page=self.paginate_queryset(rows)
        return self.get_paginated_response([{'id':str(r.pk),'plan':r.plan,'plan_hash':r.plan_hash,
            'reviewed_by':str(r.reviewed_by_id),'created_at':r.created_at} for r in page])

    @action(detail=True,methods=['post'])
    def review(self,request,pk=None):
        version=expected_version(request.headers.get('If-Match'))
        if set(request.data)-{'mapping','decisions'}: raise ValidationError('Unknown review fields.')
        def operation():
            get_object_or_404(ImportBatch,pk=pk)
            batch=lock_versioned(ImportBatch,pk,version)
            if batch.status=='applied': raise CommandConflict('Applied batch is immutable.')
            require_capability(request.user, f'masters.view_{RESOURCES[batch.target]._meta.model_name}')
            mapping=request.data.get('mapping',{})
            plan=canonical_plan(batch,mapping,request.data.get('decisions',{}),request.user)
            review=ImportReview.objects.create(batch=batch,plan=plan,plan_hash=payload_hash(plan),reviewed_by=request.user)
            batch.canonical_review=review
            batch.mapping=mapping; batch.review=plan['rows']; batch.status='reviewed'
            advance_version(batch,update_fields=['mapping','review','status','canonical_review'])
            return json_safe(BatchSerializer(batch).data),200,audit(batch,['reviewed'])
        batch=get_object_or_404(ImportBatch,pk=pk)
        require_capability(request.user,f'masters.view_{RESOURCES[batch.target]._meta.model_name}')
        return run_command(self,{'id':pk,'version':version,'data':request.data},operation)

    @action(detail=True,methods=['post'])
    def approve(self,request,pk=None):
        version=expected_version(request.headers.get('If-Match'))
        if request.data: raise ValidationError('Approval uses persisted reviewed mappings; body must be empty.')
        batch=get_object_or_404(ImportBatch,pk=pk)
        model=RESOURCES[batch.target]
        # Recheck every required capability even on idempotent replay.
        require_capability(request.user,f'masters.view_{model._meta.model_name}')
        for row in batch.review:
            verb={'create':'add','update':'change'}.get(row['decision'].get('action'))
            if verb: require_capability(request.user,f'masters.{verb}_{model._meta.model_name}')
        def operation():
            batch=lock_versioned(ImportBatch,pk,version)
            if batch.status!='reviewed': raise CommandConflict('Review required; applied batches cannot be approved twice.')
            if batch.source_kind!='client': raise ValidationError('Demo/generated source cannot become authoritative masters.')
            if not batch.canonical_review_id:
                raise CommandConflict('Legacy review requires re-review before approval.')
            reviewed=batch.canonical_review
            plan=reviewed.plan
            if payload_hash(plan)!=reviewed.plan_hash:
                raise CommandConflict('Review evidence is invalid; re-review required.')
            review=plan['rows']
            if any(r['errors'] for r in review): raise ValidationError({'rows':review})
            decisions={r['row_id']:r['decision'] for r in review}
            current=canonical_plan(batch,plan['mapping'],decisions,request.user)
            if payload_hash(current)!=reviewed.plan_hash:
                raise StaleReview('Review is stale: references, versions or candidates changed. Re-review required.')
            results=[]
            if not any(r['decision'].get('action') in ['create','update'] for r in review): raise ValidationError('No master changes selected.')
            for row in review:
                choice=row['decision']
                if choice['action']=='skip': continue
                verb='add' if choice['action']=='create' else 'change'
                require_capability(request.user,f'masters.{verb}_{model._meta.model_name}')
                obj=None
                if verb=='change': obj=lock_versioned(model,choice['target_id'],choice['expected_version'])
                s=serializer_for(model)(obj,data=row['proposed'],partial=obj is not None); s.is_valid(raise_exception=True)
                if obj is None: obj=s.save(created_by=request.user,updated_by=request.user)
                else:
                    obj=s.save(updated_by=request.user); advance_version(obj,update_fields=['updated_by'])
                results.append({'row_id':row['row_id'],'target_id':str(obj.pk),'version':obj.version})
                ImportRow.objects.filter(pk=row['row_id']).update(result_id=obj.pk)
                record_event(actor=request.user,action=f'masters.{verb}_{model._meta.model_name}',request_id=request.request_id,**audit(obj,s.validated_data))
            batch.applied_plan={'review_id':str(reviewed.pk),'plan_hash':reviewed.plan_hash,'plan':plan,'results':results}
            batch.status='applied'; batch.approved_by=request.user; batch.approved_at=timezone.now()
            advance_version(batch,update_fields=['status','approved_by','approved_at','applied_plan'])
            return json_safe(BatchSerializer(batch).data),200,audit(batch,['applied'])
        return run_command(self,{'id':pk,'version':version},operation)
