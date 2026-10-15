# Custom costing, estimates and manufacturing routing

Implemented 2026-10-09, frontend only. Existing Sales Orders, model masters, Costing, Job Cards and inventory stores are connected; no backend code, contracts or dependencies were added. See [sales fulfillment](sales-fulfillment.md) for allocation, dispatch and invoice behavior.

## Using the workflow

1. Add a Customized Product / Manufacture Sales Order line. Select a saved model revision or draft a model, enter specifications, quantity/unit and delivery date. Multiple custom lines remain independent. Save & Open Costing / Estimate saves demand before opening the linked sheet.
2. In Costing → Custom Product Costing, select the line/model. Review the entire order's recipe quantities, explicit conversions, purchase prices, exchange rates, process costs, overheads, waste, pricing and taxes. Save a draft, send it for review, and have Accounts/Admin approve internal costing. Generate a printable customer estimate; customer acceptance is recorded separately.
3. Prepare the line's manufacturing item inside the order's parent Job Card from Sales Order detail after saving costing. Repeated creation returns the same parent. Each item retains line/model/estimate IDs and revisions, requirements and proposed routing.
4. Production Manager/Admin reviews the Production Routing tab. Add/remove/reorder stages, enter department/machine, expected units/input/output, waste and instructions. Saving changes marks costing Revision Required. Apply proposed materials/stages to a new costing revision, explicitly review missing/new rates, approve costing, then use Recalculate Requirements on the job.
5. Send the draft for review and approve the Job Card. Approval preserves route/material snapshots and user/time, and forwards the card to StoreIssuePending. Routing may be reopened by PM/Admin only before material issue or production; the previous snapshot remains in history. Ordinary changes to approved routing are blocked.
6. Store Keeper/Admin confirms full or partial issue. Issued quantities stay linked to the job. This is frontend issue tracking, not a persistent Raw Material Stock OUT. Production follows mandatory approved stages with the existing tracking/handover/history fields and explicit unit safeguards.
7. QC records the exact item/stage/inspection lot, independently reviews/releases quality, and Production Manager/Admin separately authorizes accepted/rejected finished quantities. Store/Admin then posts the exact authorized batch/specification/date. Only accepted output can become Finished Goods IN. An unmapped custom product retains a prepared receipt until Store explicitly chooses an exact finished variant with matching unit/date. No name matching or inferred pieces/cartons conversion occurs. Dispatch subsequently reduces stock through the existing confirmation workflow.

## Structures and components

New domain helpers: `src/lib/customCosting.ts` (recipe/process inputs, costing totals, immutable estimate revisions/status transitions, safe customer projection), `productModels.ts` (model validation/revisions), `productionRouting.ts` (routing validation, locks and reapproval). Existing `salesJob.ts`, `jobCards.ts` and fulfillment helpers retain linked references and tracking rules.

New shared stores: `src/context/ModelsContext.tsx` (latest models plus historical revisions), `CostingContext.tsx` (line-linked estimate snapshots, approval, generation, acceptance and invalidation). Existing SalesOrdersContext, JobCardsContext and InventoryContext are reused. Provider ordering keeps one connected state graph.

New UI: `src/pages/Masters/ModelManager.tsx`; `src/pages/Costing/CustomCosting.tsx` and `CostingFields.tsx`; `src/pages/JobCards/RoutingFields.tsx`, `JobRoutingEditor.tsx`, `JobCosting.tsx`. Modified existing MastersPage, CostingPage, Sales Order form/detail, Job Card detail/forms, App providers, shared types and print styles. Job tabs include internal Costing and Production Routing. Customer preview uses existing components and browser printing, with print CSS hiding surrounding internal content.

SalesOrderItem gains model ID/revision, specifications, required date and estimate ID. Models gain revisioned descriptions/specifications/dimensions, recipe/batch configuration, process defaults, routing, waste, overheads and costing configuration. CostEstimate keeps cloned inputs/totals, lineage/revision, internal status/approval, generation and separate customer response. JobCard gains estimate/model/routing revisions, approval snapshots/history, review-required and pending-stock-receipt state. JobProductionStage gains machine, planned quantities/waste and instructions. Existing legacy fields remain compatible.

## Calculation rules

