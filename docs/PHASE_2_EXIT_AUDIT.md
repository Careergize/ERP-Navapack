# Navapack ERP — Phase 2 Exit Audit / Phase 3 Readiness

20 October 2026. Repository: `F:\WORK\Navapack-ERP`.
Audited HEAD: `800dd00ba2f103c440130c8ae597ad0c4d8dc283`, branch `main`, **plus the pre-existing uncommitted/untracked working tree**.

## 1. Executive summary

**Final decision: NO-GO for Phase 3 implementation at this exit gate. Phase 2 is substantially implemented, but is not ready for complete signoff.**

The backend contains real PostgreSQL authentication, commands, masters, immutable specifications, import staging and guarded employee administration. All **93 existing Django tests passed**. Frontend TypeScript checks, build and all 12 focused scripts passed.

Additional audit probes nevertheless reproduced **four backend API defects**, a limitation in out-of-band role-capability change control, and a frontend/backend authentication mismatch. The most serious defect permits import approval to apply a different Product UUID from the one shown in the persisted review. Seven probes finished with **six failed safety/integration expectations and one expected denial**; this is distinct from the green existing suite.

RBAC exists at the permission-resolution and governed membership-assignment layers. A complete Master Admin workflow for configuring role capabilities does not. Original controlled SOPs and stock workbooks were unavailable in the repository source tree. Inventory policy, authority and source reconciliation remain unresolved. Much of Phase 2 is untracked/uncommitted, so HEAD alone does not reproduce this implementation.

**Audit boundary:** no application code, migration, existing document, Git setting or application data was changed. Only this requested report and ignored verification artifacts were created. Tests used synthetic fixtures in fresh, uniquely named disposable PostgreSQL databases. No production database, external service or deployment was changed. No Phase 3 implementation or corrective code was started.

## 2. Implemented feature inventory

Statuses describe actual evidence, not roadmap promises. A tested feature can still have uncovered defects; see section 3.

### Implemented and tested

- **Identity/authentication:** UUID User, normalized case-insensitive unique email, hashing/validation, active checks, login/current-user/logout, JWT refresh rotation, blacklist/reuse and ownership checks, password fingerprint and concurrent single-success rotation. Logout revokes the supplied refresh, not every unexpired access token/session.
- **PostgreSQL/commands:** PostgreSQL-only settings and actual concurrent connections; atomic execution, canonical payload hashes, actor/action/scope/key uniqueness, replay authorization, row/version locks, retained successful results, 409 payload conflicts, 428 missing preconditions and 412 stale versions.
- **Audit:** protected actor/request/version references, append-only ORM and PostgreSQL UPDATE/DELETE guards, safe summaries and rollback on audit failure. This does not protect against DBA/table-owner privileges or privileged TRUNCATE.
- **Authorization:** server role/direct/group capabilities, active actors, explicit action maps, independent-actor checks including superusers, object hooks and explicit shared-catalog scope. This is not company/warehouse tenant isolation.
- **Customer/Prospect:** separate UUIDs, party metadata, explicit promotion/linkage, locking and idempotent retries; no automatic name-based merge.
- **Supplier/Department/Unit:** descriptive supplier fields, manager text distinct from optional account FK, governed unit dimension/code, unique nonblank codes/source pairs. No inferred unit aliases or conversions.
- **Product/ProductVariant:** distinct generic versus exact finished-good identities, protected FKs, source metadata, optional positive pieces and controlled unit/parent identity. Names/descriptions are not unique identity keys.
- **Material/Consumable:** raw category/family or spare category, Unit FK, activity and nullable nonnegative minimum levels; no inventory totals/openings/movements.
- **Machine/Area:** equipment classification and department/area references. Area is not a warehouse; no guessed settings are seeded.
- **ProductModel/revisions/lines/routes:** parent-locked revision numbering, exact material units, recipe/route uniqueness, numeric checks, configurable order, local process-stage linkage, reference snapshots and PostgreSQL protection of sealed headers/children. The nullable process-stage case is defective (F6).
- **Resource APIs:** actual list/detail/create/PATCH resources, standard pagination, search/filter/order allowlists, capabilities, strict input, significant-event audit and activation metadata. Coverage is not exhaustive for every resource/field combination.
- **Employee administration:** one-to-one profiles, employee ID/email uniqueness, department/designation/manager cycles, trusted provisioning, ordinary account creation/editing, status commands, multi-role changes, configured independent approval, resets and audit reads. Details in section 4.

