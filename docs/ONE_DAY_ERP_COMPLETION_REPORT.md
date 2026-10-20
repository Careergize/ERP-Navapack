# One-day ERP development completion report

Date: 21 October 2026 (Asia/Calcutta). Development implementation; not production authorization.

## Baseline and preservation

Resumed baseline: `42a78d2 Commercial Workflow Hardening, Policy Infrastructure & Integration added`.
Existing Phase 3/4A/4B work retained. No reset, clean, stash, staging, commit, push or deployment performed by this sprint. The resumed baseline differs from the earlier session baseline; it was accepted as found rather than rewritten. All 28 originals were rehashed against `docs/CLIENT_SOURCE_MANIFEST.json`: 28 matched, zero mismatches.

## Implemented

- JWT-backed commercial workspace: quick customer creation, exact-string costing, quotation and multi-product sales-order draft forms; immutable revisions/history and explicit capabilities.
- Costing → quotation → sales-order draft derivation through `/api/v1/commercial/documents/{id}/derive/`. Copies persisted editable values, exact costing references, source revision/hash and explicit unapproved lineage. No acceptance or confirmation. Foreign owners, cancelled sources and stale source revisions are rejected. Idempotency is retained. Later edits retain source mapping.
- Fixed handoff audit action and revision SHA256 to satisfy both existing commercial database evidence guards. No trigger relaxation.
- `/api/v1/rehearsal/jobs/`: persisted owner/warehouse-scoped multi-line synthetic job cards, optimistic concurrency, idempotency and atomic audit/history. Four additive migrations; no historical migration rewritten.
- Customer-order or production-for-stock origin. Stock origin uses a costing revision directly, with exact product/unit/planned quantity/specification snapshots and estimated material requirements. Exactly one source is required by service and database constraint. Stock jobs finish at synthetic finished goods; customer dispatch/invoice is blocked.
- Per-line optional ordered extrusion, printing, slitting, making and packing stages; synthetic machine/operator, server start/end times, exact input/output/waste/rejection and remarks. Prior stages must complete; output+waste+rejection must balance input. QC FAIL blocks finished completion; PASS reinspection retains failure history. Separate synthetic review, issue, QC, finish and dispatch events.
- Connected `/rehearsal` React forms, production-purpose selector, statuses, blockers, readable history, source snapshots, version-conflict retention and duplicate-submit locking. Existing legacy demo remains separate.
- Persisted dashboard counts for commercial documents/jobs/stages; permitted customer/prospect counts; estimated cost grouped by currency; synthetic output/waste/rejection grouped by exact unit. Financial totals and operational available stock remain unavailable.
- Quotation/costing/order and synthetic-invoice browser print/save-PDF previews carry `DEVELOPMENT PREVIEW — NOT APPROVED FOR CUSTOMER ISSUE`. Exact persisted lines/specifications/currency retained; no invented tax, legal number, signatory or email delivery.
- Mobile sidebar layout corrected; disconnected notification affordance no longer suggests actionable notifications.
- Loopback bounded `backend/scripts/serve_erp_acceptance.py` creates its own stamped disposable database, synthetic actors/scopes, linked commercial drafts, completed synthetic dispatch and interactive draft jobs. No configured database migration or real grant provisioning.

## Verification and corrections

Initial recovered runs were not green: one handoff audit SHA was missing, cancelled sources returned stale conflict before cancellation validation, and an old acceptance fixture violated independent scope approval. Fixed causes without weakening guards or deleting assertions. Failed logs retained under ignored `backend/.local/`.

Executed from frontend:

- `node ./node_modules/typescript/bin/tsc --noEmit`: PASS.
- `npm run build`: PASS, 1,741 modules. Existing large-bundle warning remains (approximately 1.26 MB JS before gzip).
- Every `scripts/check-*.mjs`: all 16 PASS, including new rehearsal contract checks. A subsequent frontend build after report/dashboard additions also passed.

Executed from backend:

- `.venv/Scripts/python manage.py check`: PASS, no issues.
- `.venv/Scripts/python manage.py makemigrations --check --dry-run`: PASS, no changes.
- `.venv/Scripts/python scripts/test_isolated.py --synthetic-ledger tests.test_commercial_handoffs tests.test_rehearsal tests.test_one_day_journey tests.test_rehearsal_transport`: recovered 12-test run found the issues above; corrected rerun results recorded below when complete.
- `.venv/Scripts/python scripts/test_isolated.py --synthetic-ledger`: complete 306-test regression executing in generated stamped database; final result recorded below when complete. This includes JWT, permissions, inventory/QC, concurrency, audit rollback, migration/restore, commercial and HTTP adapter tests.

