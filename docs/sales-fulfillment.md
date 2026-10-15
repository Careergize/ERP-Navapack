# Sales fulfillment frontend implementation


## Client-confirmed LED MAX and Finance demo — 15 October 2026

**Client-confirmed:** new applicable LED uses `MAX(LED_Base × 0.025, Eligible_Weight_KG / 1000 × 70 × saved USD_to_UGX)`. Higher of the Two is the default. The percentage base remains **pending client clarification** and configurable (net selling excluding LED/VAT, or sourced production cost); product applicability and VAT-on-LED are still explicit. No lower/percentage-only option is offered for new financial records. Legacy calculation modes exist only for reading/reproducing historical snapshots, which are not migrated or silently repriced.

`src/lib/led.ts` is the shared rule used by stock reverse-price analysis and forward recipe/commercial calculations. It validates both inputs before MAX: missing/incompatible KG, missing product/model carton conversion, absent/nonpositive FX, invalid FX date or unset base blocks completion with a warning; it never chooses percentage as a fallback. Confirmed rates are centralized constants, 2.5% and USD 70 per metric tonne. CTR/ctn weights use existing exact product/model/effective conversion versions. No universal carton weight is introduced. USD-costed records cannot add UGX LED without an explicit UGX document/costing; no implicit currency conversion is invented.

CostingInput now optionally carries explicit LED applicability/base/VAT/weight/FX/date/conversion input. CostingContext resolves product/model weight from the shared conversion master at saving, and CostingTotals freezes the full result. Stock price history continues storing its original policy/FX and breakdown. New snapshots retain method, base choice/value, eligible KG and conversion identity/version, both comparison amounts, raw comparison amount/selected rounded amount, selected branch (including equality), FX/date, confirmed rates and VAT treatment. They survive navigation, not refresh. Editing a generated/approved estimate still creates a new revision.

Existing quote base unit prices retain their VAT-inclusive/exclusive meaning and **exclude the separately displayed LED**. Applying approved costing copies its LED snapshot without taxing a tax-inclusive grand total again. Stock quotation/direct-order lines configure the same shared LED inputs; missing/stale conversion, price or FX snapshots require an explicit refresh. Quote approval freezes base totals plus LED/LED-related VAT; customer public projection includes only selected LED/method/VAT flag, never confidential production cost/base/FX/source IDs. Authorized Costing, Quote detail/editor, Order detail and Stock views show both calculations and selected branch. The customer print and invoice show LED as a separate charge.

Commercial totals calculate base VAT exactly as before, then add frozen LED once and VAT on LED **only** if its snapshot says so. Discount remains on the underlying commercial line-price basis; a frozen levy is not silently renegotiated by a document discount. For costing-origin estimates, net-selling LED base is the existing selling subtotal before additional charges; stock/direct commercial line base is net line selling amount. These base choices are provisional until the client defines the final statutory/commercial base. Accepted quote → Sales Order copies snapshot/FX/conversion verbatim. Direct orders with LED acquire the same commercial tax snapshot path; old no-LED direct orders retain existing arithmetic. Partial invoices apportion original selected LED without looking up current FX or conversions and reconcile final whole-order VAT/LED/total residuals. Missing actual production cost remains unavailable.

Finance demo preserves the existing FinanceDashboard and accounts sidebar implementation. `/finance/login` reuses Login with a finance-specific title and account validation, and links to/from operations login. In mock-enabled mode use **finance@navapack.com / test@123**; this always resolves to the existing `accounts` role. Operations login also offers Accounts / Finance in its demo selector. Both mock paths use the same environment gate: development defaults enabled unless explicitly false, production requires `VITE_ENABLE_MOCK_LOGIN=true`. The Context rejects direct demo calls while disabled. Starting a demo session clears stale real tokens; production authentication is not replaced. Real finance sign-in still calls the existing login API and requires an accounts role before storing tokens. Refresh still signs out; Remember me does not restore a finance session.

Accounts land on the user's existing FinanceDashboard, with Finance Dashboard home navigation/workspace label, latest-revision/unexpired pending quote counts, and dispatched orders excluded from open counts. The invoice-based value is labeled Invoiced value, not collected revenue. No expenses/collections/profit or sample invoices are invented. A finance-only read-only Quality summary avoids sending accounts into role-restricted detailed QC; original QC entry/review/release permissions remain unchanged. Other navigation/mutation controls retain existing authorizations; this is a demo login/workspace, not a separate backend authentication realm.

