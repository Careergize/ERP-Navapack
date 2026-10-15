import hashlib
from django.db import transaction
from django.utils import timezone
from rest_framework.throttling import SimpleRateThrottle
from apps.core.models import ThrottleWindow


class DatabaseAuthThrottle(SimpleRateThrottle):
    """Shared PostgreSQL fixed window, serialized across workers. No raw IP retained."""
    def allow_request(self, request, view):
        self.now = timezone.now()
        key = hashlib.sha256(f'{self.scope}:{request.META.get("REMOTE_ADDR", "unknown")}'.encode()).hexdigest()
        with transaction.atomic():
            row, _ = ThrottleWindow.objects.get_or_create(key=key, defaults={'started_at': self.now})
            row = ThrottleWindow.objects.select_for_update().get(pk=key)
            elapsed = (self.now - row.started_at).total_seconds()
            if elapsed >= self.duration:
                row.started_at, row.count = self.now, 0
                elapsed = 0
            self.remaining_wait = max(1, self.duration - elapsed)
            if row.count >= self.num_requests:
                return False
            row.count += 1
            row.save(update_fields=['started_at', 'count'])
        return True

    def wait(self):
        return self.remaining_wait


class LoginThrottle(DatabaseAuthThrottle):
    scope = 'login'


class RefreshThrottle(DatabaseAuthThrottle):
    scope = 'refresh'