`tests/test_one_day_journey.py` exercises customer creation, two products, costing, quote/order derivation, multi-line job/routes, issue, production, failed QC/reinspection, finish, dispatch, preview, dashboard and immutable history. It asserts operational ledger/balances and QC authority/postings do not change. `test_rehearsal_transport.py` invokes actual React API adapters over JWT HTTP against Django/PostgreSQL; contract script covers headers, exact strings, retries, reads and history. Stock-source regression covers finished completion and blocked dispatch.

Browser acceptance: attempted; tool reports **Local browser use is disabled in Work settings**. Full rendered-control acceptance and printed PDF visual QA are NOT passed. Harness fixture generation succeeded and persisted synthetic linked records in its active disposable session.

## Connectivity and operating the demo

Only newly generated `test_phase3b_<uuid>` databases with a verified stamp/nonce can execute these workflows. Migrations apply only inside the existing disposable runner. The configured application database was not migrated. PostgreSQL local cluster recovered from interrupted WAL recovery before tests; no data directory was deleted.

For a bounded interactive development session, from backend run:

```powershell
.venv/Scripts/python scripts/serve_erp_acceptance.py --disposable-synthetic-only --port 8014 --seconds 3600
```

The fixture metadata path is printed by the harness and stored ignored at `backend/.local/phase4b/browser-fixtures.json`. It contains test-only login details, generated database identity and stop-file path. From frontend start Vite with process-local `VITE_API_BASE_URL=http://127.0.0.1:8014/api/v1`, mock login disabled, port 5174 and host 127.0.0.1. Open `/commercial` or `/rehearsal`; log in using the synthetic fixture account. Records survive refresh/relogin while that database session is alive. On bounded shutdown the harness verifies no stock mutation and destroys only its generated database.

Persistent development and production connectivity are NOT certified by disposable tests. A persistent development deployment requires separately authorized provisioning/migrations, reviewed runtime grants, approved data retention and a suitable explicit synthetic environment design; do not point ordinary settings at a database and bypass the stamp guard. Production needs all remaining operational approvals and policies.

## Boundaries and remaining work

- Material issue is aggregate scenario evidence (`quantity`/`available_quantity`), not a material-by-material custody command. Material requirement estimates reference immutable costing components; no physical-source proof or operational stock availability is claimed.
- Production quantities use each source line's exact unit. No unapproved interstage unit conversion, yield specification or capacity planning.
- Synthetic QC outcomes are isolated rehearsal evidence. Existing Phase 3 QC implementation is preserved and separately tested; these outcomes do not issue operational QC authorizations.
- No operational reservations, stock deductions, finished-stock receipts, production approvals, physical dispatch, customer acceptance, email or legal invoice.
- Existing Phase 3 inventory/QC screens and synthetic stock workflows remain separate guarded tools; this sprint does not turn rehearsal events into ledger postings.
- UI browser acceptance/print visual QA outstanding. Unsaved-field browser-unload protection exists; complete recovery across crashes and every in-app navigation is not guaranteed.
- P4-01–P4-08 and outstanding Phase 3 gates remain open: business authority, VAT/LED, FX, specifications, physical evidence, commercial issue/acceptance and deployment/runtime authorization.
- No native Capacitor build was performed; web implementation retains existing compatible stack.

## Release decision

Production: **NO-GO**. Development: **GO for the bounded automated synthetic workflow**; rendered browser acceptance remains incomplete. This is a bounded persisted development journey, not a claim that every ERP module is complete.

## Changed and untracked files at report generation
 M backend/apps/commercial/services.py
 M backend/apps/commercial/views.py
 M backend/tests/test_phase3e_rehearsal.py
 M frontend/src/App.tsx
 M frontend/src/components/layout/AppShell.tsx
 M frontend/src/lib/commercialApi.ts
 M frontend/src/lib/rehearsalApi.ts
 M frontend/src/pages/Commercial/CommercialFoundation.tsx