Future backend must use the same MAX/rates across costing/sales/inventory projections, resolve applicable base/weight/conversion/FX from authoritative sources, freeze all financial/conversion/version facts in approval/order/invoice snapshots and reject missing-weight/FX records atomically. Never silently migrate historical method/base choices. Server-side Decimal rounding, source versions, idempotency, authorization and approval/reversal boundaries remain required. The percentage base, product scope and VAT-on-LED need client clarification. Finance needs real account provisioning/server permissions/session restoration; no backend, schema or new endpoint is implemented here.

Focused regression: `node scripts/check-led-finance.mjs` covers percentage-higher/weight-higher/equality, missing/invalid KG/FX/date/base, exact product/model CTR conversion, reverse stock/forward cost parity, costing→quote→order snapshot history, VAT-inclusive/exclusive and VAT-on-LED, partial-invoice reconciliation/public redaction, immutable FX, separate finance credentials and mock-mode gates. Existing costing/quotation/integrated/order/QC suites remain applicable; exact command results and browser coverage are in DEVELOPMENT_STATUS. No automatic commit.

## Integrated operations update — 15 October 2026

This section supersedes the earlier pending-phase statements **only** for reservation-optional dispatch, live dashboard aggregates, stock intelligence, connected trace views, multiple stage runs, quotation draft/review actions and explicit QC scheduling described here. Parent Job Card, QC quality release, separate manager stock authorization and Inventory-owned receipt posting remain intact. Order amendments, production-for-stock creation, additional material issues, persistent actual consumption/expenses and backend services remain separate work. Historical sample records are preserved.

### Audit and implementation plan

Inspected README/AGENTS, existing architecture/business/model/status/backend/module reports, shared types, all affected contexts/pages, financial/unit/routing/quality helpers, ledger posting and check scripts before code changes. Reused shared stores instead of parallel inventory/order/QC services. Found: variant-specific fixed ledger units and unknown opening balances; centralized recipe/markup/margin and quote VAT helpers; separate financial approval/customer acceptance and QC review/release; mandatory allocation before dispatch; static operational dashboard; API/mock-only trace lookup; no product conversion/threshold master, LED policy, email service or recurring QC schedule.

Implemented incrementally: (1) pure financial/conversion/alert helpers; (2) existing Inventory/Costing state extensions and atomic direct dispatch; (3) current-state dashboard/sales summaries/trace/stage/run views; (4) quotation generation/review/email drafts and QC schedules; (5) focused regression, existing regressions, TypeScript/build, UI smoke checks and affected documentation. No backend code, migrations, dependencies, new fake network endpoints or automatic commit.

### Selling price, VAT, LED and production cost

Stock and Costing reuse `StockIntelligence` and `StockAlerts`. Select an exact product/model scope; record an independent UGX selling amount, priced quantity/unit/date/batch and a new policy snapshot. Available history shows model, physical stock, priced quantity, converted KG, prices/KG and CTR, selling amount, VAT/LED/profit, estimated COP, actual COP/evidence if recorded, variance, conversion/costing revisions and Trace link. Prices per KG/CTR derive from the same entered VAT basis; they are informational and never overwrite negotiated prices. Historical accepted quotation/order prices continue using their existing immutable commercial snapshots; new stock analysis does not rewrite them.

`stockIntelligence.ts` uses existing `roundMoney` and keeps the new formulas in one shared utility. Let N be net selling excluding VAT/LED, L the selected levy, v the VAT fraction and C estimated COP. The entered inclusive amount solves `A = N + L + v × (N + (VAT-on-LED ? L : 0))`; an exclusive amount solves `A = N + L`, then VAT is added. With no levy this is exactly `N=A/(1+v)` inclusive and `VAT=N×v` exclusive. It never subtracts 18% from an inclusive price. The monotone equation handles levy bases without circular ad-hoc component calculations; amounts unable to cover a fixed levy are rejected.

Markup on cost: `C=N/(1+p)`, profit `N-C`. Gross margin on net selling: `C=N×(1-p)`, profit `N-C`; gross margin must be below 100%. The two methods are distinct. Percentage LED is configured rate × N, or rate × derived C. Weight LED is `eligibleKG/1000 × USD-per-1000KG × saved USD→UGX`; requires explicit KG, positive FX and saved FX date. The initial prototype supported multiple modes for historical records; new applicable records use Higher of the Two. **Historical initial delivery note (superseded by the client-confirmed LED MAX section above):** LED originally defaulted off with independently selectable methods. New applicable records now default to the client-confirmed Higher of the Two rule; applicability and base remain explicit. The UI confirmation is a session assertion, not evidence of client/legal approval. 18% VAT remains an editable company example. LED comparison rates 2.5% and USD 70/1,000 KG and the MAX method are now client-confirmed; percentage base/product scope/VAT treatment remain to clarify. VAT base is N with optional inclusion of LED; additional statutory bases require confirmed policy before extension.

