# Backend readiness report

15 October 2026. Documentation-only source audit of the current uncommitted frontend, not an operational certification. No backend code, migrations, dependencies or application functionality changed. The exact source/type/action/function evidence is preserved in the other seven planning documents. Existing working-tree changes were left intact.

## Verdict

**Ready to begin backend foundation: yes. Ready for production domain posting or SOP compliance signoff: no.** The React application has substantial connected session workflows with tested pure business rules, but no verified durable backend. Foundation/auth/audit/permissions/error/versioning infrastructure and approved master design can start immediately. Stock/production/QC/financial implementation must resolve the listed source and policy gaps and enforce atomic server transitions.

## Architecture and modules

React18/TypeScript/Vite/Router/Tailwind/Axios, Context/useState/useRef, browser form/filter state. Auth tokens alone persist in localStorage; business state resets on refresh. Capacitor packages/script exist, configuration/native project absent. Versioned entities are still session snapshots, not durable history.

Modules actually routed: operations/finance/QC role dashboards and logins; Sales Orders list/new/detail with embedded dispatch/invoice; parent/item Job Cards; Finished Goods Stock; Raw Materials; Consumables; Recycling read views; legacy/custom/stock Costing; connected and legacy Track & Trace; Masters; QC sections/detail/templates/schedules/reports/NC; Quotations list/settings/edit/detail/print/email drafts. Full exact route inventory/status is in [architecture](FRONTEND_ARCHITECTURE_AUDIT.md). Procurement, maintenance work orders, payment/expenses and full recycling execution are missing.

Major entities: customers/prospects/master variants/materials/units/models and revisions; orders/lines; quote families/revisions/lines/responses; estimate revisions/recipes/processes/FX/LED/conversions; parent jobs/manufacturing children/routes/requirements/runs/output lots; QC templates/answers/reviews/releases/NC/schedules; stock movements/allocations/dispatches/invoices. Field-by-field declarations, defaults/validation/naming bridge are in [models](FRONTEND_DATA_MODELS.md).

## Ranked integration risks

