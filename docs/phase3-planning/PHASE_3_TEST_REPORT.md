# Phase 3 current baseline and gate verification

## Phase 3C-1 final verification — 20 October 2026

Current implementation is an isolated synthetic workflow foundation, not operational posting or QC. [Complete contracts/files/limits](PHASE_3C_IMPLEMENTATION_REPORT.md). Existing historical sections below remain unchanged.

From backend, .venv/Scripts/python:

- Pre-implementation scripts/test_isolated.py --synthetic-ledger:170 passed in321.065s, test_phase3b_20e5aeda6a5a498799a481a46c8c2e4a, destroyed. Fresh baseline, not reused3B evidence.
- Initial scripts/test_isolated.py --synthetic-ledger tests.test_operations:20 cases,2 failures/15 errors, caused by new workflow line-sealing trigger using xmin under nested savepoints; one-case diagnostic reproduced the same defect. Corrected using server-set top-level transaction IDs in new unapplied0008/0009 migrations. Corrected20 passed in50.626s, test_phase3b_fa74581957e843dfa921e9c7785f8891, destroyed.
- Full scripts/test_isolated.py --synthetic-ledger:193 passed in431.844s, test_phase3b_ecdc4d4b5ba245b6b9c95152319e35ce, destroyed. Includes170 prior cases and23 workflow cases; no failures/skips. Subsequent focused runs verify final tightening, not a claim that this193 run used every later byte.
- scripts/test_isolated.py --synthetic-ledger tests.test_operations:23 passed in71.272s, test_phase3b_f04ca1521d394f3998d2d679d9a50cb0, destroyed, verifying final XID/decision/independence boundaries at that stage.
- Final same focused command:24 passed in75.402s, test_phase3b_e3341316307445728883c9a36e0750e8, destroyed. Includes newly added at-most-one posted adjustment per count and its permanent positive-variance reuse regression, full policy evidence, immutable original/current opening target and final schema. These runs overlap; not217 unique tests. Repository now has194 distinct test cases; a single194-case full run was not executed after final tightening.
- Final connected manage.py check passed; manage.py makemigrations --check --dry-run passed with no drift; read-only manage.py showmigrations --plan confirmed15 pending application migrations, none applied. Initial sandboxed migration generation/drift attempts warned localhost TCP was unavailable; final connected checks supersede those environmental warnings.

New coverage: receipt evidence/unit/precision/held handling; actual physical confirmation and selected recorder; known-zero/unknown opening; Admin/staff-with-explicit-capability correction initiation and no title bypass; independent approval/rejection/history and immutable original; correction after later issue; held-opening removal gate; transfer conservation/unchanged registration; original-line return bounds/hold; count variance/investigation/staleness/one-use; full audit attribution/failure rollback including nested ledger; duplicate physical requests/idempotent API retries; two connections concurrently creating duplicate evidence; two approved workflows competing to issue7 from10 with one winner; scope/permission/API filtering; late/forged decision and sealed-line/raw-write database rejection; production-disabled service/API mode. Existing full suite retains PostgreSQL restricted-role ledger protection tests; new workflow-specific deployed ACLs were not certified.

Frontend: node ./node_modules/typescript/bin/tsc -b --pretty false; npm run build; all13 scripts/check-*.mjs passed. Expanded check-inventory-api.mjs verifies actual adapter URLs, filters, headers, history and error propagation, with a mocked HTTP transport. Separate Django APIClient/PostgreSQL tests exercise real APIs. An early JSX nesting error was corrected; existing large-chunk build warning persists. One overlapping standalone transport-check invocation reported WebSocket port24678 occupied but passed; serial all13 run passed. No browser-to-live-Django deployment test or interactive synthetic server harness was implemented/claimed.

Preservation: task-start manifest314 files, no removed baseline files; original28 client sizes/hashes match. Phase3A/3B handover reports, ledger services/models/guards, base settings and isolated runner unchanged. Existing dirty3B work retained, HEAD82a32a1 unchanged, index empty. Exact new/modified3C paths in report; local logs/manifests/build artifacts ignored.

Cleanup: verified project PostgreSQL data_directory exactly F:/WORK/Navapack-ERP/backend/.local/postgres, zero remaining test databases/temporary runtime roles/other client connections. Closed verification connection and pg_ctl fast stop succeeded exit0 (“server stopped”), restoring initial state. No operational database migration/data/grant/import or deletion.