Each saved financial revision retains policy, eligible KG/conversion, percentage and weight calculations where calculable, chosen LED, FX/date, net selling, profit, VAT, final amount/price impact, estimated COP, author/time and original amount/unit. Shared monetary outputs round to two decimals; solver intermediates retain precision. Rounding components can differ from entered total by a cent; production backend needs agreed decimal/reconciliation policy. Actual COP is never inferred from selling price: absent evidence reads **Actual Cost Not Available**. Accounts/Admin may record an actual total with evidence reference; variance = recorded actual − derived estimate for that exact priced quantity/batch. This is a manual recorded total, not a verified consumption/expense ledger. Dashboard actual totals/variance disclose coverage and do not treat missing actuals as zero.

### Product conversion and stock alerts

InventoryContext owns append-only ProductConversion versions: ID, exact product/model scope, original carton unit, positive net KG/CTR, optional whole pieces/CTR, effective date/version. KG aliases are recognized explicitly; CTR/ctn/carton are labels for the carton unit, not a numeric conversion. Existing `ctn` units are preserved. No carton weight exists by default and 20 KG/CTR is not seeded. Product-only and model-specific scopes are exact; an unknown model does not inherit a different model's rule. Price/CTR = price/KG × configured KG/CTR; reverse divides by a positive configured factor. Missing/zero rules do not yield fabricated KG/prices. Existing fixed stock/order units remain authoritative; this adds reporting conversions rather than changing ledger quantities or permitting mixed-unit stock posting.

Every newly posted finished movement saves original quantity/unit, converted KG if valid at its transaction date, rule ID/version, product/model ID. Existing historical movements remain unchanged and explicitly lack historical snapshots; a later configuration never backfills guessed history. Reversals retain the original conversion snapshot (or historical unknown KG), keeping cancellation from revaluing physical mass under a newer rule. Financial snapshots retain the same conversion facts. Admin/Production Manager creates conversion versions; Admin/Store Keeper/Production Manager configures per-product alert thresholds in the exact ledger unit. Ordered validation: `0 ≤ critical ≤ minimum ≤ reorder ≤ target`. Optional lead days, high-consumption quantity/window, rapid daily-consumption threshold and explicitly recorded replenishment quantity/due date are supported.

Stock alerts derive current balances and ledger history on every render, including receipt/dispatch/reversal/manual adjustment changes. Categories: Out of Stock, Critical Stock, Low Stock, High Stock Consumption, Stock Depleting Rapidly, Recent Stock OUT, Pending Replenishment. Unknown balances do not become zero. No universal minimum/reorder quantity is imposed. Recent OUT includes non-sales movements; **consumption** uses confirmed dispatch OUT within the configured inclusive window, excluding reversed dispatches, transfers/waste/adjustments and future records. Daily observed rate requires at least two distinct dispatch dates; otherwise **Insufficient History**. This is observed activity, not a forecast. Recommended replenishment is `max(0,target−current−recordedPending)` only at/below reorder with known balance; pending supply is manually recorded, not a connected purchase order or an automatic receipt.

Sales Order/quotation creation creates no movements or mandatory reservations. Direct confirmed Sales Order dispatch reuses all existing batch/dated physical-stock/order-demand validations and posts OUT atomically in session. A closed bookkeeping allocation reference is retained for compatibility, with zero outstanding reservation; explicit old allocation remains available. Exact retries return the same dispatch; conflicting IDs reject; no state publishes on failed allocation/posting. Cancellation appends reversal and restores physical stock without introducing a direct-path reservation. Existing QC holds still block affected batch dispatch. Manual non-sales OUT requires Store/Admin, explicit transfer/waste/adjustment purpose, reference and reason; adjustments require Admin confirmation. Customer sales use confirmed dispatch. Existing historical movement purposes remain unknown, not relabeled as sales.

### Live dashboard, Sales Order summaries and traceability

Dashboard replaces independently hard-coded operational aggregates with six role-visible sections: Sales, Production, Stock, Costing, Traceability and QC. Existing sample records remain in their source datasets. Sales metrics count orders, distinct exact product/model identities (unlinked lines count separately), lines and quantities grouped by original unit; parent-card IDs deduplicate and unloaded references are disclosed. Sales Order list reuses `SalesSummary`; detail shows product/manufacturing-item counts, parent statuses/stage progress and existing per-line stock/dispatch/remaining quantities. Production-for-stock cards, if present, count separately; no creation flow is invented.