| Severity / finding | Source evidence / implication | Remedy |
|---|---|---|
| Critical — no durable domain state | Context providers and page-local masters reset; logout leaves mounted stores; all new QC/quote/job/ledger actions local | Persist server aggregates/audit, restore sessions, clear/refetch scoped domain data on identity changes. |
| Critical — raw issue not an inventory posting | JobCardsContext.issue → issueJobMaterials increases issuedQuantity, explicitly inventory unchanged | Decide WIP/consumption/return policy; atomic issue+ledger with batch allocation, avoid double deduction. |
| Critical — client authority cannot secure stock/QC | App.RequireAuth mainly identity/QC prefix; AppShell navigation not route permissions; InventoryContext allocation/reversal/raw and ConsumablesContext mutations lack actor checks | Server action/object permissions and locked status/hold enforcement; align UI guards. |
| Critical — cross-store updates lack ACID/concurrency | Quote.convert changes order/estimate/party/quote; transfer posts inventory while updating job; two clients share no lock | Single server transaction per command, versions, source unique keys and retry-safe idempotency. |
| Critical — source evidence/SOPs missing | 18 originals absent, QC template source says photographs unavailable; quote/order references absent | Obtain controlled evidence, approve exact policy/checklists; no compliance claim. |
| High — failed requests can look successful | CostingPage.handleLogRate adds row in finally; JobCards/read, Recycling/Costing/LegacyTrace catch to mocks | Explicit production failure states, gated demo mode, retry/error mapping, no success fallback on writes. |
| High — token/session gaps and demo exposure | AuthProvider no me/restore/refresh; interceptor 401 only removes legacy token; demo role choice explicitly possible in production when configured true | Authoritative me/refresh/logout/revocation and server roles; deployment safeguard for demo mode. |
| High — negative/unknown raw and consumable stock | InventoryContext.addRawMovement has hold check but no unconditional negative check; Consumables addMovement no stock/role guard; issue permits unknown availability in some cases | Define availability policy; enforce server batch/physical/held checks independent of advisory UI warnings. |
| High — unknown openings and multiple datasets | finishedGoodsData/rawMaterialData preserve null; raw adapter appends legacy demo granules; generic Masters Item separate from FG variant | Reviewed provenance imports; quarantine demo data; explicit ID/unit reconciliation, no name-based merge/null→0. |
| High — financial policy/currency/rounding | legacy ₦/NGN/GHS/ZAR vs new USD/UGX; JS Math.round; LED MAX fixed .025/USD70 but base unresolved | Approved currency/Decimal policy, central authoritative calculation with immutable snapshots and parity fixtures. |
| High — approval independence incomplete | QC reviewer!=inspector/NC verifier checks exist; approveJobCard/transitionEstimate/approveQuotation lack general maker-checker | SOP authority mapping, stable actor IDs, independent approval/rejection/history/escalation as applicable. |
| High — inconsistent retry and reversal enforcement | allocate/confirmDispatch return existing ID without full payload match; directDispatch/postReceipt compare conflicts; invoiced reverse blocked only in UI | Consistent request-hash idempotency, server invoice guard and allocation restoration policy. |
| High — inventory modal rejection not contained | InventoryMovementModal.submit locks, calls onSave without catch/finally | Catch provider/API errors, reset lock, show errors and preserve values for retry before real API integration. |
| High — intended flow exceeds implementation | for-stock origin exists but create/positive receipt needs order line; additional issue unavailable after production; raw returns and recycling movements missing | Explicit scoped domain tasks after policy decisions; never infer implementation from type/labels. |
| Medium — trace gaps / unproven consumption | ConnectedTrace shows issued KG, missing raw batch allocation/actual cost; legacy traces samples on failure | Join true batch→issue→run→lot→QC→FG→dispatch→customer; expose missing facts rather than inferred lineage. |
| Medium — model/route validation distributed | reviseProductModel lighter validation than calculateCost/validateRouting; stored vs derived SO statuses differ | Central server validators and explicit state projections; preserve original frontend fields through adapters. |
| Medium — report/source drift | Recycling “this month” unfiltered; legacy costing “month” count all; old docs claim no runs/no Stock IN; JobCardList stale transfer text | Correct UI labels/integration documentation when functionality is changed; filter server projections. |
| Medium — demand display uses two quantity bases | SalesOrderDemand shortage subtracts dispatched quantity but status compares available against original quantity; stored Draft filter can retain fully dispatched orders | One authoritative remaining-demand/status projection and tests for partial/fully dispatched orders. |
| Medium — quotation costing deep link does not select its tab | CostingPage initializes/switches custom view only for orderId; quotation editor links with quotationId/quotationLineId instead | Select custom tab for either supported source; currently user must choose Custom Costing & Estimates manually. |
| Medium — formats/platform not production validated | QC export XML not XLSX; print-to-PDF only; browser mobile/native not tested | Label formats precisely, validate artifacts and native capabilities if required. |
| Low — placeholder/UX gaps | AppShell notification button lacks handler; no global 404; some free-text generic fields | Explicitly mark placeholders and add real flows only when scoped. |

No reviewed evidence shows Sales Order creation deducting physical FG; do not “fix” this correct demand-only behavior. Current receipt/dispatch source checks are useful client safeguards but do not become server guarantees until persisted and transaction-tested.

## API and database direction

Versioned `/api/v1/` with source-linked CRUD and separate approve/issue/review/release/authorize/receive/dispatch/reverse/convert commands. Scoped pagination/filter/search/sort, Decimal strings, standard errors, JWT, expected versions and idempotency. Existing bare-array GETs need adapters. See [endpoint contracts](API_CONTRACT_BLUEPRINT.md).

One modular Django project: identity/core, masters/commercial, sales, costing, inventory, production, quality, fulfillment, billing, recycling read baseline and reports. Inventory owns one append-only scope-separated ledger; quality authorizes without posting; manufacturing owns routes/runs/outputs; invoices bill dispatch without moving stock. Parent/child jobs normalize recursive frontend data. Unique source keys, protected historical snapshots, locks/reversals and audited import provenance replace mutable browser arrays. See [database](BACKEND_DATABASE_BLUEPRINT.md).

