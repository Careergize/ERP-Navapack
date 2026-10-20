"""Production React adapters through real JWT/HTTP to disposable PostgreSQL."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
from datetime import timedelta
from django.contrib.auth.models import Permission
from django.test import LiveServerTestCase, override_settings
from django.utils import timezone
from apps.inventory.models import Warehouse, WarehouseScope
from apps.inventory.ledger_models import LedgerTransaction, LedgerEntry, BalanceProjection
from apps.inventory.quality_models import Inspection, QualityAuthorization, QualityPosting
from apps.masters.models import ProductVariant
from tests import test_commercial


class RehearsalTransportTests(LiveServerTestCase):
    def test_actual_react_journey_over_http(self):
        fx = test_commercial.CommercialTests(); fx.setUp()
        fx.user.user_permissions.add(*Permission.objects.filter(content_type__app_label='rehearsal'))
        wh = Warehouse.objects.create(code='HTTP', name='Synthetic HTTP warehouse', created_by=fx.user)
        WarehouseScope.objects.create(user=fx.user, warehouse=wh, requested_by=fx.user, approved_by=fx.other,
            policy_reference='synthetic:http', evidence_reference='synthetic:http', expires_at=timezone.now()+timedelta(hours=1))
        variant = ProductVariant.objects.create(name='Synthetic HTTP product two', product=fx.variant.product,
            unit=fx.unit, category='packing', created_by=fx.user, updated_by=fx.user)
        data = fx.data(True); data['lines'].append({**copy.deepcopy(data['lines'][0]), 'variant':str(variant.pk)})
        protected = (LedgerTransaction, LedgerEntry, BalanceProjection, Inspection, QualityAuthorization, QualityPosting)
        before = [m.objects.count() for m in protected]
        node = shutil.which('node'); self.assertIsNotNone(node)
        env = dict(os.environ, ERP_LIVE_URL=self.live_server_url+'/api/v1',
            ERP_SYNTHETIC_INPUT=json.dumps({'data':data, 'warehouse':str(wh.pk)}))
        with override_settings(SETTINGS_MODULE='config.settings.test'):
            result = subprocess.run([node, 'scripts/check-rehearsal.mjs'], cwd=Path(__file__).resolve().parents[2]/'frontend',
                env=env, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout+'\n'+result.stderr)
        self.assertIn('LIVE ERP PASS', result.stdout)
        self.assertEqual([m.objects.count() for m in protected], before)
