# Frontend Data Models

## Persistent quotation drafts — 16 October 2026

QuotationDraft stores client UUID primary key, created_by, validated editor_data JSON, positive version and timestamps. Draft schemas preserve editable public fields and source identity metadata, exclude caller-supplied approval/status/audits, support blank customer/zero lines, and validate entered line units/quantities/prices. Saved editor decimals are strings and restored to numeric frontend fields. Frontend Quotation adds optional draftVersion. Snapshot review status remains derived from backend Quotation decisions.


## User roles and quotation rejection — 16 October 2026

accounts.Role stores unique supported role code, name, active flag and permission M2M. User.assigned_role references Role with PROTECT; legacy role text remains as a fallback. effective_role resolves active assignment; JWT profile emits its code. Quotation adds rejected_by, rejected_at and rejection_reason; approval and rejection are mutually exclusive through locked review actions. Responses expose reviewed_by and rejection state.


## Editable quotation selling price — 16 October 2026

QuotationLine adds optional manualPriceOverride for explicit manual custom selling-price edits. It bypasses only equality to the calculated public costing price, not costing approval/currency/revision/source checks. It is excluded from the customer public projection.


## Quotation units and line totals — 16 October 2026

erp.Unit extends Record with unique code (max 30), name (max 100), is_active and a case-insensitive code constraint. QuotationLine optionally stores frontend unitId; public requests send unit_id. Backend resolves active master IDs/codes, rejects mismatches and snapshots canonical code/id. Derived lineTotal and unitPriceInclVat are server-controlled decimal strings. Historical snapshot unit strings remain unchanged if the unit is later deactivated.


## Quotation manager approval and saved customers — 16 October 2026

Added Quotation.submitted_at and manager-role approval checks. Customer adds contact_person, delivery_address, tin, customer_type, unique nullable creation_key and generated code default. Quotation.customer_master optionally references erp.Customer using PROTECT; public contact snapshots remain independent. Frontend backend customer IDs use db:{id}.


## Persisted quotation PDF slice — 15 October 2026

Sibling Django models `quotations.Quotation` (immutable validated public document JSON, content fingerprint, creator, server approval actor/time) and `quotations.Delivery` (request UUID, selected channel, recipient, provider submission result and actor/time) persist independently of session-only commercial frontend records. Server totals use decimal arithmetic; client approval/status/private costing are not adopted. Unique snapshot fingerprint and quotation/request/channel constraints prevent exact replay duplication. See `../Backend/quotations/README.md` for boundaries.


These are current TypeScript/frontend or mock models, not database schemas. API consumer types are not proof of implemented backend contracts.

## Sales orders (src/types/index.ts; src/lib/salesOrders.ts)

SalesOrder: id, orderNumber, customerName, date, Open/Completed status and jobCardIds; optional customerId, marketingPersonName, B2B/B2C customerType, requisitionOrder, items and orderTotal support legacy seed records.
SalesOrderItem: id, optional itemId (finished-goods variant reference), itemName, quantity, unit, unitPrice and totalPrice.
SalesOrderDraft contains form customer/date/marketing/type/requisition fields and items; customerType temporarily permits an empty value.
New orders get a UUID-derived ID and locally generated SO number (maximum numeric suffix + 1).
totalPrice = round(quantity x unitPrice, 2); orderTotal = round(sum of rounded line totals, 2). orderSummary returns the pre-tax subtotal; buildSalesOrder applies transaction tax to the order total. Direct-order invoice discounts/tax are calculated on selected dispatches. Quotation-origin orders retain optional inclusive/exclusive/discount/rounding snapshots, which the order builder and invoices honour rather than applying VAT twice.

## Finished goods (src/lib/finishedGoodsData.ts)

FinishedGood identifies a variant with id, category (carrier-bags/flat-bags/packing), subgroup, customer, itemDetails, size, brand, packingSize and unit.
Optional pieces is a positive whole-number count per package; existing reference records leave it unrecorded. InventoryContext holds navigation-safe finishedPieces overrides by variant ID. Pieces never changes the ledger unit or quantity.
openingStock is number or null; openingDate anchors the reference ledger. sourceSheet, sourceRow, sourceCustomer, customerInherited, sourceUnit, sourceClosingStock and dataNotes preserve provenance and ambiguity.