Confirmed value uses explicit non-Draft/non-Open/non-Cancelled order statuses or actual confirmed dispatch evidence; a costing/job approval alone is not commercial confirmation. Orders without recorded totals/currency are excluded from money totals rather than guessed. Dispatched commercial value apportions the existing order total across dispatched line value; it includes accepted quote tax/discount basis and remains separate from invoiced revenue. Values group by currency; quote values are never added as revenue. Completed/partial/pending are derived through the existing fulfillment helper. Legacy orders without items have no fabricated quantities/products. Operational metrics read job cards, stages, movements, raw balances, estimate/saved batch-cost history and QC state. Dashboard COP/VAT/LED totals cover latest saved product/batch snapshots, not all company production or sales; missing actual cost coverage is explicit. Today's output counts required final-stage completion once per item, not every intermediate stage output. Unknown stock/measurements are displayed, not silently summed as zero.

`ConnectedTrace` supplements preserved legacy API/sample lookup. Exact product, parent/manufacturing-item, order and batch filters join existing records by stable IDs. Stock → Trace, Job → Trace, Order → Trace, Costing → Trace and Trace → Costing reuse current routes. Views show product/model, parent/item, order, production runs/QC lots, accepted quantity, original/KG movement facts, IN/OUT/dispatch references, approved estimate revision and saved batch pricing/actual evidence where present. Raw material **issued** KG is explicitly not proven consumption; source material-batch allocation is not fabricated when absent. No name-based lineage is inferred. Unlinked legacy items, missing KG snapshots and source gaps remain exceptions.

Mass balance uses first mandatory-stage input KG, final-stage output KG and compatible stage waste KG; no stage inputs/outputs are summed repeatedly across the route. Missing/incompatible measurements yield unavailable. Difference = measured input − measured final output − measured waste is flagged for review; other accounted losses remain unrecorded. Zero difference only means recorded measurements reconcile, not proof that every process loss/material conversion is known.

### Job Card stage tracking and multiple production runs

One parent Job Card still contains independent manufacturing items. `ProductionTimeline` shows required approved stages, completed/current/next status, department, operator, start/last update, required completion and delay. Existing route approval, sequence, handover, equipment QC and mandatory item QC gates still apply. No separate supervisor production role was invented: existing Operator/Production Manager/Admin controls remain; QC Supervisor keeps independent QC authority.

`ProductionRuns` records multiple append-only executions **within each existing approved stage**. Each has request ID/run number, stage ID, input/output/waste quantities in approved units, explicit times/operator/remarks and direct mass KG where valid. Aggregate values update the existing stage; explicit final-run completion alone hands cumulative output onward. Previous mandatory stages/QC must pass first; units, overlap, chronology and handed-over input limits validate. Run-backed aggregates cannot be overwritten through the old stage editor. Historical positive stage output cannot be replaced by run records; completed stages remain locked. QC output lots remain partitions of final output and are not relabeled as execution runs. More runs can finish a stage quantity, with existing separate QC/receipts afterward; replenishing material after production starts and overproduction/amendment authority remain outstanding.

### Quotation generation, reviews, customer preview and email

Reusable `GenerateQuotation` appears in quotation workflow, prospects/customer actions, Customer Masters and costing estimate records. It reopens the same generated source family/latest revision on repeated action, avoiding duplicate offers. Explicit Create/Duplicate still deliberately creates a new offer. Quotation-origin estimates reopen their existing family; an exact customer-linked order estimate copies its costing inputs into a **new unapproved** quotation-origin costing draft, requiring normal review/explicit approved price import. No fake order, copied approval or automatic customer-name mapping.

Receptionist retains draft line/quantity/customer-contact/terms edits and reviewed manual stock prices/discount proposals. Every offer still requires internal price/tax/terms approval; custom markup/gross-margin changes remain Accounts/Admin-controlled. Pending reviewers can approve, reject with remarks or request changes back to Draft. Draft has Edit and Resubmit; approved/sent edits create revisions and new approval. View Changes compares customer-facing commercial fields with prior revision; activity preserves user/time/remarks. Internal rejection and customer Revision Requested have distinct statuses. Accepted/converted snapshots stay preserved; internal approval and customer acceptance remain separate.

