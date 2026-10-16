# Development Status

## Persistent quotation drafts — 16 October 2026

Save Draft now writes owner-scoped QuotationDraft records through /api/quotation-drafts/ and awaits a confirmed database response before reporting success. Real sessions load all saved drafts after login/refresh; edit/detail routes wait for loading. Editor metadata retains product/model/costing references, unit identity, prices, contacts and terms. Server snapshot review state reconstructs pending/approved/rejected/sent status. Repeated edits use row versions, conflicts return 409, and submitted snapshot IDs are frozen. Demo drafts remain session-only. Full costing/model/master persistence and commercial customer-response/order-conversion lifecycle remain separate.


## User roles and quotation rejection — 16 October 2026

Added a persisted Role master and user role assignment, including Project Manager. Masters → Users now creates real Django users and assigns active roles through superuser-only APIs. Users can also be assigned roles in Django Admin. Project/Production Manager roles receive quotation view/review permissions; ordinary users are not made staff/superusers. Managers see server-submitted quotations, expand full public line/contact/tax/terms details, and approve or reject with a required reason. Decisions persist with actor/time; rejected snapshots cannot be sent, resubmitted or later approved. Browser live-account interaction is not claimed; role/login/review API tests and frontend checks validate the implemented flow.


## Editable quotation selling price — 16 October 2026

Draft quotation unit prices are editable for both stock and customized products. The number input now retains blank and decimal entry state. Custom manual selling-price changes retain approved costing/model validation and require manager review before delivery; source changes/reapplying costing clear the manual override.


## Real superuser login — 16 October 2026

Real Django login is now the default; demo mode requires explicit VITE_ENABLE_MOCK_LOGIN=true. Added local frontend API configuration and clearer credential/backend/throttle errors. Existing superusers carrying the inherited receptionist default are presented as admin in the authenticated profile; backend permission/manager approval rules remain enforced. No password was changed.


## Quotation units and line totals — 16 October 2026

Added the persisted Unit master, seeded kg/ctn/pcs/roll/pack/ltr/m, authenticated paginated units API, Django admin and Masters → Units add/activate/deactivate controls. The quotation unit selector reads active backend units; stock variants retain their declared unit and custom-unit changes reset costing. Unit-price VAT basis and an inclusive price readout are explicit. Server quotation lineTotal is quantity × entered unitPrice, rounded once to two decimals; VAT is included or added according to the selected document basis. Native PDF headers now state the VAT basis and preserve entered price precision. Backend tests and quotation helper/type/build checks passed; PDF was rendered and visually inspected.


## Quotation manager approval and saved customers — 16 October 2026

Manager approval now gates real email/WhatsApp delivery. Real submission persists the snapshot, and Production Managers review a backend pending inbox. The server requires manager role plus approval permission and rejects unsubmitted/unapproved or changed snapshots for delivery. Sender self-approval controls were removed. Customer creation from quotations now persists the extended Django customer master and reloads it in real sessions; demo writes are rejected explicitly. Full commercial editor/lifecycle state remains session-only.


## Login refresh fix — 15 October 2026

Authentication now restores saved backend identity before protected routes redirect, refreshes expired access tokens once per concurrent group, persists rotated tokens and clears invalid credentials. Remember me selects persistent storage; unchecked login uses tab storage. Demo sessions restore across reloads only in enabled mock mode. Backend outages retain credentials and offer retry. Browser demo login → protected-page refresh and logout → refresh were verified; real token restoration/rotation/error cases pass mocked adapter checks. Existing business-record stores remain session-only.


## Quotation PDF and delivery — 15 October 2026

The detail screen now has PDF / Email / WhatsApp controls with independent opt-in checkboxes, customer email and editable +916282744675 WhatsApp recipient. The sibling `../Backend` Django service persists immutable public PDF snapshots, computes decimal totals, extracts persisted order/customer/line details, requires server PDF approval and records per-channel delivery results. SMTP and Meta WhatsApp Business template credentials must be configured; no real transmission was tested. Existing quotation editing, commercial lifecycle and conversion remain session-only. Native A4 reference PDF was rendered and inspected; full browser interaction is not verified. See `../Backend/quotations/README.md`.

## Monorepo layout — 15 October 2026

The parent Navapack-ERP directory is the shared Git root for frontend/ and backend/.
Frontend source and demo behavior are preserved. Continue running npm commands from
frontend/. The Django Phase 1 foundation is tracked independently in backend/;
its existence does not establish frontend API integration or domain persistence.
Vercel Root Directory must become frontend when the migration reaches the deployed
branch. See [migration and deployment](../../docs/MONOREPO_MIGRATION.md); remote
deployment settings are unchanged by this local migration.

