# Current frontend workflows and calculations

15 October 2026. Every workflow below describes inspected code, not browser acceptance or durable operations. Business changes live in session memory unless an existing HTTP attempt is explicitly named. See [architecture](FRONTEND_ARCHITECTURE_AUDIT.md) for all consumers and [models](FRONTEND_DATA_MODELS.md) for field shapes.

## Customer and prospect

Masters Customers → MasterTable add/row-edit → handleSubmit → MastersPage.addRow/editRow → CommercialProvider.saveCustomer (Admin, id/name required) → shared customers replacement → order suggestions/quotation parties refresh. Items/suppliers/departments/users instead update page-local arrays and reset on remount. ModelManager saves shared revisions. No API is called and a master user does not provision authentication.

Quotations settings prospect form → addProspect (Receptionist/Accounts/Admin) → name validation/UUID → shared prospect list. Explicit promoteProspect links an existing customer by ID or creates one shared customer and stores linkedCustomerId. Repetition returns same customer. No sales pipeline, lead assignment/history or full CRM module exists. GenerateQuotation from customer/prospect/estimate deduplicates by generationKey; source estimate is copied into a new quotation-origin draft estimate for review, not silently reused as approved pricing.

## New Sales Order: complete path

1. SalesOrderList New Order toggles modal, or mount `/sales-orders/new` initializes it. Order number uses current array max; date auto-fills local today and is read-only.
2. NewSalesOrderModal selects or types customer name (ID cleared on free typing), marketing name from MOCK_USERS suggestions or text, B2B/B2C and optional requisition reference. No requisition-order entity exists.
3. Add/remove item rows; choose stock or manufacturing. Stock selects exact FinishedGood ID/unit. Manufacturing may use an exact variant and model or model-only custom description/specification/default unit/delivery date; ModelManager can create a shared model revision. Enter quantity/rate; line amount recalculates. Currency and applicable tax require explicit entry. Optional per-line LED requires full conversion/weight/FX/base snapshot.
4. Available stock is physical minus reservations. A warning is advisory; over-demand does not block order creation or select manufacturing automatically. Demand component compares lines independently; no cumulative multi-order allocation is inferred. `SalesOrderDemand` computes remaining demand=max(0,ordered−confirmed dispatches), shortage=max(0,remaining−max(0,available)). Its status label still compares available with original ordered quantity, not remaining demand, so the status and shortage can disagree after partial dispatch. It filters stored order.status, whereas the list derives status; fully dispatched stored Draft orders may remain in this projection with zero remaining demand.
5. Submit removes untouched rows, validateOrder returns field errors, lock ref prevents repeat form submission, createSalesOrder calls buildSalesOrder, generates UUID/number, recalculates line/order totals, sets Draft and empty job links, prepends shared order array. onCreated closes modal/displays notice and table uses updated context. Save & Open Costing navigates to the first manufacturing line.
6. **No FG or raw movement, reservation, dispatch, Job Card or invoice is created.** `SalesOrdersContext` has no general order update/cancel/approve method. Stored status remains Draft even when display status derives fulfillment progress; status enum is not proof of lifecycle commands.

## Quotation → order

Create shared draft → editor party/product/model/terms/tax/discount/company snapshot → optional save and quotation-origin costing → approved estimate explicitly applied → submit current source-validated revision → Accounts/PM/Admin internal approval → mark Sent manually → record customer date/name/remarks/reference → Accepted current unexpired revision → Receptionist/Admin explicit existing customer mapping → convert.

`QuotationsContext.convert` checks latest revision, source versions and family deduplication; `quotationConversionDraft` copies line, customer, terms, currency, tax, discount, LED and estimate references into the existing SO builder. Approved estimate gets salesOrderReferences without rewriting its original quotation inputs. Conversion creates no job/inventory/invoice. All related stores update separately in React; database implementation must make conversion plus adoption/audit one atomic operation.

Request changes returns Pending Internal Approval → Draft with remarks; rejection creates Internally Rejected. Revise creates higher family revision and supersedes previous, retaining history; duplicate makes new family/logical lines and clears custom pricing sources. Internal approval and customer response are distinct. No universal no-self-approval check exists for quotations or estimates. `QuotationEmail` saves a validated draft and opens mailto only; Preview/Print invokes browser printing. No email delivery/public response portal exists.

## Job creation / parent approval

SalesOrderDetail manufacturing line → prepare manufacturing item/createLinked → load job API or mocks → find exact order/line/model revision/current estimate → buildLinkedJob → calculate materialRequirements from estimate or validate manually entered requirements → attachManufacturingItem → shared cards → linkJob on order and bindJob on estimate → detail/list reflect new parent/item.

One new parent per SO embeds one child per manufacturing line. Stock lines excluded; mixed-order exclusion is explicitly an assumption in parentJobCards.ts needing client confirmation. Historical separate cards block new parent attachment; they are not silently merged. Existing line creation returns existing parent. All manufacturing lines with exact quantity/unit must be attached before atomic parent approval. New items cannot be attached after approval/start. Legacy cards remain separate paths. Production-for-stock has an origin field/report count and documented target, but no complete create path; transfer currently requires order-line linkage for a mapped positive receipt.

PM/Admin edits draft routing/specification requirements; linked order quantity/product/unit/model locked. RoutingFields permits arbitrary process names, optional/required stages, ordering, units, planned input/output/waste, machine ID/text, instructions and QC template IDs. No rule requires every job to run every process. Legacy Stage enum and mock models hardcode Extrusion/Printing/Packaging/Stock/Ready to Sale; Slitting/Gusseting/Bag Making/Pouch Making can be entered dynamically but have no dedicated process-specific execution schemas. Packing is an inventory category, not proof of a manufacturing stage implementation.

saveRouting increments revision, clears execution fields, marks requirementsReviewRequired and invalidates linked estimate. recalculate applies a matching approved estimate; sendForReview sets PendingApproval. approve validates all children before publishing, then approveJobCard snapshots route/materials/actor/time and sets StoreIssuePending. Approval can also accept Draft; it is not a rigid mandatory submit-first rule. Reopen only before any issue/run/receipt, retaining previous approvals; no post-start amendment workflow exists.

## Material issue and raw stock

Issue Materials → MaterialIssueForm per-requirement quantities/Full Issue fill → JobCardsContext.issue → exact raw ID/unit physical-minus-held availability → issueJobMaterials → increase child issuedQuantity → MaterialIssued and activity event → parent summary changes. **No raw OUT is appended.** Partial issue permits production state; helper accepts unknown availability when no pending-QC restriction blocks it. Further issue is allowed only before production while statuses are Approved/StoreIssuePending/MaterialIssued/Issued; additional in-production issue is missing.

Raw Material Stock IN/OUT → InventoryMovementModal → RawMaterialPage maps selected grade/category/unit → InventoryProvider.addRawMovement → append raw movement → levels/movement/monthly/QC receipt views refresh. OUT checks unaccepted receipt holds, but unrestricted OUT can exceed recorded balance where there are no held quantities; role enforcement is absent. Supplier/batch/job/issue/return links absent. Actual consumption, unused-material return, batch allocation and recycling receipts have no implemented posting command. Intended backend chain: receipt/batch → authorized issue → job/run consumption → unused return/waste; each distinct event needs a reference and reconciliation, not double deductions for both issue and consumption without a defined WIP account.

## Production stage and multiple executions

Stage Update or ProductionRuns form → provider machine/checkpoint guards → updateJobStage/appendProductionRun → immutable replacement child/parent state + chronological history. Only Operator/PM/Admin, after issue. Previous required stages must complete. Required machine checks/quality coverage gate advancement. Completed stage locked; once runs exist, aggregate stage overwrite is blocked.

Stage fields: input/output/waste quantities and explicit units, status, operator, machine route, start/end, remarks, waste type/reason/sentToRecycling. Completion validates chronology/nonfuture dates/operator and same-unit bounds. Same-unit Calculate Waste fills input−output. Mixed units never get invented conversions; handover records upstream output/unit and auto-fills next input only on same unit. Waste transfer is tracking-only and does not create Recycling intake.

Run fields: unique request ID/reference/stage, input/output/waste, approved units, start/end/operator/remarks, final-run checkbox. Runs cannot overlap or predate prior completion; sums accumulate within stage. Handover caps input; final completion accounts for whole handed input. Final run hands cumulative output to next required stage. Final required stage completion sets ReadyForStock. Intermediate run batches are not individually modeled as fully allocatable stock; QC lot registration partitions completed stage output, not live run output. Planned vs actual conversion/yield remains limited.

## QC and finished receipt

NewInspection selects exact raw inward, completed child/stage lot, matching machine, area or safety subject + latest active template/date/department/samples. registerBatch creates stable immutable output-lot UUID; sum of lots cannot exceed stage output. Create → save answers/metadata/time → submit → derived Pass/Fail with immutable submitted responses → different supervisor/admin review → Passed/Failed/Reinspection Required (raw may conditionally accept but remains held) → explicit quality release after NC closure.

Failed/conditional record → linked reinspection preserves chain. Any unresolved inspection or NC holds exact subject. Machine guard blocks linked unverified equipment; stage QC coverage counts unique released lots separately by stage/unit. All unresolved production records conservatively hold the item. QC uses explicit checklist comparisons, not a complete statistical sampling/AQL engine.

For final output only: QC quality release → separate PM/Admin finished_stock authorization with accepted/rejected quantities within inspected lot → Store/Admin StockTransferForm exact authorized batch, accepted/rejected/date/QC acknowledgment → finishedAuthorization and transferJobToStock validate cumulative actual/authorization → InventoryProvider.postReceipt appends accepted FG IN with order/line/parent/item/QC/final-release/batch references. Zero accepted with rejection records disposition tracking, not a waste/return stock transfer. Card completes only when accepted+rejected accounts for all produced output; partial receipts leave ReadyForStock.

Unknown FG mapping retains prepared receipts, no movement; Store explicitly maps exact variant/output unit then postPreparedReceipts uses source IDs. postReceipt rejects conflicting repeat IDs, mismatched units/quantity/date/source authorization and cumulative overreceipt; replay does not double post. Cross-context React updates are not durable ACID: backend must lock and commit job receipt + stock + audit atomically. Final authorization does not itself receive stock; receipt does not dispatch it.

Manual FG IN is separate Admin reference-import path, blocked by active product holds and prohibited job references; it is not ordinary manufactured acceptance. Manual non-sales OUT requires Store/Admin, transfer/waste/adjustment purpose/reference/reason, known unreserved reference-batch availability; adjustment Admin-only. Both use shared movement append and conversion snapshot. There is no two-location transfer pair or independent adjustment approval record yet. pieces-per-package metadata optionally updates separately without converting stock quantity.

## Allocation, dispatch and invoice

SalesOrderDetail optional Allocate Finished Goods → allocate → exact line/unit/batch/known physical and remaining demand checks → allocation only (no physical movement). Reserved = sum(unreleased quantity−dispatched); available = physical−reserved. Allocation and some reversal/dispatch provider paths lack independent role guards.

Direct confirmed dispatch → InventoryContext.directDispatch (Admin/Store/Receptionist) re-resolves stored line, checks batch QC → confirmDirectDispatch → allocate internal request then confirmDispatch → one sale OUT + dispatch + allocation released. Reservation-based confirmDispatch decreases allocation remainder and posts one OUT; required quantity/date/delivery note/destination, available batch/physical and historical balance checks. Overdispatch blocked; no mandatory reservation step. References and conversion snapshot retained. Request replay conflicts are checked more fully on direct dispatch than legacy allocation/dispatch helpers.

Cancel with reversal → reverseDispatch → immutable IN reversalOf OUT, cancelled dispatch, allocation dispatched decremented; no deleting OUT. UI suppresses when invoice references dispatch; provider/helper itself does not enforce invoiced protection or role. With a direct allocation already released, reversal can restore physical stock without restoring active reserved demand. This needs authoritative policy tests.

InvoiceForm → select uninvoiced confirmed dispatches + company/buyer/number/date/currency/tax fields → InvoicesContext.create (Admin/Accounts/Receptionist) → createInvoice validates exact order/date/currency/unique number/no double invoice → snapshots quantities/prices/documents → invoice view. It never moves stock. Quotation commercial basis/discount/LED allocate proportionally; final invoice reconciles original totals, tax, discount and LED. Payments, receivables settlement, credit notes and fiscal API certification are missing. Manually entered authority verification strings are unverified references, not generated QR.

## Exact implemented formula register

`roundMoney(x)=Math.round(x*100)/100`; inventory round uses 1e6. These are JS floating-point results; Decimal server ports require explicit reconciliation tests, especially half-cent boundaries. All symbols below refer to input fields in the cited helper. The source appendix preserves full function bodies for exact branch/rounding order.

| Source/function | Actual arithmetic / boundary |
|---|---|
| salesOrders.lineTotal/orderTotal | R(qty×unitPrice); R(sum of rounded lines). orderSummary subtotal=total (pre-tax). |
| buildSalesOrder | Commercial config: calculateCommercialTotals; LED lines without config: same helper exclusive/discount0; otherwise R(subtotal×(1+taxRate/100)). Default Draft. |
| finishedBalance/rawMaterialBalance/consumableBalance | Closing=opening+ΣIN−ΣOUT; monthly opening=reference opening+prior signed movements; null reference remains null. FG date-range additionally filters exact unit. |
| fulfillment.reserved/batchPhysical | Reserved=Σactive(allocation.quantity−dispatched). Batch balance=Σsigned batch movements; reference-stock includes original opening and unbatched/reference rows. |
| calculateCost recipe | Explicit quantity or convert(batchQuantity×percentage/100,batchUnit,material.unit); proportions sum 100 within 1e−6. kg=1,g=.001,tonne=1000; same arbitrary unit allowed, otherwise unsupported conversion errors. Mixing%=material KG/total KG×100 only for compatible mass entries. |
| calculateCost material | R(convert(quantity,unit,priceUnit)×price×FX); FX=1 same currency, else entered positive target/purchase rate. Material and ink totals sum rounded line costs separately. |
| calculateCost process | R(rate×(fixed?1:entered quantity)); per kg requires kg, per piece pcs; no automatic labour/hour or machine power formula. Packaging/labour can be user-entered processes/costs, no independent standard engine. |
| calculateCost waste/COP | R((materials+ink+[process if selected])×wastePercent/100); COP=R(material+ink+process+waste+overheads+additional). Cost allowance does not increase recipe quantity. |
| calculateCost price | Markup R(COP×(1+p/100)); margin R(COP/(1−p/100)), p<100; profit=R(selling−COP). Scenarios hardcoded 10/15/20/25%. |
| calculateCost charges/tax/final | Charges=R(max(minimumCharge,selling×chargePercent/100)); tax=R((selling+[charges if taxOnCharges]+[LED if vatOnLED])×taxPercent/100); final=R(selling+charges+LED+tax); unit=R(final/input.quantity). |
| led.calculateLED | percentage=base×.025, weight=eligibleWeightKG/1000×70×saved USD→UGX; selected=R(max(unrounded alternatives)); equality tolerance Number.EPSILON×max(1,a,b)×8. Base is explicit net-selling/production-cost. Missing weight/FX/date/base rejects; UGX only when applicable. |
| commercialPricing.calculateCommercialTotals | S=R(ΣR(q×p)); D=R(discount), B=R(S−D); exclusive taxable=B, tax=R(B×t/100); inclusive taxable=R(B/(1+t/100)), tax=R(B−taxable). Add summed frozen LED and separate R(LED VAT sum) once; returned taxable includes VAT-applicable LED. |
| quotedCostPrice | (approved public selling subtotal+charges)/quantity, ×(1+quoteTaxRate/100) only for inclusive basis. Preserves precision; quote VAT not reapplied to tax-inclusive costing price. |
| quantitySnapshot/convertedPrices | KG unit passes quantity; exact product/model/unit/effective conversion gives cartons×kgPerCTR else null. Price/kg=price/carton÷ratio; price/carton=price/kg×ratio. Preserve original quantity/unit/rule version. |
| sellingCostBreakdown | costFactor markup=1/(1+p/100), margin=1−p/100. Levy evaluated against net or net×factor. Solve net+levy+[VAT(net+taxable levy) if inclusive]=entered amount with 100 bisection iterations. Exclusive entered amount includes LED, VAT added later. EstimatedCOP=R(net×factor), profit=R(net−cost). New saved LED policy must be higher/MAX; old helper enum retains alternatives. |
| stockAlert | Window starts date−(windowDays−1). Consumption=sum confirmed-dispatch-linked OUT not reversed by as-of date; observed history requires >=2 activity dates; daily=consumption/windowDays. Recommended=max(0,target−current−pending quantity) only current<=reorder. Threshold ordering critical<=minimum<=reorder<=target; not forecast. |
| appendProductionRun/updateJobStage | Aggregate Σrun input/output/waste; same-unit output+waste<=input; same-unit handover exact input; different units explicit. Waste-fill=round6(input−output). SentToRecycling<=waste. |
| operations.massBalance | First-stage input KG−last-stage output KG−Σstage waste KG; unsupported conversion/null yields unavailable; otherLosses=null. Issued material is not proven consumed. |
| invoices.createInvoice | Selected dispatch quantities grouped per order line, R(q×rate). Quoted discount proportional to selected subtotal except final remainder; frozen per-line LED proportional to original quantity. Final invoice total/tax/LED=original full totals−prior invoices; roundingAdjustment preserves reconciliation. |
| operations.salesMetrics | Counts unique product/model/unlinked line IDs; quantities by unit, values by currency; dispatched commercial value apportions source pricing/discount/LED. It is not automatically invoiced revenue. |
| QuotationMetrics | Converted latest families/latest family count×100, displayed 1 decimal; historical toggle does not change denominator rule. |
| RecyclingPage | Awaiting=sum wasteQty for !sentToRecycling; produced=sum granulesProducedKg, all rows regardless month. No implemented yield calculation/loss reconciliation. |

## Missing transactions explicitly recorded

Order edit/cancel/approval/amendment; production-for-stock creation; additional production-time issue; raw batch consumption/return; actual-cost aggregation; PO/GRN/payment; recycling intake/run/restock/external jobwork; physical warehouse transfer; verified SOP escalation and independent approvals outside QC; automatic schedule worker; public customer response/email delivery; full roll genealogy/recall. Do not infer any of these from a status, text label, mock row or planned API.

## Formula and validation source appendix

The following source-backed function excerpts preserve exact calculations, conditional guards and transition ordering for the next implementation session. They are not backend code.

### src/lib/commercialPricing.ts:6

```typescript
export function calculateCommercialTotals(lines: { quantity: number; unitPrice: number; ledSnapshot?: LEDSnapshot }[], discount: number, taxRate: number, mode: TaxMode): CommercialTotals {
  if (!['inclusive', 'exclusive'].includes(mode) || !Number.isFinite(taxRate) || taxRate < 0 || taxRate > 100 || !Number.isFinite(discount) || discount < 0 || lines.some(l => !Number.isFinite(l.quantity) || l.quantity <= 0 || !Number.isFinite(l.unitPrice) || l.unitPrice < 0)) throw new Error('Complete positive quantities, nonnegative prices/discount and valid tax treatment.');
  const subtotal = roundMoney(lines.reduce((sum, l) => sum + roundMoney(l.quantity * l.unitPrice), 0));
  discount = roundMoney(discount);
  if (!Number.isFinite(subtotal) || discount > subtotal) throw new Error('Discount exceeds subtotal or amounts exceed the supported range.');
  const basis = roundMoney(subtotal - discount), factor = 1 + taxRate / 100;
  const taxableAmount = mode === 'inclusive' ? roundMoney(basis / factor) : basis;
  const tax = mode === 'inclusive' ? roundMoney(basis - taxableAmount) : roundMoney(taxableAmount * taxRate / 100);
  const led = roundMoney(lines.reduce((sum,l)=>sum+(l.ledSnapshot?.selectedAmount??0),0));
  const ledTax = roundMoney(lines.reduce((sum,l)=>sum+(l.ledSnapshot?.vatOnLED?l.ledSnapshot.selectedAmount*taxRate/100:0),0));
  const totalBeforeLED = mode === 'inclusive' ? basis : roundMoney(taxableAmount + tax);
  const total=roundMoney(totalBeforeLED+led+ledTax);
  const subtotalBeforeTax = mode === 'inclusive' ? roundMoney(subtotal / factor) : subtotal;
  if (![taxableAmount, tax, total].every(Number.isFinite)) throw new Error('Unsupported monetary range.');
  return { subtotal, subtotalBeforeTax, discount, discountBeforeTax: roundMoney(subtotalBeforeTax - taxableAmount), taxableAmount:roundMoney(taxableAmount+lines.reduce((sum,l)=>sum+(l.ledSnapshot?.vatOnLED?l.ledSnapshot.selectedAmount:0),0)), tax:roundMoney(tax+ledTax), total, ...(lines.some(l=>l.ledSnapshot)?{led,ledTax}: {}) };
}
```
### src/lib/consumableData.ts:21

