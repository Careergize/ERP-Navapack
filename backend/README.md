# Navapack backend — Phases 1, 2 and inventory configuration foundation

Phase 3A adds quantity-free warehouse/location/stock-identity APIs and scoped audit
history. No operational inventory posting is enabled and no real scopes are granted.
See [Phase 3A contracts and rollout gates](docs/PHASE3A_API.md). Inventory migrations
remain unapplied to the application database pending separate authorization.

Django/DRF foundation with PostgreSQL, email identity, JWT, server-managed capabilities,
append-only audit, transactional commands, master APIs, immutable specifications and
reviewed import staging. No domain posting or frontend
integration is implemented. The sibling frontend is preserved.

## Layout

```text
backend/
  config/                 environment, URLs, WSGI/ASGI
    settings/             base, development, test, production
  apps/
    accounts/             UUID users, roles, memberships, JWT, permissions
      migrations/         0001_initial
    core/                 errors, request IDs, logging, health, audit, commands
      migrations/         0001_initial, 0002_audit_append_only
  tests/                  API, security, PostgreSQL transaction/concurrency tests
  requirements/           base, development, production, exact lock
  docs/                   architecture, contracts, decisions and status
  manage.py
  .env.example
  AGENTS.md
```

The Git root is the parent Navapack-ERP directory, shared with frontend/. Backend
commands still run from this directory and deployment remains independent.
See [monorepo migration and deployment](../docs/MONOREPO_MIGRATION.md).

## Development setup (PowerShell, from backend)

Requires Python 3.11+ and PostgreSQL 16+. Use a supported patched Python/PostgreSQL
release in deployment. Installed versions are recorded in requirements/lock.txt.

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements/lock.txt
Copy-Item .env.example .env
```

Edit .env with two independent random secrets of at least 50 characters, database
credentials and explicit hosts/origins. Generate each secret locally with
`python -c "import secrets; print(secrets.token_urlsafe(64))"`.
The example is intentionally unusable until placeholders are replaced.
Shell environment variables take precedence over .env.

Create an empty PostgreSQL database `navapack` and its owning migration role using
your local database administration tooling. Configure POSTGRES_DB, POSTGRES_USER,
POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT and POSTGRES_SSLMODE. Development
defaults to port 5432 and SSL `prefer`. Tests create and destroy `test_<POSTGRES_DB>`:
use an isolated test database role with CREATEDB, never production credentials.

```powershell
.venv/Scripts/python manage.py migrate
.venv/Scripts/python manage.py createsuperuser
.venv/Scripts/python manage.py runserver 127.0.0.1:8000
.venv/Scripts/python manage.py check
.venv/Scripts/python manage.py makemigrations --check --dry-run
.venv/Scripts/python manage.py test tests --settings=config.settings.test --noinput
```

The test settings retain PostgreSQL and use a fast test-only password hasher. Production
and development use PBKDF2. Roles and memberships are provisioned through trusted
management tooling, with approved permission changes recorded by administrators.
No public registration, role-assignment API or Django admin site is exposed.

## API surface

- `GET /api/v1/health/`: public process liveness; no database query.
- `GET /api/v1/ready/`: public database/schema readiness; 503 on database failure or pending migrations.
- `POST /api/v1/auth/login/`: `{email,password}` → `{access,refresh,user}`.
- `POST /api/v1/auth/refresh/`: `{refresh}` → `{access,refresh}`; old refresh revoked.
- `GET /api/v1/auth/me/`: bearer access → current server identity, roles and capabilities.
- `POST /api/v1/auth/logout/`: bearer access + `{refresh}` → `{revoked:true}`.

Access expires after 5 minutes; refresh expires after 8 hours. Logout revokes the
submitted refresh token. Existing access JWTs remain usable until expiry; other
sessions are unaffected. Password changes and user deactivation block both access
and refresh. Account-wide immediate logout/session families are future decisions.
Do not log request bodies or Authorization headers. Responses containing credentials
must not be cached by the ingress or client.

## Production

Set `DJANGO_SETTINGS_MODULE=config.settings.production`, explicit
DJANGO_ALLOWED_HOSTS, independent secrets, `DJANGO_DEBUG=false`, HTTPS origins and
`POSTGRES_SSLMODE=verify-full`. Configure libpq's trusted root certificate (PGSSLROOTCERT)
and a matching database hostname. The application fails early on unsafe settings.
Terminate HTTPS at a trusted ingress; set TRUST_PROXY_HTTPS=true only if it strips
client forwarding headers and writes its own X-Forwarded-Proto. Preserve a trustworthy
REMOTE_ADDR at the ingress: authentication throttles deliberately ignore arbitrary
forwarded IP headers. Configure additional ingress rate/size limits.

```powershell
$env:DJANGO_SETTINGS_MODULE='config.settings.production'
.venv/Scripts/python manage.py check --deploy
.venv/Scripts/python manage.py migrate --noinput
.venv/Scripts/waitress-serve --listen=127.0.0.1:8000 config.wsgi:application
```

Use separate migration-owner and restricted runtime DB roles. Grant runtime only the
required DML, audit SELECT/INSERT, and no audit UPDATE/DELETE/TRUNCATE, schema ownership
or trigger-disable rights. The migration installs an UPDATE/DELETE blocker; it cannot
protect against a database owner or superuser. Backups and audit export/WORM retention,
monitoring, secret rotation and deployment authorization remain operational work.
Health probes must use HTTPS when SSL redirect is enabled.

Schedule `python manage.py flushexpiredtokens` with deployment operations. Expired
authentication throttle rows may be pruned after their window; no automatic audit or
idempotency deletion is provided until retention/retry policies are approved.

See [architecture](docs/ARCHITECTURE.md), [API conventions](docs/API_CONVENTIONS.md),
[auth and permissions](docs/AUTH_AND_PERMISSIONS.md), [frontend adapter proposal](docs/FRONTEND_ADAPTER.md),
[decisions](docs/DECISION_LOG.md) and [executed verification](docs/DEVELOPMENT_STATUS.md).

## Phase 2 masters and data foundation

Apply new forward migrations with the existing migration command; Phase 1 files are
unchanged. No master/role/demo data is seeded. Provision capabilities through trusted
server tooling after client authority decisions. See [implemented API/permission matrix](docs/PHASE2_API.md),
[schema](docs/DATABASE_SCHEMA.md), [frontend mapping](docs/FRONTEND_MAPPING.md),
[verification](docs/DEVELOPMENT_STATUS.md) and [Phase 3 decisions](docs/PHASE3_DEPENDENCIES.md).
The existing frontend customer adapter requires a separate UUID/version/retry update.


## Employee accounts and Master Admin

Phase 2 additionally provides protected employee profiles and authenticated Master Admin
administration APIs, role-policy review, status changes, reset initiation and audit history.
No real administrator or business role is seeded. Apply forward accounts migrations, then
follow the [trusted provisioning and employee API guide](docs/EMPLOYEE_ADMIN.md). Passwords
are prompted securely, never CLI arguments or API output. Bootstrap technical rights do
not grant arbitrary business capabilities. Independent recovery needs two authorized
Master Admins. The guide also specifies future Admin Dashboard screens; frontend unchanged.