Verdict: CONDITIONAL GO for synthetic3C-1 review; NO-GO operational use/automatic3D. Unexecuted: populated upgrade, production ACLs, browser acceptance, real scope lifecycle/authority/QC/period/correction policies and later phases.

## Phase 3B final verification — 20 October 2026

User-authorized synthetic-only implementation; this current section supersedes older no-ledger/test limitations below only for the implemented slice. Full contracts/limitations are in [Phase 3B report](PHASE_3B_IMPLEMENTATION_REPORT.md). No application migrations or real stock/imports/grants were performed.

Commands from backend using .venv/Scripts/python:

- manage.py check — final connected run passed, no issues.
- manage.py makemigrations --check --dry-run — final connected run passed, no changes detected.
- scripts/test_isolated.py tests.test_audit_remediation tests.test_core tests.test_inventory — audit prerequisite gate:27 passed in31.677s, test_phase21_875876ff2a88484b943ad847f312c407, destroyed. Executed before ledger implementation.
- scripts/test_isolated.py --synthetic-ledger tests.test_ledger — first ledger integration run:34 passed in82.195s, including13 imported Phase3A cases in that early runner discovery. Subsequently removed imported TestCase discovery duplication; do not add this count to the final suite.
- scripts/test_isolated.py --synthetic-ledger —170 passed in320.005s, test_phase3b_bfd9fc4dbd03487e9742c7628e14def0, destroyed. Includes142 existing cases,5 permanent audit regressions and23 ledger/gate cases; no skips/failures.
- scripts/test_isolated.py --synthetic-ledger tests.test_ledger tests.test_audit_remediation — final changed-boundary verification:28 passed in73.245s, test_phase3b_502c2d3006bb497e84976ab0a0160358, destroyed. Verifies final audit metadata and forces deferred constraints IMMEDIATE while SET LOCAL ROLE uses a nonowner restricted role. Overlaps the full suite; not198 distinct cases.
- manage.py showmigrations --plan —13 pending: accounts0004/0005; core0003/0004; imports0005/0006; inventory0001–0007. Read-only; no application migrate.

Actual PostgreSQL16.3, local disposable databases. Concurrency uses two independent connections/threads against the same available balance, with exactly one successful issue and no partial residue. Tests cover immutable database/ORM evidence, unique physical sources across actors, idempotency, units/scale, known-zero versus unknown openings, held/insufficient stock, ownership/custody/lineage, conserved transfers, scoped destination history, original-preserving feasible corrections, independent exact approvals, rejection/content mismatch/self-approval, reversal/return bounds, closed dates/backdating, versions, audit rollback, projection rebuild and custody deactivation protections. No real client quantities used.

Restricted role probe: temporary NOLOGIN/NOSUPERUSER/NOCREATEDB/NOCREATEROLE role, explicit table grants, transactional SET LOCAL ROLE, service IN succeeds and deferred posting constraints run under that role. UPDATE/DELETE/TRUNCATE posted entries, trigger disabling, schema CREATE and audit TRUNCATE denied. All role/grant/data changes rolled back; final role list empty. This is an isolated runtime permission test, not verification of deployed credentials or a complete production privilege manifest. Owner/DBA control and operational log/archive governance remain separate gaps.

Frontend (unchanged source): node ./node_modules/typescript/bin/tsc -b --pretty false, npm run build and each of13 scripts/check-*.mjs passed. Vite still reports the existing large bundle warning. These regression scripts include isolated demo workflows; their passes do not establish live backend workflows. No browser-to-live-Django acceptance or deployment executed.

Preservation: all28 client source sizes/SHA-256 still match CLIENT_SOURCE_MANIFEST.json;304-file task baseline had no removed files; Phase3A handover unchanged. No stage/commit/push/deploy from this task. HEAD advanced externally to82a32a1 during development; report distinguishes task-manifest changes from current Git diff. Final index empty. Logs/manifests under backend/.local/phase3b and frontend build outputs remain ignored.

Cleanup: server data_directory verified exactly F:/WORK/Navapack-ERP/backend/.local/postgres; no remaining test_phase3b/test_phase21 databases, no temporary runtime roles and zero other client connections. Closed verification connection then pg_ctl -D <verified directory> -m fast stop succeeded exit0, “server stopped”. No data directory removed or unrelated service stopped.

