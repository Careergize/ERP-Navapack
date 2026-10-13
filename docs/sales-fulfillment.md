# Sales fulfillment frontend implementation

## Parent-card delivery summary — 13 October 2026 (before the QC phase)

Delivered the parent Job Card relationship portion of phases 1–2 of the client-confirmed workflow. New manufacturing lines from one Sales Order now join one parent Job Card instead of creating separate line-level cards. Each manufacturing item retains its own product/model identity, quantity and unit, costing revision, material requirements, approved routing, production stages and receipt batches.

The existing JobCardsContext, SalesOrdersContext, InventoryContext, costing helpers and production controls are reused. Parent approval checks the complete manufacturing scope and validates all items before applying approvals. Parent completion requires every manufacturing item to finish. List/detail screens show individual progress and chronological activity; costing recalculation and Stock model filters resolve item-level references. New stock receipts retain both parent and manufacturing-item IDs. Creation and approval do not change physical stock or automatically reserve it.

Validation passed: standalone TypeScript checking, production build, all five workflow check scripts and Git diff whitespace checking. Focused regressions cover parent creation idempotency, mixed-order stock exclusion, independent quantities/units/models, complete approval scope, historical preservation, late-item locks and completion/history aggregation. Vite retains its bundle-size warning. No browser end-to-end verification was performed for this phase.

This delivery remains frontend-only: changes reset on refresh. Historical cards are preserved; adding new manufacturing items to legacy-card orders requires an authorized migration. Stock-line exclusion is an isolated mixed-order assumption awaiting client confirmation. Durable parent/item records, atomic approvals and stock transactions, concurrency, idempotency and server-side permissions remain backend requirements.

Pending implementation includes approval-controlled order amendments, production for stock, additional material issues, Supervisor/Manager finished-goods approval, dispatch without mandatory reservation, expanded stock reports/exports and live dashboard metrics. Current allocation and Store/Admin QC behavior remains active. Mixed-order scope, the physical Job Card format, model-specific conversions/yields and partial-run/excess-stock decisions still need client clarification. The detailed phase boundary and complete changed-file list appear below. No automatic Git commit was made.

This work adds a session-only transaction chain to the existing React stores. No backend files, schema, endpoint contracts or dependencies changed. All state resets on refresh.

## Current implemented behavior

- Sales Orders retain multi-line entry and require a manual fulfillment source per line, transaction currency and tax rate (including explicit zero). Demand creation does not move stock. Tax uses a single transaction rate; line-specific or jurisdiction rule engines are not implemented.
- `/sales-orders/:id` tracks each unit separately, linked jobs, receipts, outstanding allocations, confirmed dispatches and remaining demand. The list derives fulfillment status from the same records.
- New custom lines join one parent Job Card per Sales Order, with independent manufacturing items using selected model stages and stable order/line/product/model IDs. Model BOMs contain descriptions without quantities, so materials are an explicitly editable draft entered before creation and reviewed by PM. Existing approval, Store issue, stage tracking, activity and unit handover validation remain.
- Linked quantity/product/model/unit are protected during Job Card edits. Legacy demo jobs lacking stable product/line links cannot post stock through name matching.
- After all required production stages complete, an exact batch inspection requires independent QC review/quality release and separate Production Manager/Admin final accepted/rejected authorization. Store then confirms the authorized lot/date/quantities. Positive accepted quantity posts an idempotent IN (a fully rejected remainder records QC history without a zero stock movement) to InventoryContext. Multiple partial receipt batches are supported; the job stays Ready for Stock until all final output is accounted for as accepted or rejected. Partial completion of individual production stages remains future work. Each receipt has a stable request ID and source references; no automatic allocation or dispatch occurs.
- Reservations are batch-aware and do not change physical quantities. Allocation requests are idempotent and cannot exceed unreserved known stock or remaining line demand.
- Confirmed partial dispatch posts OUT once, reduces physical and reserved quantities, and derives remaining demand. Recorded-date stock and batch availability are checked. The dispatcher records date, challan, destination, vehicle, remarks, unit, product, batch and stable order/line references.
- Dispatch cancellation appends an IN reversal, restores the reservation, and retains original OUT/history. Invoiced dispatch cancellation is disabled in the UI pending a credit-note/void workflow. There is no order-cancellation or reservation-release workflow yet.
- Manual Finished Goods OUT cannot consume reservations, exceed known stock or consume a production batch as unnamed reference stock. Raw Material and Consumables behavior is unchanged.
- Stock shows physical/reserved/available balances, transaction links/batches, month/year input and optional custom date range. Model filtering includes products with a linked production receipt; unlinked reference stock remains visible under All models. IN/OUT filters narrow movement details, never remove one direction from balance calculations. Unknown historical openings stay unknown.
- Invoice creation uses confirmed uninvoiced dispatches, quantity × order rate, a pre-tax monetary discount and configurable tax. Currency must match the order; conversion is unavailable. Buyer/seller addresses and tax/contact information are manually supplied. No sample supplier/customer is written into masters. Fiscal references are opt-in, supplied manually and unverified; no certified QR or official code is generated. Invoice creation never moves stock.

