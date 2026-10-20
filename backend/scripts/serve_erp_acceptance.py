"""Extend the existing disposable loopback harness with synthetic ERP fixtures.

Run from backend: .venv/Scripts/python scripts/serve_erp_acceptance.py
    --disposable-synthetic-only --port 8014 --seconds 3600
Never provisions the configured application database. Closing the bounded harness
destroys its generated database; all fixture actors are synthetic.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import serve_commercial_acceptance as harness
from tests import test_phase4b_transport

original_fixture = test_phase4b_transport.setup_fixture


def setup_fixture():
    from datetime import timedelta
    from django.contrib.auth.models import Permission
    from django.utils import timezone
    from apps.inventory.ledger_guard import require_synthetic_environment
    from apps.inventory.models import Warehouse, WarehouseScope
    from apps.commercial import services
    from apps.commercial.handoffs import derive
    import uuid
    require_synthetic_environment()
    fx, revision, variant = original_fixture()
    fx.user.user_permissions.add(*Permission.objects.filter(content_type__app_label__in=['rehearsal', 'inventory']))
    warehouse = Warehouse.objects.create(code='SYN-ERP', name='Synthetic ERP rehearsal warehouse', created_by=fx.user)
    WarehouseScope.objects.create(user=fx.user, warehouse=warehouse, requested_by=fx.user, approved_by=fx.other,
        policy_reference='synthetic:scenario-policy', evidence_reference='synthetic:scenario-scope',
        expires_at=timezone.now()+timedelta(hours=1))
    data = fx.data(True)
    import copy
    data['lines'].append({**copy.deepcopy(data['lines'][0]), 'variant': str(variant.pk)})
    doc, _, _ = services.command(actor=fx.user, key=str(uuid.uuid4()), request_id=uuid.uuid4(),
        kind='COSTING', data=data, reason='Synthetic browser fixture')
    for _ in range(2):
        doc, _, _ = derive(actor=fx.user, source_id=doc['revision'], key=str(uuid.uuid4()),
            request_id=uuid.uuid4(), reason='Synthetic browser draft mapping')
    from apps.rehearsal import services as rehearsal
    create = {'sales_order_revision': doc['revision'], 'warehouse': str(warehouse.pk),
        'routes': [{'line': 0, 'stages': ['EXTRUSION', 'PACKING']}, {'line': 1, 'stages': ['PACKING']}]}
    job, _, _ = rehearsal.command(actor=fx.user, key=str(uuid.uuid4()), request_id=uuid.uuid4(),
        data=create, reason='Synthetic browser walkthrough')
    steps = [('review', {}), ('issue', {'quantity': '6', 'available_quantity': '6'})]
    for index, stage in ((0, 'EXTRUSION'), (0, 'PACKING'), (1, 'PACKING')):
        steps.extend([('start', {'line': index, 'stage': stage, 'machine': 'synthetic:machine',
            'operator': 'synthetic:operator', 'input_quantity': '3'}),
            ('complete', {'line': index, 'stage': stage, 'output_quantity': '3', 'waste': '0', 'rejection': '0'})])
    steps.extend([('qc', {'outcome': 'FAIL', 'remarks': 'Synthetic initial rejection'}),
        ('qc', {'outcome': 'PASS', 'remarks': 'Synthetic reinspection'}), ('finish', {}), ('dispatch', {})])
    for action, values in steps:
        job, _, _ = rehearsal.command(actor=fx.user, key=str(uuid.uuid4()), request_id=uuid.uuid4(),
            pk=job['id'], version=job['version'], action=action, data=values, reason='Synthetic browser walkthrough')
    draft, _, _ = rehearsal.command(actor=fx.user, key=str(uuid.uuid4()), request_id=uuid.uuid4(),
        data=create, reason='Synthetic interactive draft')
    import json
    print('ERP_SYNTHETIC_FIXTURES '+json.dumps({'demand': doc['id'], 'completed_job': job['id'],
        'interactive_job': draft['id'], 'warehouse': str(warehouse.pk), 'operational': False}), flush=True)
    return fx, revision, variant


if __name__ == '__main__':
    test_phase4b_transport.setup_fixture = setup_fixture
    harness.main()