```typescript
export function consumableBalance(item: Consumable, movements: ConsumableMovement[]) {
  const ledger = movements.filter(m => m.materialId === item.id);
  const round = (value: number) => Math.round(value * 1e6) / 1e6;
  const stockIn = round(ledger.filter(m => m.type === 'IN').reduce((sum, m) => sum + m.quantity, 0));
  const stockOut = round(ledger.filter(m => m.type === 'OUT').reduce((sum, m) => sum + m.quantity, 0));
  return { stockIn, stockOut, currentStock: round(item.openingStock + stockIn - stockOut) };
}
```
### src/lib/customCosting.ts:11

```typescript
export const roundMoney = (n: number) => Math.round(n * 100) / 100;
```

### src/lib/customCosting.ts:12

```typescript
const requireValue = (ok: unknown, message: string) => { if (!ok) throw new Error(message); };
```

### src/lib/customCosting.ts:13

```typescript
export function convertQuantity(quantity: number, from: string, to: string) {
  requireValue(Number.isFinite(quantity) && quantity >= 0, 'Quantity must be finite and nonnegative.');
  if (from === to && from.trim()) return quantity;
  from = from.toLowerCase(); to = to.toLowerCase();
  const mass: Record<string, number> = { kg: 1, kgs: 1, kilo: 1, kilos: 1, kilogram: 1, kilograms: 1, g: 0.001, tonne: 1000 };
  requireValue(mass[from] && mass[to], `No configured conversion from ${from} to ${to}. Enter an explicit matching unit.`);
  return quantity * mass[from] / mass[to];
}
```

### src/lib/customCosting.ts:21

```typescript
export function calculateCost(input: CostingInput): CostingTotals {
  requireValue(input.quantity > 0 && Number.isFinite(input.quantity) && input.unit.trim(), 'Enter order quantity and unit.');
  requireValue(input.currency === 'USD' || input.currency === 'UGX', 'Select USD or UGX.');
  requireValue(['quantities', 'percentages'].includes(input.recipeMode) && ['markup', 'gross-margin'].includes(input.pricingMethod) && ['materials', 'materials-and-processes'].includes(input.wasteBasis), 'Select valid recipe, waste and pricing bases.');
  requireValue(input.materials.length && new Set(input.materials.map(m => m.materialId)).size === input.materials.length, 'Select distinct recipe materials.');
  for (const n of [input.wastePercent, input.overheads, input.additionalCosts, input.markupPercent, input.taxPercent, input.chargePercent, input.minimumCharge]) requireValue(Number.isFinite(n) && n >= 0, 'Costs and percentages must be finite and nonnegative.');
  requireValue(input.wastePercent <= 100 && input.taxPercent <= 100 && input.chargePercent <= 100 && (input.pricingMethod !== 'gross-margin' || input.markupPercent < 100), 'Invalid percentage for the chosen calculation.');
  if (input.recipeMode === 'percentages') {
    requireValue(input.batchQuantity > 0 && Number.isFinite(input.batchQuantity), 'Enter the production batch quantity.');
    requireValue(Math.abs(input.materials.reduce((sum, m) => sum + m.percentage, 0) - 100) < 1e-6 && input.materials.every(m => Number.isFinite(m.percentage) && m.percentage > 0), 'Percentage recipe must total 100%.');
  }
  const quantities = input.materials.map(m => input.recipeMode === 'percentages' ? convertQuantity(input.batchQuantity * m.percentage / 100, input.batchUnit, m.unit) : m.quantity);
  const masses = input.materials.map((m, i) => ['kg', 'g', 'tonne'].includes(m.unit) ? convertQuantity(quantities[i], m.unit, 'kg') : null);
  const totalMass = masses.every(m => m !== null) ? masses.reduce<number>((sum, n) => sum + (n ?? 0), 0) : null;
  const materials = input.materials.map((m, i) => {
    requireValue(m.materialId && m.unit && m.priceUnit && Number.isFinite(m.price) && m.price >= 0 && quantities[i] > 0 && Number.isFinite(quantities[i]), 'Complete selected material, positive quantity, unit and purchase price.');
    requireValue(m.currency === 'USD' || m.currency === 'UGX', 'Select a purchase currency.');
    requireValue(m.currency === input.currency || (Number.isFinite(m.exchangeRate) && m.exchangeRate > 0), 'Enter target currency per one purchase currency as exchange rate.');
    const rate = m.currency === input.currency ? 1 : m.exchangeRate;
    const pricedQuantity = convertQuantity(quantities[i], m.unit, m.priceUnit);
    const convertedUnitCost = convertQuantity(1, m.unit, m.priceUnit) * m.price * rate;
    return { id: m.id, quantity: quantities[i], unit: m.unit, mixingPercent: totalMass && masses[i] !== null ? masses[i]! / totalMass * 100 : null, convertedUnitCost, total: roundMoney(pricedQuantity * m.price * rate) };
  });
  const materialCost = roundMoney(materials.filter((_, i) => input.materials[i].costGroup === 'material').reduce((s, m) => s + m.total, 0));
  const inkCost = roundMoney(materials.filter((_, i) => input.materials[i].costGroup === 'ink').reduce((s, m) => s + m.total, 0));
  const processCosts = input.processes.map(p => {
    requireValue(p.name.trim() && Number.isFinite(p.rate) && p.rate >= 0 && Number.isFinite(p.quantity) && p.quantity >= 0, 'Complete process name, quantity and nonnegative rate.');
    requireValue(['per kg', 'per piece', 'per batch', 'fixed'].includes(p.basis), 'Select process cost basis.');
    if (p.basis === 'per kg') requireValue(p.unit === 'kg', 'Per KG process quantity must be in kg.');
    if (p.basis === 'per piece') requireValue(p.unit === 'pcs', 'Per piece process quantity must be in pcs.');
    return roundMoney(p.rate * (p.basis === 'fixed' ? 1 : p.quantity));
  });
  const processCost = roundMoney(processCosts.reduce((s, n) => s + n, 0));
  const wasteCost = roundMoney((materialCost + inkCost + (input.wasteBasis === 'materials-and-processes' ? processCost : 0)) * input.wastePercent / 100);
  const costOfProduction = roundMoney(materialCost + inkCost + processCost + wasteCost + input.overheads + input.additionalCosts);
  const sellingBeforeTax = roundMoney(input.pricingMethod === 'gross-margin' ? costOfProduction / (1 - input.markupPercent / 100) : costOfProduction * (1 + input.markupPercent / 100));
  const profit = roundMoney(sellingBeforeTax - costOfProduction);
  const charges = roundMoney(Math.max(input.minimumCharge, sellingBeforeTax * input.chargePercent / 100));
  const led = calculateConfiguredLED(input.led,sellingBeforeTax,costOfProduction,input.currency);
  const tax = roundMoney((sellingBeforeTax + (input.taxOnCharges ? charges : 0) + (led?.vatOnLED ? led.selectedAmount : 0)) * input.taxPercent / 100);
  const grandTotal = roundMoney(sellingBeforeTax + charges + (led?.selectedAmount ?? 0) + tax);
  requireValue([materialCost, inkCost, processCost, wasteCost, costOfProduction, sellingBeforeTax, grandTotal].every(Number.isFinite), 'Costing amounts exceed the supported range.');
  return { led, materials, materialCost, inkCost, processCosts, processCost, wasteCost, costOfProduction, profit, sellingBeforeTax, charges, tax, grandTotal, unitSellingPrice: roundMoney(grandTotal / input.quantity) };
}
```

### src/lib/customCosting.ts:65

```typescript
export function materialRequirements(input: CostingInput): JobCardMaterial[] {
  const totals = calculateCost(input);
  return input.materials.map((m, i) => ({ id: `requirement-${m.id}`, materialId: m.materialId, name: m.name, requiredQuantity: totals.materials[i].quantity, issuedQuantity: 0, unit: m.unit }));
}
```

### src/lib/customCosting.ts:69

```typescript
export function newCostingForLine(source: { customer: string; orderId?: string; quotationId?: string }, item: SalesOrderItem, model: Model): CostingInput {
  let scale: number | null = null;
  if (model.batchQuantity && model.batchUnit) { try { scale = convertQuantity(item.quantity, item.unit, model.batchUnit) / model.batchQuantity; } catch { /* Different finished units need an explicit batch/yield, never an inferred conversion. */ } }
  const materials = structuredClone(model.recipe ?? []).map(m => ({ ...m, quantity: scale === null ? NaN : m.quantity * scale }));
  const processes = structuredClone(model.processes ?? []).map(p => ({ ...p, quantity: p.basis === 'fixed' ? 1 : scale === null ? NaN : p.quantity * scale }));
  return { orderId: source.orderId ?? '', quotationId: source.quotationId, itemId: item.id, modelId: model.id, modelRevision: model.revision ?? 1, customer: source.customer, product: item.itemName, specifications: item.specifications ?? model.specifications ?? '', quantity: item.quantity, unit: item.unit, currency: model.costingConfig?.currency ?? 'UGX', recipeMode: model.recipeMode ?? 'quantities', batchQuantity: scale === null ? 0 : (model.batchQuantity ?? 0) * scale, batchUnit: model.batchUnit ?? 'kg', materials, processes, wastePercent: model.wastePercent ?? 0, wasteBasis: 'materials', overheads: model.overheads ?? 0, additionalCosts: 0, markupPercent: model.costingConfig?.markupPercent ?? 10, pricingMethod: 'markup', taxPercent: model.costingConfig?.taxPercent ?? 0, chargePercent: 0, minimumCharge: 0, taxOnCharges: true, validityDate: '', deliveryTerms: '', remarks: '' };
}
```

### src/lib/customCosting.ts:76

```typescript
export function newCostingInput(order: SalesOrder, item: SalesOrderItem, model: Model): CostingInput { return newCostingForLine({ customer: order.customerName, orderId: order.id }, item, model); }
```

### src/lib/customCosting.ts:77

```typescript
export function estimateMatchesOrder(e: CostEstimate, orderId: string, itemId?: string) { return (e.input.orderId === orderId && (!itemId || e.input.itemId === itemId)) || !!e.salesOrderReferences?.some(r => r.orderId === orderId && (!itemId || r.itemId === itemId)); }
```

### src/lib/customCosting.ts:78

```typescript
export function customerEstimate(estimate: CostEstimate) {
  const i = estimate.input, t = estimate.totals;
  return { number: estimate.number, revision: estimate.revision, date: (estimate.generatedAt ?? estimate.createdAt).slice(0, 10), customer: i.customer, product: i.product, modelId: i.modelId, modelRevision: i.modelRevision, specifications: i.specifications, quantity: i.quantity, unit: i.unit, unitSellingPrice: t.unitSellingPrice, led: t.led ? { selectedAmount:t.led.selectedAmount,vatOnLED:t.led.vatOnLED,method:t.led.method } : undefined, subtotal: t.sellingBeforeTax, charges: t.charges, tax: t.tax, grandTotal: t.grandTotal, currency: i.currency, validityDate: i.validityDate, deliveryTerms: i.deliveryTerms, remarks: i.remarks };
}
```

### src/lib/customCosting.ts:83

```typescript
export function buildEstimateRevision(input: CostingInput, all: CostEstimate[], existingId?: string, now = new Date().toISOString()): CostEstimate {
  const existing = existingId ? all.find(e => e.id === existingId) : undefined;
  if (existingId && (!existing || !((existing.input.orderId === input.orderId && existing.input.itemId === input.itemId && existing.input.quotationId === input.quotationId) || (!input.quotationId && existing.salesOrderReferences?.some(r => r.orderId === input.orderId && r.itemId === input.itemId))))) throw new Error('Estimate revision belongs to another line.');
  const frozen = !!existing && (existing.status === 'Approved' || existing.status === 'Superseded' || !!existing.generatedAt || !!existing.approvedAt || !!existing.usedByJobCardId);
  const number = existing?.number ?? `EST-${new Set(all.map(e => e.number)).size + 1}`;
  const revision = existing ? frozen ? Math.max(...all.filter(e => e.number === number).map(e => e.revision)) + 1 : existing.revision : 1;
  return { id: !frozen && existing ? existing.id : crypto.randomUUID(), number, revision, previousId: frozen ? existing?.id : existing?.previousId, status: 'Draft', customerAcceptance: 'Pending', input: structuredClone(input), totals: calculateCost(input), createdAt: now };
}
```

### src/lib/customCosting.ts:91

```typescript
export function transitionEstimate(estimate: CostEstimate, status: EstimateStatus, user: { name: string; role: string }, now = new Date().toISOString()): CostEstimate {
  if (status === 'Approved') {
    if (!['admin', 'accounts'].includes(user.role) || estimate.status !== 'Pending Review') throw new Error('Accounts/Admin can approve an estimate sent for review.');
    return { ...estimate, status, approvedBy: user.name, approvedAt: now };
  }
  if (status === 'Pending Review' && estimate.status === 'Draft') return { ...estimate, status, reviewReason: undefined };
  if (status === 'Revision Required' && ['Pending Review', 'Approved'].includes(estimate.status)) return { ...estimate, status, reviewReason: 'Reviewer requested a revision.' };
  throw new Error('Invalid costing status transition. Recalculate/save a new draft before resubmitting.');
}
```

### src/lib/customCosting.ts:101

```typescript
export function transitionEstimateLedger(all: CostEstimate[], id: string, status: EstimateStatus, user: { name: string; role: string }): CostEstimate[] {
  const estimate = all.find(e => e.id === id); if (!estimate) throw new Error('Estimate not found.');
  const next = transitionEstimate(estimate, status, user);
  return all.map(row => row.id === id ? next : status === 'Approved' && row.number === estimate.number && (row.status === 'Approved' || !!row.approvedAt || !!row.generatedAt) ? { ...row, status: 'Superseded' } : row);
}
```
### src/lib/finishedGoodsData.ts:56

```typescript
const round = (value: number) => Math.round(value * 1e6) / 1e6;
```

### src/lib/finishedGoodsData.ts:57

```typescript
export const finishedGoodName = (product: FinishedGood) => product.itemDetails || product.subgroup;
```

### src/lib/finishedGoodsData.ts:59

```typescript
export const finishedGoodLabel = (product: FinishedGood) =>
  [finishedGoodName(product), product.size, product.brand, product.packingSize, product.customer, product.unit,
    product.dataNotes.some(note => note.startsWith('Repeated variant')) ? `Source row ${product.sourceRow}` : ''].filter(Boolean).join(' · ');
```

### src/lib/finishedGoodsData.ts:62

```typescript
export function matchesFinishedGood(product: FinishedGood, query: string) {
  const text = [product.itemDetails, product.size, product.brand, product.packingSize, product.customer, product.subgroup, product.id].join(' ').toLowerCase();
  const normalize = (value: string) => value.toLowerCase().replace(/\s+/g, '');
  return query.trim().toLowerCase().split(/\s+/).every(word => text.includes(word)) || normalize(text).includes(normalize(query));
}
```

### src/lib/finishedGoodsData.ts:67

```typescript
export function finishedBalance(product: FinishedGood, movements: FinishedGoodsMovement[], month?: string) {
  const ledger = movements.filter(movement => movement.productId === product.id);
  const inMonth = month ? ledger.filter(movement => movement.date.startsWith(month)) : ledger;
  const stockIn = round(inMonth.filter(movement => movement.type === 'IN').reduce((sum, movement) => sum + movement.quantity, 0));
  const stockOut = round(inMonth.filter(movement => movement.type === 'OUT').reduce((sum, movement) => sum + movement.quantity, 0));
  if (product.openingStock === null || (month && `${month}-01` < product.openingDate)) {
    return { openingStock: null, stockIn, stockOut, currentStock: null };
  }
  const openingStock = round(product.openingStock + (month ? ledger.filter(movement => movement.date < `${month}-01`)
    .reduce((sum, movement) => sum + (movement.type === 'IN' ? movement.quantity : -movement.quantity), 0) : 0));
  return { openingStock, stockIn, stockOut, currentStock: round(openingStock + stockIn - stockOut) };
}
```

### src/lib/finishedGoodsData.ts:79

```typescript
export function findFinishedGood(itemId: string | undefined, name: string, unit: string) {
  const byId = itemId ? FINISHED_BY_ID.get(itemId) : undefined;
  if (byId) return byId;
  const normalize = (value: string) => value.toLowerCase().replace(/\s+/g, '');
  const matches = FINISHED_GOODS.filter(product => product.unit === unit &&
    (normalize(finishedGoodLabel(product)) === normalize(name) || normalize(product.itemDetails) === normalize(name)));
  // Never silently choose between different brands, customers or packing sizes.
  return matches.length === 1 ? matches[0] : undefined;
}
```

### src/lib/finishedGoodsData.ts:89

```typescript
export function finishedRangeBalance(product: FinishedGood, movements: FinishedGoodsMovement[], from: string, to: string) {
  const ledger = movements.filter(m => m.productId === product.id && m.unit === product.unit);
  const inRange = ledger.filter(m => m.date >= from && m.date <= to);
  const stockIn = round(inRange.filter(m => m.type === 'IN').reduce((sum, m) => sum + m.quantity, 0));
  const stockOut = round(inRange.filter(m => m.type === 'OUT').reduce((sum, m) => sum + m.quantity, 0));
  if (!from || !to || to < from || product.openingStock === null || from < product.openingDate) return { openingStock: null, stockIn, stockOut, currentStock: null };
  const openingStock = round(product.openingStock + ledger.filter(m => m.date < from).reduce((sum, m) => sum + (m.type === 'IN' ? m.quantity : -m.quantity), 0));
  return { openingStock, stockIn, stockOut, currentStock: round(openingStock + stockIn - stockOut) };
}
```
### src/lib/fulfillment.ts:6

```typescript
const round = (value: number) => Math.round(value * 1e6) / 1e6;
```

### src/lib/fulfillment.ts:7

```typescript
const check = (ok: unknown, message: string) => { if (!ok) throw new Error(message); };
```

### src/lib/fulfillment.ts:8

```typescript
export const reserved = (state: FulfillmentLedger, productId: string, batch?: string) => round(state.allocations.filter(a => !a.released && a.productId === productId && (batch === undefined || a.batch === batch)).reduce((sum, a) => sum + a.quantity - a.dispatched, 0));
```

### src/lib/fulfillment.ts:9

```typescript
export function physical(state: FulfillmentLedger, productId: string) { const product = FINISHED_BY_ID.get(productId); return product ? finishedBalance(product, state.movements).currentStock : null; }
```

### src/lib/fulfillment.ts:10

```typescript
export function batchPhysical(state: FulfillmentLedger, productId: string, batch: string) {
  if (batch === 'reference-stock') { const product = FINISHED_BY_ID.get(productId); return product ? finishedBalance(product, state.movements.filter(m => !m.batch || m.batch === batch)).currentStock : null; }
  return state.movements.filter(m => m.productId === productId && m.batch === batch).reduce((sum, m) => sum + (m.type === 'IN' ? m.quantity : -m.quantity), 0);
}
```

### src/lib/fulfillment.ts:14