FinishedGoodsMovement: id, productId -> FinishedGood.id, date, type (IN/OUT), quantity, unit; optional customer, reference and remarks.
InventoryContext validates product existence, matching unit and positive finite quantity on additions.

## Raw material (src/lib/rawMaterialData.ts)

RawMaterial: id, name, family, category (virgin/recycled/ink), unit, nullable openingStock and openingDate; optional minLevel, sourceRow and nullable sourceClosingStock.
RawMaterialMovement: id, date, materialId -> RawMaterial.id, materialName, category, movementType (IN/OUT), quantity, unit, reference and remarks.
InventoryContext validates material/category/unit and positive finite quantity; it takes materialName from the master.

Both balance helpers return openingStock, stockIn, stockOut and currentStock. For known openings, currentStock = openingStock + stockIn - stockOut (six-decimal rounding).
Monthly opening adds signed movements before month start; monthly totals use dates starting with the selected month.
Unknown reference opening or a month before openingDate returns null opening/current balances while retaining movement totals.

## Demand projection (src/pages/Stocks/SalesOrderDemand.tsx)

There is no named SalesOrderDemand interface. A derived row extends an open SalesOrderItem with product, available, required, status, orderNumber and customer.
Product links by variant ID, with unique legacy-name/unit fallback. available is null if unlinked, mismatched or unrecorded.
required = max(0, quantity - max(0, available)) when available is known. Rows independently compare physical stock; demand creation itself neither reserves nor posts OUT. Optional allocations and direct confirmed dispatch share InventoryContext.

## Production and trace (src/types/index.ts)

JobCard retains id, jobCardNumber, salesOrderId, modelName, qty, status, department and legacy stages. Optional salesOrderNumber, customerName, product, specifications, productionRequirements, unit, createdDate, requiredDate, approval, requiredMaterials, productionStages, activityHistory, acceptedQuantity and stockTransfer support manufacturing tracking. Missing API quantities remain unrecorded; order references are resolved from existing SalesOrdersContext when available.
JobCardStatus additionally supports StoreIssuePending, MaterialIssued, OnHold and ReadyForStock; legacy Issued is displayed as Material Issued. Delayed is derived from requiredDate and is not stored as a replacement status.
JobCardMaterial contains id, optional exact raw materialId, name, requiredQuantity, issuedQuantity and unit. Availability is read only for an exact material/unit match; issue actions do not modify inventory.
JobProductionStage contains id, free-form name/department, sequence, required, production/stock kind, optional legacyStage mapping, Pending/Received/InProgress/Completed/OnHold status, nullable input/output/waste quantities, independent input/output/waste units, startedAt/completedAt, operator, remarks, optional handover source/quantity/unit, wasteType, wasteReason and sentToRecycling. Waste rows, current location and final produced quantity are derived from these records, avoiding duplicate quantities and incompatible-unit totals.
JobCardActivity contains id, timestamp, action, user, department and description. Stock transfer retains accepted quantity/unit, batch date, confirmation user/time, and job/sales-order/customer/model/product references. Neither is a permanent audit or inventory transaction.
Legacy JobCardStageEntry remains stage, sequenceOrder, required and Pending/InProgress/Complete status. Stage still enumerates Extrusion/Printing/Packaging/Stock/Ready to Sale for existing modules; dynamic manufacturing stage names do not extend or hard-code this shared enum. Required flags and completed statuses stay synchronized for mapped legacy stages.
TraceResult: traceId, SalesOrder/JobCard/MaterialBatch/GranulesBatch type, currentStatus, optional currentStage and label/timestamp history. Lookup results are API/mock data, not computed from Context records.

## Recycling and costing (src/types/index.ts)

WasteEntry: id, jobCardNumber (text reference), stage, wasteQty, kg unit, wasteType, sentToRecycling and date.
GranulesBatch: id, batchNumber, date, inputWasteQty, granulesProducedKg and destination; optional reEnteredQty, soldQty, soldTo. These fields do not automatically change inventory.
Recycling summaries sum unsent wasteQty and all loaded granulesProducedKg; despite month labels, there is no month filter.

