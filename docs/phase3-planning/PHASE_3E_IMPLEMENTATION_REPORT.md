# Phase 3E integration and acceptance report

Recorded 20 October 2026. **CONDITIONAL GO for closing synthetic development, subject to outstanding browser acceptance; NO-GO for operational release.** This report finishes the interrupted verification and documents its limits. It does not approve business policies, production permissions, migrations or posting.

## Repository baseline and interrupted work

The original Phase 3E snapshot is preserved at `backend/.local/phase3e/baseline.json`: HEAD `787e328deeac05016b5d5ed44b9e6848793dde8e`, 339 source entries, including existing uncommitted Phase 3D work. The initial review matched all 338 entries in the Phase 3D manifest and all 28 client originals. On resume, HEAD was already `5f5c775108ee35f946519bae4474cacf272d9cbc`; Phase 3D files were tracked at that intervening checkpoint. This task did not create that commit. No reset, cleanup of source, staging, commit, push or deployment was performed.

The interrupted session's three modified and seven untracked integration files were recovered intact. The resume snapshot is `backend/.local/phase3e/resume-snapshot.json`. The final 251-case PostgreSQL run was still finishing; it was observed to complete rather than duplicated. The third recovery log already contained a successful UTC-normalized comparison. No additional application-code changes were necessary during the resume. Original failed attempts remain in the local evidence folder.

## Implemented integration

- `CustodyViewSet` adds GET `/api/v1/inventory/custody/balances/`, `movements/` and `scope/`. All require the existing stamped synthetic environment and explicit `inventory.view_synthetic_custody` capability. Non-oversight users are filtered through existing warehouse scopes. Explicit oversight is a capability decision, not an Admin/superuser shortcut.
- Balance and movement lists use existing DRF pagination; UUID filters are validated, and item type is restricted to material, variant or consumable. Quantities/deltas are decimal strings. Rows are exact stock/unit/location/quality partitions, never cross-unit totals. Responses are observations, not reservations or issue authorization.
- Movement reads expose local ledger legs and transaction UUID/type, without source documents, registration provenance or the opposite warehouse's movement evidence. Exact-scope lookup rejects a foreign identity with no permitted local history. Root containment is a conservative availability flag; detailed hold evidence is not exposed by the reader.
- Exact opening coverage remains UNKNOWN with null quantities when unresolved; only known coverage can report a missing partition as zero. The scope read takes the established posting locks for a consistent observation. The reader does not update balances.
- `InventoryCustody` consumes those APIs through the existing JWT transport, displays HELD/RELEASED separately, pagination, empty/loading/error states, and an unavailable state outside the disposable environment.
- `IdentityRegistration` calls the existing audited/idempotent identity API. UUID/reference remain server-generated. Registration creates no quantity, opening coverage or QC clearance. Retry uses the same key for unchanged intent; changing a form value rotates the key. Existing backend item/unit/identity constraints remain authoritative.
- The existing authenticated Inventory Foundation links these screens. Existing configuration, operations and QC screens continue using their established APIs; legacy demo modules remain separate. No new authentication, competing ledger, audit store, migration or operational posting path was added.

## Verified automated acceptance

`backend/tests/test_phase3e.py` contains 11 combined scenarios using real JWT login and DRF requests against PostgreSQL. They exercise warehouse/location/identity creation, persisted custody, receipt to held stock, independent inspection/review/release and eligible physical OUT; failed inspection/NCR/CAPA/reinspection without automatic release; opening/QC; held transfer conservation and inherited-clearance rejection; concurrent OUT; duplicate receipts/approvals/releases and cross-actor retry; warehouse isolation; stale versions/balances/plans; unknown coverage and unsupported partial/disposition boundaries; independent opening correction preserving the original; returns/counts/adjustments.

The scenario names and exact per-capability classifications are in `PHASE_3E_ACCEPTANCE_MATRIX.md`. These are API integration tests, not browser tests. Existing tests additionally cover audit failure rollback, append-only guards, restricted nonowner runtime ACLs, decimal-string boundaries, physical-source deduplication, QC concurrency and projection rebuild.

## Browser acceptance: incomplete

