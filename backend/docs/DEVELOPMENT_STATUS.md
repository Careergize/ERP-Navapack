# Development status — 15 October 2026

## Implemented Phase 1

Existing empty backend sibling now contains config/settings, apps/accounts,
apps/core, tests, requirements and documentation. Django 5.2.18, DRF 3.17.2,
Simple JWT 5.5.1, psycopg 3.3.6, django-cors-headers 4.9.0, django-filter 25.2,
python-dotenv 1.2.4 and Waitress 3.0.2 installed into backend/.venv. Full exact
dependency resolution is recorded in requirements/lock.txt. No global Python
environment was modified.

Implemented email/UUID identity, multiple server-managed role memberships, action/object
permission hooks, independent-actor checks, JWT rotation/revocation, database-backed auth
throttling, request IDs, JSON logging/errors, pagination/filter defaults, health/readiness,
append-only audit and transactional idempotency/version helpers. Frontend remains unchanged.

Endpoints: GET /api/v1/health/, GET /api/v1/ready/, POST /api/v1/auth/login/,
POST /api/v1/auth/refresh/, GET /api/v1/auth/me/, POST /api/v1/auth/logout/.
No public registration, business endpoints, demo accounts or authority matrix seeded.

## Migrations and executed verification

Created and successfully applied to isolated local PostgreSQL 16.3:

- accounts/0001_initial: custom User, Role, Membership and identity constraints.
- core/0001_initial: AuditEvent, IdempotencyRecord, ThrottleWindow and constraints/indexes.
- core/0002_audit_append_only: PostgreSQL function/trigger rejecting audit UPDATE/DELETE.
- Required upstream auth/contenttypes/sessions/Simple JWT blacklist migrations also applied.

Executed backend verification:

- `python manage.py test tests --settings=config.settings.test --noinput -v 1`:
  **35 tests passed** against PostgreSQL, including actual concurrent connections.
- Authentication success/failure, identity, active/inactive/password-change behavior,
  refresh rotation/reuse, token ownership/logout, unauthenticated access and throttling.
- Permission denial, role capability/object hooks, no-self-approval including superusers,
  case-insensitive email uniqueness and production password hashing.
- Audit creation, ORM/raw SQL immutability, safe summaries, operation/audit rollback.
- Idempotent replay, hash conflicts, stale versions and authorization recheck on replay.
- Invalid command keys and unsuccessful-result retention rejection.
- Concurrent identical commands, conflicting payloads, distinct-key stale versions and
  simultaneous refresh rotations each have exactly one permitted successful mutation.
- Health/readiness, database failure, CORS, safe internal errors and request IDs.
- Configuration validation, valid production profile and ten unsafe production cases.
- `python manage.py check`: no issues. `makemigrations --check --dry-run`: no changes.
- `pip check`: no broken requirements.
- `check --deploy` with explicit production hosts/HTTPS origins/TLS configuration:
  no issues. This validates the settings profile, not a deployed ingress/certificate.

Executed frontend verification without modifying its source:

- `node ./node_modules/typescript/bin/tsc --noEmit`: passed.
- Vite production build into backend/.local/frontend-build: passed (1,712 modules).
  Existing >500 kB chunk warning remains; output directory outside frontend is intentional.
- All nine scripts/check-*.mjs passed: finished-goods, inventory-workflows, job-cards,
  custom-costing, sales-fulfillment, quality, quotations, integrated-operations, led-finance.
- Final frontend Git status remained clean, matching the initial status.

No SQLite substitution, live frontend integration, browser acceptance, remote service,
stock/approval/QC/dispatch domain concurrency test or production deployment was performed.
Foundation tests do not certify future domain invariants or SOP compliance.

## Local verification artifacts

The preinstalled PostgreSQL binaries were used to create a disposable cluster under
backend/.local/postgres, listening only on 127.0.0.1:55432 during verification. Database
navapack and local role navapack_local use randomly generated credentials in ignored .env.
The isolated local role is a cluster owner solely for test/migration verification; it is
not a production runtime role. No existing PostgreSQL service/database was modified.
Test database test_navapack was created and destroyed by Django. Logs/build artifacts are
ignored under .local. The disposable server is stopped after verification.

To reuse this workstation cluster (with the installed binaries), run from backend:

```powershell
& 'C:/Program Files/PostgreSQL/16/bin/pg_ctl.exe' -D "$PWD/.local/postgres" -l "$PWD/.local/postgres.log" -o '-h 127.0.0.1 -p 55432' start
# Run manage.py commands using the ignored local .env.
& 'C:/Program Files/PostgreSQL/16/bin/pg_ctl.exe' -D "$PWD/.local/postgres" -m fast stop
```

Fresh environments should follow README.md and .env.example with their own PostgreSQL
database/credentials; no credentials are part of the deliverable files.

## Remaining gates and Phase 2

Approve tenancy, role/action/object authority, independence rules, token storage and
revocation breadth, production ingress/TLS/secrets/DB grants, audit/idempotency retention
and operational recovery/monitoring. The monorepo migration includes backend under
the shared parent Git root; CI hosting and production deployment remain operational
decisions. See [migration and deployment](../../docs/MONOREPO_MIGRATION.md).
No production readiness is claimed.

Recommended Phase 2: governed masters and import staging with approved source IDs,
variant/unit reconciliation, provenance and unknown-opening preservation. Obtain missing
controlled SOPs and references before subsequent stock, QC and operational posting.
See DECISION_LOG.md and FRONTEND_ADAPTER.md for pending decisions and separate integration.
