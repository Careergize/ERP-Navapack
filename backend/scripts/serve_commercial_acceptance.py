"""Bounded, loopback-only browser harness; always creates its own stamped database."""
import argparse
import json
import os
from pathlib import Path
import sys
import time
import uuid
from socketserver import ThreadingMixIn
from wsgiref.simple_server import make_server, WSGIServer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.test')
import django
django.setup()
from django.conf import settings
from django.db import connection, connections
from django.core.wsgi import get_wsgi_application
from scripts.test_isolated import SyntheticLedgerRunner
from apps.inventory.ledger_guard import require_synthetic_environment


class LoopbackServer(ThreadingMixIn, WSGIServer):
    daemon_threads = False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--disposable-synthetic-only', action='store_true', required=True)
    parser.add_argument('--port', type=int, default=8014)
    parser.add_argument('--seconds', type=int, default=1800)
    args = parser.parse_args()
    if settings.SETTINGS_MODULE != 'config.settings.test' or connection.vendor != 'postgresql' or connection.settings_dict['HOST'] not in ('localhost', '127.0.0.1', '::1'):
        raise SystemExit('Only local PostgreSQL/config.settings.test is supported.')
    if not 1 <= args.seconds <= 3600 or not 1024 <= args.port <= 65535:
        raise SystemExit('Use a bounded lifetime and unprivileged port.')
    name = 'test_phase3b_'+uuid.uuid4().hex
    with connection.cursor() as c:
        c.execute('SELECT 1 FROM pg_database WHERE datname=%s', [name])
        if c.fetchone(): raise SystemExit('Refusing an existing database.')
    settings.DATABASES['default'].setdefault('TEST', {})['NAME'] = name
    runner = SyntheticLedgerRunner(verbosity=0, interactive=False)
    old = runner.setup_databases()
    try:
        require_synthetic_environment()
        from tests.test_phase4b_transport import setup_fixture
        fx, revision, variant = setup_fixture()
        settings.CORS_ALLOWED_ORIGINS = ['http://127.0.0.1:5174', 'http://localhost:5174']
        folder = Path('.local/phase4b').resolve(); folder.mkdir(parents=True, exist_ok=True)
        stop = folder/('stop-'+uuid.uuid4().hex)
        metadata = {'database': name, 'api': f'http://127.0.0.1:{args.port}/api/v1', 'stop_file': str(stop),
            'users': [fx.user.email, fx.other.email], 'synthetic_password': 'password', 'model_revision': str(revision.pk),
            'variant': str(fx.variant.pk), 'second_variant': str(variant.pk), 'unit': str(fx.unit.pk),
            'material': str(fx.material.pk), 'customer': str(fx.customer.pk), 'operational': False}
        (folder/'browser-fixtures.json').write_text(json.dumps(metadata, indent=2))
        with make_server('127.0.0.1', args.port, get_wsgi_application(), server_class=LoopbackServer) as server:
            server.timeout = 0.5
            print('COMMERCIAL_BROWSER_READY '+str(folder/'browser-fixtures.json'), flush=True)
            deadline = time.monotonic()+args.seconds
            while time.monotonic() < deadline and not stop.exists(): server.handle_request()
        from apps.inventory.ledger_models import LedgerTransaction, LedgerEntry, BalanceProjection
        counts = {m._meta.model_name: m.objects.count() for m in (LedgerTransaction, LedgerEntry, BalanceProjection)}
        if any(counts.values()): raise RuntimeError('Browser acceptance unexpectedly mutated inventory.')
        print('COMMERCIAL_BROWSER_NO_STOCK_MUTATION '+json.dumps(counts), flush=True)
    finally:
        if connection.settings_dict['NAME'] != name: raise RuntimeError('Unexpected cleanup database; refusing teardown.')
        connections.close_all(); runner.teardown_databases(old)
        print('COMMERCIAL_BROWSER_DATABASE_DESTROYED '+name, flush=True)


if __name__ == '__main__': main()
