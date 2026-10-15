# Frontend data models and mappings

15 October 2026. Source: current frontend working tree. This document catalogs declarations without silently changing frontend field names. The generated declaration appendix includes every interface/type/enum in `src`, including UI props and Context contracts; those UI contracts are not automatically database entities. In TypeScript, `?` means optional; `T | null` is distinct from optional and zero; required declaration fields can still be blank/NaN in unfinished forms. No runtime schema library exists. Never use a TypeScript cast as server validation.

## Domain catalog and backend ownership

| Frontend entity / source | Meaning, persistence and proposed backend mapping | Relationships / decisions |
|---|---|---|
| User, Role, MasterUser / types + AuthContext | In-memory auth identity; generic Masters user rows are page-local and separate. `identity.User`, role/permission memberships. | User.id must be server identity; email/role free-text master editing does not create login accounts. Nine current roles need SOP mapping. |
| Customer / types; CustomerProspect / CommercialContext | Shared MOCK_CUSTOMERS + empty prospects, session-only. `masters.Customer`, `sales.Prospect`. | Explicit linkedCustomerId/prospectId; preserve contact/billing/delivery/TIN snapshots on documents; free-text order names still allowed. |
| Item, Supplier, Department / types | Page-local MOCK arrays. `masters.Product`, `Supplier`, `Department` after identity reconciliation. | Item is not the imported FinishedGood variant master; supplier materialSupplied and manager name are text, not FKs. |
| Model / types, Machine / ModelsContext | Shared revisioned seed models and empty machines. `ProductModel`, `ProductModelRevision`, `Machine`. | Recipe, process, routing and default-cost config snapshots. Machine type only extruder/recycle_extruder; no comprehensive equipment model yet. |
| FinishedGood / finishedGoodsData | Workbook reference master; optional pieces, nullable openingStock/sourceClosingStock and source provenance. `ProductVariant`, `OpeningBalanceImport`. | Category Carrier Bags/Flat Bags/Packing; do not merge repeated identity rows automatically. Customer string is not Customer FK. |
| FinishedGoodsMovement / finishedGoodsData | Shared ledger seeded from workbook; append on IN/OUT/receipt/dispatch/reversal. `StockMovement`. | Exact product, unit, job parent/item, order/line, QC/final release, batch, dispatch, reversal and conversion snapshot. No warehouse FK currently. |
| RawMaterial, RawMaterialMovement / rawMaterialData | Specific grade/category/family/master + separate shared ledger; reference plus legacy demo granules. `Material`, `MaterialReceipt`, inventory movement. | No supplier/batch/source-job FK in actual movement type. materialName is display snapshot; category must match master. |
| Consumable, ConsumableMovement / consumableData | Empty session store, imported/local spares, Each/Both/Litres/Kilos. `Consumable`, shared ledger scope. | Opening/unit lock after posting; no maintenance record link. |
| Movement, ItemMaster, Category / stockData | Legacy name-keyed mixed ledger and currency/rate metadata. Migration evidence only. | Only granules are adapted into RawMaterial; do not instantiate a competing new ledger or autoimport raw/FG legacy examples. |
| SalesOrderDraft / salesOrders; SalesOrder, SalesOrderItem / types | Shared seeds + create session orders; derived statuses separate from stored status. `SalesOrder`, `SalesOrderLine`. | Optional items supports legacy headers; line id stable, itemId is FG variant, modelId optional custom source, estimate/version, quotation lineage, LED snapshots. |
| JobCard / types | API/fallback shared store. Same recursive type represents parent header and manufacturing child plus legacy single-item jobs. `JobCard` + `JobCardItem`. | One new parent per order; child unique order line; no summing unlike-unit children into qty. `origin` supports a target for-stock intent but creation/receipt path incomplete. |
| JobCardStageEntry, Stage / types | Legacy enum route: Extrusion, Printing, Packaging, Stock, Ready to Sale. | Compatibility projection only. Dynamic JobProductionStage names are arbitrary configured processes. |
| JobCardMaterial / types | Required/issued quantity rows embedded in job. `JobMaterialRequirement`, `MaterialIssueLine`. | `issuedQuantity` is cumulative frontend tracking, not evidence of raw ledger OUT or consumption. |
| JobProductionStage, JobCardActivity / types | Per-item route, planned/actual quantities/units, machine/operator/handovers and events. `JobRouteStage`, `StageExecution`, `AuditEvent`. | Stable stage ID, unique sequence, required and kind, checkpoint template IDs; operator currently text. |
| ProductionRun / productionRuns | Indexed alias to JobCard.productionRuns element; item/stage input/output/waste/time data. `ProductionRun`. | Multiple nonoverlapping sequential runs accumulate; not the same as QC lot partition. |
| JobCard.productionBatches, stockTransfers, routingApproved | Inline nested objects, not named interfaces. `OutputLot`, `FinishedReceipt`, `RoutingApproval`. | Preserve child/parent/source identities, immutable approval route/material snapshots and cumulative authorization. |
| Allocation, Dispatch, FulfillmentLedger / fulfillment | Empty allocations/dispatches with shared FG movements. `Reservation`, `Dispatch`, `DispatchLine`. | Allocation optional; direct dispatch creates/releases an internal allocation; OUT links dispatch; reversal immutable paired IN. |
| Invoice, InvoiceDraft / invoices | Empty shared immutable session snapshots. `billing.Invoice`, `InvoiceLine`, dispatch join. | Exactly uninvoiced confirmed dispatches; no stock on invoice, payments/credit notes missing. Keep LED/tax/discount final reconciliation. |
| MaterialRecipe, ProcessCost, CostingInput, CostingTotals, CostEstimate / customCosting | Session revisioned estimates; persisted nowhere. `CostEstimateRevision`, `RecipeLine`, `ProcessCostLine`, frozen totals. | Origin actual order line or quotation family/logical line; quotation-origin orderId is empty, not fabricated FK. Cost currency USD/UGX. |
| CostingRecord, ExchangeRate / types | Legacy API/mock reads and local rate POST fallback. `CostSummary` projection, `ExchangeRate`. | Currencies USD/NGN/GHS/ZAR and ₦ local UI conflict with UGX snapshots; choose explicit currency pairs and historical policy. |
| LEDInput, LEDSnapshot / led | Embedded config/result snapshots in estimates, quotes and order lines. `PricingPolicyRevision`, immutable monetary snapshot. | MAX 2.5% base vs USD70/tonne×FX; base and applicability still explicit/pending client confirmation. No KG/FX fallback. |
| ProductConversion, QuantitySnapshot / stockIntelligence | Empty session versioned conversions; new movement snapshots freeze KG. `ProductConversionRevision`, movement snapshot. | Exact product/model/unit/effective date; ctn↔kg requires configured ratio. pieces metadata does not imply mass. |
| StockThreshold, PricePolicy, StockPriceSnapshot / stockIntelligence | Session reorder configuration and versioned financial snapshot. `StockPolicy`, `StockPriceRevision`. | Exact stock unit and batch; actualCOP requires evidence reference, not automatically actual production cost. Legacy LEDMode includes alternatives rejected for new saved snapshots. |
| BankAccount, CompanySettings, QuotationCustomer, QuotationTerms / quotations | Shared defaults/terms/prospects settings; frozen document snapshots. `CompanySettingsRevision`, `BankAccount`, document JSON snapshots. | UGX/18% inclusive/14-day defaults are editable examples, not verified statutory/SOP policy. Sensitive bank details remain blank pending reference. |
| Quotation, QuotationLine, QuotationResponse, QuotationEvent, QuotationStatus / quotations | Empty shared revision families; `Quotation`, `QuotationRevision`, `QuotationLine`, `CustomerResponse`, `ApprovalEvent`. | rootId family, id revision, logical line IDs preserved across revision; one resulting SO per family. Internal approval != customer acceptance. |
| QuotationEmailDraft / quotationReview | Session draft with manual PDF attachment description. `CommunicationDraft` initially; outbox if later approved. | Status literal Draft — not sent; mailto has no delivery evidence/public link. |
| QCItem, QCTemplate, QCResponse, QCSubject, QCEvent, QCApproval, QCInspection, QCRelease, QCNonConformance, QCState / quality | Empty inspections/releases/findings; seeded provisional template revisions/areas. Dedicated quality entities. | Exact receipt/item/stage/lot/machine/area references; template snapshot; independent review; separate quality and final stock purposes. |
| QCSchedule / qualitySchedule | Empty session schedules; exact subject/template/date/shift/assignee. `InspectionSchedule`, unique occurrence. | Explicit generation, weekly/monthly/per-shift logic; do not recur consumed raw/production lots as daily inspections. |
| WasteEntry, GranulesBatch / types | Recycling API/mock card projections. `WasteLot`, proposed `RecyclingBatch`. | JobCardNumber text and quantities; no stable input/output allocation or actual inventory transfer. |
| TraceResult / types | Legacy API/sample trace projection. `reports.TraceProjection`, not another persistent business entity. | Current connected trace derives from shared IDs; legacy history label/time lacks authoritative event lineage. |