## Workflow and SOP limits

Current chain is demand → model/estimate → parent/child job → PM approval → issue tracking → sequential runs/stages → QC lot/review/quality release → separate manager authorization → FG receipt → optional reservation/direct dispatch → invoice snapshot. Orders/quotes do not move stock; raw issue/recycling are not actual linked inventory consumption. Details and exact arithmetic are in [workflows](FRONTEND_WORKFLOWS.md).

No full SOP comparison can be completed without originals. The [gap analysis](SOP_FRONTEND_GAP_ANALYSIS.md) separates code facts, recorded prior decisions and unresolved evidence. Immediate client decisions: role/authority/maker-checker, openings/units/locations, WIP issue/consumption/returns, for-stock/additional issues/amendments, QC source/tolerances/disposition/final authority, LED base/applicability/FX/VAT/rounding and fiscal/payment boundaries.

## Development sequence and integration prerequisites

Evidence/decision log → foundation identity/audit → masters/import staging → ledger + QC foundation → costing + commercial → parent planning/atomic issue → production/full QC/FG/dispatch → billing/reporting and approved procurement/recycling/maintenance extensions. Costing and basic quality move earlier because real quote/job/issue flows depend on them. Full exit criteria/tests: [roadmap](BACKEND_IMPLEMENTATION_ROADMAP.md).

Before frontend integration: align guards and identity lifecycle, eliminate production mock/write success fallback, introduce response/error/Decimal adapters, catch modal failures, reconcile master IDs/units, preserve frozen document sources and derived statuses. These are identified future changes, not modifications made by this audit.

## Documentation deliverables

1. [FRONTEND_ARCHITECTURE_AUDIT.md](FRONTEND_ARCHITECTURE_AUDIT.md): structure, routes/pages/actions/data/API/auth inventory.
2. [FRONTEND_DATA_MODELS.md](FRONTEND_DATA_MODELS.md): domain mappings/defaults/validation plus all named TS declarations.
3. [FRONTEND_WORKFLOWS.md](FRONTEND_WORKFLOWS.md): current event chains, missing transactions, formulas and exact function evidence.
4. [API_CONTRACT_BLUEPRINT.md](API_CONTRACT_BLUEPRINT.md): proposed endpoints/shared schemas/permissions/validation/atomic actions.
5. [BACKEND_DATABASE_BLUEPRINT.md](BACKEND_DATABASE_BLUEPRINT.md): model fields/relations/constraints/indexes/lifecycle/ownership.
6. [SOP_FRONTEND_GAP_ANALYSIS.md](SOP_FRONTEND_GAP_ANALYSIS.md): evidence limits, gap/priority matrix and decision register.
7. [BACKEND_IMPLEMENTATION_ROADMAP.md](BACKEND_IMPLEMENTATION_ROADMAP.md): dependencies, phases, tests and validation results.
8. [BACKEND_READINESS_REPORT.md](BACKEND_READINESS_REPORT.md): verdict, ranked risks and implementation handoff.

## Exact next Codex task

“Implement only the approved backend foundation for Navapack ERP in the agreed backend directory: Django + DRF + PostgreSQL configuration, environment-based settings, health/readiness endpoints, identity/User/roles and provisional action permissions, JWT login/refresh/me/logout, structured validation errors/request IDs, audit and idempotency/versioning primitives, and focused authentication/permission tests. Read all eight backend-planning documents first, preserve the frontend working tree, and obtain the missing backend directory/deployment/tenancy decisions before dependent setup. Do not yet implement commercial, stock, production or QC business postings; do not invent SOP roles or fiscal policy. Report exact tests and configuration requirements.”

Backend directory and deployment choices are not established by this source audit; the foundation task should inspect available workspace context first. This recommendation does not authorize starting that task now.
