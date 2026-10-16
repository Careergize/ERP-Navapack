# Quotations and Proforma Invoice implementation / proposed backend contract

## Reference PDF / delivery implementation — 15 October 2026

One reference photograph is now supplied and used for the native PDF layout and editable company/bank defaults. The sibling `../Backend/quotations` app implements a focused public PDF snapshot/extraction/delivery slice, not the full proposed commercial schema below. Detail screen PDF / Email / WhatsApp opens independent unchecked delivery options; default WhatsApp recipient is +916282744675. The PDF snapshot requires explicit backend approval and configured SMTP and/or Meta Business template credentials. Real delivery was not exercised; provider transports are tested with mocks and an in-memory email attachment check. See `../Backend/quotations/README.md` for actual API contracts and limitations; older statements below that no native PDF or communications service exists are superseded for this slice only.


Updated 13 October 2026. Canonical module specification; the existing ERP report summarizes this work in sales-fulfillment.md. Frontend only: no backend, database, new endpoints or dependencies were implemented.

## Source references and dependency review

The attachment contains the written task only. The two client reference documents/photographs (NAVAPACK Sales Quotation / Proforma Invoice and NAVAPACK Sales Order) were **not supplied**, so their exact layout, document identifiers, bank/contact/TIN/signatory fields and multi-page appearance could not be verified. Layout follows the supplied written header/company/customer/items/totals/footer structure and existing Nava logo. NAVAPACK and Nova Recycling Industries Ltd are the names explicitly given in the task, stored once in editable company settings. No handwritten signature or sample product specification was copied into a reusable asset/master.

Existing implementation had multi-line Sales Orders, versioned models/estimates, public customer-estimate projection, Accounts/Admin costing approval, parent/item Job Cards, QC/stock/dispatch contexts, invoice/amount-in-words helpers, CSV exports and print styles. Costing required a Sales Order first. Customer Masters were page-local; no prospect form/store or company-settings master existed. The implementation extends these stores/helpers rather than creating fake orders, another costing engine or a second order/inventory system. Customer master state is now shared; unrelated Masters remain as before.

## Screens and roles

- `/quotations`: latest-revision list, historical revisions toggle, number/customer/date/status/creator filters, row actions, derived metrics and CSV report export.
- `/quotations/:id`: details, review/source warnings, submit/approve/request changes, Mark Sent, response records, revise/duplicate, preview/print, conversion and history.
- `/quotations/:id/edit`: draft form with document/customer/model/product/price/tax/terms fields; creation allocates a local draft then opens this screen.
- `/quotations/settings`: prospect creation, explicit promotion/linking, reusable company/bank/signatory/default-tax settings and optional terms templates.
- Existing `/costing?quotationId=<revision-id>&quotationLineId=<logical-line-id>`: the same Custom Product Costing screen, materials/process/FX/waste/markup engine and approved estimate revisions, with a quotation source.

Receptionist/Accounts/Admin create and edit drafts, submit, mark sent, record responses and revise/duplicate. Accounts/Production Manager/Admin provide internal review/approval or request changes. Receptionist/Admin converts to the existing Sales Order store. Admin edits document numbers, shared customer masters, company defaults/banks/signatory and terms templates. Receptionist/Accounts/Admin manage prospects and deliberately promote/link customers; conversion itself does not invent customer records. Production Manager may draft costing through the existing permitted costing controls but cannot silently change quotation commercial terms. These are proposed frontend role choices; future backend permissions must enforce the agreed policy. QC roles cannot access Quotations through direct routes. No new authentication service or authoritative role mapping is claimed.

## Creation and customer/company workflow

Create an empty draft, select an existing customer or prospect, supply customer contact/billing/delivery/TIN/type and a sales representative, then add exact products or custom models. Contact changes are document snapshots, not automatic master edits. Submission/approval requires an exact selected customer or prospect ID; a typed name alone cannot authorize an unlinked commercial record. New prospects use stable IDs and preserve their reference on quotations/orders. Explicit prospect promotion either links a selected existing customer ID or creates one new customer; repeated promotion returns the same linked record. Conversion requires an explicitly confirmed existing customer; it can record the selected prospect/customer relationship without duplicating a master.