## Defaults, validation and derived fields

Sales: date local today, next SO max numeric suffix +1, UUID `so-` id, status Draft, jobCardIds empty. New form starts quantity/price as NaN and source/type/currency/tax unset; draft controls allow incompleteness, submit requires currency, tax 0–100, B2B/B2C, customer name, marketing name, real date, at least one selected product or manufacturing model, positive finite quantity, nonblank unit and finite nonnegative rate. Required custom delivery date >= order date. Customer/marketing IDs are not universally required. Source/unit consistency needs server improvement.

Models: new revision zero in form then max revision+1 on save; default kg batch unit, quantity zero, UGX/10% markup/0 tax, empty recipe/process/route, waste/overhead zero. `reviseProductModel` requires identity/name/default unit, exact raw IDs/unit and nonnegative finite defaults; it does not validate every route/recipe formula at model-save time. `calculateCost` performs stronger checks later.

FG/raw: opening null stays null after movements; known IN/OUT totals can coexist with unknown closing. Six-decimal ledger arithmetic; monthly opening includes prior dated movement carry-forward. Reference data provenance is retained. No default inferred balance, unit conversion or customer association should be invented. Consumables start opening 0; its save validates category/units/opening/date pattern/minimum; posted unit/opening/date are locked.

Quotations: QT max suffix+1; UUID family=id, revision1, blank party/lines/terms, date today and configured validity. blank line defaults stock, quantity1, rate0. Full validation requires actual customer/prospect ID, representative and items; draft validation permits some incomplete state. Approval freezes totals/rounding; exact approved custom estimate/model source validated again on send/conversion. Expiry is often derived rather than stored. Prospect requires name only; shared customer requires admin/id/name.

QC: template revisions start1, effective 2026-10-13, active except KSEC. Templates are provisional. createInspection creates UUID/QC short number, Draft, assigned actor, empty responses/metadata/time/history. Production samples 1–8, other categories 1. Submission requires valid time, nonfuture inspection date, completed required answers, NA reason and numeric tolerances; raw sampled quantity and COA/TDS/MSDS metadata; cleaning method/chemicals/cleaner. Review requires different user and remarks; fail cannot pass. Conditional raw acceptance stays held. `qualityIntegration.ts` supplies cross-domain guards; no actual database constraints exist.

Manufacturing: exact materials/date/unit validated before linked job; draft if estimate-backed, otherwise pending approval. Approved route/material snapshot cannot change after issue/start. Stage quantities may be null until recorded; not zero by default. Completion requires chronology/operator/finite quantities, compatible-unit bounds. Unknown raw availability can be accepted for issue when no unreleased receipt causes a block; this is a frontend limitation. See workflows for actual command constraints.

Invoice: caller supplies number/company/contact/tax/billing data; helper snapshots order and dispatch descriptions, unit prices, quantities, tax/discount/LED and amount-in-words. One dispatch cannot be invoiced twice. Invoice is not fiscal certification or payment.

## Explicit naming bridge (proposal)

Keep camelCase in an initial adapter if minimizing client changes; if API adopts snake_case, map explicitly:

| Existing field | Proposed API field | Meaning |
|---|---|---|
| SalesOrder.orderNumber / orderTotal | order_number / total | Server-issued number / recomputed frozen commercial total. |
| SalesOrderItem.id / itemId | id / product_variant_id | Line identity / exact FG variant, not generic master item. |
| SalesOrderItem.totalPrice | line_total | Rounded quantity×unit price before document tax/discount. |
| marketingPersonName | marketing_person_name + marketing_person_id | Retain entered snapshot; stable user/employee relation separately. |
| JobCard.qty / salesOrderItemId | quantity / sales_order_line_id | Manufacturing child quantity in explicit unit. |
| JobCard.manufacturingItems | items | Normalize to child rows, compatibility serializer may preserve original key. |
| JobCard.requiredMaterials | material_requirements | Planned requirements, separate issue records. |
| JobProductionStage.sequence / machine / operator | sequence / machine_name / operator_name | Add machine_id/operator_id without discarding text history. |
| RawMaterialMovement.movementType vs FG.type | direction | Same IN/OUT domain; explicit adapters for each client shape. |
| RawMaterialMovement.materialId / FG.productId | material_id / product_variant_id | Separate inventory scopes; reject both/neither. |
| stockApprovalId / qualityReleaseId | stock_authorization_id / quality_release_id | Two distinct decisions; neither is a stock movement. |
| Quotation.rootId / id | quotation_id / revision_id | Family uniqueness vs historical document identity. |
| CostingInput.itemId | source_line_id plus source_kind | Can be quotation logical line or SO line; never blindly FK to SO. |
| ExchangeRate.rate | target_per_source | Require explicit source_currency/target_currency/effective_date. |
| finishedPieces[productId] | pieces_per_package | Metadata only, never physical quantity. |

Open business decisions: role mapping, numerical precision/rounding, unit vocabulary and conversion governance, order amendments/status authority, for-stock manufacturing, supplier lot allocation, issue/return/consumption timing, final stock authority, QC disposition and source checklists, import openings, LED percentage base/VAT treatment, fiscal/payment integration. Do not silently resolve these in migrations.

## Exact declaration appendix

Extracted from source with the installed TypeScript parser. Complete named declarations preserve optionality, literal enums, nested objects and utility types. Source excerpts establish shape only; behavioral defaults/validation are above and in source helpers. UI-only props/context interfaces are deliberately retained for completeness and must not become database tables.


### src/components/layout/AppShell.tsx

#### NavItem — src/components/layout/AppShell.tsx:20

```typescript
interface NavItem {
  to: string;
  label: string;
  icon: typeof LayoutDashboard;
  roles: Role[];
}
```

