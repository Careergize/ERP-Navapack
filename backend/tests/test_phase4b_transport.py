import json
import os
from pathlib import Path
import shutil
import subprocess
from django.test import LiveServerTestCase, override_settings
from apps.specifications.models import ProductModel, ProductModelRevision
from apps.masters.models import ProductVariant
from apps.inventory.ledger_models import LedgerTransaction, LedgerEntry, BalanceProjection
from tests import test_commercial


def setup_fixture():
    fx = test_commercial.CommercialTests(); fx.setUp()
    fx.user.name = 'Synthetic commercial employee'; fx.user.save(update_fields=['name'])
    fx.other.name = 'Synthetic other owner'; fx.other.save(update_fields=['name'])
    model = ProductModel.objects.create(name='Synthetic model', created_by=fx.user, updated_by=fx.user)
    revision = ProductModelRevision.objects.create(model=model, number=1, name='Synthetic sealed specification', specifications='Synthetic specification',
        default_unit=fx.unit, recipe_mode='quantities', sealed=True, created_by=fx.user)
    variant = ProductVariant.objects.create(name='Synthetic second product', product=fx.variant.product, unit=fx.unit, category='packing', created_by=fx.user, updated_by=fx.user)
    return fx, revision, variant


class Phase4BTransportTests(LiveServerTestCase):
    def test_real_react_adapter_and_lossless_editor(self):
        fx, revision, variant = setup_fixture()
        env = dict(os.environ, PHASE4B_LIVE_URL=self.live_server_url+'/api/v1', PHASE4B_SYNTHETIC_INPUT=json.dumps(fx.data(True)),
                   PHASE4B_MODEL_REVISION=str(revision.pk), PHASE4B_SECOND_VARIANT=str(variant.pk))
        self.assertEqual(os.environ['DJANGO_SETTINGS_MODULE'], 'config.settings.test')
        with override_settings(SETTINGS_MODULE='config.settings.test'):
            result = subprocess.run([shutil.which('node'), 'scripts/check-commercial-hardening.mjs'], cwd=Path(__file__).resolve().parents[2]/'frontend',
                                    env=env, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout+'\n'+result.stderr)
        self.assertIn('LIVE PHASE4B PASS', result.stdout)
        for model in (LedgerTransaction, LedgerEntry, BalanceProjection): self.assertEqual(model.objects.count(), 0)
