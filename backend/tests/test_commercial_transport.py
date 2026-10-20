"""Real TypeScript adapter to JWT/HTTP/PostgreSQL; no browser acceptance claim."""
import json
import os
from pathlib import Path
import shutil
import subprocess
from django.test import LiveServerTestCase, override_settings
from tests import test_commercial
from apps.inventory.ledger_models import LedgerTransaction, LedgerEntry, BalanceProjection


class CommercialTransportTests(LiveServerTestCase):
    def test_actual_frontend_adapter_against_disposable_backend(self):
        fixture = test_commercial.CommercialTests(); fixture.setUp()
        frontend = Path(__file__).resolve().parents[2] / 'frontend'
        node = shutil.which('node')
        self.assertIsNotNone(node, 'Node is required for real adapter acceptance.')
        env = dict(os.environ, PHASE4A_LIVE_URL=self.live_server_url+'/api/v1',
                   PHASE4A_SYNTHETIC_INPUT=json.dumps(fixture.data(True)))
        self.assertEqual(os.environ['DJANGO_SETTINGS_MODULE'], 'config.settings.test')
        # LiveServerTestCase's ALLOWED_HOSTS UserSettingsHolder resets this
        # metadata to None. Retain the genuine module, preserving every stamp gate.
        with override_settings(SETTINGS_MODULE='config.settings.test'):
            result = subprocess.run([node, 'scripts/check-commercial-api.mjs'], cwd=frontend, env=env,
                                    capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout+'\n'+result.stderr)
        self.assertIn('LIVE PASS', result.stdout)
        for model in (LedgerTransaction, LedgerEntry, BalanceProjection):
            self.assertEqual(model.objects.count(), 0)
