"""Run Django tests in a new local PostgreSQL DB, never reuse/drop a prior DB.

From backend: .venv/Scripts/python scripts/test_isolated.py [test labels ...]
"""
import os
from pathlib import Path
import sys
import uuid

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings.test')
import django
django.setup()
from django.conf import settings
from django.db import connection
from django.test.runner import DiscoverRunner

if __name__ == '__main__':
    config=settings.DATABASES['default']
    if connection.vendor!='postgresql' or config['HOST'] not in {'127.0.0.1','localhost','::1'}:
        raise SystemExit('Use a dedicated local PostgreSQL test cluster.')
    name='test_phase21_'+uuid.uuid4().hex
    with connection.cursor() as cursor:
        cursor.execute('SELECT 1 FROM pg_database WHERE datname=%s',[name])
        if cursor.fetchone(): raise SystemExit('Refusing to reuse an existing test database.')
    config.setdefault('TEST',{})['NAME']=name
    print('ISOLATED_DATABASE='+name,flush=True)
    raise SystemExit(bool(DiscoverRunner(verbosity=2,interactive=True).run_tests(sys.argv[1:] or ['tests'])))
