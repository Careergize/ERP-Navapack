# Navapack hosted DEMO deployment plan

Prepared 21 October 2026. Source baseline `5c61da5` (`integrated Navapack ERP system`).
No push, hosted database migration, resource provisioning or deployment is authorized
or performed by this work. Existing application database and operational gates remain unchanged.

## Architecture and exact service configuration

Vercel serves the existing React/Vite frontend. Render runs the existing Django API
using Gunicorn and a separate persistent Render Managed PostgreSQL DEMO database.
No Render-specific business logic. No combined/root package manager.

Suggested names are templates requiring approval, not existing resources:

- Render service: `navapack-demo-api`; Docker runtime; Dockerfile `backend/Dockerfile`;
  Docker context `backend`; health check `/api/v1/ready/`; auto-deploy **off**.
  Docker command: default image CMD, `sh scripts/start_web.sh`.
- Native Render alternative: Root Directory `backend`; build
  `pip install -r requirements/deploy.txt`; start `sh scripts/start_web.sh`;
  Python 3.11. No pre-deploy migration command.
- Gunicorn: `gunicorn config.wsgi:application --config gunicorn.conf.py`;
  bind `0.0.0.0:$PORT` (default 8000), 2 gthread workers × 2 threads, 60s timeout.
- Database: PostgreSQL **16 or newer**, dedicated name
  `navapack_demo_<approved_unique_suffix>` (suffix 8–48 lowercase letters/digits/underscores),
  dedicated migration owner and separate `NOINHERIT` runtime login with no role memberships,
  no DB/schema/table ownership or administrative attributes. Region/tier/cost require approval.
- Vercel: Framework **Vite**, Root Directory **frontend**, Install `npm ci`,
  Build `npm run build`, Output **dist**, supported Node **22**.
  Keep existing `frontend/vercel.json` SPA rewrite. Use a separate demo project/domain;
  coordinate existing production Root Directory migration before touching an existing project.