```typescript
export function allocate(state: FulfillmentLedger, order: SalesOrder, item: SalesOrderItem, quantity: number, batch: string, requestId: string = crypto.randomUUID()): FulfillmentLedger {
  if (state.allocations.some(a => a.id === requestId)) return state;
  const product = FINISHED_BY_ID.get(item.itemId ?? '');
  check(product && product.unit === item.unit && !['Completed', 'Cancelled'].includes(order.status) && order.items?.some(i => i.id === item.id && i.itemId === item.itemId) && !!item.fulfillmentSource, 'Select a valid product with the order unit.');
  check(Number.isFinite(quantity) && quantity > 0 && batch, 'Enter a positive quantity and select a batch.');
  const balance = physical(state, product!.id), batchBalance = batchPhysical(state, product!.id, batch);
  check(balance !== null && batchBalance !== null && quantity <= balance - reserved(state, product!.id) && quantity <= batchBalance - reserved(state, product!.id, batch), 'Allocation exceeds known unreserved stock.');
  const committed = state.allocations.filter(a => a.orderId === order.id && a.itemId === item.id).reduce((sum, a) => sum + (a.released ? a.dispatched : a.quantity), 0);
  check(quantity <= item.quantity - committed, 'Allocation exceeds the unallocated order balance.');
  return { ...state, allocations: [...state.allocations, { id: requestId, orderId: order.id, itemId: item.id, productId: product!.id, batch, quantity, dispatched: 0, released: false }] };
}
```

### src/lib/fulfillment.ts:25

```typescript
export function confirmDispatch(state: FulfillmentLedger, draft: Omit<Dispatch, 'status' | 'number' | 'orderId' | 'itemId' | 'productId' | 'batch' | 'unit'>): FulfillmentLedger {
  if (state.dispatches.some(d => d.id === draft.id)) return state;
  check(draft.id, 'Dispatch request identifier is required.');
  const a = state.allocations.find(a => a.id === draft.allocationId);
  check(a && !a.released, 'Select an active allocation.');
  const balance = physical(state, a!.productId), batchBalance = batchPhysical(state, a!.productId, a!.batch);
  check(Number.isFinite(draft.quantity) && draft.quantity > 0 && draft.quantity <= a!.quantity - a!.dispatched && balance !== null && balance >= draft.quantity && batchBalance !== null && batchBalance >= draft.quantity, 'Dispatch exceeds allocated or physical stock.');
  check(/^\d{4}-\d{2}-\d{2}$/.test(draft.date) && Number.isFinite(Date.parse(draft.date)), 'Choose a valid dispatch date.');
  const product = FINISHED_BY_ID.get(a!.productId)!;
  const batchReceipts = state.movements.filter(m => m.productId === a!.productId && m.batch === a!.batch && m.type === 'IN');
  check(a!.batch === 'reference-stock' || batchReceipts.some(m => m.date <= draft.date), 'Dispatch cannot precede batch receipt.');
  const datedBalance = finishedBalance(product, state.movements.filter(m => m.date <= draft.date)).currentStock;
  const datedBatch = batchPhysical({ ...state, movements: state.movements.filter(m => m.date <= draft.date) }, a!.productId, a!.batch);
  check(datedBalance !== null && datedBalance >= draft.quantity && datedBatch !== null && datedBatch >= draft.quantity, 'Stock was unavailable on the selected dispatch date.');
  const laterDates = [...new Set(state.movements.filter(m => m.productId === product.id && m.date > draft.date).map(m => m.date))];
  check(laterDates.every(date => (finishedBalance(product, state.movements.filter(m => m.date <= date)).currentStock ?? 0) >= draft.quantity && (batchPhysical({ ...state, movements: state.movements.filter(m => m.date <= date) }, product.id, a!.batch) ?? 0) >= draft.quantity), 'Backdated dispatch would make a later historical balance negative.');
  check(draft.date >= product.openingDate && draft.destination.trim() && draft.challan.trim(), 'Date must follow opening; destination and delivery note are required.');
  const dispatch: Dispatch = { ...draft, modelId: batchReceipts[0]?.modelId, modelName: batchReceipts[0]?.modelName, number: `DSP-${state.dispatches.length + 1}`, orderId: a!.orderId, itemId: a!.itemId, productId: a!.productId, batch: a!.batch, unit: product.unit, status: 'Confirmed' };
  return { movements: [...state.movements, { id: `out-${draft.id}`, type: 'OUT', movementPurpose: 'sale', modelId: dispatch.modelId, modelName: dispatch.modelName, productId: a!.productId, quantity: draft.quantity, unit: product.unit, date: draft.date, salesOrderId: a!.orderId, salesOrderItemId: a!.itemId, dispatchId: draft.id, batch: a!.batch, reference: dispatch.number, remarks: draft.remarks }], allocations: state.allocations.map(row => row.id === a!.id ? { ...row, dispatched: round(row.dispatched + draft.quantity) } : row), dispatches: [...state.dispatches, dispatch] };
}
```

### src/lib/fulfillment.ts:45

```typescript
export function reverseDispatch(state: FulfillmentLedger, id: string, date: string, reason: string): FulfillmentLedger {
  const d = state.dispatches.find(d => d.id === id);
  check(d && reason.trim() && /^\d{4}-\d{2}-\d{2}$/.test(date) && Number.isFinite(Date.parse(date)) && date >= d.date, 'Record a reversal date and reason.');
  if (d!.status === 'Cancelled') return state;
  return { ...state, movements: [...state.movements, { id: `reverse-${id}`, productId: d!.productId, quantity: d!.quantity, unit: d!.unit, date, type: 'IN', batch: d!.batch, salesOrderId: d!.orderId, salesOrderItemId: d!.itemId, dispatchId: id, reversalOf: `out-${id}`, reference: `Reversal ${d!.number}`, remarks: reason }], allocations: state.allocations.map(a => a.id === d!.allocationId ? { ...a, dispatched: round(a.dispatched - d!.quantity) } : a), dispatches: state.dispatches.map(row => row.id === id ? { ...row, status: 'Cancelled' } : row) };
}
```

### src/lib/fulfillment.ts:53

```typescript
export function confirmDirectDispatch(state: FulfillmentLedger, order: SalesOrder, item: SalesOrderItem, batch: string, draft: Omit<Dispatch, 'allocationId' | 'status' | 'number' | 'orderId' | 'itemId' | 'productId' | 'batch' | 'unit'>): FulfillmentLedger {
  const previous = state.dispatches.find(d=>d.id===draft.id);
  if (previous) { check(previous.orderId===order.id && previous.itemId===item.id && previous.batch===batch && previous.quantity===draft.quantity && previous.date===draft.date && previous.challan===draft.challan && previous.destination===draft.destination && previous.vehicle===draft.vehicle && previous.remarks===draft.remarks, 'Dispatch request ID conflicts with existing dispatch.'); return state; }
  check(!['Cancelled','Completed','Dispatched'].includes(order.status), 'Order is closed.');
  const allocated = allocate(state, order, item, draft.quantity, batch, `direct-${draft.id}`);
  const posted = confirmDispatch(allocated, { ...draft, allocationId:`direct-${draft.id}` });
  return { ...posted, allocations: posted.allocations.map(a=>a.id===`direct-${draft.id}`?{...a,released:true}:a) };
}
```

### src/lib/fulfillment.ts:62

```typescript
export function orderFulfillmentStatus(order: SalesOrder, state: FulfillmentLedger, cards: JobCard[]): SalesOrder['status'] {
  if (order.status === 'Cancelled' || !order.items?.length) return order.status;
  const dispatched = (itemId: string) => state.dispatches.filter(d => d.orderId === order.id && d.itemId === itemId && d.status === 'Confirmed').reduce((sum, d) => sum + d.quantity, 0);
  if (order.items.every(i => dispatched(i.id) >= i.quantity)) return 'Dispatched';
  if (order.items.some(i => dispatched(i.id) > 0)) return 'Partially Dispatched';
  if (state.allocations.some(a => a.orderId === order.id && !a.released && a.quantity > a.dispatched)) return 'Reserved';
  if (state.movements.some(m => m.salesOrderId === order.id && m.jobCardId && m.type === 'IN')) return 'Stock Received';
  const jobs = cards.filter(c => c.salesOrderId === order.id).flatMap(c => c.manufacturingItems ?? [c]);
  if (jobs.some(j => j.status === 'ReadyForStock')) return 'Ready for Stock';
  if (jobs.some(j => ['MaterialIssued', 'InProduction', 'OnHold'].includes(j.status))) return 'In Production';
  if (jobs.some(j => j.approval)) return 'Approved';
  return 'Draft';
}
```
### src/lib/invoices.ts:6

```typescript
const money = (value: number) => Math.round(value * 100) / 100;
```

### src/lib/invoices.ts:7

```typescript
export function createInvoice(draft: InvoiceDraft, order: SalesOrder, dispatches: Dispatch[], existing: Invoice[]): Invoice {
  if (!draft.number.trim() || existing.some(i => i.number === draft.number) || !draft.seller.trim() || !draft.currency.trim() || !draft.billingAddress.trim() || !draft.date || !Number.isFinite(Date.parse(draft.date))) throw new Error('Complete unique invoice number, seller, currency, date and billing address.');
  if (!Number.isFinite(draft.taxRate) || draft.taxRate < 0 || draft.taxRate > 100 || !Number.isFinite(draft.discount) || draft.discount < 0) throw new Error('Invalid tax rate or discount.');
  if (order.currency && draft.currency !== order.currency) throw new Error('Invoice currency must match the order; currency conversion is not configured.');
  const selected = dispatches.filter(d => draft.dispatchIds.includes(d.id));
  if (!selected.length || selected.length !== new Set(draft.dispatchIds).size || selected.some(d => d.orderId !== order.id || d.status !== 'Confirmed' || d.date > draft.date || existing.some(i => i.dispatchIds.includes(d.id)))) throw new Error('Select confirmed, uninvoiced dispatches dated on or before the invoice.');
  const items = (order.items ?? []).flatMap(item => { const quantity = selected.filter(d => d.itemId === item.id).reduce((sum, d) => sum + d.quantity, 0); return quantity ? [{ itemId: item.id, description: item.itemName, quantity, unit: item.unit, rate: item.unitPrice, amount: money(quantity * item.unitPrice),ledSnapshot:item.ledSnapshot?{...structuredClone(item.ledSnapshot),baseAmount:item.ledSnapshot.baseAmount*quantity/item.quantity,selectedUnrounded:item.ledSnapshot.selectedUnrounded*quantity/item.quantity,selectedAmount:money(item.ledSnapshot.selectedAmount*quantity/item.quantity),percentageAmount:money(item.ledSnapshot.percentageAmount*quantity/item.quantity),weightAmount:money(item.ledSnapshot.weightAmount*quantity/item.quantity),eligibleWeightKG:item.ledSnapshot.eligibleWeightKG*quantity/item.quantity}:undefined }] : []; });
  const subtotal = money(items.reduce((sum, i) => sum + i.amount, 0));
  if (draft.discount > subtotal) throw new Error('Discount exceeds subtotal.');
  let led:number|undefined;
  let discount = draft.discount, taxMode = 'exclusive' as 'inclusive' | 'exclusive', quotationDiscount: number | undefined, roundingAdjustment: number | undefined;
  let tax = money((subtotal - discount) * draft.taxRate / 100), total = money(subtotal - discount + tax);
  if (order.commercialPricing) {
    if (draft.taxRate !== order.taxRate || draft.discount !== 0) throw new Error('Quoted VAT is frozen and the accepted discount is apportioned automatically. Additional invoice adjustments need a separate authorized workflow.');
    taxMode = order.commercialPricing.taxMode;
    const full = calculateCommercialTotals(order.items ?? [], order.commercialPricing.discount, order.taxRate ?? 0, taxMode);
    const prior = existing.filter(i => i.orderId === order.id);
    const fullyInvoiced = (order.items ?? []).every(item => { const billed = prior.reduce((sum, invoice) => sum + invoice.items.filter(i => i.itemId === item.id).reduce((s, i) => s + i.quantity, 0), 0) + items.filter(i => i.itemId === item.id).reduce((sum, i) => sum + i.quantity, 0); return Math.abs(billed - item.quantity) <= Number.EPSILON * Math.max(1, item.quantity) * 8; });
    const alreadyDiscounted = prior.reduce((sum, i) => sum + (i.quotationDiscount ?? 0), 0);
    quotationDiscount = fullyInvoiced ? money(full.discount - alreadyDiscounted) : Math.min(money(full.discount * (full.subtotal ? subtotal / full.subtotal : 0)), money(full.discount - alreadyDiscounted));
    discount = quotationDiscount;
    const calculated = calculateCommercialTotals(items.map(i => ({ quantity: i.quantity, unitPrice: i.rate,ledSnapshot:i.ledSnapshot })), discount, draft.taxRate, taxMode);
    tax = calculated.tax; total = calculated.total; led=calculated.led;
    if (fullyInvoiced) {
      const reconciled = money(full.total - prior.reduce((sum, i) => sum + i.total, 0));
      if(full.led!==undefined)led=money(full.led-prior.reduce((n,i)=>n+(i.led??0),0));
      roundingAdjustment = money(reconciled - total); total = reconciled;
      tax = money(full.tax - prior.reduce((sum, i) => sum + i.tax, 0));
    }
  }
  if (![subtotal, tax, total].every(Number.isFinite)) throw new Error('Invoice amounts exceed the supported range.');
  return { ...draft, led, discount, taxMode, quotationDiscount, roundingAdjustment, id: crypto.randomUUID(), orderId: order.id, orderNumber: order.orderNumber, buyer: order.customerName, dispatchNumbers: selected.map(d => d.number), po: order.requisitionOrder ?? '', challans: selected.map(d => d.challan).join(', '), items, subtotal, tax, total };
}
```

### src/lib/invoices.ts:40

```typescript
export function amountInWords(amount: number, currency: string) {
  const ones = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen'];
  const tens = ['', '', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety'];
  const words = (n: number): string => n < 20 ? ones[n] : n < 100 ? tens[Math.floor(n / 10)] + (n % 10 ? ` ${ones[n % 10]}` : '') : n < 1000 ? `${ones[Math.floor(n / 100)]} hundred${n % 100 ? ` ${words(n % 100)}` : ''}` : [...[[1e12, 'trillion'], [1e9, 'billion'], [1e6, 'million'], [1000, 'thousand']] as [number, string][]].filter(([v]) => n >= v).slice(0, 1).map(([v, label]) => `${words(Math.floor(n / v))} ${label}${n % v ? ` ${words(n % v)}` : ''}`).join('');
  if (amount >= 1e15) return 'Amount exceeds supported words range';
  const cents = Math.round(amount * 100); return `${currency} ${words(Math.floor(cents / 100))} and ${String(cents % 100).padStart(2, '0')}/100 only`;
}
```
### src/lib/jobCards.ts:8

```typescript
export const localToday = () => new Date().toLocaleDateString('en-CA');
```

### src/lib/jobCards.ts:9

```typescript
export const orderedStages = (card: JobCard) => [...(card.productionStages ?? [])].sort((a, b) => a.sequence - b.sequence);
```

### src/lib/jobCards.ts:10

```typescript
export const productionStages = (card: JobCard) => orderedStages(card).filter(s => s.required && s.kind === 'production');
```

### src/lib/jobCards.ts:11

```typescript
export const isDelayed = (card: JobCard, today = localToday()): boolean => card.manufacturingItems ? card.manufacturingItems.some(i => isDelayed(i, today)) : card.status !== 'Completed' && !!card.requiredDate && card.requiredDate < today;
```

### src/lib/jobCards.ts:12

```typescript
export const fmtQuantity = (value: number | null | undefined, unit = '') => value == null ? 'Not recorded' : `${value.toLocaleString('en-IN', { maximumFractionDigits: 3 })}${unit ? ` ${unit}` : ''}`;
```

### src/lib/jobCards.ts:13

```typescript
export function currentLocation(card: JobCard): { department: string; stage: string } {
  if (card.manufacturingItems) { const locations = card.manufacturingItems.map(currentLocation); return { department: [...new Set(locations.map(l => l.department))].join(', '), stage: [...new Set(locations.map(l => l.stage))].join(', ') }; }
  if (card.status === 'Draft' || card.status === 'PendingApproval') return { department: 'Production Manager', stage: 'PM Approval' };
  if (card.status === 'Approved' || card.status === 'StoreIssuePending') return { department: 'Store', stage: 'Store Issue' };
  if (card.status === 'ReadyForStock' || card.status === 'Completed') return { department: 'Stock Keeping', stage: card.status === 'Completed' ? 'Stock Confirmed' : orderedStages(card).find(s => s.required && s.kind === 'stock' && s.status !== 'Completed')?.name ?? 'Stock Keeping' };
  const stages = orderedStages(card).filter(s => s.required);
  const current = stages.find(s => ['InProgress', 'OnHold', 'Received'].includes(s.status)) ?? stages.find(s => s.status !== 'Completed');
  return { department: current?.department ?? card.department, stage: current?.name ?? 'Not recorded' };
}
```

### src/lib/jobCards.ts:22

```typescript
export function productionTotals(card: JobCard) {
  const stages = productionStages(card);
  const last = stages.at(-1);
  const waste = new Map<string, number>();
  stages.forEach(stage => { if (stage.wasteQuantity != null) waste.set(stage.wasteUnit, (waste.get(stage.wasteUnit) ?? 0) + stage.wasteQuantity); });
  return { produced: last?.outputQuantity ?? null, unit: last?.outputUnit ?? card.unit ?? '', waste: [...waste].map(([unit, quantity]) => fmtQuantity(quantity, unit)).join(', ') || 'Not recorded' };
}
```

### src/lib/jobCards.ts:29

```typescript
export function jobSummary(cards: JobCard[], today = localToday()) {
  return [
    ['Total Active', cards.filter(c => c.status !== 'Completed').length],
    ['Pending Approval', cards.filter(c => c.status === 'PendingApproval').length],
    ['Store Issue Pending', cards.filter(c => ['Approved', 'StoreIssuePending'].includes(c.status)).length],
    ['In Production', cards.filter(c => c.status === 'InProduction').length],
    ['Delayed', cards.filter(c => isDelayed(c, today)).length],
    ['Completed', cards.filter(c => c.status === 'Completed').length],
  ] as [string, number][];
}
```

### src/lib/jobCards.ts:39

```typescript
export function normalizeJobCard(card: JobCard, orders: SalesOrder[] = []): JobCard {
  const order = orders.find(o => o.id === card.salesOrderId);
  const stages: JobProductionStage[] = card.productionStages ?? (card.stages ?? []).map(stage => ({
    id: `${card.id}-${stage.stage}`, legacyStage: stage.stage, name: stage.stage, department: stage.stage,
    sequence: stage.sequenceOrder, required: stage.required, kind: ['Stock', 'Ready to Sale'].includes(stage.stage) ? 'stock' : 'production',
    status: stage.status === 'Complete' ? 'Completed' : stage.status === 'InProgress' ? 'InProgress' : 'Pending',
    inputQuantity: null, outputQuantity: null, wasteQuantity: null, inputUnit: '', outputUnit: '', wasteUnit: '', operator: '', remarks: '',
  }));
  const normalized = { ...card, stages: card.stages ?? [], salesOrderNumber: card.salesOrderNumber ?? order?.orderNumber,
    customerName: card.customerName ?? order?.customerName, productionStages: stages, requiredMaterials: card.requiredMaterials ?? [], activityHistory: card.activityHistory ?? [] };
  return { ...normalized, department: currentLocation(normalized).department };
}
```

### src/lib/jobCards.ts:52