Company settings store logo, trading/legal names, address/telephone/email/TIN, multiple bank accounts, signatory, currency, default VAT treatment/rate and validity days. Missing identity/bank/signatory details stay blank. Defaults UGX, inclusive pricing, 18% VAT and 14-day validity are **editable task examples**, not statutory rules or permanently confirmed policy. Delivery lead time is separate and initially unspecified. Each new quotation/revision gets a company snapshot; settings changes do not rewrite approved/sent documents. Drafts have an explicit Use Current Company Settings action. Authorized number changes affect only the current draft; prior printed numbers/history remain intact.

Terms templates are optional and initially empty. A draft deliberately selects or writes price-validity/delivery/payment clauses, advance percentage, credit days, exchange-rate/material-price revision clause, quantity tolerance, additional terms and remarks. No automatic 50% advance, 30-day credit or +/-10% allowance is imposed. Commercial tolerance is copied to the order but never relaxes ordered quantities, dispatch limits, production approval or invoice quantity bounds. Text clauses and numeric lead times remain explicit; conflicting text requires internal review rather than an inferred interpretation.

Existing products select exact Finished Goods variants and preserve their unit. No selling-price master is available for these imported variants; authorized draft entry supplies reviewed rates, not a guessed suggested price. Customized products select a saved model revision (or use the existing model editor), quantity/unit/specification and the existing costing screen. Descriptions/specifications can be multiline and grouped by heading. No task sample bag size or product description is treated as a universal specification. KG/cartons/pieces/rolls are never implicitly converted.

## Custom costing integration and source boundaries

`newCostingForLine` generalizes the existing `newCostingInput`; Sales Order callers still use the wrapper unchanged. Quotation-origin CostingInput has `quotationId` (stable quotation family) and logical line `itemId`; its `orderId` is empty because no order exists, **not a fake order reference**. `saveForQuotation` validates a saved draft line, customer, exact quantity/unit/model/specification and known recipe materials, then uses the existing `buildEstimateRevision` / `calculateCost` implementation. Internal recipe/process/FX/waste/markup calculations and approval rules are not duplicated.

After Accounts/Admin approves a costing revision, the quotation editor explicitly applies its public selling price. It uses `customerEstimate`'s net selling subtotal plus public charges, divided by quoted quantity; quote VAT-inclusive/exclusive treatment then applies the configured quote rate once. Costing's tax-inclusive unit price is not taxed again. Costing monetary tax/charge policies may differ from commercial quotation policy; reviewers must confirm the chosen document treatment. No implicit currency conversion occurs; approved estimate currency must equal quotation currency.

The line retains estimate ID/revision and model ID/revision. Custom prices are read-only imports; negotiated reductions can be an explicitly reviewed document discount or a new costing revision. Changed quantity/unit/specification clears the applied reference, and model/costing changes after approval block sending/conversion until quotation revision/review. Current model revision, exact costing source and approved status must match. Prior quotation prices/terms/company/acceptance snapshots remain unchanged. Historical preview is available, but stale unconverted documents cannot be sent or converted by the workflow.

Conversion binds the same approved CostEstimate to the real Sales Order line through `salesOrderReferences`, without rewriting its original quotation inputs or financial totals. `estimateMatchesOrder` lets existing Job Card creation/recalculation consume that exact adopted source. If manufacturing routing/material review later requires a costing revision, the Costing screen creates an actual-order-scoped revision of the bound series; original quotation approval/prices and source costing references remain historical. A production estimate change does not silently change accepted customer prices. Order amendments and renegotiation remain separately authorized workflows.

## Pricing, VAT and rounding snapshots

One shared `commercialPricing.ts` helper handles commercial arithmetic and reuses the existing `roundMoney` policy. Line amount = round(quantity × entered unit price, 2); preserve full stored unit-price precision instead of rounding a derived net rate prematurely. Subtotal is the sum of rounded lines. Discount is a monetary amount **in the selected unit-price basis** and cannot exceed subtotal. Each quote uses one currency and VAT rate; no mixed-currency or line-specific tax engine is implied.

