# Business Rules

## Guarded local integration — 21 October 2026

Real-session module saves require backend acknowledgment, capabilities, object scope,
retry keys and current versions. Synthetic recycling intake cannot exceed the remaining
completed source-stage waste/rejection; recovered + rejected + disposed equals intake
in the source unit. No recovered output becomes operational available stock. Draft
finance estimates are separated by currency/kind and do not constitute revenue,
receivables, accounting entries or approved customer documents.


## Phase 4A persistent commercial boundary

`/commercial` supports development drafts and review only, using explicit employee capability rather than demo role names. Backend Decimal snapshots determine estimates; no authoritative VAT/LED/final amount or inferred currency/unit conversion. Only draft edits and pre-approval cancellations are available; review must return to draft first. Orders never reserve/deduct stock or execute manufacturing/dispatch. Historical revisions retain their original inputs and prices. [Contracts and pending policies](../../docs/phase4-planning/PHASE_4A_DOMAIN_CONTRACTS.md) govern this path; older demo rules below are not backend authority.

## Phase 3C-1 remediation rules — 20 October 2026

Numeric JSON quantities are invalid; decimal strings only. Stock OUT eligibility rechecked at verification/physical confirmation/approval with controlled unavailable errors; these steps reserve/deduct nothing. Final ledger remains authoritative. Current counts/openings reject caller-selected historical cutoffs; authoritative historical reconciliation deferred. Receipts/counts/openings must claim a matching pre-registered physical source line once; different delivery/count occurrences under the same document are allowed. Live registration/alias/correction governance remains pending. Synthetic guards and independent approval unchanged.

## Phase 3C-1 workflow rules — 20 October 2026

Real-session inventory requests are evidence, not stock movements. Backend enforces active capabilities/scopes and independent review; selected Procurement recorder invokes synthetic-only ledger. Receipts/returns/new positive compensations held, no QC release. Explicit batch/unit; unknown openings never zero. Opening correction shows original/current/proposed/difference, immutable original; held removal approval blocked. Counts investigated before adjustment; no count reuse. Same Admin login grants no self-approval bypass. Outside isolated context show unavailable, never fake success/balance. [Actual scope](../../docs/phase3-planning/PHASE_3C_IMPLEMENTATION_REPORT.md).

## Phase 3A backend configuration boundary — 20 October 2026

Warehouse count is configurable. Location hierarchy stays within warehouse and cannot cycle. Registered identity relations do not create, split, merge or release physical quantities. All stock identities are operationally unavailable. Admin status does not grant warehouse scope, configuration rights or business approval. Warehouse code uniqueness is global/case-insensitive as a technical convention, not a claim about client geography. Operational opening corrections remain planned, unavailable until immutable opening and independent workflow exist. Real sessions use only the integrated configuration pages; demo inventory totals are not live stock.

## Persistent quotation drafts — 16 October 2026

Save Draft succeeds only after durable backend confirmation for real users. Saved drafts reload across page refresh and later sign-in under their owner. Same UUID edits update one row; conflicting versions fail with 409 instead of silently overwriting. Once a snapshot for that draft ID is submitted, changed content requires a new revision/UUID. Draft content cannot assert manager approval or authorize sending. Demo saves are explicitly labeled as session-only.


## User roles and quotation rejection — 16 October 2026

Only Project Manager or Production Manager roles with review permission may review quotations. Manager role assignment uses real database role records and does not grant user-administration access. Pending submissions can be approved or rejected with a nonblank reason. Rejected decisions cannot be overwritten, approved, sent or resubmitted as the same snapshot; submit a revised quotation. Approval never automatically sends. User create/change endpoints are superuser-only and never accept client superuser/staff flags.


## Editable quotation selling price — 16 October 2026

A draft custom quotation may override the public selling price manually. Approved current costing/model/customer/quantity/unit dependencies remain required. The manager reviews the entered selling price, and changing approved content still creates a new snapshot requiring approval.