```typescript
export function filterJobCards(cards: JobCard[], filters: JobFilters, today = localToday()) {
  return cards.filter(card => {
    const items = card.manufacturingItems ?? [card];
    const text = [card.jobCardNumber, card.salesOrderNumber, card.customerName, ...items.flatMap(i => [i.modelName, i.product])].join(' ').toLowerCase();
    return filters.query.trim().toLowerCase().split(/\s+/).every(word => text.includes(word)) &&
      (filters.status === 'all' || (filters.status === 'Delayed' ? isDelayed(card, today) : filters.status === 'MaterialIssued' ? ['Issued', 'MaterialIssued'].includes(card.status) : card.status === filters.status)) &&
      (filters.department === 'all' || items.some(i => currentLocation(i).department === filters.department)) && (filters.stage === 'all' || items.some(i => currentLocation(i).stage === filters.stage)) &&
      (!filters.from || (!!card.createdDate && card.createdDate.slice(0, 10) >= filters.from)) &&
      (!filters.to || (!!card.createdDate && card.createdDate.slice(0, 10) <= filters.to));
  });
}
```

### src/lib/jobCards.ts:63

```typescript
function assert(condition: unknown, message: string): asserts condition { if (!condition) throw new Error(message); }
```

### src/lib/jobCards.ts:64

```typescript
const validQuantity = (value: number | null) => value !== null && Number.isFinite(value) && value >= 0;
```

### src/lib/jobCards.ts:65

```typescript
const timestamp = (value: string | undefined) => value ? Date.parse(value) : NaN;
```

### src/lib/jobCards.ts:66

```typescript
function requireRole(user: User, roles: string[]) { assert(roles.includes(user.role), 'Your role cannot perform this action.'); }
```

### src/lib/jobCards.ts:67

```typescript
function event(card: JobCard, user: User, action: string, description: string, now: string, department = currentLocation(card).department): JobCardActivity[] {
  return [...(card.activityHistory ?? []), { id: crypto.randomUUID(), timestamp: now, action, user: user.name, department, description }];
}
```

### src/lib/jobCards.ts:70

```typescript
export function approveJobCard(card: JobCard, user: User, now = new Date().toISOString()): JobCard {
  requireRole(user, ['production_manager', 'admin']);
  assert(['Draft', 'PendingApproval'].includes(card.status), 'This job card is already approved.');
  assert(!card.requirementsReviewRequired, 'Recalculate/review requirements and costing before routing approval.');
  assert(productionStages(card).length, 'At least one production stage is required.');
  return { ...card, status: 'StoreIssuePending', department: 'Store', routingApproved: { revision: card.routingRevision ?? 1, stages: structuredClone(orderedStages(card)), materials: structuredClone(card.requiredMaterials ?? []), approvedBy: user.name, approvedAt: now }, approval: { approvedBy: user.name, approvedAt: now },
    activityHistory: event(card, user, 'Approved', 'Production Manager approved the job card and forwarded it for Store Issue.', now) };
}
```

### src/lib/jobCards.ts:78

```typescript
export function issueJobMaterials(card: JobCard, quantities: Record<string, number>, available: Record<string, number | null>, user: User, now = new Date().toISOString()): JobCard {
  requireRole(user, ['store_keeper', 'admin']);
  assert(['Approved', 'StoreIssuePending', 'MaterialIssued', 'Issued'].includes(card.status), 'Materials can only be issued after approval and before production.');
  const materials = card.requiredMaterials ?? [];
  assert(materials.length, 'Required materials are not configured.');
  let issuedAny = false;
  const requiredMaterials = materials.map(material => {
    const quantity = quantities[material.id] ?? 0;
    assert(validQuantity(quantity), 'Issue quantities must be finite and nonnegative.');
    assert(quantity <= Math.max(0, material.requiredQuantity - material.issuedQuantity) + 1e-6, `Issue exceeds the remaining requirement for ${material.name}.`);
    assert(quantity === 0 || available[material.id] == null || quantity <= available[material.id]! + 1e-6, `Issue exceeds recorded availability for ${material.name}.`);
    issuedAny ||= quantity > 0;
    return { ...material, issuedQuantity: Math.round((material.issuedQuantity + quantity) * 1e6) / 1e6 };
  });
  assert(issuedAny, 'Enter an issue quantity greater than zero.');
  const full = requiredMaterials.every(material => material.issuedQuantity >= material.requiredQuantity);
  const updated: JobCard = { ...card, requiredMaterials, status: 'MaterialIssued', activityHistory: event(card, user, 'Materials issued', `${full ? 'Full' : 'Partial'} material issue recorded in frontend state; inventory is unchanged.`, now, 'Store') };
  return { ...updated, department: currentLocation(updated).department };
}
```

### src/lib/jobCards.ts:98

```typescript
export function updateJobStage(card: JobCard, id: string, update: StageUpdate, user: User, now = new Date().toISOString()): JobCard {
  requireRole(user, ['production_operator', 'production_manager', 'admin']);
  assert(['Issued', 'MaterialIssued', 'InProduction', 'OnHold'].includes(card.status), 'Approve and issue materials before updating production.');
  const all = orderedStages(card);
  assert(new Set(all.map(s => s.id)).size === all.length && new Set(all.map(s => s.sequence)).size === all.length && all.every(s => Number.isFinite(s.sequence) && s.sequence > 0), 'Stage IDs and sequence numbers must be unique and valid.');
  const stage = all.find(s => s.id === id);
  assert(stage && stage.required && stage.kind === 'production', 'Select a required production stage.');
  const approvedStage = card.estimateId ? card.routingApproved?.stages.find(s => s.id === id) : undefined;
  if (approvedStage) assert(update.inputUnit === approvedStage.inputUnit && update.outputUnit === approvedStage.outputUnit && update.wasteUnit === approvedStage.wasteUnit, 'Actual stage units must match the PM-approved routing.');
  assert(stage.status !== 'Completed', 'Completed stage records are locked.');
  const previous = all.filter(s => s.required && s.kind === 'production' && s.sequence < stage.sequence);
  assert(previous.every(s => s.status === 'Completed'), 'Complete the previous stages before updating this stage.');
  assert(Object.hasOwn(PRODUCTION_STATUS_LABELS, update.status), 'Invalid stage status.');
  for (const value of [update.inputQuantity, update.outputQuantity, update.wasteQuantity]) assert(value === null || validQuantity(value), 'Stage quantities must be finite and nonnegative.');
  assert(Number.isFinite(update.sentToRecycling ?? 0) && (update.sentToRecycling ?? 0) >= 0 && (update.sentToRecycling ?? 0) <= (update.wasteQuantity ?? 0), 'Recycling quantity cannot exceed stage waste.');
  if (stage.handover && stage.handover.unit === stage.inputUnit) assert(update.inputUnit === stage.inputUnit && update.inputQuantity === stage.handover.quantity, 'Received input and unit must match the previous stage output.');
  if (update.status !== 'Pending') {
    assert(validQuantity(update.inputQuantity) && update.inputUnit.trim(), 'Record input quantity and unit.');
    assert(update.operator.trim(), 'Record the responsible operator.');
  }
  if (['InProgress', 'Completed', 'OnHold'].includes(update.status)) assert(Number.isFinite(timestamp(update.startedAt)), 'Record a valid start date/time.');
  if (update.completedAt) assert(update.status === 'Completed', 'Completion time is only allowed for a completed stage.');
  if (update.startedAt) assert(Number.isFinite(timestamp(update.startedAt)) && timestamp(update.startedAt) <= timestamp(now), 'Start time cannot be invalid or in the future.');
  if (update.status === 'Completed') {
    assert(validQuantity(update.outputQuantity) && validQuantity(update.wasteQuantity) && update.outputUnit.trim() && update.wasteUnit.trim(), 'Record output, waste and their units.');
    assert(Number.isFinite(timestamp(update.completedAt)) && timestamp(update.completedAt) >= timestamp(update.startedAt) && timestamp(update.completedAt) <= timestamp(now), 'Completion time must follow the start and cannot be in the future.');
  }
  if (update.inputUnit && update.inputUnit === update.outputUnit && update.inputQuantity !== null && update.outputQuantity !== null) {
    assert(update.outputQuantity <= update.inputQuantity + 1e-6, 'Output cannot exceed input in the same unit.');
    if (update.wasteUnit === update.inputUnit && update.wasteQuantity !== null) assert(update.outputQuantity + update.wasteQuantity <= update.inputQuantity + 1e-6, 'Output plus waste exceeds input.');
  }
  let activityHistory = event(card, user, `${stage.name}: ${PRODUCTION_STATUS_LABELS[update.status]}`, `Input ${fmtQuantity(update.inputQuantity, update.inputUnit)}; output ${fmtQuantity(update.outputQuantity, update.outputUnit)}; waste ${fmtQuantity(update.wasteQuantity, update.wasteUnit)}.`, now);
  const productionStages = all.map(s => s.id === id ? { ...s, ...update } : { ...s });
  if (update.status === 'Completed') {
    const next = productionStages.find(s => s.required && s.kind === 'production' && s.sequence > stage.sequence);
    if (next) {
      assert(next.status === 'Pending' && next.inputQuantity === null && !next.handover, 'The next stage already has recorded input; handover would overwrite it.');
      next.handover = { quantity: update.outputQuantity!, unit: update.outputUnit, fromStageId: stage.id };
      if (next.inputUnit === update.outputUnit) { next.inputQuantity = update.outputQuantity; next.status = 'Received'; }
      activityHistory = [...activityHistory, { id: crypto.randomUUID(), timestamp: now, user: user.name, department: next.department, action: 'Stage handover', description: `${stage.name} sent ${fmtQuantity(update.outputQuantity, update.outputUnit)} to ${next.name}.${next.inputUnit !== update.outputUnit ? ' Different input unit: enter the received quantity explicitly; no conversion is assumed.' : ''}` }];
    }
  }
  const required = productionStages.filter(s => s.required && s.kind === 'production');
  const ready = required.length > 0 && required.every(s => s.status === 'Completed');
  const status = ready ? 'ReadyForStock' : required.some(s => s.status === 'OnHold') ? 'OnHold' : required.some(s => ['InProgress', 'Completed'].includes(s.status)) ? 'InProduction' : 'MaterialIssued';
  const updated = { ...card, productionStages, status, activityHistory } as JobCard;
  return { ...updated, department: currentLocation(updated).department, stages: card.stages.map(legacy => {
    const tracked = productionStages.find(s => s.legacyStage === legacy.stage);
    return tracked ? { ...legacy, required: tracked.required, status: tracked.status === 'Completed' ? 'Complete' : ['InProgress', 'OnHold'].includes(tracked.status) ? 'InProgress' : 'Pending' } : legacy;
  }) };
}
```

### src/lib/jobCards.ts:150

```typescript
export function transferJobToStock(card: JobCard, acceptedQuantity: number, batchDate: string, user: User, now = new Date().toISOString(), receipt?: StockReceiptOptions): JobCard {
  requireRole(user, ['store_keeper', 'admin']);
  if (receipt && card.stockTransfers?.some(r => r.id === receipt.id)) return card;
  assert(card.approval, 'Production Manager approval is required.');
  assert(card.status === 'ReadyForStock' && (!card.stockTransfer || !!receipt), 'Only ready jobs can be transferred once.');
  const totals = productionTotals(card);
  const previouslyAccepted = card.acceptedQuantity ?? 0, previouslyRejected = card.rejectedQuantity ?? 0;
  const rejected = receipt?.rejected ?? Math.max(0, (totals.produced ?? 0) - acceptedQuantity);
  if (receipt) assert(receipt.id && receipt.batch.trim() && receipt.qcVerified, 'Record a batch and confirm QC verification.');
  assert(validQuantity(rejected) && previouslyAccepted + previouslyRejected + acceptedQuantity + rejected <= (totals.produced ?? 0), 'Accepted and rejected batches exceed produced quantity.');
  const complete = Math.abs(previouslyAccepted + previouslyRejected + acceptedQuantity + rejected - (totals.produced ?? 0)) < 1e-6;
  assert(productionStages(card).every(s => s.status === 'Completed'), 'Complete all required production stages.');
  assert(validQuantity(acceptedQuantity) && (acceptedQuantity > 0 || (!!receipt && rejected > 0)) && totals.produced !== null && acceptedQuantity <= totals.produced && totals.unit, 'Confirm positive accepted or rejected quantity; accepted quantity cannot exceed final output.');
  assert(/^\d{4}-\d{2}-\d{2}$/.test(batchDate) && Number.isFinite(Date.parse(batchDate)) && batchDate <= new Date(now).toLocaleDateString('en-CA') && (!card.createdDate || batchDate >= card.createdDate.slice(0, 10)), 'Choose a valid batch date between creation and today.');
  return { ...card, status: complete ? 'Completed' : 'ReadyForStock', department: 'Stock Keeping', acceptedQuantity: previouslyAccepted + acceptedQuantity, rejectedQuantity: previouslyRejected + rejected,
    stockTransfers: [...(card.stockTransfers ?? []), { id: receipt?.id ?? `receipt-${card.id}`, batch: receipt?.batch ?? `LOT-${card.jobCardNumber}`, quantity: acceptedQuantity, rejectedQuantity: rejected, date: batchDate }],
    stages: card.stages.map(stage => card.productionStages?.some(s => s.required && s.kind === 'stock' && s.legacyStage === stage.stage) ? { ...stage, status: 'Complete' } : stage),
    stockTransfer: { quantity: acceptedQuantity, unit: totals.unit, batchDate, confirmedBy: user.name, confirmedAt: now, jobCardId: card.id, salesOrderId: card.salesOrderId, customerName: card.customerName ?? '', modelName: card.modelName, product: card.product ?? card.modelName },
    productionStages: orderedStages(card).map(s => s.required && s.kind === 'stock' ? { ...s, status: 'Completed', inputQuantity: acceptedQuantity, outputQuantity: acceptedQuantity, wasteQuantity: 0, inputUnit: totals.unit, outputUnit: totals.unit, wasteUnit: totals.unit, operator: user.name, startedAt: now, completedAt: now } : s),
    activityHistory: event(card, user, 'Finished quantity confirmed', `${fmtQuantity(acceptedQuantity, totals.unit)} confirmed for Stock Keeping. Verified transfer reference prepared; shared inventory posting is performed by JobCardsContext.`, now) };
}
```

### src/lib/jobCards.ts:171

```typescript
export function editJobCard(card: JobCard, change: Pick<JobCard, 'modelName' | 'product' | 'specifications' | 'qty' | 'unit' | 'requiredDate' | 'productionRequirements'>, user: User, now = new Date().toISOString()): JobCard {
  requireRole(user, ['production_manager', 'admin']);
  assert(['Draft', 'PendingApproval'].includes(card.status), 'Job fields are locked after approval.');
  assert(change.modelName.trim() && change.product?.trim() && Number.isFinite(change.qty) && change.qty > 0 && change.unit?.trim(), 'Model, product, positive order quantity and unit are required.');
  assert(!!change.requiredDate && /^\d{4}-\d{2}-\d{2}$/.test(change.requiredDate) && Number.isFinite(Date.parse(change.requiredDate)) && (!card.createdDate || change.requiredDate >= card.createdDate.slice(0, 10)), 'Required date must be valid and on or after creation.');
  return { ...card, ...change, activityHistory: event(card, user, 'Job card edited', 'Production Manager updated job specifications and requirements.', now) };
}
```

### src/lib/jobCards.ts:178

```typescript
export function toggleJobStage(card: JobCard, id: string, user: User, now = new Date().toISOString()): JobCard {
  requireRole(user, ['receptionist', 'production_manager', 'admin']);
  assert(!card.approval && ['Draft', 'PendingApproval'].includes(card.status), 'Approved routing is locked; request an authorized revision before changing stages.');
  const stage = card.productionStages?.find(s => s.id === id);
  assert(stage && stage.status === 'Pending', 'Only pending stages can be added or removed.');
  if (stage.required && stage.kind === 'production') assert(productionStages(card).length > 1, 'Keep at least one required production stage.');
  if (!stage.required && stage.kind === 'production') assert(!productionStages(card).some(s => s.sequence > stage.sequence && s.status !== 'Pending'), 'Cannot insert a stage before production that has already been received or started.');
  const updated: JobCard = { ...card, productionStages: card.productionStages!.map(s => s.id === id ? { ...s, required: !s.required } : s),
    stages: card.stages.map(s => s.stage === stage.legacyStage ? { ...s, required: !stage.required } : s),
    activityHistory: event(card, user, 'Stage requirement changed', `${stage.name} ${stage.required ? 'removed from' : 'added to'} required production.`, now) };
  if (['MaterialIssued', 'Issued', 'InProduction', 'OnHold', 'ReadyForStock'].includes(card.status)) {
    const required = productionStages(updated);
    if (required.length && required.every(s => s.status === 'Completed')) updated.status = 'ReadyForStock';
    else if (card.status === 'ReadyForStock') updated.status = 'InProduction';
  }
  return { ...updated, department: currentLocation(updated).department };
}
```
### src/lib/led.ts:7

```typescript
const money=(n:number)=>Math.round(n*100)/100;
```

### src/lib/led.ts:8

```typescript
export function calculateLED(base:number,weightKG:number|null,usdToUGX:number|undefined,fxDate:string|undefined,percentageBase:LEDInput['percentageBase'],vatOnLED=false):LEDSnapshot {
 if(!['net-selling','production-cost'].includes(percentageBase??''))throw new Error('Choose the LED percentage base; final client base clarification is pending.');
 if(!Number.isFinite(base)||base<0)throw new Error('LED percentage base must be finite and nonnegative.');
 if(weightKG===null||!Number.isFinite(weightKG)||weightKG<0)throw new Error('LED MAX comparison requires eligible KG. Configure an exact product/model CTR conversion; percentage-only fallback is not permitted.');
 if(!usdToUGX||!Number.isFinite(usdToUGX)||usdToUGX<=0||!fxDate||!/^\d{4}-\d{2}-\d{2}$/.test(fxDate)||!Number.isFinite(Date.parse(fxDate))||new Date(fxDate+'T00:00:00Z').toISOString().slice(0,10)!==fxDate)throw new Error('LED MAX comparison requires a saved positive USD→UGX exchange rate and valid rate date.');
 const percentage=base*LED_PERCENT/100,weight=weightKG/1000*LED_USD_PER_TONNE*usdToUGX;
 if(![percentage,weight].every(Number.isFinite))throw new Error('LED exceeds the supported amount range.');
 return {method:'higher',percentageBase:percentageBase!,baseAmount:base,eligibleWeightKG:weightKG,percentageRate:LED_PERCENT,usdPerTonne:LED_USD_PER_TONNE,usdToUGX,fxDate,percentageAmount:money(percentage),weightAmount:money(weight),selectedUnrounded:Math.max(percentage,weight),selectedAmount:money(Math.max(percentage,weight)),selected:Math.abs(percentage-weight)<=Number.EPSILON*Math.max(1,percentage,weight)*8?'equal':percentage>weight?'percentage':'weight',vatOnLED};
}
```

### src/lib/led.ts:17

```typescript
export function calculateConfiguredLED(input:LEDInput|undefined,netSelling:number,productionCost:number|undefined,currency:string):LEDSnapshot|undefined {
 if(!input?.applies)return;
 if(currency!=='UGX')throw new Error('LED is calculated in UGX. Use an UGX costing/quotation; no implicit document currency conversion.');
 const base=input.percentageBase==='production-cost'?productionCost:netSelling;
 if(base===undefined)throw new Error('Production-cost LED base requires an approved costing source.');
 return {...calculateLED(base,input.eligibleWeightKG,input.usdToUGX,input.fxDate,input.percentageBase,input.vatOnLED),conversion:input.conversion?structuredClone(input.conversion):undefined};
}
```
### src/lib/operations.ts:7