### Partially implemented

- **Import pipeline:** bounded CSV/data-only XLSX, digest/filename/sheet/row/raw evidence, explicit mappings/decisions, duplicate candidates, review, authorized atomic application and retries exist. Reviewed identity preservation fails (F1); importing a User FK fails (F5).
- **Specification readiness:** sealing provides immutability, not approved production readiness. Empty specification recipes/routes are permitted. Checkpoint IDs are provisional JSON strings, not QC-template FKs.
- **Error handling:** safe envelopes exist, but several boundary cases return unexpected 500 responses (F5–F7).
- **RBAC administration:** effective permission resolution and governed assignments are real; managed capability editing is incomplete (F2).
- **Frontend integration:** mapping documents and some adapters exist; actual authentication/master contracts disagree (F3). Session-only simulation is not backend persistence.

### Implemented but untested at the required boundary

- Real client workbook normalization/interpretation: tests use synthetic CSV/XLSX, not unavailable original merged/formula workbooks.
- Comprehensive hostile-file/resource-limit behavior: macro/XML/size guards exist, but the suite does not exercise all parser attack/limit combinations.
- An approved restricted production DB role, deployed ingress/TLS and browser-to-live-Django acceptance were not verified. These cannot be inferred from configuration or unit tests.

### Not implemented

Backend inventory ledger, warehouses/bins, lots/batches/genealogy, receipts/issues/consumption/returns, reservations, QC holds/releases, stock projections, opening reconciliation and stock corrections. Employee Admin Dashboard, role-capability editing workflow, public/emailed recovery and MFA/SSO are also absent. These omissions must not be concealed by frontend screens or planning documents.

### Blocked by client decision

Controlled SOP/authority matrix, role-capability contents, independence/approval rules, scope/privacy, real source mappings, exact units/conversions/precision, openings, negative/unknown/backdated stock policy, QC authority, recovery/retention and operational security. No values or limits were invented.

## 3. Missing or incomplete features and concrete findings

P1 = close before the relevant exit/release gate. P2 = fix functional/validation behavior before authoritative use. No remote unauthenticated privilege takeover was demonstrated; trusted out-of-band mutation is explicitly identified.

### F1 — P1: approval can apply a foreign identity different from review

Evidence: `backend/apps/imports/views.py:66–70,169–170,192–203`; probe `test_01_reviewed_foreign_key_must_not_rebind`.

Review saves resolved UUIDs in `batch.review`. Approval discards its proposed values, runs `preview` again from raw columns and resolves current master codes. Reference identities/versions are not bound to the reviewed plan.

Reproduction through authenticated APIs in a disposable database:

1. Create Product A with code `PROD-1` and a governed unit.
2. Stage a finished-good row referencing `PROD-1`; review proposes Product A's UUID.
3. PATCH A's code to `PROD-OLD` with its current version; create Product B with `PROD-1`.
4. Approve the unchanged reviewed import batch with the correct batch version.
5. **Actual: HTTP 200; the new variant references B while the persisted review proposes A.**

Approval therefore does not prove which identity was authorized. Batch locking/idempotency does not close this gap. Before authoritative import/stock use, approve a canonical normalized plan containing resolved IDs, target/reference versions and relevant candidate identities; reject drift and require review again. Retain the actually applied plan and add concurrent reference-change regressions. A prior boolean duplicate acknowledgment must not silently approve changed candidates.

### F2 — P1 scope/change-control gap: role-capability administration is incomplete

Evidence: `backend/apps/accounts/employee_views.py:202–209`, `management/commands/configure_employee_role.py:12–35`, `backends.py:20–25`, `employee_services.py:56–100`; probes 05/06.

