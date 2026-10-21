# Complete Render DEMO environment checklist

This is the checklist for `config.settings.render_demo`, not production or the
older strict `config.settings.demo` profile. Set all values together in the Render
backend service Environment panel. `.env.render.example` is a tracked template;
it is not automatically loaded. `base.py` only loads backend/.env if one exists,
without overriding environment values. Do not upload a real .env to Git.

## Required runtime values

These exact examples are illustrative, not existing resources. Replace service
domains, internal host, runtime credentials and approved instance identity.

```dotenv
DJANGO_SETTINGS_MODULE=config.settings.render_demo
APP_ENV=DEMO
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=navapack-demo-api.onrender.com
DJANGO_SECRET_KEY=replace-me-independent-random-at-least-50-character-django-secret
JWT_SIGNING_KEY=replace-me-independent-random-at-least-50-character-jwt-secret
DEMO_EXECUTION_SECRET=replace-me-third-independent-random-at-least-64-character-demo-secret
DEMO_INSTANCE_ID=a86034d2-a80b-4512-b55e-82505591915a
DEMO_DATABASE_NAME=navapack_demo_client_20261021
POSTGRES_DB=navapack_demo_client_20261021
POSTGRES_USER=navapack_demo_runtime
POSTGRES_PASSWORD=replace-me-runtime-role-password
POSTGRES_HOST=dpg-example-only-internal-host
POSTGRES_PORT=5432
POSTGRES_SSLMODE=require
CORS_ALLOWED_ORIGINS=https://navapack-demo.vercel.app
CSRF_TRUSTED_ORIGINS=https://navapack-demo.vercel.app
TRUST_PROXY_HTTPS=true
LOG_LEVEL=INFO
PYTHON_VERSION=3.12.12
```

Every `replace-me` secret is deliberately invalid. Generate three independent
random values in a protected operator terminal, separately, with
`python -c "import secrets; print(secrets.token_hex(32))"`. Never use the same
value for Django, JWT and demo execution. Keep the already stamped demo execution
secret and UUID; generating new ones for a stamped database causes a mismatch.
Use the actual restricted runtime user's password, not a newly generated value
that has not been assigned to the database role.

## Accepted values and defaults

- `DJANGO_SETTINGS_MODULE`: exact `config.settings.render_demo` for this service.
  WSGI otherwise defaults to strict production; demo services only allow the exact
  approved demo profiles. A typo fails module import.
- `APP_ENV`: required, exact uppercase `DEMO` after trimming.
- `DJANGO_SECRET_KEY`, `JWT_SIGNING_KEY`: required, at least 50 characters after
  trimming. Must differ. Use independent high-entropy values; deploy checks also
  reject obviously insecure Django keys.
- `DEMO_EXECUTION_SECRET`: required, at least 64 characters after trimming;
  different from both keys. Must match the database stamp's SHA-256 hash.
- `DEMO_INSTANCE_ID`: required, parseable UUID. Canonicalized to UUID text. Must
  match the approved immutable database stamp. The example UUID is synthetic.