### src/components/login/TextField.tsx

#### TextFieldProps — src/components/login/TextField.tsx:3

```typescript
interface TextFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
  icon?: ReactNode;
  trailing?: ReactNode;
}
```

### src/components/ui/InventoryMovementModal.tsx

#### InventoryOption — src/components/ui/InventoryMovementModal.tsx:5

```typescript
export interface InventoryOption { id: string; name: string; category: string; unit: string; available: number | null; openingDate?: string; detail?: string; fields?: [string, string][]; pieces?: number | null; customer?: string }
```

#### InventoryEntry — src/components/ui/InventoryMovementModal.tsx:6

```typescript
export interface InventoryEntry { movementPurpose?: 'transfer' | 'waste' | 'adjustment'; date: string; materialId: string; quantity: number; reference: string; remarks: string; customer?: string; pieces?: number }
```

### src/components/ui/SearchSelect.tsx

#### SearchOption — src/components/ui/SearchSelect.tsx:4

```typescript
export interface SearchOption { id: string; name: string; detail?: string }
```

#### Props — src/components/ui/SearchSelect.tsx:5

```typescript
interface Props {
  label: string; value: string; options: SearchOption[]; error?: string; inputId?: string;
  onChange: (value: string) => void; onSelect: (option: SearchOption) => void;
  onAdvance?: () => void;
}
```

### src/context/AuthContext.tsx

#### AuthContextValue — src/context/AuthContext.tsx:6

```typescript
interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string, finance?:boolean) => Promise<void>;
  loginAsDemo: (role: Role) => void;
  logout: () => void;
}
```

### src/context/CommercialContext.tsx

#### CustomerProspect — src/context/CommercialContext.tsx:6

```typescript
export interface CustomerProspect extends Customer { linkedCustomerId?: string }
```

#### CommercialValue — src/context/CommercialContext.tsx:7

```typescript
interface CommercialValue { customers: Customer[]; prospects: CustomerProspect[]; company: CompanySettings; termsTemplates: QuotationTerms[]; saveCustomer: (customer: Customer) => void; addProspect: (prospect: Omit<CustomerProspect, 'id'>) => CustomerProspect; promoteProspect: (id: string, customerId?: string) => Customer; saveSettings: (company: CompanySettings) => void; saveTermsTemplate: (terms: QuotationTerms) => void }
```

### src/context/ConsumablesContext.tsx

#### ConsumablesState — src/context/ConsumablesContext.tsx:4

```typescript
interface ConsumablesState {
  items: Consumable[];
  movements: ConsumableMovement[];
  saveItem: (item: Consumable) => void;
  addMovement: (movement: Omit<ConsumableMovement, 'id'>) => void;
}
```

### src/context/CostingContext.tsx

#### State — src/context/CostingContext.tsx:11

```typescript
interface State { stockPrices: StockPriceSnapshot[]; saveStockPrice: (draft: Omit<StockPriceSnapshot, 'id' | 'revision' | 'actor' | 'createdAt' | 'breakdown'>) => void; saveForQuotation: (input: CostingInput, quotation: Quotation, existingId?: string) => CostEstimate; bindQuotationOrder: (estimateId: string, orderId: string, itemId: string) => void; bindJob: (id: string, jobCardId: string) => void; estimates: CostEstimate[]; save: (input: CostingInput, existingId?: string) => CostEstimate; setStatus: (id: string, status: EstimateStatus) => void; accept: (id: string, accepted: boolean) => void; generate: (id: string) => void; invalidate: (id: string, reason: string) => void }
```

### src/context/InventoryContext.tsx

#### InventoryContextValue — src/context/InventoryContext.tsx:14

```typescript
interface InventoryContextValue {
  conversions: ProductConversion[];
  thresholds: StockThreshold[];
  saveConversion: (draft: Omit<ProductConversion, 'id' | 'version'>) => void;
  saveThreshold: (draft: StockThreshold) => void;
  directDispatch: (order: SalesOrder, item: SalesOrderItem, batch: string, draft: Parameters<typeof confirmDirectDispatch>[4]) => void;
  ledger: FulfillmentLedger;
  allocateStock: (order: SalesOrder, item: SalesOrderItem, quantity: number, batch: string, requestId?: string) => void;
  dispatch: (draft: Parameters<typeof confirmDispatch>[1]) => void;
  reverse: (id: string, date: string, reason: string) => void;
  postReceipt: (movement: FinishedGoodsMovement) => void;
  finishedMovements: FinishedGoodsMovement[];
  finishedPieces: Record<string, number>;
  updateFinishedPieces: (productId: string, pieces: number) => void;
  rawMovements: RawMaterialMovement[];
  addFinishedMovement: (movement: Omit<FinishedGoodsMovement, 'id'>) => void;
  addRawMovement: (movement: Omit<RawMaterialMovement, 'id'>) => void;
}
```

### src/context/JobCardsContext.tsx

#### JobCardsState — src/context/JobCardsContext.tsx:21

```typescript
interface JobCardsState {
  recordRun: (id: string, run: ProductionRun, finish: boolean) => void;
  registerBatch: (id: string, stageId: string, number: string, quantity: number) => NonNullable<JobCard['productionBatches']>[number];
  createLinked: (orderId: string, itemId: string, modelId: string, requiredDate: string, specifications: string, materials: NonNullable<JobCard["requiredMaterials"]>, estimateId?: string) => Promise<JobCard>;
  cards: JobCard[];
  loading: boolean;
  usingDemo: boolean;
  load: () => Promise<void>;
  loadDetail: (id: string) => Promise<void>;
  postPreparedReceipts: (id: string, productId: string) => void;
  saveRouting: (id: string, stages: NonNullable<JobCard['productionStages']>, materials: NonNullable<JobCard['requiredMaterials']>) => void;
  reviseRouting: (id: string) => void;
  recalculate: (id: string, estimateId: string) => void;
  sendForReview: (id: string) => void;
  approve: (id: string) => void;
  issue: (id: string, quantities: Record<string, number>, available: Record<string, number | null>) => void;
  updateStage: (id: string, stageId: string, update: StageUpdate) => void;
  transfer: (id: string, accepted: number, batchDate: string, receipt?: StockReceiptOptions) => void;
  edit: (id: string, change: Parameters<typeof editJobCard>[1]) => void;
  toggleStage: (id: string, stageId: string) => void;
  saveSequence: (id: string) => Promise<boolean>;
}
```

### src/context/ModelsContext.tsx

#### Machine — src/context/ModelsContext.tsx:6

```typescript
export interface Machine { id: string; name: string; department: string; type: 'extruder' | 'recycle_extruder'; active: boolean }
```

### src/context/QualityContext.tsx

#### QualityValue — src/context/QualityContext.tsx:7

```typescript
interface QualityValue extends QCState {
  schedules: QCSchedule[];
  addSchedule: (sourceId:string,startDate:string,endDate:string|undefined,shift:string|undefined,assignedTo:string)=>void;
  toggleSchedule: (id:string)=>void;
  generateSchedule: (id:string,date:string)=>void;
  templates: QCTemplate[];
  areas: { id: string; name: string }[];
  getState: () => QCState;
  create: (template: QCTemplate, subject: QCSubject, date: string, department: string, samples: number) => QCInspection;
  save: (id: string, draft: Pick<QCInspection, 'time' | 'responses' | 'metadata' | 'comments'>) => void;
  submit: (id: string) => void;
  review: (id: string, decision: QCApproval['decision'], remarks: string) => void;
  reinspection: (id: string) => QCInspection;
  release: (id: string, purpose: QCRelease['purpose'], accepted?: number, rejected?: number) => void;
  reportFinding: (id: string, description: string, severity: QCNonConformance['severity']) => void;
  updateFinding: (id: string, change: Parameters<typeof updateNonConformance>[1]) => void;
  reviseTemplate: (template: QCTemplate) => void;
  assign: (id: string, userId: string) => void;
  addArea: (name: string) => void;
}
```