Role-to-Permission M2M and multi-role resolution exist. `GET /roles/` is read-only; Master Admin POST returns 403. There is no API or dedicated audited workflow to create/edit permitted role capabilities. The trusted policy command accepts an existing role and independence choice, and explicitly grants no capabilities.

A probe configured an independent policy and existing membership, then changed `Role.permissions` directly. The policy became stale, but the existing employee immediately acquired the added capability. Digest checks govern new assignment/approval, not runtime expansion of existing memberships. **This requires privileged/out-of-band mutation, not an exposed HTTP mutation.**

Decide between a versioned/audited/scoped capability-configuration workflow with approved independence rules, or an explicitly accepted restricted trusted-only boundary with controlled role definitions. Existing memberships must be addressed in change control. The full Admin Dashboard permission editor is not complete; no final business authority matrix may be guessed.

### F3 — P1 integration-release gap: frontend/auth/master contracts disagree

Evidence: `frontend/.env.example:1`, `src/lib/api.ts:6,13,30`, `src/context/AuthContext.tsx:32–34,84,104–105`, `src/lib/customersApi.ts:7,32,41,47`, `src/lib/unitsApi.ts:6,11`; backend accounts serializers.

- Default/example frontend base is `/api`, backend is `/api/v1`. An environment override is possible, but no matching checked-in default/proxy establishes integration.
- Frontend sends `username`; backend requires `email`. API probe: username body **400**, equivalent email body **200**.
- Frontend requires a singular known `role`; backend returns `roles[]`, `permissions[]`, `is_master_admin` and no singular role. Correcting only the request field is insufficient.
- Frontend logout clears browser state without calling backend refresh revocation.
- Customer adapter assumes numeric IDs/`db:\d+`, body `creation_key`, no retry/version headers and `active` rather than `is_active`. Backend uses UUIDs, Idempotency-Key, If-Match and rejects unknown `creation_key`. Unit DTO/filter assumptions also disagree.
- Most master/stock/model providers remain local/reference stores. Quotation draft/snapshot consumers reference routes absent from this backend.

These are integration gates, not proof the backend resources are absent: frontend changes were explicitly excluded from the implementation phase. Approve real session/DTO/UUID/header adapters and backend contract tests separately. Mocked scripts passing does not establish a functioning integrated ERP.

### F4 — P1 exit/reproducibility gap: Phase 2 is not a Git release boundary

Masters/specifications/imports, employee modules, migrations and tests are largely untracked; existing config/accounts/docs are modified. A fresh checkout of HEAD omits the audited additions. After approved fixes/review, establish a reproducible Phase 2 commit/release with its evidence before mixing in another phase. No staging/commit/push/history change is authorized by this report.

### F5 — P2: valid department import referencing User returns 500

Evidence: `backend/apps/imports/views.py:66–70`; probe 02. FK resolution first queries `related.objects.filter(code__iexact=value)` for every nonempty reference. `Department.manager` targets User, which has no `code`; a valid User UUID causes unhandled FieldError. **Actual: 500 internal_error.** Resolve UUIDs first and use only explicitly supported code identities; test mixed/User references.

### F6 — P2: nullable process-stage input returns 500

Evidence: `backend/apps/specifications/views.py:75,115–118`; probe 03. `stage: null` passes the truthiness check and remains in the line. Creation supplies `stage=...` again alongside `**line`, causing a duplicate-keyword failure. **Actual: 500**, instead of supported input or 400. The transaction rolls back. Define the write schema explicitly and test omitted/null/cross-revision linkage.

### F7 — P2: malformed master write UUID returns 500

Evidence: `backend/apps/masters/views.py:75–80`; probe 04. Authorized PATCH `/customers/not-a-uuid/` with required headers causes an unhandled Django UUID conversion error: **500**, not 400/404. Employee commands validate UUID syntax, generic masters do not. Audit similar promotion/revision/import command lookups; only the customer failure was dynamically confirmed.

### F8 — P2/decision gap: import evidence is not a full review archive