```typescript
export function salesMetrics(orders:SalesOrder[],cards:JobCard[],ledger:FulfillmentLedger) {
  const units:Record<string,number>={},confirmed:Record<string,number>={},dispatched:Record<string,number>={}; const products=new Set<string>(); let lines=0;
  const statuses=orders.map(o=>orderFulfillmentStatus(o,ledger,cards));
  orders.forEach(o=>{(o.items??[]).forEach(i=>{lines++;products.add(i.itemId??(i.modelId?`model:${i.modelId}`:`unlinked:${o.id}:${i.id}`));if(o.status!=='Cancelled')units[i.unit]=(units[i.unit]??0)+i.quantity;});
    const knownConfirmed=!['Draft','Open','Cancelled'].includes(o.status)||ledger.dispatches.some(d=>d.orderId===o.id&&d.status==='Confirmed');
    if(knownConfirmed&&o.currency&&o.orderTotal!==undefined)confirmed[o.currency]=roundMoney((confirmed[o.currency]??0)+o.orderTotal);
    if(o.currency){const items=o.items??[],basis=items.reduce((s,i)=>s+i.totalPrice,0);ledger.dispatches.filter(d=>d.orderId===o.id&&d.status==='Confirmed').forEach(d=>{const i=items.find(i=>i.id===d.itemId);if(i){const value=items.some(l=>l.ledSnapshot)?calculateCommercialTotals([{quantity:d.quantity,unitPrice:i.unitPrice,ledSnapshot:i.ledSnapshot?{...i.ledSnapshot,selectedAmount:i.ledSnapshot.selectedAmount*d.quantity/i.quantity}:undefined}],(o.commercialPricing?.discount??0)*(basis?i.unitPrice*d.quantity/basis:0),o.taxRate??0,o.commercialPricing?.taxMode??'exclusive').total:i.unitPrice*d.quantity*(basis&&o.orderTotal!==undefined?o.orderTotal/basis:1);dispatched[o.currency!]=roundMoney((dispatched[o.currency!]??0)+value);}});}
  });
  return {total:orders.length,products:products.size,lines,units,confirmed,dispatched,linkedCards:new Set(cards.filter(c=>orders.some(o=>o.id===c.salesOrderId)).map(c=>c.id)).size,unloadedCardReferences:new Set(orders.flatMap(o=>o.jobCardIds).filter(id=>!cards.some(c=>c.id===id))).size,manufacturing:orders.filter(o=>o.items?.some(i=>i.fulfillmentSource==='manufacturing')).length,stockOrders:orders.filter(o=>o.items?.length&&o.items.every(i=>i.fulfillmentSource==='stock')).length,partial:statuses.filter(s=>s==='Partially Dispatched').length,completed:statuses.filter(s=>['Completed','Dispatched'].includes(s)).length,pending:statuses.filter(s=>!['Completed','Dispatched','Cancelled'].includes(s)).length,forStock:cards.filter(c=>c.origin==='production_for_stock'&&!c.salesOrderId).length};
}
```

### src/lib/operations.ts:17

```typescript
export function stageTracking(card:JobCard) {
  const stages=productionStages(card),current=stages.find(s=>['Received','InProgress','OnHold'].includes(s.status))??stages.find(s=>s.status==='Pending');
  return {stages,current,next:current?stages.find(s=>s.sequence>current.sequence&&s.status!=='Completed'):undefined,completed:stages.filter(s=>s.status==='Completed'),pending:stages.filter(s=>s.status!=='Completed'),lastUpdate:(card.activityHistory??[]).map(e=>e.timestamp).sort().at(-1)};
}
```

### src/lib/operations.ts:21

```typescript
export function massBalance(card:JobCard) {
  const stages=productionStages(card),first=stages[0],last=stages.at(-1);
  const kg=(q:number|null|undefined,u:string|undefined)=>{if(q===null||q===undefined||!u)return null;try{return convertQuantity(q,u,'kg');}catch{return null;}};
  const input=kg(first?.inputQuantity,first?.inputUnit),output=kg(last?.outputQuantity,last?.outputUnit),wastes=stages.map(s=>kg(s.wasteQuantity,s.wasteUnit));
  const waste=wastes.length&&wastes.every(n=>n!==null)?wastes.reduce<number>((s,n)=>s+(n??0),0):null;
  const difference=input!==null&&output!==null&&waste!==null?Math.round((input-output-waste)*1e6)/1e6:null;
  return {input,output,waste,difference,otherLosses:null,message:difference===null?'Insufficient compatible KG measurements':difference!==0?'Unexplained difference — review other process losses / measurement basis':'Measured quantities reconcile; other losses are not recorded'};
}
```
### src/lib/parentJobCards.ts:4

```typescript
export const manufacturingLines = (order: SalesOrder) => (order.items ?? []).filter(i => i.fulfillmentSource === 'manufacturing');
```

### src/lib/parentJobCards.ts:5

```typescript
export const workItems = (card: JobCard): JobCard[] => card.manufacturingItems ?? [card];
```

### src/lib/parentJobCards.ts:6

```typescript
export const findWorkItem = (cards: JobCard[], id: string) => cards.flatMap(workItems).find(i => i.id === id);
```

### src/lib/parentJobCards.ts:7

```typescript
export const parentForItem = (cards: JobCard[], id: string) => cards.find(c => c.id === id || c.manufacturingItems?.some(i => i.id === id));
```

### src/lib/parentJobCards.ts:9

```typescript
export function summarizeParent(parent: JobCard, items: JobCard[]): JobCard {
  if (!items.length || items.some(i => i.manufacturingItems || i.parentJobCardId !== parent.id || i.salesOrderId !== parent.salesOrderId || !i.salesOrderItemId) || new Set(items.map(i => i.id)).size !== items.length || new Set(items.map(i => i.salesOrderItemId)).size !== items.length) throw new Error('Parent manufacturing items must have distinct stable item and order-line references.');
  const status = items.every(i => i.status === 'Completed') ? 'Completed'
    : items.some(i => i.status === 'Draft' || i.status === 'PendingApproval') ? 'PendingApproval'
    : items.some(i => i.status === 'OnHold') ? 'OnHold'
    : items.every(i => ['ReadyForStock', 'Completed'].includes(i.status)) ? 'ReadyForStock'
    : items.some(i => i.status === 'InProduction' || i.status === 'Completed' || i.status === 'ReadyForStock') ? 'InProduction'
    : items.some(i => i.status === 'MaterialIssued' || i.status === 'Issued') ? 'MaterialIssued' : 'StoreIssuePending';
  const events = items.flatMap(i => (i.activityHistory ?? []).map(e => ({ ...e, jobCardId: parent.id, manufacturingItemId: i.id })));
  const ownEvents = (parent.activityHistory ?? []).filter(e => !e.manufacturingItemId);
  return { ...parent, manufacturingItems: items, status, department: 'See manufacturing items',
    requiredDate: items.map(i => i.requiredDate).filter((d): d is string => !!d).sort()[0],
    activityHistory: [...ownEvents, ...events].sort((a, b) => a.timestamp.localeCompare(b.timestamp)) };
}
```

### src/lib/parentJobCards.ts:24

```typescript
export function attachManufacturingItem(cards: JobCard[], order: SalesOrder, item: JobCard): { parent: JobCard; item: JobCard } {
  if (!manufacturingLines(order).some(line => line.id === item.salesOrderItemId)) throw new Error('Only manufacturing lines belong in a parent Job Card.');
  const linked = cards.filter(c => c.salesOrderId === order.id);
  if (linked.some(c => !c.manufacturingItems) || linked.length > 1) throw new Error('Historical Job Cards are preserved. An authorized migration of existing references is required before adding manufacturing items.');
  const existing = linked[0];
  const duplicate = existing?.manufacturingItems?.find(i => i.salesOrderItemId === item.salesOrderItemId);
  if (duplicate) return { parent: existing!, item: duplicate };
  if (existing?.manufacturingItems?.some(i => i.approval || !['Draft', 'PendingApproval'].includes(i.status))) throw new Error('Manufacturing items cannot be added after approval. Request an authorized order amendment.');
  const parent: JobCard = existing ?? { id: crypto.randomUUID(), jobCardNumber: item.jobCardNumber,
    origin: 'sales_order', salesOrderId: order.id, salesOrderNumber: order.orderNumber, customerName: order.customerName,
    modelName: 'Multiple manufacturing items', qty: 0, status: 'PendingApproval', department: 'Production Manager', stages: [],
    createdDate: item.createdDate, activityHistory: [] };
  const child = { ...item, parentJobCardId: parent.id, origin: 'sales_order' as const, jobCardNumber: parent.jobCardNumber };
  return { parent: summarizeParent(parent, [...(existing?.manufacturingItems ?? []), child]), item: child };
}
```

### src/lib/parentJobCards.ts:40

```typescript
export function assertCompleteManufacturingScope(parent: JobCard, order?: SalesOrder) {
  if (!parent.manufacturingItems) return;
  if (!order || manufacturingLines(order).length !== parent.manufacturingItems.length || manufacturingLines(order).some(line => !parent.manufacturingItems!.some(i => i.salesOrderItemId === line.id && i.qty === line.quantity && i.unit === line.unit))) throw new Error('Prepare every manufacturing line with its ordered quantity and unit before approving the parent Job Card.');
}
```
### src/lib/productionRouting.ts:3

```typescript
export function validateRouting(stages: JobProductionStage[]) {
  if (!stages.some(s => s.required && s.kind === 'production') || new Set(stages.map(s => s.id)).size !== stages.length || new Set(stages.map(s => s.sequence)).size !== stages.length) throw new Error('Keep mandatory production stages with unique IDs and sequences.');
  if (stages.some(s => !s.name.trim() || !s.department.trim() || !s.inputUnit.trim() || !s.outputUnit.trim() || !s.wasteUnit.trim() || !Number.isInteger(s.sequence) || s.sequence < 1 || [s.expectedInput, s.expectedOutput, s.plannedWastePercent].some(n => n !== undefined && (!Number.isFinite(n) || n < 0)) || (s.plannedWastePercent ?? 0) > 100)) throw new Error('Complete stage names, departments, units and valid planned quantities/waste.');
}
```

### src/lib/productionRouting.ts:7

```typescript
export function changeRouting(card: JobCard, stages: JobProductionStage[], materials: JobCardMaterial[], user: User): JobCard {
  if (!['admin', 'production_manager'].includes(user.role)) throw new Error('Only Production Manager/Admin can edit routing.');
  if (card.approval || !['Draft', 'PendingApproval'].includes(card.status) || orderedStages(card).some(s => s.status !== 'Pending')) throw new Error('Approved or started routing is locked. Use authorized revision/reapproval before production.');
  validateRouting(stages);
  if (!materials.length || materials.some(m => !m.materialId || !m.unit.trim() || !Number.isFinite(m.requiredQuantity) || m.requiredQuantity <= 0 || m.issuedQuantity !== 0) || new Set(materials.map(m => m.materialId)).size !== materials.length) throw new Error('Complete distinct unissued material requirements.');
  const nextStages = stages.map((s, i) => ({ ...s, sequence: i + 1, status: 'Pending' as const, inputQuantity: null, outputQuantity: null, wasteQuantity: null, operator: '', remarks: '', startedAt: undefined, completedAt: undefined, handover: undefined }));
  return { ...card, status: 'Draft', routingRevision: (card.routingRevision ?? 1) + 1, productionStages: nextStages, requiredMaterials: structuredClone(materials), requirementsReviewRequired: true, activityHistory: [...(card.activityHistory ?? []), { id: crypto.randomUUID(), timestamp: new Date().toISOString(), action: 'Routing revised', user: user.name, department: 'Production Manager', description: 'Proposed route/materials changed; linked costing requires recalculation/review.' }] };
}
```

### src/lib/productionRouting.ts:15

```typescript
export function reopenRouting(card: JobCard, user: User): JobCard {
  if (!['admin', 'production_manager'].includes(user.role)) throw new Error('Your role cannot request routing revision.');
  if (!card.approval || card.stockTransfers?.length || (card.requiredMaterials ?? []).some(m => m.issuedQuantity > 0) || orderedStages(card).some(s => s.status !== 'Pending')) throw new Error('Reapproval is available only before material issue or production. Recorded history cannot be discarded.');
  return { ...card, approval: undefined, status: 'Draft', routingApprovalHistory: [...(card.routingApprovalHistory ?? []), ...(card.routingApproved ? [structuredClone(card.routingApproved)] : [])], routingApproved: undefined, requirementsReviewRequired: true, activityHistory: [...(card.activityHistory ?? []), { id: crypto.randomUUID(), timestamp: new Date().toISOString(), action: 'Routing revision requested', user: user.name, department: 'Production Manager', description: 'Previous approval retained in activity history; a new routing approval is required.' }] };
}
```
### src/lib/productionRuns.ts:5

```typescript
export function appendProductionRun(card:JobCard,run:ProductionRun,finish:boolean,user:User,now=new Date().toISOString()):JobCard {
 const duplicate=card.productionRuns?.find(r=>r.id===run.id);if(duplicate){if(JSON.stringify({...duplicate,inputKG:undefined,completesStage:undefined})!==JSON.stringify({...run,inputKG:undefined,completesStage:undefined}) || duplicate.completesStage!==finish)throw new Error('Run request ID conflicts.');return card;}
 const stage=card.productionStages?.find(s=>s.id===run.stageId);if(!stage||!run.id||!run.number.trim()||card.productionRuns?.some(r=>r.number===run.number)||![run.inputQuantity,run.outputQuantity,run.wasteQuantity].every(n=>Number.isFinite(n)&&n>=0)||run.inputQuantity<=0||!run.operator.trim()||![run.startedAt,run.completedAt].every(t=>Number.isFinite(Date.parse(t)))||run.startedAt>run.completedAt||Date.parse(run.completedAt)>Date.parse(now))throw new Error('Complete distinct run identity, quantities, operator and valid chronological times.');
 if(run.inputUnit===run.outputUnit && (run.outputQuantity>run.inputQuantity+1e-6 || run.wasteUnit===run.inputUnit && run.outputQuantity+run.wasteQuantity>run.inputQuantity+1e-6))throw new Error('Run output/waste exceeds its own input.');
 if(run.inputUnit!==stage.inputUnit||run.outputUnit!==stage.outputUnit||run.wasteUnit!==stage.wasteUnit)throw new Error('Run units must match the approved stage units.');
 const priorStage=(card.productionStages??[]).filter(s=>s.required&&s.kind==='production'&&s.sequence<stage.sequence).sort((a,b)=>b.sequence-a.sequence)[0];if(priorStage?.completedAt&&Date.parse(run.startedAt)<Date.parse(priorStage.completedAt))throw new Error('Run cannot start before the previous stage completed.');
 const previous=(card.productionRuns??[]).filter(r=>r.stageId===stage.id);
 if(!previous.length&&stage.outputQuantity!==null&&stage.outputQuantity>0)throw new Error('Historical stage quantities cannot be replaced by run aggregates.');
 if(previous.some(r=>Date.parse(r.completedAt)>Date.parse(run.startedAt)))throw new Error('Runs of this stage cannot overlap.');
 let inputKG:number|undefined;try{inputKG=convertQuantity(run.inputQuantity,run.inputUnit,'kg');}catch{/* No invented package conversion. */}
 const saved={...run,inputKG,completesStage:finish},runs=[...(card.productionRuns??[]),saved],selected=runs.filter(r=>r.stageId===stage.id),sum=(key:'inputQuantity'|'outputQuantity'|'wasteQuantity')=>selected.reduce((n,r)=>n+r[key],0);
 if(stage.handover?.unit===stage.inputUnit&&sum('inputQuantity')>stage.handover.quantity+1e-6)throw new Error('Run input exceeds received stage input.');
 if(finish&&stage.handover?.unit===stage.inputUnit&&Math.abs(sum('inputQuantity')-stage.handover.quantity)>1e-6)throw new Error('Account for all handed-over input before completing this stage.');
 const next=updateJobStage(card,stage.id,{status:finish?'Completed':'InProgress',inputQuantity:stage.handover?.unit===stage.inputUnit?stage.handover.quantity:sum('inputQuantity'),outputQuantity:sum('outputQuantity'),wasteQuantity:sum('wasteQuantity'),inputUnit:stage.inputUnit,outputUnit:stage.outputUnit,wasteUnit:stage.wasteUnit,operator:run.operator,startedAt:selected[0].startedAt,completedAt:finish?run.completedAt:undefined,remarks:run.remarks,sentToRecycling:stage.sentToRecycling??0},user,now);
 return {...next,productionRuns:runs,activityHistory:[...(next.activityHistory??[]),{id:crypto.randomUUID(),timestamp:now,user:user.name,department:stage.department,action:'Production run recorded',description:`${run.number}; stage ${stage.name}; ${run.outputQuantity} ${run.outputUnit}; ${finish?'stage completed':'additional run allowed; no handover yet'}.`}]};
}
```
### src/lib/productModels.ts:3

```typescript
export function reviseProductModel(model: Model, versions: Model[]): Model {
  if (!model.id || !model.name.trim() || !model.defaultUnit?.trim()) throw new Error('Model ID, name and default quantity unit are required.');
  if ((model.recipe ?? []).some(m => !RAW_MATERIALS.some(raw => raw.id === m.materialId && raw.unit === m.unit))) throw new Error('Recipe must reference selected raw material IDs and units.');
  for (const n of [model.wastePercent, model.overheads, model.batchQuantity, model.costingConfig?.markupPercent, model.costingConfig?.taxPercent]) if (n !== undefined && (!Number.isFinite(n) || n < 0)) throw new Error('Model defaults must be finite and nonnegative.');
  if ((model.wastePercent ?? 0) > 100 || (model.costingConfig?.taxPercent ?? 0) > 100) throw new Error('Model waste/tax percentages cannot exceed 100.');
  const revision = Math.max(0, ...versions.filter(m => m.id === model.id).map(m => m.revision ?? 1)) + 1;
  return structuredClone({ ...model, revision });
}
```
### src/lib/quality.ts:19

```typescript
export const canRecordQC = (role?: Role) => !!role && ['qc_inspector', 'qc_supervisor', 'admin'].includes(role);
```

### src/lib/quality.ts:20

```typescript
export const canViewQC = (role?: Role) => !!role && QC_VIEW_ROLES.includes(role);
```

### src/lib/quality.ts:21

```typescript
export const isQCRole = (role?: Role) => role === 'qc_inspector' || role === 'qc_supervisor';
```

### src/lib/quality.ts:22

```typescript
export const optionsFor = (type: ResponseType): string[] => ({ yes_no: ['Yes', 'No'], ok_not_ok: ['OK', 'Not OK'], tick_cross: ['Tick', 'Cross'], pass_fail: ['Pass', 'Fail'], numeric: [], text: [] })[type];
```

### src/lib/quality.ts:23

```typescript
function ensure(value: unknown, message: string): asserts value { if (!value) throw new Error(message); }
```

### src/lib/quality.ts:24

```typescript
const role = (user: User, roles: Role[]) => ensure(roles.includes(user.role), 'Your role cannot perform this QC action.');
```

### src/lib/quality.ts:25

```typescript
const validDate = (date: string) => /^\d{4}-\d{2}-\d{2}$/.test(date) && Number.isFinite(Date.parse(date)) && new Date(`${date}T00:00:00Z`).toISOString().slice(0, 10) === date;
```

### src/lib/quality.ts:26

```typescript
const finite = (n: unknown): n is number => typeof n === 'number' && Number.isFinite(n);
```

### src/lib/quality.ts:27

```typescript
const event = (user: User, type: string, description: string): QCEvent => ({ id: crypto.randomUUID(), type, description, userId: user.id, user: user.name, at: new Date().toISOString() });
```

### src/lib/quality.ts:28

```typescript
export function validateTemplate(t: QCTemplate) {
  ensure(!(t.id === 'ksec' && t.active && t.items.some(i => i.label === 'Client-confirmed checklist required before activation')), 'Configure client-confirmed KSEC checks before activation; its meaning is undefined.');
  ensure(t.id && t.name.trim() && t.department.trim() && validDate(t.effectiveDate), 'Complete template identity, department and effective date.');
  ensure(QC_FREQUENCIES.includes(t.frequency), 'Choose a supported frequency.');
  ensure(t.items.length && new Set(t.items.map(i => i.id)).size === t.items.length, 'Use distinct checklist items.');
  t.items.forEach(i => { ensure(i.label.trim() && (i.type === 'text' || i.type === 'numeric' || optionsFor(i.type).includes(i.acceptable ?? '')), 'Set an acceptable answer for each choice item.'); });
}
```