## Frontend interfaces

`SalesOrderItem.fulfillmentSource`, `SalesOrder.taxRate/currency` and additional display statuses; `JobCard.salesOrderItemId/finishedProductId/modelId/rejectedQuantity/stockTransfers`; movement source IDs, model and batch metadata; `Allocation`, `Dispatch`, `FulfillmentLedger`, `Invoice`, `InvoiceDraft`, and `StockReceiptOptions`.

InventoryContext owns reservations, dispatches, receipts and finished movements through a synchronous current-state ref. JobCardsContext validates completion before posting its receipt; order links use SalesOrdersContext; InvoicesContext retains invoice snapshots. Pure helpers implement transaction guards and calculations.

## Changed files

- `src/App.tsx`, `src/types/index.ts`, `src/components/ui/StatusBadge.tsx`
- `src/context/InventoryContext.tsx`, `SalesOrdersContext.tsx`, `JobCardsContext.tsx`, new `InvoicesContext.tsx`
- `src/lib/finishedGoodsData.ts`, `jobCards.ts`, `salesOrders.ts`, new `fulfillment.ts`, `salesJob.ts`, `invoices.ts`
- `src/pages/SalesOrders/NewSalesOrderModal.tsx`, `SalesOrderList.tsx`, new `SalesOrderDetail.tsx`, `SalesInvoice.tsx`
- `src/pages/JobCards/JobCardDetail.tsx`, `JobCardForms.tsx`
- `src/pages/Stocks/stocks.tsx`, `SalesOrderDemand.tsx`
- new `scripts/check-sales-fulfillment.mjs`
- affected status, business-rules, models, backend, architecture, changelog and this implementation note

## Validation

Passed: TypeScript, production build, all five check scripts and diff whitespace check.

Commands: `node ./node_modules/typescript/bin/tsc --noEmit`, `npm run build`, `node scripts/check-sales-fulfillment.mjs`, `node scripts/check-job-cards.mjs`, `node scripts/check-custom-costing.mjs`, `node scripts/check-finished-goods.mjs`, `node scripts/check-inventory-workflows.mjs`, `git diff --check`.

The new suite verifies stock-only order creation, explicit source/currency/tax validation, linked model-based job creation, parent/item scope and completion guards, material draft guards, reservation idempotency and no physical deduction, partial dispatch/remaining quantities, repeated OUT prevention, batch/date bounds, reversals, unknown openings, month/range carry-forward, tax/discount/words and no invoice stock mutation, QC/approval guards and repeated/partial receipt batches. Existing suites cover PM approval, material issue, production ordering/handovers and reference-data/raw-material/consumable regressions.

Browser-driven UI verification was attempted but blocked: the in-app browser timed out reaching localhost, and the Chrome browser provider was unavailable. Do not treat build/helper checks as an end-to-end browser test. Vite reports a large bundle warning; no build error.

## Backend integration and unresolved decisions