Unexecuted/blocked: populated application upgrade, deployed restricted-role grants, browser acceptance, load/volume testing, operational scope/approval/QC/correction/backdating workflows, full audit filters/retention/export and all Phase3C–3E. Synthetic tests do not approve client policy. Verdict: CONDITIONAL GO for review of synthetic3B, NO-GO operational3C/live posting.

## Resumed Phase 3A verification — current evidence

20 October 2026, Asia/Kolkata. This section supersedes the earlier documentation-only stop below. Baseline HEAD remains 0823b2065e6e01dc670c5b09f5b622bbfadf8eb2. The seven existing uncommitted planning deliverables were preserved; application files were initially clean on resume. No staging/commit/push/deployment.

### Backend commands

From backend with `.venv/Scripts/python`:

- `scripts/test_isolated.py`: full regression after foundation implementation **141 passed in 225.204s**, before adding the history isolation case and strengthening superuser coverage.
- Expanded 142-case run and 31-case inventory/core/command run initially each had one failure: strengthened Employee+superuser test exposed Django's inherited superuser permission shortcut. Fixed by extracting shared explicit-role resolution and a direct/group/governed-grant resolver that excludes the shortcut. The auth profile now reports the same explicit inventory capability set; other existing namespaces retain prior semantics.
- `scripts/test_isolated.py tests.test_inventory tests.test_auth tests.test_role_capabilities`: **49 passed in 87.471s** on the final backend source, including all 13 inventory cases and final profile assertions, in disposable database `test_phase21_8ef5ea4e0da9458a868b6fd666afd174`, destroyed afterward. Existing auth/RBAC infrastructure was reused rather than granting a new Admin bypass.
- Corrected full `scripts/test_isolated.py`: **142 passed in 259.005s**, disposable PostgreSQL database `test_phase21_3269b01176bc4673963bedee2ac5d079` created/migrated/destroyed. The final 49-case run above additionally validates the last auth-profile assertion/refinement. These runs overlap; do not sum them as distinct coverage. Tests use synthetic fixtures and actual PostgreSQL 16, including two independent connections racing opposite hierarchy edits. No real client quantities/owners/warehouse grants are used.
- Connected `manage.py check` passed, no issues. `manage.py makemigrations --check --dry-run` passed, no changes detected. `manage.py showmigrations inventory --plan` confirms all inventory0001–0005 **unapplied in the application database**. `sqlmigrate inventory 0002` was inspected. No application migrate command executed. Test runners alone apply migrations in fresh disposable databases.

Earlier development failures also included a missing Employee department fixture and accidental reuse of master source_id validation for inventory source_reference. Both corrected; an intermediate eight-case inventory suite then passed. Initial migration-generation checks under the sandbox warned about local TCP access; the connected final checks above had no history warning. Cluster was already running from the prior session; an attempted start reported already-running and did not restart it. These intermediate failures are retained as diagnostic evidence, not final pass claims.

### Covered behavior

Warehouse UUIDs/uniqueness, idempotent create and one audit event, safe before/after/employee attribution, optimistic conflicts and missing version; same-warehouse hierarchy/cycle/raw-SQL guards and concurrent opposite-parent race; typed stock item/unit/provenance and generated immutable UUID/readable reference; parent integrity; explicit ownership shape and nonunique supplier batch; inactive warehouse/dependent restrictions; no API deletion/raw deletion/identity mutation; scope evidence independence/immutability/expiry/replay reauthorization; active identity/JWT/plural-role contract; no Admin/Master Admin/superuser implicit inventory capability or scope; warehouse list/detail isolation; scoped audit-history capability/record/warehouse restrictions; injected audit failure rolls back configuration/idempotency; absent operational receipt/issue/transfer/opening-correction/release routes.

No inventory ledger/quantity-operation tests are claimed. Scoped approval/rejection/publication/revocation is blocked, so no fabricated scope transition tests or real-user grants. Restricted nonowner runtime-role privileges, TRUNCATE/DBA boundaries, retention/export, populated upgrade/restore rehearsal, browser-to-live-Django and deployment remain unverified. Existing DB-owner-capable tests are not runtime-role proof.

### Frontend commands

From frontend:

- `node ./node_modules/typescript/bin/tsc --noEmit` — passed on final frontend source.
- `node ./node_modules/vite/bin/vite.js build --outDir ../backend/.local/phase3-review/phase3a-reviewed-build` — passed, 1,723 modules; existing >500kB bundle and intentional external-output-directory warnings retained.
- All **13** `scripts/check-*.mjs` passed, including the new check-inventory-api. This checks UUID/multi-role/no-role profile handling, email login, /api/v1 normalization (including the existing ignored .env legacy value without editing it), pagination/filter, retry/version headers, denied-save propagation and backend logout. The other 12 scripts remain additional demo/adapter regressions, not backend stock execution proof. Final auth/inventory adapter scripts were rerun after the history UI additions; final metadata-only viewer additions were typechecked/built.

No mocked success fallback introduced. Real browser acceptance is not claimed. Real-session routing is deliberately limited to integrated Phase 3A; demo modules remain available only as opt-in demonstrations.

### Preservation and deliverables

Final 28/28 original source sizes/SHA-256 hashes still match CLIENT_SOURCE_MANIFEST.json. No SOP/workbook saved, recalculated or imported. `git diff --check` passed; local Markdown targets resolve; index remains unchanged. Test logs, SQL inspection, derived extraction and frontend build output under backend/.local/phase3-review remain ignored. Exact absolute paths for every changed deliverable are in PHASE_3_IMPLEMENTATION_PROGRESS.md.

Current cleanup: verified PostgreSQL SHOW data_directory resolves exactly to `F:\WORK\Navapack-ERP\backend\.local\postgres`; pg_stat_activity showed **zero other client connections**. Closed the verification connection, then `pg_ctl -D <verified-directory> -m fast stop` succeeded with exit 0 and “server stopped”. No unrelated service or data directory was stopped/deleted. Prior approval-review failure and may-still-be-running statements in the retained historical section are resolved by this successful cleanup.

20 October 2026, Asia/Kolkata. Source baseline `0823b2065e6e01dc670c5b09f5b622bbfadf8eb2`, initially clean working tree. Documentation-only stop under the user's Phase 3A gate; **no Phase 3 feature acceptance is claimed**.

## Backend commands and exact results

Commands run from `F:\WORK\Navapack-ERP\backend` using `.venv/Scripts/python`:

- `manage.py check` — passed, no issues.
- `manage.py makemigrations --check --dry-run` — final run passed, no changes detected and no database-history warning.
- `manage.py showmigrations --plan` — passed with local PostgreSQL access, all displayed migrations applied in the configured local application DB, including accounts 0004/0005 and imports 0005/0006. Read-only assessment; no application `migrate` command executed. This is not a production/deployment claim.
- `scripts/test_isolated.py` — **129 tests passed in 190.668 seconds**, actual PostgreSQL 16, database `test_phase21_4650af2076754391b831ef77a5bcc991` created/migrated by the test runner and destroyed afterward. Includes Phase 1/2/2.1 auth, command/concurrency, imports, employee and role-governance regressions. Existing tests use synthetic fixtures, not client openings. This closes the earlier documentary limitation that the final 129 cases had not run together.

The existing runner was inspected first: localhost/PostgreSQL enforcement, absent UUID-named database check, no reuse/drop of a pre-existing test DB. Existing ignored dedicated cluster `.local/postgres` on 127.0.0.1:55432 was started for verification. No operational application migrations, grants or data changes were made. The test role is an owner-capable local test role, **not evidence of restricted production runtime permissions**.

Initial sandbox execution failed before test discovery/database creation with local TCP Permission denied (10013); an approved unsandboxed retry initially timed out. Starting/reaching the dedicated cluster in the approved process resolved connectivity; the final complete run passed. An initial drift run said no changes but warned that DB history could not be checked; only the later connected run supports the final migration-check result. These environmental failures are not hidden as passing tests.

Local evidence: ignored `backend/.local/phase3-review/baseline-tests.log`, `migration-state.log` and `postgres.log`. Log output contains expected denial/conflict and injected safe-error cases; final suite result is OK. No stock-engine/concurrent-OUT tests are included merely because the existing foundation concurrency tests pass.

## Frontend baseline

Commands run from `F:\WORK\Navapack-ERP\frontend`:

- `node ./node_modules/typescript/bin/tsc --noEmit`.
- `node ./node_modules/vite/bin/vite.js build --outDir ../backend/.local/phase3-review/frontend-build`.
- Each existing `scripts/check-*.mjs` using Node.

Final results: typecheck passed; Vite build passed (1,720 modules); all 12 scripts passed: check-auth, check-custom-costing, check-customers, check-finished-goods, check-integrated-operations, check-inventory-workflows, check-job-cards, check-led-finance, check-quality, check-quotation-persistence, check-quotations and check-sales-fulfillment. Build retained the existing >500 kB chunk warning and expected external-output-directory warning. Existing demos/mock-based scripts do not prove real Django inventory/auth integration. No frontend source changed and no browser/deployment acceptance was performed.

Final preservation checks: all 28 original sizes/hashes remained unchanged. Local Markdown links in all seven deliverables resolved. `git diff --check` passed, with only Git's LF-to-CRLF notices. Test logs and frontend build output were confirmed ignored. Final deliverable changes are limited to the seven Markdown files listed in the progress report.

Cluster cleanup limitation: the attempt to stop the dedicated local test cluster was not executed. Automatic approval review failed because of a usage limit, explicitly not a finding that shutdown was unsafe. Shutdown is therefore unverified; the cluster may still be running on localhost:55432. No bypass was attempted. An authorized operator can restore its initial stopped state from backend with `& 'C:/Program Files/PostgreSQL/16/bin/pg_ctl.exe' -D "$PWD/.local/postgres" -m fast stop` after confirming no other work now uses this dedicated cluster.

## Source and repository verification

All 28 original paths/sizes/SHA-256 values matched `docs/CLIENT_SOURCE_MANIFEST.json` before extraction. All 18 DOCX paragraph/table XML texts extracted read-only; both XLSX scanned in formula/cached-value passes without save/recalculation. Observed sheet extents/populated/formulas: Raw Sheet1 103×81 / 856 / 283; Carrier Bags 92×74 / 1068 / 307; Flat Bags 253×78 / 2763 / 848; Packing 94×72 / 545 / 271. No formula lacked a stored cache; this does not establish correct business quantities. Source anomalies and unreconciled units/dates remain pending, not repaired. Final hash verification and Git whitespace/link checks are recorded after completion below.

## Not executed / not implemented

No Phase 3 tests were added because the schema/scope gate stopped implementation. Warehouse uniqueness/auth changes, immutable stock IDs/collisions, ledger duplicates/concurrent OUT/insufficiency/QC-held issue/unit precision/unknown opening, post-approval opening correction/Admin initiation/self-approval/closed periods/downstream history, original ledger preservation/rebuild and Phase 3 audit/filter access tests remain **unexecuted**, not passed or skipped successes. Their acceptance requirements remain in the implementation plan and audit specification.

Restricted runtime DB-role privilege probes, deployment migration rehearsal/restore, production ingress/TLS/runtime grants, real browser contract acceptance, approved SOP cutover and client stock reconciliation remain unverified. Green foundation regressions do not close these gates.


## Phase3D synthetic QC verification — 20 October2026

Corrected full disposable PostgreSQL regression237 passed720.953s (all208 existing plus29 QC cases). Corrected ledger/QC boundaries52 passed226.954s; final expanded QC31 passed168.819s; final scoped history/NCR3 passed11.344s. Counts overlap. Last two QC cases/history refinements are covered by final focused runs; no single239-case full invocation claimed. All13 frontend check scripts, typecheck/build, Django check and migration drift checks passed.20 application migrations remain unapplied (17 predecessors plus inventory0012–0014). Restricted runtime QC posting and denial of UPDATE/DELETE/TRUNCATE/trigger changes executed in disposable PG.

Retained failures: initialQC20 had19 trigger row-field errors; next20 had1 invalid scope-deletion fixture error; initialfull237 had64 guard denials and1-case diagnostic reproduced a settings-override fixture defect. New triggers/fixtures corrected; service guard not relaxed. Intermediate27 passed78.290s. All databases destroyed and temporary roles rolled back; verified cluster stopped after zero other clients. Runtime and database IDs, commands, exact files and limits are in PHASE_3D_IMPLEMENTATION_REPORT.md. No deployed browser acceptance, production runtime credential provisioning or populated upgrade verification.