- Actual recipe quantities may total any positive mass. Proportion = normalized row mass / total comparable mass × 100. Percentage recipe quantities = entered batch × percentage / 100, converted into each material's inventory unit. Percentages must total 100.
- Explicit mass conversions: 1 kg = 1,000 g; 1 tonne = 1,000 kg. Other units must match exactly. Pieces, rolls and cartons never imply mass. Model recipes scale only when order and reference-batch units are explicitly comparable; otherwise the user supplies order requirements/yield.
- Purchase prices are entered **net**, per configured price unit. Row cost = converted required quantity × net purchase price × entered exchange rate. The rate is estimate currency per purchase currency; same currency uses 1. USD and UGX are supported and rates are saved in each revision.
- Process costs = rate × entered process quantity for per-kg/per-piece/per-batch bases; fixed charge applies once. All rates and overhead/additional amounts are in estimate currency. Ink is a separate material cost group.
- Waste cost = selected cost basis × waste percent / 100. Bases are materials+ink or materials+ink+processes. This monetary allowance does not silently increase physical material requirements or define yield.
- Production cost = materials + ink + processes + waste allowance + overheads + additional costs.
- Workbook pricing method: selling before tax = production cost × (1 + markup/100). Gross-margin alternative = production cost / (1 − margin/100), clearly distinguished and restricted to Accounts/Admin. Scenarios are 10%, 15%, 20%, 25% markup on cost; custom percentages require Accounts/Admin.
- Charge = max(entered minimum in estimate currency, selling before tax × entered charge percent/100). Tax = entered percent × selling price, optionally including charges. Grand total = selling before tax + charge + tax. Tax-inclusive unit price = grand total / order quantity. Totals round to two decimals; the full-order total is authoritative if rounded unit price × quantity differs.
- Customer projection includes commercial totals/product/terms only; material prices, FX, overheads, processes and profit percentages are excluded. Estimates do not silently change Sales Order commercial prices or invoice snapshots.

## Workbook reference and clarification

Read-only source: `C:/Users/nidhi/Downloads/Costing Sheet for Pricing.xlsx`, Sheet1. Example inputs are references, not permanent business rates.

- I4:I8 = 70, 10, 20, 5, 2 kg; I9 = 107. J4:J8 normalize to percentage. B4:B8 use those percentages as quantities for a normalized 100 kg calculation. The frontend supports either the actual 107 kg mix or a chosen percentage batch.
- F1 example exchange rate is 4,000. C4:C7 example USD rates become local cost in E4:E7 after subtracting 18%; E8 similarly subtracts 18% from a local price. **Clarify whether prices include tax, are net, or use a discount.** Subtracting 18% differs from removing tax by dividing by 1.18. The frontend requires net input rather than assuming either rule.
- F13 sums normalized material costs; F15 divides by 100; F16 applies 3% to raw-material cost; F17 adds printing ink. Waste/ink/process values are configurable in the frontend.
- A18 labels process rates 1,800 + 1,000 + 250 + 500 = 3,550, but F18 contains 2,300. **Clarify the intended process/overhead amount and applicable quantity basis.** No rate is imported as a universal default.
- F19 totals raw cost, waste, ink and overhead; C21:F21 contain 10/15/20/25% markup. The frontend preserves markup-on-cost and labels gross margin separately.
- C25 uses MAX(0.07, C24 × 2.5%) under a USD70/MT label, while prior values are local currency. **Clarify levy applicability, unit and currency conversion.** The configured minimum is entered in estimate currency, and the sample USD minimum is not silently imposed.
- The sheet applies 18% tax after the levy and extends unit amounts to the example order quantity in B35:B38. Tax rate/base, charge and order quantity remain entered configuration.

## Roles, persistence and backend requirements

Models: Receptionist/PM/Admin may draft revisions. Costing: Receptionist/PM/Accounts/Admin may edit; Accounts/Admin approve internal costing and custom pricing. Routing approval: PM/Admin. Issue/QC/receipt: Store/Admin. These are frontend guards using existing user roles, not authoritative server permissions.

All new state is session-only and resets on refresh. Legacy API reads/fallbacks remain as before. No new costing/model/routing writes use fabricated endpoints. Historical financial numbers and approval snapshots remain frozen; workflow status may change to Revision Required/Superseded without changing those numbers. A job-bound or generated draft also requires a new revision when edited.