- Inclusive basis: discounted inclusive amount = subtotal − discount; taxable amount = round(discounted inclusive amount / (1 + VAT%/100), 2); VAT = round(discounted inclusive amount − taxable amount, 2); grand total = discounted inclusive amount.
- Exclusive basis: taxable amount = subtotal − discount; VAT = round(taxable amount × VAT%/100, 2); grand total = round(taxable amount + VAT, 2).
- Subtotal before tax is derived in the same basis. Discount before tax is the rounded difference between pre-tax subtotal and taxable amount, keeping displayed components reconciled.
- Inclusive/exclusive choice and VAT rate are explicit; changing a draft's basis/rate requires price review/reapplication of custom prices. 0% is supported; 18% is not immutable.
- Approval freezes exact totals, line prices, tax basis/rate, currency, discount and the rounding-policy text. No later company tax setting re-prices a sent revision.

UGX words reuse the existing `amountInWords` engine with the label Uganda shillings. The frontend uses two decimal monetary values, including UGX, as an explicit existing ERP convention; client must confirm required currency precision/rounding and amount-in-words wording before production use. No tax-law certification or fiscal compliance is asserted.

## Approval, customer response and revisions

Draft → Pending Internal Approval → Approved → Sent → Accepted/Rejected → Converted to Sales Order. Pending review can request changes back to the unapproved draft. Expired is derived for unconverted Approved/Sent/Accepted revisions after valid-until. Superseded retains prior financial content and history. Draft/pending expiry needs review; sending/conversion of expired offers is blocked.

Internal approval is distinct from customer acceptance. Mark Sent records a local event only; it sends no email. Preview/printing does not send, approve, accept, create an order or stock transaction. Responses retain response type (Pending/Accepted/Rejected/Revision Requested), date, respondent, remarks, supporting reference and exact revision. Pending/revision-requested leaves the document Sent; acceptance/rejection updates status. Acceptance after expiry requires a new approved revision. Responses cannot be dated before recorded sending or in the future. Response identity/reference is entered by staff; no signed customer portal/attachment verification exists.

Approved/sent commercial content cannot be edited. Revision appends a new UUID revision under the same quotation family/logical lines, clears approvals/customer responses and uses a current company snapshot/date/validity; old content/approvals/responses stay retained with a Superseded audit event. Duplicate creates a separate family/number with new logical line IDs and clears custom costing links so another offer cannot impersonate the previous source. Converted documents cannot be revised into another order; duplication creates a separate offer. Local numbers are not authoritative sequences.

## Conversion and downstream workflow

Convert only the current internally approved, accepted, unexpired revision with valid source costing/model references. Confirm customer master identity and an actual manufacturing required date; delivery lead time does not silently invent a factory due date. `quotationConversionDraft` passes the accepted snapshot to existing `createSalesOrder` / `buildSalesOrder`.

Order fields retain quotation family/revision ID, number/revision, prospect ID, customer/contact/billing/delivery/TIN/type, sales representative, products/specifications/quantity/unit, exact approved rates, tax/discount/rounding and terms. Lines retain logical quotation line IDs and original costing ID/revision, alongside their actual order line IDs/model refs. Converted orders follow the existing new-order **Draft lifecycle**; this module does not pretend to implement the previously pending confirmed-order amendment system.

The existing order store and quotation store both guard against another order for the same quotation family. Repeated conversion returns the same order reference. Only manual order Job Card preparation triggers manufacturing; there is no automatic Job Card at quotation draft/approval/sending/conversion. Manufacturing lines enter the existing one-parent-per-order workflow; stock lines follow ordinary fulfillment. Quote operations create no inventory movement/reservation. QC quality/final-stock authorization, batch receipt and confirmed dispatch remain unchanged. The earlier reservation-free dispatch phase is still pending independently.

To avoid double VAT, converted orders preserve entered inclusive/exclusive rates rather than approximating net rates. `commercialPricing` carries tax mode/discount/rounding into the existing order builder. Direct orders without this optional snapshot keep their previous exclusive arithmetic. Existing invoice creation for converted orders uses the same basis, locks accepted VAT, prorates accepted quotation discount over confirmed billed dispatches and reconciles residual tax/total/discount on the final fully billed order. Final rounding adjustments are shown explicitly. Extra invoice discounts/tax changes on converted orders require a separate authorized adjustment workflow. Old direct-order invoice behavior remains unchanged. Neither conversion nor proforma printing posts a tax/fiscal invoice or an inventory transaction.

## Printable design and reports