The interrupted session started React with mock login disabled against a loopback-only Django harness in newly stamped database `test_phase3b_1b7fedf207d74812aebc7a92a5d0d82f`. Recorded actions reached authenticated navigation and warehouse configuration. Server evidence shows duplicate warehouse validation HTTP 400, then warehouse creation HTTP 201 and list reload HTTP 200. The final saved UI state/screenshot was not captured before interruption; this is limited browser/API evidence, not complete visual acceptance.

On resume, the existing browser binding was recovered, but the tool reported **“Local browser use is disabled in Work settings.”** No alternative browser automation bypass was attempted. Location and identity forms, custody views, workflow transitions, QC/NCR interactions, role visibility and the full loading/empty/validation/conflict/unauthorized/retry/history matrix therefore remain **not browser-accepted**. API tests and frontend transport checks do not substitute for those results. No successful browser stock or QC release is claimed.

## Installation, upgrade and recovery

`backend/tests/test_phase3e_rehearsal.py` verifies a clean installation through the normal disposable runner, then an upgrade from the configured 20-migration checkpoint in that disposable database. It creates synthetic historical employee/unit/material/audit rows using historical models, applies all 20 forward dependencies, verifies preserved identities and old audit evidence, creates held stock with an independently authorized QC transition, and creates a custom-format backup.

The backup is restored into a separately generated disposable database. UTC-normalized table fingerprints match for 12 tables: user, unit, material, audit event/evidence, transaction, ledger entry, balance projection, inspection, review, quality authorization and quality posting. Triggers remain enabled, and restored writes without the synthetic nonce are rejected. The restored database is dropped in `finally`; the runner destroys its source test database.

Independent successful rehearsal: 1 test in **37.832s**; source `test_phase3b_2e7d5482fffe4628b94d0eb525230306`, restored `test_phase3b_e10e06ac2d0043b1b93d2ddadf66bd70`. Evidence: `backend/.local/phase3e/rehearsal-tests-3.log` and `recovery/02e1664f260c4d7bb3c35eb23779eff3.json`. The full regression includes a fresh execution of this same test, not another unique case.

Earlier rehearsal failures were a missing synthetic audit request ID and timestamp rendering across session timezones. Both were corrected in test fixtures/fingerprinting before the final passing run; UTC normalization does not discard timestamps or other fields. The first acceptance attempt accidentally discovered helper tests and collided with a fixture attribute; the final module uses an imported module and a distinct helper name. Those failures are retained in `integration-tests.log`, `rehearsal-tests.log` and `rehearsal-tests-2.log`.

This is a representative synthetic populated upgrade, not proof for every possible production dataset. No populated immutable production schema was downgraded. Recovery planning uses independent backup restoration, not destructive reverse migrations. See the release-readiness document for prerequisites and exact dependency order.

## Final verification evidence

Commands run from `backend/`, with existing local PostgreSQL configuration:

```powershell
.venv/Scripts/python scripts/test_isolated.py --synthetic-ledger
.venv/Scripts/python scripts/test_isolated.py --synthetic-ledger tests.test_phase3e
.venv/Scripts/python scripts/test_isolated.py --synthetic-ledger tests.test_phase3e_rehearsal
.venv/Scripts/python manage.py check
.venv/Scripts/python manage.py makemigrations --check --dry-run
.venv/Scripts/python manage.py showmigrations --plan
```

- Initial baseline: 239 tests passed in 543.170s (`baseline-full-tests.log`); deliberately not repeated on resume.
- Final complete suite: **251 tests passed in 719.625s**, database `test_phase3b_27bf422973684d88a7995a0b673ccb40` (`final-full-tests.log`). This is **239 existing + 11 acceptance + 1 rehearsal unique tests**; do not sum overlapping runs.
- Independent JWT/API acceptance: **11 passed in 54.581s** (`integration-tests-2.log`).
- Independent installation/recovery rehearsal: **1 passed in 37.832s**.
- Final Django checks: exit 0, no issues. Drift: exit 0, no changes detected. Migration plan: exit 0, **20 pending**, byte-for-byte equal to the initial recorded plan. The first sandbox-limited read could not connect and emitted a drift history warning; these checks were rerun with local database access and passed without that limitation.
- From `frontend/`: `node ./node_modules/typescript/bin/tsc -b --pretty false`, `npm run build`, and each `node scripts/check-*.mjs`: all exit 0. All 13 scripts passed: auth, custom-costing, customers, finished-goods, integrated-operations, inventory-api, inventory-workflows, job-cards, led-finance, quality, quotation-persistence, quotations, sales-fulfillment. Results are in `final-frontend-results.json`; build emits a Vite plugin timing diagnostic, not a test failure.
- `git diff --check` passed. The index remained empty. All 28 client originals still match `docs/CLIENT_SOURCE_MANIFEST.json`.