## Quotation units and line totals — 16 October 2026

Quotation line total equals quantity × entered unit price, rounded to two decimals. Inclusive prices already contain VAT; exclusive prices add VAT once at document totals. The inclusive unit-price readout is informational and is never multiplied again to double-charge tax. New quotation snapshots require an active registered unit; mismatched unit ID/code is rejected. Stock units follow the exact product variant, and no kg/carton/piece conversions are inferred. Unit deactivation hides it from new selections without rewriting old documents.


## Quotation manager approval and saved customers — 16 October 2026

Quotation delivery requires submission and approval of the exact snapshot by a Production Manager with approval permission. Admin/Accounts/sales cannot bypass it; approval does not automatically send. Changed content needs new approval. New quotation customers are explicitly saved to the shared database master; existing contact edits on a quote do not overwrite the master.


## Quotation PDF delivery — 15 October 2026

PDF generation and delivery use only public customer/company/items/terms fields. Only checked Email/WhatsApp channels are submitted, after server approval of the exact unexpired immutable PDF snapshot. Provider acceptance is not recipient delivery or customer acceptance. Missing configuration prevents both selected channels from starting. Failed/unknown/pending results are explicit; exact request replay does not resend. The default WhatsApp recipient is +916282744675 and must be checked/edited for each intended recipient. No order, job or stock posting occurs. Photo-derived company/bank defaults are editable; no photographed signature is reproduced.


This separates verified frontend behavior from decisions still needing confirmation.

## Sales Orders

- Customer name and marketing person are required. Marketing Person identifies who brought the customer; it is currently recorded as a name.
- Customer type must be B2B or B2C; order date defaults to the browser's local current date and must parse as a valid date.
- Multiple items are supported; at least one selected item with ID/name and unit is required.
- Quantity must be finite and greater than zero. Editable unit price must be finite and nonnegative; zero is allowed.
- Line total = quantity x unit price, rounded to two decimals. Order total sums rounded line totals and rounds to two decimals.
- Requisition order is optional text. New orders start Draft with no job-card links. Fulfillment status is derived in the list/detail from ledger records.
- The form warns when requested quantity exceeds stock; this does not block an order.

## Inventory terminology and posting

Stock means Finished Goods only. Raw Material is separate production input inventory, classified as Virgin Material, Recycled Granules or Ink.
Stock IN/OUT belongs to the module where it is recorded.

Creating a Sales Order creates demand only: no physical Stock OUT and no automatic reservation. Explicit allocation is a separate operation. Never double-deduct stock.
Demand comparisons use unreserved stock; explicit allocation validates competing reservations cumulatively.
Required Qty = max(0, ordered quantity - max(0, available stock)).
Unknown stock, unlinked items and unit mismatches have no calculated shortage.

Balances = opening + IN - OUT, with six-decimal rounding. Monthly opening carries forward earlier movements; monthly IN/OUT use the selected month. Unknown opening or a month before the reference opening date produces an unknown balance, not zero. Do not add incompatible units.

Movement entry requires a selected product/material, date and positive finite quantity. The UI disallows dates before its reference opening date and fixes the unit from the selected record. Finished Goods OUT is blocked beyond known unreserved reference stock. Raw Material and Consumables retain their existing warning behavior.

Finished Goods Pieces means optional pieces per package in this frontend. It is positive whole-number metadata, initially unrecorded, edited on Stock IN and read-only on Stock OUT. It does not multiply stock quantities or infer counts from packaging dimensions. Raw Material uses Stock in Hand only as a display label; balances and stored categories are unchanged.

## Finished Goods and source fidelity

Categories are Carrier Bags, Flat Bags and Packing. Identity includes category, subgroup, customer, item details, size, brand, packing size and unit. Preserve stable IDs and source provenance; repeated identities must not be silently merged.
Legacy name matching is accepted only when unique for the unit. See [source interpretation](finished-goods-reference.md) for customer inheritance, inferred units and unknown Packing balances.