Replace session stores with authoritative persistent operations, atomic ledger writes, reservation locking, server-side roles, idempotency keys and numbering. Reconcile order/job updates atomically with receipt/dispatch operations and invalidate/reload client state after successful writes. Existing Job Card GET/stage PATCH contracts were retained; new writes have no invented API endpoints. Server-loaded job data and in-memory reference inventory are not a production integration.

Resolve company settings, authoritative customer/model masters, BOM quantities and yields, final Supervisor/Manager role mapping, warehouse locations, tax/jurisdiction rules and rounding, credit notes/invoice voids, order cancellations/reservation releases, approval revisions, historical Job Card migration and partial stage completions. Invoice discounts apply before tax as an explicit frontend convention requiring confirmation. Existing stock uses the labelled `reference-stock` bucket because original batch identities are unavailable; they are not fabricated lots. Unknown openings block allocation even after receipts until authoritative inventory is reconciled. Store Keeper/Admin posts authorized stock receipts; it cannot replace the independent QC review and final managerial authorization described in the QC section.

The ERP.xlsx workbook and invoice image mentioned in the task were not supplied in the accessible task attachment or repository; the pasted fields and existing workbook-derived inventory references were used. Masters remain page-local and Dashboard/Track & Trace retain their existing mock/API behavior. Raw issue remains production tracking without raw inventory deduction. These limitations are visible/documented rather than presented as persistence or complete backend integration.

## Client-confirmed integration — 13 October 2026, parent-card phase boundary

Client confirmation received 12 October: one Job Card covers the whole Sales Order; different products retain separate production routes and quantities. This change implements the parent/item relationship portion of phases 1–2, reusing existing stores and production/costing controls. It does **not** complete all Sales Order changes in phase 1 or the full requested workflow.

New manufacturing lines are prepared individually into one parent card. Repeat creation returns the same parent. Stock-source lines are excluded as an isolated implementation assumption (`manufacturingLines` in `parentJobCards.ts`), pending explicit client confirmation for mixed orders. Parent approval requires all manufacturing lines to be prepared with their order quantities/units, validates every item before publishing approvals, and retains item-level route/material snapshots. New lines cannot be appended after approval. Item routing, costing, issue, tracking, waste and receipts reuse existing functions through the same JobCardsContext. Parent status is derived from its items; completion requires every item completed. Quantities are displayed per product/unit; progress counts mandatory production stages per item.

Job Card list displays one parent with item progress; detail switches between items and shows combined chronological activity with item references. Sales Order detail resolves items under the parent. Custom Costing resolves item-level proposed routes for recalculation, and Stock model filters resolve receipt item/model references. New receipts retain parent Job Card ID plus manufacturing item ID and order-line/model/batch references in the existing inventory ledger. Existing costing estimate links resolve work-item IDs through the parent detail route. Manufacturing creation and approval do not reserve or change physical inventory.

Historical single-product cards are never automatically grouped or relinked. Existing cards continue through their original controls. Adding a new manufacturing line to an order already containing legacy cards is blocked pending an authorized migration; existing references, batches, movements and history must be reviewed together. No migration or historical deletion was performed. New parent/item tracking is session-only and does not call the legacy per-card stage PATCH with work-item IDs.

### Explicitly pending at this boundary

- Approval-controlled confirmed-order edits/cancellation and amendment states.
- Production-for-stock creation without a Sales Order; origin is prepared in the type but no internal-production UI or posting workflow is implemented.
- Complete phase 3 review/reapproval policy across items and costing; current per-item routing controls and parent approval are reused.
- Additional material issue during production, append-only structured issue transactions, receiving department/person and raw-stock integration.
- Supervisor role/completion controls, stage rejection and accepted quantities, additional production runs and authorized excess-stock decisions.
- Supervisor/Manager approval before Finished Goods IN. The current Store/Admin QC receipt action remains legacy behavior and is not the newly confirmed authority model.
- Dispatch without mandatory reservation. Current explicit allocation/dispatch remains in place; no automatic reservation on order creation is introduced by this change.
- Expanded report filters and Excel/PDF exports for all stock categories; existing transaction-based balances remain functional.
- Dashboard replacement of demo metrics, live management trace and expanded activity events.