Customer preview reuses the existing whitelisted A4 projection and printing; no internal recipe/profit/source IDs/email-draft actors appear in it. No unsecured customer route/public link is introduced. Backend must supply expiring, revocable, revision-scoped capability links with authorization, safe field projection, access logs and authenticated/token-scoped acceptance/rejection; hashes/expiry/revocation checks apply server-side and public requests never expose internal IDs/private fields.

Quotation email captures recipient, optional comma-separated CC, subject, message, exact number/revision and manual PDF attachment instructions; saves draft history/author/time. Approved current source validation applies; malformed addresses/header-injected subjects reject. Optional mailto opens the user's app with URL-encoded fields, no automatic PDF attachment or public link. **Draft — not sent** remains explicit. It never marks an offer Sent, fabricates provider delivery or sends messages from this task. Mark Sent is the existing separately recorded communication event, not successful email transmission. Future backend owns authorized sender identity/templates, customer-safe PDF generation/storage, attachment/link generation, provider adapter/outbox, idempotent send key per revision/payload, delivery/provider-webhook history, failure state and controlled retries. No credentials/provider/API was added.

### QC daily inspections and configurable schedules

Existing QC templates now support Per Receipt, Per Batch, Per Shift, Daily, Weekly, Monthly and On Demand; legacy Per Activity remains supported. Weekly source checklists are not changed to daily. Existing six templates, inspection forms/responses/measurements/findings/reviews/reinspection/NCs and release guards are reused. KSEC is an **inactive configurable placeholder**, meaning/checks/category/frequency pending client clarification; no definition or operational checks were invented. Admin must replace/configure confirmed checks before activation.

QC Supervisor/Admin creates a schedule from an existing exact-subject inspection and latest active template, matching its configured frequency, start/end, assigned stable QC user ID, department and optional explicit shift. Daily dashboard shows scheduled/completed/pending/failed/awaiting-review counts, open actions and due schedules. Generate due inspection is an explicit session action for a selected date, idempotent by schedule/date/shift; an already recorded same-template/subject/date/shift check satisfies the occurrence without another inspection. Pause/resume is supported. Daily/per-shift recurs by day, weekly by seven-day interval, monthly by matching day-of-month (months lacking that day have no occurrence). Receipt/batch source subjects are not auto-recurred as daily lots; on-demand/event schedules use their start date. Weekly schedules remain weekly. Assignment IDs need authoritative backend user validation. Existing inspection date/time/inspector/department/subject/template/measurement/comment/reviewer history remains.

Generating a schedule/inspection or submitting/passing QC never posts stock. Independent QC release and separate Production Manager/Admin final authorization remain necessary before authorized Store receipt; failed/unresolved checks keep exact material/production subjects held. Machine/source batch/item/product links use existing subject fields; absent supplier-batch allocation is not invented. No background scheduler, notifications or persistent recurrence service exists.

### Future backend ownership, requirements and transaction boundaries

All following are proposed requirements, **not implemented endpoints/schema**. `sales`: orders, quotations, versioned approvals/customer responses/dispatch references and email/access orchestration. `production`: parent/items, immutable approved routes, execution runs/stage aggregates/handover. `inventory`: balances, postings, exact product/model conversion versions, reorder policies and alert projections. `costing`: immutable financial policy/calculation revisions, FX, estimated vs evidenced actual costs. `tracing`: ID-linked material/batch/job/stock/dispatch lineage projection. `quality`: templates/versions, schedules/occurrences, inspection/review/release/NC actions. `accounts`: users/roles/authentication/permissions; invoice/accounting integration remains to define. `reports`: role-scoped aggregate queries and exports. This ownership supersedes earlier draft statements placing costing under accounts; no backend directory was modified.

Required API capabilities (route naming remains unimplemented): versioned product conversions/effective-date queries, threshold/replenishment configuration, dated scoped stock alerts/consumption, pricing-policy validation/snapshot create/history/read, authoritative actual-cost evidence, dashboard/sales summaries with period/unit/currency/coverage, exact trace graph/exceptions, append-run/complete-stage actions, source-idempotent quotation generation, review/change comparison, customer-link issue/revoke/read/respond, email draft/send/status/retry and QC schedule/pause/occurrence generation/history. Existing proposed quotation/QC specs remain canonical for their base entities. New requests require authenticated actor, exact source IDs, expected version, request ID and policy references; server independently resolves all records, recalculates prices/KG/balances and enforces permissions. Validation/stale/conflict failures return explicit errors; local fallback is not successful persistence.