Raw cells/hash/provenance and latest review are retained; original binaries are external. Re-review replaces prior detailed mappings/decisions; audit proves events, not every prior preview body. One target per batch/global content-digest uniqueness also requires explicit preparation for mixed workbooks. These limits are disclosed in existing docs. Approve evidence/source retention and immutable review/applied-plan requirements. Blank raw openings are not reconciled typed balances.

## 4. Employee/RBAC verification

Actual backend routes and tests were checked, not frontend button visibility:

- Employee list/create/detail/PATCH: tested creation, identity uniqueness, editing, manager cycles, strict input and scope. Client passwords/User IDs/direct permissions/groups/privileged flags cannot be injected.
- Activate/deactivate: tested server status, access/refresh/login rejection and old-JWT rejection after reactivation. Password fingerprint changes; roles/history remain, and verified reset is needed to restore login.
- Role list: tested permission visibility. Capability editing is absent (F2).
- Assignment POST, membership DELETE and nested approval/cancel: tested multiple memberships, ceilings, missing/stale policy denial, independent grants/removals, superuser self-approval denial, cross-employee scope and concurrent single application. Pending removal retains access until approval; deactivation is immediate suspension. Inactive-account revocation is tested.
- Reset initiation/offline completion: tested metadata-only response, independent authorized completer, stale target and ceiling. No email, public token, recovery expiry or self-service delivery is implemented.
- Administrative audit GET: tested gate, pagination/employee filters and actual actor. Module actions are audited; arbitrary trusted role-permission edits are outside that workflow.
- Trusted provisioning: tested secure validated prompt, technical grants only, duplicates/weak passwords, no staff/superuser flags and rollback on audit failure. No live admin was provisioned by this audit.

Master Admin designation **and** an action capability are required. Superuser alone or a non-admin with accounts permissions is denied. Self/privileged targets cannot be mutated through the employee API. Directory scope is explicitly shared; department/manager names grant no authority. Bootstrap grants technical rights only; business delegation requires separate approved provisioning. Existing accounts are not automatically enrolled/promoted.

**Assessment: genuinely implemented RBAC engine and governed assignments; partially implemented configurable RBAC administration.** It is neither merely planned nor a complete capability-management product.

## 5. Master-data/API verification

Actual registrations: customers, prospects, suppliers, departments, units, products, finished-goods, raw-materials, consumables, machines, areas, models, model-revisions and imports. Commands implement promotion, revision creation and import review/application.

Verified model/serializer properties include UUIDs, versions, UTC timestamps, protected actor/domain FKs, required names, nonblank case-insensitive code uniqueness, exact complete source-pair uniqueness and no automatic name merge. Generic products/variants/materials remain separate. Customer text on a variant is not silently a Customer FK. Pieces does not imply mass.

New active references are validated under locks; unchanged inactive references may remain during metadata correction. Unit code/dimension, master unit and variant parent changes are API-restricted, not independently guarded by raw-SQL triggers on all master fields. Future transaction services must preserve these invariants.

Specifications use NUMERIC(20,6), distinct materials/route sequences, exact units and reference snapshots. Sealed headers/children have database guards. Sealing is not workflow approval; future transactions need exact protected revision UUIDs and relevant snapshots. QC checkpoint strings are not validated QC releases.

APIs use capability maps, pagination (25 default/100 maximum), search/filter/order allowlists and strict writes. No hard master DELETE, opening quantity update, stock ledger command or unrestricted approval-state CRUD was found.

Imports retain filename/sheet/row/raw/hash and detect candidate names/codes/source identities without merging automatically. Declared demo batches cannot apply; no reference/mock array is auto-imported. Source authenticity is still an authorized assertion pending originals. F1 prevents certifying identity-preserving reviewed application, despite passing existing import concurrency/retry tests.

## 6. SOP and client-decision gaps

Repository discovery included hidden/ignored source filenames, excluding Git internals, dependencies, local DB/build directories and history backups. No original PDF/DOCX/stock workbook was found. The SOP-named document found was `frontend/docs/backend-planning/SOP_FRONTEND_GAP_ANALYSIS.md`, explicitly recording missing originals. No off-repository archive, mailbox/shared drive or external connector was claimed reviewed.

