# Temporary Render demo profile

Prepared locally; no hosted service, environment, database or migration changed.
Production settings and the disposable synthetic ledger gate are unchanged.
This profile supersedes the strict certificate requirement in the original Render
instructions only. All original identity, approval, backup and privilege gates apply.

## Render configuration

- Runtime: Python (native; Docker is optional and not used by this template).
- Root Directory: `backend`.
- Python: `PYTHON_VERSION=3.12.12`.
- Build: `pip install -r requirements/production.txt` (includes Waitress).
- Start: `waitress-serve --listen=0.0.0.0:$PORT --url-scheme=https config.wsgi:application`.
- Settings: `DJANGO_SETTINGS_MODULE=config.settings.render_demo`.
- Health check: `/api/v1/ready/` (503 until migration and demo stamp are ready).
- Auto-deploy: off. No migration, seed or grant runs in the build/start command.

Set `APP_ENV=DEMO`, `DJANGO_DEBUG=false`, `TRUST_PROXY_HTTPS=true`, exact
`DJANGO_ALLOWED_HOSTS` without scheme, and explicit HTTPS frontend origins in
`CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS`. Only trust the proxy header
behind Render's trusted HTTPS ingress. Waitress strips untrusted forwarding headers;
`--url-scheme=https` is required here to avoid HTTPS redirect loops after Render
terminates TLS. Use this command only behind the HTTPS-only Render ingress.
No wildcard proxy trust is enabled and forwarded client IPs remain untrusted.
Keep separate random Django/JWT secrets (at least 50 characters each) and a third
independent `DEMO_EXECUTION_SECRET` (at least 64 characters). No mock authentication.

Set individual `POSTGRES_HOST`, `POSTGRES_PORT=5432`, `POSTGRES_DB`,
`POSTGRES_USER`, `POSTGRES_PASSWORD` from the dedicated approved DEMO database.
Use the direct internal endpoint in the same region, not a transaction pooler.
`DATABASE_URL` is not consumed by these settings. Database name must match
`navapack_demo_[a-z0-9_]{8,48}` and `DEMO_DATABASE_NAME`; configure the approved
`DEMO_INSTANCE_ID`. Do not point at a production database or use its credentials.

## Temporary TLS boundary

Set `POSTGRES_SSLMODE=require` (also the new profile's default).
Render documents that internal PostgreSQL supports this mode. Encryption is
required, but full certificate identity verification is not provided. A custom CA
is not required; remove inherited `PGSSLROOTCERT` file settings
when using the internal self-signed endpoint. This profile does not strip libpq
CA environment settings silently; an explicitly configured CA can change libpq
verification behavior.

Explicit `POSTGRES_SSLMODE=prefer` is accepted for provider compatibility only:
it does not verify the server certificate and may allow an unencrypted connection.
There is no automatic fallback from require. `disable`, `allow` and unknown modes
are rejected. `verify-full` remains available with the appropriate certificate.
`production.py` and the existing strict `demo.py` still require verify-full.

Sources: [Render internal SSL modes](https://render.com/docs/postgresql-creating-connecting),
[Render Python version](https://render.com/docs/python-version).

## Activation and verification

Follow `DEMO_DATABASE_MIGRATION_PLAN.md` for the reviewed migration hash,
approved backup/reference, dedicated migration owner, immutable boundary stamp,
restricted NOINHERIT runtime role and explicit grants. These commands now accept
both exact demo profiles. Use render_demo for each process; never change the
underlying stamp/security policy. Hosted changes still require separate approval.

Runtime must pass `python manage.py check --deploy --fail-level WARNING` and
`python manage.py deployment_diagnostics` as manual preflight after provisioning.
The exact requested Waitress command runs no provisioning; readiness performs
schema and restricted DEMO boundary validation before traffic is declared ready.
Keep the migration owner credentials out of runtime service environment variables.

Seed and export tools work under render_demo with the same guards. The separate
restore tool deliberately retains its original strict `config.settings.demo` and
verify-full recovery policy: restore into a separately reviewed empty recovery
target through a certificate-verified endpoint. It is not an internal-TLS bypass.
All invoices/documents remain previews; no stock, QC or finance authority is added.

## Local verification

See the current task results below. Local Python is 3.11; Python 3.12.12 on Render
and actual internal managed PostgreSQL TLS require hosted verification after approval.

Executed from backend:

```text
.venv/Scripts/python scripts/test_isolated.py --synthetic-ledger tests.test_render_demo tests.test_demo_settings tests.test_demo_environment
.venv/Scripts/python manage.py check --settings=config.settings.test
.venv/Scripts/python manage.py makemigrations --check --dry-run --settings=config.settings.test
```

All four focused tests passed in a freshly generated disposable PostgreSQL database.
Both strict and Render DEMO profiles passed the complete existing clone scenario:
seed, JWT/relogin, concurrency, stock isolation, expiry/secret/identity guards,
backup/restore and logical reset. Settings subprocesses passed Django deploy checks
and rejected unsafe settings; production still rejected sslmode=require.
Django checks passed and migration drift reported no changes. Waitress 3.0.2 HTTPS
scheme option was validated locally. No frontend source changed or frontend checks
rerun. Full backend regression was not rerun for this bounded settings change.

The first settings test was affected by the local .env and failed safely on its
SSL mode; the rerun disables dotenv for configuration-default assertions. The
local .env was not edited. Final log: backend/.local/render-demo-tests.log (ignored).
No hosted migrations/deployments or commits were performed.