### src/context/QuotationsContext.tsx

#### Value — src/context/QuotationsContext.tsx:10

```typescript
interface Value { generateQuotation:(source:{customerId?:string;prospectId?:string;estimateId?:string})=>Quotation; reject:(id:string,remarks:string)=>void; saveEmailDraft:(id:string,to:string,cc:string,subject:string,message:string)=>void; quotations: Quotation[]; create: () => Quotation; edit: (draft: Quotation) => void; linkEstimate: (id: string, lineId: string, estimateId: string) => void; submit: (id: string) => void; approve: (id: string) => void; requestChanges: (id: string, remarks: string) => void; send: (id: string) => void; respond: (id: string, response: Omit<QuotationResponse, 'id' | 'revision'>) => void; revise: (id: string, duplicate?: boolean) => Quotation; convert: (id: string, customerId: string, requiredDate: string) => string }
```

### src/context/SalesOrdersContext.tsx

#### OrdersContextValue — src/context/SalesOrdersContext.tsx:6

```typescript
interface OrdersContextValue {
  orders: SalesOrder[];
  getOrders: () => SalesOrder[];
  linkFinishedProduct: (orderId: string, itemId: string, productId: string) => void;
  linkEstimate: (orderId: string, itemId: string, estimateId: string) => void;
  linkJob: (orderId: string, jobId: string) => void;
  createSalesOrder: (draft: SalesOrderDraft) => SalesOrder;
}
```

### src/lib/api.ts

#### LoginRequest — src/lib/api.ts:11

```typescript
export interface LoginRequest {
  username: string;
  password: string;
}
```

#### LoginResponse — src/lib/api.ts:16

```typescript
export interface LoginResponse {
  access: string;
  refresh: string;
  user?: {
    id: string | number;
    name?: string;
    username?: string;
    email?: string;
    role?: string;
    department?: string;
  };
}
```

### src/lib/commercialPricing.ts

#### TaxMode — src/lib/commercialPricing.ts:3

```typescript
export type TaxMode = 'inclusive' | 'exclusive';
```

#### CommercialTotals — src/lib/commercialPricing.ts:5

```typescript
export interface CommercialTotals { led?: number; ledTax?: number; subtotal: number; subtotalBeforeTax: number; discount: number; discountBeforeTax: number; taxableAmount: number; tax: number; total: number }
```

### src/lib/consumableData.ts

#### Consumable — src/lib/consumableData.ts:3

```typescript
export interface Consumable {
  id: string;
  name: string;
  category: typeof CONSUMABLE_CATEGORIES[number][0];
  unit: typeof CONSUMABLE_UNITS[number];
  openingStock: number;
  openingDate: string;
  minLevel?: number;
}
```

#### ConsumableMovement — src/lib/consumableData.ts:12

```typescript
export interface ConsumableMovement {
  id: string;
  materialId: string;
  date: string;
  type: 'IN' | 'OUT';
  quantity: number;
  reference: string;
  remarks: string;
}
```

### src/lib/customCosting.ts

#### CostCurrency — src/lib/customCosting.ts:3

```typescript
export type CostCurrency = 'USD' | 'UGX';
```

#### MaterialRecipe — src/lib/customCosting.ts:4

```typescript
export interface MaterialRecipe { id: string; materialId: string; name: string; quantity: number; unit: string; currency: CostCurrency; price: number; priceUnit: string; exchangeRate: number; percentage: number; costGroup: 'material' | 'ink' }
```

#### ProcessCost — src/lib/customCosting.ts:5

```typescript
export interface ProcessCost { stageId?: string; id: string; name: string; basis: 'per kg' | 'per piece' | 'per batch' | 'fixed'; rate: number; quantity: number; unit: string; remarks: string }
```

#### CostingInput — src/lib/customCosting.ts:6

```typescript
export interface CostingInput { led?: LEDInput; quotationId?: string; orderId: string; itemId: string; modelId: string; modelRevision: number; customer: string; product: string; specifications: string; quantity: number; unit: string; currency: CostCurrency; recipeMode: 'quantities' | 'percentages'; batchQuantity: number; batchUnit: string; materials: MaterialRecipe[]; processes: ProcessCost[]; wastePercent: number; wasteBasis: 'materials' | 'materials-and-processes'; overheads: number; additionalCosts: number; markupPercent: number; pricingMethod: 'markup' | 'gross-margin'; taxPercent: number; chargePercent: number; minimumCharge: number; taxOnCharges: boolean; validityDate: string; deliveryTerms: string; remarks: string }
```

#### CostingTotals — src/lib/customCosting.ts:7

```typescript
export interface CostingTotals { led?: LEDSnapshot; materials: { id: string; quantity: number; unit: string; mixingPercent: number | null; convertedUnitCost: number; total: number }[]; materialCost: number; inkCost: number; processCosts: number[]; processCost: number; wasteCost: number; costOfProduction: number; profit: number; sellingBeforeTax: number; charges: number; tax: number; grandTotal: number; unitSellingPrice: number }
```

#### EstimateStatus — src/lib/customCosting.ts:8

```typescript
export type EstimateStatus = 'Draft' | 'Pending Review' | 'Approved' | 'Revision Required' | 'Superseded';
```

#### CostEstimate — src/lib/customCosting.ts:9

```typescript
export interface CostEstimate { salesOrderReferences?: { orderId: string; itemId: string }[]; id: string; number: string; revision: number; previousId?: string; usedByJobCardId?: string; status: EstimateStatus; customerAcceptance: 'Pending' | 'Accepted' | 'Rejected'; input: CostingInput; totals: CostingTotals; createdAt: string; generatedAt?: string; approvedBy?: string; approvedAt?: string; reviewReason?: string }
```

### src/lib/finishedGoodsData.ts

#### FinishedCategory — src/lib/finishedGoodsData.ts:3

```typescript
export type FinishedCategory = 'carrier-bags' | 'flat-bags' | 'packing';
```

#### FinishedGood — src/lib/finishedGoodsData.ts:7

```typescript
export interface FinishedGood {
  id: string;
  category: FinishedCategory;
  subgroup: string;
  customer: string;
  itemDetails: string;
  size: string;
  brand: string;
  packingSize: string;
  pieces?: number | null; // Optional pieces per package; never converts ledger quantities.
  unit: string;
  openingStock: number | null;
  openingDate: string;
  sourceSheet: string;
  sourceRow: number;
  sourceCustomer: string;
  customerInherited: boolean;
  sourceUnit: string;
  sourceClosingStock: number | null;
  dataNotes: string[];
}
```

#### FinishedGoodsMovement — src/lib/finishedGoodsData.ts:28