?? backend/apps/commercial/handoffs.py
?? backend/apps/rehearsal/migrations/0001_initial.py
?? backend/apps/rehearsal/migrations/0002_evidence_guards.py
?? backend/apps/rehearsal/migrations/0003_rehearsaljob_costing_revision_and_more.py
?? backend/apps/rehearsal/migrations/0004_stock_source_guard.py
?? backend/apps/rehearsal/models.py
?? backend/apps/rehearsal/services.py
?? backend/apps/rehearsal/urls.py
?? backend/apps/rehearsal/views.py
?? backend/scripts/serve_erp_acceptance.py
?? backend/tests/test_commercial_handoffs.py
?? backend/tests/test_one_day_journey.py
?? backend/tests/test_rehearsal.py
?? backend/tests/test_rehearsal_transport.py
?? docs/ONE_DAY_ERP_COMPLETION_REPORT.md
?? frontend/scripts/check-rehearsal.mjs
?? frontend/src/pages/Commercial/DraftPreview.tsx
?? frontend/src/pages/Commercial/QuickCustomer.tsx
?? frontend/src/pages/Rehearsal/RehearsalInvoicePreview.tsx
?? frontend/src/pages/Rehearsal/RehearsalSummary.tsx
?? frontend/src/pages/Rehearsal/RehearsalWorkspace.tsx

## Recovery verification update

- Original interrupted full run: 304 tests, 1001.945 seconds, FAILED (13 failures, 79 errors). Its obsolete rehearsal migration-name expectation interrupted the upgrade test and caused later missing-schema failures. This result is retained, not counted as passing.
- Recovered 12-test acceptance run: 80.326 seconds, 11 passed / 1 failure (cancelled source error precedence); fixed by validating cancellation before stale revision.
- Fresh `scripts/test_isolated.py --synthetic-ledger tests.test_phase3e_rehearsal tests.test_commercial_handoffs`: **5 tests PASS in 101.947 seconds**. Includes exact migration upgrade, populated independent backup/restore, enabled triggers, nonce denial and all corrected handoff regressions.
- All 28 source originals reverified in this resumed session: zero SHA256 mismatches.
- Active bounded demo: generated database `test_phase3b_c4c32065ab9a4dceb57ec6a6978ca080`; demand `5448b924-d161-4acd-a517-1b9b7b19f5b0`; completed synthetic dispatch job `69de2dbe-9069-4502-b6be-72f563937d71`; interactive draft job `94575b8b-840d-4057-8627-f7e74a5de368`. These are disposable identifiers, not operational records.

Final focused acceptance: **12 tests PASS in 55.245 seconds**, fresh stamped database created/destroyed (`backend/.local/resume-acceptance-final.log`). This includes all four handoff tests, six production tests, one complete API journey and one actual React-adapter JWT/HTTP journey. Final frontend TypeScript/build passed after material-estimate UI additions (`backend/.local/resume-frontend-final-build.log`). A clean final complete regression was started after these corrections; final outcome follows below.

The first resumed complete regression finished: **306 tests, 1213.231 seconds, 305 passing / one failure**, solely the cancellation-validation error precedence fixed afterward. It had no remaining migration, inventory/QC or operational-stock regression. The final clean full run includes the corrected code and has completed populated upgrade/restore successfully; its final summary is recorded below.

Frontend navigation correction: backend sessions no longer enter the legacy demo QC-role redirect, preventing a role-label conflict with capability-governed workspace navigation. Production build passed again after this correction (`backend/.local/resume-frontend-release-build.log`). The actual HTTP adapter scenario additionally signs in again and verifies persisted job version/status/source hash.

Task-owned frontend server 5174 was restarted with process-local `VITE_ENABLE_MOCK_LOGIN=false` and the disposable API URL. Existing `.env` and the user's server on 5173 were preserved. No unknown process or database was deleted.

Active fixture readback (explicit stamped disposable database only): 3 commercial documents, 2 rehearsal jobs, 14 rehearsal revisions; **0 ledger entries, 0 balance projections, 0 operational QC authorizations and 0 QC postings**. The completed journey is therefore persisted while operational stock and QC authority remain empty in that session.

Production-for-stock without a customer: strengthened source fixture omits customer and classification, asserts null party snapshot and null Sales Order reference, completes synthetic production/QC/finished goods and rejects dispatch. Focused rerun **1 test PASS in 3.506 seconds**, disposable DB created/destroyed (`backend/.local/resume-stock-without-customer.log`). No implementation changed after the final full run began; this strengthens a test already in that run.

