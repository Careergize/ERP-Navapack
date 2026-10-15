import os
from pathlib import Path
import subprocess
import sys
from django.test import SimpleTestCase


class ProductionConfigurationTests(SimpleTestCase):
    def load(self, **changes):
        env = os.environ.copy()
        env.update({
            'DJANGO_SECRET_KEY': 'test-django-independent-secret-' * 4,
            'JWT_SIGNING_KEY': 'test-jwt-independent-secret-' * 4,
            'POSTGRES_DB': 'test_config', 'POSTGRES_USER': 'test_config',
            'POSTGRES_PASSWORD': 'test-config-only', 'POSTGRES_PORT': '5432',
            'POSTGRES_SSLMODE': 'verify-full', 'DJANGO_DEBUG': 'false',
            'DJANGO_ALLOWED_HOSTS': 'erp.example.com', 'TRUST_PROXY_HTTPS': 'false',
            'CORS_ALLOWED_ORIGINS': 'https://erp.example.com',
            'CSRF_TRUSTED_ORIGINS': 'https://erp.example.com',
        })
        env.update(changes)
        return subprocess.run([sys.executable, '-c', 'import config.settings.production'],
                              cwd=Path(__file__).resolve().parents[1], env=env,
                              capture_output=True, text=True, timeout=15)

    def test_valid_production_settings_load(self):
        result = self.load()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_unsafe_production_settings_fail_early(self):
        for change in (
            {'DJANGO_DEBUG': 'true'}, {'DJANGO_DEBUG': 'yes'},
            {'DJANGO_ALLOWED_HOSTS': '*'}, {'DJANGO_ALLOWED_HOSTS': ''},
            {'POSTGRES_SSLMODE': 'require'}, {'POSTGRES_PORT': 'invalid'},
            {'DJANGO_SECRET_KEY': 'short'},
            {'JWT_SIGNING_KEY': 'test-django-independent-secret-' * 4},
            {'CORS_ALLOWED_ORIGINS': 'http://erp.example.com'},
            {'CSRF_TRUSTED_ORIGINS': 'https://erp.example.com/path'},
        ):
            with self.subTest(change=next(iter(change))):
                result = self.load(**change)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('ImproperlyConfigured', result.stderr)