### src/lib/quality.ts:35

```typescript
export function responsePass(item: QCItem, response: QCResponse): boolean {
  if (response.value === 'NA') return item.allowNA && !!response.remarks.trim();
  if (item.type === 'text') return !!response.value.trim();
  if (item.type !== 'numeric') return response.value === item.acceptable;
  const actual = Number(response.value);
  return !!response.value.trim() && finite(actual) && finite(response.target) && finite(response.lowerTolerance) && finite(response.upperTolerance) && response.lowerTolerance >= 0 && response.upperTolerance >= 0 && !!response.unit?.trim() && actual >= response.target - response.lowerTolerance && actual <= response.target + response.upperTolerance;
}
```

### src/lib/quality.ts:42

```typescript
export function inspectionResult(i: QCInspection): 'Pass' | 'Fail' {
  ensure(Number.isInteger(i.sampleCount) && i.sampleCount >= 1 && i.sampleCount <= (i.template.category === 'production' ? 8 : 1), 'Use one to eight production samples; other records have one response set.');
  ensure(new Set(i.responses.map(r => `${r.itemId}:${r.sample}`)).size === i.responses.length && i.responses.every(r => i.template.items.some(t => t.id === r.itemId) && Number.isInteger(r.sample) && r.sample >= 1 && r.sample <= i.sampleCount), 'Responses must reference distinct items and valid sample numbers.');
  let failed = false, applicable = 0;
  for (let sample = 1; sample <= i.sampleCount; sample++) for (const item of i.template.items) {
    const r = i.responses.find(r => r.itemId === item.id && r.sample === sample);
    if (!r?.value.trim() && !item.required) continue;
    ensure(r && r.value.trim(), `Record ${item.label}, sample ${sample}.`);
    ensure(r.value !== 'NA' || (item.allowNA && r.remarks.trim()), 'Not Applicable needs permission and a reason.');
    if (r.value !== 'NA') applicable++;
    if (item.type === 'numeric' && r.value !== 'NA') ensure(finite(Number(r.value)) && finite(r.target) && finite(r.lowerTolerance) && finite(r.upperTolerance) && r.lowerTolerance >= 0 && r.upperTolerance >= 0 && !!r.unit?.trim(), 'Record actual measurement, specification target, nonnegative tolerances and unit.');
    if (!['numeric', 'text'].includes(item.type) && r.value !== 'NA') ensure(optionsFor(item.type).includes(r.value), 'Invalid checklist answer.');
    const pass = responsePass(item, r);
    ensure(!(item.remarksRequired || !pass) || !!r.remarks.trim(), 'Record remarks for required or non-compliant findings.');
    failed ||= !pass;
  }
  ensure(applicable > 0, 'An all-Not-Applicable inspection cannot pass.');
  return failed ? 'Fail' : 'Pass';
}
```

### src/lib/quality.ts:61

```typescript
export function createInspection(template: QCTemplate, subject: QCSubject, user: User, date: string, department: string, sampleCount = 1): QCInspection {
  ensure(canRecordQC(user.role), 'Only QC staff/Admin can record inspections.'); validateTemplate(template);
  ensure(template.active && subject.kind === template.category && date >= template.effectiveDate && validDate(date) && department.trim(), 'Use an active applicable template, date and department.');
  ensure(subject.label.trim(), 'Select an inspection subject.');
  if (subject.kind === 'raw') ensure(subject.receiptId && subject.materialId && finite(subject.quantity) && subject.quantity > 0 && subject.unit, 'Link an exact Raw Material IN receipt.');
  if (subject.kind === 'production') ensure(subject.jobCardId && subject.manufacturingItemId && subject.stageId && subject.batchId && subject.batchNumber && finite(subject.quantity) && subject.quantity >= 0 && subject.unit, 'Link the exact Job Card item, stage and QC lot.');
  if (subject.kind === 'machine') ensure(subject.machineId && subject.machineType === template.applicable, 'Select a machine with the matching machine type.');
  if (subject.kind === 'cleaning') ensure(subject.areaId, 'Select a configured cleaning area.');
  ensure(Number.isInteger(sampleCount) && sampleCount >= 1 && sampleCount <= (subject.kind === 'production' ? 8 : 1), 'Invalid sample count.');
  const id = crypto.randomUUID();
  return { id, number: `QC-${id.slice(0, 8)}`, template: structuredClone(template), subject: structuredClone(subject), date, time: '', department, inspectorId: user.id, inspector: user.name, assignedTo: user.id, sampleCount, responses: [], metadata: {}, comments: '', status: 'Draft', approvals: [], events: [event(user, 'Created', 'Inspection created with an exact template revision snapshot.')] };
}
```

### src/lib/quality.ts:73

```typescript
export function saveInspection(i: QCInspection, draft: Pick<QCInspection, 'time' | 'responses' | 'metadata' | 'comments'>, user: User): QCInspection {
  ensure(canRecordQC(user.role) && (user.id === i.assignedTo || user.role === 'admin') && i.status === 'Draft', 'Only assigned QC staff/Admin can edit a draft. Submitted records are immutable.');
  return { ...i, ...structuredClone(draft), events: [...i.events, event(user, 'Draft saved', 'Measurements and findings saved in frontend state.')] };
}
```

### src/lib/quality.ts:77

```typescript
export function submitInspection(i: QCInspection, user: User): QCInspection {
  ensure(canRecordQC(user.role) && (i.assignedTo === user.id || user.role === 'admin') && i.status === 'Draft', 'Only assigned QC staff/Admin can submit a draft.');
  ensure(i.date <= new Date().toLocaleDateString('en-CA'), 'A scheduled future inspection cannot be submitted as completed.');
  ensure(/^([01]\d|2[0-3]):[0-5]\d$/.test(i.time), 'Record inspection time.');
  if (i.subject.kind === 'cleaning') ensure(['cleaningMethod', 'chemicals', 'cleanedBy'].every(k => i.metadata[k]?.trim()), 'Record cleaning method, chemicals/instruments and cleaned by.');
  if (i.subject.kind === 'raw') ensure(i.subject.batchNumber?.trim() && ['sampledQuantity', 'coa', 'tds', 'msds'].every(k => i.metadata[k]?.trim()) && Number.isFinite(Number(i.metadata.sampledQuantity)) && Number(i.metadata.sampledQuantity) > 0 && Number(i.metadata.sampledQuantity) <= i.subject.quantity!, 'Record supplier batch, document availability and valid sampled quantity in receipt units.');
  return { ...i, inspectorId: user.id, inspector: user.name, result: inspectionResult(i), status: 'Submitted', events: [...i.events, event(user, 'Submitted', 'Submitted; no stock or release authorization created.')] };
}
```

### src/lib/quality.ts:85

```typescript
export function reviewInspection(i: QCInspection, decision: QCApproval['decision'], remarks: string, user: User): QCInspection {
  role(user, QC_REVIEW_ROLES); ensure(i.status === 'Submitted' && remarks.trim(), 'Review a submitted inspection with remarks.');
  ensure(user.id !== i.inspectorId, 'A different authorized reviewer must verify the inspection.');
  ensure(decision !== 'Conditionally Accepted' || i.subject.kind === 'raw', 'Conditional acceptance applies to raw receipts only and remains held.');
  const result = inspectionResult(i); ensure(decision !== 'Passed' || result === 'Pass', 'Failed checks cannot be approved. Record corrective action and reinspection.');
  const approval: QCApproval = { id: crypto.randomUUID(), decision, remarks, userId: user.id, user: user.name, at: new Date().toISOString() };
  return { ...i, result, status: decision, approvals: [...i.approvals, approval], events: [...i.events, event(user, decision, remarks)] };
}
```

### src/lib/quality.ts:93

```typescript
export function subjectKey(s: QCSubject) { return s.kind === 'raw' ? `raw:${s.receiptId}` : s.kind === 'production' ? `production:${s.manufacturingItemId}:${s.batchId}:${s.stageId}` : s.kind === 'machine' ? `machine:${s.machineId}` : s.kind === 'cleaning' ? `cleaning:${s.areaId}` : `safety:${s.label}`; }
```

### src/lib/quality.ts:94

```typescript
export function qualityReleased(state: QCState, i: QCInspection) { return state.releases.some(r => r.inspectionId === i.id && r.purpose === 'quality'); }
```

### src/lib/quality.ts:95

```typescript
export function subjectHeld(state: QCState, subject: QCSubject): boolean {
  const records = state.inspections.filter(i => subjectKey(i.subject) === subjectKey(subject));
  // Every unresolved record keeps the subject held; unrelated items/batches are untouched.
  const resolved = (i: QCInspection, visited = new Set<string>()): boolean => { if (visited.has(i.id)) return false; visited.add(i.id); return qualityReleased(state, i) || records.some(n => n.previousInspectionId === i.id && resolved(n, new Set(visited))); };
  return records.some(i => !resolved(i)) || state.nonConformances.some(n => n.status !== 'Closed' && records.some(i => i.id === n.inspectionId));
}
```

### src/lib/quality.ts:101

```typescript
export function releaseInspection(state: QCState, id: string, purpose: QCRelease['purpose'], requestId: string, user: User, accepted?: number, rejected?: number): QCState {
  role(user, purpose === 'quality' ? QC_REVIEW_ROLES : ['production_manager', 'admin']);
  const existing = state.releases.find(r => r.requestId === requestId);
  if (existing) { ensure(existing.inspectionId === id && existing.purpose === purpose && existing.acceptedQuantity === accepted && existing.rejectedQuantity === rejected, 'Idempotency key conflicts with another release.'); return state; }
  const i = state.inspections.find(i => i.id === id); ensure(i && requestId, 'Inspection and release request ID are required.');
  ensure(i.status === 'Passed' || i.status === 'Approved/Released', 'Only an independently reviewed passing inspection can be released.');
  ensure(!state.nonConformances.some(n => n.status !== 'Closed' && state.inspections.some(source => source.id === n.inspectionId && subjectKey(source.subject) === subjectKey(i.subject))), 'Verify and close related non-conformances first.');
  ensure(!state.releases.some(r => r.inspectionId === id && r.purpose === purpose), 'This action already has a release reference.');
  if (purpose === 'finished_stock') {
    ensure(!state.releases.some(r => r.purpose === 'finished_stock' && subjectKey(r.subject) === subjectKey(i.subject)), 'This exact physical QC lot already has final stock authorization.');
    ensure(i.subject.kind === 'production' && i.subject.isFinishedOutput === true && qualityReleased(state, i) && !subjectHeld(state, i.subject), 'Quality release is required before final stock authorization.');
    ensure(finite(accepted) && accepted >= 0 && finite(rejected) && rejected >= 0 && accepted + rejected > 0 && accepted + rejected <= i.subject.quantity!, 'Accepted/rejected quantities must fit inspected output in its explicit unit.');
  }
  const release: QCRelease = { id: crypto.randomUUID(), requestId, inspectionId: id, subject: structuredClone(i.subject), purpose, acceptedQuantity: accepted, rejectedQuantity: rejected, unit: i.subject.unit, userId: user.id, user: user.name, at: new Date().toISOString() };
  return { ...state, releases: [...state.releases, release], inspections: state.inspections.map(row => row.id === id ? { ...row, status: 'Approved/Released', events: [...row.events, event(user, purpose === 'quality' ? 'Quality released' : 'Stock authorization', `Release ${release.id}; no inventory posting.`)] } : row) };
}
```

### src/lib/quality.ts:117

```typescript
export function reinspect(i: QCInspection, user: User): QCInspection {
  ensure(canRecordQC(user.role) && ['Failed', 'Reinspection Required', 'Conditionally Accepted'].includes(i.status), 'Create reinspection from a failed/reinspection record.');
  const next = createInspection(i.template, i.subject, user, new Date().toLocaleDateString('en-CA'), i.department, i.sampleCount);
  return { ...next, previousInspectionId: i.id, metadata: structuredClone(i.metadata) };
}
```

### src/lib/quality.ts:122

```typescript
export function createNonConformance(i: QCInspection, description: string, severity: QCNonConformance['severity'], user: User): QCNonConformance {
  ensure(canRecordQC(user.role) && description.trim() && i.status !== 'Draft', 'Record a finding against a submitted inspection.');
  const id = crypto.randomUUID(); return { id, number: `NC-${id.slice(0, 8)}`, inspectionId: i.id, description, severity, department: i.department, assignedTo: '', immediateAction: '', correctiveAction: '', dueDate: '', verification: '', status: 'Open', events: [event(user, 'Reported', description)] };
}
```

### src/lib/quality.ts:126

```typescript
export function updateNonConformance(n: QCNonConformance, change: Pick<QCNonConformance, 'assignedTo' | 'immediateAction' | 'correctiveAction' | 'dueDate' | 'verification' | 'status'>, user: User): QCNonConformance {
  role(user, QC_REVIEW_ROLES); ensure(n.status !== 'Closed', 'Closed findings are immutable.');
  const allowed: Record<QCNonConformance['status'], QCNonConformance['status'][]> = { Open: ['Assigned'], Assigned: ['In Progress'], 'In Progress': ['Awaiting Verification'], 'Awaiting Verification': ['Closed', 'In Progress'], Closed: [] };
  ensure(change.status === n.status || allowed[n.status].includes(change.status), 'Follow assignment, correction and verification before closure.');
  ensure(change.assignedTo.trim() && change.dueDate && Number.isFinite(Date.parse(change.dueDate)), 'Set assignment and due date.');
  if (['Awaiting Verification', 'Closed'].includes(change.status)) ensure(change.correctiveAction.trim(), 'Record corrective action.');
  if (change.status === 'Closed') ensure(change.verification.trim() && user.id !== change.assignedTo, 'Closure needs an independent verification outcome.');
  return { ...n, ...change, events: [...n.events, event(user, change.status, change.verification || change.correctiveAction || change.immediateAction || 'Assignment updated.')] };
}
```

### src/lib/quality.ts:136

```typescript
export function inspectionStatusLabel(i: QCInspection) {
  if (i.subject.kind === 'cleaning') return ({ Draft: 'Scheduled Cleaning', Submitted: 'Completed / Pending Verification', Passed: 'Review Passed / Pending Verification Release', Failed: 'Recleaning Required', 'Reinspection Required': 'Recleaning Required', 'Approved/Released': 'Verified', 'Conditionally Accepted': 'On Hold' })[i.status];
  if (i.subject.kind === 'raw') return ({ Draft: 'Pending Inspection', Submitted: 'Inspection In Progress / Awaiting Review', Passed: 'Passed / Awaiting Acceptance Release', Failed: 'Rejected / On Hold', 'Reinspection Required': 'Reinspection Required', 'Approved/Released': 'Accepted / Released', 'Conditionally Accepted': 'Conditionally Accepted / On Hold' })[i.status];
  return i.status;
}
```
### src/lib/qualityIntegration.ts:6

```typescript
export function rawQualityStatus(state: QCState, receiptId: string) {
  const records = state.inspections.filter(i => i.subject.kind === 'raw' && i.subject.receiptId === receiptId);
  if (!records.length) return 'Pending QC';
  if (records.at(-1)?.status === 'Conditionally Accepted') return 'Conditionally Accepted / On Hold';
  if (subjectHeld(state, records[0].subject)) return records.some(i => i.status === 'Failed') ? 'Rejected / On Hold' : 'Pending QC / On Hold';
  return records.some(i => qualityReleased(state, i)) ? 'Accepted / Released' : 'Pending QC';
}
```

### src/lib/qualityIntegration.ts:13

```typescript
export function rawHeldQuantity(state: QCState, movements: RawMaterialMovement[], materialId: string) {
  return movements.filter(m => m.materialId === materialId && m.movementType === 'IN' && rawQualityStatus(state, m.id) !== 'Accepted / Released').reduce((sum, m) => sum + m.quantity, 0);
}
```

### src/lib/qualityIntegration.ts:16

```typescript
export function assertProductionQC(state: QCState, card: JobCard, beforeSequence = Infinity) {
  const records = state.inspections.filter(i => i.subject.manufacturingItemId === card.id);
  if (records.some(i => subjectHeld(state, i.subject))) throw new Error('This manufacturing item has an unresolved QC hold. Unrelated items remain available.');
  const stages = card.routingApproved?.stages ?? card.productionStages ?? [];
  for (const stage of stages.filter(s => s.required && s.kind === 'production' && s.sequence < beforeSequence)) {
    for (const templateId of stage.qcTemplateIds ?? []) {
      const actual = card.productionStages?.find(s => s.id === stage.id);
      const batches = new Map<string, number>();
      records.filter(i => i.template.id === templateId && i.subject.stageId === stage.id && i.subject.unit === actual?.outputUnit && qualityReleased(state, i) && !subjectHeld(state, i.subject)).forEach(i => batches.set(i.subject.batchId!, i.subject.quantity ?? 0));
      if (!actual || actual.status !== 'Completed' || !batches.size || [...batches.values()].reduce((a, b) => a + b, 0) < (actual.outputQuantity ?? Infinity)) throw new Error(`Mandatory QC for ${stage.name} must cover its recorded output before advancement/release.`);
    }
  }
}
```

### src/lib/qualityIntegration.ts:29

```typescript
export function finishedAuthorization(state: QCState, card: JobCard, batch: string, accepted: number, rejected: number): QCRelease {
  assertProductionQC(state, card);
  const last = [...(card.productionStages ?? [])].filter(s => s.required && s.kind === 'production').sort((a, b) => a.sequence - b.sequence).at(-1);
  const release = state.releases.find(r => r.purpose === 'finished_stock' && r.subject.manufacturingItemId === card.id && r.subject.stageId === last?.id && r.subject.batchNumber === batch);
  if (!release || subjectHeld(state, release.subject) || release.unit !== last?.outputUnit) throw new Error('This exact finished batch needs QC release and separate Production Manager/Admin stock authorization.');
  const posted = (card.stockTransfers ?? []).filter(r => r.batch === batch);
  if (posted.reduce((sum, r) => sum + r.quantity, 0) + accepted > (release.acceptedQuantity ?? 0) || posted.reduce((sum, r) => sum + r.rejectedQuantity, 0) + rejected > (release.rejectedQuantity ?? 0)) throw new Error('Stock receipt exceeds the authorized accepted/rejected quantities for this batch.');
  return release;
}
```

### src/lib/qualityIntegration.ts:39

```typescript
export function assertMachineQC(state: QCState, machineId?: string) {
  if (!machineId) return;
  const records = state.inspections.filter(i => i.subject.kind === 'machine' && i.subject.machineId === machineId);
  const latest = records.at(-1);
  if (!latest || subjectHeld(state, latest.subject) || !records.some(i => qualityReleased(state, i))) throw new Error('Assigned machine requires a verified QC record and resolution of equipment warnings.');
}
```

### src/lib/qualityIntegration.ts:46

```typescript
export function assertFinishedReceiptQC(state: QCState, movement: FinishedGoodsMovement, movements: FinishedGoodsMovement[]) {
  const authorization = state.releases.find(r => r.id === movement.stockApprovalId && r.purpose === 'finished_stock');
  const qualityRelease = state.releases.find(r => r.id === movement.qualityReleaseId && r.purpose === 'quality');
  if (!authorization || !qualityRelease || qualityRelease.inspectionId !== authorization.inspectionId || authorization.subject.manufacturingItemId !== movement.manufacturingItemId || authorization.subject.jobCardId !== movement.jobCardId || authorization.subject.batchNumber !== movement.batch || authorization.unit !== movement.unit || subjectHeld(state, authorization.subject) || (authorization.subject.productId && authorization.subject.productId !== movement.productId)) throw new Error('Production receipt requires exact QC and final stock authorization references.');
  if (movement.date < new Date(authorization.at).toLocaleDateString('en-CA')) throw new Error('Stock receipt cannot precede final managerial authorization.');
  const received = movements.filter(m => m.stockApprovalId === authorization.id && m.type === 'IN').reduce((sum, m) => sum + m.quantity, 0);
  if (received + movement.quantity > (authorization.acceptedQuantity ?? 0)) throw new Error('Receipt exceeds this batch stock authorization.');
}
```

