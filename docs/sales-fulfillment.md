# Sales fulfillment frontend implementation

## Latest change summary — 13 October 2026

Delivered the parent Job Card relationship portion of phases 1–2 of the client-confirmed workflow. New manufacturing lines from one Sales Order now join one parent Job Card instead of creating separate line-level cards. Each manufacturing item retains its own product/model identity, quantity and unit, costing revision, material requirements, approved routing, production stages and receipt batches.

The existing JobCardsContext, SalesOrdersContext, InventoryContext, costing helpers and production controls are reused. Parent approval checks the complete manufacturing scope and validates all items before applying approvals. Parent completion requires every manufacturing item to finish. List/detail screens show individual progress and chronological activity; costing recalculation and Stock model filters resolve item-level references. New stock receipts retain both parent and manufacturing-item IDs. Creation and approval do not change physical stock or automatically reserve it.

Validation passed: standalone TypeScript checking, production build, all five workflow check scripts and Git diff whitespace checking. Focused regressions cover parent creation idempotency, mixed-order stock exclusion, independent quantities/units/models, complete approval scope, historical preservation, late-item locks and completion/history aggregation. Vite retains its bundle-size warning. No browser end-to-end verification was performed for this phase.

This delivery remains frontend-only: changes reset on refresh. Historical cards are preserved; adding new manufacturing items to legacy-card orders requires an authorized migration. Stock-line exclusion is an isolated mixed-order assumption awaiting client confirmation. Durable parent/item records, atomic approvals and stock transactions, concurrency, idempotency and server-side permissions remain backend requirements.

Pending implementation includes approval-controlled order amendments, production for stock, additional material issues, Supervisor/Manager finished-goods approval, dispatch without mandatory reservation, expanded stock reports/exports and live dashboard metrics. Current allocation and Store/Admin QC behavior remains active. Mixed-order scope, the physical Job Card format, model-specific conversions/yields and partial-run/excess-stock decisions still need client clarification. The detailed phase boundary and complete changed-file list appear below. No automatic Git commit was made.

This work adds a session-only transaction chain to the existing React stores. No backend files, schema, endpoint contracts or dependencies changed. All state resets on refresh.

## Implemented behavior

- Sales Orders retain multi-line entry and require a manual fulfillment source per line, transaction currency and tax rate (including explicit zero). Demand creation does not move stock. Tax uses a single transaction rate; line-specific or jurisdiction rule engines are not implemented.
- `/sales-orders/:id` tracks each unit separately, linked jobs, receipts, outstanding allocations, confirmed dispatches and remaining demand. The list derives fulfillment status from the same records.
- New custom lines join one parent Job Card per Sales Order, with independent manufacturing items using selected model stages and stable order/line/product/model IDs. Model BOMs contain descriptions without quantities, so materials are an explicitly editable draft entered before creation and reviewed by PM. Existing approval, Store issue, stage tracking, activity and unit handover validation remain.
- Linked quantity/product/model/unit are protected during Job Card edits. Legacy demo jobs lacking stable product/line links cannot post stock through name matching.
- After all required production stages complete, Store confirms QC, accepted quantity, rejected quantity, lot and date. Positive accepted quantity posts an idempotent IN (a fully rejected remainder records QC history without a zero stock movement) to InventoryContext. Multiple partial receipt batches are supported; the job stays Ready for Stock until all final output is accounted for as accepted or rejected. Partial completion of individual production stages remains future work. Each receipt has a stable request ID and source references; no automatic allocation or dispatch occurs.
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

Resolve company settings, authoritative customer/model masters, BOM quantities and yields, QC authority, warehouse locations, tax/jurisdiction rules and rounding, credit notes/invoice voids, order cancellations/reservation releases, approval revisions, split Job Cards and partial stage completions. Invoice discounts apply before tax as an explicit frontend convention requiring confirmation. Existing stock uses the labelled `reference-stock` bucket because original batch identities are unavailable; they are not fabricated lots. Unknown openings block allocation even after receipts until authoritative inventory is reconciled. Accepted stock confirmation currently uses Store Keeper/Admin roles, preserving the existing workflow.

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

Client decisions still needed: mixed-stock scope, physical Job Card fields, model-specific conversions/yields, partial-run authorization and excess-stock disposition. The confirmed no-reservation and Supervisor/Manager approval rules are implementation work still pending, not unresolved client decisions. Existing recycling, waste and USD costing requirements remain applicable.

### Files changed in the parent-card phase

- `src/types/index.ts`, `src/context/JobCardsContext.tsx`
- `src/lib/parentJobCards.ts` (new), `src/lib/jobCards.ts`, `src/lib/fulfillment.ts`, `src/lib/finishedGoodsData.ts`
- `src/pages/JobCards/JobCardList.tsx`, `src/pages/JobCards/JobCardDetail.tsx`
- `src/pages/SalesOrders/SalesOrderDetail.tsx`, `src/pages/Costing/CustomCosting.tsx`, `src/pages/Stocks/stocks.tsx`
- `scripts/check-sales-fulfillment.mjs`
- `docs/sales-fulfillment.md`, `docs/custom-costing-routing.md`, `docs/ARCHITECTURE.md`, `docs/DATA_MODELS.md`, `docs/BUSINESS_RULES.md`, `docs/BACKEND_TODO.md`, `docs/DEVELOPMENT_STATUS.md`, `docs/CHANGELOG.md`

Final diff is limited to the parent/item integration, affected dependent views, focused regression checks and related documentation. No dependencies, backend APIs, database schemas, source inventory data, historical/sample records or Git commits changed.