Public A4 projection contains branding, title/number/revision/date/validity/delivery, company/customer/contact/billing/delivery/TIN, item/group/multiline particulars/specifications/quantity/unit/price/basis/amount, VAT totals, amount in words, selected terms/bank details and configured signatory. No material prices, recipe, margins, exchange-rate inputs, internal approval actor IDs or costing links enter this public projection. No signature image was copied. CSS hides app UI, uses A4 margins, repeats table headers and supports page flow/long descriptions. Exact reference resemblance, multi-page layout and browser PDF output still require source files and browser verification. PDF uses Print/Save as PDF, not a backend/generated-PDF service.

Quotation metrics on list/dashboard derive from latest revisions of actual session families: Draft/Pending/Accepted/Expired/Converted, latest-revision sent history and pending customer responses. Conversion rate is converted families / all current quotation families ×100; empty state is No Quotations. This denominator is a proposed KPI definition requiring client confirmation. Currency amounts are never combined into a cross-currency dashboard total. CSV report follows selected filters/revision history and guards formula-looking strings. Existing demo operations metrics remain explicitly separate; only the new quotation metrics are live session values.

## Proposed backend architecture / entities (not implemented)

Place quotation business logic in the future/planned Django **sales** app. No backend exists in this repository; this is not proof of deployed sales endpoints. Reuse authoritative Customer, CustomerProspect, Product, ProductModel, CostEstimate, SalesOrder, User and CompanySettings entities. Inventory and production remain their existing owners; quotations must not create another stock or order store. Reuse company/terms template settings through snapshots, not mutable references at print time.

New server PKs UUID; retain explicit legacy seed-ID mappings for existing frontend references. Mutable draft records have created_at/by, updated_at/by and integer version. Immutable actions add actor/timestamp/request ID and source versions. Decimal quantities/rates/amounts have explicit units/currency and agreed precision; never trust JavaScript floating-point output as authoritative accounting. Preserve referenced records/history on deletion.

### Quotation

PK UUID; unique authoritative document number (authorized draft-only changes with number history), creator User FK, customer/prospect FKs, active revision FK, optional unique converted SalesOrder FK. One conversion per quotation family. Status comes from active revision/customer response/expiry/conversion; include lifecycle, source and audit events. Receptionist/Sales creates; Accounts/authorized manager approves revisions; only configured order-creation roles convert. Draft families can revise; converted families cannot silently create a second order.

### QuotationLine

PK UUID per revision; QuotationRevision FK, stable logical line key, sequence/group/description/specifications, stock/custom type, Product or ProductModel/revision FK, decimal quantity/explicit unit and frozen public unit price/currency basis, CostEstimate FK/approved revision when custom. Unique (revision, logical line key) and sequence. Validate positive quantity, nonnegative price, exact stock unit, current approved custom source/model/currency/specification and permitted pricing adjustments. Line content is mutable only in draft and frozen at approval/sending. No implicit quantity conversions or cross-product quantities. Created/updated audit fields.

### QuotationRevision

PK UUID; Quotation FK, positive revision and previous revision FK; document type enum Sales Quotation/Proforma Invoice; dates/validity/delivery; customer/contact/company/bank/signatory/terms snapshots; currency, tax mode enum inclusive/exclusive, rate, discount basis, price/totals/rounding snapshots, status enum as above. Unique (quotation, revision). Valid-until derives from date + explicit validity; delivery lead time is separate. Approval/sent versions are immutable except append-only lifecycle/audit changes; new commercial content appends a version. Customer acceptance identifies this exact revision. Source-model/costing versions are validated at approval/sending/conversion without mutating old prices.

### QuotationApproval

PK UUID; revision FK, authorized actor FK, approve/request-changes decision, required reviewer notes where rejecting/requesting changes, server timestamp, source versions and frozen totals/policy hash. Unique action request ID. Approval is internal only; it cannot imply customer acceptance or order/stock creation. Append-only; authorization verified server-side. Resubmission of an unapproved draft preserves prior review events; changing approved content requires a new quotation revision.

### QuotationCustomerResponse

PK UUID; exact revision FK; response enum Pending/Accepted/Rejected/Revision Requested; response date, respondent/contact identity, remarks, supporting reference/evidence, recorded-by User FK and server timestamp; accepted revision FK when accepted. Unique response request ID. Acceptance must be attributable to the correct sent/current offer and date policy; printing/internal approval is not evidence of acceptance. Retain original responses and changes as separate events, never overwrite previous accepted prices/revision. Evidence upload/customer authentication is future work.