- Vercel environment (demo project's Production and approved Preview scopes only):
  `VITE_API_BASE_URL=https://<approved-demo-api-host>/api/v1`,
  `VITE_ENABLE_MOCK_LOGIN=false`. These are public build-time values; rebuild after changes.
  Set `VITE_HOSTED_DEMO=true` to activate build-time rejection of missing/HTTP API
  URLs, wrong API paths, embedded credentials and mock login.

`render.demo.yaml` is a prepared Blueprint template, not a deployed service. Importing
it can create billable resources and requires separate approval. It intentionally does
not create a database, seed data, apply migrations or deploy automatically on Git pushes.
Set Blueprint **Auto Sync to No** as well: service auto-deploy off does not substitute
for controlling Blueprint configuration sync. Both changes require separate approval.

## Independent persistent-demo boundary

`config.settings.demo` inherits production HTTPS/TLS/security settings and additionally
requires APP_ENV=DEMO, exact database identity, unique instance UUID and independent
execution secret. A trusted owner stamps `core_demoboundary` only after separate
migration/backup/target approval. The immutable stamp binds database name, instance,
secret hash, runtime role and expiry (maximum 90 days). Both Python and PostgreSQL
validate the boundary. Runtime must not own the database, public schema or tables,
inherit roles or have superuser/CREATEDB/CREATEROLE/BYPASSRLS powers.

Only commercial draft/proposal and production rehearsal triggers gain a separate
DEMO branch. Original synthetic trigger bodies remain the fallback, and
`apps/inventory/ledger_guard.py` is unchanged. No `navapack.ledger_nonce` is installed
by the persistent demo gate. Operational stock/QC services and ledger database guards
remain test-only. No P4 policy is activated; all invoices/dispatch are simulations.

## Release order — manual approval required before steps that write hosted state

1. Review source/diff, exact image/dependency versions, domains, tier/cost, region,
   owner/runtime separation and backup storage. Authorize Git commit/push separately.
2. Authorize creation of dedicated resources. Do not reuse any operational database.
3. Verify external PostgreSQL hostname and certificate chain using verify-full;
   Render internal self-signed endpoint is not compatible with this strict policy.
4. Follow `DEMO_DATABASE_MIGRATION_PLAN.md`: backup, inspect exact forward plan, clone
   rehearsal, approve hash, migrate as owner, provision restricted runtime grants,
   stamp boundary and seed. Do not give owner credentials to the web service.
5. Deploy backend with runtime credentials; startup fails on missing schema, wrong
   stamp/role/expiry. No automatic migrate/seed during build/start.
6. Build Vercel frontend using approved HTTPS API URL and mock login false. Set
   exact frontend HTTPS origins on API CORS/CSRF lists, no wildcards.
7. Run `DEMO_ACCEPTANCE_CHECKLIST.md`, including real JWT, full journey, refresh,
   concurrent edits, no stock/QC posting, health, backup and restore checks.

## Seed/reset and expiry

`seed_demo` runs only as the approved operator/owner against the explicit DEMO target.
It uses independent passwords from protected files, creates synthetic example.invalid
actors with explicit capabilities (no Admin bypass), scoped independent actors and
two products. It seeds linked costing → quotation → order, completed simulated
production/fail/reinspection/dispatch, an interactive order job and a stock-origin job.
Business commands execute under the restricted runtime role inside the transaction.
Repeating a generation is a no-op; no password or history is overwritten.

Logical reset: approve a new generation, call `seed_demo` with new protected passwords
and `--retire-previous-generations`. Previous synthetic accounts are deactivated and
their immutable evidence remains. No truncation, audit deletion or operational cleanup.
Physical reset/secret rotation/expiry renewal uses a **fresh separately approved
database** and identity. Old stamps cannot be edited. Back up and retain old evidence.

## Startup/health and troubleshooting

- `/api/v1/health/`: process liveness; `/api/v1/ready/`: schema and DEMO identity/role
  readiness. Public probe endpoints are the only HTTPS redirect exemptions and expose
  no credentials or dataset. Authentication and application endpoints require HTTPS.
- `python manage.py deployment_diagnostics`: read-only schema/boundary diagnostics.
  It never migrates, seeds or grants permissions.
- 503/startup refusal: compare actual DB identity, settings module, stamp, secret,
  expiry, runtime flags/ownership, migration head and TLS trust. Do not disable guards.
- CORS error: ensure API URL ends `/api/v1`, exact HTTPS frontend origin is allowed,
  frontend rebuilt after environment changes, and JWT login is real.
- 403: check explicit employee capability, ownership, warehouse scope and demo identity.
  An Admin label never authorizes a command. Operational inventory/QC 403 is expected.
- 412: reload latest version; retain entered fields, inspect history and retry changed
  intent with a new key. Network retries of unchanged intent reuse their key.
- TLS error: verify approved external host and CA bundle, never change verify-full to
  require/disable. Trust proxy headers only when Render ingress strips untrusted copies.
- 5xx: correlate request IDs in JSON logs; do not enable DEBUG or log tokens/bodies.

## Implemented / tested / prepared / deployed

Implemented: demo gate/migration, restricted grants template, controlled commands,
seed/reset generation, Gunicorn/Docker/startup, health integration and backup/restore tools.
Prepared: Render/Vercel values, manual release sequence and AWS migration guidance.
Deployed: **nothing**. No hosted endpoint exists in this task and no hosted smoke test
can be claimed. Docker Linux daemon was unavailable here; image build/runtime is a
release gate. Executed test results are recorded in `DEMO_ACCEPTANCE_CHECKLIST.md`.

Official references: [Render Django](https://render.com/docs/deploy-django),
[Docker](https://render.com/docs/docker),
[PostgreSQL connections](https://render.com/docs/postgresql-creating-connecting),
[Vercel Vite](https://vercel.com/docs/frameworks/frontend/vite).


Temporary Render native Python deployment: see [Render demo setup](RENDER_DEMO_SETUP.md).
Its explicit render_demo profile uses required TLS without a custom CA; the strict
demo/production and recovery profiles retain their original TLS policies.
