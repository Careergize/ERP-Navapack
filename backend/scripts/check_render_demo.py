"""Offline Render artifact check: dummy configuration, no database or server startup."""
import os
from pathlib import Path
import secrets
import subprocess
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    if not (root / 'config/settings/render_demo.py').is_file():
        raise SystemExit('Missing config/settings/render_demo.py: verify deployed Git revision and backend root.')
    # Child-only environment; never load .env or contact a configured database.
    env = {key: value for key, value in os.environ.items()
           if key.upper() in ('PATH', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP', 'LD_LIBRARY_PATH')}
    env.update(
        PYTHON_DOTENV_DISABLED='1', DJANGO_SETTINGS_MODULE='config.settings.render_demo',
        APP_ENV='DEMO', DJANGO_DEBUG='false', DJANGO_ALLOWED_HOSTS='demo-api.example.invalid',
        DJANGO_SECRET_KEY=secrets.token_hex(32), JWT_SIGNING_KEY=secrets.token_hex(32),
        DEMO_EXECUTION_SECRET=secrets.token_hex(32),
        DEMO_INSTANCE_ID='a86034d2-a80b-4512-b55e-82505591915a',
        DEMO_DATABASE_NAME='navapack_demo_importcheck', POSTGRES_DB='navapack_demo_importcheck',
        POSTGRES_USER='offline_demo_check', POSTGRES_PASSWORD=secrets.token_hex(24),
        POSTGRES_HOST='database.example.invalid', POSTGRES_PORT='5432', POSTGRES_SSLMODE='require',
        CORS_ALLOWED_ORIGINS='https://demo-ui.example.invalid',
        CSRF_TRUSTED_ORIGINS='https://demo-ui.example.invalid', TRUST_PROXY_HTTPS='true',
    )
    commands = [
        [sys.executable, 'manage.py', 'check', '--deploy', '--fail-level', 'WARNING'],
        [sys.executable, '-c', '''
from waitress.runner import run
from django.db.backends.base.base import BaseDatabaseWrapper

def no_database(*args, **kwargs):
    raise AssertionError('Offline import check attempted a database connection')

BaseDatabaseWrapper.ensure_connection = no_database
seen = []
def inspect(application, **options):
    assert callable(application)
    assert options['listen'].strip() == '0.0.0.0:10000'
    seen.append(application)

for flags in ([], ['--url-scheme=https']):
    assert run(['waitress-serve', '--listen=0.0.0.0:10000', *flags,
                'config.wsgi:application'], _serve=inspect) == 0
assert len(seen) == 2
from django.conf import settings
assert settings.SETTINGS_MODULE == 'config.settings.render_demo'
assert settings.DATABASES['default']['OPTIONS']['sslmode'] == 'require'
assert not settings.DEBUG and not settings.SYNTHETIC_LEDGER_ENABLED
import config.settings.render_demo as profile
print('Settings artifact:', profile.__file__)
print('Both Waitress command variants imported config.wsgi:application; no server or database started.')
'''],
    ]
    for command in commands:
        subprocess.run(command, cwd=root, env=env, check=True, timeout=60)
    print('Offline Render deployment import check passed.')


if __name__ == '__main__':
    main()
