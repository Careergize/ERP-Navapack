"""HTTPS-only persistent demo; intentionally distinct from production and tests."""
from .production import *  # noqa: F403
from config.environment import required
import re
import uuid
from django.core.exceptions import ImproperlyConfigured

APP_ENV = required('APP_ENV')
DEMO_DATABASE_NAME = required('DEMO_DATABASE_NAME')
DEMO_INSTANCE_ID = str(uuid.UUID(required('DEMO_INSTANCE_ID')))
DEMO_EXECUTION_SECRET = required('DEMO_EXECUTION_SECRET', 64)
if APP_ENV != 'DEMO' or not re.fullmatch(r'navapack_demo_[a-z0-9_]{8,48}', DEMO_DATABASE_NAME):
    raise ImproperlyConfigured('Use a dedicated explicitly named DEMO database.')
if DATABASES['default']['NAME'] != DEMO_DATABASE_NAME:
    raise ImproperlyConfigured('Configured PostgreSQL identity must equal DEMO_DATABASE_NAME.')
if DEMO_EXECUTION_SECRET in (SECRET_KEY, JWT_SIGNING_KEY):
    raise ImproperlyConfigured('DEMO execution secret must be independent.')
if not CORS_ALLOWED_ORIGINS or not CSRF_TRUSTED_ORIGINS:
    raise ImproperlyConfigured('DEMO requires explicit HTTPS frontend origins.')
SESSION_COOKIE_NAME = 'navapack_demo_session'
SECURE_REDIRECT_EXEMPT = [r'^api/v1/health/$', r'^api/v1/ready/$']
