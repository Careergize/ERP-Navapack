import os
from urllib.parse import urlsplit
from django.core.exceptions import ImproperlyConfigured


def required(name, minimum=1):
    value = os.getenv(name, '').strip()
    if len(value) < minimum or value.lower().startswith(('change-me', 'replace-me')):
        raise ImproperlyConfigured(f'{name} must be configured (minimum {minimum} characters).')
    return value


def boolean(name, default=False):
    value = os.getenv(name, str(default)).lower()
    if value not in ('true', 'false'):
        raise ImproperlyConfigured(f'{name} must be true or false.')
    return value == 'true'


def csv(name, default=''):
    return [value.strip() for value in os.getenv(name, default).split(',') if value.strip()]


def port(name, default='5432'):
    try:
        value = int(os.getenv(name, default))
        if not 1 <= value <= 65535:
            raise ValueError()
    except ValueError:
        raise ImproperlyConfigured(f'{name} must be a port between 1 and 65535.')
    return value


def origins(name, production=False):
    values = csv(name)
    for value in values:
        parsed = urlsplit(value)
        try:
            parsed.port
        except ValueError:
            raise ImproperlyConfigured(f'{name} contains an invalid port.')
        if (parsed.scheme not in ('http', 'https') or not parsed.hostname
                or parsed.username or parsed.password or '*' in value
                or parsed.path or parsed.query or parsed.fragment
                or (production and parsed.scheme != 'https')):
            raise ImproperlyConfigured(f'{name} must contain explicit origins without paths; HTTPS in production.')
    return values