CostingRecord: id, itemOrModel, rawMaterialCost, productionCost, otherCost, USD/NGN/GHS/ZAR currency, exchangeRateUsed, totalCostLocal and lastUpdated. totalCostLocal is supplied data; CostingPage does not calculate it.
ExchangeRate: id, currency, rate, date, enteredBy. New local entries prepend to history; existing costs are unchanged.

## Masters and user (src/types/index.ts)

Item: id, name, unit, category. This generic demo master is separate from FinishedGood.
Model: id, name, billOfMaterials (text), stages.
Customer: id, name, contactPerson, phone.
Supplier: id, name, materialSupplied, phone.
Department: id, name, assignedProductionManager (text).
MasterUser: id, name, email, role, optional department.
User: id, name, role, optional department; held by AuthContext.
Role: receptionist, production_manager, store_keeper, production_operator, recycling_operator, accounts, qc_inspector, qc_supervisor or admin.
Customer master state is shared via CommercialContext and models via ModelsContext; other Master page edits remain local. Name fields are not backend foreign-key enforcement.

## Consumables (src/lib/consumableData.ts; ConsumablesContext)

Consumable: id, name, imported/local category, Each/Both/Litres/Kilos unit, openingStock, openingDate and optional minLevel. ConsumableMovement: id, materialId, date, IN/OUT type, quantity, reference and remarks. ConsumablesContext owns empty initial masters and movements, validates additions and locks posted units/openings. State survives navigation and resets on refresh.

## Sales fulfillment extensions

See [sales-fulfillment.md](sales-fulfillment.md) for extended line/order/job/movement fields and Allocation, Dispatch, FulfillmentLedger, Invoice and receipt interfaces. Tax/currency are transaction fields; invoice snapshots are separate from physical stock events. InventoryContext owns all finished movements/reservations/dispatches. Multiple receipt batches retain stable source/request IDs.

## Custom costing and routing additions

Revisioned Model recipes/processes/routing and CostEstimate input/totals/approval/customer-response snapshots are session models. Order lines retain model/revision/specification/delivery/estimate references; Job Cards retain model/estimate/routing revisions, approved material/route snapshots and reapproval history. Production stages carry machine, expected quantities/units, planned waste and instructions. Unmapped QC output may retain stockReceiptPending until an exact finished variant is selected. See [field and formula details](custom-costing-routing.md).

## Parent Job Cards — 13 October 2026

New JobCard headers contain `origin: sales_order` and `manufacturingItems`; each item reuses the existing JobCard workflow fields with a distinct stable `id`, `parentJobCardId`, `salesOrderItemId`, product/model/estimate revisions, quantities/units, materials, approved routing, stages and receipts. Headers do not expose a summed production quantity: compatibility `qty` is zero, and views use item quantities. Header status/due date/activity derive from items. JobCardActivity adds parent `jobCardId` and `manufacturingItemId`; FinishedGoodsMovement adds `manufacturingItemId` while `jobCardId` points to the parent for new receipts. Old records keep their existing IDs and shape. `production_for_stock` is a prepared origin value only; its workflow remains pending. See the phase boundary in sales-fulfillment.md.

## Quality Control frontend models

`src/lib/quality.ts` defines QCItem, QCTemplate, QCResponse, QCSubject, QCInspection, QCApproval, QCRelease, QCNonConformance and QCEvent. Templates and inspections retain exact revision snapshots, independent samples/measurements/tolerances/units, typed source IDs, assignment, immutable submission/review/reinspection history and purpose-specific release references. The live session NC stores corrective action/verification plus append-only events; separate action/attachment persistence is a future contract.

JobProductionStage adds optional `qcTemplateIds` and `machineId`, preserved in approved routing. JobCard adds `productionBatches` inspection-lot records (stable ID/number/stage/quantity/unit/time); these partition existing output and are not independent execution runs. FinishedGoodsMovement adds `qualityReleaseId` and `stockApprovalId`, alongside parent/manufacturing-item references. ModelsContext owns shared Machine records (UUID, name, department, extruder/recycle_extruder type, active). QualityContext owns configurable area IDs, versioned templates, inspections/releases and NCs. Raw inward IDs remain source references; missing supplier identity is not fabricated.