## Client-confirmed LED MAX / Finance demo follow-up — 15 October 2026

Higher of the Two is now the default for new applicable LED records: MAX(2.5% × chosen base, eligible KG/1,000 × USD 70 × saved FX). Percentage base is still pending clarification/configurable; applicability and VAT-on-LED stay explicit. Shared led.ts is connected to stock reverse-price analysis, recipe costing, stock/custom quotations, direct/converted Sales Orders, dispatch-value metrics and partial invoices. Both alternatives/selected branch/FX/date/conversion remain immutable snapshots. Missing weight/conversion/FX/base/date blocks finalization rather than percentage fallback. Base VAT-inclusive/exclusive logic remains, with LED and optional VAT on LED added once. Historical records are preserved.

The existing user-authored FinanceDashboard/accounts sidebar is reused with `/finance/login`, finance@navapack.com / test@123 in mock-enabled mode, Accounts / Finance demo selector, finance home label/navigation and restricted read-only Quality summary. Wrong credentials reject; successful finance credentials resolve accounts and open FinanceDashboard. Real sign-in uses the existing API with accounts role check. Detailed QC permissions remain unchanged; production mock mode stays explicitly opt-in. No invented revenue/expenses/collections or backend accounts.

Passed: new check-led-finance plus all eight existing regression scripts; standalone TypeScript/build and Git whitespace review. Concurrent check processes emit existing non-fatal Vite WebSocket port warnings; build retains its large-chunk warning. Focused tests cover MAX percentage/weight/equal and missing inputs, exact product/model conversion, cost→quote→order frozen FX/history, inclusive/exclusive VAT, separate LED and partial-invoice reconciliation, mixed-line dispatched financial values, public redaction and demo credential/mode gating. Browser smoke verified separate finance page, bad-password rejection, successful accounts landing, Finance Dashboard home link and read-only Quality summary navigation. Finance Stock view displayed Higher of the Two by default and rejected a save with missing CTR weight/FX; no test financial snapshot was posted. A finance preview screenshot was saved in the chat visualization directory. This does not establish backend persistence or all-role end-to-end coverage.

