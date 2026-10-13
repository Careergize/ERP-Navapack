# Business Rules

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
