# Phase 4A implementation report

20–21 October 2026, Asia/Kolkata. Repository `F:\WORK\Navapack-ERP`.

## Outcome and Phase 4B recommendation

Implemented a bounded, synthetic-only commercial foundation. **NO-GO for Phase 4B approval/operational expansion** until the blocking client policy decisions and browser acceptance below are closed. This is not approval to migrate, grant permissions, commit, push or deploy.

The gap analysis was written before commercial implementation. Actual source, Phase 3A–3E reports, original SOP XML and workbook XML were inspected. All 28 client-original SHA-256 hashes match the designated manifest. The supplied stock books have 283 raw-material formulas and 307/848/271 finished-goods formulas; the raw KG/Bag headers, cross-row BO4/BO5 references, negative BQ25 cache and Packing opening-date inconsistency are retained as observations. No costing workbook appears among those originals. Frontend historical costing/LED statements are conflicting evidence, not client tax approval.

## Implemented source and migrations

- New `backend/apps/commercial/`: strict Decimal contracts/calculations; CommercialDocument/CommercialRevision; transactional/scoped services; DRF views/URLs; additive migrations `0001_initial` and `0002_evidence_guards`. Reuse existing master/specification identities, employee/capability checks, catalog lock, row-version locks, idempotency, audit and stamped synthetic environment. Database guards enforce immutable evidence and atomic audited revisions.
- `backend/config/settings/base.py` registers the app; `backend/config/urls.py` mounts its separate API namespace. `backend/apps/accounts/serializers.py` extends the existing inventory explicit-permission presentation rule to commercial permissions, preventing a technical superuser profile from advertising ungranted commercial authority.
- New `backend/tests/test_commercial.py`: PostgreSQL calculation/security/workflow/rollback/concurrency tests. New `backend/tests/test_commercial_transport.py` exercises actual React TypeScript adapter functions through JWT/HTTP against disposable Django/PostgreSQL.
- `backend/tests/test_phase3e_rehearsal.py`: retain the original exact 20 Phase 3 migration assertion and explicitly assert the additional commercial guard migration. No original inventory/QC guard, ledger, workflow or posting service changed.
- New `frontend/src/lib/commercialApi.ts`, `frontend/src/pages/Commercial/CommercialFoundation.tsx` and `frontend/scripts/check-commercial-api.mjs`. Existing App and AppShell gain a separate backend-session entry point; existing demo commercial contexts/pages remain separate.
- Updated backend development status and frontend development status, models, rules, integration TODO and changelog. Created all four requested documents under `docs/phase4-planning/`.

No configured application migration was applied. Read-only migration plan reports **22 pending migrations**, comprising the previous 20 plus the two new commercial migrations. All schema application/rollback/backup-restore rehearsal occurs in generated disposable PostgreSQL databases only. No operational imports, stock postings, real financial records or permission grants were created.

## Supported behavior and explicit limits

Costing supports multiple gross-consumption material components, process amounts, loss assumptions/evidence, explicit output quantity, estimated production cost, native unit cost/kg/ctr, suggested markup pricing and separate entered gross margin. Product costing can exist without a customer or sales order; quotations and sales orders retain their required party references. Exact Decimal strings, unit/currency checks, declared rounding and immutable snapshots prevent silent FX or unit conversion. Loss assumptions are recorded rather than applied a second time to gross inputs. Actual cost is unavailable.

Quotations and orders support multiple exact product lines, specifications/customisation, retained costing revisions, existing customer/prospect identity (orders require Customer), optional classification/marketing Employee/date references, entered prices/discounts/terms, immutable history and governed draft edits. Stock identity/warehouse references require existing capability/scope and assert no reservation. DRAFT/REVIEW/pre-approval cancellation are supported. Approval, confirmed-order amendment/cancellation, quotation acceptance/conversion, customer-facing delivery, PDF/email, production, invoicing and dispatch remain blocked.

Owner-only commercial access is a conservative development restriction, not a client-approved visibility policy. No customer-facing price template is invented. The basic frontend form supports one material/process input per costing line; API contracts support up to 100. Drafts with advanced fields not represented by the form cannot be edited through that form. Full snapshots/history and the API retain those fields.

VAT/LED/final payable totals are null, never zero-tax claims. The new contract rejects tax/levy override fields. It does not reuse the frontend Number-based LED calculator as server authority. See P4-01 for the 1,000-units versus tonne/FX conflict and P4-02 for currency/rounding.

## Verification evidence

Ignored local logs are under `backend/.local/phase4a/`. Verification completed after midnight on 21 October 2026, Asia/Kolkata.

- Complete regression: **275 tests passed in 911.711 seconds**, including all 251 existing cases and the then-current 24 commercial/transport cases, in generated database `test_phase3b_394050df5f0f4856948b03e33c3a9cc9`. The final 25-case commercial rerun below additionally validates customer-independent costing. There are 276 distinct covered cases across these runs; this is not a claim that a single 276-case run was executed. The complete regression includes Phase 3 API/security/ledger/QC compatibility and the corrected upgrade/recovery rehearsal. Both generated primary test databases and the recovery clone were destroyed.

