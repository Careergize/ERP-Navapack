"""Bounded loopback browser harness. Creates/destroys its own stamped test database.

From backend: .venv/Scripts/python scripts/serve_synthetic_acceptance.py --disposable-synthetic-only
Stop by creating the printed metadata stop_file, or wait for the bounded lifetime.
No existing DB/name/nonce can be supplied; all writes still use ordinary guarded services.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import time
import uuid
from socketserver import ThreadingMixIn
from wsgiref.simple_server import make_server, WSGIServer

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings.test')
import django
django.setup()
from django.conf import settings
from django.db import connection, connections
from django.core.wsgi import get_wsgi_application
from scripts.test_isolated import SyntheticLedgerRunner
from apps.inventory.ledger_guard import require_synthetic_environment


class LoopbackServer(ThreadingMixIn,WSGIServer):
    daemon_threads=False


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--disposable-synthetic-only',action='store_true',required=True)
    parser.add_argument('--port',type=int,default=8013)
    parser.add_argument('--seconds',type=int,default=1800)
    args=parser.parse_args()
    if settings.SETTINGS_MODULE!='config.settings.test' or connection.vendor!='postgresql' or connection.settings_dict['HOST'] not in ['127.0.0.1','localhost','::1']:
        raise SystemExit('Only config.settings.test and local PostgreSQL are allowed.')
    if not 1<=args.seconds<=3600 or not 1024<=args.port<=65535:raise SystemExit('Use a bounded test lifetime and unprivileged loopback port.')
    name='test_phase3b_'+uuid.uuid4().hex
    with connection.cursor() as cursor:
        cursor.execute('SELECT 1 FROM pg_database WHERE datname=%s',[name])
        if cursor.fetchone():raise SystemExit('Refusing to reuse any existing database.')
    settings.DATABASES['default'].setdefault('TEST',{})['NAME']=name
    runner=SyntheticLedgerRunner(verbosity=0,interactive=False)
    old=runner.setup_databases()
    try:
        require_synthetic_environment()
        settings.CORS_ALLOWED_ORIGINS=['http://127.0.0.1:5173','http://localhost:5173']
        from tests.test_phase3e import Phase3EAcceptanceTests
        from apps.inventory.models import StockIdentity
        from apps.inventory.quality_models import Nonconformance
        case=Phase3EAcceptanceTests();case.initialize()
        def new_root(label):
            case.stock=StockIdentity.objects.create(warehouse=case.wh,location=case.loc,material=case.material,unit=case.unit,kind='BATCH',ownership='COMPANY',ownership_evidence='synthetic:company',source_system='synthetic:browser',source_reference=uuid.uuid4().hex,physical_reference='SYN-BROWSER-'+label,created_by=case.actor)
        case.test_a_receipt_held_inspection_release_actual_issue_and_history()
        issued_stock=str(case.stock.pk)
        new_root('NCR');case.test_b_failed_inspection_ncr_capa_reinspection_never_auto_releases()
        ncr=str(Nonconformance.objects.get().pk)
        new_root('PENDING-QC')
        opening=case.posted(case.body('OPENING'))
        plan=case.plan();inspection=case.inspect(opening,plan)
        # Pending correction capture, not approval/posting, against an actual immutable opening.
        correction=case.create_operation(case.body('OPENING_CORRECTION','12',related=opening['ledger_transaction']))
        pending_stock=str(case.stock.pk)
        # Provide a governed fixture-only physical line for an actual browser receipt submission.
        new_root('BROWSER-RECEIPT');case.posted(case.body('OPENING','0'))
        receipt_body=case.body('IN','5')
        new_root('TRANSFER');case.test_d_held_transfer_preserves_identity_quality_and_clearance_gate()
        new_root('COUNT');case.posted(case.body('OPENING'))
        count=case.prepared(case.create_operation(case.body('COUNT','12')))
        adjustment=case.create_operation(case.body('ADJUSTMENT','12',count_session=count['id']))
        folder=Path('.local/phase3e').resolve();folder.mkdir(parents=True,exist_ok=True)
        stop=folder/('stop-'+uuid.uuid4().hex)
        metadata={'database':name,'api_base':f'http://127.0.0.1:{args.port}/api/v1','frontend':'http://127.0.0.1:5173',
            'stop_file':str(stop),'lifetime_seconds':args.seconds,'operational_posting':False,
            'synthetic_accounts':[case.actor.email,case.maker.email,case.reviewer.email],'test_password':'password',
            'warehouse':str(case.wh.pk),'other_warehouse':str(case.wh2.pk),'location':str(case.loc.pk),
            'department':str(case.department.pk),'material':str(case.material.pk),'unit':str(case.unit.pk),
            'policy':str(case.policy.pk),'pending_inspection':inspection['id'],'pending_stock':pending_stock,
            'issued_stock':issued_stock,'ncr':ncr,'opening_correction':correction['id'],'adjustment':adjustment['id'],
            'browser_receipt_body':receipt_body}
        (folder/'browser-fixtures.json').write_text(json.dumps(metadata,indent=2))
        with make_server('127.0.0.1',args.port,get_wsgi_application(),server_class=LoopbackServer) as server:
            server.timeout=0.5
            print('SYNTHETIC_BROWSER_READY '+str(folder/'browser-fixtures.json'),flush=True)
            deadline=time.monotonic()+args.seconds
            while time.monotonic()<deadline and not stop.exists():server.handle_request()
    finally:
        # Ensure teardown is still bound to this generated test database, never the app DB.
        if connection.settings_dict['NAME']!=name:raise RuntimeError('Refusing teardown of an unexpected database.')
        connections.close_all();runner.teardown_databases(old)
        print('SYNTHETIC_BROWSER_DATABASE_DESTROYED '+name,flush=True)


if __name__=='__main__':main()