Server transactions must: lock product/batch/order remaining demand for dispatch and receipt; validate quality holds/releases and dated stock; post original/KG/conversion snapshot plus audit exactly once; roll back the whole operation on any failure; keep reversals append-only. Conversion versions never alter past movements. Pricing/FX/profit/VAT/LED snapshots remain immutable after use; decimal precision/rounding is server-owned. Runs lock item/stage/previous handover/QC and aggregate once; stage completion and handover commit together. Quotation generation/conversion has unique source/family keys and frozen accepted revision. QC occurrence uniqueness is schedule/date/shift; create and occurrence history commit atomically, with durable assignment checks. Email sends use transactional outbox after approved snapshot commit, provider idempotency and signed delivery webhooks; failed/retried delivery cannot manufacture acceptance or double-send. Secure customer token access is revocable/expiring and never broadens internal permissions. Server audit covers author, role, time, before/after versions, source/request IDs and reasons. Concurrency-safe balances/aggregates cannot trust React guards.

### Validation and remaining decisions

New `check-integrated-operations.mjs` covers product/date/model-specific KG/CTR and per-unit price conversion, missing/zero factors, inclusive/exclusive VAT, LED modes/FX/weight/minimum feasibility, markup vs gross margin, alert boundaries/history/reversal exclusion, direct confirmed dispatch/no reservation/idempotence/demand limits/reversal, no creation stock side effects, unit/currency/parent sales counts, multi-run stage sequence/handover and mass-balance gaps, daily/weekly/monthly/shift schedules/duplicate prevention, KSEC inactivity, QC submission/independent review/holds, email draft validation/redaction and rejection/change comparison. Existing seven suites remain required. TypeScript/build/whitespace and browser smoke results are recorded in DEVELOPMENT_STATUS; passing helper checks do not prove durable server behavior or full end-to-end production readiness.

Outstanding client decisions: KSEC meaning and exact checks/category/frequency; LED scope/mode/base and VAT-on-levy treatment; final percentage base for the confirmed MAX rule; FX source/effective date/rounding; real product/model KG/CTR weights/effective versions and independent prices; stock alert thresholds/windows/lead times/replenishment source; complete actual consumption/process expenses and mass-loss tolerances; order commercial confirmation/amendment/overproduction rules; production supervisor permissions/material replenishment; acceptance evidence/secure-link lifetime/revocation; email sender/provider/attachments/retry policy; QC assignment/shift/calendar/month-end policy. Existing missing QC photographs and quotation reference documents still apply. All new state resets on refresh; no public portal, email delivery, backend authorization, scheduler/database lock or fiscal posting is claimed.

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

## Quotations & Proforma Invoice Module

Implemented 13 October 2026, frontend only. The dedicated `/quotations` module provides current/history lists and filters, draft creation/editing, details, duplication/revisions, preview/A4 printing, internal price/tax/terms approval, separate customer response and accepted-revision conversion. Source documents mentioned in the task were not attached; layout follows the written fields and existing logo, with unverified company/bank/contact/signatory values left unrecorded. No handwritten signature or sample bag specifications were made permanent defaults.

### Creation, prospects and commercial settings

Select a shared customer or create/select a prospect, enter contact/billing/delivery/TIN/type and representative, then add exact existing products or custom models. Customer Master changes and direct Sales Order customer suggestions now use the same CommercialContext; unrelated Masters remain unchanged. Prospect promotion/linking is explicit and idempotent, preserving original prospect IDs without automatic duplicate customers. Company settings centralize trading/legal names/logo, multiple bank accounts, signatory, currency, configurable VAT basis/rate and default validity. UGX/18% inclusive/14-day validity are editable task examples, not immutable tax or business policy; delivery lead time is separate. Optional terms templates preserve advance/credit/payment/price-revision/tolerance clauses only when selected. A tolerance never grants excess dispatch/invoicing.

### Custom costing, pricing and taxes

Quotation custom lines reuse the existing model/recipe/process/waste/overhead/FX/markup engine through a quotation origin; no fake Sales Order or second pricing engine is created. Lines retain exact approved estimate/model IDs and revisions. The public net selling subtotal plus charges supplies the price; quotation inclusive/exclusive VAT applies once, without taxing an already inclusive estimate price again. Currency must match; no implicit conversion or KG/carton/piece inference occurs. No suggested selling-price data exists for imported stock variants, so authorized draft prices are entered and reviewed.

