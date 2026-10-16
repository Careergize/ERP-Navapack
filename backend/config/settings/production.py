from django.core.exceptions import ImproperlyConfigured
from .base import *  # noqa: F403
from config.environment import origins, boolean

if not ALLOWED_HOSTS or '*' in ALLOWED_HOSTS or any('*' in host for host in ALLOWED_HOSTS):
    raise ImproperlyConfigured('Production requires explicit DJANGO_ALLOWED_HOSTS.')
if not os.getenv('DJANGO_ALLOWED_HOSTS') or boolean('DJANGO_DEBUG'):
    raise ImproperlyConfigured('Production requires explicit hosts and DJANGO_DEBUG=false.')
if SECRET_KEY == JWT_SIGNING_KEY:
    raise ImproperlyConfigured('JWT_SIGNING_KEY must be independent from DJANGO_SECRET_KEY.')
if DATABASES['default']['OPTIONS']['sslmode'] != 'verify-full':
    raise ImproperlyConfigured('Production requires POSTGRES_SSLMODE=verify-full and a trusted database certificate.')
CORS_ALLOWED_ORIGINS = origins('CORS_ALLOWED_ORIGINS', production=True)
CSRF_TRUSTED_ORIGINS = origins('CSRF_TRUSTED_ORIGINS', production=True)
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
# Enable only behind an ingress that strips client-supplied forwarding headers.
if boolean('TRUST_PROXY_HTTPS'):
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
