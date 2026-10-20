import os
from pathlib import Path
import secrets
import subprocess
import sys
from unittest import TestCase


class DemoSettingsTests(TestCase):
    def test_deploy_checks_and_unsafe_configuration_refusals(self):
        env = dict(os.environ, DJANGO_SETTINGS_MODULE='config.settings.demo', APP_ENV='DEMO',
            DJANGO_SECRET_KEY=secrets.token_hex(32), JWT_SIGNING_KEY=secrets.token_hex(32),
            DEMO_EXECUTION_SECRET=secrets.token_hex(32), DEMO_INSTANCE_ID='a86034d2-a80b-4512-b55e-82505591915a',
            DEMO_DATABASE_NAME='navapack_demo_settingscheck', POSTGRES_DB='navapack_demo_settingscheck',
            DJANGO_DEBUG='false', DJANGO_ALLOWED_HOSTS='demo-api.example.invalid', POSTGRES_SSLMODE='verify-full',
            CORS_ALLOWED_ORIGINS='https://demo-ui.example.invalid', CSRF_TRUSTED_ORIGINS='https://demo-ui.example.invalid',
            TRUST_PROXY_HTTPS='true')
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run([sys.executable, 'manage.py', 'check', '--deploy', '--fail-level', 'WARNING'],
            cwd=root, env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        for changes in ({'APP_ENV':'PRODUCTION'}, {'POSTGRES_SSLMODE':'require'},
                        {'POSTGRES_DB':'production'}, {'DEMO_EXECUTION_SECRET':env['JWT_SIGNING_KEY']},
                        {'CORS_ALLOWED_ORIGINS':'http://demo-ui.example.invalid'}):
            invalid = subprocess.run([sys.executable,'-c','import django; django.setup()'], cwd=root,
                env=dict(env,**changes),capture_output=True,text=True,timeout=60)
            self.assertNotEqual(invalid.returncode,0)
