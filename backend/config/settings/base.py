import os
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv
from config.environment import required, csv, origins, port

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / '.env', override=False)
SECRET_KEY = required('DJANGO_SECRET_KEY', 50)
JWT_SIGNING_KEY = required('JWT_SIGNING_KEY', 50)
DEBUG = False
ALLOWED_HOSTS = csv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1')
INSTALLED_APPS = [
    'django.contrib.auth', 'django.contrib.contenttypes', 'django.contrib.sessions',
    'django.contrib.staticfiles', 'corsheaders', 'rest_framework', 'django_filters',
    'rest_framework_simplejwt.token_blacklist', 'apps.accounts', 'apps.core',
    'apps.masters', 'apps.specifications', 'apps.imports', 'apps.inventory', 'apps.commercial',
    'apps.rehearsal',
]
MIDDLEWARE = [
    'apps.core.middleware.RequestIDMiddleware',
    'django.middleware.security.SecurityMiddleware', 'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware', 'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'
DATABASES = {'default': {
    'ENGINE': 'django.db.backends.postgresql', 'NAME': required('POSTGRES_DB'),
    'USER': required('POSTGRES_USER'), 'PASSWORD': required('POSTGRES_PASSWORD'),
    'HOST': os.getenv('POSTGRES_HOST', '127.0.0.1'), 'PORT': port('POSTGRES_PORT'),
    'CONN_MAX_AGE': 60, 'CONN_HEALTH_CHECKS': True,
    'OPTIONS': {'connect_timeout': 5, 'sslmode': os.getenv('POSTGRES_SSLMODE', 'prefer')},
}}
AUTH_USER_MODEL = 'accounts.User'
SYNTHETIC_LEDGER_ENABLED = False  # Never enabled by environment variables or production settings.
AUTHENTICATION_BACKENDS = ['apps.accounts.backends.EmailBackend']
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 12}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
PASSWORD_HASHERS = ['django.contrib.auth.hashers.PBKDF2PasswordHasher']
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
CORS_ALLOWED_ORIGINS = origins('CORS_ALLOWED_ORIGINS')
CORS_ALLOW_CREDENTIALS = False
CSRF_TRUSTED_ORIGINS = origins('CSRF_TRUSTED_ORIGINS')
from corsheaders.defaults import default_headers
CORS_ALLOW_HEADERS = (*default_headers, 'x-request-id', 'idempotency-key', 'if-match')
CORS_EXPOSE_HEADERS = ['X-Request-ID', 'ETag', 'Retry-After']
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework_simplejwt.authentication.JWTAuthentication'],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],
    'DEFAULT_PAGINATION_CLASS': 'apps.core.api.StandardPagination', 'PAGE_SIZE': 25,
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend',
                               'rest_framework.filters.SearchFilter', 'rest_framework.filters.OrderingFilter'],
    'EXCEPTION_HANDLER': 'apps.core.api.exception_handler',
    'DEFAULT_THROTTLE_RATES': {'login': '5/minute', 'refresh': '30/minute'},
    'COERCE_DECIMAL_TO_STRING': True,
}
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=5), 'REFRESH_TOKEN_LIFETIME': timedelta(hours=8),
    'ROTATE_REFRESH_TOKENS': True, 'BLACKLIST_AFTER_ROTATION': True,
    'SIGNING_KEY': JWT_SIGNING_KEY, 'UPDATE_LAST_LOGIN': False,
    'CHECK_REVOKE_TOKEN': True,
}
LOGGING = {
    'version': 1, 'disable_existing_loggers': False,
    'formatters': {'json': {'()': 'apps.core.logging.JSONFormatter'}},
    'handlers': {'console': {'class': 'logging.StreamHandler', 'formatter': 'json'}},
    'root': {'handlers': ['console'], 'level': os.getenv('LOG_LEVEL', 'INFO')},
    'loggers': {'django.request': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False}},
}
