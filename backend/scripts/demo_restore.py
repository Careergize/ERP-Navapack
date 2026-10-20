"""Restore only into an explicitly approved empty alternate DEMO database.

Identity stamps restored from another database deliberately fail closed. Restore
validation is not activation or authorization of that restored database.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import psycopg


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--database', required=True)
    p.add_argument('--backup', required=True)
    p.add_argument('--sha256', required=True)
    p.add_argument('--approval-reference', required=True)
    p.add_argument('--pg-restore', default='pg_restore')
    args = p.parse_args()
    backup = Path(args.backup)
    manifest = json.loads(Path(str(backup)+'.json').read_text())
    if (os.getenv('APP_ENV') != 'DEMO' or os.getenv('DJANGO_SETTINGS_MODULE') != 'config.settings.demo'
            or os.getenv('DEMO_DATABASE_NAME') != args.database or os.getenv('POSTGRES_DB') != args.database
            or not re.fullmatch(r'navapack_demo_[a-z0-9_]{8,48}', args.database)
            or args.database == manifest['source_database'] or manifest.get('environment') != 'DEMO'
            or args.sha256 != manifest['sha256'] or hashlib.sha256(backup.read_bytes()).hexdigest() != args.sha256
            or not args.approval_reference or os.getenv('POSTGRES_SSLMODE') != 'verify-full'):
        p.error('Approved alternate DEMO target, exact verified backup hash and certificate-verified TLS required.')
    env = dict(os.environ, PGDATABASE=args.database, PGHOST=os.environ['POSTGRES_HOST'],
        PGPORT=os.getenv('POSTGRES_PORT','5432'), PGUSER=os.environ['POSTGRES_USER'],
        PGPASSWORD=os.environ['POSTGRES_PASSWORD'], PGSSLMODE='verify-full')
    with psycopg.connect(dbname=args.database, host=env['PGHOST'], port=env['PGPORT'], user=env['PGUSER'],
                         password=env['PGPASSWORD'], sslmode='verify-full') as db:
        if db.execute('SELECT count(*) FROM pg_tables WHERE schemaname=%s', ['public']).fetchone()[0]:
            p.error('Restore target must be empty. No overwrite/clean/drop option is supported.')
    result = subprocess.run([args.pg_restore,'--exit-on-error','--no-owner','--no-privileges','--dbname',args.database,str(backup)],
                            env=env, capture_output=True)
    if result.returncode:
        raise SystemExit('Restore failed. Preserve partial alternate database; no automatic destructive cleanup.')
    print('Restored into alternate DEMO database; identity mismatch keeps execution disabled pending separate review.')


if __name__ == '__main__': main()