[quality.md](quality.md) is the canonical proposed Django/DRF data contract, including UUID/FK/field/status/validation/unique/audit/lifecycle/permission requirements for all eleven requested entities and audit integration. No backend schema was created.

## Quotations / commercial additions

`src/lib/quotations.ts`: Quotation family/revision identity, type/dates/validity/delivery, party/company/terms/price/tax snapshots, exact lines/product/model/costing references, status, approvals, responses and events. CompanySettings includes multiple BankAccount records and editable commercial defaults. QuotationCustomer retains customer/prospect/contact/billing/delivery/TIN/type; QuotationTerms stores optional advance/credit/tolerance clauses. CommercialContext reuses Customer and adds CustomerProspect with explicit linkedCustomerId; no duplicate customer store remains on Masters.

CostingInput adds optional quotationId with logical quotation-line itemId and no fabricated order ID; CostEstimate adds salesOrderReferences for immutable source adoption. `estimateMatchesOrder` resolves original/adopted order-line sources. SalesOrder/Draft add quotation family/revision IDs/number, prospect/contact/terms and commercialPricing (taxMode/discount/rounding); items preserve quotationLineId and original quotationCostEstimateId/revision. Invoices add taxMode, allocated quotationDiscount and explicit roundingAdjustment for final billed reconciliation. Public projection excludes internal costing inputs/source actor IDs.

Future Django sales entities, relationships/constraints/precision/status/permissions/audit and proposed DRF contracts are defined once in [quotations.md](quotations.md); no schema was implemented.

## Integrated operations — 15 October 2026

InventoryContext adds append-only ProductConversion (product/model/unit, KG-per-CTR, pieces, effective date/version), StockThreshold (ordered levels, exact unit, observation window, optional lead/consumption/replenishment settings). New FinishedGoodsMovement saves QuantitySnapshot original quantity/unit, nullable KG and exact rule/version/product/model, plus explicit movementPurpose. Old movements remain unchanged. Direct confirmed dispatch reuses closed allocation provenance with zero reservation.

CostingContext adds StockPriceSnapshot: batch/product/model/date/quantity/unit/UGX amount; immutable PricePolicy VAT/LED/base/FX/profit settings; QuantitySnapshot; computed breakdown; optional evidenced actual COP; revision/author/time. No cost estimate or commercial order snapshot is rewritten. JobCard adds append-only productionRuns with stage ID, execution quantities/approved units/times/operator/remarks and completesStage; existing stage aggregates/handover remain authoritative.

Quotation adds generationKey, session emailDrafts and distinct Internally Rejected/Revision Requested states. Generate source key survives ordinary revisions; deliberate duplicates start a new family. Email drafts retain exact number/revision/recipient/CC/subject/message/manual attachment note, author/time and Draft — not sent status, never public projection. QC template frequencies extend without changing existing seeds; QCSchedule references exact subject/latest template/configured frequency/date range/assignment/shift/active state/creator/time. QCInspection.scheduleKey deduplicates occurrences. KSEC starts inactive pending defined checks/category.

Canonical formulas, field semantics, ownership, role checks, server capabilities and transaction boundaries are in [the integrated report](sales-fulfillment.md#integrated-operations-update--15-october-2026). These are frontend state models, not migrations.

## Confirmed LED / finance follow-up

Optional CostingInput.led and QuotationLine.led capture applicability, provisional percentage base, eligible KG, conversion, FX/date and VAT-on-LED. CostingTotals.led, QuotationLine.ledSnapshot and SalesOrderItem.ledSnapshot retain LEDSnapshot (confirmed higher method/rates, base value/choice, KG, both comparison amounts, selected raw/rounded amount/branch, FX/date, conversion identity/version, VAT flag). CommercialTotals optionally adds led/ledTax; accepted order totals include them. Invoice retains apportioned per-line snapshots/LED total and final reconciliation. Existing historical records without LED fields retain prior behavior; no migration/backend model was added. Finance uses the existing accounts Role/User; no parallel user entity.
