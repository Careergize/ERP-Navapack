"""Verify the complete Render template and startup configuration refusals offline."""
import os
from pathlib import Path
import secrets
import subprocess
import sys
from unittest import TestCase


class RenderEnvironmentTemplateTests(TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        self.env = {key: value for key, value in os.environ.items()
                    if key.upper() in ('PATH', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP', 'LD_LIBRARY_PATH')}
        for line in (self.root / '.env.render.example').read_text().splitlines():
            if line.strip() and not line.lstrip().startswith('#'):
                name, value = line.split('=', 1)
                self.env[name] = value
        for name in ('DJANGO_SECRET_KEY', 'JWT_SIGNING_KEY', 'DEMO_EXECUTION_SECRET', 'POSTGRES_PASSWORD'):
            self.env[name] = secrets.token_hex(32)
        self.env['PYTHON_DOTENV_DISABLED'] = '1'

    def run_python(self, env):
        return subprocess.run([sys.executable, '-c',
            'import django; django.setup(); import config.wsgi; assert callable(config.wsgi.application)'],
            cwd=self.root, env=env, capture_output=True, text=True, timeout=60)

    def test_complete_template_import_and_deploy_check(self):
        result = self.run_python(self.env)
        self.assertEqual(result.returncode, 0, result.stderr)
        result = subprocess.run([sys.executable, 'manage.py', 'check', '--deploy', '--fail-level', 'WARNING'],
            cwd=self.root, env=self.env, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_all_mandatory_fields_fail_when_omitted(self):
        for name in ('DJANGO_SECRET_KEY', 'JWT_SIGNING_KEY', 'POSTGRES_DB', 'POSTGRES_USER',
                     'POSTGRES_PASSWORD', 'DJANGO_ALLOWED_HOSTS', 'APP_ENV', 'DEMO_DATABASE_NAME',
                     'DEMO_INSTANCE_ID', 'DEMO_EXECUTION_SECRET', 'CORS_ALLOWED_ORIGINS',
                     'CSRF_TRUSTED_ORIGINS'):
            with self.subTest(field=name):
                env = dict(self.env)
                del env[name]
                self.assertNotEqual(self.run_python(env).returncode, 0)

    def test_cross_variable_and_format_refusals(self):
        cases = [
            {'DEMO_DATABASE_NAME': 'navapack_demo_different'},
            {'POSTGRES_DB': 'production'},
            {'POSTGRES_DB': 'navapack-demo-client', 'DEMO_DATABASE_NAME': 'navapack-demo-client'},
            {'APP_ENV': 'PRODUCTION'}, {'DEMO_INSTANCE_ID': 'not-a-uuid'},
            {'JWT_SIGNING_KEY': self.env['DJANGO_SECRET_KEY']},
            {'DEMO_EXECUTION_SECRET': self.env['JWT_SIGNING_KEY']},
            {'DEMO_EXECUTION_SECRET': 'too-short'}, {'DJANGO_DEBUG': 'true'},
            {'DJANGO_ALLOWED_HOSTS': '*'}, {'POSTGRES_PORT': '65536'},
            {'POSTGRES_SSLMODE': 'disable'}, {'CORS_ALLOWED_ORIGINS': 'http://demo.example.invalid'},
            {'CSRF_TRUSTED_ORIGINS': 'https://demo.example.invalid/'},
            {'TRUST_PROXY_HTTPS': 'yes'}, {'LOG_LEVEL': 'INVALID'},
        ]
        for index, changes in enumerate(cases):
            with self.subTest(case=index):
                self.assertNotEqual(self.run_python(dict(self.env, **changes)).returncode, 0)
