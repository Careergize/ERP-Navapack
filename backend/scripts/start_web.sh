#!/bin/sh
set -eu
: "${DJANGO_SETTINGS_MODULE:?Set config.settings.demo or config.settings.production}"
case "$DJANGO_SETTINGS_MODULE" in
  config.settings.demo|config.settings.production) ;;
  *) echo 'Refusing non-hosted settings' >&2; exit 1 ;;
esac
python manage.py check --deploy --fail-level WARNING
python manage.py deployment_diagnostics
exec gunicorn config.wsgi:application --config gunicorn.conf.py
