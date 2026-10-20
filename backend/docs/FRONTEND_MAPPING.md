# Phase 2 frontend mapping

20 October 2026. Frontend files inspected directly; no frontend files changed. Mapping
is an integration contract, not a claim the current browser calls every new endpoint.
Stable database IDs are always generated UUIDs; source IDs are retained separately and
must never be reinterpreted as UUIDs. No real company record has been created/mapped by
this implementation. Examples below are existing frontend reference/demo IDs, not seeds.

## Shared fields and identity

Every entity: frontend id -> API id (server UUID) after explicitly approved mapping;
original frontend id -> source_id with controlled source_system. Optional frontend
fields remain absent/blank or null where documented, never an invented source value.
API supplies version/created_at/updated_at/created_by/updated_by (import batch has
created_by and approved_by). Decimal strings require explicit frontend numeric conversion,
with future arithmetic preserving precision. Active -> is_active. Unit display strings
resolve to a governed Unit UUID by approved code mapping, never an implicit mass ratio.

## Customer / CustomerProspect -> masters.Customer / masters.Prospect

Source: types/index.ts, CommercialContext.tsx, customersApi.ts.

- name/code/phone/email/tin -> identical API fields (text; no name identity inference).
- contactPerson -> contact_person; billingAddress -> address; deliveryAddress -> delivery_address.
- customerType -> customer_type, optional B2B/B2C; no default customer type is inferred.
- prospectId -> reverse Prospect.linked_customer relation; do not write a client-supplied
  prospect into customer creation. Promote explicitly by persisted prospect UUID.
- linkedCustomerId -> linked_customer, read-only; promotion command accepts existing_customer_id.
- cu-1..cu-3 are mock customers; prospects currently use browser UUIDs. Neither is
  authoritative client master data. Approved source mapping uses separate source IDs.
- Existing adapter CustomerRecord.id is typed number, formats db:<id>, and only allows
  /^db:\d+$/ updates. New API uses UUIDs. It also sends creation_key in body, omits
  Idempotency-Key and If-Match, and filters active=true rather than is_active=true.
  These require a separately scoped frontend adapter update; no numeric-ID compatibility
  alias or silent unversioned update has been added. Unknown creation_key is rejected.

## Supplier / Department -> masters.Supplier / masters.Department

- Supplier id source su-1/su-2 (mock), name/phone unchanged; materialSupplied -> material_supplied
  descriptive text, not FK or proof of supply. Real codes supplied only by approved source.
- Department id source d-1..d-3 (mock), name unchanged; assignedProductionManager ->
  assigned_production_manager text snapshot. Optional API manager UUID is a separately
  verified server account association; name never assigns an account or capability.

## Item -> masters.Product; FinishedGood -> masters.ProductVariant

Generic Items i-1..i-3 are mock page-local rows, not exact FG variants. Item name/category
map unchanged; unit label -> Unit FK. No automatic Item-to-FinishedGood merge.

- FinishedGood.id (e.g. fg-b07c01e715bd) -> approved source_id, not Product UUID.
  ProductVariant.id is new stable UUID; required product FK needs explicit reviewed
  generic-product assignment. name must be explicitly supplied from approved description;
  do not treat category or customer name as identity.
- category/subgroup/customer/size/brand/pieces -> same fields; customer is display text.
- itemDetails -> item_details; packingSize -> packing_size; unit -> approved Unit UUID.
- sourceSheet/sourceRow/sourceCustomer/customerInherited/sourceUnit/dataNotes ->
  source_sheet/source_row/source_customer/customer_inherited/source_unit/data_notes.
- openingStock/openingDate/sourceClosingStock -> retained raw ImportRow evidence with
  source filename/sheet/row. No writable master quantity or inventory projection in Phase 2.
  Blank openings remain unknown; pieces is packaging metadata and never KG conversion.

## RawMaterial / Consumable -> masters.Material / masters.Consumable

- RawMaterial reference id excel-4 etc. -> approved source_id; new Material UUID returned.
  legacy-<name> granules are generated demo data and must not be approved company stock.
- name/family/category unchanged; unit label -> governed Unit UUID; minLevel -> min_level
  nullable nonnegative decimal string. Raw categories virgin/recycled/ink remain exact.
- sourceRow and sourceClosingStock/openingStock/openingDate retained in raw import evidence.
  Do not convert a missing balance to zero or classify reference rows as transactions.
- Consumable browser UUID -> approved source_id; name/category unchanged, imported/local.
  Each/Both/Litres/Kilos require distinct approved Unit mappings; Both is not silently two
  pieces. minLevel -> min_level; openingStock/openingDate retained evidence only, even
  though frontend consumable store starts with a zero default. No balances returned.

## Model -> specifications.ProductModel + ProductModelRevision

