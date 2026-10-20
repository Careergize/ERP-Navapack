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


class SyntheticLedgerRunner(DiscoverRunner):
    def setup_databases(self, **kwargs):
        old=super().setup_databases(**kwargs)
        name=settings.DATABASES['default']['TEST']['NAME']
        with connection.cursor() as cursor:
            cursor.execute('SELECT current_database()')
            if cursor.fetchone()[0]!=name or not name.startswith('test_phase3b_'):
                raise RuntimeError('Synthetic context requires the newly created disposable database.')
            nonce=uuid.uuid4()
            cursor.execute('CREATE TABLE public.navapack_synthetic_environment (singleton boolean PRIMARY KEY CHECK(singleton), nonce uuid NOT NULL)')
            cursor.execute('INSERT INTO public.navapack_synthetic_environment VALUES (true,%s)',[nonce])
        settings.SYNTHETIC_LEDGER_ENABLED=True
        settings.SYNTHETIC_LEDGER_DATABASE=name
        settings.SYNTHETIC_LEDGER_NONCE=str(nonce)
        return old

if __name__ == '__main__':
    config=settings.DATABASES['default']
    if connection.vendor!='postgresql' or config['HOST'] not in {'127.0.0.1','localhost','::1'}:
        raise SystemExit('Use a dedicated local PostgreSQL test cluster.')
    synthetic='--synthetic-ledger' in sys.argv
    if synthetic: sys.argv.remove('--synthetic-ledger')
    if synthetic and settings.SETTINGS_MODULE!='config.settings.test':
        raise SystemExit('Synthetic execution requires config.settings.test.')
    name=('test_phase3b_' if synthetic else 'test_phase21_')+uuid.uuid4().hex
    with connection.cursor() as cursor:
        cursor.execute('SELECT 1 FROM pg_database WHERE datname=%s',[name])
        if cursor.fetchone(): raise SystemExit('Refusing to reuse an existing test database.')
    config.setdefault('TEST',{})['NAME']=name
    print('ISOLATED_DATABASE='+name,flush=True)
    runner=SyntheticLedgerRunner if synthetic else DiscoverRunner
    raise SystemExit(bool(runner(verbosity=2,interactive=True).run_tests(sys.argv[1:] or ['tests'])))
