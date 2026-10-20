import uuid
from django.conf import settings
from django.db import models


class VersionedModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-created_at', 'id']
        constraints = [models.CheckConstraint(condition=models.Q(version__gte=1), name='%(app_label)s_%(class)s_version_positive')]


class AppendOnlyQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValueError('Audit events are append-only.')

    def delete(self):
        raise ValueError('Audit events are append-only.')

    def bulk_update(self, objs, fields, batch_size=None):
        raise ValueError('Audit events are append-only.')


class AuditEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT)
    action = models.CharField(max_length=100)
    entity_type = models.CharField(max_length=100)
    entity_id = models.CharField(max_length=200)
    timestamp = models.DateTimeField(auto_now_add=True)
    request_id = models.UUIDField()
    summary = models.JSONField(default=dict)
    reason = models.TextField(blank=True)
    source_version = models.PositiveIntegerField(null=True)
    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        indexes = [models.Index(fields=['entity_type', 'entity_id', 'timestamp']),
                   models.Index(fields=['actor', 'timestamp'])]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError('Audit events are append-only.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError('Audit events are append-only.')


class AuditEvidence(models.Model):
    """Bounded sanitized change payload; access only through its scoped event."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.OneToOneField(AuditEvent, on_delete=models.PROTECT, related_name='evidence')
    payload = models.JSONField()
    sha256 = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    objects = AppendOnlyQuerySet.as_manager()

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError('Audit evidence is append-only.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError('Audit evidence is append-only.')


class IdempotencyRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    scope = models.CharField(max_length=200)
    action = models.CharField(max_length=100)
    key = models.CharField(max_length=200)
    payload_hash = models.CharField(max_length=64)
    result = models.JSONField(null=True)
    response_status = models.PositiveSmallIntegerField(default=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['actor', 'scope', 'action', 'key'], name='unique_command_key')]


class ThrottleWindow(models.Model):
    key = models.CharField(max_length=64, primary_key=True)
    started_at = models.DateTimeField()
    count = models.PositiveIntegerField(default=0)