Source: types/index.ts, ModelsContext.tsx, productModels.ts, customCosting.ts,
productionRouting.ts. m-1..m-3 are model demo IDs, not approved specifications.

- id -> ProductModel source_id then UUID; revision -> server-assigned revision number.
  Revision UUID uniquely identifies history; do not use family UUID alone on future orders.
- name/category -> family metadata; name also snapshotted per revision.
- description/specifications/dimensions -> identical revision fields.
- defaultUnit/batchUnit -> default_unit/batch_unit governed Unit UUIDs;
  batchQuantity/recipeMode -> batch_quantity/recipe_mode.
- wastePercent/overheads -> waste_percent/overheads; costingConfig.currency/
  markupPercent/taxPercent -> currency/markup_percent/tax_percent. Omitted values null;
  frontend 10%/0% examples are not seeded rates. No costing calculation here.
- billOfMaterials/stages -> bill_of_materials/legacy_stages compatibility evidence.
  Legacy stages do not establish a universal executable route.
- recipe -> RecipeLine array. id -> line source_id (new line UUID returned);
  materialId -> material UUID; name -> frozen reference_snapshot material label;
  quantity/unit/currency/price/percentage -> same fields (unit UUID, decimals strings);
  priceUnit/exchangeRate/costGroup -> price_unit/exchange_rate/cost_group.
- processes -> ProcessCostLine array. id -> source_id; name/basis/rate/quantity/unit/remarks
  -> same (decimal/unit conversions above); stageId -> source_stage_id for local route
  resolution; response stage is new ModelRouteStage UUID from the same revision.
- routing -> ModelRouteStage array. id -> source_id; machineId -> machine UUID;
  department text -> explicitly approved Department UUID; machine text -> snapshot of
  verified machine reference, not an inferred lookup. name/sequence/required/kind unchanged;
  inputUnit/outputUnit/wasteUnit -> input_unit/output_unit/waste_unit UUIDs;
  expectedInput/expectedOutput/plannedWastePercent -> expected_input/expected_output/
  planned_waste_percent decimal strings; instructions/remarks unchanged;
  legacyStage -> legacy_stage; qcTemplateIds -> checkpoint_template_ids (provisional
  strings, unresolved until a later QC template foundation).
- status, actual inputQuantity/outputQuantity/wasteQuantity, operator, startedAt/
  completedAt, handover, wasteType/wasteReason/sentToRecycling are runtime stage data,
  excluded from specification writes. They require future transaction modules.

## Machine / Area -> masters.Machine / masters.Area

ModelsContext Machine id browser UUID -> approved source_id/new UUID; name/type
unchanged; department text -> explicitly approved Department UUID; active -> is_active;
optional area -> Area UUID. Empty machine store creates no seed machines.
Quality cleaning-area IDs -> approved Area source_id/new UUID; name unchanged;
optional description/department supplied only from verified source. Areas are locations
for master classification, not stock warehouses or QC release records.

## Integration gate

Future adapter must use version/ETag and stable retry headers, page through resources,
retain source-to-UUID maps, resolve active references explicitly, handle unknown stock
as unavailable rather than zero and distinguish missing masters from demo fallback.
Do not pass complete frontend objects to strict API serializers. UI role labels are not
permission grants; all role/action/object assignments remain server-managed decisions.


## Employee administration extension

Frontend MasterUser and demo User/Role labels do not create backend Employee/Role or
Master Admin authority. New Employee API uses id=employee UUID, user=authenticated User
UUID, employee_id=approved human code, name/email from User, department=Department UUID,
designation, reporting_manager=Employee UUID, is_active from User, server-only is_master_admin,
role_assignments=Membership UUID+Role UUID/code, and effective permissions. It adds profile
version/timestamps/actors plus pending access and reset request metadata. No profile or
role is auto-derived from existing mock u-/d- IDs or free-text manager names.

Future employee directory/editor, role review, account status/reset, permission visibility
and audit screens/adapters are specified in EMPLOYEE_ADMIN.md. They are not implemented
frontend components. Keep source identities distinct; use backend ETags/retry headers and
real JWT sessions. Never turn demo role labels into administration flags or client grants.


## Phase 2.1 integration preparation

The existing mapping remains authoritative for field semantics. Actual api.ts,
AuthContext.tsx, customersApi.ts and unitsApi.ts disagree with Django on base URL,
email login, plural roles, UUID DTOs, active filters and command headers. See
PHASE21_FRONTEND_CONTRACT_PLAN.md for exact corrections and browser acceptance gates.
No frontend source or mock/source identifier was changed. No real database UUID/source
mapping or approved client matrix was invented. Import reviews now expose resolved
UUID/version references and immutable history; applied_plan records the exact mapping
actually used. Future Admin UI must use governed role proposal/approval APIs.
