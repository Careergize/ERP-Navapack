"""Read-only protected DEMO export. Use PostgreSQL client >= source server major."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.demo')
import django
django.setup()
from django.conf import settings
from apps.core.demo import require_demo_environment


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--database', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--pg-dump', default='pg_dump')
    args = p.parse_args()
    require_demo_environment()
    if args.database != settings.DEMO_DATABASE_NAME:
        p.error('Explicit target does not match the approved DEMO database.')
    output = Path(args.output)
    # Claim the output exclusively; never overwrite an existing backup.
    with output.open('xb'):
        pass
    output.chmod(0o600)
    c = settings.DATABASES['default']
    env = dict(os.environ, PGHOST=c['HOST'], PGPORT=str(c['PORT']), PGUSER=c['USER'], PGPASSWORD=c['PASSWORD'],
        PGDATABASE=args.database, PGSSLMODE=c['OPTIONS']['sslmode'])
    try:
        result = subprocess.run([args.pg_dump, '--format=custom', '--no-owner', '--no-privileges', '--file', str(output)],
                                env=env, capture_output=True)
        if result.returncode:
            raise SystemExit('Export failed; retain the partial file for investigation. No database was modified.')
        manifest = {'environment':'DEMO', 'source_database':args.database, 'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
                    'instance':settings.DEMO_INSTANCE_ID, 'operational_authority':False}
        metadata = Path(str(output)+'.json')
        with metadata.open('x') as stream:
            json.dump(manifest, stream, indent=2)
        metadata.chmod(0o600)
        print(json.dumps(manifest))
    finally:
        # Never delete/export into another database, and never print credentials.
        pass


if __name__ == '__main__': main()