## Final verification result and cleanup

**Full isolated PostgreSQL regression: 306 tests PASS in 1024.338 seconds.** Command: `.venv/Scripts/python scripts/test_isolated.py --synthetic-ledger`. Final log: `backend/.local/resume-final-full.log`; database `test_phase3b_fc81f2ecfddc4354adf76348340cf820` was created, stamped, migrated and destroyed by the runner, exit 0. This clean run includes the actual React adapter HTTP journey with fresh-login persistence verification and all existing Phase 3/4, JWT, permission, concurrency, idempotency, audit and inventory/QC regressions. Earlier failure logs are preserved and superseded by this result.

Additional executed evidence: 12-test ERP acceptance PASS (55.245s), 5-test handoff/upgrade/restore PASS (101.947s), customer-free stock-production PASS (3.506s), TypeScript/build PASS (1741 modules), all 16 frontend validation scripts PASS, Django checks/drift PASS and Git whitespace check PASS. These are separate runs, not added together as unique test coverage.

Cleanup: all completed resumed test-run databases were destroyed by their owning runners, including the temporary recovery databases. Two pre-existing inactive disposable database names (`test_phase3b_143c821ed38040b688f9582e280a50c3`, `test_phase3b_b244e597a7ce42e793935aabdce25159`) were observed and preserved because ownership/cleanup provenance was not established. No unknown process/database was removed. The intentional bounded demo harness remains active on loopback 8014, with task frontend on 5174 and mock login disabled; its database is destroyed by its own bounded teardown. Existing user server 5173 remains untouched. Stop the harness by creating its generated `stop_file` from the ignored fixture metadata, or allow the bounded timeout. The frontend server can then be stopped from its own terminal. Useful logs/backups remain ignored under `.local`.

Development decision: **GO for the tested bounded synthetic API/frontend journey; rendered-browser and print visual acceptance outstanding.** Production decision: **NO-GO**. Persistent local development deployment remains separately unprovisioned/unapproved; the configured application database has no sprint migrations, real grants or operational records from this work. No commit, push or deployment performed.

## Final working-tree manifest

The following includes tracked modifications and all untracked files, including interrupted work preserved at resume:

```text
 M backend/apps/commercial/services.py
 M backend/apps/commercial/views.py
 M backend/tests/test_phase3e_rehearsal.py
 M frontend/docs/BACKEND_TODO.md
 M frontend/docs/BUSINESS_RULES.md
 M frontend/docs/CHANGELOG.md
 M frontend/docs/DATA_MODELS.md
 M frontend/docs/DEVELOPMENT_STATUS.md
 M frontend/src/App.tsx
 M frontend/src/components/layout/AppShell.tsx
 M frontend/src/lib/commercialApi.ts
 M frontend/src/lib/rehearsalApi.ts
 M frontend/src/pages/Commercial/CommercialFoundation.tsx
?? backend/apps/commercial/handoffs.py
?? backend/apps/rehearsal/migrations/0001_initial.py
?? backend/apps/rehearsal/migrations/0002_evidence_guards.py
?? backend/apps/rehearsal/migrations/0003_rehearsaljob_costing_revision_and_more.py
?? backend/apps/rehearsal/migrations/0004_stock_source_guard.py
?? backend/apps/rehearsal/models.py
?? backend/apps/rehearsal/services.py
?? backend/apps/rehearsal/urls.py
?? backend/apps/rehearsal/views.py
?? backend/scripts/serve_erp_acceptance.py
?? backend/tests/test_commercial_handoffs.py
?? backend/tests/test_one_day_journey.py
?? backend/tests/test_rehearsal.py
?? backend/tests/test_rehearsal_transport.py
?? docs/ONE_DAY_ERP_COMPLETION_REPORT.md
?? frontend/scripts/check-rehearsal.mjs
?? frontend/src/pages/Commercial/DraftPreview.tsx
?? frontend/src/pages/Commercial/QuickCustomer.tsx
?? frontend/src/pages/Rehearsal/RehearsalInvoicePreview.tsx
?? frontend/src/pages/Rehearsal/RehearsalSummary.tsx
?? frontend/src/pages/Rehearsal/RehearsalWorkspace.tsx
```
