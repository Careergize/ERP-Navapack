# Client originals reviewed — 20 October 2026

All 18 SOP DOCX documents, both original client stock workbooks and eight JPEG
references under client-reference/ have now been reviewed. Treat these originals as
authoritative client source material; older source-unavailability notes below and in
historical audits describe an earlier review. See
[verified requirements and remaining decisions](../../docs/CLIENT_SOURCE_REVIEW.md)
and [source hash manifest](../../docs/CLIENT_SOURCE_MANIFEST.json).

SOPs 01–17 state v1.0 and SOP 18 v1.1, all effective 1 November 2026. Confirm cutover,
actual delegated authority/memberships and dispatch-point independence. Original
workbooks still need unit, period, formula, identity and physical reconciliation;
unknowns remain unknown and no opening quantity is approved by their availability.
No Phase 3 implementation or automatic permission/stock import was performed.

# Phase 2.1 remediation — 20 October 2026

Canonical import review history/applied plans, safe UUID/User-FK resolution, explicit
nullable process-stage validation and governed role-capability proposals/publication
are implemented. Forward migrations only; no frontend source changes or Phase 3 work.
Verification: 128-test full PostgreSQL suite passed (93 existing + 35 regressions),
expanded focused checks and frontend noEmit/build/all 12 scripts passed as recorded
in ../../docs/PHASE_2_1_REMEDIATION_REPORT.md. Migration drift/system checks passed;
application DB has not been migrated. Phase 3 and integrated release remain NO-GO
pending reviewed reproducible release and client SOP/authority/source decisions.
See ../../docs/PHASE_2_1_REMEDIATION_REPORT.md for final test evidence and decision;
PHASE21_FRONTEND_CONTRACT_PLAN.md and ../../docs/PHASE_2_RELEASE_PLAN.md describe open
integration/release gates. Existing historical status entries follow; this section
supersedes their pre-remediation capability-editor/import-review limitations.

# Employee accounts extension — 20 October 2026

## Implemented

Phase 2 now extends accounts with Employee profiles linked one-to-one to User,
server-controlled Master Admin designation, explicit RoleAssignmentPolicy,
RoleChangeRequest and EmployeeResetRequest. Protected UUID references, immutable human
employee IDs, current server capabilities, scoped targets, delegation ceilings,
independent approval where configured, access reset safeguards and full significant-event
audit reuse Phase 1 identity/JWT/commands. No business roles/permissions or real employees seeded.

New trusted commands: provision_master_admin (secure password prompt; technical rights
only), configure_employee_role (explicit policy for existing reviewed role; no grants),
complete_employee_password_reset (different authorized administrator, verified identity,
current employee version; no token/email/credential output). Master Admin status cannot
be granted through API, role code or superuser status alone. Self and privileged targets
are excluded from API mutations. No public registration or generic permission editor.

Employee create/edit/status/reset, role list/assignment/removal/independent approval/
cancellation, permission visibility and administrative audit reads are implemented under
/api/v1/. Pending changes are distinct from effective memberships. Deactivation changes
the unusable password fingerprint, so old JWTs remain invalid after reactivation. Existing
JWTs resolve changed memberships on later requests. Request IDs and safe role references
are audited without passwords/tokens/PII snapshots. See EMPLOYEE_ADMIN.md for exact contracts,
permission matrix, command instructions, frontend screens/integration and operational limits.

## New migrations and executed verification

Forward accounts migrations applied on the isolated local PostgreSQL 16.3 cluster:

- 0002_user_is_master_admin_employee_employeeresetrequest_and_more: flag and employee/
  policy/change/reset schema; depends on existing accounts/0001 and Phase 2 masters/0002.
- 0003_employeeresetrequest_one_pending_employee_reset_and_more: unique pending requests,
  positive reset precondition, evidence and independent-actor database checks.

No existing migration was replaced or modified. Phase 1 authentication views, backend,
permission helpers and core audit/command implementation are unchanged. User output gains
read-only is_master_admin; no client authority is accepted from it. No new dependencies.

From backend with .venv/Scripts/python:

- manage.py migrate --noinput: both new accounts migrations applied successfully.
- manage.py check: no issues.
- manage.py makemigrations --check --dry-run: no changes detected (connected PostgreSQL run).
- manage.py test tests --settings=config.settings.test --noinput -v 1:
  **93 tests passed in 121.525 seconds**, real PostgreSQL, disposable database created/destroyed.
  Includes all 35 Phase 1 tests, 31 earlier Phase 2 tests and 27 employee-administration tests.
- New coverage: secure/weak/duplicate provisioning and rollback; one-to-one/unique identity;
  unapproved/unauthenticated/superuser-only denial; forbidden privilege/password/user inputs;
  self and privileged-target denial; reporting cycles; profile editing; directory filters,
  search/pagination; role-policy setup/current digest/ceiling/reserved permissions; multi-role
  assignment; independent grants/removals including superuser self-approval denial and
  database invariants; existing-JWT role changes; inactive-account revocation; access/refresh/
  login invalidation across deactivation/reactivation; reset initiation/independent completion/
  stale-target and target ceiling; retry authority checks; audit/object scoping; concurrent
  approvals; malformed IDs; atomic User/profile/membership/audit rollback.
- Expected injected audit failures returned safe internal errors and rolled back; no unexpected
  failures remain. The first employee run's UUID-vs-rendered-JSON assertion was corrected.

From frontend, unchanged source:

- node ./node_modules/typescript/bin/tsc --noEmit: passed.
- node ./node_modules/vite/bin/vite.js build --outDir ../backend/.local/employee-frontend-build:
  passed, 1720 modules. Existing chunk-size and intentional external-output warnings remain.
