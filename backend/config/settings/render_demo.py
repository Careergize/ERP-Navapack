"""Temporary Render DEMO profile. Production TLS policy remains independent."""
from .base import *  # noqa: F403
from config.environment import boolean, origins
from django.core.exceptions import ImproperlyConfigured

if not os.getenv('DJANGO_ALLOWED_HOSTS') or not ALLOWED_HOSTS or any('*' in host for host in ALLOWED_HOSTS):
    raise ImproperlyConfigured('Render DEMO requires explicit DJANGO_ALLOWED_HOSTS.')
if boolean('DJANGO_DEBUG'):
    raise ImproperlyConfigured('Render DEMO requires DJANGO_DEBUG=false.')
if SECRET_KEY == JWT_SIGNING_KEY:
    raise ImproperlyConfigured('JWT_SIGNING_KEY must be independent from DJANGO_SECRET_KEY.')
# Render internal PostgreSQL supports required TLS without a custom CA.
# Explicit prefer allows plaintext fallback and does not verify server identity.
DATABASES['default']['OPTIONS']['sslmode'] = os.getenv('POSTGRES_SSLMODE', 'require')
if DATABASES['default']['OPTIONS']['sslmode'] not in ('require', 'prefer', 'verify-full'):
    raise ImproperlyConfigured('Render DEMO permits require, prefer or verify-full PostgreSQL TLS modes only.')
CORS_ALLOWED_ORIGINS = origins('CORS_ALLOWED_ORIGINS', production=True)
CSRF_TRUSTED_ORIGINS = origins('CSRF_TRUSTED_ORIGINS', production=True)
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
if boolean('TRUST_PROXY_HTTPS'):
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
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
