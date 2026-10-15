# REST API contract blueprint

15 October 2026. **Design proposal, not implemented endpoints.** Existing HTTP expectations are exhaustively listed in [architecture](FRONTEND_ARCHITECTURE_AUDIT.md). No server was contacted to verify them. Base for new contracts: `/api/v1/`; trailing slashes retained. Existing `/api` consumers need a configured base and response adapter. Source-confirmed UI capability does not mean client-approved authorization/SOP policy.

## Common contract applied to every endpoint

All ordinary resources return server UUID `id`, `version` integer, created_at/updated_at and actor IDs as appropriate; human-readable document numbers are server-generated independently. Quantities and money travel as decimal strings, dates as ISO dates, timestamps as UTC ISO8601; explicit unit and currency mandatory. Null unknown balances remain null. Prefer snake_case API with explicit adapters from the camelCase declarations in [models](FRONTEND_DATA_MODELS.md). Never trust submitted totals, actor IDs, role, approval booleans, inventory balances or linked source snapshots.

GET list returns `{count,next,previous,results:[Resource]}`. page/page_size defaults 1/25, max100; stable ordering `-created_at,id`. `search`, allowlisted `ordering`, status and exact FK filters; dates `date_from/date_to`; never raw SQL field names. Resources support module-specific filters listed below. Detail returns Resource. POST create returns 201 Resource and Location; business actions return 200 Resource or action result with versions and transaction IDs. No hard DELETE for posted records. Draft deletion is deferred until retention policy; revision/supersede/reversal is preferred.

JWT bearer access; POST login/refresh are anonymous with rate limits. Every other request requires authenticated active user plus permission and object scope. Client role labels below are provisional least-authority mapping from actual guards, not SOP certification. QC draft edit also requires assigned user; reports must redact internal pricing from unauthorized actors. Public customer links are not included in baseline because no public frontend exists.

Mutation requires `If-Match: "version"` (or explicit expected_version where multi-source) and validates all source versions. Missing precondition 428; stale version 412 (consistently use this rather than mixing with 409). Business state/idempotency conflicts 409; invalid field data 400; unauthenticated 401; forbidden 403; inaccessible/missing object 404; request throttle 429. Standard error:

```json
{"error":{"code":"insufficient_stock","message":"Available batch stock is insufficient.","fields":{"quantity":["Exceeds available stock."]},"details":{"available":"12.000000","unit":"kg"},"request_id":"uuid"}}
```

POST business commands require `Idempotency-Key` UUID or durable source key, scoped by actor/company/action, with request hash and stored result. Same key/same payload returns original result; different payload →409. Enforce uniqueness at DB level. Never use array length/timestamp UI IDs as durable idempotency policy. Lock source order/lines, batch balances, allocations, inspections/releases and run/stage records as needed in one transaction. Write audit with old/new status, actor, request key and reason in that transaction; async notifications only after commit via outbox if later needed. Recheck QC holds under the same locks as dispatch/receipt. Failures roll back all quantity/state/audit changes.

## Schemas and permission profiles

Request/response names below refer to the exact frontend declarations preserved in the model appendix, mapped through the naming bridge. Write schemas omit id/derived totals/actor/history/version; servers populate them. `Resource` response means all authorized fields of the named model plus computed totals/status/source versions. Nested draft line creation is atomic; posted snapshots immutable.

Profiles: **read** scoped module view; **master-admin** Admin for master writes (Model draft exceptions below); **sales-edit** Receptionist/Admin orders; **quote-edit** Receptionist/Accounts/Admin; **commercial-review** Accounts/PM/Admin; **cost-edit** Receptionist/Accounts/PM/Admin, custom markup/margin Accounts/Admin; **pm** PM/Admin; **store** Store/Admin; **dispatch** Store/Admin/Receptionist from direct-dispatch code; **invoice** Accounts/Admin/Receptionist; **qc-record** Inspector/Supervisor/Admin with assignment; **qc-review** Supervisor/Admin independent inspector; **qc-final** PM/Admin after quality release. Reports follow module access; Accounts gets QC summary only. Missing/unsafe frontend guards must not be copied as unrestricted API access.

