import os
# Test-only values never used by development or production settings.
os.environ.setdefault('DJANGO_SECRET_KEY', 'test-only-django-key-' * 4)
os.environ.setdefault('JWT_SIGNING_KEY', 'test-only-jwt-signing-' * 4)
from .base import *  # noqa: F403, E402
ALLOWED_HOSTS = ['testserver', 'localhost', '127.0.0.1']
DATABASES['default']['CONN_MAX_AGE'] = 0
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