### QuotationTermsSnapshot

PK UUID; one-to-one revision FK; original optional terms-template ID/version; explicit price-validity/delivery/payment clauses, advance percentage/credit days, price-revision clause, quantity tolerance, additional terms/remarks. Validate nonnegative days and configured percent bounds, with credit/advance policy server review. Snapshot immutable with approved revision; terms templates changing later do not alter it. A tolerance cannot authorize excess dispatch/invoicing or revise order demand. Common draft audits and immutable approval reference.

## Proposed DRF contracts (not existing endpoints)

Existing authentication, server role/scope enforcement and authoritative source IDs apply. Common paging `{count,next,previous,results}` with page/page_size (default 25, max 100); filters customer_id/prospect_id, date_from/date_to, effective status, created_by, document number/type/currency, include_revisions and converted sales_order_id. Return decimals as strings and exact revision/source/policy IDs. All writes require current record/revision version (If-Match or expected_version) and unique request/idempotency key; server derives actor and timestamps.

- `GET /api/quotations/`: permission-scoped list/latest revisions with history option and related order references; report/dashboard aggregates use the same scoped records.
- `POST /api/quotations/`: create draft family/revision/lines using exact party/model/product IDs and explicit currency/tax basis/terms. Allocate number server-side; no customer/order/production/stock side effects.
- `GET /api/quotations/{id}/`: active revision, immutable version history/approval/responses, source review flags, conversion link and allowed actions. Public print projection must omit private costing data.
- `PATCH /api/quotations/{id}/`: current draft-only allowed fields; validate source identity, amounts, dates, authorized number/rate edits and expected version. Reject commercial edits after approval/sending; no generic status override.
- `POST /api/quotations/{id}/submit/`: validate complete customer/lines, approved custom costing and tax/terms, freeze submission version and append review request; no customer acceptance.
- `POST /api/quotations/{id}/approve/`: Accounts/authorized manager/Admin, exact revision/version, source dependency checks, prices/taxes/terms review and immutable approval/totals/policy snapshot. A request-changes decision returns only an unapproved pending revision to draft with notes.
- `POST /api/quotations/{id}/send/`: only a current approved, unexpired revision with valid source snapshots; append delivery reference/event. Transmission integration is separate; an actual failed send must not be recorded as success. Sending is not acceptance.
- `POST /api/quotations/{id}/record-response/`: exact sent revision/date/respondent/type/evidence and recorded actor; independently verify customer acceptance policy. Revision Requested creates a recorded request, not an overwritten offer.
- `POST /api/quotations/{id}/revise/`: lock family/current revision, append next revision and mark prior current revision Superseded with history. Validate no converted family reuse; duplicate mode creates a new family and resets approval/acceptance/source costing links appropriately.
- `POST /api/quotations/{id}/convert-to-sales-order/`: only accepted approved current unexpired/source-valid revision; confirmed customer identity and actual manufacturing due dates. Atomically create one existing SalesOrder/header/lines with exact commercial references and adopted costing links, update conversion/audit, return existing order on an exact retry. Never create a Job Card, reservation, stock move or posted invoice here.

### Example payloads and responses

Draft example (UUIDs illustrative, not actual records):

```json
{
  "request_id": "d1ec4000-0000-4000-8000-000000000001",
  "customer_id": "d1ec4000-0000-4000-8000-000000000002",
  "prospect_id": "d1ec4000-0000-4000-8000-000000000003",
  "document_type": "Proforma Invoice",
  "date": "2026-10-13", "validity_days": 14, "delivery_days": 21,
  "currency": "UGX", "tax_mode": "inclusive", "vat_rate": "18.00", "discount": "0.00",
  "lines": [{
    "logical_line_id": "d1ec4000-0000-4000-8000-000000000004",
    "type": "custom", "model_id": "d1ec4000-0000-4000-8000-000000000005",
    "model_revision": 1, "description": "Customer-specific product", "specifications": "Approved specification",
    "quantity": "500", "unit": "pcs",
    "cost_estimate_id": "d1ec4000-0000-4000-8000-000000000006", "costing_revision": 2
  }]
}
```