Validation profiles: **identity** existing stable FK and unit/category/currency compatibility; **draft** source validation/positive quantity/nonnegative rate/date/required business fields; **snapshot** exact immutable source revision/pricing/tax/model reference; **transition** explicit state graph and actor permission; **stock** known physical/usable/batch stock and no excess order/authorization; **qc** responses/independent review/hold/checkpoint rules; **dated** opening/receipt/authorization/chronology/backdating checks. These profiles apply in addition to per-row rules.

## Endpoint contracts

Each row specifies method/path, payload→response, permissions, validation/side effects, source/consumer and status. **P** means proposed contract justified by source; **C?** means capability boundary or policy needs client clarification before implementation. GET/POST and list/detail paths are written separately so method scope is explicit. All share the standard pagination/error/concurrency conventions above.

| Method / path under /api/v1 | Purpose, request → response | Permissions; validation; side effects | Consumer/source; status |
|---|---|---|---|
| POST auth/login/ | username,password → access,refresh,user | Anonymous credentials/rate limit; audit login, no domain writes | Login/AuthContext.login; P existing shape |
| POST auth/refresh/ | refresh → access[,rotated refresh] | Valid refresh, revocation policy; audit rotation | api interceptor replacement; P missing client flow |
| GET auth/me/ | no body → User, permissions | Active bearer; role/object scope | AuthProvider restoration; P |
| POST auth/logout/ | refresh → revoked=true | Token ownership/revocation; audit | AuthProvider.logout; P |
| GET users/; GET users/{id}/ | user search/role/department → User list/detail | Admin, scoped assignment lookup for QC/PM; redact private fields | Masters/assignment controls; P |
| POST users/; PATCH users/{id}/ | name,email,roles,department,active → User | master-admin; identity/email uniqueness, no client role escalation | MasterTable user; P policy C? |
| GET roles/ | role/capability definitions → list | Authenticated role lookup; server configured permissions | Login/User master; P |
| GET customers/; GET customers/{id}/ | search/type → Customer list/detail | read parties | CommercialContext/NewSalesOrderModal/quotations; P |
| POST customers/; PATCH customers/{id}/ | Customer business fields → Customer | master-admin, required name, duplicate/link review; audit | saveCustomer/Masters; P |
| GET prospects/; POST prospects/ | filters / name,contact,phone,email,addresses,tin,type → Prospect | quote-edit; nonblank name; create only | QuotationSettings/addProspect; P |
| POST prospects/{id}/promote/ | existing_customer_id OR explicit create_customer fields → prospect,customer | quote-edit; identity, one linked customer; atomic create/link/audit | promoteProspect; P authority C? |
| GET suppliers/; POST suppliers/; PATCH suppliers/{id}/ | Supplier business fields → Supplier/list | read/master-admin; name/identity; no purchasing side effect | MastersPage suppliers; P |
| GET departments/; POST departments/; PATCH departments/{id}/ | name,manager_id and legacy snapshot → Department | read/master-admin; validate manager assignment | MastersPage departments; P |
| GET items/; POST items/; PATCH items/{id}/ | generic Item fields → Item | read/master-admin; reconcile with FG variant master, no implicit merge | MastersPage items; C? identity mapping |
| GET finished-goods/; GET finished-goods/{id}/ | category/brand/customer/unit/model/search → FinishedGood + balance projections | inventory read; identity; unknown remains null | StockPage/NewSalesOrderModal; P |
| PATCH finished-goods/{id}/ | pieces_per_package, reviewed metadata → variant | master-admin/store metadata authority C?; positive integer; never mutate balance/opening | updateFinishedPieces; P/C? |
| GET raw-materials/; GET raw-materials/{id}/ | category/family/unit/search/status → RawMaterial + physical/held/usable | inventory read; do not sum unlike units | RawMaterialPage/material selection; P |
| GET consumables/; POST consumables/; PATCH consumables/{id}/ | Consumable writable fields → Consumable | store; identity, positive/zero opening, posted unit/opening locked | ConsumablesContext.saveItem; P permission C? |
| GET models/; GET models/{id}/revisions/ | current/search or all revisions → ModelRevision list | scoped models read | ModelsContext/ModelManager; P |
| POST models/; POST models/{id}/revisions/ | model business fields, recipe,process,route,defaults → ModelRevision | Admin/PM/Receptionist per code; exact material/unit, validate route; immutable revision | saveModel/reviseProductModel; P |
| GET machines/; POST machines/ | machine fields → Machine/list | read/master-admin; unique identity/type/department/active | ModelsProvider.addMachine/QualityTemplates/RoutingFields; P |
| GET company-settings/; POST company-settings/revisions/ | CompanySettings → frozen revision | read authorized commercial/master-admin; company/bank/tax/validity checks; no past-doc rewrite | CommercialProvider.saveSettings; P |
| GET terms-templates/; POST terms-templates/; PATCH terms-templates/{id}/ | QuotationTerms + name → terms | quote read/master-admin; percentages/credit/date clauses validated | saveTermsTemplate/TermsFields; P |
| GET sales-orders/; GET sales-orders/{id}/ | query/customer/status/date/source + ordering → Order/list | sales-read provisional; totals and fulfillment projection | SalesOrderList/Detail; P |
| POST sales-orders/ | SalesOrderDraft + stable party/source IDs → SO with lines,server number,totals | sales-edit; draft/identity/snapshot, transaction currency/tax; **demand only**, no stock | createSalesOrder/buildSalesOrder; P |
| POST sales-orders/{id}/manufacturing-items/ | line_id,model_revision,estimate_revision,required_date,specifications,manual_materials if allowed → parent,child | Receptionist/PM/Admin; complete source identity; dedup parent/line; audit links, no issue/stock | createLinked/buildLinkedJob; P |
| GET job-cards/; GET job-cards/{id}/ | status/department/stage/date/customer/order/search → parent/items/legacy adapter | job read, scoped QC view redacts costing | JobCardsProvider.load/loadDetail; P |
| PATCH job-card-items/{id}/ | draft specification/date/requirements fields → child | pm; transition/draft; linked qty/product/unit/model immutable | editJobCard/JobEditForm; P |
| PUT job-card-items/{id}/routing/ | expected_version,stages,materials → revised child | pm; preissue/unstarted, unique route sequence/IDs, units; invalidates costing and review state | saveRouting/changeRouting; P |
| POST job-card-items/{id}/reopen-routing/ | reason → draft + preserved approval history | pm; before issue/run/receipt only; audit | reviseRouting/reopenRouting; P |
| POST job-card-items/{id}/recalculate-requirements/ | approved_estimate_revision_id → material requirements | pm; exact line/model/quantity/source, approved snapshot; no physical stock | recalculate/materialRequirements; P |
| POST job-cards/{id}/submit/ | expected_version → parent/item pending review | Receptionist/PM/Admin; Draft only | sendForReview, parent facade must define scope; P/C? |
| POST job-cards/{id}/approve/ | expected_parent_version,item_versions → approved snapshot/StoreIssuePending | pm; all manufacturing lines prepared, each route/material reviewed; **all-or-none** children+audit | approve/approveJobCard/assertCompleteManufacturingScope; P |
| POST material-issues/ | job_item_id,requirement line IDs,batch allocations,qty,unit,date,reason → issue + raw OUT/WIP transactions | store; stock/draft/identity/qc/dated; atomic usable stock check and ledger posting | MaterialIssueForm/issueJobMaterials; P posting policy C? |
| GET material-issues/ | item/material/batch/date → issues list | store/pm scoped; audit/read only | Requirements/history future persistent counterpart; P |
| PATCH production-stages/{id}/ | StageUpdate + expected_version → updated execution/item | Operator/PM/Admin; transition/dated/qc, approved units, prior stages, completed lock, refuse run aggregate overwrite; handover on completion | updateStage/updateJobStage; P |
| POST production-runs/ | job_item_id + ProductionRun writable fields,completes_stage → run,stage totals,item versions | Operator/PM/Admin; identity/date/qc, no overlap, unique source key, cumulative handover cap; completion atomic | ProductionRuns/appendProductionRun; P |
| GET production-runs/ | item/stage/machine/operator/date → list | scoped production read | production timeline/trace; P |
| POST job-card-items/{id}/output-lots/ | stage_id,number,quantity,unit → immutable lot | QC/Admin; completed stage exact unit, sum<=actual output; repeated identity exact payload only | registerBatch/NewInspection; P |
| GET stock-movements/ | scope=fg/raw/consumable,product/material,batch,date,direction,source → ledger list | inventory read; separate scope/unit, actor/audit links | Stock/Raw/Consumable history; P |
| POST stock-movements/ | scope,exact entity,date,direction,qty,unit,purpose,reference,reason → transaction | Admin import IN; Store/Admin non-sales OUT, adjustments Admin; stock/dated/qc; prevent manufactured bypass; immutable posting | InventoryMovementModal/add*Movement; P policy C? |
| POST finished-receipts/ | job_item_id,output_lot_id,product_variant_id,quality_release_id,stock_authorization_id,accepted,rejected,date → receipt,movement IDs,item state | store; stock/qc/identity/dated; lock authorization totals and append IN once; prepared mappings exact | transfer/postPreparedReceipts/postReceipt; P |
| POST reservations/ | order_line_id,product_id,batch_id,quantity → Allocation | dispatch provisional; stock/order remainder; no physical stock | allocateStock/allocate; P |
| GET reservations/ | order/product/batch/active → list | fulfillment read | SalesOrderDetail/available balances; P |
| POST dispatches/ | order_line_id,batch_id,optional allocation_id,quantity,date,challan,destination,vehicle,remarks → Dispatch + OUT ID | dispatch; stock/qc/dated/order bound; physical OUT+allocation+audit atomic; reservation optional | directDispatch/dispatch/confirmDispatch; P |
| GET dispatches/; GET dispatches/{id}/ | order/batch/status/date → dispatch resources | fulfillment/invoice read | SalesOrderDetail/InvoiceForm; P |
| POST dispatches/{id}/reverse/ | reversal_date,reason → cancelled dispatch,reversal movement | store/admin provisional; not already invoiced unless explicit credit workflow; reverse allocation consistently | reverseDispatch/UI invoice guard; P policy C? |
| GET invoices/; GET invoices/{id}/ | order/customer/date/currency → Invoice/list | invoice/read finance scope | InvoiceView/FinanceDashboard; P |
| POST invoices/ | InvoiceDraft buyer/seller refs,dispatch_ids,date,number,tax settings → Invoice immutable snapshot | invoice; snapshot/dated/no duplicate billed dispatch; server recomputes original commercial rounding/LED; no stock | createInvoice/InvoiceForm; P |
| GET cost-estimates/; GET cost-estimates/{id}/ | source_kind/source_id,line,model,status → CostEstimate/list | cost-edit/scoped read; redact internals in public projection | CustomCosting/JobCosting; P |
| POST cost-estimates/; POST cost-estimates/{id}/revisions/ | CostingInput with unambiguous source → CostEstimate revision/totals | cost-edit; source exact quantity/unit/model, recipe/FX/formula validation; never auto-reprice prior docs | save/saveForQuotation/buildEstimateRevision; P |
| POST cost-estimates/{id}/submit/ | expected_version → pending | cost-edit; Draft→Pending Review | transitionEstimate; P |
| POST cost-estimates/{id}/approve/ | reason/expected_version → approved snapshot | Accounts/Admin; Pending Review, server recalculation; supersede approved series; independent maker check policy C? | setStatus; P/C? |
| POST cost-estimates/{id}/request-revision/ | reason → Revision Required | Accounts/Admin proposed stricter reviewer mapping; transition checks | CustomCosting/transitionEstimate; P |
| POST cost-estimates/{id}/generate/; POST cost-estimates/{id}/customer-response/ | validity / accepted-or-rejected + evidence → estimate/public preview | cost-edit; response only generated Approved; no quotation acceptance implication | generate/accept; P |
| GET exchange-rates/; POST exchange-rates/ | source_currency,target_currency,rate,date,source → Rate/list | Accounts/Admin; positive finite pair/date and version; no historical rewrite | legacy rates + LED/Costing; P |
| GET product-conversions/; POST product-conversions/ | ProductConversion business fields → revision/list | read / PM/Admin; exact ctn/model/effective date/positive KG ratio | saveConversion/quantitySnapshot; P |
| GET stock-thresholds/; PUT stock-thresholds/{product}/ | StockThreshold → policy/list | read / Store/PM/Admin; exact unit and ordered limits/window/date | saveThreshold/StockAlerts; P |
| GET stock-prices/; POST stock-prices/ | StockPriceSnapshot input fields/policy/evidence → immutable calculated snapshot | Accounts/Admin; server conversion+MAX+FX+reverse-price calculation; actual cost evidence | saveStockPrice/StockIntelligence; P |
| GET quotations/; GET quotations/{revision}/ | customer/date/status/creator/history/search → quotation revision/list | quote view; filtered historical state | QuotationList/Detail; P |
| POST quotations/ | draft fields / optional generation source IDs → Quotation revision | quote-edit; unique generation/source key, company snapshot, no order/stock | create/generateQuotation; P |
| PATCH quotations/{revision}/ | writable Quotation draft fields/line snapshots → draft | quote-edit, number change Admin; identity/draft, immutable family/history/creator; server recalculation | edit/QuotationEditor; P |
| POST quotations/{revision}/submit/ | expected version/source versions → pending | quote-edit; complete/exact party/model/approved costing/current validity | submitQuotation; P |
| POST quotations/{revision}/approve/ | expected/source versions → frozen totals/approval | commercial-review; Pending, current sources; no customer acceptance or stock | approveQuotation; P |
| POST quotations/{revision}/request-changes/; POST quotations/{revision}/reject/ | remarks → Draft or Internally Rejected | commercial-review; pending + nonblank reason; audit | requestChanges/rejectQuotation; P |
| POST quotations/{revision}/mark-sent/ | delivery_reference,expected_version → Sent | quote-edit; approved/unexpired/source current; records manual delivery only, no mail success | sendQuotation; P |
| POST quotations/{revision}/responses/ | QuotationResponse writable fields → response + revision state | quote-edit; sent/date window/valid respondent/evidence; accept only within validity | recordQuotationResponse; P |
| POST quotations/{revision}/revise/; POST quotations/{revision}/duplicate/ | expected_version → new revision or family | quote-edit; old immutable/superseded; copied logical IDs only on revision; copied custom price review | reviseQuotation; P |
| POST quotations/{revision}/convert/ | customer_id,required_date,expected/source versions → order_id,order,adopted estimate links | Receptionist/Admin; latest accepted approved unexpired; one order/family; all related writes atomic, no stock/job/invoice | convert/quotationConversionDraft; P |
| POST quotations/{revision}/email-drafts/ | recipient,cc,subject,message → QuotationEmailDraft | quote-edit excluding PM; valid addresses/single-line subject and approved current revision; no delivery status claim | saveEmailDraft/emailDraft; P |
| GET quotations/{revision}/customer-document/ | no body → publicQuotation safe schema | Authorized commercial viewer; whitelist projection; no internal BOM/margin/IDs beyond public references | QuotationPrint/publicQuotation; P; public link C? deferred |
| GET quality-templates/; POST quality-templates/{id}/revisions/ | QCTemplate/items → template/list | QC read / Admin write; active/latest/frequency/acceptable polarity, KSEC inactive until clarified | reviseTemplate/QualityTemplates; P |
| GET cleaning-areas/; POST cleaning-areas/ | name → area/list | QC read/Admin create; nonblank unique governed identity | addArea; P |
| GET quality-inspections/; GET quality-inspections/{id}/ | category/source/status/assignee/date/search → inspection/list | QC_VIEW_ROLES object-scope; no Accounts detailed exposure | QualityPage/InspectionDetail; P |
| POST quality-inspections/ | template_revision_id,typed source FK,date,department,sample_count → Draft | qc-record; identity/qc/exact completed stage lot or raw receipt; snapshot template | createInspection/NewInspection; P |
| PATCH quality-inspections/{id}/ | time,responses,metadata,comments → draft | assigned qc-record/Admin; Draft only, validate response keys/units | saveInspection/InspectionForm; P |
| POST quality-inspections/{id}/assign/ | assigned_to → inspection | Admin; valid active QC user, Draft only | assign; P |
| POST quality-inspections/{id}/submit/ | expected_version → Submitted,result | assigned qc-record; all answer/metadata/time/date validation; no release/stock | submitInspection; P |
| POST quality-inspections/{id}/review/ | decision,remarks → approval+inspection | independent qc-review; submitted, passing result for Pass; conditional raw held | reviewInspection; P |
| POST quality-inspections/{id}/reinspect/ | expected_version → linked new Draft | qc-record; failed/reinspection/conditional only, preserve old answers/history | reinspect; P |
| POST quality-inspections/{id}/release/ | purpose=quality → QCRelease | qc-review; independently Passed, no open NC, idempotent; no stock | releaseInspection; P |
| POST quality-inspections/{id}/authorize-stock/ | accepted_quantity,rejected_quantity,unit → final QCRelease | qc-final; final exact lot, quality released/no hold, bounded quantities; no stock | release purpose finished_stock; P authority C? |
| GET non-conformances/; POST non-conformances/ | source inspection,description,severity → finding/list | QC scoped / qc-record; submitted source, required description/severity | reportFinding/createNonConformance; P |
| POST non-conformances/{id}/actions/ | assignment,immediate/corrective action,due,verification,next_status → finding/action history | qc-review; ordered transitions, independent closure; no stock disposal implied | updateFinding/updateNonConformance; P |
| GET quality-schedules/; POST quality-schedules/ | QCSchedule writable fields/exact source → schedule/list | QC read / Supervisor/Admin; frequency/date/assignment/source constraints | DailySchedules/addSchedule; P |
| PATCH quality-schedules/{id}/ | active → schedule | Supervisor/Admin; keep source/frequency version history | toggleSchedule; P |
| POST quality-schedules/{id}/generate/ | occurrence_date,shift → inspection or original occurrence | Supervisor/Admin; scheduleDue unique schedule/date/shift AND duplicate subject occurrence check | generateScheduled; P explicit invocation only |
| GET recycling/waste/; GET recycling/granules/ | date/source/destination filters → WasteEntry/GranulesBatch list | Recycling/Admin plus scoped trace/report | RecyclingPage existing GETs; P adapter |
| GET trace/ | product_id,job_id,order_id,batch_id → lineage/events,missing facts | scoped trace, cost redaction | ConnectedTrace/operations; P |
| GET trace/lookup/{query}/ | exact allowed reference → legacy TraceResult | scoped trace; no mock fallback in production; existing `/trace/{query}/` needs adapter or retained compatibility alias | LegacyTrace.searchTrace; P compatibility |
| GET reports/inventory/; GET reports/stock-alerts/ | exact scope/unit/as_of/from/to/model → grouped balance/alert rows | inventory view; complete ledger, unknown openings explicit | Stock/raw/monthly/StockAlerts; P |
| GET reports/sales/; GET reports/operations/; GET reports/finance/ | filters/as_of/currency → grouped aggregate projections | scoped role views; no summing currencies or treating dispatch as revenue | Dashboard/SalesSummary/FinanceDashboard; P |
| GET reports/quality/; GET reports/quality-summary/ | QC filter set → detailed rows or counts | QC view detailed; Accounts summary; no hidden material costs | QualityPage/reports/FinanceQualityOverview; P |

