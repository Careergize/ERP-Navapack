"""Bounded local existing-interface acceptance; fresh stamped PostgreSQL only.

No configured database migration, real grants, existing database reuse or guard bypass.
The generated test database is destroyed at shutdown; use the stop_file to end early.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import time
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.test')
import django
django.setup()
from django.conf import settings
from django.db import connection, connections
from django.core.wsgi import get_wsgi_application
from wsgiref.simple_server import make_server
from scripts.serve_commercial_acceptance import LoopbackServer
from scripts.test_isolated import SyntheticLedgerRunner


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--disposable-synthetic-only', action='store_true', required=True)
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--seconds', type=int, default=3600)
    args = parser.parse_args()
    if settings.SETTINGS_MODULE != 'config.settings.test' or connection.vendor != 'postgresql' or connection.settings_dict['HOST'] not in ('localhost','127.0.0.1','::1'):
        raise SystemExit('Only local PostgreSQL and config.settings.test are supported.')
    if not 1 <= args.seconds <= 3600 or not 1024 <= args.port <= 65535:
        raise SystemExit('Bounded lifetime and unprivileged loopback port required.')
    name = 'test_phase3b_'+uuid.uuid4().hex
    with connection.cursor() as cursor:
        cursor.execute('SELECT 1 FROM pg_database WHERE datname=%s', [name])
        if cursor.fetchone(): raise SystemExit('Refusing an existing database.')
    settings.DATABASES['default'].setdefault('TEST', {})['NAME'] = name
    runner = SyntheticLedgerRunner(verbosity=0, interactive=False)
    old = runner.setup_databases()
    try:
        from apps.inventory.ledger_guard import require_synthetic_environment
        require_synthetic_environment()
        from scripts.serve_erp_acceptance import setup_fixture
        fx, revision, variant = setup_fixture()
        from tests.test_phase3e import Phase3EAcceptanceTests
        case = Phase3EAcceptanceTests(); case.initialize()
        case.test_a_receipt_held_inspection_release_actual_issue_and_history()
        from apps.inventory.models import WarehouseScope
        from django.utils import timezone
        from datetime import timedelta
        # Synthetic account only, in this newly generated test database.
        WarehouseScope.objects.create(user=fx.user, company_wide=True, requested_by=fx.user, approved_by=fx.other,
            policy_reference='synthetic:full-interface', evidence_reference='synthetic:full-interface',
            expires_at=timezone.now()+timedelta(seconds=args.seconds))
        fx.user.is_master_admin = True
        fx.user.save(update_fields=['is_master_admin'])
        from django.contrib.auth.models import Permission
        fx.user.user_permissions.add(*Permission.objects.filter(content_type__app_label='imports'))
        # Recycling evidence belongs only to this disposable synthetic production source.
        from apps.commercial.models import CommercialDocument
        from apps.rehearsal import services as rehearsal
        from apps.inventory.models import Warehouse
        source = CommercialDocument.objects.get(owner=fx.user, kind='SALES_ORDER')
        source_revision = source.revisions.get(number=source.version)
        warehouse = Warehouse.objects.get(code='SYN-ERP')
        body = {'sales_order_revision':str(source_revision.pk),'warehouse':str(warehouse.pk),
            'routes':[{'line':i,'stages':['PACKING']} for i in range(len(source_revision.snapshot['input']['lines']))]}
        def run(job=None, action='create', data=None):
            return rehearsal.command(actor=fx.user,key=str(uuid.uuid4()),request_id=uuid.uuid4(),
                pk=job['id'] if job else None,version=job['version'] if job else None,
                action=action,data=data,reason='Synthetic full-interface recycling fixture')[0]
        job = run(data=body)
        job = run(job,'review',{})
        job = run(job,'issue',{'quantity':'6','available_quantity':'6'})
        for i in range(len(body['routes'])):
            job = run(job,'start',{'line':i,'stage':'PACKING','machine':'synthetic:packing','operator':'synthetic:operator','input_quantity':'3'})
            job = run(job,'complete',{'line':i,'stage':'PACKING','output_quantity':'2','waste':'0.75','rejection':'0.25'})
        run(job,'recycle',{'line':0,'stage':'PACKING','classification':'PROCESS_WASTE','unit':str(fx.unit.pk),
            'intake':'0.5','recovered':'0.25','rejected':'0.125','disposed':'0.125','batch_reference':'synthetic:full-interface-recycling'})
        settings.CORS_ALLOWED_ORIGINS = ['http://localhost:5173','http://127.0.0.1:5173']
        folder = Path('.local/full-interface').resolve(); folder.mkdir(parents=True, exist_ok=True)
        stop = folder/('stop-'+uuid.uuid4().hex)
        metadata = {'database':name,'api':f'http://127.0.0.1:{args.port}/api/v1',
            'frontend':'http://localhost:5173','stop_file':str(stop),'lifetime_seconds':args.seconds,
            'synthetic_user':fx.user.email,'synthetic_password':'password','operational':False}
        (folder/'browser-fixtures.json').write_text(json.dumps(metadata,indent=2))
        with make_server('127.0.0.1',args.port,get_wsgi_application(),server_class=LoopbackServer) as server:
            server.timeout = 0.5
            print('FULL_ERP_BROWSER_READY '+str(folder/'browser-fixtures.json'),flush=True)
            deadline = time.monotonic()+args.seconds
            while time.monotonic() < deadline and not stop.exists(): server.handle_request()
    finally:
        if connection.settings_dict['NAME'] != name:
            raise RuntimeError('Refusing teardown of an unexpected database.')
        connections.close_all()
        runner.teardown_databases(old)
        print('FULL_ERP_DISPOSABLE_DATABASE_DESTROYED '+name,flush=True)


if __name__ == '__main__': main()
