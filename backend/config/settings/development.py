from .base import *  # noqa: F403
from config.environment import boolean

DEBUG = boolean('DJANGO_DEBUG')
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