```typescript
export interface FinishedGoodsMovement {
  quantitySnapshot?: import('./stockIntelligence').QuantitySnapshot;
  movementPurpose?: 'sale' | 'transfer' | 'waste' | 'adjustment' | 'receipt';
  id: string;
  productId: string;
  date: string;
  type: 'IN' | 'OUT';
  quantity: number;
  unit: string;
  customer?: string;
  reference?: string;
  remarks?: string;
  salesOrderId?: string;
  salesOrderItemId?: string;
  jobCardId?: string;
  manufacturingItemId?: string;
  qualityReleaseId?: string;
  stockApprovalId?: string;
  modelId?: string;
  modelName?: string;
  batch?: string;
  dispatchId?: string;
  reversalOf?: string;
}
```

### src/lib/fulfillment.ts

#### Allocation — src/lib/fulfillment.ts:3

```typescript
export interface Allocation { id: string; orderId: string; itemId: string; productId: string; batch: string; quantity: number; dispatched: number; released: boolean }
```

#### Dispatch — src/lib/fulfillment.ts:4

```typescript
export interface Dispatch { modelId?: string; modelName?: string; id: string; number: string; allocationId: string; orderId: string; itemId: string; productId: string; batch: string; quantity: number; unit: string; date: string; challan: string; destination: string; vehicle: string; remarks: string; status: 'Confirmed' | 'Cancelled' }
```

#### FulfillmentLedger — src/lib/fulfillment.ts:5

```typescript
export interface FulfillmentLedger { movements: FinishedGoodsMovement[]; allocations: Allocation[]; dispatches: Dispatch[] }
```

### src/lib/invoices.ts

#### Invoice — src/lib/invoices.ts:4

```typescript
export interface Invoice { led?: number; taxMode?: 'inclusive' | 'exclusive'; quotationDiscount?: number; roundingAdjustment?: number; id: string; number: string; orderId: string; orderNumber: string; date: string; dispatchIds: string[]; dispatchNumbers?: string[]; seller: string; sellerAddress: string; sellerTax: string; email: string; contact: string; buyer: string; billingAddress: string; deliveryAddress: string; buyerTax: string; po: string; paymentTerms: string; destination: string; challans: string; currency: string; discount: number; taxRate: number; subtotal: number; tax: number; total: number; fiscalNumber?: string; verificationCode?: string; items: { itemId: string; description: string; quantity: number; unit: string; rate: number; amount: number; ledSnapshot?: import('./led').LEDSnapshot }[] }
```

#### InvoiceDraft — src/lib/invoices.ts:5

```typescript
export type InvoiceDraft = Omit<Invoice, 'id' | 'orderId' | 'orderNumber' | 'buyer' | 'po' | 'challans' | 'items' | 'subtotal' | 'tax' | 'total'>;
```

### src/lib/jobCards.ts

#### JobFilters — src/lib/jobCards.ts:51

```typescript
export interface JobFilters { query: string; status: string; department: string; stage: string; from: string; to: string }
```

#### StageUpdate — src/lib/jobCards.ts:97

```typescript
export type StageUpdate = Pick<JobProductionStage, 'inputQuantity' | 'outputQuantity' | 'wasteQuantity' | 'inputUnit' | 'outputUnit' | 'wasteUnit' | 'status' | 'startedAt' | 'completedAt' | 'operator' | 'remarks' | 'wasteType' | 'wasteReason' | 'sentToRecycling'>;
```

#### StockReceiptOptions — src/lib/jobCards.ts:149

```typescript
export interface StockReceiptOptions { id: string; batch: string; rejected: number; qcVerified: boolean }
```

### src/lib/led.ts

#### LEDInput — src/lib/led.ts:5

```typescript
export interface LEDInput { applies: boolean; percentageBase?: 'net-selling' | 'production-cost'; eligibleWeightKG: number | null; usdToUGX?: number; fxDate?: string; vatOnLED: boolean; conversion?: { productId: string; modelId?: string; originalQuantity: number; originalUnit: string; convertedKG: number | null; conversionId?: string; conversionVersion?: number } }
```

#### LEDSnapshot — src/lib/led.ts:6

```typescript
export interface LEDSnapshot { method: 'higher'; percentageBase: NonNullable<LEDInput['percentageBase']>; baseAmount: number; eligibleWeightKG: number; percentageRate: number; usdPerTonne: number; usdToUGX: number; fxDate: string; percentageAmount: number; weightAmount: number; selectedUnrounded: number; selectedAmount: number; selected: 'percentage' | 'weight' | 'equal'; vatOnLED: boolean; conversion?: LEDInput['conversion'] }
```

### src/lib/productionRuns.ts

#### ProductionRun — src/lib/productionRuns.ts:4

```typescript
export type ProductionRun = NonNullable<JobCard['productionRuns']>[number];
```

### src/lib/quality.ts

#### QCCategory — src/lib/quality.ts:4

```typescript
export type QCCategory = 'raw' | 'production' | 'machine' | 'cleaning' | 'safety';
```

#### ResponseType — src/lib/quality.ts:5

```typescript
export type ResponseType = 'yes_no' | 'ok_not_ok' | 'tick_cross' | 'pass_fail' | 'numeric' | 'text';
```

#### QCStatus — src/lib/quality.ts:6

```typescript
export type QCStatus = 'Draft' | 'Submitted' | 'Passed' | 'Failed' | 'Reinspection Required' | 'Approved/Released' | 'Conditionally Accepted';
```

#### QCItem — src/lib/quality.ts:7

```typescript
export interface QCItem { id: string; label: string; type: ResponseType; acceptable?: string; required: boolean; allowNA: boolean; remarksRequired?: boolean; measurementUnit?: string }
```

#### QCTemplate — src/lib/quality.ts:8

```typescript
export interface QCTemplate { id: string; name: string; documentCode?: string; revision: number; effectiveDate: string; department: string; category: QCCategory; frequency: typeof QC_FREQUENCIES[number]; applicable: string; active: boolean; approvalRequired: boolean; items: QCItem[]; source: string }
```

#### QCResponse — src/lib/quality.ts:9

```typescript
export interface QCResponse { itemId: string; sample: number; value: string; remarks: string; target?: number; lowerTolerance?: number; upperTolerance?: number; unit?: string }
```

#### QCSubject — src/lib/quality.ts:10

```typescript
export interface QCSubject { kind: QCCategory; label: string; materialId?: string; receiptId?: string; supplierId?: string; supplierName?: string; jobCardId?: string; manufacturingItemId?: string; productId?: string; modelId?: string; modelName?: string; modelRevision?: number; stageId?: string; isFinishedOutput?: boolean; batchId?: string; batchNumber?: string; machineId?: string; machineType?: string; areaId?: string; quantity?: number; unit?: string }
```

#### QCEvent — src/lib/quality.ts:11

```typescript
export interface QCEvent { id: string; type: string; at: string; userId: string; user: string; description: string }
```

#### QCApproval — src/lib/quality.ts:12

```typescript
export interface QCApproval { id: string; decision: 'Passed' | 'Failed' | 'Reinspection Required' | 'Conditionally Accepted'; userId: string; user: string; at: string; remarks: string }
```

#### QCInspection — src/lib/quality.ts:13

```typescript
export interface QCInspection { scheduleKey?: string; id: string; number: string; template: QCTemplate; subject: QCSubject; date: string; time: string; department: string; inspectorId: string; inspector: string; assignedTo: string; sampleCount: number; responses: QCResponse[]; metadata: Record<string, string>; comments: string; status: QCStatus; result?: 'Pass' | 'Fail'; previousInspectionId?: string; approvals: QCApproval[]; events: QCEvent[] }
```

