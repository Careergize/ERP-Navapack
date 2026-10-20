"""Render settings validation plus the existing full PostgreSQL boundary scenario."""
import os
from pathlib import Path
import secrets
import subprocess
import sys
from unittest import TestCase
from tests import test_demo_environment


class RenderDemoBoundaryTests(test_demo_environment.PersistentDemoTests):
    demo_settings_module = 'config.settings.render_demo'


class RenderDemoSettingsTests(TestCase):
    def test_tls_defaults_and_security_refusals(self):
        env = dict(os.environ, DJANGO_SETTINGS_MODULE='config.settings.render_demo', APP_ENV='DEMO',
            DJANGO_SECRET_KEY=secrets.token_hex(32), JWT_SIGNING_KEY=secrets.token_hex(32),
            DEMO_EXECUTION_SECRET=secrets.token_hex(32), DEMO_INSTANCE_ID='a86034d2-a80b-4512-b55e-82505591915a',
            DEMO_DATABASE_NAME='navapack_demo_settingscheck', POSTGRES_DB='navapack_demo_settingscheck',
            DJANGO_DEBUG='false', DJANGO_ALLOWED_HOSTS='demo-api.example.invalid',
            CORS_ALLOWED_ORIGINS='https://demo-ui.example.invalid', CSRF_TRUSTED_ORIGINS='https://demo-ui.example.invalid',
            TRUST_PROXY_HTTPS='true', PYTHON_DOTENV_DISABLED='1')
        env.pop('POSTGRES_SSLMODE', None)
        env.pop('PGSSLROOTCERT', None)
        root = Path(__file__).resolve().parents[1]
        for mode in (None, 'require', 'prefer', 'verify-full'):
            selected = dict(env)
            if mode:
                selected['POSTGRES_SSLMODE'] = mode
            code = ("import django; django.setup(); from django.conf import settings; "
                    "assert settings.DATABASES['default']['OPTIONS']['sslmode'] == " + repr(mode or 'require') +
                    "; assert not settings.DEBUG; assert not settings.SYNTHETIC_LEDGER_ENABLED")
            result = subprocess.run([sys.executable, '-c', code], cwd=root, env=selected,
                capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        result = subprocess.run([sys.executable, 'manage.py', 'check', '--deploy', '--fail-level', 'WARNING'],
            cwd=root, env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for changes in ({'APP_ENV':'PRODUCTION'}, {'POSTGRES_SSLMODE':'disable'}, {'DJANGO_DEBUG':'true'},
                        {'DJANGO_ALLOWED_HOSTS':'*'}, {'POSTGRES_DB':'production'},
                        {'JWT_SIGNING_KEY':env['DJANGO_SECRET_KEY']}, {'DEMO_EXECUTION_SECRET':env['JWT_SIGNING_KEY']},
                        {'CORS_ALLOWED_ORIGINS':'http://demo-ui.example.invalid'}, {'CSRF_TRUSTED_ORIGINS':''},
                        {'DJANGO_SETTINGS_MODULE':'config.settings.production', 'POSTGRES_SSLMODE':'require'}):
            result = subprocess.run([sys.executable, '-c', 'import django; django.setup()'], cwd=root,
                env=dict(env, **changes), capture_output=True, text=True, timeout=60)
            self.assertNotEqual(result.returncode, 0, str(changes))