The numbers/titles below identify the user's requested references, **not verified controlled document identities**:

- **SOP 01 — Authority and Internal Controls: blocked, original unavailable.** Need signed actor/action/object matrix, delegation, capability-change authority, independence, approval limits, privileged maintenance and audit retention. Technical controls were verified, not mapped to missing signed paragraphs.
- **SOP 03 — Stores and Inventory: blocked, original unavailable.** Need locations, units/conversions, lots, approved openings/as-of dates, unknown/negative/backdated policy, receipt/issue/return authority and adjustment reconciliation.
- **SOP 05 — Production Planning and Control: blocked, original unavailable.** Need specification/route readiness, plan approval, issue versus consumption, WIP, extra issues/returns, yield/loss and genealogy. Configurable routes do not establish a universal approved sequence.
- **SOP 11 — Quality Control: blocked, original unavailable.** Need original checklists/photos, sampling/tolerances, hold scope, conditional acceptance, release/concession/reinspection authority and separation of quality versus final stock authorization. Frontend transcriptions remain provisional.
- **SOP 15 — Dispatch and Delivery: blocked, original unavailable.** Need dispatch authority, QC/availability gates, lot selection, partial/reversal rules and delivery/transport evidence. Session simulation is not certified dispatch control.

Secondary evidence reviewed: actual frontend types/providers, authentication/master adapters, stock/reference files and extraction logic, quality integration, planning model/database/API blueprints, SOP gap notes, and backend architecture/decisions/contracts. Generated references name `09.FG Stock September .xlsx` and `08- September 2026  Daily Raw Material Physical stock  -.xlsx`; **neither original was available/opened/imported**. Prior notes refer to 18 SOPs and eight QC photographs; this audit cannot independently verify that register, versions or originals.

Verified technical behaviors—explicit identities, no inferred balances/conversions, configured independent review, immutable audit/specifications and transactions—are implementation facts, not SOP compliance certification. No approval limit, grade, supplier code, setting, balance or tolerance was invented.

## 7. Database and migration verification

Local verification used PostgreSQL **16.3**, loopback `127.0.0.1:55432`, the existing isolated workstation cluster. Its verification role has SUPERUSER/CREATEDB; this is **not a restricted production runtime role demonstration**.

- Standard check clean; no model drift/pending migrations. Read-only metadata counted **43 applied migrations**. Fresh test databases successfully built from the full working-tree migration graph.
- New graph includes accounts/0002–0003, masters/0001–0002, specifications/0001–0005 and imports/0001–0004; original Phase 1 files were unchanged.
- Eight enabled custom triggers were read from PostgreSQL: audit_no_mutation; immutable_import_batch; immutable_import_row; immutable_import_row_insert; immutable_revision; immutable_revision_line on three child tables.
- No migration was generated, edited, applied to the existing application database, reversed or faked. Test DB setup applied its own migrations only.
- Ledger, warehouse/bin, lot/batch, receipt/issue/return, reservation, QC hold/release, stock balance and opening reconciliation tables are absent. These are deferred models, not existing infrastructure.

Git/configuration findings:

- Actual origin is `https://github.com/Careergize/ERP-Navapack-frontend.git` for fetch/push. `docs/MONOREPO_MIGRATION.md` still names `https://github.com/Careergize/ERP-Navapack.git`; reconcile docs before publication. No cause for the difference is inferred and no remote was changed.
- Cached origin/main equals HEAD (0 ahead/0 behind); no fetch/current GitHub-state claim. Original frontend tip `5aa0687` is an ancestor (exit 0).
- Single repository root; no frontend/backend nested `.git` directories found. Independent application builds/dependencies are preserved. No root package manager introduced.
- `git diff --check` passed. Tracked path scan found no environment files, dependency/database/build trees, credential keys or history backups. Ignore checks confirmed expected sensitive/generated paths. This is not a full historical secret scan.
- SHA-256 baseline of **257 existing nonignored repository files** verified source/migration/existing-doc preservation. The only new nonignored deliverable is this report; harness/log/build outputs are ignored.
- Much of Phase 2 is untracked/uncommitted (F4), so migrations working locally does not prove a committed deployment can reproduce them.