Actual consumption/process expenses are unavailable: Actual Cost and Variance explicitly show unavailable, rather than invented values. New finished product master creation and persistent raw issue are future integration work; if no compatible variant exists, accepted output remains a prepared receipt. The current fixed sidebar can still limit narrow screens; browser visual verification was unavailable for this change.

Backend integration must provide durable versioned model/estimate/job data, independent internal/customer approval, server role enforcement, concurrency/revision checks, immutable approval/history records and atomic/idempotent inventory postings. Raw issue must validate stock and record Stock OUT transactionally; actual consumption, process expenses/waste and additional expenses must feed actual costing. Finished product configuration must supply stable variants/units/opening dates; QC receipts, allocation, dispatch and invoice references must persist together under confirmed business rules.

## Verification

`node node_modules/typescript/bin/tsc --noEmit` and Vite production build; `scripts/check-custom-costing.mjs`, `check-sales-fulfillment.mjs`, `check-job-cards.mjs`, `check-inventory-workflows.mjs`, `check-finished-goods.mjs`; Git whitespace review. New tests cover model/estimate revisions, multi-line custom orders, the 107 kg example and percentage batches, explicit conversions/FX, costs/markup/gross margin, public data redaction, linked snapshots, route add/remove/reorder/approval/locks/reapproval, Store issue and approved-stage handover. Existing checks cover QC/receipt quantities and stock/sales regressions. Browser printing and UI interaction were not verified in a browser in this session. Vite retains a large-bundle warning.

The 13 October parent-card change preserves item-level costing and routing. Historical single-product cards are not migrated. See [current phase boundary](sales-fulfillment.md#client-confirmed-integration--13-october-2026-parent-card-phase-boundary) for confirmed requirements still pending.

The later QC module adds mandatory checkpoint template and machine-ID references to approved routes and separate quality/final-stock authorizations. Costing revisions/formulas remain unchanged. Store QC acknowledgement alone cannot authorize stock; see [quality.md](quality.md).

## Quotation-origin costing — 13 October 2026

Custom Product Costing now also accepts a saved quotation line via the same input/recipe/process/FX/waste/pricing/revision functions, without a fake order. After internal costing approval, the quotation explicitly imports only public net selling subtotal plus charges and applies its own VAT basis once. Approved quotation financial snapshots remain immutable. Conversion adopts the estimate into the real order through exact source bindings; later production cost revisions are order-scoped and never silently re-price the original accepted quotation. See quotations.md for source guards, currency/tax/rounding and conversion behavior. Existing direct-order costing, recycling/waste and USD/UGX rules remain intact.

## Integrated stock analysis and production runs — 15 October 2026

Stock pricing/COP analysis reuses existing rounding/mass utilities and stores revisioned batch policy snapshots in CostingContext. It distinguishes VAT basis, configured LED bases/modes/FX, markup/gross margin, estimated COP and actual totals with evidence; it never changes approved estimate/order/quote prices. Product-specific KG/CTR versions and posted conversion snapshots live in InventoryContext; no universal package conversion was added. Multiple executions now aggregate within existing approved stages, using normal sequence/equipment/item-QC/handover gates and immutable history. Historical positive output is preserved. [Integrated formulas, source integrity, roles and limits](sales-fulfillment.md#integrated-operations-update--15-october-2026).

## Confirmed LED MAX rule — 15 October 2026

Client-confirmed LED is the higher of 2.5% × the selected LED base and eligible KG/1,000 × USD 70 × saved USD→UGX. New applicable records default to Higher of the Two. The percentage base remains configurable/pending clarification, as do product scope and VAT-on-LED treatment. Shared `led.ts` validates both calculations; missing product/model carton weight or saved FX/date blocks the result instead of percentage fallback. Existing costing and stock rounding/recipe/margin logic remains. Input/totals and accepted quote/order/invoice snapshots preserve both amounts, selected branch/rates/FX/conversion and VAT flag. Historical snapshots are unchanged. [Canonical calculation/commercial/backend details](sales-fulfillment.md#client-confirmed-led-max-and-finance-demo--15-october-2026).