#### QCRelease — src/lib/quality.ts:14

```typescript
export interface QCRelease { id: string; requestId: string; inspectionId: string; subject: QCSubject; purpose: 'quality' | 'finished_stock'; acceptedQuantity?: number; rejectedQuantity?: number; unit?: string; userId: string; user: string; at: string }
```

#### QCNonConformance — src/lib/quality.ts:15

```typescript
export interface QCNonConformance { id: string; number: string; inspectionId: string; description: string; severity: 'Minor' | 'Major' | 'Critical'; quantityAffected?: number; unit?: string; department: string; assignedTo: string; immediateAction: string; correctiveAction: string; dueDate: string; verification: string; status: 'Open' | 'Assigned' | 'In Progress' | 'Awaiting Verification' | 'Closed'; events: QCEvent[] }
```

#### QCState — src/lib/quality.ts:16

```typescript
export interface QCState { inspections: QCInspection[]; releases: QCRelease[]; nonConformances: QCNonConformance[] }
```

### src/lib/qualitySchedule.ts

#### QCSchedule — src/lib/qualitySchedule.ts:4

```typescript
export interface QCSchedule { id:string; templateId:string; subject:QCSubject; frequency:QCTemplate['frequency']; startDate:string; endDate?:string; shift?:string; assignedTo:string; department:string; active:boolean; createdBy:string; createdAt:string }
```

### src/lib/quotationReview.ts

#### QuotationEmailDraft — src/lib/quotationReview.ts:3

```typescript
export interface QuotationEmailDraft { id:string; recipient:string; cc:string; subject:string; message:string; quotationNumber:string; revision:number; attachment:string; status:'Draft — not sent'; createdBy:string; createdAt:string }
```

### src/lib/quotations.ts

#### BankAccount — src/lib/quotations.ts:6

```typescript
export interface BankAccount { id: string; bank: string; accountName: string; accountNumber: string; currency: string; branch: string }
```

#### CompanySettings — src/lib/quotations.ts:7

```typescript
export interface CompanySettings { tradingName: string; legalName: string; logo: string; address: string; telephone: string; email: string; tin: string; signatory: string; banks: BankAccount[]; currency: string; taxRate: number; taxMode: TaxMode; validityDays: number }
```

#### QuotationCustomer — src/lib/quotations.ts:8

```typescript
export interface QuotationCustomer { customerId?: string; prospectId?: string; name: string; billingAddress: string; deliveryAddress: string; contactPerson: string; telephone: string; email: string; customerType: CustomerType; tin: string }
```

#### QuotationTerms — src/lib/quotations.ts:9

```typescript
export interface QuotationTerms { name?: string; priceValidity: string; deliveryPeriod: string; paymentTerms: string; advancePercent?: number; creditDays?: number; revisionClause: string; quantityTolerance?: number; additionalTerms: string; remarks: string }
```

#### QuotationLine — src/lib/quotations.ts:10

```typescript
export interface QuotationLine { led?: LEDInput; ledSnapshot?: LEDSnapshot; id: string; type: 'stock' | 'custom'; productId?: string; modelId?: string; modelRevision?: number; description: string; group: string; specifications: string; quantity: number; unit: string; unitPrice: number; estimateId?: string; estimateRevision?: number }
```

#### QuotationStatus — src/lib/quotations.ts:11

```typescript
export type QuotationStatus = 'Internally Rejected' | 'Revision Requested' | 'Draft' | 'Pending Internal Approval' | 'Approved' | 'Sent' | 'Accepted' | 'Rejected' | 'Expired' | 'Converted to Sales Order' | 'Superseded';
```

#### QuotationEvent — src/lib/quotations.ts:12

```typescript
export interface QuotationEvent { id: string; at: string; user: string; userId: string; type: string; description: string }
```

#### QuotationResponse — src/lib/quotations.ts:13

```typescript
export interface QuotationResponse { id: string; response: 'Accepted' | 'Rejected' | 'Revision Requested' | 'Pending'; date: string; respondedBy: string; remarks: string; reference: string; revision: number }
```

#### Quotation — src/lib/quotations.ts:14

```typescript
export interface Quotation { generationKey?: string; emailDrafts?: import('./quotationReview').QuotationEmailDraft[]; id: string; rootId: string; number: string; revision: number; previousId?: string; documentType: 'Sales Quotation' | 'Proforma Invoice'; date: string; validityDays: number; validUntil: string; deliveryDays?: number; currency: string; taxRate: number; taxMode: TaxMode; discount: number; customer: QuotationCustomer; company: CompanySettings; terms: QuotationTerms; salesRepresentative: string; lines: QuotationLine[]; status: QuotationStatus; createdBy: string; createdById: string; approval?: { id: string; user: string; userId: string; at: string; totals: CommercialTotals; roundingPolicy: string }; responses: QuotationResponse[]; events: QuotationEvent[]; salesOrderId?: string }
```

### src/lib/rawMaterialData.ts

#### RawCategory — src/lib/rawMaterialData.ts:4

```typescript
export type RawCategory = 'virgin' | 'recycled' | 'ink';
```

#### RawMaterial — src/lib/rawMaterialData.ts:8

```typescript
export interface RawMaterial {
  id: string;
  name: string;
  family: string;
  category: RawCategory;
  unit: string;
  openingStock: number | null;
  openingDate: string;
  minLevel?: number;
  sourceRow?: number;
  sourceClosingStock?: number | null;
}
```

#### RawMaterialMovement — src/lib/rawMaterialData.ts:20

```typescript
export interface RawMaterialMovement {
  id: string;
  date: string;
  materialId: string;
  materialName: string;
  category: RawCategory;
  movementType: 'IN' | 'OUT';
  quantity: number;
  unit: string;
  reference: string;
  remarks: string;
}
```

### src/lib/salesOrders.ts

#### SalesOrderDraft — src/lib/salesOrders.ts:5

```typescript
export interface SalesOrderDraft extends Pick<SalesOrder, 'quotationId' | 'quotationRevisionId' | 'quotationNumber' | 'quotationRevision' | 'prospectId' | 'customerContact' | 'commercialTerms' | 'commercialPricing'> {
  taxRate?: number;
  currency?: string;
  customerId?: string;
  customerName: string;
  date: string;
  marketingPersonName: string;
  customerType: CustomerType | '';
  requisitionOrder: string;
  items: SalesOrderItem[];
}
```

### src/lib/stockData.ts

#### Category — src/lib/stockData.ts:1

```typescript
export type Category = "raw" | "finished" | "granules";
```

#### Direction — src/lib/stockData.ts:2

```typescript
export type Direction = "in" | "out";
```

#### ItemMaster — src/lib/stockData.ts:4

```typescript
interface ItemMaster {
  category: Category;
  unit: string;
  minLevel?: number;
}
```

#### Movement — src/lib/stockData.ts:12

```typescript
export interface Movement {
  id: string;
  date: string; // YYYY-MM-DD
  category: Category;
  item: string;
  model?: string; // finished goods only
  type: Direction;
  qty: number;
  ref: string; // Supplier bill, Job Card, Sales Order, recycling batch or granules sale
  party: string;
  price?: number; // inward raw material only, per unit
  currency?: "INR" | "USD";
  rate?: number; // USD to INR rate entered at purchase
}
```

### src/lib/stockIntelligence.ts

#### ProductConversion — src/lib/stockIntelligence.ts:5