## Security, policy and operational limits

The existing service/database nonce and stamp guards are unchanged; `SYNTHETIC_LEDGER_ENABLED=False` remains the default and is not enabled through environment variables. No live stock or QC endpoint was enabled, no actual stock imported, no real employee grants provisioned. Synthetic harness fixtures exist only in newly generated databases; there is no option to stamp an existing application database.

Existing governed capabilities, independent approvers, warehouse scopes, policy versions, physical-source identities, idempotency and optimistic version checks remain enforced. Stock requests/approvals do not reserve or deduct stock. Final posting revalidates and locks quantities. AuditEvidence and immutable append-only ledger history remain the existing authority; source/evidence access is not broadened by local custody visibility.

Unresolved: named QC/inventory authorities and ceilings, warehouse-scope provisioning lifecycle, actual inspection specifications, physical lot marking/segregation, opening dates/quantities/reconciliation, source-document governance, ownership/custody policy, allocation, backdating/period-close policy, rejected disposition, and documented SOP operational adoption (original effective date remains 1 November 2026). These are not approved by tests. Production runtime role provisioning, recovery/backup retention, monitoring, immutable audit export, secrets/TLS and deployment authorization are also outstanding.

## Cleanup and configured database safety

Only disposable databases were migrated or mutated by the write-path checks. Configured `navapack` was used for read-only connection/migration inspection; its recorded migration plan is unchanged. No before/after fingerprint of every application table was captured, so this report does not claim an independent forensic proof of every row's immutability. The commands and generated database checks bound all test writes to disposable names.

The harness stopped through its exact generated stop file and logged database destruction. Final PostgreSQL inspection reported no `test_%` databases, no runtime/synthetic temporary role candidates and no other client connections. Verified project Vite PID 25704 was stopped. The exact project cluster `backend/.local/postgres` on loopback port 55432 was then stopped successfully, restoring its original stopped state. Unrelated PostgreSQL services were preserved. Local logs, dumps and fixture metadata remain ignored and must not be staged.

## Exact Phase 3E files

Modified application/validation files:

- `backend/apps/inventory/urls.py`
- `frontend/scripts/check-inventory-api.mjs`
- `frontend/src/pages/Inventory/InventoryFoundation.tsx`

New application/test files (untracked and preserved):

- `backend/apps/inventory/custody_views.py`
- `backend/scripts/serve_synthetic_acceptance.py`
- `backend/tests/test_phase3e.py`
- `backend/tests/test_phase3e_rehearsal.py`
- `frontend/src/lib/custodyApi.ts`
- `frontend/src/pages/Inventory/IdentityRegistration.tsx`
- `frontend/src/pages/Inventory/InventoryCustody.tsx`

New deliverables:

- `docs/phase3-planning/PHASE_3E_IMPLEMENTATION_REPORT.md`
- `docs/phase3-planning/PHASE_3E_ACCEPTANCE_MATRIX.md`
- `docs/phase3-planning/PHASE_3_RELEASE_READINESS.md`
- `docs/phase3-planning/PHASE_3E_REPRODUCIBILITY_MANIFEST.json`

Updated cross-references:

- `docs/phase3-planning/PHASE_3_IMPLEMENTATION_PROGRESS.md`
- `docs/phase3-planning/PHASE_3_TEST_REPORT.md`
- `docs/phase3-planning/PHASE_3_READINESS_REPORT.md`
- `docs/phase3-planning/PHASE_3_FRONTEND_INTEGRATION.md`

The reproducibility manifest records exact source hashes, status, task paths and portable test evidence; it excludes itself from hashing. Phase 3D's manifest and client originals are preserved. Review this complete working tree before any separately authorized Git checkpoint. No Phase 4 work was started.