Response 201: `id`, document number, `revision_id`, revision/version, `status: Draft`, company/customer/terms snapshots, priced lines, computed tax/total snapshots and source review flags. Server derives/custom-validates unit price; it never accepts confidential cost inputs in a customer-facing response.

Approval/send actions include `request_id`, `revision_id`, `expected_version` and reviewer/delivery reference fields. Response example:

```json
{
  "request_id": "d1ec4000-0000-4000-8000-000000000007",
  "revision_id": "d1ec4000-0000-4000-8000-000000000008",
  "expected_version": 4,
  "response": "Accepted", "response_date": "2026-10-13",
  "responded_by": "Verified customer contact", "remarks": "Accepted this revision",
  "supporting_reference": "Customer communication reference"
}
```

Conversion payload includes request_id, accepted revision ID, expected_version, confirmed customer_id and manufacturing required dates per line. Response 201 `{quotation_id,revision_id,sales_order_id,sales_order_number,created:true}`; exact retry returns 200 with the same order and `created:false`. Same key/different payload returns 409. Validation errors 400 carry stable code and field errors (e.g. costing_revision_required, tax_basis_invalid, expired_offer, customer_link_required); 401 unauthenticated; 403 unauthorized price/approval/number/conversion scope; 404 inaccessible/missing record; 409 stale versions, invalid frozen transition or conversion conflict. No frontend fake requests target these paths.

## Transaction boundaries, failure and concurrency

1. Draft writes atomically validate identities/lines/prices/units/dates/policy and increment draft version with audit. Never link masters by name or automatically duplicate a prospect/customer.
2. Submission/approval locks current quotation/revision and source costing/model versions, computes totals once with fixed decimal rules, snapshots financial/terms/company data and appends approval. Dependency drift rejects the action or requires a new revision; it never silently re-prices a sent offer.
3. Sending/customer-response actions lock exact revision/expiry/source versions and append delivery/acceptance evidence. Internal approval/printing does not imply acceptance. Customer proof policy and actual communications need production integration.
4. Revision locks quotation family and appends unique (family, revision), preserving old content/approvals/responses. Credit/tolerance terms remain commercial, not inventory authorizations.
5. Conversion locks family/current accepted revision, customer linkage, existing order-conversion uniqueness and approved costing references. In one transaction create the existing SalesOrder/lines with original rates/basis/discount/contacts/terms and quote provenance, adopt immutable costing references, write conversion/audit and commit. Any validation/write failure rolls back order/binding/conversion changes. A unique quotation-family-to-order relation prevents simultaneous duplicate conversions even with different request keys.
6. Inventory/production operations occur later through existing authorized flows. Dispatch validates exact ordered remaining quantities regardless of quotation tolerance. Invoice pricing honours accepted inclusive/exclusive/discount snapshots without double VAT; partial/final rounding reconciliation must be transactional/decimal-safe against previous billed quantities.
7. Store idempotency payload hashes and original responses; exact retries return the original result and conflicting keys return 409. Stale client versions must reload authoritative current state. Publish any notifications after commit/outbox; retry notification delivery independently. Never claim local fallback is persisted conversion or fiscal posting.

## Open client decisions / frontend limits / verification

Supply both client reference documents for exact A4 layout/wording/company/contact/bank/TIN/signatory verification. Confirm company settings/tax basis/rate/currency precision/rounding, permitted manual prices/approval roles, validity and delivery policy, advance/credit/FX/tolerance clauses, acceptance evidence and expiry exceptions, number editing, prospect promotion and conversion-rate denominator. Confirm discount allocation/final invoice rounding and credit-note/amendment workflows for converted orders. No sample commercial clause overrides dispatch limits or the previously confirmed one-parent Job Card/QC/inventory rules.

All quotation/prospect/customer/company/terms/costing-binding mutations are session-only and reset on refresh. No durable audit, concurrent locking, real acceptance verification, authoritative document sequence, fiscal invoice certification, native PDF generator or customer communications service exists. The A4 structure follows written requirements; exact reference resemblance and interactive/multi-page printing are unverified because the source documents and accessible browser are unavailable. Browser verification was attempted for this module: the in-app browser timed out reaching localhost and Chrome was unavailable; build/helper checks do not establish visual equivalence. Existing costing/quote source checks are frontend guards; backend must independently resolve real source records and policy.