- All 12 scripts/check-*.mjs passed: auth, custom-costing, customers, finished-goods,
  integrated-operations, inventory-workflows, job-cards, led-finance, quality,
  quotation-persistence, quotations and sales-fulfillment.

Repository verification: git diff --check passed; frontend and all existing migration files
unchanged; core diff empty. No staging/commits/pushes/deployment changes. Test logs/builds
remain ignored under backend/.local. The isolated test cluster was stopped afterward.

## Outstanding gates

No production administrator was created. Supply approved human identifiers/Department UUID
and strong prompted credentials through trusted provisioning. Client business role contents,
per-role independence, named administrators/business delegation ceilings, recovery delivery/
verification/expiry, privileged-account maintenance, privacy/tenant scope and MFA/SSO remain
client/operational decisions. Independent recovery needs two authorized Master Admins.
No stock/domain posting or original-source/SOP compliance claims added. Frontend Admin
Dashboard is specified only; no frontend components or Context providers were changed.

---

Earlier Phase 2 and Phase 1 implementation/verification history follows.

# Phase 2 development status — 20 October 2026

## Implemented and verified

New apps masters, specifications and imports provide Customer, Prospect, Supplier,
Department, Unit, Product, ProductVariant, Material, Consumable, Machine, Area,
ProductModel, ProductModelRevision, RecipeLine, ProcessCostLine, ModelRouteStage,
ImportBatch and ImportRow. UUID identities, source mapping, protected actor/FK references,
constraints/indexes, transactional audit, capability checks and versioned idempotent
writes reuse Phase 1 infrastructure. No seed data, role grants or inventory postings.

Implemented REST collections and commands are detailed in PHASE2_API.md, including
permission matrix, field contracts, allowed filters and safe import workflow. Sealed
specifications and import evidence have PostgreSQL mutation guards. Review/import
approval applies only master metadata, never stock observations or opening transactions.
See DATABASE_SCHEMA.md, FRONTEND_MAPPING.md and PHASE3_DEPENDENCIES.md.

New forward migrations applied successfully on isolated local PostgreSQL 16.3:

- masters: 0001_initial; 0002 master lookup/filter indexes.
- specifications: 0001_initial; 0002 decimal checks; 0003 immutable revision triggers;
  0004 route instructions/legacy label/kinds; 0005 model name index.
- imports: 0001_initial; 0002 source-evidence guards; 0003 staged-row insert guard;
  0004 status/target indexes.

No accounts/core/Phase 1 migration was modified. No dependency install was needed.

## Executed checks

From backend using backend/.venv/Scripts/python and the ignored local PostgreSQL config:

- `manage.py migrate --noinput`: all new migrations applied successfully.
- `manage.py check`: no issues.
- `manage.py makemigrations --check --dry-run`: no changes detected.
- `manage.py test tests --settings=config.settings.test --noinput -v 1`:
  **66 tests passed in 69.544 seconds**, real PostgreSQL; disposable test database
  created/destroyed. All 35 retained Phase 1 tests plus 31 new Phase 2 tests.
- New coverage: each master resource create/update, uniqueness/source pairs, actor and
  target capabilities, inactive actors/references, stale/missing preconditions, strict
  field validation, unit/variant identity, pagination/filter/search/order, explicit
  prospect promotion/retry, configurable route/process linkage, revision numbering,
  protected historical headers/children, import column/unit/source/duplicate/demo
  validation, reviewed mapping application, explicit updates/stale targets, evidence
  immutability, same-key and competing-key concurrent approvals, audit and rollback.
- Synthetic CSV/XLSX reader fixtures only; no claim of testing unavailable client originals.
- Expected injected audit/internal failures produced safe 500 responses in rollback tests;
  the final suite has no unexpected failures. Earlier validation defects were corrected
  before this final full run.

From frontend, unchanged source:

- `node ./node_modules/typescript/bin/tsc --noEmit`: passed.
- `node ./node_modules/vite/bin/vite.js build --outDir ../backend/.local/phase2-frontend-build`:
  passed, 1720 modules. Existing >500 kB chunk warning; ignored external output directory
  warning. No browser or production deployment performed.
- All **12** `scripts/check-*.mjs` passed: check-auth, check-custom-costing, check-customers, check-finished-goods, check-integrated-operations, check-inventory-workflows, check-job-cards, check-led-finance, check-quality, check-quotation-persistence, check-quotations, check-sales-fulfillment.

The isolated local PostgreSQL cluster started for verification was stopped afterward.

Repository checks: `git diff --check` passed; frontend, accounts and core Git diffs
empty. Source files and existing client references preserved. Logs/builds remain ignored
under backend/.local. No staging, commits, pushes, deployment settings or remote changes.

## Limits and handoff

Current catalog scope is explicitly shared/global behind capabilities; company/tenant
isolation is not implemented. Approval authority/maker-checker and source authenticity
require client decisions. Original workbooks/SOPs/QC photos unavailable; no original
source import, SOP compliance or production readiness claimed. Import binary storage
is external; DB stores parsed cells/hash/provenance and latest review, with audit history.

The existing frontend customer adapter expects numeric db IDs, body creation_key and
unversioned PATCH; it requires a separately scoped UUID/retry/version adapter update.
Frontend was not modified and is not certified integrated with these master APIs.
No opening balance, movement, Sales Order, Job Card, production run, QC release,
dispatch, invoice or costing computation was added. Phase 3 remains separately scoped.

---

The following retained section records the original Phase 1 verification/history.

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
