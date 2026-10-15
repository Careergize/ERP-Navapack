# Backend implementation roadmap

15 October 2026. Planning only; no backend implementation authorized by this audit. Read [readiness](BACKEND_READINESS_REPORT.md) and the unresolved decision register in [SOP gaps](SOP_FRONTEND_GAP_ANALYSIS.md) before domain work.

## Phase 0 — evidence and integration boundaries

Baseline current working tree and preserve existing changes; inventory actual API expectations and agree versioned response adapters. Obtain SOPs, source workbooks/photos/commercial references. Resolve role scope, inventory opening/units/locations and decimal/rounding policy. Agree route guards and forbid silent demo fallback in production. Preserve UI behavior during integration; do not rewrite all stores at once.

Exit: approved decision log and source-ID mapping strategy, user/object permission matrix, documented safe demo mode, baseline tests recorded. Foundation need not wait for every later fiscal/recycling decision.

## Phase 1 — foundation, identity and audit

One Django project/DRF/PostgreSQL; configuration/environment separation, health/readiness checks, structured errors/request IDs, JWT login/refresh/me/logout, active user/permission checks, audit/idempotency/concurrency infrastructure, test database/CI. No manufacturing or stock posting initially. Agree production token storage/client handling and user restoration. Scope permissions by company/object if multi-company is confirmed.

Frontend integration: replace AuthContext/API lifecycle only; add explicit validation/error mapping and production fallback policy. Test unauthenticated/forbidden/stale token/expired refresh/logout/restoration/re-login data lifecycle. Health endpoints expose no secrets or fabricated business counts.

## Phase 2 — governed masters and import staging

Customer/prospect/supplier/department/user lookup, unit/material/FG variant/consumable/model revision/machine/area/company/terms settings. Stage workbook imports with provenance and null openings; exclude demo sources; reconcile repeated variants rather than deduplicate by name. Establish stable IDs and compatibility adapters for existing seed references.

Exit: master authorization, versioned model/template source identity, reviewed import mappings, pagination/search, exact unit compatibility; no synthetic supplier/batch acceptance. Tests cover protected historical revisions and unknown balances.

## Phase 3 — inventory ledger and minimal quality foundation

Create authoritative append-only scope-separated ledger/location/batch model and idempotent command services, optional atomic balance projections, opening imports, conservative holds/usability, report projections, reservations and reversals. Define WIP/material issue vs consumption accounting before writes. QC template versions/inspection/review/release source identity should arrive here because raw usability and later manufacturing/dispatch rely on them.

Exit: concurrent OUT/receipt tests, no double-post/replay, rollback/audit, future/as-of/backdating checks, no unknown→0, no unlike-unit sums, raw receipt held until release. Integrate Stock/Raw/Consumable read views and permitted manual movements; leave ordinary manufactured IN guarded until phase6.

## Phase 4 — costing and commercial operations

Persist versioned formula configuration, model/recipe/process/FX/LED/conversion snapshots and estimate approvals. Then quotations/family revisions/party/settings/terms/internal review/manual customer responses/source validation, Sales Orders/lines, atomic quote conversion/adoption and numbering. Include standalone SO create demand-only. Costing moves earlier than a generic finance-last plan because current custom quote/order-to-job creation depends on saved estimates and model revisions.

Exit: exact source/version validation, public projection redaction, immutable accepted commercial amounts, server Decimal parity, partial-invoice allocation test fixtures prepared. Resolve LED base and invoice policy before accepting production financial data. Frontend consumes real contexts via adapters and explicit errors; no local success on failed save.

## Phase 5 — parent production planning and issue

Normalize parent/child cards with complete manufacturing scope, legacy preservation, atomic PM review/approval, configurable route snapshots and checkpoints, real material batch issue/WIP transaction, scoped machine/operator identity. Support for-stock only after confirmed source/receipt design; never fabricate order IDs. Additional issues/amendments require explicit permissions and audit.

Exit: one new parent per order, unique child line scope, all-or-none approval and no-self rules if approved, exact requirement/stock checks under concurrency, immutable approved/started route, trace-preserving historical migration policy.

## Phase 6 — execution, QC completion, FG and dispatch

Persist multiple production runs, sequential stage completion/handover/machine QC guards/output lots/waste/loss evidence; integrate full QC answers/review/reinspection/NC actions/checkpoint coverage; separate final managerial stock authorization; idempotent FG receipt; optional allocation/direct partial dispatch/reversal. This phase depends on phase3 ledger and QC foundation, phase4 source snapshots and phase5 approved routes.