## 8. Test evidence and exact commands

### Backend checks — working directory backend

```powershell
& 'C:/Program Files/PostgreSQL/16/bin/pg_ctl.exe' -D "$PWD/.local/postgres" -l "$PWD/.local/postgres.log" -o '-h 127.0.0.1 -p 55432' start
.venv/Scripts/python manage.py check
.venv/Scripts/python manage.py makemigrations --check --dry-run
.venv/Scripts/python manage.py migrate --check
.venv/Scripts/python manage.py showmigrations --plan
.venv/Scripts/python -m pip check
.venv/Scripts/python manage.py check --deploy
```

Results: cluster started; check clean; no drift; no pending migrations; plan all applied; **No broken requirements found**. Development deploy check exited successfully with **four warnings: security.W004, W008, W012, W016** for HSTS, HTTPS redirect and secure session/CSRF cookies. Those warnings are not a production-security pass.

A separate process checked synthetic production settings; random secrets existed only in memory and were never printed:

```powershell
@'
import os,secrets
os.environ.update(DJANGO_ALLOWED_HOSTS='erp.audit.example.invalid',DJANGO_DEBUG='false',DJANGO_SECRET_KEY=secrets.token_urlsafe(64),JWT_SIGNING_KEY=secrets.token_urlsafe(64),POSTGRES_SSLMODE='verify-full',CORS_ALLOWED_ORIGINS='https://erp.audit.example.invalid',CSRF_TRUSTED_ORIGINS='https://erp.audit.example.invalid')
from django.core.management import execute_from_command_line
execute_from_command_line(['manage.py','check','--deploy','--settings=config.settings.production'])
'@ | .venv/Scripts/python -
```

Result: **no issues**. This checks the settings profile, not deployed ingress/certificates/TLS/DB grants. No external vulnerability scan or penetration test was performed.

### Existing Django suite — working directory backend

The normal command was invoked through call_command with only a unique test DB name override, avoiding reuse/destruction of any existing test_navapack database:

```powershell
$env:LOG_LEVEL='ERROR'
@'
import os, uuid, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings.test')
django.setup()
from django.conf import settings
from django.db import connection
from django.core.management import call_command
config=settings.DATABASES['default']
assert config['HOST']=='127.0.0.1' and str(config['PORT'])=='55432'
name='test_exit_audit_20261020_'+uuid.uuid4().hex[:10]
with connection.cursor() as cursor:
    cursor.execute('SELECT 1 FROM pg_database WHERE datname=%s',[name])
    assert cursor.fetchone() is None
config['TEST']['NAME']=name
print('DISPOSABLE_TEST_DATABASE='+name,flush=True)
call_command('test','tests',interactive=False,verbosity=1)
'@ | .venv/Scripts/python - *> .local/phase2-exit-audit-tests.log
```

**93 tests passed in 117.374 seconds; exit 0.** Includes 35 Phase 1, 31 initial Phase 2 and 27 employee tests with actual PostgreSQL concurrency. `test_exit_audit_20261020_f98986db85` was created/destroyed by the runner. Expected injected rollback/internal-error messages are asserted behavior, not suite failures.

### Additional audit-only probes — working directory backend

```powershell
$env:LOG_LEVEL='ERROR'
.venv/Scripts/python .local/phase2-exit-audit-probes.py *> .local/phase2-exit-audit-probes.log
```

The ignored harness checks loopback/port and absence of its random DB before creating it. Final execution: **7 probes, 6 failed expectations, 1 passed, 9.625 seconds; exit 1**. `test_exit_audit_probes_20261020_59228356` was destroyed afterward. An earlier six-probe run independently reproduced the first five findings. Initial harness import-path setup failed before DB connection and was corrected only in the harness; no application correction occurred.

Exact probe results:

1. `test_01_reviewed_foreign_key_must_not_rebind`: FAIL — approval 200, actual product differs from persisted review (F1).
2. `test_02_department_import_accepts_user_uuid_reference`: FAIL — valid User FK returns 500 (F5).
3. `test_03_null_process_stage_is_not_an_internal_error`: FAIL — nullable stage returns 500 (F6).
4. `test_04_malformed_master_write_identity_is_not_internal_error`: FAIL — bad customer UUID returns 500 (F7).
5. `test_05_stale_role_policy_does_not_silently_expand_existing_access`: FAIL — privileged permission edit expands existing membership while policy stale (F2; not an HTTP mutation exploit).
6. `test_06_role_permission_configuration_has_no_write_api`: PASS — Master Admin POST roles returns 403 and creates no role; confirms missing capability-edit workflow (F2).
7. `test_07_frontend_login_payload_does_not_match_backend_contract`: FAIL — username payload 400, email payload 200, successful response lacks singular role (F3).

These probes were not added to/replaced in the repository suite. Their permanent regression-test adoption belongs to a separately approved fix scope. Harness/logs remain ignored local artifacts; this report records their scenarios/results.

### Frontend — working directory frontend

```powershell
node --version
npm --version
node ./node_modules/typescript/bin/tsc --noEmit
node ./node_modules/typescript/bin/tsc -b
node ./node_modules/vite/bin/vite.js build --outDir ../backend/.local/phase2-exit-audit-build
Get-ChildItem scripts/check-*.mjs | ForEach-Object { & node $_.FullName; if ($LASTEXITCODE -ne 0) { throw "Failed: $($_.Name)" } }
```

Node **v24.14.0**, npm **11.9.0**; both TypeScript commands passed. Vite built **1,720 modules**, exit 0; existing >500 kB chunk and intentional outside-root output warnings remain. These are the package build steps with output redirected to ignored verification artifacts, not a deployment.

All **12** scripts passed: check-auth, check-custom-costing, check-customers, check-finished-goods, check-integrated-operations, check-inventory-workflows, check-job-cards, check-led-finance, check-quality, check-quotation-persistence, check-quotations and check-sales-fulfillment (all .mjs). Some mock Axios/backend responses or simulate browser state. Their success does not establish real Django contract compatibility. No browser-to-live-backend acceptance run was claimed.

### Repository and cleanup evidence

Read-only Git commands included status/porcelain, branch, remote -v, log -5, rev-parse HEAD/root, rev-list HEAD...origin/main, merge-base --is-ancestor 5aa0687 HEAD, configuration reads, ls-files, check-ignore and diff --check. `rg --files`/`rg -n` discovered source/evidence; SHA-256 comparisons checked preservation. No staging, configuration changes, commits or ref changes were performed.

After verification, the cluster started for this audit is stopped with:

```powershell
& 'C:/Program Files/PostgreSQL/16/bin/pg_ctl.exe' -D "$PWD/.local/postgres" -m fast stop
```

Only fresh disposable test databases were created/destroyed; no flush, destructive query or migration was run against the existing application database.

## 9. Critical blockers and Phase 3 prerequisites

Exit blockers are F1 reviewed/applied identity drift, unresolved F2 capability administration/change control, F4 reproducible release state, and missing approved inventory/SOP/authority/source decisions. F3 blocks integrated frontend release; it need not prohibit isolated design discussion. F5–F7 prevent a clean functional Phase 2 signoff.

UUIDs, protected masters/units/revisions, audit and commands can support separate future inventory apps without rewriting Phase 1. They do not already implement these domain guarantees:

- **Immutable inventory ledger — Not implemented.** Need typed stock identity, location/lot/unit, signed append-only entries, unique source event, actor/time, reversal links and projection reconciliation. Do not store independently writable stock totals on masters.
- **Raw receipts/issues — Not implemented; policy blocked.** Need supplier/source/lot identity, receipt acceptance/hold status, authorized issue destination, exact units, cumulative caps and atomic posting.
- **Finished receipts/dispatches — Not implemented; policy blocked.** Exact variant IDs exist; documents, lot/QC/stock authorization, partial/reversal rules, applicable reservations/order links and double-post prevention do not.
- **Lot/batch traceability — Not implemented.** Need scoped batch uniqueness, supplier/manufacturing genealogy, input/output allocations and protected typed references. Free-text frontend batch labels are insufficient.
- **QC holds/releases — Not implemented.** Need verified template/subject versions, whole-lot/quantity hold semantics, independent release authority and shared stock/QC locks. JSON checkpoint IDs are not release records.
- **Physical versus available — Not implemented.** Distinguish known physical, held, reserved and usable quantities by exact entity/location/lot/unit. Unknown openings remain unknown; an active master is not usable stock.
- **Consumption/returns — Not implemented; policy blocked.** Issue is not consumption. Define WIP/cumulative usage, returns/loss/scrap and correction ownership with ledger links; do not treat frontend issuedQuantity as consumption evidence.
- **Opening reconciliation — Not implemented; source blocked.** Raw evidence exists, but typed approved openings/as-of/location/unit/reconciliation and opening posting do not. Master approval must stay separate from any later authorized opening transaction.
- **Audited stock corrections — Not implemented.** Define reason/evidence/authority/independence and append-only compensation/reversal with backdating controls. Never silently overwrite posted movements.
- **Concurrency/idempotency — Foundation tested; stock semantics absent.** Need unique absent-row creation, consistent stock/QC/reservation lock order, no over-issue/dispatch, retry/audit rollback tests, dated availability and deterministic ledger/projection rebuild.

Before schema/commands are frozen, approve warehouse/location identity, entity typing, exact units/conversions/precision, unknown/negative/backdated policy and authority boundaries. Area/Machine cannot be silently treated as a warehouse. A sealed incomplete specification is not production approval. Future transaction FKs must PROTECT exact revision UUIDs and preserve relevant snapshots.

## 10. Recommended fixes in priority order

1. **Approve a bounded Phase 2 remediation scope; keep Phase 3 implementation paused.** Preserve the audit/baseline and do not silently fix findings.
2. **Fix F1 first:** canonical reviewed/applied plan, resolved IDs and versions, rejection/re-review on reference or duplicate-candidate drift, retained applied evidence and concurrency regressions.
3. **Resolve F2 scope and change control:** approve the capability-configuration workflow/responsibility; implement/version/audit it if required. Address existing memberships after role changes or explicitly restrict/govern out-of-band edits. Seed no speculative business authority.
4. **Fix F5/F6/F7:** typed FK resolution, explicit nullable stage inputs and consistent UUID command validation. Add permanent regressions and rerun retained/new tests.
5. **Obtain originals and authority decisions:** record controlled versions/owners/signoff and paragraph-to-action/test traceability. Reconcile units, variants, IDs, duplicate candidates and openings. Preserve unknown quantities.
6. **Approve inventory design before coding:** locations/lots/entity types; physical/held/reserved/usable definitions; issue/consumption/return/correction separation; opening evidence; lock order and domain acceptance tests. Narrow initial Phase 3 scope; do not add incidental sales/production/QC/dispatch transactions.
7. **Scope frontend adapters separately:** base URL, email/profile roles, real logout, UUID DTOs, active filters, retries/ETags and backend master stores. Add actual contract tests and authorized browser acceptance; do not weaken security for demo/numeric compatibility.
8. **Close release/operations gates:** import/review retention, restricted DB privileges, secrets/TLS/ingress/recovery/MFA and stale remote/deployment docs. Create a reviewed reproducible Phase 2 release only when authorized; no automatic push or deployment change.
9. **Repeat the exit audit:** retain green existing tests and permanent adversarial regressions, close or explicitly risk-accept findings with owners/scope, document client/source gates and identify the reproducible release/migration state.

## 11. Final decision

**NO-GO for Phase 3 implementation now.** Green existing tests do not close import identity drift, complete capability governance, establish source/SOP authority or make the working tree a reproducible release.

Design discussion and collection of controlled originals may continue at the user's direction. Implementation should wait for approved Phase 2 remediation and an explicit policy-backed inventory scope. This report makes no production/SOP compliance claim and authorizes no import, posting, architectural fix, deployment, commit or push.