### src/lib/qualityIntegration.ts:55

```typescript
export function assertManualFinishedINQC(state: QCState, userRole: Role | undefined, productId: string) {
  if (userRole !== 'admin') throw new Error('Production Stock IN must use a QC-authorized Job Card receipt. Admin alone can record a separate legacy reference import.');
  if (state.inspections.some(i => i.subject.productId === productId && subjectHeld(state, i.subject))) throw new Error('Manual unbatched Stock IN cannot bypass this product QC hold. Use an exact authorized batch receipt.');
}
```
### src/lib/qualitySchedule.ts:5

```typescript
export function validateSchedule(s:QCSchedule,t:QCTemplate){
 if(!s.id||!s.assignedTo.trim()||!s.department.trim()||!validDate(s.startDate)||(s.endDate&&(!validDate(s.endDate)||s.endDate<s.startDate))||!t.active||s.templateId!==t.id||s.subject.kind!==t.category||s.frequency!==t.frequency)throw new Error('Use an active template, exact subject, assignment, matching configured frequency and valid date range.');
 if(['raw','production'].includes(s.subject.kind)&&!['per_receipt','per_batch','on_demand','per_activity'].includes(s.frequency))throw new Error('Receipt/batch inspections need a new exact source; do not recur a consumed physical lot.');
 if(s.frequency==='per_shift'&&!s.shift?.trim())throw new Error('Per-shift schedules require an explicit shift identifier.');
}
```

### src/lib/qualitySchedule.ts:10

```typescript
export function scheduleDue(s:QCSchedule,date:string){if(!s.active||!validDate(date)||date<s.startDate||(s.endDate&&date>s.endDate))return false;const days=(Date.parse(date)-Date.parse(s.startDate))/86400000;return s.frequency==='daily'||s.frequency==='per_shift'||s.frequency==='weekly'&&days%7===0||s.frequency==='monthly'&&date.slice(8)===s.startDate.slice(8)||['per_receipt','per_batch','on_demand','per_activity'].includes(s.frequency)&&date===s.startDate;}
```

### src/lib/qualitySchedule.ts:11

```typescript
export function generateScheduled(s:QCSchedule,t:QCTemplate,date:string,all:QCInspection[],user:User):QCInspection|undefined{
 validateSchedule(s,t);if(!scheduleDue(s,date))return;const key=`${s.id}:${date}:${s.shift??''}`;if(all.some(i=>i.scheduleKey===key || i.date===date && i.template.id===t.id && subjectKey(i.subject)===subjectKey(s.subject) && (i.metadata.shift??'')===(s.shift??'')))return;
 const i=createInspection(t,s.subject,user,date,s.department);return {...i,scheduleKey:key,assignedTo:s.assignedTo,metadata:{...i.metadata,scheduleId:s.id,shift:s.shift??''}};
}
```
### src/lib/quotations.ts:20

```typescript
export const blankCustomer = (): QuotationCustomer => ({ name: '', billingAddress: '', deliveryAddress: '', contactPerson: '', telephone: '', email: '', customerType: 'B2B', tin: '' });
```

### src/lib/quotations.ts:21

```typescript
export const blankQuotationLine = (): QuotationLine => ({ id: crypto.randomUUID(), type: 'stock', description: '', group: '', specifications: '', quantity: 1, unit: '', unitPrice: 0 });
```

### src/lib/quotations.ts:22

```typescript
export function validCommercialDate(date: string) { return /^\d{4}-\d{2}-\d{2}$/.test(date) && Number.isFinite(Date.parse(date)) && new Date(`${date}T00:00:00Z`).toISOString().slice(0, 10) === date; }
```

### src/lib/quotations.ts:23

```typescript
export function addDays(date: string, days: number) { if (!validCommercialDate(date) || !Number.isInteger(days) || days < 0 || days > 3650) throw new Error('Use a valid date and 0–3650 days.'); const d = new Date(`${date}T00:00:00Z`); d.setUTCDate(d.getUTCDate() + days); return d.toISOString().slice(0, 10); }
```

### src/lib/quotations.ts:24

```typescript
export const quotationTotals = (q: Quotation) => {
 q.lines.forEach(l=>{if(l.led?.applies){if(!l.ledSnapshot)throw new Error('LED MAX requires valid weight, FX and an explicitly applied snapshot; percentage fallback is forbidden.');if(l.type==='stock'){if(l.led.conversion?.productId!==l.productId||l.led.conversion?.modelId!==l.modelId||l.led.conversion?.originalQuantity!==l.quantity||l.led.conversion?.originalUnit!==l.unit)throw new Error('LED weight source changed. Refresh the product/model conversion snapshot.');const net=l.quantity*l.unitPrice/(q.taxMode==='inclusive'?1+q.taxRate/100:1);const expected=calculateConfiguredLED(l.led,net,undefined,q.currency);if(JSON.stringify(expected)!==JSON.stringify(l.ledSnapshot))throw new Error('LED source/price changed. Refresh and apply the LED snapshot.');}}});
 return calculateCommercialTotals(q.lines,q.discount,q.taxRate,q.taxMode);
};
```

### src/lib/quotations.ts:28

```typescript
export function effectiveQuotationStatus(q: Quotation, date = today()): QuotationStatus { return ['Approved', 'Sent', 'Accepted'].includes(q.status) && q.validUntil < date ? 'Expired' : q.status; }
```

### src/lib/quotations.ts:29

```typescript
export function quotationEvent(user: User, type: string, description: string): QuotationEvent { return { id: crypto.randomUUID(), at: new Date().toISOString(), user: user.name, userId: user.id, type, description }; }
```

### src/lib/quotations.ts:30

```typescript
export function createQuotation(company: CompanySettings, all: Quotation[], user: User): Quotation {
  if (!QUOTATION_EDIT_ROLES.includes(user.role)) throw new Error('Your role cannot create quotations.');
  const id = crypto.randomUUID(); const date = today();
  return { id, rootId: id, number: `QT-${Math.max(0, ...all.map(q => Number(q.number.replace('QT-', '')) || 0)) + 1}`, revision: 1, documentType: 'Sales Quotation', date, validityDays: company.validityDays, validUntil: addDays(date, company.validityDays), currency: company.currency, taxRate: company.taxRate, taxMode: company.taxMode, discount: 0, customer: blankCustomer(), company: structuredClone(company), terms: { ...EMPTY_TERMS }, salesRepresentative: '', lines: [], status: 'Draft', createdBy: user.name, createdById: user.id, responses: [], events: [quotationEvent(user, 'Created', 'Commercial draft; no order, production or stock transaction.')] };
}
```

### src/lib/quotations.ts:35

```typescript
export function validateQuotation(q: Quotation, complete = true) {
  if (!q.number.trim() || !validCommercialDate(q.date) || q.validUntil !== addDays(q.date, q.validityDays) || !q.currency.trim() || !['Sales Quotation', 'Proforma Invoice'].includes(q.documentType)) throw new Error('Complete document identity, dates, currency and type.');
  if (q.deliveryDays !== undefined && (!Number.isInteger(q.deliveryDays) || q.deliveryDays < 0)) throw new Error('Delivery lead time must be a nonnegative whole number.');
  for (const n of [q.terms.advancePercent, q.terms.quantityTolerance]) if (n !== undefined && (!Number.isFinite(n) || n < 0 || n > 100)) throw new Error('Commercial percentages must be 0–100.');
  if (q.terms.creditDays !== undefined && (!Number.isInteger(q.terms.creditDays) || q.terms.creditDays < 0)) throw new Error('Credit days must be nonnegative.');
  if (new Set(q.lines.map(l => l.id)).size !== q.lines.length) throw new Error('Quotation line IDs must be distinct.');
  if (complete && ((!q.customer.customerId && !q.customer.prospectId) || !q.customer.name.trim() || !['B2B', 'B2C'].includes(q.customer.customerType) || !q.salesRepresentative.trim() || !q.lines.length)) throw new Error('Complete customer, sales representative and at least one line.');
  if (q.lines.some(l => !l.description.trim() || !l.unit.trim() || (l.type === 'stock' ? !l.productId : !l.modelId || !l.modelRevision))) throw new Error('Choose exact products/models, descriptions and units for each line.');
  quotationTotals(q);
}
```

### src/lib/quotations.ts:45

```typescript
export function matchesQuotationCost(e: CostEstimate, q: Quotation, line: QuotationLine) { return e.input.quotationId === q.rootId && e.input.itemId === line.id && e.input.customer === q.customer.name && e.input.quantity === line.quantity && e.input.unit === line.unit && e.input.modelId === line.modelId && e.input.modelRevision === line.modelRevision && e.input.specifications === line.specifications; }
```

### src/lib/quotations.ts:46

```typescript
export function quotedCostPrice(e: CostEstimate, q: Pick<Quotation, 'currency' | 'taxMode' | 'taxRate'>) {
  const publicPrice = customerEstimate(e);
  if (e.status !== 'Approved' || publicPrice.currency !== q.currency) throw new Error('Select approved costing in this document currency; no implicit exchange conversion.');
  const net = (publicPrice.subtotal + publicPrice.charges) / publicPrice.quantity;
  return q.taxMode === 'inclusive' ? net * (1 + q.taxRate / 100) : net;
}
```

### src/lib/quotations.ts:52

```typescript
export function validateQuotationSources(q: Quotation, estimates: CostEstimate[], versions: Model[]) {
  q.lines.filter(l => l.type === 'custom').forEach(line => {
    const e = estimates.find(e => e.id === line.estimateId);
    const latest = Math.max(...versions.filter(m => m.id === line.modelId).map(m => m.revision ?? 1));
    if (!e || e.revision !== line.estimateRevision || !matchesQuotationCost(e, q, line) || latest !== line.modelRevision || Math.abs(quotedCostPrice(e, q) - line.unitPrice) > 1e-9 || JSON.stringify(e.totals.led)!==JSON.stringify(line.ledSnapshot)) throw new Error('Custom model/costing/quantity/price changed or is not approved. Revise/review this quotation and explicitly apply the approved price.');
  });
}
```

### src/lib/quotations.ts:59

```typescript
export function submitQuotation(q: Quotation, estimates: CostEstimate[], models: Model[], user: User, date = today()): Quotation {
  if (!QUOTATION_EDIT_ROLES.includes(user.role) || q.status !== 'Draft' || q.validUntil < date) throw new Error('Submit only a current draft with an authorized sales role.');
  validateQuotation(q); validateQuotationSources(q, estimates, models);
  return { ...q, status: 'Pending Internal Approval', events: [...q.events, quotationEvent(user, 'Submitted', 'Internal price/tax/terms review requested.')] };
}
```

### src/lib/quotations.ts:64

```typescript
export function approveQuotation(q: Quotation, estimates: CostEstimate[], models: Model[], user: User, date = today()): Quotation {
  if (!QUOTATION_APPROVE_ROLES.includes(user.role) || q.status !== 'Pending Internal Approval' || q.validUntil < date) throw new Error('Authorized Accounts/Manager/Admin approves current submitted revisions.');
  validateQuotation(q); validateQuotationSources(q, estimates, models);
  return { ...q, status: 'Approved', approval: { id: crypto.randomUUID(), user: user.name, userId: user.id, at: new Date().toISOString(), totals: quotationTotals(q), roundingPolicy: COMMERCIAL_ROUNDING }, events: [...q.events, quotationEvent(user, 'Internally approved', 'Commercial snapshots frozen; customer has not accepted.')] };
}
```

### src/lib/quotations.ts:69

```typescript
export function sendQuotation(q: Quotation, estimates: CostEstimate[], models: Model[], user: User, date = today()): Quotation {
  if (!QUOTATION_EDIT_ROLES.includes(user.role) || effectiveQuotationStatus(q, date) !== 'Approved') throw new Error('Mark only current internally approved revisions as sent.');
  validateQuotationSources(q, estimates, models);
  return { ...q, status: 'Sent', events: [...q.events, quotationEvent(user, 'Marked sent', 'Recorded customer delivery; no automatic acceptance or email transmission.')] };
}
```

### src/lib/quotations.ts:74

```typescript
export function recordQuotationResponse(q: Quotation, response: Omit<QuotationResponse, 'id' | 'revision'>, user: User, date = today()): Quotation {
  const sentDate = q.events.find(e => e.type === 'Marked sent')?.at.slice(0, 10) ?? q.date;
  if (!QUOTATION_EDIT_ROLES.includes(user.role) || q.status !== 'Sent' || !['Accepted', 'Rejected', 'Revision Requested', 'Pending'].includes(response.response) || !validCommercialDate(response.date) || response.date > date || response.date < sentDate || !response.respondedBy.trim() || !response.remarks.trim()) throw new Error('Record a response to a sent revision with valid date, respondent and remarks.');
  if (response.response === 'Accepted' && response.date > q.validUntil) throw new Error('Acceptance after expiry requires a new approved revision.');
  const r = { ...response, id: crypto.randomUUID(), revision: q.revision };
  return { ...q, responses: [...q.responses, r], status: r.response === 'Accepted' ? 'Accepted' : r.response === 'Rejected' ? 'Rejected' : r.response === 'Revision Requested' ? 'Revision Requested' : 'Sent', events: [...q.events, quotationEvent(user, `Customer ${r.response}`, `${r.respondedBy}, ${r.date}; ${r.remarks}; reference ${r.reference || 'not supplied'}.`)] };
}
```

### src/lib/quotations.ts:81

```typescript
export function publicQuotation(q: Quotation) {
  return { number: q.number, revision: q.revision, documentType: q.documentType, date: q.date, validityDays: q.validityDays, validUntil: q.validUntil, deliveryDays: q.deliveryDays, currency: q.currency, taxRate: q.taxRate, taxMode: q.taxMode, status: effectiveQuotationStatus(q), salesRepresentative: q.salesRepresentative,
    company: { tradingName: q.company.tradingName, legalName: q.company.legalName, logo: q.company.logo, address: q.company.address, telephone: q.company.telephone, email: q.company.email, tin: q.company.tin, signatory: q.company.signatory, banks: structuredClone(q.company.banks) },
    customer: { name: q.customer.name, billingAddress: q.customer.billingAddress, deliveryAddress: q.customer.deliveryAddress, contactPerson: q.customer.contactPerson, telephone: q.customer.telephone, email: q.customer.email, customerType: q.customer.customerType, tin: q.customer.tin },
    lines: q.lines.map(l => ({ description: l.description, group: l.group, specifications: l.specifications, quantity: l.quantity, unit: l.unit, unitPrice: l.unitPrice, led: l.ledSnapshot ? {method:l.ledSnapshot.method,selectedAmount:l.ledSnapshot.selectedAmount,vatOnLED:l.ledSnapshot.vatOnLED} : undefined })), terms: structuredClone(q.terms), totals: structuredClone(q.approval?.totals ?? quotationTotals(q)) };
}
```

### src/lib/quotations.ts:87

```typescript
export function reviseQuotation(q: Quotation, all: Quotation[], company: CompanySettings, user: User, duplicate = false): Quotation {
  if (!QUOTATION_EDIT_ROLES.includes(user.role) || (!duplicate && ['Converted to Sales Order', 'Superseded'].includes(q.status))) throw new Error('Revise the current unconverted quotation, or duplicate into a new offer.');
  const fresh = createQuotation(company, all, user);
  return { ...fresh, generationKey: duplicate ? undefined : q.generationKey, rootId: duplicate ? fresh.rootId : q.rootId, number: duplicate ? fresh.number : q.number, revision: duplicate ? 1 : Math.max(...all.filter(n => n.rootId === q.rootId).map(n => n.revision)) + 1, previousId: duplicate ? undefined : q.id, documentType: q.documentType, validityDays: q.validityDays, validUntil: addDays(fresh.date, q.validityDays), deliveryDays: q.deliveryDays, currency: q.currency, taxRate: q.taxRate, taxMode: q.taxMode, discount: q.discount, customer: structuredClone(q.customer), terms: structuredClone(q.terms), salesRepresentative: q.salesRepresentative, lines: structuredClone(q.lines).map(l => duplicate ? { ...l, id: crypto.randomUUID(), led:undefined,ledSnapshot:undefined, estimateId: undefined, estimateRevision: undefined, unitPrice: l.type === 'custom' ? 0 : l.unitPrice } : l), events: [quotationEvent(user, duplicate ? 'Duplicated' : 'Revision created', `From ${q.number} revision ${q.revision}; prior commercial content retained.`)] };
}
```

### src/lib/quotations.ts:92

```typescript
export function quotationConversionDraft(q: Quotation, customerId: string, requiredDate: string, orders: SalesOrder[], estimates: CostEstimate[], models: Model[], date = today()): SalesOrderDraft {
  if (orders.some(o => o.quotationId === q.rootId)) throw new Error('This quotation already has a Sales Order.');
  if (effectiveQuotationStatus(q, date) !== 'Accepted' || !q.approval || !q.responses.some(r => r.response === 'Accepted' && r.revision === q.revision)) throw new Error('Convert only the current, internally approved, accepted and unexpired revision.');
  validateQuotation(q); validateQuotationSources(q, estimates, models);
  if (!customerId) throw new Error('Explicitly select/link the customer master; conversion never creates a customer automatically.');
  if (q.lines.some(l => l.type === 'custom') && (!validCommercialDate(requiredDate) || requiredDate < date)) throw new Error('Confirm a manufacturing delivery date on or after the order date.');
  return { quotationId: q.rootId, quotationRevisionId: q.id, quotationNumber: q.number, quotationRevision: q.revision, prospectId: q.customer.prospectId, customerId, customerName: q.customer.name, date, marketingPersonName: q.salesRepresentative, customerType: q.customer.customerType, requisitionOrder: '', customerContact: structuredClone(q.customer), commercialTerms: structuredClone(q.terms), commercialPricing: { taxMode: q.taxMode, discount: q.discount, roundingPolicy: q.approval.roundingPolicy }, taxRate: q.taxRate, currency: q.currency, items: q.lines.map(l => ({ id: crypto.randomUUID(), quotationLineId: l.id, ledSnapshot:l.ledSnapshot?structuredClone(l.ledSnapshot):undefined, itemId: l.productId, modelId: l.modelId, modelRevision: l.modelRevision, estimateId: l.estimateId, quotationCostEstimateId: l.estimateId, quotationCostEstimateRevision: l.estimateRevision, fulfillmentSource: l.type === 'custom' ? 'manufacturing' : 'stock', itemName: l.description, specifications: l.specifications, quantity: l.quantity, unit: l.unit, unitPrice: l.unitPrice, totalPrice: l.quantity * l.unitPrice, requiredDate: l.type === 'custom' ? requiredDate : undefined })) };
}
```
### src/lib/rawMaterialData.ts:46

```typescript
const round = (n: number) => Math.round(n * 1e6) / 1e6;
```

### src/lib/rawMaterialData.ts:49

```typescript
export function rawMaterialBalance(material: RawMaterial, movements: RawMaterialMovement[], month?: string) {
  const ledger = movements.filter(m => m.materialId === material.id);
  const applicable = month ? ledger.filter(m => m.date.startsWith(month)) : ledger;
  const stockIn = round(applicable.filter(m => m.movementType === 'IN').reduce((sum, m) => sum + m.quantity, 0));
  const stockOut = round(applicable.filter(m => m.movementType === 'OUT').reduce((sum, m) => sum + m.quantity, 0));
  if (material.openingStock === null || (month && `${month}-01` < material.openingDate)) {
    return { openingStock: null, stockIn, stockOut, currentStock: null };
  }
  const openingStock = round(material.openingStock + (month ? ledger.filter(m => m.date < `${month}-01`)
    .reduce((sum, m) => sum + (m.movementType === 'IN' ? m.quantity : -m.quantity), 0) : 0));
  return { openingStock, stockIn, stockOut, currentStock: round(openingStock + stockIn - stockOut) };
}
```
### src/lib/salesJob.ts:7