- `DEMO_DATABASE_NAME`: required, matches `navapack_demo_[a-z0-9_]{8,48}` exactly.
  The suffix must have 8–48 lowercase letters, digits or underscores. No hyphens,
  spaces, uppercase or URL. Must equal `POSTGRES_DB` and actual current_database().
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`: required nonempty strings
  after trimming. DB must satisfy the identity rule; user must be the approved
  restricted login role. No owner credentials in the web service.
- Every value parsed by `required()` rejects a case-insensitive leading
  `change-me` or `replace-me`, even if long enough. Never use secret placeholders.
- `DJANGO_ALLOWED_HOSTS`: explicitly supplied nonempty comma-separated hostnames
  without wildcards. Use hostnames only, no scheme, path or port. The parser only
  checks explicit presence/nonempty list/no `*`; malformed hostname strings can
  pass import but cause HTTP DisallowedHost. Include every approved backend host
  used for requests and health probes.
- `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`: both required nonempty lists of
  comma-separated explicit HTTPS origins. Valid port allowed; credentials, `*`,
  any path (including trailing `/`), query and fragment rejected. Match the actual
  frontend scheme/domain/port. Multiple approved domains may be listed. HTTPS
  origins are required even though base settings alone allow HTTP.
- `DJANGO_DEBUG`: accepts case-insensitive true/false, but true is rejected in
  render_demo. Omission defaults false; explicitly set false for reviewed hosting.
  DEBUG stays false in base; values such as 0, 1, yes or surrounding spaces fail.
- `POSTGRES_HOST`: no settings assertion; defaults 127.0.0.1 if omitted. Therefore
  deployment must explicitly set the actual managed database direct hostname.
  An empty/incorrect host may import successfully but will fail connection.
- `POSTGRES_PORT`: integer 1–65535, default 5432. Empty/invalid/out-of-range fails.
- `POSTGRES_SSLMODE`: exact lowercase require, prefer or verify-full. Default
  require in render_demo. Require mandates encryption without full certificate
  identity verification; no custom CA is required. Prefer may fall back to
  plaintext and does not verify server identity; not the recommended setting.
  Verify-full needs a valid certificate trust configuration. Disable/allow/
  verify-ca/empty/uppercase values are rejected. Production remains verify-full.
- `TRUST_PROXY_HTTPS`: case-insensitive true/false, default false; no surrounding
  spaces. Set true only behind reviewed sanitizing HTTPS ingress. Waitress clears
  untrusted forwarded headers; the prepared command sets URL scheme explicitly.
- `LOG_LEVEL`: default INFO. Use standard uppercase DEBUG, INFO, WARNING, ERROR,
  CRITICAL (NOTSET also recognized by Python). Invalid level names can make
  django.setup() fail while configuring logging. INFO is recommended here.
- `PYTHON_VERSION=3.12.12`: Render build configuration, not a Django validator.
- `PORT`: Render-provided listening port, expanded by the shell in the Start
  Command. No Django settings validator reads it. Do not override with literal
  `$PORT`. A local manual invocation can use 10000 instead.
- `PYTHON_DOTENV_DISABLED=1`: optional python-dotenv switch to prevent local .env
  loading; used in offline tests. No .env file should be present on the service.

## Database identity is not a label

For the reported error, set DEMO_DATABASE_NAME to the ACTUAL isolated database
name, and set POSTGRES_DB to that same name. Do not set either to the service name,
host, username, connection URL or production database name. Do not rename an env
value to pretend an existing differently named database is approved. If Render
provisioned a name outside the permitted pattern, a new dedicated compliant demo
database requires separate approval/provisioning; the guard must stay intact.

Settings compare the two configured names before connecting. Runtime additionally
compares actual current_database(), current_user, immutable marker's name, UUID,
secret hash, runtime role and unexpired timestamp. A name match alone is not proof
of nonproduction isolation. Verify the host/credentials identify a separately
approved dedicated DEMO database; never reuse a production database with a
demo-looking name. No configured or hosted database was inspected or modified
for this audit.

## All remaining release prerequisites

- Repository/branch/commit includes config/settings/render_demo.py; Root Directory
  backend. Template selects main. Existing Render services need manual review;
  changing YAML locally does not update their settings.
- Build: `pip install -r requirements/production.txt && python scripts/check_render_demo.py`.
  This check uses dummy values to verify the artifact, not the real service env.
- Start: `waitress-serve --listen=0.0.0.0:$PORT --url-scheme=https config.wsgi:application`.
  Scheme flag assumes Render's HTTPS-only public ingress. No wildcard proxy trust.
- Health: `/api/v1/ready/`; `/api/v1/health/` only proves the process is running.
  Both are HTTPS-redirect exempt; ready returns 503 while schema/stamp is invalid.
- Approved database identity, backup and reviewed migration plan BEFORE applying
  migrations. Follow DEMO_DATABASE_MIGRATION_PLAN.md, not startup auto-migrate.
- Existing core_demoboundary table and immutable approved stamp required, with
  expiry in future (initial approval duration 1–90 days), exact UUID/secret/role.
- Runtime must have LOGIN, NOSUPERUSER, NOCREATEDB, NOCREATEROLE, NOBYPASSRLS,
  NOINHERIT, no role memberships, no database/public-schema/public-table ownership.
  Use explicit reviewed demo_runtime_grants.sql; default managed owner fails gate.
- Approved schema, grants, independent synthetic accounts and capabilities. Demo
  use is never inferred from an Admin role. Preserve all stock/QC/financial guards.
- Connectivity/firewall/direct endpoint/credentials/TLS verified against the actual
  approved DEMO target, plus post-provisioning deployment_diagnostics and real
  login/full journey smoke. Import/check alone does not test these prerequisites.
- No automatic customer communications, operational stock, real QC release, legal
  invoices or unresolved P4 policy activation.

Do not add DATABASE_URL expecting automatic parsing: this app reads POSTGRES_*
fields only. Do not set PGSSLROOTCERT/PGSSLMODE/PGSERVICE/PYTHONPATH from another
deployment without review; libpq/import environment can alter behavior. In
particular a stale CA path can break internal TLS. No custom CA is needed with
the recommended Render demo require mode. Gunicorn-specific variables are unused
by the native Waitress command. SYNTHETIC_LEDGER_ENABLED is not an env switch.

## Audit verification

Run from backend: `python scripts/check_render_demo.py`. It checks settings import,
Django deploy/system checks and both Waitress command imports using fresh synthetic
nonproduction credentials, with dotenv disabled and DB connections forbidden for
WSGI import. Production settings/business code remain unchanged. See final audit
results for executed commands and remaining hosted-verification gaps.

Executed for this audit (local Python 3.11, no hosted credentials or DB access):

```text
.venv/Scripts/python scripts/check_render_demo.py
.venv/Scripts/python -m unittest tests.test_render_environment_template -v
git diff --check
```

Offline settings/deploy checks and both Waitress imports passed. All 3 template
tests passed in 38.791 seconds: complete-template settings/WSGI import and deploy
check, omission of each of 12 mandatory fields, and 16 invalid format/cross-variable
configurations. The four secret placeholders were replaced only in the test
child environment with newly generated synthetic values. No secrets were printed.
Actual Render host/database/name/stamp/expiry/privileges and Python 3.12 runtime
were not verified. No backend regression or frontend build rerun was needed for
these documentation/template/offline-test changes; no runtime application code,
production security, migration or business permissions changed. Real env files
remain ignored; only the exact new example file is exempted from ignore rules.