No browser end-to-end verification was performed for this change. Pure-helper regressions cover parent idempotency, mixed-stock exclusion, product/unit separation, complete approval scope, historical preservation, late-item locks, parent completion/history and unchanged inventory. All five existing check suites, TypeScript and production build passed. The build retains the bundle-size warning.

Backend requirements: durable parent/item identity, authoritative one-parent-per-order uniqueness, atomic scope/approval operations, item-level costing/routing/material/stage/receipt/audit references, concurrency and server authorization. Existing read/stage APIs were not changed. Confirmed dispatch, raw issues and approved receipts ultimately require atomic persistent transactions and idempotency. No backend persistence is claimed.

Client decisions still needed: mixed-stock scope, physical Job Card fields, model-specific conversions/yields, partial-run authorization and excess-stock disposition. At this parent-card boundary the confirmed no-reservation and Supervisor/Manager approval rules were pending; the later QC section implements the latter with a proposed role mapping. Reservation-free dispatch remains pending. Existing recycling, waste and USD costing requirements remain applicable.

### Files changed in the parent-card phase

- `src/types/index.ts`, `src/context/JobCardsContext.tsx`
- `src/lib/parentJobCards.ts` (new), `src/lib/jobCards.ts`, `src/lib/fulfillment.ts`, `src/lib/finishedGoodsData.ts`
- `src/pages/JobCards/JobCardList.tsx`, `src/pages/JobCards/JobCardDetail.tsx`
- `src/pages/SalesOrders/SalesOrderDetail.tsx`, `src/pages/Costing/CustomCosting.tsx`, `src/pages/Stocks/stocks.tsx`
- `scripts/check-sales-fulfillment.mjs`
- `docs/sales-fulfillment.md`, `docs/custom-costing-routing.md`, `docs/ARCHITECTURE.md`, `docs/DATA_MODELS.md`, `docs/BUSINESS_RULES.md`, `docs/BACKEND_TODO.md`, `docs/DEVELOPMENT_STATUS.md`, `docs/CHANGELOG.md`

Final diff is limited to the parent/item integration, affected dependent views, focused regression checks and related documentation. No dependencies, backend APIs, database schemas, source inventory data, historical/sample records or Git commits changed.

## Quality Control & Quality Assurance Module

Added 13 October 2026. This section supersedes the earlier pending Store-QC/final-FG-authority notes for the implemented QC phase. The full model/API contract is maintained once in [quality.md](quality.md); all proposed endpoints and models there are future backend work.

### A. Purpose and Scope

Dedicated QC within the existing ERP covers receipt acceptance, production samples, equipment, cleaning, safety, reviews, corrective actions and release traceability. Existing inventory ownership and costing remain intact.

### B. Existing Paper Forms Studied

Only the supplied task transcription was available; none of the eight photographs could be studied. Six described form structures were provisionally configured. Printed document codes/revisions and source-image references remain unverified; handwritten entries were not used as defaults.

### C. QC Roles and Permissions

Same login; new QC Inspector and QC Supervisor roles. Inspectors record assigned drafts/submit/report findings; independent supervisors review/release/verify corrective actions. Admin manages templates/assignments. Production Manager provides separate final stock authorization; Store posts authorized stock. Guards are frontend demonstration only.

### D. QC Dashboard

QC login opens a dedicated dashboard; counts use recorded inspections, raw receipts and configured machines. It shows assigned inspections, recent status/history, pending approvals/holds and equipment checks. Dates, department, inspector, status and source references are filterable. Missing scheduling data is not fabricated.

### E. Raw Material Inspection

Exact inward receipt/material IDs, supplier lot, procured quantity/unit, sample quantity, grade, documents, appearance/colour/packaging and review observations. Existing supplier master/batch IDs are absent from inward data and stay unrecorded. Physical receipt remains distinct from acceptance; pending/rejected/conditional quantities remain held without automatic returns or quantity subtraction.

### F. Production and Sample Inspection

One to eight samples with positive/negative answer polarity and actual width/thickness, targets, explicit tolerances and units. Mandatory route checkpoints determine advancement coverage. Inspections reference parent/item/stage and stable QC lots; the lot records partition existing stage output and do not pretend to be separate production execution runs.