```typescript
export interface ProductConversion { id: string; productId: string; modelId?: string; unit: string; piecesPerCTR?: number; kgPerCTR: number; version: number; effectiveDate: string }
```

#### QuantitySnapshot — src/lib/stockIntelligence.ts:6

```typescript
export interface QuantitySnapshot { originalQuantity: number; originalUnit: string; convertedKG: number | null; conversionId?: string; conversionVersion?: number; productId: string; modelId?: string }
```

#### StockThreshold — src/lib/stockIntelligence.ts:34

```typescript
export interface StockThreshold { productId: string; unit: string; minimum: number; critical: number; reorder: number; target: number; leadDays?: number; windowDays: number; highConsumption?: number; rapidDaily?: number; replenishmentDue?: string; replenishmentQuantity?: number }
```

#### LEDMode — src/lib/stockIntelligence.ts:55

```typescript
export type LEDMode = 'percentage' | 'weight' | 'higher' | 'lower';
```

#### PricePolicy — src/lib/stockIntelligence.ts:56

```typescript
export interface PricePolicy { vatRate: number; vatMode: 'inclusive' | 'exclusive'; ledApplies: boolean; ledMode: LEDMode; selectionConfirmed: boolean; ledRate: number; usdPer1000KG: number; usdToUGX?: number; fxDate?: string; percentageBase: 'net-selling' | 'production-cost'; vatOnLED: boolean; profitMethod: 'markup' | 'gross-margin'; profitPercent: number }
```

#### StockPriceSnapshot — src/lib/stockIntelligence.ts:78

```typescript
export interface StockPriceSnapshot { id: string; productId: string; modelId?: string; batch: string; revision: number; date: string; quantity: number; unit: string; amount: number; conversion: QuantitySnapshot; policy: PricePolicy; breakdown: ReturnType<typeof sellingCostBreakdown>; actualCOP?: number; actualReference?: string; actor: string; createdAt: string }
```

### src/pages/Costing/CostingPage.tsx

#### View — src/pages/Costing/CostingPage.tsx:10

```typescript
type View = "costing" | "rates" | "custom";
```

#### Currency — src/pages/Costing/CostingPage.tsx:11

```typescript
type Currency = "USD" | "NGN" | "GHS" | "ZAR";
```

### src/pages/JobCards/JobCardDetail.tsx

#### Tab — src/pages/JobCards/JobCardDetail.tsx:24

```typescript
type Tab = typeof allTabs[number];
```

### src/pages/Masters/MastersPage.tsx

#### MasterKey — src/pages/Masters/MastersPage.tsx:10

```typescript
type MasterKey = "items" | "models" | "customers" | "suppliers" | "departments" | "users";
```

#### MasterData — src/pages/Masters/MastersPage.tsx:11

```typescript
type MasterData = Item | Model | Customer | Supplier | Department | MasterUser;
```

#### MasterConfig — src/pages/Masters/MastersPage.tsx:13

```typescript
interface MasterConfig {
  label: string;
  columns: MasterColumn[];
  rows: MasterData[];
}
```

### src/pages/Masters/MasterTable.tsx

#### MasterRow — src/pages/Masters/MasterTable.tsx:7

```typescript
export type MasterRow = { id: string };
```

#### MasterColumn — src/pages/Masters/MasterTable.tsx:8

```typescript
export type MasterColumn = { key: string; label: string; kind?: "text" | "stages" };
```

#### MasterTableProps — src/pages/Masters/MasterTable.tsx:10

```typescript
interface MasterTableProps<T extends MasterRow> {
  title: string;
  columns: MasterColumn[];
  rows: T[];
  onAdd: (row: T) => void;
  onEdit: (row: T) => void;
}
```

#### FormValue — src/pages/Masters/MasterTable.tsx:18

```typescript
type FormValue = string | Stage[];
```

### src/pages/RawMaterials/RawMaterialPage.tsx

#### View — src/pages/RawMaterials/RawMaterialPage.tsx:12

```typescript
type View = 'levels' | 'movements' | 'report';
```

### src/pages/Recycling/RecyclingPage.tsx

#### View — src/pages/Recycling/RecyclingPage.tsx:10

```typescript
type View = "waste" | "granules";
```

### src/pages/SalesOrders/SalesOrderList.tsx

#### SortKey — src/pages/SalesOrders/SalesOrderList.tsx:18

```typescript
type SortKey = "newest" | "oldest" | "customer" | "jobcards";
```

### src/pages/Stocks/stocks.tsx

#### Tab — src/pages/Stocks/stocks.tsx:16

```typescript
type Tab = 'levels' | 'movements' | 'report';
```

#### CategoryFilter — src/pages/Stocks/stocks.tsx:17

```typescript
type CategoryFilter = FinishedCategory | 'all';
```

### src/types/index.ts

#### Role — src/types/index.ts:1

```typescript
export type Role =
  | "qc_inspector"
  | "qc_supervisor"
  | "receptionist"
  | "production_manager"
  | "store_keeper"
  | "production_operator"
  | "recycling_operator"
  | "accounts"
  | "admin";
```

#### Stage — src/types/index.ts:12

```typescript
export type Stage = "Extrusion" | "Printing" | "Packaging" | "Stock" | "Ready to Sale";
```

#### JobCardStatus — src/types/index.ts:14

```typescript
export type JobCardStatus =
  | "Draft"
  | "PendingApproval"
  | "Approved"
  | "Issued"
  | "InProduction"
  | "StoreIssuePending"
  | "MaterialIssued"
  | "OnHold"
  | "ReadyForStock"
  | "Completed";
```

#### User — src/types/index.ts:26

```typescript
export interface User {
  id: string;
  name: string;
  role: Role;
  department?: string;
}
```

#### CustomerType — src/types/index.ts:33

```typescript
export type CustomerType = "B2B" | "B2C";
```

#### SalesOrderItem — src/types/index.ts:34

```typescript
export interface SalesOrderItem {
  led?: import('@/lib/led').LEDInput;
  ledSnapshot?: import('@/lib/led').LEDSnapshot;
  quotationLineId?: string;
  quotationCostEstimateId?: string;
  quotationCostEstimateRevision?: number;
  id: string;
  modelId?: string;
  modelRevision?: number;
  specifications?: string;
  requiredDate?: string;
  estimateId?: string;
  fulfillmentSource?: "stock" | "manufacturing";
  itemId?: string;
  itemName: string;
  quantity: number;
  unit: string;
  unitPrice: number;
  totalPrice: number;
}
```

#### SalesOrder — src/types/index.ts:55

```typescript
export interface SalesOrder {
  quotationId?: string;
  quotationRevisionId?: string;
  quotationNumber?: string;
  quotationRevision?: number;
  prospectId?: string;
  customerContact?: import('@/lib/quotations').QuotationCustomer;
  commercialTerms?: import('@/lib/quotations').QuotationTerms;
  commercialPricing?: { taxMode: import('@/lib/commercialPricing').TaxMode; discount: number; roundingPolicy: string };

  taxRate?: number;
  currency?: string;
  customerId?: string;
  marketingPersonName?: string;
  customerType?: CustomerType;
  requisitionOrder?: string;
  items?: SalesOrderItem[];
  orderTotal?: number;
  id: string;
  orderNumber: string;
  customerName: string;
  date: string;
  status: "Open" | "Completed" | "Draft" | "Approved" | "Reserved" | "In Production" | "Ready for Stock" | "Stock Received" | "Partially Dispatched" | "Dispatched" | "Cancelled";
  jobCardIds: string[];
}
```