## Consumables

Categories are Imported Spare and Local Spare; units are Each, Both, Litres and Kilos. New records require a name, opening date and nonnegative opening balance. Minimum level is optional and nonnegative. Balances use opening + IN - OUT, separately per item/unit. After movements exist, edits cannot change unit, opening balance or opening date. Stock OUT over balance warns and remains allowed, matching the existing inventory simulation.

## Raw Material

Preserve specific client grades rather than replacing them with generic names such as HDPE Resin.
The extractor maps HDPE, PP, LDPE, LLDPE, MASTER BATCH and ADDITIVES to Virgin Material; INKS & SOLVENTS to Ink; RECYCLE MATERIAL and CRUSHED MATERIAL to Recycled Granules.
Workbook references supply input inventory; legacy recycled-granule demo records remain separately identified. Blank/unrecorded balances stay unknown.

## Production and other modules

Job Cards render ordered production-stage arrays per card/model. Legacy stage choices remain compatible; Receptionist, Production Manager and Admin can toggle pending stage requirements without changing model defaults. Active/completed stage records and completed jobs are protected; stages cannot be inserted before production already received or started. PM/Admin can add/remove/reorder draft custom routing; approved routing is locked and reapproval is limited to before issue/production.
Production Manager/Admin edit pending job fields and approve into StoreIssuePending, recording approval user/time. Store Keeper/Admin record full or partial material issues against remaining requirements; known availability limits each entry, unknown availability remains explicitly unrecorded. Partial issue permits production, but replenishment after production starts is not implemented. Legacy requirements are supplied frontend data; custom requirements derive from explicit revisioned recipe quantities and units, with PM review.
Production Operator/Production Manager/Admin record nonnegative stage quantities and valid timestamps. Previous required production stages must be complete. Completion passes output to the next stage: matching-unit input is prefilled/locked; differing-unit input requires explicit entry without an assumed conversion. Output/waste consistency and optional waste calculation apply only to matching units. Recycling quantity cannot exceed stage waste; no Recycling entry is posted.
All required production stages complete -> ReadyForStock. Produced quantity is final-stage output, not the sum of outputs across stages; waste totals stay separated by unit. Store Keeper/Admin confirms a positive accepted quantity up to final output and a valid batch date -> Completed. Linked jobs post accepted Finished Goods IN to shared session state after explicit QC confirmation. Partial receipt batches retain ReadyForStock until output is accounted for; raw stock remains unchanged. Unlinked legacy jobs cannot post a guessed product.
Delayed means browser-local today is later than requiredDate and the job is not Completed. It is a separate warning. Completed jobs retain all materials/stages/waste/history. JobCardsContext changes survive navigation and reset on refresh; new manufacturing actions are local only. Existing GET list/detail and PATCH stage requirements keep their existing endpoints, with explicit frontend fallback on failed writes.
Recycling currently displays waste and granule records; it does not post raw-material movements.
Legacy Costing displays supplied totals; entering a legacy exchange rate does not recalculate existing records. Custom costing calculates entered recipe/process costs and freezes exchange rates in estimate revisions.
See [sales fulfillment rules and unresolved decisions](sales-fulfillment.md) for the implemented frontend reservation/dispatch/receipt workflow and backend limitations.

## Custom costing and routing

Custom lines are independent; repeated manufacturing-item preparation is idempotent per line within one new parent Job Card. Recipes use actual quantities or proportions × explicit batch, with no inferred pieces/cartons-to-mass conversion. Rates, FX, costs, taxes and charges are entered configuration; workbook examples do not define permanent rates. Markup and gross margin remain distinct. Generated, job-linked or approved financial snapshots require a new revision for edits. Internal costing approval and customer acceptance are separate. PM/Admin may change routing before approval; approval freezes route/material snapshots. Routing changes mark costing for review; reapproval is available only before issue/production. Store issue remains frontend tracking. QC accepted output requires exact variant/unit mapping before frontend Stock IN. Actual Cost/Variance remain unavailable until consumption and expense data exist. See [rules, roles and workbook ambiguities](custom-costing-routing.md).