### G. Machine Checklists

Separate standard and recycling extruder templates; stable machines live in the existing shared model-master context. Each machine has a separate inspection and consolidated status matrix. Failed/pending checks display equipment warnings; linked machines require verification before production updates. Recycling consumes warnings, not QC-created stock transactions.

### H. Cleaning and Safety Checklists

Separate cleaning records by area/activity/time/method/chemicals/cleaner; independent review records verification or recleaning requirements. Areas can be configured. Personnel safety retains the seven task checks with finding remarks; unnecessary medical diagnoses are excluded.

### I. QC Approval and Release

Immutable submission → independent review → quality release → separate Production Manager/Admin accepted/rejected quantity authorization → Store receipt. Submission/review/release alone never posts stock. Failed findings cannot be approved as passing; conditional raw acceptance remains held. Release references and cumulative receipt limits prevent repeated posting.

### J. Non-Conformance Workflow

Source findings remain intact. Open → Assigned → In Progress → Awaiting Verification → Closed, with independent verification, due dates, assignee IDs, immediate/corrective actions and event history. Closing a finding does not silently pass/release its source. Reinspection creates a linked record.

### K. Integration with Job Cards

QC decisions apply to exact manufacturing items/lots, preserving separate products/routes/units and previous-stage completion. Item-specific holds do not block unrelated products. Job Card detail shows QC history and release links; approved routing can select mandatory templates and exact machine IDs. Per-run advancement remains pending because existing stages are item-wide.

### L. Integration with Raw Materials and Finished Goods

InventoryContext retains physical ledger ownership. Raw issue/OUT respects held receipt quantities. Production Stock IN validates quality/final-authority references and exact lot/unit/accepted limits; matching held stock batches cannot dispatch. Existing historical movements are preserved. The earlier reservation-free dispatch phase remains pending.

### M. Proposed Backend Models

Canonical contracts in quality.md cover templates/versions/items, inspections/responses/samples, approvals, NCs/corrective actions, releases/attachments and audit events. Each defines identity/FKs, fields/statuses, validation, uniqueness, audit, lifecycle and permissions. Existing supplier/product/model/job/item/run/machine/inventory masters are reused.

### N. Proposed API Contracts

quality.md specifies future DRF dashboard/template/inspection/submit/approve/reject/reinspect/NC/release/report contracts, examples, pagination/filters, role scope, immutable transitions, validation errors, conflicts and idempotency. No fake QC network requests or backend endpoints were added.

### O. Backend Transaction and Validation Rules

Receipt ≠ acceptance; rejected/held material cannot ordinary-issue. Exact batch/item/source versions govern QC. Mandatory failing checks block release. Quality release ≠ final stock authorization ≠ ledger posting. Persistent approvals/audit and inventory availability must be atomic, concurrency-safe and retry-idempotent. Dispatch confirmation alone deducts physical stock; correction/reinspection history is append-only. Detailed transaction boundaries/failure handling are in quality.md.

### P. QC Reporting

Raw acceptance, sample results, Job Card history, machine compliance, cleaning, safety, NC register and monthly summary. Date ranges/department/inspector/status/source filters; Excel-readable SpreadsheetML XML export and browser Print/Save as PDF. These are not native XLSX or a server PDF service. Dashboard/report data derives from available session records.

### Q. Open Client Clarifications

Supply eight source photographs; confirm paper codes/revisions, final authority mappings, specifications/sampling, mandatory stage QC, machine schedules, actual run/batch identity, supplier receipt metadata, concessions/partial disposition, signatures/retention and NC escalation. Mandatory no-reservation dispatch is confirmed but its separate implementation is pending.

### R. Frontend-Only Limitations

QC, templates, master additions, lots, approvals/releases and corrective histories reset on refresh. Server permissions, audit, transactions, attachments, schedules and production-run persistence remain future work. No photograph-based verification or browser end-to-end verification is claimed. TypeScript/build and six check suites pass; browser testing was blocked by localhost timeout and unavailable Chrome. Vite retains its bundle-size warning. No automatic commit was made.