Line amount = quantity × stored unit price rounded to 2 decimals. Inclusive discounted total divides by (1 + VAT rate) to derive net/tax; exclusive net adds VAT once. Discounts use the selected price basis. Approval freezes exact rates/currency/discount/tax mode/rate/totals and rounding policy. UGX words reuse the existing formatter. Public print projection excludes recipes, material prices, margins, exchange-rate inputs and internal costing links.

### Approval, acceptance and revision history

Draft → Pending Internal Approval → Approved → Sent → customer Accepted/Rejected → Converted. Receptionist/Accounts/Admin draft and record customer responses; Accounts/Production Manager/Admin internally approve; Receptionist/Admin converts. Customer acceptance is separate from internal approval/printing/sending. Responses capture actual date/respondent/remarks/reference and accepted revision. Sent/approved commercial content is immutable; new revisions preserve prior prices/company/terms/approval/response history. Model/costing/quantity/specification drift blocks sending/conversion until explicit revision/review. Expired offers cannot convert; converted records cannot be revised into another order. Mark Sent is only a session event, not an email send.

### Quotation-to-Sales-Order and manufacturing integration

Only the current approved, accepted, unexpired/source-valid revision converts through existing `createSalesOrder`. Customer identity and actual manufacturing due date are confirmed; no customer, Job Card, reservation or stock transaction is created automatically. Repeating conversion returns the same order, guarded in both shared stores. The existing order Draft lifecycle remains; confirmed-order amendments are still the separately pending phase.

Converted orders retain customer/prospect/contact/billing/delivery data, exact commercial rates and tax basis/discount/rounding, payment/delivery/tolerance terms, model/costing references and quotation number/revision/line provenance. Approved quotation costing is adopted into the real order without rewriting its financial snapshot. Manufacturing enters the existing one-parent Job Card/routing/material/stage/QC/Stock IN/dispatch workflow when manually prepared; stock-source lines remain dispatch demand only. Direct Sales Order creation remains available.

Existing invoice helpers honour converted-order inclusive/exclusive pricing and automatically apportion the accepted quotation discount over billed dispatches, with final tax/total/discount rounding reconciliation shown explicitly. Direct-order invoice behavior remains unchanged. Proforma preview/conversion does not create a posted tax/fiscal invoice or inventory transaction.

### Printable layout, reporting and backend architecture

A4 design includes branding/title/date/number/revision/validity/delivery, company/customer sections, grouped multiline items, units/rates/basis/totals, VAT/words, bank details/selected terms and configured signatory. Application UI is hidden on print; table headers repeat. Exact resemblance/multi-page PDF layout still requires the two missing reference documents and browser verification. Print/Save as PDF uses the existing browser workflow.

List/dashboard metrics derive from latest session quotation families (draft/pending/sent/awaiting response/accepted/expired/converted and defined conversion rate); reports export filtered CSV without independent hard-coded totals. Existing unrelated operations demo metrics remain separate.

The canonical [quotation specification](quotations.md) defines future Django `sales` ownership; Quotation, QuotationLine, QuotationRevision, QuotationApproval, QuotationCustomerResponse and QuotationTermsSnapshot; reused masters/settings/costing/order entities; PK/FK/revision/status/price/tax/approval/audit/validation rules; proposed DRF list/create/detail/draft-patch/submit/approve/send/response/revise/convert contracts; pagination/errors/examples; and atomic, concurrency-safe idempotent conversion. These are proposed contracts, not implemented backend endpoints/schema.

### Validation, limitations and open decisions

Standalone TypeScript, production build, new quotation regression suite and all six existing suites passed; Git diff whitespace review passed. Regressions cover source costing without fake orders, public redaction, approval/acceptance/revision/expiry guards, conversion/source preservation/duplicate prevention, parent manufacturing eligibility, inclusive/exclusive VAT/discount/words and partial-invoice reconciliation. Vite retains its bundle-size warning. Browser/reference-layout verification is not claimed.

All new quotes/prospects/company/terms/customer/estimate bindings reset on refresh. Durable audit, roles, document numbering, accepted evidence, database transactions/locking, communications and fiscal/PDF services remain backend work. Supply the two source documents; confirm company/tax/rounding/credit/advance/tolerance/validity/expiry/signatory/approval policy, acceptance evidence and conversion-rate denominator. Existing recycling, waste, USD/UGX costing, QC and traceability requirements are retained. The earlier reservation-free dispatch/amendment/internal-production pending phases remain separate work. No dependencies/backend/schema changes or automatic commit.

## Integrated operations changed-file inventory — 15 October 2026