```typescript
export function buildLinkedJob(order: SalesOrder, item: SalesOrderItem, model: Model, requiredDate: string, specifications: string, materials: NonNullable<JobCard['requiredMaterials']>, user: User, cards: JobCard[], estimate?: CostEstimate) {
  if (estimate && (!estimateMatchesOrder(estimate, order.id, item.id) || estimate.input.modelId !== model.id || estimate.input.modelRevision !== (model.revision ?? 1) || ['Superseded', 'Revision Required'].includes(estimate.status))) throw new Error('Use a current costing revision for this order line and model.');
  if (estimate) materials = materialRequirements(estimate.input);
  if (item.fulfillmentSource !== 'manufacturing' || !order.items?.some(i => i.id === item.id)) throw new Error('Select a manufacturing line from this order.');
  if (new Set(materials.map(m => m.materialId)).size !== materials.length || materials.some(m => !RAW_MATERIALS.some(raw => raw.id === m.materialId && raw.unit === m.unit))) throw new Error('Use distinct raw materials with their configured units.');
    if (!/^\d{4}-\d{2}-\d{2}$/.test(requiredDate) || !Number.isFinite(Date.parse(requiredDate)) || requiredDate < order.date || !materials.length || materials.some(m => !m.materialId || !Number.isFinite(m.requiredQuantity) || m.requiredQuantity <= 0)) throw new Error('Complete delivery date and editable material requirements. Model quantities are not configured.');
    const id = crypto.randomUUID();
    const card = normalizeJobCard({ id, jobCardNumber: `JC-${Math.max(0, ...cards.map(c => Number(c.jobCardNumber.replace('JC-', '')) || 0)) + 1}`, salesOrderId: order.id, salesOrderItemId: item.id, finishedProductId: item.itemId, salesOrderNumber: order.orderNumber, customerName: order.customerName, product: item.itemName, modelId: model.id, modelRevision: model.revision ?? 1, estimateId: estimate?.id, estimateRevision: estimate?.revision, routingRevision: 1, modelName: model.name, qty: item.quantity, unit: item.unit, createdDate: today(), requiredDate, specifications, productionRequirements: estimate ? `Estimate ${estimate.number} revision ${estimate.revision}: explicit recipe quantities and configured units. PM review required.` : `Editable draft: ${model.billOfMaterials}. Material quantities entered manually; no configured formula.`, requiredMaterials: materials, status: estimate ? 'Draft' : 'PendingApproval', department: 'Production Manager', stages: model.stages.map((stage, i) => ({ stage, sequenceOrder: i + 1, required: true, status: 'Pending' })), activityHistory: [{ id: crypto.randomUUID(), timestamp: new Date().toISOString(), action: 'Job card created', user: user.name, department: 'Production Manager', description: `Linked to ${order.orderNumber}, item ${item.id}. Draft requirements require PM review.` }] }, [order]);
    if (model.routing?.length) card.productionStages = structuredClone(model.routing).map((s, i) => ({ ...s, sequence: i + 1, status: 'Pending', inputQuantity: null, outputQuantity: null, wasteQuantity: null, operator: '', remarks: '', handover: undefined, startedAt: undefined, completedAt: undefined }));
    else card.productionStages = card.productionStages?.map(stage => ({ ...stage, inputUnit: item.unit, outputUnit: item.unit, wasteUnit: item.unit }));
  return card;
}
```
### src/lib/salesOrders.ts:16

```typescript
export const today = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};
```

### src/lib/salesOrders.ts:20

```typescript
export const lineTotal = (quantity: number, price: number) => Math.round(quantity * price * 100) / 100;
```

### src/lib/salesOrders.ts:21

```typescript
export const orderTotal = (items: SalesOrderItem[]) => Math.round(items.reduce((sum, item) => sum + lineTotal(item.quantity, item.unitPrice), 0) * 100) / 100;
```

### src/lib/salesOrders.ts:22

```typescript
export function validateOrder(draft: SalesOrderDraft) {
  const errors: Record<string, string> = {};
  if (!draft.customerName.trim()) errors.customerName = 'Customer name is required.';
  if (!draft.marketingPersonName.trim()) errors.marketingPersonName = 'Marketing person is required.';
  if (!['B2B', 'B2C'].includes(draft.customerType)) errors.customerType = 'Select B2B or B2C.';
  if (!draft.date || !Number.isFinite(Date.parse(draft.date))) errors.date = 'A valid order date is required.';
  if (draft.taxRate !== undefined && (!Number.isFinite(draft.taxRate) || draft.taxRate < 0 || draft.taxRate > 100)) errors.taxRate = 'Tax rate must be between 0 and 100.';
  if (!draft.items.length) errors.items = 'Add at least one item.';
  if (!draft.currency?.trim()) errors.currency = 'Enter the transaction currency.';
  if (draft.taxRate === undefined) errors.taxRate = 'Confirm the transaction tax rate (0 for no tax).';
  draft.items.forEach((item, i) => {
    if (!['stock', 'manufacturing'].includes(item.fulfillmentSource ?? '')) errors[`${i}.source`] = 'Select a fulfillment source.';
    if ((!item.itemId && !(item.fulfillmentSource === 'manufacturing' && item.modelId)) || !item.itemName.trim()) errors[`${i}.item`] = 'Select an item.';
    if (item.modelId && (!item.requiredDate || !Number.isFinite(Date.parse(item.requiredDate)) || item.requiredDate < draft.date)) errors[`${i}.item`] = 'Enter a required delivery date on or after the order date.';
    if(item.led?.applies){try{const expected=calculateConfiguredLED(item.led,item.quantity*item.unitPrice,undefined,draft.currency??'');if(JSON.stringify(expected)!==JSON.stringify(item.ledSnapshot)||item.ledSnapshot?.conversion?.originalQuantity!==item.quantity||item.ledSnapshot?.conversion?.originalUnit!==item.unit||item.ledSnapshot?.conversion?.productId!==(item.itemId??''))throw new Error();}catch{errors[`${i}.led`]='LED MAX needs valid weight/conversion, FX and a refreshed snapshot.';}}
    if (!Number.isFinite(item.quantity) || item.quantity <= 0) errors[`${i}.quantity`] = 'Quantity must be greater than 0.';
    if (!item.unit.trim()) errors[`${i}.unit`] = 'Select a unit.';
    if (!Number.isFinite(item.unitPrice) || item.unitPrice < 0) errors[`${i}.price`] = 'Price must be 0 or greater.';
    if (Number.isFinite(item.quantity) && Number.isFinite(item.unitPrice) && !Number.isFinite(lineTotal(item.quantity, item.unitPrice))) errors[`${i}.price`] = 'The line total is too large.';
  });
  if (draft.commercialPricing) { try { calculateCommercialTotals(draft.items, draft.commercialPricing.discount, draft.taxRate ?? 0, draft.commercialPricing.taxMode); } catch { errors.items = 'Invalid commercial tax/discount snapshot.'; } }
  if (draft.items.every(item => Number.isFinite(item.quantity) && Number.isFinite(item.unitPrice)) && !Number.isFinite(orderTotal(draft.items))) errors.items = 'The order total is too large.';
  return errors;
}
```

### src/lib/salesOrders.ts:46

```typescript
export const nextOrderNumber = (existing: SalesOrder[]) => `SO-${Math.max(0, ...existing.map(order => Number(order.orderNumber.replace(/^SO-/, '')) || 0)) + 1}`;
```

### src/lib/salesOrders.ts:47

```typescript
export const orderSummary = (items: SalesOrderItem[]) => { const subtotal = orderTotal(items.filter(item => Number.isFinite(item.quantity) && Number.isFinite(item.unitPrice))); return { subtotal, total: subtotal }; };
```

### src/lib/salesOrders.ts:49

```typescript
export function buildSalesOrder(draft: SalesOrderDraft, existing: SalesOrder[]): SalesOrder {
  if (Object.keys(validateOrder(draft)).length) throw new Error('Please correct the highlighted fields.');
  return {
    ...draft, id: `so-${crypto.randomUUID()}`, orderNumber: nextOrderNumber(existing),
    customerName: draft.customerName.trim(), marketingPersonName: draft.marketingPersonName.trim(),
    requisitionOrder: draft.requisitionOrder.trim(), customerType: draft.customerType as CustomerType,
    items: draft.items.map(item => ({ ...item, totalPrice: lineTotal(item.quantity, item.unitPrice) })),
    commercialPricing:draft.commercialPricing??(draft.items.some(i=>i.ledSnapshot)?{taxMode:'exclusive',discount:0,roundingPolicy:'LED and VAT rounded to 2 decimals; frozen per-line MAX snapshots.'}:undefined),
    orderTotal: draft.commercialPricing ? calculateCommercialTotals(draft.items, draft.commercialPricing.discount, draft.taxRate ?? 0, draft.commercialPricing.taxMode).total : draft.items.some(i=>i.ledSnapshot)?calculateCommercialTotals(draft.items,0,draft.taxRate??0,'exclusive').total:lineTotal(orderTotal(draft.items), 1 + (draft.taxRate ?? 0) / 100), status: 'Draft', jobCardIds: [],
  };
}
```
### src/lib/stockIntelligence.ts:7

```typescript
export const isKG = (u: string) => ['kg', 'kgs', 'kilo', 'kilos', 'kilogram', 'kilograms'].includes(u.toLowerCase());
```

### src/lib/stockIntelligence.ts:8

```typescript
export const isCTR = (u: string) => ['ctr', 'ctrs', 'ctn', 'ctns', 'carton', 'cartons'].includes(u.toLowerCase());
```

### src/lib/stockIntelligence.ts:9

```typescript
export function validateConversion(c: ProductConversion) {
  if (!c.productId || !isCTR(c.unit) || !(c.kgPerCTR > 0) || !Number.isFinite(c.kgPerCTR) || !Number.isInteger(c.version) || c.version < 1 || !validDate(c.effectiveDate) || (c.piecesPerCTR !== undefined && (!Number.isInteger(c.piecesPerCTR) || c.piecesPerCTR <= 0))) throw new Error('Use an exact CTR product, positive KG/CTR, version and effective date.');
}
```

### src/lib/stockIntelligence.ts:12

```typescript
export function quantitySnapshot(productId: string, quantity: number, unit: string, date: string, rules: ProductConversion[], modelId?: string): QuantitySnapshot {
  if (!Number.isFinite(quantity) || quantity < 0) throw new Error('Quantity must be finite and nonnegative.');
  const c = rules.filter(r => r.productId === productId && r.unit === unit && r.modelId === modelId && r.effectiveDate <= date).sort((a,b) => b.effectiveDate.localeCompare(a.effectiveDate) || b.version-a.version)[0];
  if (c) validateConversion(c);
  const convertedKG = isKG(unit) ? quantity : isCTR(unit) && c ? quantity * c.kgPerCTR : null;
  if (convertedKG !== null && !Number.isFinite(convertedKG)) throw new Error('Converted quantity exceeds supported range.');
  return { productId, modelId, originalQuantity: quantity, originalUnit: unit, convertedKG, ...(c ? { conversionId: c.id, conversionVersion: c.version } : {}) };
}
```

### src/lib/stockIntelligence.ts:20

```typescript
export function convertedPrices(price: number, unit: string, kgPerCTR?: number) {
  if (!Number.isFinite(price) || price < 0 || (kgPerCTR !== undefined && (!Number.isFinite(kgPerCTR) || kgPerCTR <= 0))) throw new Error('Use a valid price and positive product conversion.');
  return { perKG: isKG(unit) ? price : isCTR(unit) && kgPerCTR ? price / kgPerCTR : null, perCTR: isCTR(unit) ? price : isKG(unit) && kgPerCTR ? price * kgPerCTR : null };
}
```

### src/lib/stockIntelligence.ts:24

```typescript
export function snapshotMovements(previous:FinishedGoodsMovement[],next:FinishedGoodsMovement[],rules:ProductConversion[]):FinishedGoodsMovement[]{
  const existing=new Set(previous.map(m=>m.id));
  return next.map(m=>{
    if(existing.has(m.id))return m;
    const original=m.reversalOf?previous.find(row=>row.id===m.reversalOf):undefined;
    const snapshot=original?original.quantitySnapshot?structuredClone(original.quantitySnapshot):{productId:m.productId,modelId:original.modelId,originalQuantity:m.quantity,originalUnit:m.unit,convertedKG:null}:quantitySnapshot(m.productId,m.quantity,m.unit,m.date,rules,m.modelId);
    return {...m,quantitySnapshot:snapshot};
  });
}
```

### src/lib/stockIntelligence.ts:33

```typescript
export const validDate = (d: string) => /^\d{4}-\d{2}-\d{2}$/.test(d) && Number.isFinite(Date.parse(d)) && new Date(d+'T00:00:00Z').toISOString().slice(0,10) === d;
```

### src/lib/stockIntelligence.ts:35

```typescript
export function validateThreshold(t: StockThreshold) {
  if (![t.minimum,t.critical,t.reorder,t.target].every(n => Number.isFinite(n) && n >= 0) || t.critical > t.minimum || t.minimum > t.reorder || t.reorder > t.target || !Number.isInteger(t.windowDays) || t.windowDays < 2 || (t.leadDays !== undefined && (!Number.isFinite(t.leadDays) || t.leadDays < 0)) || [t.highConsumption,t.rapidDaily,t.replenishmentQuantity].some(n => n !== undefined && (!Number.isFinite(n) || n < 0)) || (t.replenishmentDue && !validDate(t.replenishmentDue))) throw new Error('Require 0 ≤ critical ≤ minimum ≤ reorder ≤ target, valid consumption window and optional quantities/dates.');
}
```

### src/lib/stockIntelligence.ts:38

```typescript
export function stockAlert(productId: string, unit: string, current: number | null, movements: FinishedGoodsMovement[], date: string, t?: StockThreshold) {
  if (t) { validateThreshold(t); if (t.productId !== productId || t.unit !== unit) throw new Error('Threshold unit/product mismatch.'); }
  const windowDays = t?.windowDays ?? 7, end = Date.parse(date+'T00:00:00Z'), start = new Date(end - (windowDays-1)*86400000).toISOString().slice(0,10);
  const outs = movements.filter(m => m.productId === productId && m.unit === unit && m.type === 'OUT' && m.date <= date && m.date >= start && !!m.dispatchId && !movements.some(r => r.reversalOf === m.id && r.date <= date));
  const consumption = outs.reduce((s,m) => s+m.quantity,0), days = new Set(outs.map(m => m.date)).size;
  const history = days >= 2; // Observed dispatch activity only; never a sales forecast.
  const labels: string[] = [];
  if (current !== null && current <= 0) labels.push('Out of Stock');
  else if (current !== null && t && current <= t.critical) labels.push('Critical Stock');
  else if (current !== null && t && current <= t.minimum) labels.push('Low Stock');
  if (movements.some(m=>m.productId===productId&&m.unit===unit&&m.type==='OUT'&&m.date>=start&&m.date<=date)) labels.push('Recent Stock OUT');
  if (t?.highConsumption !== undefined && consumption >= t.highConsumption && outs.length) labels.push('High Stock Consumption');
  if (history && t?.rapidDaily !== undefined && consumption/windowDays >= t.rapidDaily) labels.push('Stock Depleting Rapidly');
  if (t?.replenishmentQuantity && t.replenishmentDue) labels.push('Pending Replenishment');
  return { labels, severity: labels.includes('Out of Stock') || labels.includes('Critical Stock') ? 'Critical' : labels.includes('Low Stock') || labels.includes('Stock Depleting Rapidly') ? 'Warning' : 'Info', consumption, lastOUT: movements.filter(m => m.productId === productId && m.unit === unit && m.type === 'OUT' && m.date <= date).map(m=>m.date).sort().at(-1), history: history ? 'Observed consumption' : 'Insufficient History', dailyConsumption: history ? consumption/windowDays : null, recommended: current !== null && t && current <= t.reorder ? Math.max(0,t.target-current-(t.replenishmentQuantity ?? 0)) : null };
}
```

### src/lib/stockIntelligence.ts:58

```typescript
export function sellingCostBreakdown(amount: number, kg: number | null, p: PricePolicy) {
  if (!Number.isFinite(amount) || amount < 0 || ![p.vatRate,p.ledRate,p.usdPer1000KG,p.profitPercent].every(n=>Number.isFinite(n)&&n>=0) || p.vatRate>100 || p.ledRate>100 || (p.profitMethod==='gross-margin'&&p.profitPercent>=100) || (kg!==null&&(!Number.isFinite(kg)||kg<0)) || !['inclusive','exclusive'].includes(p.vatMode) || !['markup','gross-margin'].includes(p.profitMethod) || !['net-selling','production-cost'].includes(p.percentageBase) || !['percentage','weight','higher','lower'].includes(p.ledMode)) throw new Error('Invalid financial calculation configuration.');
  if(p.ledApplies && p.ledMode==='higher' && (p.ledRate!==LED_PERCENT || p.usdPer1000KG!==LED_USD_PER_TONNE))throw new Error('Confirmed MAX rates are 2.5% and USD 70 per metric tonne.');
  if (p.ledApplies && !p.selectionConfirmed) throw new Error('Confirm LED applicability and select the configurable percentage base before calculation. Higher of the Two is client-confirmed.');
  const v=p.vatRate/100, rate=p.ledRate/100, costFactor=p.profitMethod==='markup'?1/(1+p.profitPercent/100):1-p.profitPercent/100;
  const needsWeight=p.ledApplies&&p.ledMode!=='percentage';
  if (needsWeight && (kg===null || !p.usdToUGX || !Number.isFinite(p.usdToUGX) || !p.fxDate || !validDate(p.fxDate))) throw new Error('Weight-based LED requires valid KG and a saved positive USD→UGX rate/date.');
  const weight=kg!==null&&p.usdToUGX&&validDate(p.fxDate??'')?kg/1000*p.usdPer1000KG*p.usdToUGX:null;
  const levy=(net: number) => { const percentage=net*(p.percentageBase==='production-cost'?costFactor:1)*rate; if (!p.ledApplies) return 0; return p.ledMode==='higher'?calculateLED(net*(p.percentageBase==='production-cost'?costFactor:1),kg,p.usdToUGX,p.fxDate,p.percentageBase,p.vatOnLED).selectedUnrounded:p.ledMode==='percentage'?percentage:p.ledMode==='weight'?weight!:Math.min(percentage,weight!); };
  // Entered amount includes LED; inclusive mode also includes VAT. Solve a monotone
  // gross-price equation, including VAT-on-LED and cost-based levy, rather than subtracting assumed percentages.
  const gross=(net:number)=>net+levy(net)+v*(net+(p.vatOnLED?levy(net):0));
  const equation=(net:number)=>p.vatMode==='inclusive'?gross(net):net+levy(net);
  if (equation(0)>amount+0.0000001) throw new Error('Selling amount cannot cover the configured fixed weight levy.');
  let low=0,high=amount; for(let i=0;i<100;i++){const mid=(low+high)/2;if(equation(mid)>amount)high=mid;else low=mid;}
  const net=(low+high)/2, led=levy(net), vat=v*(net+(p.vatOnLED?led:0)), cost=net*costFactor;
  const result={ netSelling:roundMoney(net), vat:roundMoney(vat), percentageLED:p.ledApplies?roundMoney(net*(p.percentageBase==='production-cost'?costFactor:1)*rate):0, weightLED:weight===null?null:roundMoney(weight), selectedLED:roundMoney(led), selectedCalculation:p.ledApplies&&p.ledMode==='higher'?calculateLED(net*(p.percentageBase==='production-cost'?costFactor:1),kg,p.usdToUGX,p.fxDate,p.percentageBase,p.vatOnLED).selected:'legacy / not applicable', profit:roundMoney(net-cost), estimatedCOP:roundMoney(cost), finalPrice:p.vatMode==='inclusive'?roundMoney(amount):roundMoney(amount+vat), eligibleKG:kg, policy:structuredClone(p) };
  if (!Object.values(result).filter(v=>typeof v==='number').every(Number.isFinite)) throw new Error('Amounts exceed supported range.');
  return result;
}
```