#### JobCardStageEntry — src/types/index.ts:81

```typescript
export interface JobCardStageEntry {
  stage: Stage;
  sequenceOrder: number;
  required: boolean;
  status: "Pending" | "InProgress" | "Complete";
}
```

#### JobCard — src/types/index.ts:88

```typescript
export interface JobCard {
  productionRuns?: { completesStage?: boolean; id: string; number: string; stageId: string; inputKG?: number; inputQuantity: number; outputQuantity: number; wasteQuantity: number; inputUnit: string; outputUnit: string; wasteUnit: string; startedAt: string; completedAt: string; operator: string; remarks: string }[];
  productionBatches?: { id: string; number: string; stageId: string; quantity: number; unit: string; createdAt: string }[];
  /** Present only on new parent cards; legacy single-product records stay unchanged. */
  manufacturingItems?: JobCard[];
  parentJobCardId?: string;
  origin?: 'sales_order' | 'production_for_stock';
  id: string;
  jobCardNumber: string;
  salesOrderId: string;
  salesOrderItemId?: string;
  finishedProductId?: string;
  modelId?: string;
  modelRevision?: number;
  estimateId?: string;
  estimateRevision?: number;
  routingRevision?: number;
  routingApproved?: { revision: number; stages: JobProductionStage[]; materials: JobCardMaterial[]; approvedBy: string; approvedAt: string };
  routingApprovalHistory?: NonNullable<JobCard['routingApproved']>[];
  requirementsReviewRequired?: boolean;
  modelName: string;
  qty: number;
  status: JobCardStatus;
  department: string;
  stages: JobCardStageEntry[];
  salesOrderNumber?: string;
  customerName?: string;
  product?: string;
  specifications?: string;
  productionRequirements?: string;
  unit?: string;
  createdDate?: string;
  requiredDate?: string;
  approval?: { approvedBy: string; approvedAt: string };
  requiredMaterials?: JobCardMaterial[];
  productionStages?: JobProductionStage[];
  activityHistory?: JobCardActivity[];
  acceptedQuantity?: number;
  rejectedQuantity?: number;
  stockReceiptPending?: boolean;
  stockTransfers?: { id: string; batch: string; quantity: number; rejectedQuantity: number; date: string }[];
  stockTransfer?: { quantity: number; unit: string; batchDate: string; confirmedBy: string; confirmedAt: string; jobCardId: string; salesOrderId: string; customerName: string; modelName: string; product: string };
}
```

#### JobCardMaterial — src/types/index.ts:132

```typescript
export interface JobCardMaterial {
  id: string;
  materialId?: string;
  name: string;
  requiredQuantity: number;
  issuedQuantity: number;
  unit: string;
}
```

#### ProductionStageStatus — src/types/index.ts:140

```typescript
export type ProductionStageStatus = "Pending" | "Received" | "InProgress" | "Completed" | "OnHold";
```

#### JobProductionStage — src/types/index.ts:141

```typescript
export interface JobProductionStage {
  qcTemplateIds?: string[];
  machineId?: string;
  id: string;
  name: string;
  department: string;
  sequence: number;
  required: boolean;
  kind: "production" | "stock";
  legacyStage?: Stage;
  status: ProductionStageStatus;
  inputQuantity: number | null;
  outputQuantity: number | null;
  wasteQuantity: number | null;
  inputUnit: string;
  outputUnit: string;
  wasteUnit: string;
  startedAt?: string;
  completedAt?: string;
  machine?: string;
  expectedInput?: number;
  expectedOutput?: number;
  plannedWastePercent?: number;
  instructions?: string;
  operator: string;
  remarks: string;
  handover?: { quantity: number; unit: string; fromStageId: string };
  wasteType?: string;
  wasteReason?: string;
  sentToRecycling?: number;
}
```

#### JobCardActivity — src/types/index.ts:172

```typescript
export interface JobCardActivity {
  jobCardId?: string;
  manufacturingItemId?: string;
  id: string;
  timestamp: string;
  action: string;
  user: string;
  department: string;
  description: string;
}
```

#### TraceResult — src/types/index.ts:183

```typescript
export interface TraceResult {
  traceId: string;
  type: "SalesOrder" | "JobCard" | "MaterialBatch" | "GranulesBatch";
  currentStatus: string;
  currentStage?: Stage;
  history: { label: string; timestamp: string }[];
}
```

#### WasteEntry — src/types/index.ts:191

```typescript
export interface WasteEntry {
  id: string;
  jobCardNumber: string;
  stage: Stage;
  wasteQty: number;
  unit: "kg";
  wasteType: string;
  sentToRecycling: boolean;
  date: string;
}
```

#### GranulesBatch — src/types/index.ts:202

```typescript
export interface GranulesBatch {
  id: string;
  batchNumber: string;
  date: string;
  inputWasteQty: number;
  granulesProducedKg: number;
  destination: "Restocked as raw material" | "Sold externally" | "Partially sold";
  reEnteredQty?: number;
  soldQty?: number;
  soldTo?: string;
}
```

#### CostingRecord — src/types/index.ts:214

```typescript
export interface CostingRecord {
  id: string;
  itemOrModel: string;
  rawMaterialCost: number;
  productionCost: number;
  otherCost: number;
  currency: "USD" | "NGN" | "GHS" | "ZAR";
  exchangeRateUsed: number;
  totalCostLocal: number;
  lastUpdated: string;
}
```

#### ExchangeRate — src/types/index.ts:226

```typescript
export interface ExchangeRate {
  id: string;
  currency: string;
  rate: number;
  date: string;
  enteredBy: string;
}
```

#### Item — src/types/index.ts:234

```typescript
export interface Item {
  id: string;
  name: string;
  unit: string;
  category: string;
}
```

#### Model — src/types/index.ts:241

```typescript
export interface Model {
  id: string;
  name: string;
  revision?: number;
  category?: string;
  description?: string;
  specifications?: string;
  dimensions?: string;
  defaultUnit?: string;
  recipe?: import('@/lib/customCosting').MaterialRecipe[];
  recipeMode?: 'quantities' | 'percentages';
  batchQuantity?: number;
  batchUnit?: string;
  processes?: import('@/lib/customCosting').ProcessCost[];
  routing?: JobProductionStage[];
  wastePercent?: number;
  overheads?: number;
  costingConfig?: { currency: 'USD' | 'UGX'; markupPercent: number; taxPercent: number };
  billOfMaterials: string;
  stages: Stage[];
}
```

#### Customer — src/types/index.ts:263

```typescript
export interface Customer {
  prospectId?: string;
  billingAddress?: string;
  deliveryAddress?: string;
  email?: string;
  tin?: string;
  customerType?: CustomerType;
  id: string;
  name: string;
  contactPerson: string;
  phone: string;
}
```

#### Supplier — src/types/index.ts:276

```typescript
export interface Supplier {
  id: string;
  name: string;
  materialSupplied: string;
  phone: string;
}
```

#### Department — src/types/index.ts:283

```typescript
export interface Department {
  id: string;
  name: string;
  assignedProductionManager: string;
}
```

#### MasterUser — src/types/index.ts:289

```typescript
export interface MasterUser {
  id: string;
  name: string;
  email: string;
  role: Role;
  department?: string;
}
```