Compound rows enumerate each stated method against its stated collection/detail path; GET list, GET detail, POST collection and PATCH detail use the common CRUD semantics. Action alternatives are separate commands with the same specified schema and status-specific result; no unrestricted generic status PATCH is proposed for approval/stock/release commands.

## Deliberately deferred resources and contracts

Do not fabricate purchase-order, payment, warehouse CRUD, maintenance records, recycling-job write, customer portal/public link/email-send, tax authority or Tally endpoints. Existing frontend read views and business goals justify investigation, but do not establish request fields, authority or posting policy. Warehouse identity is needed in the ledger schema, yet no location UI exists; choose deployment defaults with the client. Raw returns/consumption, in-production additional issues and for-stock creation require workflow clarification, then explicit action endpoints. An email outbox/PDF/customer-link service is an optional later capability, not evidence of implemented transmission.

## Concrete critical request/response example (proposed)

```http
POST /api/v1/finished-receipts/
Authorization: Bearer <access>
Idempotency-Key: <uuid>
If-Match: "7"
Content-Type: application/json
```

```json
{"job_item_id":"uuid","output_lot_id":"uuid","product_variant_id":"uuid","quality_release_id":"uuid","stock_authorization_id":"uuid","accepted_quantity":"20.000000","rejected_quantity":"1.000000","unit":"kg","date":"2026-10-15","source_versions":{"job_item":7,"stock_authorization":2}}
```

```json
{"id":"uuid","version":1,"accepted_quantity":"20.000000","rejected_quantity":"1.000000","movement_ids":["uuid"],"job_item":{"id":"uuid","version":8,"status":"ReadyForStock"},"request_id":"uuid"}
```

The quantities are illustrative contract data, not a claim about a real lot. A concurrent hold/overreceipt rejects the entire action; repeating the successful request never duplicates IN. This same atomic command pattern applies to issue, run completion, dispatch/reversal, invoice and quotation conversion.