- Focused final commercial/transport run: **25 tests passed in 101.625 seconds**, fresh stamped PostgreSQL database `test_phase3b_dd16f913dd4d4616a64be2a5f9837e01`, destroyed by the runner. Includes a real Node/Vite-loaded TypeScript adapter with actual JWT login, HTTP persistence, unchanged-key retry, costing snapshot linkage, stale edit, review/reopen/history and multi-line order; verifies no ledger/balance rows. This final rerun also covers the added customer-independent costing case, while retaining mandatory parties for quotations/orders.
- Django system checks: passed, no issues. Migration drift: passed, no changes detected. Commands use `config.settings.test`; application migration status is read-only.
- Frontend TypeScript `--noEmit` and production build: passed. Existing large-bundle warning remains; no build output staged.
- All 13 pre-existing `scripts/check-*.mjs` scripts passed. New commercial transport contract script also passed (14 scripts total). Mocked adapter checks and real-backend adapter acceptance are reported separately.
- Corrected populated upgrade/independent backup-restore rehearsal: **1 test passed in 63.970 seconds**. Preserved the original 20 Phase 3 forward migrations plus the explicitly enumerated commercial guard migration, historical identities/audit, 12 recovered table fingerprints and enabled database triggers; unstamped restored ledger writes remained rejected. Generated source and recovery databases were destroyed. This is Phase 3 recovery compatibility, not a populated commercial recovery certification.
- `git diff --check`: passed (existing CRLF normalization warnings are informational).

Earlier attempts are retained honestly: first focused run passed 18/20, finding an unknown-field formatting 500 and a wrong test expectation about shared exception handling. Both were corrected; 20/20 then passed. First live transport attempt failed because LiveServerTestCase's settings wrapper resets SETTINGS_MODULE metadata to None. The test now explicitly preserves the genuine test module while retaining the database-name/nonce/environment gates; no production guard was changed. The initial broad regression ran 271 tests in 731.221 seconds, with one hard-coded migration-count failure (21 versus 20) and 65 dependent errors after that failed rehearsal left its disposable schema downgraded. The final run uses the explicit additive migration assertion and a fresh database.

No browser visual acceptance is claimed. The earlier Phase 3 report records browser tooling disabled in Work settings; actual TypeScript HTTP acceptance supplies integration evidence, not UI interaction/screenshots, print acceptance or customer approval.

## Preservation and release limits

Entry HEAD `5f5c775108ee35f946519bae4474cacf272d9cbc`; origin `https://github.com/Careergize/ERP-Navapack-frontend.git`; existing Phase 3E dirty/untracked work preserved. Before documentation/rehearsal updates, 344 of 349 Phase 3E manifest entries matched exactly; the only five differences were the intended account-profile/configuration/App/AppShell edits. The later rehearsal change is explicitly listed above. Existing uncommitted Phase 3E application source was not rewritten. No staged changes, commit, push, remote settings or deployment action.

Final preservation check: **337/349 prior manifest entries remain byte-identical**. The 12 differences are exactly the five shared-code edits, the rehearsal assertion and six development/model/rule/TODO/changelog documentation updates listed in this report. All 28 client originals still match. Final read-only database verification found **zero remaining databases among all 10 generated test/recovery names recorded by this task**, and the configured application still has 22 pending migrations. The loopback PostgreSQL cluster started for verification was stopped. Logs, backups, dependencies, environment files and build output remain ignored; the Git index is empty. Local verification summary: `backend/.local/phase4a/final-verification.json`.

This worktree still needs a separately authorized reproducible checkpoint. Do not treat untracked commercial sources or passing disposable tests as deployed availability. Runtime database grants, private evidence retention, client policy publication, operational migration/restore and browser acceptance require separate review.

## Reproduction commands

From `backend`, with the local test cluster available:

```powershell
.venv/Scripts/python scripts/test_isolated.py --synthetic-ledger tests
.venv/Scripts/python manage.py check --settings=config.settings.test
.venv/Scripts/python manage.py makemigrations --check --dry-run --settings=config.settings.test
```

The isolated runner generates a new database name, installs the existing nonce stamp and destroys that database; never substitute an application database or reuse a test database. Node/Vite and PostgreSQL 16 dump/restore binaries are required by the integration/recovery tests. The genuine settings module is retained explicitly around LiveServerTestCase HTTP calls because Django's test settings wrapper otherwise clears its metadata.

From `frontend`:

```powershell
node node_modules/typescript/bin/tsc --noEmit
npm run build
Get-ChildItem scripts/check-*.mjs | ForEach-Object { node $_.FullName; if ($LASTEXITCODE) { throw $_.Name } }
```

These commands do not send customer communications or deploy build output.

## Next steps and gate owners

Management/Finance must resolve P4-01/02/04 (tax/levy, monetary policy and authority) with dated controlled evidence; Production/QC/Finance must resolve P4-03 (gross/net/yield/unit rules); Sales/Management/IT must resolve P4-05/06 (access/acceptance/document standards). Complete P4-08 browser and release acceptance. Phase 3 opening/ownership/QC/period/dispatch decisions remain prerequisites for later inventory/production integration.

After those gates, separately scope Phase 4B around governed independent approvals, immutable policy versions, confirmed-order amendments and explicit quote-to-order acceptance. Preserve the current demand-only order boundary, no reservations, physical-dispatch-only stock deduction, parent-order Job Card option and independent stock manufacturing. Do not start execution or fiscal/dispatch integrations on the basis of this report.
