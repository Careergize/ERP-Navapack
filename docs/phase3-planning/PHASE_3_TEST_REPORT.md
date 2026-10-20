# Phase 3 current baseline and gate verification

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