## Client-confirmed parent workflow — 13 October 2026

For newly prepared orders, one parent Job Card contains separate manufacturing items. Manual stock-source lines are excluded as an isolated mixed-order assumption. Every manufacturing line must be prepared before atomic parent approval. Items preserve independent products, quantities/units, costing and routes; the parent completes only when every item completes. Adding items after approval is blocked. Historical cards are preserved and require authorized migration before new items can be attached. New parent creation/approval does not move or reserve stock.

This is the relationship portion of phases 1–2 only. Confirmed-order amendment approval, production for stock, Supervisor/Manager finished approval and dispatch without mandatory reservation remain unimplemented. Earlier Store QC and allocation rules describe current legacy behavior, not the newly confirmed target. See sales-fulfillment.md for the explicit remaining scope.

## QC integration — 13 October 2026 (supersedes earlier Store-only QC receipt rules)

Physical raw receipt is not QC acceptance. Pending/rejected/conditionally accepted receipts remain physically recorded but are excluded from usable availability; unknown held balances cannot ordinary-issue. QC inspection targets exact receipt or item/stage/lot IDs. Independent review uses per-item acceptable answers and explicit numeric tolerances, including No for objectionable odour. Failed checks cannot become Passed; submitted answers/template snapshots are immutable. Correction/reinspection preserves original results; open NCs prevent release and independent verification closes actions.

Mandatory approved-route checkpoints and item-specific holds gate production while previous-stage completion still applies. Linked machines require verified checks; no product-name or machine-name linking is inferred. QC review/quality release never posts stock. Separate Production Manager/Admin final stock authorization bounds batch acceptance/rejection; Store/Admin receipt validates exact authorization/unit/lot and cumulative quantities. Held production batches cannot dispatch. Legacy historical movements remain unchanged, while new legacy-card transfers require explicit QC authorization. The earlier reservation-free dispatch phase remains pending; this QC change does not silently replace that allocation workflow.

QC Inspector records assigned drafts/submits; QC Supervisor independently reviews/releases/manages corrections; Admin configures templates and assignments. Frontend checks are not backend permissions. Source photographs and final authority policy still need confirmation. See quality.md for precise implemented behavior, proposed backend rules, exports and limitations; existing waste/recycling and USD/UGX costing rules remain applicable.

QC stock intake guard: Store must use the exact authorized Job Card receipt. Manual unbatched reference imports are Admin-only and blocked for products with active QC holds; they are a proposed legacy/import exception awaiting client confirmation, not an alternative manufactured receipt.

## Quotations and Proforma Invoice — 13 October 2026

Offers/proformas are separate from Sales Orders/tax invoices. Quotation creation/approval/sending/printing never creates production, reservations or physical stock movements. Internal approval is not customer acceptance. Commercial content freezes at approval; sent/model/costing/price/terms changes require a new revision and review. Accepted current unexpired/source-valid revisions alone may convert once through the existing order store. Preserve contact/terms/price/tax/model/costing/quote/prospect references; conversion does not automatically create a customer or Job Card. Direct orders remain supported; manufacturing still uses one parent Job Card per order.

Inclusive/exclusive VAT is explicit and configurable, with two-decimal line/tax/total rounding and full stored unit-price precision. Discount uses entered price basis; quote tax applies to the public net selling price once. Converted order/invoice paths honour the accepted basis/discount and show final invoice rounding reconciliation; direct-order behavior is unchanged. Commercial tolerance never authorizes excess dispatch/invoicing. UGX/18%/14-day defaults are editable examples requiring company confirmation, not immutable rules. Customer/prospect/company/terms data is shared session state; promotions are explicit and idempotent. Role choices, source-document limitations and exact workflow/backend rules are in quotations.md.