Run `npm run dev`, then `/finance/login`. Demo state resets on refresh; real session restoration, account provisioning/server authorization and durable financial snapshots remain backend requirements. Full formulas, client-confirmed vs pending rules, demo limits and exact follow-up changed-file list are in [the report](sales-fulfillment.md#client-confirmed-led-max-and-finance-demo--15-october-2026). No backend changes, dependencies or commit.

## Integrated operations — 15 October 2026

Implemented frontend enhancements across Stock/Costing, Dashboard, connected Track & Trace, Sales Order list/detail, parent/item Job Card tracking, quotation workflow/settings/Customer Masters, and QC dashboard/template configuration. Existing inventory/order/job/model/costing/quality contexts, routes, reference data and workflow guards are reused.

New shared StockIntelligence/StockAlerts, SalesSummary, ProductionTimeline/ProductionRuns and GenerateQuotation components expose configurable VAT/LED/markup-vs-margin/COP snapshots; product/model effective KG–CTR versions; product-specific alerts; optional-reservation confirmed dispatch; unit/currency-separated sales metrics; ID-linked costing/trace movement facts; append-only stage runs; source-idempotent quotation generation, internal rejection/change comparison/email drafts; and explicit QC schedule/occurrence generation. KSEC remains inactive/undefined; weekly templates remain weekly.

Validation: all eight scripts passed (`check-integrated-operations`, `check-quotations`, `check-quality`, `check-sales-fulfillment`, `check-job-cards`, `check-custom-costing`, `check-finished-goods`, `check-inventory-workflows`); TypeScript/build and Git diff whitespace checks passed. Concurrent Vite SSR checks emitted non-fatal WebSocket port-in-use warnings; the production build retains the large-bundle warning. QC regression now explicitly verifies inactive KSEC cannot create inspections; all six active template tests remain.

Browser smoke on the local Admin demo verified six-section dashboard rendering, saved product `ctn` conversion, saved financial snapshot and Trace navigation showing matching KG/estimated COP, repeated Generate Quotation returning QT-1, and a QC source/schedule with duplicate generation retaining the same count. No email was sent, public portal accessed or production stock posted. This is targeted smoke coverage, not all-role/end-to-end or print-layout verification. Initial localhost attempt timed out before Vite was ready; retry succeeded. A dashboard screenshot was saved outside source in the chat visualization directory.

Canonical formulas, roles, changed-file inventory, backend ownership/capabilities/atomicity and unresolved business rules are in [the existing report](sales-fulfillment.md#integrated-operations-update--15-october-2026). All new state resets on refresh. Actual total costs need manual evidence; material-batch consumption/process expenses are not invented. Backend persistence/server permissions/locks, email PDF/provider/outbox/delivery, secure customer links and background recurrence remain future work. LED percentage base/applicability/VAT treatment (MAX comparison is now confirmed), conversion weights, thresholds, KSEC/shift/calendar rules and missing reference documents/photos require confirmation. No dependencies/backend files or automatic commit.

## Quotations and Proforma Invoice module — 13 October 2026

Implemented dedicated list/detail/edit/preview/revision/approval/customer-response/conversion screens; shared customer/prospect/company/bank/terms session state; quotation-source costing using the existing engine; and idempotent conversion into existing Sales Orders with parent Job Card eligibility. Accepted inclusive/exclusive/discount/rounding snapshots carry through orders and partial/final invoices. Added derived quotation dashboard metrics/CSV and A4 browser printing. Updated the ERP report and workflow diagram; canonical proposed Django sales model/API/transaction contracts are in quotations.md.

All seven helper suites, TypeScript and production build pass; bundle warning remains. Both referenced client documents were absent, so exact source layout/signature/identity and browser print validation remain outstanding. No persistent backend, server roles/locks, tax/fiscal certification or external communication is implemented. Existing operations demo metrics and earlier amendment/internal-production/reservation-free dispatch pending work remain separate.

## Quality Control module — 13 October 2026

Implemented dedicated QC routes/dashboard, same-login QC Inspector/Supervisor roles, six provisional versioned templates, up to eight samples/explicit measurements, immutable submission/independent review/reinspection, NC action history, raw receipt holds, mandatory item routing checkpoints/machine verification and separate quality/final-stock authorizations. Store postings and held-batch dispatch use shared inventory guards. Excel-readable XML and browser Print/Save as PDF use no new dependencies. Shared machine IDs live in ModelsContext. Complete report section and canonical proposed Django quality-app/models/API/transactions are in sales-fulfillment.md and quality.md.

Eight photographs were absent; paper codes/revisions remain unverified. All QC data is session-only. Separate execution runs, supplier receipt metadata, persistent assignments/attachments/schedules, server permissions/atomic postings and native XLSX/PDF exports remain backend work. TypeScript/build and all six helper suites passed; browser interaction was blocked by localhost timeout and unavailable Chrome. Existing bundle warning remains. Reservation-free dispatch and other earlier parent-workflow pending phases remain separate work.

## Client-confirmed parent-card integration — 13 October 2026

Implemented the relationship portion of phases 1–2: one new parent Job Card per Sales Order, independent manufacturing items, complete-scope atomic parent approval, item controls/history and parent receipt traceability. Historical cards remain unchanged. TypeScript, production build and all five check suites passed, including focused parent regressions; browser verification was not performed. Vite retains its bundle warning.

This is a coherent partial delivery, not completion of the 22-section task. Order amendments, production for stock, additional issues, Supervisor/Manager FG approval, dispatch without reservation, expanded reports/exports and live dashboard remain pending. Existing explicit allocation and Store/Admin QC behavior remains active. Everything remains session-only. Details and backend requirements are in sales-fulfillment.md.

Repository baseline: routed frontend pages exist for all nine modules. No backend source or verified end-to-end persistence is present. API attempts with mock fallback are not marked Integrated.

## Module status

- Dashboard: frontend/mock role-specific widgets and navigation; static metrics, not synchronized with orders/inventory. Backend pending.
- Sales Orders: frontend/mock fast-entry multi-line form, validation, filters, sorting, pagination and CSV export; shared navigation-safe Context. Backend pending.
- Job Cards: data-derived summaries, combined search/status/department/stage/date filters, detail tabs, approval/edit, full/partial material issue, dynamic production tracking and handovers, stage waste, activity history, delay warnings and frontend Stock Keeping confirmation. Existing stage toggles/API fallback retained; shared navigation-safe JobCardsContext. Linked-order receipts now post into shared frontend inventory; backend persistence remains pending; custom requirements now derive from explicit model/estimate recipes.
- Stock: frontend/reference variant inventory, Brand → Pieces → Packaging columns, optional pieces-per-package metadata, detailed Stock IN/OUT, history, monthly reporting/export and open-order demand comparison. Backend pending.
- Raw Material: frontend/reference category/family views, combinable family/unit/status filters and search with reset, Stock in Hand labels, detailed Stock IN/OUT, balances, movement history and monthly CSV reports. Backend pending.
- Consumables: frontend Add/Edit/View, Imported Spare/Local Spare categories, Each/Both/Litres/Kilos units, search/filter/reset, Stock IN/OUT and movement history. Starts empty; navigation-safe state resets on refresh. No Spare Parts module exists in this checkout. Backend pending.
- Recycling: waste/granule read views and summaries; API/mock fallback. No intake/production posting workflow. Backend pending.
- Costing: cost/rate read views and rate entry; API/mock/local fallback. No cost recalculation. Backend pending.
- Track & Trace: search and history display; API lookup with seeded examples on failure. Backend pending.
- Masters: shared session-only revisioned model drafts used by orders/costing/jobs; other item/customer/supplier/department/user edits remain page-local. Backend persistence pending.

## Sales fulfillment update

Sales Order detail, per-line manual fulfillment, linked custom jobs, QC-confirmed partial receipt batches, reservations, partial dispatch/reversals and invoice snapshots now share session state. Stock includes reserved/available balances and date-range history. See [implementation, checks and limitations](sales-fulfillment.md). Browser verification is blocked by browser access to localhost.

## Recently Completed

Available in the inspected baseline (not a claim about implementation dates): multi-line sales entry, separate finished-goods/raw-material ledgers, workbook-derived reference loading and finished-goods demand comparison.
Documentation baseline now records actual architecture, models and integration gaps.

## Currently In Progress

Overall phase: frontend workflow validation. No separate active implementation task is inferred from this snapshot.

## Next Priorities

- Confirm authoritative inventory reservation/issue/production/dispatch rules and source-data ambiguities.
- Plan durable orders, masters and inventory integration at the existing state boundaries.
- Replace silent mock/local write fallback with explicit success/failure behavior during integration.
- Connect dashboard/recycling/master data flows and verify server permissions.

## Review limitations

Local orders and inventory reset on refresh; non-model page-local master edits reset on remount; shared model revisions reset on refresh. Job-card stage and costing-rate writes may appear updated after an API failure.
Authentication is not restored from stored tokens. Role-filtered navigation is not server access control.
Recycling and costing summary month labels do not filter loaded rows by month; Dashboard uses separate demo currency/metrics.

## Verification

Documentation-only changes do not change application behavior. Use README commands for typecheck, build and the finished-goods data check; no lint setup exists.

Baseline checks passed: TypeScript without emit, Vite production build to a temporary directory, finished-goods checks, Markdown links and Git whitespace checks. Standard npm run build could not write the existing tsconfig.tsbuildinfo (EPERM); the separate checks avoid that file. Vite reported a bundle-size warning.

Inventory update verification: TypeScript passed using a temporary incremental cache; Vite production build and both inventory data-check scripts passed. Browser checks covered Consumables Add/Edit/View, categories/units, filters/reset, movement history and navigation-safe state; Raw Material combined search/filters and IN/OUT; Finished Goods pieces prefilling and IN/OUT. No browser console errors were captured in these workflows. Desktop/tablet layouts and mobile modal containment were inspected. The existing fixed-width sidebar remains limiting on narrow screens. Standard npm run build still hits the pre-existing tsconfig.tsbuildinfo EPERM; Vite still reports the existing bundle-size warning.

Job Cards upgrade verification: TypeScript with a temporary incremental cache, Vite production build, manufacturing invariant checks and both inventory checks passed. Browser checks covered combined filters, required stages, editing/approval, partial/full issue, stage completion, same-unit handover, mixed-unit safeguards, waste/history, stock confirmation and completed-card locks. No console errors were captured during those workflows. Tablet forms were inspected; the existing fixed sidebar limits narrow screens. Standard npm run build retains the existing tsconfig.tsbuildinfo EPERM; Vite retains its bundle-size warning.
Final clean reload rendered Job Cards correctly. Development hot updates briefly produced a provider-context mismatch; reloading cleared it. Backend integration still needs durable workflow storage and atomic inventory posting.

## Custom costing and routing — 2026-10-09

Implemented and connected frontend custom lines, versioned models, recipe/process costing, USD/UGX snapshots, markup scenarios, estimate revision/approval/printing/customer response, linked draft Job Cards, dynamic PM routing and approved-stage tracking. Store issue remains local tracking; unmapped QC output retains prepared receipts. Actual Cost/Variance are unavailable. TypeScript, build and all five workflow checks passed; browser UI/printing validation remains unavailable and Vite reports a large-bundle warning. No backend/dependencies/contracts changed. See [changed files, formulas, assumptions and remaining integration](custom-costing-routing.md).