Passed commands: standalone TypeScript check, production build, `scripts/check-quotations.mjs` and all six existing check suites (quality, sales-fulfillment, job-cards, custom-costing, finished-goods, inventory-workflows), plus Git whitespace review. The quotation suite exercises multi-line/source costing, lifecycle/role separation, response/expiry/revision/company snapshots, public redaction, dependency drift, adopted order/job references, VAT/discount/UGX words and partial-invoice reconciliation. Browser validation is not claimed. Vite retains its large-bundle warning. No dependencies/backend/schema changes or automatic Git commit.

## Changed-file inventory

- `docs/ARCHITECTURE.md`
- `docs/BACKEND_TODO.md`
- `docs/BUSINESS_RULES.md`
- `docs/CHANGELOG.md`
- `docs/custom-costing-routing.md`
- `docs/DATA_MODELS.md`
- `docs/DEVELOPMENT_STATUS.md`
- `docs/quotations.md`
- `docs/sales-fulfillment.md`
- `README.md`
- `scripts/check-quotations.mjs`
- `src/App.tsx`
- `src/components/layout/AppShell.tsx`
- `src/context/CommercialContext.tsx`
- `src/context/CostingContext.tsx`
- `src/context/JobCardsContext.tsx`
- `src/context/QuotationsContext.tsx`
- `src/context/SalesOrdersContext.tsx`
- `src/index.css`
- `src/lib/commercialPricing.ts`
- `src/lib/customCosting.ts`
- `src/lib/invoices.ts`
- `src/lib/quotations.ts`
- `src/lib/salesJob.ts`
- `src/lib/salesOrders.ts`
- `src/pages/Costing/CustomCosting.tsx`
- `src/pages/Dashboard.tsx`
- `src/pages/Masters/MastersPage.tsx`
- `src/pages/Quotations/QuotationDetail.tsx`
- `src/pages/Quotations/QuotationEditor.tsx`
- `src/pages/Quotations/QuotationList.tsx`
- `src/pages/Quotations/QuotationPrint.tsx`
- `src/pages/Quotations/QuotationSettings.tsx`
- `src/pages/SalesOrders/NewSalesOrderModal.tsx`
- `src/pages/SalesOrders/SalesInvoice.tsx`
- `src/pages/SalesOrders/SalesOrderDetail.tsx`
- `src/types/index.ts`


## Receptionist/customer review and email enhancement — 15 October 2026

Generate Quotation is source-idempotent across customer/prospect/costing/workflow actions and ordinary revisions. Explicit duplicate/create remains intentional new work. Copying order-origin costing creates a new quotation-origin draft requiring existing approval/price import; no approval is cloned. Reviewer rejection and customer Revision Requested are distinct; request changes returns a pending offer to Draft, Edit and Resubmit repeats review, and View Changes compares prior commercial projection. Original accepted/converted snapshots remain.

Email interface saves recipient/CC/subject/message/exact document revision/manual PDF instructions with draft history; optional mailto only prepares the user's email app. Drafts do not change Sent/acceptance/delivery and are excluded from customer projection. No email provider/public link/customer portal was added. Backend needs expiring revocable revision-scoped safe links/access logs and authorized email templates/PDF/provider/outbox/status/retry integration. The canonical new integrity/role/source behavior is in [the integrated report](sales-fulfillment.md#quotation-generation-reviews-customer-preview-and-email).

## Client-confirmed LED MAX follow-up

Applicable quotation lines now carry the shared higher-of-2.5%-or-USD70/tonne calculation snapshot, eligible KG/product-model conversion and saved FX/date. The percentage base is still pending clarification/configurable. Custom lines import approved costing LED; stock lines explicitly apply shared LED inputs. Missing/stale weight/FX/base blocks save/approval with warnings. Base unit prices preserve VAT basis and exclude separately added LED; VAT on LED follows its own flag and is applied once. Internal views show both calculations/selected branch. Public preview includes selected charge/method without confidential cost/base/FX/source IDs. Acceptance/conversion preserves exact history; partial invoices apportion frozen original LED. [Canonical confirmed rule and boundaries](sales-fulfillment.md#client-confirmed-led-max-and-finance-demo--15-october-2026).