## Integrated operations — 15 October 2026 (supersedes earlier pending entries where stated)

Confirmed dispatch can post OUT without prior reservation; legacy allocation remains optional. Direct dispatch preserves batch/date/order bounds, QC holds, idempotency/reversal and zero outstanding reservation. Manual non-sales OUT requires purpose/reference/reason and Store/Admin; adjustment requires Admin confirmation. Orders/offers never move stock.

Conversions are positive product/model-specific effective versions; CTR/ctn/carton aliases never imply weight. New transactions freeze conversion facts; missing history remains unknown. Thresholds are per exact stock unit with critical≤minimum≤reorder≤target. Consumption uses unreversed confirmed dispatch history, never all OUT; sparse history has no forecast.

Financial snapshots distinguish entered inclusive/exclusive VAT and LED, percent vs saved-FX weight levy, markup vs gross margin, derived estimated COP vs evidenced actual COP. LED applicability remains explicit; new applicable records default to the client-confirmed MAX rule (2.5% versus USD 70/tonne × saved FX). The percentage base and VAT-on-LED remain pending/configurable; legacy modes apply only to historical snapshots. Historical quotation/order pricing remains unchanged.

Parent Job Cards remain one per order. Multiple append-only executions aggregate within approved stages; explicit final completion and existing QC/handover gates control progression. Source-scoped Generate Quotation reopens prior family; review rejection/change requests and immutable revisions retain history. Email drafts/mailto never mark Sent or claim delivery. Daily QC schedules are explicit idempotent session generation; weekly templates remain weekly and receipt/batch subjects are not auto-recurred as daily lots. KSEC remains inactive until configured. See [integrated report](sales-fulfillment.md#integrated-operations-update--15-october-2026) for formulas, metric definitions, permissions and outstanding policies.

## Client-confirmed LED MAX — 15 October 2026

LED = MAX(LED_Base × 2.5%, Eligible_KG/1,000 × USD 70 × saved USD→UGX). Higher of the Two is now the default for new applicable records. This supersedes prior statements that higher/lower selection awaits confirmation. **Percentage base remains pending clarification** and explicitly configurable; applicability and VAT-on-LED are not assumed. Both weight and FX/date are mandatory for the comparison; missing product/model KG conversion blocks finalization, never percentage-only fallback. Historical method/rate/base/FX/amount snapshots are preserved. LED is a separate commercial charge; existing base VAT basis is retained and additional VAT applies to LED only when explicitly configured. Source snapshots, not current exchange rates, flow through quotes/orders/partial invoices. See the updated sales-fulfillment report.


## Phase 3D synthetic QC — 20 October 2026

Versioned QC evidence, guarded whole-root quality reclassification, containment and NCR/CAPA foundation now use the existing authenticated inventory APIs. Operational posting remains disabled; partial indistinguishable scopes, disposition and inherited transfer QC clearance fail closed. No demo success is treated as backend persistence. See ../../docs/phase3-planning/PHASE_3D_IMPLEMENTATION_REPORT.md for exact implementation, verification and remaining gates. No application migration or real authority grant is performed.
## Synthetic development journey — 21 October 2026

Commercial draft derivation is unapproved immutable lineage, not acceptance.
Synthetic Job Cards cover all source lines and choose applicable manufacturing
stages. Each stage waits for its predecessors; output + waste + rejection equals
input in the same exact source unit. Failed QC blocks completion; reinspection
retains failure evidence. Production-for-stock uses costing without a customer
order and ends at synthetic finished goods. Only order-origin simulations can
simulate dispatch and expose a marked invoice example. Nothing posts operational
stock, QC authority, financial records or customer communications. VAT/LED/final
payable remain unavailable. Existing legacy-demo rules below do not authorize these
backend actions.