- `docs/ARCHITECTURE.md`
- `docs/BACKEND_TODO.md`
- `docs/BUSINESS_RULES.md`
- `docs/CHANGELOG.md`
- `docs/custom-costing-routing.md`
- `docs/DATA_MODELS.md`
- `docs/DEVELOPMENT_STATUS.md`
- `docs/quality.md`
- `docs/quotations.md`
- `docs/sales-fulfillment.md`
- `README.md`
- `scripts/check-custom-costing.mjs`
- `scripts/check-finished-goods.mjs`
- `scripts/check-integrated-operations.mjs`
- `scripts/check-inventory-workflows.mjs`
- `scripts/check-job-cards.mjs`
- `scripts/check-quality.mjs`
- `scripts/check-sales-fulfillment.mjs`
- `src/App.tsx`
- `src/components/GenerateQuotation.tsx`
- `src/components/ProductionRuns.tsx`
- `src/components/ProductionTimeline.tsx`
- `src/components/SalesSummary.tsx`
- `src/components/StockIntelligence.tsx`
- `src/components/ui/InventoryMovementModal.tsx`
- `src/context/CostingContext.tsx`
- `src/context/InventoryContext.tsx`
- `src/context/JobCardsContext.tsx`
- `src/context/QualityContext.tsx`
- `src/context/QuotationsContext.tsx`
- `src/lib/customCosting.ts`
- `src/lib/finishedGoodsData.ts`
- `src/lib/fulfillment.ts`
- `src/lib/operations.ts`
- `src/lib/productionRuns.ts`
- `src/lib/quality.ts`
- `src/lib/qualitySchedule.ts`
- `src/lib/qualityTemplates.ts`
- `src/lib/quotationReview.ts`
- `src/lib/quotations.ts`
- `src/lib/stockIntelligence.ts`
- `src/pages/Costing/CostingPage.tsx`
- `src/pages/Costing/CustomCosting.tsx`
- `src/pages/Dashboard.tsx`
- `src/pages/JobCards/JobCardDetail.tsx`
- `src/pages/Masters/MastersPage.tsx`
- `src/pages/Quality/DailySchedules.tsx`
- `src/pages/Quality/QualityPage.tsx`
- `src/pages/Quality/QualityTemplates.tsx`
- `src/pages/Quotations/QuotationDetail.tsx`
- `src/pages/Quotations/QuotationEmail.tsx`
- `src/pages/Quotations/QuotationList.tsx`
- `src/pages/Quotations/QuotationSettings.tsx`
- `src/pages/SalesOrders/SalesOrderDetail.tsx`
- `src/pages/SalesOrders/SalesOrderList.tsx`
- `src/pages/Stocks/stocks.tsx`
- `src/pages/TrackTrace/ConnectedTrace.tsx`
- `src/pages/TrackTrace/TrackTrace.tsx`
- `src/types/index.ts`

## LED MAX / Finance demo follow-up file inventory

This follow-up preserves prior uncommitted ERP changes and the user's finance dashboard/navigation. Scoped files touched for the confirmed rule/demo are:

- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/BACKEND_TODO.md`
- `docs/BUSINESS_RULES.md`
- `docs/CHANGELOG.md`
- `docs/DATA_MODELS.md`
- `docs/DEVELOPMENT_STATUS.md`
- `docs/custom-costing-routing.md`
- `docs/quotations.md`
- `docs/sales-fulfillment.md`
- `scripts/check-led-finance.mjs`
- `src/App.tsx`
- `src/components/LEDFields.tsx`
- `src/components/StockIntelligence.tsx`
- `src/components/layout/AppShell.tsx`
- `src/context/AuthContext.tsx`
- `src/context/CostingContext.tsx`
- `src/lib/commercialPricing.ts`
- `src/lib/customCosting.ts`
- `src/lib/demoAuth.ts`
- `src/lib/invoices.ts`
- `src/lib/led.ts`
- `src/lib/operations.ts`
- `src/lib/quotations.ts`
- `src/lib/salesOrders.ts`
- `src/lib/stockIntelligence.ts`
- `src/pages/Costing/CustomCosting.tsx`
- `src/pages/FinanceDashboard.tsx`
- `src/pages/Login.tsx`
- `src/pages/Quotations/QuotationDetail.tsx`
- `src/pages/Quotations/QuotationEditor.tsx`
- `src/pages/Quotations/QuotationPrint.tsx`
- `src/pages/SalesOrders/NewSalesOrderModal.tsx`
- `src/pages/SalesOrders/SalesInvoice.tsx`
- `src/pages/SalesOrders/SalesOrderDetail.tsx`
- `src/types/index.ts`