Exit: complete source chain plus explicit missing facts; concurrent holds block dispatch/receipt atomically; overissue/output/authorization/dispatch prevented; legitimate partial lots and multi-input/output paths covered; no physical deduction at SO creation. Recycling write workflows remain gated on actual SOP intake/disposition/yield rules, not merely these waste fields.

## Phase 7 — billing, reporting and confirmed extensions

Immutable invoice snapshots from uninvoiced confirmed dispatches; frozen tax/discount/LED proportional allocation and final reconciliation, credit/adjustment/payment/expense policies if approved. Add scoped sales/operations/finance/QC/inventory/trace projections, scheduled QC occurrence worker only with authoritative calendars. External fiscal/accounting/mail/PDF/public-link capabilities require separate confirmed contracts; mail outbox and customer-safe artifacts must never expose internal cost data.

Procurement, recycling execution/external jobwork and maintenance are requirements-gated workstreams. Their masters/ledger/QC dependencies can be prepared, but absent SOPs and frontend forms do not justify guessed production workflows. Their detailed delivery order follows confirmed operational priority, not current sidebar ordering.

## Verification strategy

Frontend baseline: TypeScript, build and all nine focused check scripts. These execute pure helper/invariant assertions and do not replace browser/server tests. Adapter tests must assert bare-array→paginated compatibility and camelCase→snake_case mapping. Browser tests: all routes/roles including direct URLs, draft validation, fallback errors/retries, create→navigation→refresh, separate users, modal rejection recovery, printing/downloads and tablet/mobile/Capacitor paths once configured.

Backend: unit tests for decimal formulas and all lifecycle transitions; API validation/permissions/object scope; integration tests for FK/protected history/import source; DB transaction tests with concurrent connections for stock/hold/approval/replay/run completion/quote conversion/billing; idempotency same/different payload and timeout retry; atomic rollback after injected failure; ledger/projection rebuild parity. Finance golden cases must cover MAX percentage/weight/equal, missing KG/FX, inclusive/exclusive VAT-on-LED, fractional unit rates, final rounding and historical FX immutability.

End-to-end acceptance: approved masters → draft/approved estimate → quote approve/send/manual acceptance → order (no stock) → complete parent manufacturing scope → PM approval → raw issue → optional configurable processes/runs → QC lot/independent review/quality release → manager authorization → partial FG IN → direct/optional reserved partial dispatch OUT → immutable invoice → allowed reversal/credit policy. Include failures and mixed units/partial quantities, not just happy path.

## Audit validation run (15 October 2026)

From frontend: `node ./node_modules/typescript/bin/tsc --noEmit` completed successfully. All nine scripts passed: check-finished-goods, check-inventory-workflows, check-job-cards, check-custom-costing, check-sales-fulfillment, check-quality, check-quotations, check-integrated-operations, check-led-finance. Their output has ten result groups because parent-card assertions have a separate success line. Do not treat a passing old “unchanged inventories” helper test as proof that the newer Context receipt path never posts inventory.

Discovery commands that used `rg --files` filters for absent SOP/PDF/DOCX/Capacitor matches returned exit1/no matches; this means references were not found, not that application compilation failed. `Get-Content README.md` at the enclosing workspace had no file (suppressed error); actual README is in frontend. No dependencies installed. No browser/live backend tests performed.

Production bundling: `node ./node_modules/vite/bin/vite.js build --outDir <new temporary directory>` passed (Vite8.3.0, 1,712 modules; JS bundle approximately 1,137 kB / 240 kB gzip). Vite warned about >500 kB chunks and explained that the external temporary outDir would not be emptied; it was a newly created unique path. Typecheck and Vite were run separately to avoid touching the existing incremental build cache or existing dist. The standard npm build was not run during this audit; earlier docs' cache EPERM failures were not reproduced as a claim about this run.

Coverage evidence: 103 source TS/TSX/CSS files read; 121 named TS interface/type/enum declarations cataloged, 309 JSX action/form/navigation elements and associated form fields/column arrays cataloged; 146 calculation/validation/transition source excerpts retained. These counts describe static evidence, not 309 individually browser-tested controls. Existing config/docs/scripts were additionally inspected. Generated reference record bodies are not duplicated in the audit; provenance hashes and actual source arrays remain available.

Documentation verification passed: eight requested Markdown files, 37 local document links resolved, 273 fenced source/schema/diagram blocks balanced, all 103 recorded source hashes unchanged and no trailing whitespace. `git diff --check -- docs/backend-planning` returned success; because these are new untracked documents, the explicit whitespace/link/fence scan supplies the substantive content check. Final Git status for this scope is only `?? docs/backend-planning/`; no existing application files were modified by the audit.
