# Frontend architecture audit

Audit date: 15 October 2026 (Asia/Calcutta). Scope: the current working tree in `F:/WORK/Navapack-ERP/frontend`, including pre-existing uncommitted changes, rather than HEAD alone. Documentation-only audit; no application behavior, dependencies, backend or migrations changed. Paths below are relative to `frontend/`. Source inspection and existing automated checks support the findings; browser interactions and live server persistence were not tested.

## Evidence and reading order

Read this file, [models](FRONTEND_DATA_MODELS.md), [workflows](FRONTEND_WORKFLOWS.md), [API](API_CONTRACT_BLUEPRINT.md), [database](BACKEND_DATABASE_BLUEPRINT.md), [gaps](SOP_FRONTEND_GAP_ANALYSIS.md), [roadmap](BACKEND_IMPLEMENTATION_ROADMAP.md), then [readiness](BACKEND_READINESS_REPORT.md). Existing module documents remain useful design history: [fulfillment](../sales-fulfillment.md), [custom costing](../custom-costing-routing.md), [QC](../quality.md), [quotations](../quotations.md), [reference inventory](../finished-goods-reference.md). They are not SOP originals. This audit supersedes stale descriptions only where actual source proves newer behavior.

## Repository and startup

The project/Git root is `frontend/`; the containing workspace is not the application root. React 18.3, TypeScript 5.6, Vite 8.3, Router 7.18, Tailwind 3.4, Axios 1.7 and Lucide are declared dependency ranges in `package.json`, not a statement of versions installed globally. No Redux, Zustand, schema-validation library or query cache is declared. No test/lint script exists; nine standalone check scripts are present (their output includes an additional parent-card result group). `tsconfig.json` enables strict checks, ES2022, bundler resolution, noEmit, unused checks and `@/*` → `src/*`. `vite.config.ts` supplies React, port 5173, relative asset base and the same alias. `vercel.json` rewrites all paths to index.html; a future same-origin API deployment must exempt `/api/` from SPA fallback.

```text
frontend/
  package.json, tsconfig.json, vite.config.ts, vercel.json
  index.html -> src/main.tsx -> src/App.tsx
  src/types/index.ts                 shared commercial/manufacturing/master types
  src/context/                      11 domain/auth providers
  src/pages/
    Dashboard.tsx, FinanceDashboard.tsx, Login.tsx
    SalesOrders/                     list, new modal, detail, invoice
    JobCards/                        parent/item details, forms, routing, costing
    Stocks/                          finished goods + demand
    RawMaterials/, Consumables/, Recycling/, Costing/
    Quality/                         templates, inspections, findings, schedules
    Quotations/                      offers, editor, settings, print, email draft
    Masters/, TrackTrace/
  src/components/                    StockIntelligence, LEDFields, ProductionRuns,
                                     ProductionTimeline, GenerateQuotation, SalesSummary
    layout/AppShell.tsx, ui/InventoryMovementModal.tsx, ui/SearchSelect.tsx
  src/lib/
    api.ts, demoAuth.ts, mockData.ts, jobCardDemo.ts
    finishedGoodsData.ts, finishedGoodsReference.ts
    rawMaterialData.ts, rawMaterialReference.ts, stockData.ts, consumableData.ts
    salesOrders.ts, fulfillment.ts, invoices.ts, salesJob.ts, parentJobCards.ts
    jobCards.ts, productionRouting.ts, productionRuns.ts, operations.ts
    customCosting.ts, productModels.ts, led.ts, commercialPricing.ts,
    stockIntelligence.ts, quotations.ts, quotationReview.ts
    quality.ts, qualityIntegration.ts, qualityTemplates.ts, qualitySchedule.ts,
    qualityReports.ts
  scripts/check-*.mjs                 focused source/runtime invariants
  scripts/extract-*.py                reference workbook extraction
  docs/                              existing domain documentation and this audit
```

`main.tsx` mounts StrictMode → BrowserRouter → App. `App.tsx` nests Auth → SalesOrders → Models → Commercial → Quality → Inventory → Costing → Quotations → Consumables → JobCards → Invoices. AppShell renders Outlet. This order encodes dependencies: QC guards inventory, costing reads inventory conversions and models, quotation conversion writes existing orders/costing, production writes inventory, invoices read dispatches. Providers remain mounted on logout: logout clears identity/tokens, not these domain stores; a different login in the same mounted app can inherit session data.

Capacitor Android/core/CLI dependencies and `cap:sync` exist. No Capacitor config or native Android/iOS project was discovered. BrowserRouter, absolute logo URLs, browser storage, Blob downloads, mailto and window.print require native integration testing; an Android client is not established by these dependencies.

## Route and page inventory

Status terminology: **session** = implemented code updating React memory, not durable production functionality; **fallback** = API attempt with demo on failure; **display** = read-only projection; **missing** = no corresponding routed workflow. Every path here is declared in `src/App.tsx`; extra section names are selections consumed by the dynamic QC route.

| Module / actual URL | Component / purpose | Source, state and functionality | Backend needs / gaps |
|---|---|---|---|
| `/login`, `/finance/login` | `pages/Login.tsx:Login` | Email/password, remember checkbox, password visibility, mock role selection, login; finance constrains accounts identity. AuthContext/API or gated demo. | JWT/user restoration/refresh; remember flag does not restore login. No recovery service. |
| `/` operations | `Dashboard:Dashboard` | Sales/production/stock/costing/trace/QC sections, StockAlerts and navigation; shared providers, grouped currency/unit aggregates. QC users see QualityPage; accounts see FinanceDashboard. | Scoped aggregate APIs; sample records remain; actual cost and consumption incomplete. |
| `/` accounts | `FinanceDashboard:FinanceDashboard` | Invoice totals by currency, quotation/order counts and activity links. Expenses, collections and P&L explicitly unavailable. | Invoice/report resources; no payment/expense engine exists. |
| `/finance/quality` | `FinanceQualityOverview` | Accounts-only route condition; read-only inspection/review/failure/NC counts. | Authorized summary projection; not detailed QC permission. |
| `/sales-orders`, `/sales-orders/new` | `SalesOrderList`, `NewSalesOrderModal` | Session seed orders; search, derived status filter/counts, four sorts, eight-row pagination, details/job links, CSV, New Order modal. `/new` initializes modal on list mount. | Order/line persistence, server numbering/filtering. No order edit/cancel/approve command despite status union. |
| `/sales-orders/:id` | `SalesOrderDetail` | Per-line stock/manufacturing choice retained, model/costing links, prepare parent/item job, allocation, direct dispatch, allocation dispatch, uninvoiced reversal, invoices and lineage. | Transactional fulfillment; role gaps; see workflows. |
| `/job-cards` | `JobCardList` | List API/fallback; parent/item cards, summary, combined query/status/department/stage/date filters and reset. | Paginated parent/item read model. Text claiming stock transfer never posts inventory is stale. |
| `/job-cards/:id` | `JobCardDetail` | `?item=` selects child. Overview, Materials, Costing, Routing, Tracking, Waste, Activity; edit/approve all items, issue, stage/run tracking, authorized receipt and prepared mapping. QC hides Costing tab. | Persistent transition services, atomic parent approval, real material ledger. |
| `/stock` | `Stocks/stocks:StockPage` | FG levels/movements/monthly/date range, category/brand/unit/model/type/search filters; more rows, daily expansion, CSV/print; admin manual IN, non-sales OUT, demand and StockIntelligence. | Ledger, batches, product conversion/threshold policies, reports; seed openings ambiguous. |
| `/raw-materials` | `RawMaterialPage` | Separate raw ledger; Virgin/Recycled/Ink tabs; levels/movements/monthly; query/family/unit/status/type/reset; IN/OUT, CSV, receipt QC status links. | Grade/batch/supplier master and issue/return/consumption links missing. |
| `/consumables` | `ConsumablesPage` | Empty initial shared store; add/edit/view consumable, category/unit/search/reset, levels and movement tables, IN/OUT. | Durable master/ledger; no provider role check or negative-stock blocking. |
| `/recycling` | `RecyclingPage` | Waste/granule GETs/fallback, two views, totals and recycle-machine QC warnings. | Display only: no intake, job, conversion, restock, sale or reconciliation action. “This month” totals sum all loaded rows. |
| `/costing` | `CostingPage`, `CustomCosting` | Legacy cost/rate GET/fallback and rate POST/local success; custom estimates, version review/approval/customer response, stock price reverse analysis. `?orderId=&itemId=` or `?quotationId=&quotationLineId=` scopes custom source. | Versioned costing/FX/configuration; old currency/₦ display differs from USD/UGX flow. Only orderId auto-selects custom tab; quotation deep link requires manual custom-tab selection. |
| `/masters` | `MastersPage`, `MasterTable`, `ModelManager` | Items/models/customers/suppliers/departments/users. Add/edit via generic form; models revisioned/shared; customers shared/admin-only; other categories page state. Generate quotation from customer. | Unified master IDs; generic role field is free text; no actual account provisioning. |
| `/track-trace` | `ConnectedTrace:TrackTrace` | Product/job/order/batch URL filters; jobs/stages/runs/QC lots/FG movements/conversion snapshots/cost views; button embeds legacy trace API/fallback lookup. | Stable lineage projection and authorization. Raw batches/actual consumption absent; no scanner/QR implementation. |
| `/qc` | `QualityPage`, `DailySchedules` | QC dashboard, assignment/hold metrics, explicit schedule creation/pause/resume/generate selected-date inspection. | Session schedules only; no scheduler. |
| `/qc/raw`, `/qc/production`, `/qc/machine`, `/qc/cleaning`, `/qc/safety` | `QualityPage`, `NewInspection` | Exact receipt/completed stage QC lot/machine/area source, active template, date/department/sample count; history/search/filter controls. | Supplier/batch identity and verified checklists; no inspection seed. |
| `/qc/non-conformances` | `QualityPage` | Source-linked findings, severity, assignee/action/due/verification/status form, history. | NC lifecycle persistence and independent closure; full preventive-action program not implemented. |
| `/qc/reports` | `QualityPage` | Daily/weekly/monthly/custom range, department/inspector/status/category search; SpreadsheetML XML download and browser print/PDF. | Filtered report projection/artifact generation if required. No native XLSX/PDF service. |
| `/qc/templates` | `QualityTemplates` | Admin template revision/checklist editing, machine creation and cleaning area addition. | Template/item versioning, source verification, machine master scope. |
| `/qc/inspections/:id` | `InspectionDetail`, `InspectionForm` | Draft answers/metadata, submit, independent review, quality release, reinspection, NC, final FG authority, assignment and history. | Exact template/subject snapshots, hold checks and release authorization. |
| `/quotations` | `QuotationList` | Latest/history toggle, number/customer/date/status/creator filters, metrics/CSV; generate/create/edit/duplicate/preview/sent/response/conversion links. | Durable family/revision store; not a table despite report-like rows. |
| `/quotations/settings` | `QuotationSettings` | Prospect form/promotion/linking, Admin company/banks/defaults/terms. | Shared party/settings/version data; no separate CRM route. |
| `/quotations/:id` | `QuotationDetail`, `QuotationPrint`, `QuotationEmail` | Submit/approve/request changes/reject, new revision/duplicate, mark sent, manual customer response, accepted conversion, differences/history, preview/print and saved email drafts/mailto. | Approval/response/conversion actions. No public customer URL, actual mail transmission or fiscal certification. |
| `/quotations/:id/edit` | `QuotationEditor`, `TermsFields` | Draft document/party/lines/tax/discount/terms, exact product/model, costing application, LED snapshot, refresh company snapshot, save and detail link. | Schema and source-version validation; snapshots must survive master changes. |

No procurement/purchase-order, receiving-document, payment, maintenance-work-order, independent dispatch-list, invoice-list or employee administration route exists. Suppliers and machine QC do not implement procurement or maintenance. `Placeholder.tsx` is not routed. Original `TrackTrace.tsx` remains reachable only through the connected screen's legacy toggle. Arbitrary `/qc/:section` values render generic QC content; there is no general wildcard route/404.

## Data loading, submissions and persistence

Auth is in-memory User plus localStorage tokens. All business providers use useState, usually a useRef current value to coordinate synchronous mutations; no useReducer/Redux/Zustand/sessionStorage business persistence was discovered. Components use local form/filter/modal state, FormData or controlled inputs, native validation plus pure helper validation, then Context commands. No form framework or durable offline queue exists. Page-local master edits disappear on remount; shared state survives navigation and resets on full refresh.

`mockData.ts` supplies orders/models/customers/master seeds and recycling/costing/trace fallback. `jobCardDemo.ts` supplies manufacturing demonstrations used by mockData. `finishedGoodsReference.ts` and `rawMaterialReference.ts` are generated workbook-derived arrays, not APIs. `stockData.ts` remains a separate legacy ledger feeding demo recycled granules only into the new raw adapter. Consumables, estimates, quotes, QC, machines, allocations, dispatches and invoices initially have no durable source. Imported records include client-sensitive identity; do not fabricate replacements.

Error handling is component try/catch and local notices, list loading flags and Axios interceptor. No global error boundary, retry policy, refresh-token flow, server validation mapping or offline reconciliation was found. InventoryMovementModal sets a submission lock and invokes onSave without catch/finally: rejected provider mutations can escape and leave its form locked. API fallback often masks authentication/network/server/data-shape errors alike.

## Exhaustive existing HTTP call families

All calls use `lib/api.ts:api`; default development base `http://localhost:8000/api`, production `/api`; VITE_API_BASE_URL overrides it. These are client expectations, not verified backend endpoints. GETs expect bare arrays/objects, incompatible with a DRF pagination envelope without an adapter.

| Method / relative path | Consumer | Expected payload/shape | Failure behavior |
|---|---|---|---|
| POST `/auth/login/` | `loginRequest`, AuthProvider.login | `{username,password}` → `{access,refresh,user?}` | Login displays error; no silent real-login persistence claim. |
| GET `/job-cards/` | JobCardsProvider.load | `JobCard[]`, minimal shape validation | Seeds normalized mocks; usingDemo=true; cached promise has no reload/retry command. |
| GET `/job-cards/{id}/` | loadDetail | one exact JobCard | Keeps known list/mock entry; unknown stays not found; dirty/parent guards skip refresh. |
| PATCH `/job-cards/{id}/stages/` | saveSequence | `{stages: JobCardStageEntry[]}` | Local history/save remains; UI reports whether API accepted. Not called for estimate-linked/parent children. |
| GET `/recycling/waste/`, `/recycling/granules/` | RecyclingPage effect | WasteEntry[] / GranulesBatch[] | Mock fallback. |
| GET `/costing/`, `/costing/exchange-rates/` | CostingPage effect | CostingRecord[] / ExchangeRate[] | Mock fallback. |
| POST `/costing/exchange-rates/` | handleLogRate | Client-built ExchangeRate | Adds local row in finally even on failure. Does not recalculate saved costing. |
| GET `/trace/{encoded query}/` | LegacyTrace.handleSearch | TraceResult | Sample lookup on failure. |

There are no quotation, QC, order, invoice, master or inventory HTTP requests. No server code is present in the inspected frontend tree. A real API URL/token path exists, but no running production server or successful database persistence was established.

## Authentication / permission inventory

`types/index.ts:Role` has nine values: qc_inspector, qc_supervisor, receptionist, production_manager, store_keeper, production_operator, recycling_operator, accounts, admin. `demoAuth.ts` accepts hardcoded demo identities/password only when explicitly gated (development defaults enabled unless disabled; production requires true). Operations admin aliases can select a demo role; finance identity resolves accounts. Demo login clears existing tokens. Real login stores navapack_access/navapack_refresh, takes role from response with receptionist default, and does not restore user on reload. Login remembers only `navapack_remember=true`; it has no persistence consumer. Logout removes access, refresh and legacy navapack_token; not remember. Interceptor adds access or legacy token; 401 removes only legacy token before redirect, leaving access/refresh behind. No refresh endpoint is called.

RequireAuth protects all shell routes by user presence and restricts QC identities to `/`, `/qc*`, `/job-cards*`. QualityGuard and QuotationsGuard enforce their view-role lists; finance/quality explicitly checks accounts. Most other routes have no domain role guard. Sidebar roles differ from direct URL reachability; finance sidebar exposes otherwise restricted pages. Context/pure-command checks are inconsistent: raw/consumable mutations and allocation/reversal lack actor guards, whereas direct dispatch, model/customer/settings saves and production/QC commands enforce some roles. Server permissions must use object scope and transitions independently.

QC review disallows inspector self-review and NC closure disallows the correction assignee as verifier. Job/estimate/quotation approval does not implement a universal maker/checker prohibition. No automatic escalation, delegated authority, durable authentication activity or tamper-proof audit exists. Existing name-based activity fields need stable user IDs plus preserved display snapshots.

## Documentation drift identified

Older ARCHITECTURE/DEVELOPMENT_STATUS/BACKEND_TODO sections describe independent dashboard metrics, local-only customers, reservations as mandatory, stock transfer as never posting, and execution runs as absent. Current code has shared customers, connected dashboard, direct dispatch and production runs. Raw issue/recycling remain tracking-only. Existing docs also record confirmed target production-for-stock and additional issues, but no complete routed implementation exists. Use this source audit plus later sections of the canonical module documents; do not promote historical plans into implemented facts.

## Generated source inspection appendices

The appendices below inventory all inspected source files and interactive JSX evidence. They preserve handler expressions, labels, fields and column-producing expressions, including mapped/dynamic controls. They are static evidence, not browser pass claims. Read their business classification together with the page inventory and workflows.

### Inspected source manifest

All source files were parsed/read. Hashes identify this working-tree snapshot; generated data arrays were inspected structurally without reproducing sensitive record dumps.

| Source | Lines | SHA256 prefix |
|---|---:|---|
| src/App.tsx | 92 | 3b6a8cbf01eaf878 |
| src/components/GenerateQuotation.tsx | 6 | aa1541f823a5ac8b |
| src/components/layout/AppShell.tsx | 121 | debadd47e5abae36 |
| src/components/LEDFields.tsx | 12 | 6290235461affbf0 |
| src/components/login/BrandPanel.tsx | 31 | 4418cd04be30e840 |
| src/components/login/Button.tsx | 12 | ab85d76b65be6737 |
| src/components/login/RecycleLoop.tsx | 21 | e7e9ed53673ea4a2 |
| src/components/login/TextField.tsx | 25 | 800b82ee758d0d13 |
| src/components/login/WovenBackground.tsx | 14 | d740d429f882de94 |
| src/components/ProductionRuns.tsx | 8 | b93697074c748a15 |
| src/components/ProductionTimeline.tsx | 5 | 490182ec108ed79e |
| src/components/SalesSummary.tsx | 7 | f8d046dccf791d0c |
| src/components/StockIntelligence.tsx | 37 | 1ee18241f2a68a64 |
| src/components/ui/Card.tsx | 10 | 47fa946b01456ac6 |
| src/components/ui/InventoryMovementModal.tsx | 86 | 6cd18ce3b931d3e9 |
| src/components/ui/SearchSelect.tsx | 59 | d9d5be7140ce1592 |
| src/components/ui/StatusBadge.tsx | 38 | a959a4484820d584 |
| src/context/AuthContext.tsx | 77 | 0782a38777c9ce13 |
| src/context/CommercialContext.tsx | 29 | ee440be09bb49a5d |
| src/context/ConsumablesContext.tsx | 36 | ad855788b5fcfddb |
| src/context/CostingContext.tsx | 51 | 941c51036bcfd983 |
| src/context/InventoryContext.tsx | 89 | da762d41c108b45c |
| src/context/InvoicesContext.tsx | 16 | 3c4ecb3859dd635a |
| src/context/JobCardsContext.tsx | 205 | 7d22c97be147c070 |
| src/context/ModelsContext.tsx | 20 | 766cfab21e23025b |
| src/context/QualityContext.tsx | 58 | ebde0860092bc025 |
| src/context/QuotationsContext.tsx | 59 | 1fdb025712ea2618 |
| src/context/SalesOrdersContext.tsx | 35 | 1a85c76fc0c41181 |
| src/index.css | 55 | e9b816e9a18f1cab |
| src/lib/api.ts | 52 | 5e568dde91022045 |
| src/lib/commercialPricing.ts | 22 | c47cde6ba4b79fa6 |
| src/lib/consumableData.ts | 28 | f2aa90496dc963b8 |
| src/lib/customCosting.ts | 106 | 96b8a9166b535784 |
| src/lib/demoAuth.ts | 10 | a1445569a4811a4d |
| src/lib/finishedGoodsData.ts | 98 | ab7a3cd79190244c |
| src/lib/finishedGoodsReference.ts | 1174 | 0b475fb5adb25594 |
| src/lib/fulfillment.ts | 75 | 53d867f9845ef79d |
| src/lib/invoices.ts | 47 | e744d583d01a5a31 |
| src/lib/jobCardDemo.ts | 54 | c769ce36963106cd |
| src/lib/jobCards.ts | 195 | 2840a9e89a9c6ce6 |
| src/lib/led.ts | 24 | 654d4c3b5b97d31b |
| src/lib/mockData.ts | 199 | 1bae6586d97d47f9 |
| src/lib/operations.ts | 29 | 9e730e7a1b5c2704 |
| src/lib/parentJobCards.ts | 44 | 5257ecbe1f1ebd68 |
| src/lib/productionRouting.ts | 20 | 1026103aaa3d2726 |
| src/lib/productionRuns.ts | 21 | 06853da3c7cae822 |
| src/lib/productModels.ts | 11 | 947d7c86055bc644 |
| src/lib/quality.ts | 141 | 4d0510a86b07fb22 |
| src/lib/qualityIntegration.ts | 59 | 862d92a6c72fe364 |
| src/lib/qualityReports.ts | 12 | 637920e6bc05f831 |
| src/lib/qualitySchedule.ts | 15 | 439bf286015e5055 |
| src/lib/qualityTemplates.ts | 27 | 60cc9792ec2170a6 |
| src/lib/quotationReview.ts | 13 | 9250bd71e7ee5713 |
| src/lib/quotations.ts | 100 | 2f722766326617f0 |
| src/lib/rawMaterialData.ts | 61 | de95176d164e800a |
| src/lib/rawMaterialReference.ts | 4944 | 71726a2eeca0cf84 |
| src/lib/salesJob.ts | 19 | c3972cbf82d15ee9 |
| src/lib/salesOrders.ts | 61 | beeafe1e67591b95 |
| src/lib/stockData.ts | 126 | 87eb32e48b4e1042 |
| src/lib/stockIntelligence.ts | 79 | 28eefbadb807a0e1 |
| src/main.tsx | 14 | b726f96e0cdb32c8 |
| src/pages/Consumables/ConsumablesPage.tsx | 89 | f18b260dd7095fcf |
| src/pages/Costing/CostingFields.tsx | 16 | 8704fa993aa669ff |
| src/pages/Costing/CostingPage.tsx | 212 | 800505ad72c59c6f |
| src/pages/Costing/CustomCosting.tsx | 68 | 0c23856e499b902b |
| src/pages/Dashboard.tsx | 37 | 9f9563b1a49ed8f9 |
| src/pages/FinanceDashboard.tsx | 97 | b579abb09eb81569 |
| src/pages/JobCards/JobCardDetail.tsx | 90 | ad8904ee831d9da3 |
| src/pages/JobCards/JobCardForms.tsx | 88 | 84c986a8b2fd40b1 |
| src/pages/JobCards/JobCardList.tsx | 45 | 53372a5756797974 |
| src/pages/JobCards/JobCardUI.tsx | 33 | e75f14fa09a00c74 |
| src/pages/JobCards/JobCosting.tsx | 10 | dc6dfbae8eac53df |
| src/pages/JobCards/JobRoutingEditor.tsx | 21 | e082db7e91a38420 |
| src/pages/JobCards/RoutingFields.tsx | 13 | 8c0a04778de735dc |
| src/pages/Login.tsx | 74 | a812a8475222e343 |
| src/pages/Masters/MastersPage.tsx | 115 | 4f7cbbdcd6f8c61a |
| src/pages/Masters/MasterTable.tsx | 140 | b2f3790073c5aa02 |
| src/pages/Masters/ModelManager.tsx | 14 | 089fe810fd0e811d |
| src/pages/Placeholder.tsx | 13 | 1d640ac04eb085d5 |
| src/pages/Quality/DailySchedules.tsx | 12 | 80db50a2c0425cfa |
| src/pages/Quality/InspectionDetail.tsx | 35 | d8b058a3051fb0e4 |
| src/pages/Quality/InspectionForm.tsx | 31 | b597ea1c19121f39 |
| src/pages/Quality/NewInspection.tsx | 44 | b97952614393f99d |
| src/pages/Quality/QualityPage.tsx | 47 | 491e837f7841c1ea |
| src/pages/Quality/QualityTemplates.tsx | 18 | 7d172060ac9d587b |
| src/pages/Quotations/QuotationDetail.tsx | 38 | 44ea4d07da2212e5 |
| src/pages/Quotations/QuotationEditor.tsx | 41 | 136c8a6583316d23 |
| src/pages/Quotations/QuotationEmail.tsx | 8 | 1fed9a5f4b5f9215 |
| src/pages/Quotations/QuotationList.tsx | 24 | 2528587267a58156 |
| src/pages/Quotations/QuotationPrint.tsx | 13 | 75fb3326d769f3d4 |
| src/pages/Quotations/QuotationSettings.tsx | 20 | 63388d712c4cff2f |
| src/pages/RawMaterials/RawMaterialPage.tsx | 77 | 794215a51f4d8855 |
| src/pages/Recycling/RecyclingPage.tsx | 128 | e9c2c2f9e3c1822a |
| src/pages/SalesOrders/NewSalesOrderModal.tsx | 125 | 57b29a38805f1696 |
| src/pages/SalesOrders/SalesInvoice.tsx | 21 | a58620dde8c451d7 |
| src/pages/SalesOrders/SalesOrderDetail.tsx | 59 | c4dfe5dbb637e2bc |
| src/pages/SalesOrders/SalesOrderList.tsx | 420 | 7a30cd7e850154d0 |
| src/pages/Stocks/SalesOrderDemand.tsx | 35 | 9c4116f4e390612d |
| src/pages/Stocks/stocks.tsx | 153 | e22ebe3bef5bc1f5 |
| src/pages/TrackTrace/ConnectedTrace.tsx | 30 | b7bcd7efeab08749 |
| src/pages/TrackTrace/TrackTrace.tsx | 114 | 6f9b0e79b1c67dd7 |
| src/types/index.ts | 296 | 3a1c8d0b5a3abf82 |
| src/vite-env.d.ts | 2 | 65996936fbb04291 |

### Interactive JSX evidence

An unlabeled button with no handler is only a submit action when nested in a form; otherwise it is inert. Dynamic mapped controls retain binding expressions and their source arrays below. Provider and helper analysis above determines whether actions are local, API, or missing.


### src/components/GenerateQuotation.tsx

Actions and submission/navigation handlers:

- L5 button: Generate Quotation — onClick={()=>{try{const q=store.generateQuotation({customerId,prospectId,estimateId});nav(`/quotations/${q.id}${q.status==='Draft'?'/edit':''}`);}catch(e){setError(e instanceof Error?e.message:'Unable to generate quotation.');}}}; type="button"

Table headers and mapped label/option arrays (includes filter/UI enums):

- L5 mapped labels/options: ['admin','receptionist','accounts']

### src/components/layout/AppShell.tsx

Actions and submission/navigation handlers:

- L76 NavLink: {label} — to={to}
- L100 button: Sign out — onClick={logout}
- L111 button: (icon/dynamic content) — aria-label="Notifications" [implicit submit if inside form; otherwise no click handler]

Table headers and mapped label/option arrays (includes filter/UI enums):

- L28 mapped labels/options: ["receptionist", "accounts", "production_manager", "admin"]
- L30 mapped labels/options: ["receptionist", "production_manager", "store_keeper", "production_operator", "recycling_operator", "accounts", "admin"]
- L31 mapped labels/options: ["receptionist", "admin"]
- L32 mapped labels/options: ["receptionist", "production_manager", "store_keeper", "production_operator", "admin"]
- L33 mapped labels/options: ["store_keeper", "admin"]
- L34 mapped labels/options: ["store_keeper", "admin"]
- L35 mapped labels/options: ["store_keeper", "admin"]
- L36 mapped labels/options: ["recycling_operator", "admin"]
- L37 mapped labels/options: ["accounts", "admin"]
- L38 mapped labels/options: ["receptionist", "production_manager", "store_keeper", "production_operator", "recycling_operator", "accounts", "admin"]
- L39 mapped labels/options: ["admin"]
- L43 mapped labels/options: ["accounts"]
- L44 mapped labels/options: ["accounts"]
- L45 mapped labels/options: ["accounts"]
- L46 mapped labels/options: ["accounts"]
- L47 mapped labels/options: ["accounts"]
- L48 mapped labels/options: ["accounts"]
- L49 mapped labels/options: ["accounts"]
- L50 mapped labels/options: ["accounts"]
- L51 mapped labels/options: ["accounts"]
- L52 mapped labels/options: ["accounts"]
- L53 mapped labels/options: ["accounts"]

### src/components/LEDFields.tsx

Actions and submission/navigation handlers:

- L10 button: Apply current conversion / refresh LED inputs — onClick={()=>update({})}; type="button"

Form fields and binding/validation evidence:

- L10 input LED applies to this item: type="checkbox"; onChange={e=>update({applies:e.target.checked})}
- L10 select Provisional LED percentage base: value={current.percentageBase??''}; onChange={e=>update({percentageBase:e.target.value as LEDInput['percentageBase']})}
- L10 input Saved USD→UGX rate: type="number"; value={current.usdToUGX??''}; min="0.000001"; step="any"; onChange={e=>update({usdToUGX:e.target.value===''?undefined:e.target.valueAsNumber})}
- L10 input FX effective date: type="date"; value={current.fxDate??''}; onChange={e=>update({fxDate:e.target.value})}
- L10 input Include LED in VAT base: type="checkbox"; onChange={e=>update({vatOnLED:e.target.checked})}


### src/components/login/Button.tsx

Actions and submission/navigation handlers:

- L5 button: {loading ? : success ? : null} {success ? "Signed in" : children} {!loading && !success && } [implicit submit if inside form; otherwise no click handler]


### src/components/login/TextField.tsx

Form fields and binding/validation evidence:

- L17 input: id={inputId}


### src/components/ProductionRuns.tsx

Actions and submission/navigation handlers:

- L7 form: Stage (approved units){stages.map(s=>{s.name} · {s.inputUnit} → {s.outputUnit} · waste {s.wasteUnit})} {[['number','Run reference','text'],['input','Run input','number'],['output','Run output','number'],['waste','Run waste','number'],['start','Started','datetime-local'],['end','Finished execution','datetime-local'],['remarks','Remarks','text']].map(([k,l,t])=>{l})} Final run: complete this stage Record run — onSubmit={e=>{e.preventDefault();const f=new FormData(e.currentTarget),s=stages.find(s=>s.id===String(f.get('stage')));if(!s)return;try{recordRun(card.id,{id:`run-${card.id}-${card.productionRuns?.length??0}`,number:String(f.get('number')),stageId:s.id,inputQuantity:Number(f.get('input')),outputQuantity:Number(f.get('output')),wasteQuantity:Number(f.get('waste')),inputUnit:s.inputUnit,outputUnit:s.outputUnit,wasteUnit:s.wasteUnit,startedAt:new Date(String(f.get('start'))).toISOString(),completedAt:new Date(String(f.get('end'))).toISOString(),operator:user?.name??'',remarks:String(f.get('remarks'))},f.get('finish')==='on');setError('');e.currentTarget.reset();}catch(err){setError(err instanceof Error?err.message:'Unable to record run.');}}}
- L7 button: Record run [implicit submit if inside form; otherwise no click handler]

Form fields and binding/validation evidence:

- L7 select Stage (approved units): name="stage"
- L7 input: name={k}; type={t}; required={k!=='remarks'}; min="0"; step="any"
- L7 input Final run: complete this stage: name="finish"; type="checkbox"

Table headers and mapped label/option arrays (includes filter/UI enums):

- L7 mapped labels/options: ['admin','production_manager','production_operator']
- L7 mapped labels/options: ['MaterialIssued','Issued','InProduction','OnHold']
- L7 mapped labels/options: [['number','Run reference','text'],['input','Run input','number'],['output','Run output','number'],['waste','Run waste','number'],['start','Started','datetime-local'],['end','Finished execution','datetime-local'],['remarks','Remarks','text']]
- L7 mapped labels/options: ['number','Run reference','text']
- L7 mapped labels/options: ['input','Run input','number']
- L7 mapped labels/options: ['output','Run output','number']
- L7 mapped labels/options: ['waste','Run waste','number']
- L7 mapped labels/options: ['start','Started','datetime-local']
- L7 mapped labels/options: ['end','Finished execution','datetime-local']
- L7 mapped labels/options: ['remarks','Remarks','text']

### src/components/StockIntelligence.tsx

Actions and submission/navigation handlers:

- L17 Link: {finishedGoodLabel(p)} — to={`/track-trace?productId=${p.id}`}
- L27 Link: Stock → Trace — to={`/track-trace?productId=${id}`}
- L28 form: Net KG per CTR Pieces per CTR (optional) Effective date Save new conversion version — onSubmit={e=>{e.preventDefault();const f=new FormData(e.currentTarget);run(()=>inv.saveConversion({productId:id,modelId:modelId||undefined,unit:product.unit,kgPerCTR:Number(f.get('kg')),piecesPerCTR:optional(f,'pieces'),effectiveDate:String(f.get('date'))}));}}
- L28 button: Save new conversion version [implicit submit if inside form; otherwise no click handler]
- L30 form: Product alerts · thresholds in {product.unit} {(['critical','minimum','reorder','target','windowDays','leadDays','highConsumption','rapidDaily','replenishmentQuantity'] as const).map(k=>{{critical:'Critical',minimum:'Minimum',reorder:'Reorder',target:'Target',windowDays:'Consumption window days',leadDays:'Lead time days',highConsumption:'High consumption in window',rapidDaily:'Rapid daily consumption',replenishmentQuantity:'Pending replenishment quantity'}[k]})} Replenishment expected Save thresholds — onSubmit={e=>{e.preventDefault();const f=new FormData(e.currentTarget);run(()=>inv.saveThreshold({productId:id,unit:product.unit,minimum:Number(f.get('minimum')),critical:Number(f.get('critical')),reorder:Number(f.get('reorder')),target:Number(f.get('target')),windowDays:Number(f.get('windowDays')),leadDays:optional(f,'leadDays'),highConsumption:optional(f,'highConsumption'),rapidDaily:optional(f,'rapidDaily'),replenishmentQuantity:optional(f,'replenishmentQuantity'),replenishmentDue:String(f.get('replenishmentDue'))||undefined}));}}
- L30 button: Save thresholds [implicit submit if inside form; otherwise no click handler]
- L31 form: Revisioned stock price / estimated COP (UGX) Independent commercial price; conversions never overwrite negotiated prices. Enter total selling amount including LED when applicable. This analysis does not reprice accepted orders or quotations. Actual cost requires recorded evidence. {[['batch','Exact batch / reference','text'],['date','Snapshot date','date'],['quantity',`Priced quantity (${product.unit})`,'number'],['amount','Selling amount (entered VAT basis)','number'],['actualCOP','Actual COP total (optional)','number'],['actualReference','Actual cost evidence reference','text']].map(([k,l,t])=>{l})} VAT basissetPolicy({...policy,vatMode:e.target.value as PricePolicy['vatMode']})}>InclusiveExclusiveVAT %setPolicy({...policy,vatRate:e.target.valueAsNumber})} className={ENTRY_INPUT}/>Profit methodsetPolicy({...policy,profitMethod:e.target.value as PricePolicy['profitMethod']})}>Markup on production costGross margin on net sellingProfit %setPolicy({...policy,profitPercent:e.target.valueAsNumber})} className={ENTRY_INPUT}/> setPolicy({...policy,ledApplies:e.target.checked,selectionConfirmed:false})}/> LED applies to this product{policy.ledApplies&&LED method: Higher of the Two — client-confirmed (2.5% vs USD 70/tonne)Percentage basesetPolicy({...policy,percentageBase:e.target.value as PricePolicy['percentageBase']})}>Net selling excluding levy/profit deductionDerived production cost{([['ledRate','LED %'],['usdPer1000KG','USD per 1,000 KG'],['usdToUGX','Saved USD→UGX']] as const).map(([k,l])=>{l}setPolicy({...policy,[k]:e.target.value===''?undefined:e.target.valueAsNumber})} className={ENTRY_INPUT}/>)}FX rate datesetPolicy({...policy,fxDate:e.target.value})} className={ENTRY_INPUT}/>setPolicy({...policy,vatOnLED:e.target.checked})}/> LED included in VAT taxable basesetPolicy({...policy,selectionConfirmed:e.target.checked})}/> Confirm applicability and selected provisional percentage base (base pending client clarification)} Save financial snapshot LED MAX(2.5% of selected base, USD 70 per tonne × saved FX) is client-confirmed. Product applicability, percentage base and VAT-on-LED remain explicit. — onSubmit={e=>{e.preventDefault();const f=new FormData(e.currentTarget);run(()=>{const date=String(f.get('date')),quantity=Number(f.get('quantity'));cost.saveStockPrice({productId:id,modelId:modelId||undefined,batch:String(f.get('batch')),date,quantity,unit:product.unit,amount:Number(f.get('amount')),conversion:quantitySnapshot(id,quantity,product.unit,date,inv.conversions,modelId||undefined),policy,actualCOP:optional(f,'actualCOP'),actualReference:String(f.get('actualReference'))||undefined});});}}
- L33 button: Save financial snapshot [implicit submit if inside form; otherwise no click handler]
- L34 Link: Traceability reference — to={`/track-trace?productId=${s.productId}&batch=${encodeURIComponent(s.batch)}`}

Form fields and binding/validation evidence:

- L27 select Exact finished-goods variant: value={id}; onChange={e=>{setId(e.target.value);setModelId('');}}
- L27 select Exact model scope (optional): value={modelId}; onChange={e=>setModelId(e.target.value)}
- L28 input Net KG per CTR: name="kg"; type="number"; min="0.000001"; step="any"
- L28 input Pieces per CTR (optional): name="pieces"; type="number"; min="1"; step="1"
- L28 input Effective date: name="date"; type="date"; defaultValue={today()}
- L30 input: name={k}; type="number"; defaultValue={threshold?.[k]??(k==='windowDays'?7:undefined)}; required={['critical','minimum','reorder','target','windowDays'].includes(k)}; min="0"; step="any"
- L30 input Replenishment expected: name="replenishmentDue"; type="date"; defaultValue={threshold?.replenishmentDue}
- L31 input: name={k}; type={t}; defaultValue={k==='date'?today():undefined}; required={['batch','date','quantity','amount'].includes(k)}; min="0"; step="any"
- L32 select VAT basis: value={policy.vatMode}; onChange={e=>setPolicy({...policy,vatMode:e.target.value as PricePolicy['vatMode']})}
- L32 input VAT %: type="number"; value={policy.vatRate}; min="0"; max="100"; step="any"; onChange={e=>setPolicy({...policy,vatRate:e.target.valueAsNumber})}
- L32 select Profit method: value={policy.profitMethod}; onChange={e=>setPolicy({...policy,profitMethod:e.target.value as PricePolicy['profitMethod']})}
- L32 input Profit %: type="number"; value={policy.profitPercent}; min="0"; step="any"; onChange={e=>setPolicy({...policy,profitPercent:e.target.valueAsNumber})}
- L33 input LED applies to this product: type="checkbox"; onChange={e=>setPolicy({...policy,ledApplies:e.target.checked,selectionConfirmed:false})}
- L33 select Percentage base: value={policy.percentageBase}; onChange={e=>setPolicy({...policy,percentageBase:e.target.value as PricePolicy['percentageBase']})}
- L33 input: type="number"; value={policy[k]??''}; readOnly={k==='ledRate'||k==='usdPer1000KG'}; min="0"; step="any"; onChange={e=>setPolicy({...policy,[k]:e.target.value===''?undefined:e.target.valueAsNumber})}
- L33 input FX rate date: type="date"; value={policy.fxDate??''}; onChange={e=>setPolicy({...policy,fxDate:e.target.value})}
- L33 input LED included in VAT taxable base: type="checkbox"; onChange={e=>setPolicy({...policy,vatOnLED:e.target.checked})}
- L33 input Confirm applicability and selected provisional percentage base (base pending client clarification): type="checkbox"; onChange={e=>setPolicy({...policy,selectionConfirmed:e.target.checked})}

Table headers and mapped label/option arrays (includes filter/UI enums):

- L17 mapped labels/options: ['Product / stock / unit','Reorder / severity','Last OUT / consumption','Replenishment / history']
- L17 {l}
- L24 mapped labels/options: ['accounts','admin']
- L24 mapped labels/options: ['admin','store_keeper','production_manager']
- L24 mapped labels/options: ['admin','production_manager']
- L25 mapped labels/options: ['admin','accounts','production_manager']
- L30 mapped labels/options: ['critical','minimum','reorder','target','windowDays','leadDays','highConsumption','rapidDaily','replenishmentQuantity']
- L30 mapped labels/options: ['critical','minimum','reorder','target','windowDays']
- L31 mapped labels/options: [['batch','Exact batch / reference','text'],['date','Snapshot date','date'],['quantity',`Priced quantity (${product.unit})`,'number'],['amount','Selling amount (entered VAT basis)','number'],['actualCOP','Actual COP total (optional)','number'],['actualReference','Actual cost evidence reference','text']]
- L31 mapped labels/options: ['batch','Exact batch / reference','text']
- L31 mapped labels/options: ['date','Snapshot date','date']
- L31 mapped labels/options: ['amount','Selling amount (entered VAT basis)','number']
- L31 mapped labels/options: ['actualCOP','Actual COP total (optional)','number']
- L31 mapped labels/options: ['actualReference','Actual cost evidence reference','text']
- L31 mapped labels/options: ['batch','date','quantity','amount']
- L33 mapped labels/options: [['ledRate','LED %'],['usdPer1000KG','USD per 1,000 KG'],['usdToUGX','Saved USD→UGX']]
- L33 mapped labels/options: ['ledRate','LED %']
- L33 mapped labels/options: ['usdPer1000KG','USD per 1,000 KG']
- L33 mapped labels/options: ['usdToUGX','Saved USD→UGX']

### src/components/ui/InventoryMovementModal.tsx

Actions and submission/navigation handlers:

- L60 button: (icon/dynamic content) — onClick={onClose}; type="button"; aria-label="Close"
- L61 form: Frontend simulation. Entries survive navigation and reset on refresh. Date setDate(event.target.value)} className={`${ENTRY_INPUT} mt-1`} /> {finishedGoods ? 'Category' : 'Material Category'} { setCategory(event.target.value); setMaterialId(''); setName(''); setPieces(''); setCustomer(''); }} className={`${ENTRY_INPUT} mt-1`}>{categories.map(([id, label]) => {label})} {finishedGoods ? 'Product / Variant' : 'Material / Grade'} option.category === category).map(option => ({ ...option, detail: option.detail ?? option.unit }))} onChange={value => { setName(value); setMaterialId(''); setPieces(''); setCustomer(''); }} onSelect={option => { const record = options.find(item => item.id === option.id)!; setName(option.name); setMaterialId(option.id); setPieces(record.pieces == null ? '' : String(record.pieces)); setCustomer(record.customer ?? ''); }} /> {selected?.fields && {selected.fields.map(([label, value]) => {label})}} {finishedGoods && Pieces setPieces(event.target.value)} className={`${ENTRY_INPUT} mt-1`} />Pieces per package, when applicable. Stock quantity remains in the selected unit.} {selected && {finishedGoods ? 'Current Stock' : 'Available'}: {selected.available === null ? 'Not recorded' : `${selected.available.toLocaleString('en-IN', { maximumFractionDigits: 2 })} ${selected.unit}`}} {direction === 'OUT' && selected?.available != null && Number(quantity) > selected.available && Quantity exceeds the recorded balance. This simulation allows the entry.} Quantity setQuantity(event.target.value)} className={`${ENTRY_INPUT} mt-1`} /> Unit {finishedGoods && direction === 'OUT' && Customer / Destination setCustomer(event.target.value)} className={`${ENTRY_INPUT} mt-1`} />} {finishedGoods&&direction==='OUT'&&Non-sales Stock OUT purposesetMovementPurpose(e.target.value as typeof movementPurpose)}>TransferWasteApproved adjustment (Admin confirmation)Customer sales must use confirmed Sales Order dispatch. Adjustments require Admin approval, reference and reason.} Reference setReference(event.target.value)} className={`${ENTRY_INPUT} mt-1`} /> Remarks setRemarks(event.target.value)} className={`${ENTRY_INPUT} mt-1`} /> {error && {error}} CancelSave Stock {direction} — onSubmit={submit}
- L81 button: Cancel — onClick={onClose}; type="button"
- L81 button: Save Stock {direction} — type="submit"

Form fields and binding/validation evidence:

- L64 input Date: type="date"; value={date}; min={selected?.openingDate}; onChange={event => setDate(event.target.value)}
- L65 select: value={category}; onChange={event => { setCategory(event.target.value); setMaterialId(''); setName(''); setPieces(''); setCustomer(''); }}
- L67 SearchSelect: inputId="inventory-material"; label={finishedGoods ? 'Product / Variant' : 'Material / Grade'}; value={name}; onChange={value => { setName(value); setMaterialId(''); setPieces(''); setCustomer(''); }}; onSelect={option => { const record = options.find(item => item.id === option.id)!; setName(option.name); setMaterialId(option.id); setPieces(record.pieces == null ? '' : String(record.pieces)); setCustomer(record.customer ?? ''); }}
- L68 input: value={value}
- L69 input Pieces: type="number"; value={pieces}; readOnly={direction === 'OUT'}; disabled={!selected}; min="1"; step="1"; onChange={event => setPieces(event.target.value)}
- L73 input Quantity: type="number"; value={quantity}; min="0.000001"; step="any"; onChange={event => setQuantity(event.target.value)}
- L74 input Unit: value={selected?.unit ?? ''}
- L76 input Customer / Destination: value={customer}; onChange={event => setCustomer(event.target.value)}
- L77 select Non-sales Stock OUT purpose: value={movementPurpose}; onChange={e=>setMovementPurpose(e.target.value as typeof movementPurpose)}
- L78 input Reference: value={reference}; onChange={event => setReference(event.target.value)}
- L79 textarea Remarks: value={remarks}; onChange={event => setRemarks(event.target.value)}


### src/components/ui/SearchSelect.tsx

Form fields and binding/validation evidence:

- L50 input: id={inputId}; aria-label={label}; value={value}; onChange={event => { onChange(event.target.value); setSearching(true); setOpen(true); setActive(0); }}


### src/context/CommercialContext.tsx

Table headers and mapped label/option arrays (includes filter/UI enums):

- L24 mapped labels/options: ['inclusive', 'exclusive']

### src/context/ConsumablesContext.tsx

Table headers and mapped label/option arrays (includes filter/UI enums):

- L25 mapped labels/options: ['IN', 'OUT']

### src/context/CostingContext.tsx

Table headers and mapped label/option arrays (includes filter/UI enums):

- L19 mapped labels/options: ['admin', 'accounts', 'receptionist', 'production_manager']
- L26 mapped labels/options: ['admin', 'accounts']
- L33 mapped labels/options: ['admin','accounts']
- L38 mapped labels/options: ['admin', 'accounts']

### src/context/InventoryContext.tsx

Table headers and mapped label/option arrays (includes filter/UI enums):

- L65 mapped labels/options: ['admin','store_keeper']
- L65 mapped labels/options: ['transfer','waste','adjustment']
- L75 mapped labels/options: ['admin','production_manager']
- L76 mapped labels/options: ['admin','store_keeper','production_manager']
- L77 mapped labels/options: ['admin','store_keeper','receptionist']

### src/context/InvoicesContext.tsx

Table headers and mapped label/option arrays (includes filter/UI enums):

- L10 mapped labels/options: ['admin', 'accounts', 'receptionist']

### src/context/JobCardsContext.tsx

Table headers and mapped label/option arrays (includes filter/UI enums):

- L93 mapped labels/options: ['admin', 'receptionist', 'production_manager']
- L95 mapped labels/options: ['Draft', 'PendingApproval']
- L102 mapped labels/options: ['admin', 'receptionist', 'production_manager']
- L120 mapped labels/options: ['admin', 'qc_inspector', 'qc_supervisor']
- L130 mapped labels/options: ['admin', 'store_keeper']
- L142 mapped labels/options: ['admin', 'production_manager']
- L142 mapped labels/options: ['Draft', 'PendingApproval']
- L149 mapped labels/options: ['admin', 'production_manager', 'receptionist']
- L153 mapped labels/options: ['admin', 'production_manager']
- L159 mapped labels/options: ['Revision Required', 'Superseded']
- L163 mapped labels/options: ['Revision Required', 'Superseded']
- L180 mapped labels/options: ['admin', 'store_keeper']

### src/context/ModelsContext.tsx

Table headers and mapped label/option arrays (includes filter/UI enums):

- L14 mapped labels/options: ['admin', 'production_manager', 'receptionist']

### src/context/QualityContext.tsx

Table headers and mapped label/option arrays (includes filter/UI enums):

- L40 mapped labels/options: ['admin','qc_supervisor']
- L41 mapped labels/options: ['admin','qc_supervisor']
- L42 mapped labels/options: ['admin','qc_supervisor']

### src/context/QuotationsContext.tsx

Table headers and mapped label/option arrays (includes filter/UI enums):

- L39 mapped labels/options: ['admin', 'accounts', 'receptionist', 'production_manager']
- L47 mapped labels/options: ['receptionist', 'admin']

### src/pages/Consumables/ConsumablesPage.tsx

Actions and submission/navigation handlers:

- L44 button: (icon/dynamic content) — onClick={onClose}; type="button"; aria-label="Close"
- L45 form: Name setDraft({ ...draft, name: e.target.value })} className={`${ENTRY_INPUT} mt-1`} /> Category setDraft({ ...draft, category: e.target.value as Consumable['category'] })} className={`${ENTRY_INPUT} mt-1`}>{categories.map(([id, label]) => {label})} Unit setDraft({ ...draft, unit: e.target.value as Consumable['unit'] })} className={`${ENTRY_INPUT} mt-1`}>{CONSUMABLE_UNITS.map(unit => {unit})} Opening Stock setOpeningStock(e.target.value)} className={`${ENTRY_INPUT} mt-1`} /> Opening Date setDraft({ ...draft, openingDate: e.target.value })} className={`${ENTRY_INPUT} mt-1`} /> Minimum Level setDraft({ ...draft, minLevel: e.target.value === '' ? undefined : Number(e.target.value) })} className={`${ENTRY_INPUT} mt-1`} /> {posted && Unit and opening balance are locked after stock movements have been recorded.} {error && {error}} {readOnly ? 'Close' : 'Cancel'}{!readOnly && Save Consumable} — onSubmit={submit}
- L56 button: {readOnly ? 'Close' : 'Cancel'} — onClick={onClose}; type="button"
- L56 button: Save Consumable — type="submit"
- L75 button: Add Consumable — onClick={() => setEditing({ item: { id: crypto.randomUUID(), name: '', category: 'imported', unit: 'Each', openingStock: 0, openingDate: new Date().toLocaleDateString('en-CA') }, readOnly: false })}
- L75 button: Stock IN — onClick={() => setDirection('IN')}
- L75 button: Stock OUT — onClick={() => setDirection('OUT')}
- L78 button: {id === 'levels' ? 'Stock Levels' : 'Movements'} — onClick={() => setView(id)}
- L79 button: Clear filters — onClick={() => { setQuery(''); setCategory('all'); setUnit('all'); }}
- L81 button: View — onClick={() => setEditing({ item, readOnly: true })}; aria-label={`View ${item.name}`}
- L81 button: Edit — onClick={() => setEditing({ item, readOnly: false })}; aria-label={`Edit ${item.name}`}

Form fields and binding/validation evidence:

- L46 input Name: value={draft.name}; readOnly={readOnly}; onChange={e => setDraft({ ...draft, name: e.target.value })}
- L48 select Category: value={draft.category}; disabled={readOnly}; onChange={e => setDraft({ ...draft, category: e.target.value as Consumable['category'] })}
- L49 select Unit: value={draft.unit}; disabled={readOnly || posted}; onChange={e => setDraft({ ...draft, unit: e.target.value as Consumable['unit'] })}
- L50 input Opening Stock: type="number"; value={openingStock}; readOnly={readOnly || posted}; min="0"; step="any"; onChange={e => setOpeningStock(e.target.value)}
- L51 input Opening Date: type="date"; value={draft.openingDate}; readOnly={readOnly || posted}; onChange={e => setDraft({ ...draft, openingDate: e.target.value })}
- L52 input Minimum Level: type="number"; value={draft.minLevel ?? ''}; readOnly={readOnly}; min="0"; step="any"; onChange={e => setDraft({ ...draft, minLevel: e.target.value === '' ? undefined : Number(e.target.value) })}
- L79 input: aria-label="Search consumables"; type="search"; value={query}; onChange={e => setQuery(e.target.value)}
- L79 select: aria-label="Consumable category filter"; value={category}; onChange={e => setCategory(e.target.value)}
- L79 select: aria-label="Consumable unit filter"; value={unit}; onChange={e => setUnit(e.target.value)}

Table headers and mapped label/option arrays (includes filter/UI enums):

- L76 mapped labels/options: [['Consumables', items.length], ['Imported Spare', items.filter(item => item.category === 'imported').length], ['Local Spare', items.filter(item => item.category === 'local').length], ['Below Minimum', items.filter(item => item.minLevel !== undefined && consumableBalance(item, movements).currentStock < item.minLevel).length]]
- L78 mapped labels/options: ['levels', 'movements']
- L80 mapped labels/options: ['Name', 'Category', 'Opening Stock', 'Stock IN', 'Stock OUT', 'Current Stock', 'Unit', 'Status', 'Actions']
- L80 mapped labels/options: ['Date', 'Name', 'Category', 'Type', 'Quantity', 'Unit', 'Reference', 'Remarks']
- L80 {label}
- L86 mapped labels/options: [['Opening Stock', fmt(item.openingStock)], ['Stock IN', fmt(consumableBalance(item, movements).stockIn)], ['Stock OUT', fmt(consumableBalance(item, movements).stockOut)], ['Status', statusLabel(item, consumableBalance(item, movements).currentStock)]]

### src/pages/Costing/CostingFields.tsx

Actions and submission/navigation handlers:

- L10 button: Remove — onClick={() => onChange(materials.filter(row => row.id !== m.id))}; type="button"
- L10 button: Add material — onClick={() => onChange([...materials, emptyMaterial()])}; type="button"
- L14 button: Remove — onClick={() => onChange(processes.filter(row => row.id !== p.id))}; type="button"
- L14 button: Add process cost — onClick={() => onChange([...processes, emptyProcess()])}; type="button"

Form fields and binding/validation evidence:

- L10 select: aria-label={`Recipe material ${i + 1}`}; value={m.materialId}; onChange={e => { const raw = RAW_MATERIALS.find(r => r.id === e.target.value); edit(m.id, { materialId: raw?.id ?? '', name: raw?.name ?? '', unit: raw?.unit ?? '', priceUnit: raw?.unit ?? '' }); }}
- L10 input: aria-label={`Recipe quantity ${i + 1}`}; type="number"; value={num(mode === 'quantities' ? m.quantity : m.percentage)}; min="0"; step="any"; onChange={e => edit(m.id, { [mode === 'quantities' ? 'quantity' : 'percentage']: e.target.valueAsNumber })}
- L10 select: aria-label={`Purchase currency ${i + 1}`}; value={m.currency}; onChange={e => edit(m.id, { currency: e.target.value as MaterialRecipe['currency'] })}
- L10 input: aria-label={`Purchase price ${i + 1}`}; type="number"; value={num(m.price)}; min="0"; step="any"; onChange={e => edit(m.id, { price: e.target.valueAsNumber })}
- L10 input: aria-label={`Price unit ${i + 1}`}; value={m.priceUnit}; onChange={e => edit(m.id, { priceUnit: e.target.value })}
- L10 input: aria-label={`Exchange rate ${i + 1}`}; type="number"; value={num(m.exchangeRate)}; min="0"; step="any"; onChange={e => edit(m.id, { exchangeRate: e.target.valueAsNumber })}
- L10 select: aria-label={`Cost group ${i + 1}`}; value={m.costGroup}; onChange={e => edit(m.id, { costGroup: e.target.value as MaterialRecipe['costGroup'] })}
- L14 input Process: aria-label={`Process name ${i + 1}`}; value={p.name}; onChange={e => edit(p.id, { name: e.target.value })}
- L14 select Routing Stage (optional): value={p.stageId ?? ''}; onChange={e => edit(p.id, { stageId: e.target.value || undefined })}
- L14 select Cost Basis: value={p.basis}; onChange={e => edit(p.id, { basis: e.target.value as ProcessCost['basis'], unit: e.target.value === 'per kg' ? 'kg' : e.target.value === 'per piece' ? 'pcs' : 'batch' })}
- L14 input Rate: type="number"; value={num(p.rate)}; min="0"; step="any"; onChange={e => edit(p.id, { rate: e.target.valueAsNumber })}
- L14 input Quantity ( ): type="number"; value={num(p.quantity)}; disabled={p.basis === 'fixed'}; min="0"; step="any"; onChange={e => edit(p.id, { quantity: e.target.valueAsNumber })}
- L14 input Remarks: value={p.remarks}; onChange={e => edit(p.id, { remarks: e.target.value })}

Table headers and mapped label/option arrays (includes filter/UI enums):

- L10 {label}
- L14 mapped labels/options: ['per kg', 'per piece', 'per batch', 'fixed']

### src/pages/Costing/CostingPage.tsx

Actions and submission/navigation handlers:

- L99 button: {tab === "costing" ? "Item/Model Costing" : tab === "custom" ? "Custom Costing & Estimates" : "Exchange Rates"} — onClick={() => setView(tab)}; type="button"
- L158 form: Currency setCurrency(event.target.value as Currency)} className="mt-1 block w-full rounded-card border border-gray-200 bg-white px-3 py-2 text-sm text-ink focus:border-blue focus:outline-none"> {(["USD", "NGN", "GHS", "ZAR"] as const).map((option) => {option})} Rate setRate(event.target.value)} placeholder="e.g. 1552" className="mt-1 block w-full rounded-card border border-gray-200 px-3 py-2 text-sm text-ink focus:border-blue focus:outline-none" /> Date setDate(event.target.value)} className="mt-1 block w-full rounded-card border border-gray-200 px-3 py-2 text-sm text-ink focus:border-blue focus:outline-none" /> {submitting ? "Logging…" : "Log rate"} — onSubmit={handleLogRate}
- L174 button: {submitting ? "Logging…" : "Log rate"} — type="submit"; disabled={submitting}

Form fields and binding/validation evidence:

- L162 select Currency: value={currency}; onChange={(event) => setCurrency(event.target.value as Currency)}
- L168 input Rate: type="number"; value={rate}; min="0"; step="0.01"; onChange={(event) => setRate(event.target.value)}
- L172 input Date: type="date"; value={date}; onChange={(event) => setDate(event.target.value)}

Table headers and mapped label/option arrays (includes filter/UI enums):

- L96 mapped labels/options: ["costing", "custom", "rates"]
- L124 Item/Model
- L125 Raw Material Cost
- L126 Production Cost
- L127 Other Cost
- L128 Currency
- L129 Exchange Rate Used
- L130 Total (local currency)
- L131 Last Updated
- L163 mapped labels/options: ["USD", "NGN", "GHS", "ZAR"]
- L187 Currency
- L188 Rate
- L189 Date
- L190 Entered by

### src/pages/Costing/CustomCosting.tsx

Actions and submission/navigation handlers:

- L48 button: Open costing from quoted model revision — onClick={() => begin(quotationLine?.modelId ?? "")}; disabled={!quotationLine || quotation.status !== "Draft"}
- L48 Link: Return to quotation — to={`/quotations/${quotation.id}/edit`}
- L48 Link: Return to {order.orderNumber} — to={`/sales-orders/${order.id}`}
- L50 form: A. Product Details{draft.customer} · {draft.product} · {draft.quantity} {draft.unit} · Model Revision {draft.modelRevision}Specifications setDraft({ ...draft, specifications: e.target.value })} className={ENTRY_INPUT} />This sheet costs the entire stated order. Enter total material/process quantities for that order. Order units are never treated as material mass automatically. B. Material Recipe{proposedJob?.requirementsReviewRequired && Job Card routing/materials changed. Review revised quantities and process rates before approval. setDraft({ ...draft, recipeMode: 'quantities', materials: (proposedJob.requiredMaterials ?? []).map(m => ({ ...(draft.materials.find(row => row.materialId === m.materialId) ?? emptyMaterial()), materialId: m.materialId ?? '', name: m.name, quantity: m.requiredQuantity, unit: m.unit, priceUnit: draft.materials.find(row => row.materialId === m.materialId)?.priceUnit ?? m.unit })), processes: (proposedJob.productionStages ?? []).filter(s => s.required && s.kind === 'production').map(s => ({ ...(draft.processes.find(p => p.stageId === s.id) ?? emptyProcess()), stageId: s.id, name: s.name })) })}>Apply proposed materials and route stages to this draftPrices match by stable material ID and process-stage ID. New process rates remain blank for review; no cost formula is invented.}Recipe basis setDraft({ ...draft, recipeMode: e.target.value as CostingInput['recipeMode'] })} className={ENTRY_INPUT}>Actual total quantitiesProportions × production batchTotal batch quantity editNumber('batchQuantity', e.target.valueAsNumber)} className={ENTRY_INPUT} />Batch unit setDraft({ ...draft, batchUnit: e.target.value })} className={ENTRY_INPUT} />{draft.recipeMode === 'quantities' && totals && totals.materials.every(m => m.mixingPercent !== null) && setDraft({ ...draft, recipeMode: 'percentages', batchUnit: 'kg', batchQuantity: totals!.materials.reduce((sum, m) => sum + convertQuantity(m.quantity, m.unit, 'kg'), 0), materials: draft.materials.map((m, i) => ({ ...m, percentage: totals!.materials[i].mixingPercent! })) })}>Convert actual mix to percentage recipe} setDraft({ ...draft, materials })} />Supported mass conversions: 1 kg = 1,000 g; 1 tonne = 1,000 kg. Other units must match exactly. Mixing percentages are shown only for comparable mass units. C. Currency & Exchange RateEstimate Currency setDraft({ ...draft, currency: e.target.value as CostingInput['currency'] })} className={ENTRY_INPUT}>UGXUSDEach recipe exchange rate is estimate currency per one purchase currency (e.g. UGX per USD). Same-currency conversion uses 1. Enter new rates when changing currencies; no current rate overrides a saved revision. Purchase prices are entered net; VAT removal from the source workbook needs client clarification. D. Production Costs m.id === draft.modelId && m.revision === draft.modelRevision)?.routing} processes={draft.processes} onChange={processes => setDraft({ ...draft, processes })} />{(['overheads', 'additionalCosts'] as const).map(key => {key === 'overheads' ? 'Other Overheads' : 'Additional Applicable Costs'} ({draft.currency}) editNumber(key, e.target.valueAsNumber)} className={ENTRY_INPUT} />)}Printing ink is a separately labelled recipe cost group. Process rates are in estimate currency; fixed charges apply once and other bases use the entered quantity. E. Waste AllowanceWaste % editNumber('wastePercent', e.target.valueAsNumber)} className={ENTRY_INPUT} />Cost allowance basis setDraft({ ...draft, wasteBasis: e.target.value as CostingInput['wasteBasis'] })} className={ENTRY_INPUT}>Materials + inkMaterials + ink + processesWaste is an explicit cost allowance. It does not silently increase material requirements or imply production yield. F. Profit / MarkupPricing Method setDraft({ ...draft, pricingMethod: e.target.value as CostingInput['pricingMethod'] })} className={ENTRY_INPUT}>Markup on Cost (workbook method)Gross Profit Margin (Accounts/Admin){draft.pricingMethod === 'markup' ? 'Markup on Cost %' : 'Gross Profit Margin %'}{canCustom ? editNumber('markupPercent', e.target.valueAsNumber)} className={ENTRY_INPUT} /> : editNumber('markupPercent', Number(e.target.value))} className={ENTRY_INPUT}>{MARKUP_SCENARIOS.map(n => {n})}}{totals && {['Markup on Cost', 'Production Cost', 'Profit', 'Before Tax', 'Charges', 'Tax', 'Final Price', 'Unit Price', 'Order Estimate'].map(label => {label})}{MARKUP_SCENARIOS.map(n => { const t = calculateCost({ ...draft, pricingMethod: 'markup', markupPercent: n }); return {[`${n}%`, t.costOfProduction, t.profit, t.sellingBeforeTax, t.charges, t.tax, t.grandTotal, t.unitSellingPrice, t.grandTotal].map((v, j) => {typeof v === 'number' ? v.toFixed(2) : v})}; })}} G. Taxes & Charges{(['taxPercent', 'chargePercent', 'minimumCharge'] as const).map(key => {{ taxPercent: 'Applicable Tax %', chargePercent: 'Additional Charge %', minimumCharge: `Minimum Charge (${draft.currency}, converted by user)` }[key]} editNumber(key, e.target.valueAsNumber)} className={ENTRY_INPUT} />)} setDraft({ ...draft, taxOnCharges: e.target.checked })} /> Include charges in tax baseCharge = higher of configured minimum or percentage of selling price. No levy rate, USD minimum or 18% VAT is imposed universally. setDraft({...draft,led})} productId={item?.itemId??quotationLine?.productId} modelId={draft.modelId} quantity={draft.quantity} unit={draft.unit} date={quotation?.date??order?.date??today()} currency={draft.currency} netSelling={baseTotals?.sellingBeforeTax??0} productionCost={baseTotals?.costOfProduction}/> H. Final Estimate{totals && }Valid Until setDraft({ ...draft, validityDate: e.target.value })} className={ENTRY_INPUT} />Delivery Terms setDraft({ ...draft, deliveryTerms: e.target.value })} className={ENTRY_INPUT} />Customer Remarks setDraft({ ...draft, remarks: e.target.value })} className={ENTRY_INPUT} />{validation && {validation}}Save costing {existingId ? 'revision' : 'draft'} setDraft(null)}>Cancel — onSubmit={submit}
- L51 button: Apply proposed materials and route stages to this draft — onClick={() => setDraft({ ...draft, recipeMode: 'quantities', materials: (proposedJob.requiredMaterials ?? []).map(m => ({ ...(draft.materials.find(row => row.materialId === m.materialId) ?? emptyMaterial()), materialId: m.materialId ?? '', name: m.name, quantity: m.requiredQuantity, unit: m.unit, priceUnit: draft.materials.find(row => row.materialId === m.materialId)?.priceUnit ?? m.unit })), processes: (proposedJob.productionStages ?? []).filter(s => s.required && s.kind === 'production').map(s => ({ ...(draft.processes.find(p => p.stageId === s.id) ?? emptyProcess()), stageId: s.id, name: s.name })) })}; type="button"
- L51 button: Convert actual mix to percentage recipe — onClick={() => setDraft({ ...draft, recipeMode: 'percentages', batchUnit: 'kg', batchQuantity: totals!.materials.reduce((sum, m) => sum + convertQuantity(m.quantity, m.unit, 'kg'), 0), materials: draft.materials.map((m, i) => ({ ...m, percentage: totals!.materials[i].mixingPercent! })) })}; type="button"
- L58 button: Save costing {existingId ? 'revision' : 'draft'} — disabled={!totals} [implicit submit if inside form; otherwise no click handler]
- L58 button: Cancel — onClick={() => setDraft(null)}; type="button"
- L59 Link: Costing → Trace — to={`/track-trace?orderId=${e.input.orderId||e.salesOrderReferences?.[0]?.orderId||''}`}
- L59 button: {e.approvedAt || e.generatedAt || e.usedByJobCardId ? 'Create New Revision' : 'Edit Draft'} — onClick={() => editEstimate(e)}
- L59 button: Send for Review — onClick={() => run(() => setStatus(e.id, 'Pending Review'))}
- L59 button: Approve Costing — onClick={() => run(() => setStatus(e.id, 'Approved'))}
- L59 button: Request Revision — onClick={() => run(() => setStatus(e.id, 'Revision Required'))}
- L59 button: Generate Estimate — onClick={() => run(() => { generate(e.id); setPreviewId(e.id); })}; disabled={e.status === 'Superseded' || e.status === 'Revision Required'}
- L59 button: Preview Estimate — onClick={() => setPreviewId(e.id)}
- L59 button: Record Customer Acceptance — onClick={() => run(() => accept(e.id, true))}
- L59 button: Record Customer Rejection — onClick={() => run(() => accept(e.id, false))}
- L66 button: Print Customer Estimate — onClick={() => window.print()}; type="button"
- L66 button: Close — onClick={onClose}; type="button"

Form fields and binding/validation evidence:

- L48 select Sales Order: value={order?.id ?? ''}; onChange={e => { setParams({ orderId: e.target.value }); setDraft(null); }}
- L48 select Custom Order Line: value={item?.id ?? ''}; onChange={e => { setParams({ orderId: order!.id, itemId: e.target.value }); setDraft(null); }}
- L48 select Use Model: value=""; disabled={!item}; onChange={e => begin(e.target.value)}
- L50 textarea Specifications: value={draft.specifications}; onChange={e => setDraft({ ...draft, specifications: e.target.value })}
- L51 select Recipe basis: value={draft.recipeMode}; onChange={e => setDraft({ ...draft, recipeMode: e.target.value as CostingInput['recipeMode'] })}
- L51 input Total batch quantity: type="number"; value={draft.batchQuantity}; min="0"; step="any"; onChange={e => editNumber('batchQuantity', e.target.valueAsNumber)}
- L51 input Batch unit: value={draft.batchUnit}; onChange={e => setDraft({ ...draft, batchUnit: e.target.value })}
- L52 select Estimate Currency: value={draft.currency}; onChange={e => setDraft({ ...draft, currency: e.target.value as CostingInput['currency'] })}
- L53 input ( ): type="number"; value={draft[key]}; min="0"; step="any"; onChange={e => editNumber(key, e.target.valueAsNumber)}
- L54 input Waste %: type="number"; value={draft.wastePercent}; min="0"; max="100"; step="any"; onChange={e => editNumber('wastePercent', e.target.valueAsNumber)}
- L54 select Cost allowance basis: value={draft.wasteBasis}; onChange={e => setDraft({ ...draft, wasteBasis: e.target.value as CostingInput['wasteBasis'] })}
- L55 select Pricing Method: value={draft.pricingMethod}; disabled={!canCustom}; onChange={e => setDraft({ ...draft, pricingMethod: e.target.value as CostingInput['pricingMethod'] })}
- L55 input: type="number"; value={draft.markupPercent}; min="0"; step="any"; onChange={e => editNumber('markupPercent', e.target.valueAsNumber)}
- L55 select: value={draft.markupPercent}; onChange={e => editNumber('markupPercent', Number(e.target.value))}
- L56 input: type="number"; value={draft[key]}; min="0"; step="any"; onChange={e => editNumber(key, e.target.valueAsNumber)}
- L56 input Include charges in tax base: type="checkbox"; onChange={e => setDraft({ ...draft, taxOnCharges: e.target.checked })}
- L58 input Valid Until: type="date"; value={draft.validityDate}; onChange={e => setDraft({ ...draft, validityDate: e.target.value })}
- L58 input Delivery Terms: value={draft.deliveryTerms}; onChange={e => setDraft({ ...draft, deliveryTerms: e.target.value })}
- L58 input Customer Remarks: value={draft.remarks}; onChange={e => setDraft({ ...draft, remarks: e.target.value })}

Table headers and mapped label/option arrays (includes filter/UI enums):

- L28 mapped labels/options: ['admin', 'accounts']
- L53 mapped labels/options: ['overheads', 'additionalCosts']
- L55 mapped labels/options: ['Markup on Cost', 'Production Cost', 'Profit', 'Before Tax', 'Charges', 'Tax', 'Final Price', 'Unit Price', 'Order Estimate']
- L55 {label}
- L56 mapped labels/options: ['taxPercent', 'chargePercent', 'minimumCharge']
- L63 mapped labels/options: [['Materials', t.materialCost], ['Printing Ink', t.inkCost], ['Process Costs', t.processCost], ['Waste Allowance', t.wasteCost], ['Overheads', estimate.input.overheads], ['Additional Costs', estimate.input.additionalCosts], ['Cost of Production', t.costOfProduction], ['Profit / Markup', t.profit], ['Before Tax', t.sellingBeforeTax], ['Charges', t.charges], ['Applicable Tax', t.tax], ['Grand Total', t.grandTotal], ['Unit Selling Price (tax inclusive)', t.unitSellingPrice]]
- L66 mapped labels/options: [['Customer', e.customer], ['Product', e.product], ['Model', `${modelName} · Revision ${e.modelRevision}`], ['Specifications', e.specifications], ['Quantity', `${e.quantity} ${e.unit}`], ['Unit Selling Price (tax inclusive)', `${e.currency} ${e.unitSellingPrice.toFixed(2)}`], ['Subtotal before charges/tax', `${e.currency} ${e.subtotal.toFixed(2)}`], ['Applicable Charges', `${e.currency} ${e.charges.toFixed(2)}`], ['LED (Higher of the Two)', `${e.currency} ${(e.led?.selectedAmount??0).toFixed(2)}`], ['Applicable Tax', `${e.currency} ${e.tax.toFixed(2)}`], ['Grand Total', `${e.currency} ${e.grandTotal.toFixed(2)}`], ['Valid Until', e.validityDate], ['Delivery Terms', e.deliveryTerms], ['Remarks', e.remarks]]

### src/pages/Dashboard.tsx

Actions and submission/navigation handlers:

- L21 Link: {title} — to={link}

Table headers and mapped label/option arrays (includes filter/UI enums):

- L25 mapped labels/options: ['admin','accounts','production_manager']
- L30 mapped labels/options: ['Draft','PendingApproval']

### src/pages/FinanceDashboard.tsx

Actions and submission/navigation handlers:

- L51 Link: View quotations — to="/quotations"
- L78 Link: {activity.title}{activity.detail} {activity.date} — to={activity.href}
- L96 Link: Finance Dashboard — to="/"

Table headers and mapped label/option arrays (includes filter/UI enums):

- L34 mapped labels/options: ["Draft", "Pending Internal Approval", "Approved", "Sent"]
- L35 mapped labels/options: ["Completed", "Dispatched", "Cancelled"]

### src/pages/JobCards/JobCardDetail.tsx

Actions and submission/navigation handlers:

- L45 Link: Back to Job Cards — to="/job-cards"
- L60 Link: Back to Job Cards — to="/job-cards"
- L61 Link: {card.salesOrderNumber ?? card.salesOrderId} — to={`/sales-orders/${card.salesOrderId}`}
- L61 button: Edit — onClick={() => setForm('edit')}
- L61 button: Approve {parent?.manufacturingItems ? 'all manufacturing items' : 'Job Card'} — onClick={() => run(() => approve(parent?.id ?? card.id), 'Approved and forwarded to Store Issue Pending.')}
- L61 button: Issue Materials — onClick={() => setForm('issue')}
- L61 button: Transfer to Finished Goods — onClick={() => setForm('transfer')}
- L62 button: {item.product} · {fmtQuantity(item.qty, item.unit)} · — onClick={() => setSearch({ item: item.id })}
- L63 Link: Record / review production QC — to="/qc/production"
- L63 Link: {i.number} — to={`/qc/inspections/${i.id}`}
- L66 Link: Job Card → Trace — to={`/track-trace?jobId=${card.id}`}
- L69 button: {name} — onClick={() => setTab(name)}
- L72 button: Issue Materials — onClick={() => setForm('issue')}
- L75 button: {saving ? 'Saving…' : 'Save stage sequence'} — onClick={() => void save()}; disabled={saving}
- L77 button: Update {stage.name} — onClick={() => setStageId(stage.id)}
- L77 button: {stage.required ? 'Remove stage' : 'Add stage'} — onClick={() => run(() => toggleStage(card.id, stage.id), 'Stage requirement updated in frontend state.')}
- L85 button: Post Prepared Stock IN — onClick={() => run(() => postPreparedReceipts(card.id, stockProduct), 'QC-prepared receipts posted to shared Finished Goods inventory.')}
- L86 Link: Stock transaction {receipt.id} — to="/stock"

Form fields and binding/validation evidence:

- L85 select Finished Product: value={stockProduct}; onChange={e => setStockProduct(e.target.value)}

Table headers and mapped label/option arrays (includes filter/UI enums):

- L23 mapped labels/options: ['Overview', 'Materials', 'Costing', 'Production Routing', 'Production Tracking', 'Waste', 'Activity History']
- L49 mapped labels/options: ['production_manager', 'admin']
- L49 mapped labels/options: ['Draft', 'PendingApproval']
- L50 mapped labels/options: ['production_manager', 'admin']
- L50 mapped labels/options: ['Draft', 'PendingApproval']
- L51 mapped labels/options: ['store_keeper', 'admin']
- L51 mapped labels/options: ['Approved', 'StoreIssuePending', 'MaterialIssued', 'Issued']
- L52 mapped labels/options: ['production_operator', 'production_manager', 'admin']
- L52 mapped labels/options: ['MaterialIssued', 'Issued', 'InProduction', 'OnHold']
- L53 mapped labels/options: ['store_keeper', 'admin']
- L58 mapped labels/options: [['Job Card No.', card.jobCardNumber], ['Sales Order No.', card.salesOrderNumber ?? 'Not recorded'], ['Customer', card.customerName ?? 'Not recorded'], ['Model', card.modelName], ['Model Revision', String(card.modelRevision ?? 'Not recorded')], ['Costing Revision', String(card.estimateRevision ?? 'Not recorded')], ['Product', card.product ?? 'Not recorded'], ['Specifications', card.specifications ?? 'Not recorded'], ['Order Quantity', fmtQuantity(card.qty, card.unit)], ['Required Date', jobDate(card.requiredDate)], ['Created Date', jobDate(card.createdDate)], ['Production Requirements', card.productionRequirements ?? 'Not configured'], ['Current Department', location.department], ['Current Stage', location.stage]]
- L67 mapped labels/options: ['Specifications', 'Production Requirements', 'Job Card No.', 'Sales Order No.']
- L68 mapped labels/options: [["Order Quantity", fmtQuantity(card.qty, card.unit)], ['Total Produced (final production stage)', fmtQuantity(totals.produced, totals.unit)], ['Total Waste (by unit)', totals.waste], ['Accepted Finished Quantity', fmtQuantity(card.acceptedQuantity, card.stockTransfer?.unit ?? totals.unit)], ['Production / Batch Date', jobDate(card.stockTransfer?.batchDate)], ['Confirmed By', card.stockTransfer?.confirmedBy ?? 'Not confirmed']]
- L71 mapped labels/options: [["Approval Status", 'Approved'], ['Approved By', card.approval.approvedBy], ['Approved Date/Time', jobDate(card.approval.approvedAt)]]
- L71 mapped labels/options: ["Approval Status", 'Approved']
- L71 mapped labels/options: ['PendingApproval', 'Draft']
- L72 mapped labels/options: ['Material', 'Required Quantity', 'Unit', 'Issued Quantity', 'Balance Quantity', 'Issue Status']
- L72 {label}
- L77 mapped labels/options: [["Stage Name", stage.name], ['Department', stage.department], ['Sequence', String(stage.sequence)], ['Input Quantity', fmtQuantity(stage.inputQuantity, stage.inputUnit)], ['Output Quantity', fmtQuantity(stage.outputQuantity, stage.outputUnit)], ['Waste Quantity', fmtQuantity(stage.wasteQuantity, stage.wasteUnit)], ['Started Date/Time', jobDate(stage.startedAt)], ['Completed Date/Time', jobDate(stage.completedAt)], ['Operator / Responsible Person', stage.operator || 'Not assigned'], ['Machine', stage.machine || 'Not configured'], ['Planned Input', fmtQuantity(stage.expectedInput, stage.inputUnit)], ['Planned Output / Yield', fmtQuantity(stage.expectedOutput, stage.outputUnit)], ['Instructions', stage.instructions || '—'], ['Remarks', stage.remarks || '—']]
- L79 mapped labels/options: ['Date', 'Item', 'Model', 'Job Card', 'Department / Process', 'Production Quantity', 'Waste Quantity', 'Waste Type / Category', 'Reason', 'Quantity Sent to Recycling', 'Remaining Waste', 'Remarks']
- L79 {label}
- L85 mapped labels/options: ['admin', 'store_keeper']

### src/pages/JobCards/JobCardForms.tsx

Actions and submission/navigation handlers:

- L30 button: (icon/dynamic content) — onClick={onClose}; type="button"; aria-label="Close"
- L45 form: {([['modelName', 'Model'], ['product', 'Product'], ['qty', 'Order Quantity'], ['unit', 'Unit'], ['requiredDate', 'Required Date']] as const).map(([key, label]) => {label} setDraft({ ...draft, [key]: e.target.value })} className={`${ENTRY_INPUT} mt-1`} />)} {([['specifications', 'Specifications'], ['productionRequirements', 'Production Requirements']] as const).map(([key, label]) => {label} setDraft({ ...draft, [key]: e.target.value })} className={`${ENTRY_INPUT} mt-1`} />)} Editing quantity or requirements does not calculate a material BOM automatically. {error && {error}} CancelSave Job Card — onSubmit={submit}
- L45 button: Cancel — onClick={onClose}; type="button"
- L45 button: Save Job Card [implicit submit if inside form; otherwise no click handler]
- L53 form: Frontend issue only. Raw Material stock is unchanged. Unrecorded availability requires Store confirmation before real posting. setValues(Object.fromEntries(materials.map(m => [m.id, String(Math.max(0, m.requiredQuantity - m.issuedQuantity))])))}>Full Issue — Fill Remaining {materials.map(m => {m.name}Required{fmtQuantity(m.requiredQuantity, m.unit)}Already Issued{fmtQuantity(m.issuedQuantity, m.unit)}Remaining{fmtQuantity(Math.max(0, m.requiredQuantity - m.issuedQuantity), m.unit)}Available{fmtQuantity(available[m.id], m.unit)}Issue Quantity — {m.name} setValues({ ...values, [m.id]: e.target.value })} className={`${ENTRY_INPUT} mt-1`} />Unit: {m.unit}. Enter less than the remaining requirement for a partial issue.)} {error && {error}} CancelRecord Material Issue — onSubmit={submit}
- L53 button: Full Issue — Fill Remaining — onClick={() => setValues(Object.fromEntries(materials.map(m => [m.id, String(Math.max(0, m.requiredQuantity - m.issuedQuantity))])))}; type="button"
- L53 button: Cancel — onClick={onClose}; type="button"
- L53 button: Record Material Issue [implicit submit if inside form; otherwise no click handler]
- L69 form: {stage.handover && Previous stage output: {fmtQuantity(stage.handover.quantity, stage.handover.unit)}. {received ? 'Received input is prefilled and locked.' : 'This stage uses a different input unit; record received input explicitly.'}} {([['inputQuantity', 'Input Quantity'], ['outputQuantity', 'Output Quantity'], ['wasteQuantity', 'Waste Quantity']] as const).map(([key, label]) => {label} setDraft({ ...draft, [key]: e.target.value })} className={`${ENTRY_INPUT} mt-1`} />)}{([['inputUnit', 'Input Unit'], ['outputUnit', 'Output Unit'], ['wasteUnit', 'Waste Unit'], ['operator', 'Operator / Responsible Person'], ['wasteType', 'Waste Type / Category'], ['wasteReason', 'Waste Reason']] as const).map(([key, label]) => {label} setDraft({ ...draft, [key]: e.target.value })} className={`${ENTRY_INPUT} mt-1`} />)}Quantity Sent to Recycling setDraft({ ...draft, sentToRecycling: e.target.value })} className={`${ENTRY_INPUT} mt-1`} />Status setDraft({ ...draft, status: e.target.value as JobProductionStage['status'] })} className={`${ENTRY_INPUT} mt-1`}>{Object.entries(PRODUCTION_STATUS_LABELS).map(([id, label]) => {label})}Start Date/Time setDraft({ ...draft, startedAt: e.target.value })} className={`${ENTRY_INPUT} mt-1`} />Completion Date/Time setDraft({ ...draft, completedAt: e.target.value })} className={`${ENTRY_INPUT} mt-1`} /> Number(draft.inputQuantity)} onClick={() => setDraft({ ...draft, wasteQuantity: String(Math.round((Number(draft.inputQuantity) - Number(draft.outputQuantity)) * 1e6) / 1e6) })}>Calculate Waste (same units) Remarks setDraft({ ...draft, remarks: e.target.value })} className={`${ENTRY_INPUT} mt-1`} /> Recycling quantities are Job Card tracking only; no Recycling movement is posted. Completed records are locked. {error && {error}} CancelSave StageComplete &amp; Send to Next Stage — onSubmit={submit}
- L70 button: Calculate Waste (same units) — onClick={() => setDraft({ ...draft, wasteQuantity: String(Math.round((Number(draft.inputQuantity) - Number(draft.outputQuantity)) * 1e6) / 1e6) })}; type="button"; disabled={!draft.inputUnit || draft.inputUnit !== draft.outputUnit || draft.inputUnit !== draft.wasteUnit || draft.inputQuantity === '' || draft.outputQuantity === '' || Number(draft.outputQuantity) > Number(draft.inputQuantity)}
- L70 button: Cancel — onClick={onClose}; type="button"
- L70 button: Save Stage — value="save" [implicit submit if inside form; otherwise no click handler]
- L70 button: Complete &amp; Send to Next Stage — value="complete" [implicit submit if inside form; otherwise no click handler]
- L86 form: Job: {card.jobCardNumber} · Sales Order: {card.salesOrderNumber} · Customer: {card.customerName} · Product: {card.product} · Model: {card.modelName} · Remaining unaccounted: {remaining} {totals.unit}. Final produced quantity: {fmtQuantity(totals.produced, totals.unit)} Authorized QC Batch / Lot setBatch(e.target.value)} className={ENTRY_INPUT}>Select authorized batch{authorizedBatches.map(r => {r.subject.batchNumber} · Approved {r.acceptedQuantity} / Rejected {r.rejectedQuantity} {r.unit})} Rejected Quantity setRejected(e.target.value)} className={ENTRY_INPUT} /> setVerified(e.target.checked)} /> QC verified accepted quantity Accepted Finished Quantity setAccepted(e.target.value)} className={`${ENTRY_INPUT} mt-1`} /> Production / Batch Date setBatchDate(e.target.value)} className={`${ENTRY_INPUT} mt-1`} /> Confirm that QC accepted this quantity. Rejected this batch: {rejected} {totals.unit}. Remaining quantity can be received in another batch. Posts Finished Goods Stock IN in shared frontend state; no dispatch occurs. Location is not configured. {error && {error}} CancelConfirm Transfer — onSubmit={submit}
- L86 button: Cancel — onClick={onClose}; type="button"
- L86 button: Confirm Transfer [implicit submit if inside form; otherwise no click handler]

Form fields and binding/validation evidence:

- L45 input: type={key === 'qty' ? 'number' : key === 'requiredDate' ? 'date' : 'text'}; value={draft[key]}; min={key === 'qty' ? '0.000001' : key === 'requiredDate' ? card.createdDate?.slice(0, 10) : undefined}; step={key === 'qty' ? 'any' : undefined}; onChange={e => setDraft({ ...draft, [key]: e.target.value })}
- L45 textarea: value={draft[key]}; onChange={e => setDraft({ ...draft, [key]: e.target.value })}
- L53 input Issue Quantity —: aria-label={`Issue quantity ${m.name}`}; type="number"; value={values[m.id] ?? ''}; min="0"; max={Math.max(0, m.requiredQuantity - m.issuedQuantity)}; step="any"; onChange={e => setValues({ ...values, [m.id]: e.target.value })}
- L69 input: type="number"; value={draft[key]}; readOnly={key === 'inputQuantity' && received}; min="0"; step="any"; onChange={e => setDraft({ ...draft, [key]: e.target.value })}
- L69 input: value={draft[key]}; readOnly={lockUnits && ['inputUnit', 'outputUnit', 'wasteUnit'].includes(key) || key === 'inputUnit' && received}; onChange={e => setDraft({ ...draft, [key]: e.target.value })}
- L69 input Quantity Sent to Recycling: type="number"; value={draft.sentToRecycling}; min="0"; step="any"; onChange={e => setDraft({ ...draft, sentToRecycling: e.target.value })}
- L69 select Status: aria-label="Stage status"; value={draft.status}; onChange={e => setDraft({ ...draft, status: e.target.value as JobProductionStage['status'] })}
- L69 input Start Date/Time: type="datetime-local"; value={draft.startedAt}; onChange={e => setDraft({ ...draft, startedAt: e.target.value })}
- L69 input Completion Date/Time: type="datetime-local"; value={draft.completedAt}; onChange={e => setDraft({ ...draft, completedAt: e.target.value })}
- L70 textarea Remarks: value={draft.remarks}; onChange={e => setDraft({ ...draft, remarks: e.target.value })}
- L86 select Authorized QC Batch / Lot: value={batch}; onChange={e => setBatch(e.target.value)}
- L86 input Rejected Quantity: type="number"; value={rejected}; min="0"; max={remaining}; step="any"; onChange={e => setRejected(e.target.value)}
- L86 input QC verified accepted quantity: type="checkbox"; onChange={e => setVerified(e.target.checked)}
- L86 input Accepted Finished Quantity: type="number"; value={accepted}; min="0"; max={remaining}; step="any"; onChange={e => setAccepted(e.target.value)}
- L86 input Production / Batch Date: type="date"; value={batchDate}; min={card.createdDate?.slice(0, 10)}; max={localToday()}; onChange={e => setBatchDate(e.target.value)}

Table headers and mapped label/option arrays (includes filter/UI enums):

- L45 mapped labels/options: [['modelName', 'Model'], ['product', 'Product'], ['qty', 'Order Quantity'], ['unit', 'Unit'], ['requiredDate', 'Required Date']]
- L45 mapped labels/options: ['modelName', 'Model']
- L45 mapped labels/options: ['product', 'Product']
- L45 mapped labels/options: ['qty', 'Order Quantity']
- L45 mapped labels/options: ['unit', 'Unit']
- L45 mapped labels/options: ['requiredDate', 'Required Date']
- L45 mapped labels/options: [['specifications', 'Specifications'], ['productionRequirements', 'Production Requirements']]
- L45 mapped labels/options: ['specifications', 'Specifications']
- L45 mapped labels/options: ['productionRequirements', 'Production Requirements']
- L69 mapped labels/options: [['inputQuantity', 'Input Quantity'], ['outputQuantity', 'Output Quantity'], ['wasteQuantity', 'Waste Quantity']]
- L69 mapped labels/options: ['inputQuantity', 'Input Quantity']
- L69 mapped labels/options: ['outputQuantity', 'Output Quantity']
- L69 mapped labels/options: ['wasteQuantity', 'Waste Quantity']
- L69 mapped labels/options: [['inputUnit', 'Input Unit'], ['outputUnit', 'Output Unit'], ['wasteUnit', 'Waste Unit'], ['operator', 'Operator / Responsible Person'], ['wasteType', 'Waste Type / Category'], ['wasteReason', 'Waste Reason']]
- L69 mapped labels/options: ['inputUnit', 'Input Unit']
- L69 mapped labels/options: ['outputUnit', 'Output Unit']
- L69 mapped labels/options: ['wasteUnit', 'Waste Unit']
- L69 mapped labels/options: ['operator', 'Operator / Responsible Person']
- L69 mapped labels/options: ['wasteType', 'Waste Type / Category']
- L69 mapped labels/options: ['wasteReason', 'Waste Reason']
- L69 mapped labels/options: ['inputUnit', 'outputUnit', 'wasteUnit']

### src/pages/JobCards/JobCardList.tsx

Actions and submission/navigation handlers:

- L30 button: Clear Filters — onClick={() => setFilters(emptyFilters)}
- L37 Link: {card.jobCardNumber}{card.salesOrderNumber ?? 'Sales order not recorded'} · {card.customerName ?? 'Customer not recorded'}{isDelayed(card) && } {card.manufacturingItems ? {card.manufacturingItems.map(item => {item.product} · {item.modelName} · {fmtQuantity(item.qty, item.unit)} · {currentLocation(item).department} / {currentLocation(item).stage})}Due: {jobDate(card.requiredDate)} · {card.manufacturingItems.length} manufacturing items : } {!card.manufacturingItems && }View Details → — to={`/job-cards/${card.id}`}; aria-label={`View ${card.jobCardNumber}`}

Form fields and binding/validation evidence:

- L26 input: aria-label="Search job cards"; type="search"; value={filters.query}; onChange={e => update('query', e.target.value)}
- L27 select Status: aria-label="Job status filter"; value={filters.status}; onChange={e => update('status', e.target.value)}
- L28 select Department: aria-label="Department filter"; value={filters.department}; onChange={e => update('department', e.target.value)}
- L29 select Current stage: aria-label="Production stage filter"; value={filters.stage}; onChange={e => update('stage', e.target.value)}
- L30 input Created from: aria-label="Created from"; type="date"; value={filters.from}; max={filters.to || undefined}; onChange={e => update('from', e.target.value)}
- L30 input Created to: aria-label="Created to"; type="date"; value={filters.to}; min={filters.from || undefined}; onChange={e => update('to', e.target.value)}

Table headers and mapped label/option arrays (includes filter/UI enums):

- L39 mapped labels/options: [["Model / Product", [card.modelName, card.product !== card.modelName ? card.product : ''].filter(Boolean).join(' · ')], ['Order Quantity', fmtQuantity(card.qty, card.unit)], ['Current Department', location.department], ['Current Production Stage', location.stage], ['Output / Produced Quantity', fmtQuantity(latest?.outputQuantity, latest?.outputUnit)], ['Waste Quantity', totals.waste], ['Required / Due Date', jobDate(card.requiredDate)]]

### src/pages/JobCards/JobCardUI.tsx

Table headers and mapped label/option arrays (includes filter/UI enums):

- L17 mapped labels/options: ['Draft', 'PendingApproval']
- L18 mapped labels/options: ['Approved', 'StoreIssuePending']
- L30 mapped labels/options: ['Received', 'InProgress']

### src/pages/JobCards/JobCosting.tsx

Actions and submission/navigation handlers:

- L8 Link: Open Linked Costing / Estimate — to={`/costing?orderId=${card.salesOrderId}&itemId=${card.salesOrderItemId ?? ''}`}


### src/pages/JobCards/JobRoutingEditor.tsx

Actions and submission/navigation handlers:

- L19 button: Remove — onClick={() => setMaterials(materials.filter(row => row.id !== m.id))}; type="button"
- L19 button: Add required material — onClick={() => setMaterials([...materials, { id: crypto.randomUUID(), name: '', requiredQuantity: 0, issuedQuantity: 0, unit: '' }])}; type="button"
- L19 button: Save Routing Changes — onClick={() => run(() => saveRouting(card.id, stages, materials))}; type="button"
- L19 button: Send Job Card for Review — onClick={() => run(() => sendForReview(card.id))}; type="button"
- L19 button: Request Authorized Revision / Reapproval — onClick={() => run(() => reviseRouting(card.id))}; type="button"
- L19 Link: Review / Recalculate Linked Costing — to={`/costing?orderId=${card.salesOrderId}&itemId=${card.salesOrderItemId}`}
- L19 button: Recalculate Requirements from Reviewed Estimate — onClick={() => run(() => recalculate(card.id, estimateId))}; type="button"

Form fields and binding/validation evidence:

- L19 select Material: value={m.materialId ?? ''}; onChange={e => { const raw = RAW_MATERIALS.find(r => r.id === e.target.value); setMaterials(materials.map(row => row.id === m.id ? { ...row, materialId: raw?.id, name: raw?.name ?? '', unit: raw?.unit ?? '' } : row)); }}
- L19 input Required Quantity: type="number"; value={m.requiredQuantity}; min="0"; step="any"; onChange={e => setMaterials(materials.map(row => row.id === m.id ? { ...row, requiredQuantity: e.target.valueAsNumber } : row))}
- L19 select Approved Costing Revision: value={estimateId}; onChange={e => setEstimateId(e.target.value)}

Table headers and mapped label/option arrays (includes filter/UI enums):

- L17 mapped labels/options: ['admin', 'production_manager']
- L17 mapped labels/options: ['Draft', 'PendingApproval']

### src/pages/JobCards/RoutingFields.tsx

Actions and submission/navigation handlers:

- L11 button: Move up — onClick={() => move(i, -1)}; type="button"; disabled={i === 0}
- L11 button: Move down — onClick={() => move(i, 1)}; type="button"; disabled={i === stages.length - 1}
- L11 button: Remove — onClick={() => publish(stages.filter(row => row.id !== s.id))}; type="button"
- L11 button: Add production stage — onClick={() => publish([...stages, newRoutingStage()])}; type="button"

Form fields and binding/validation evidence:

- L11 select Machine master (optional): value={s.machineId ?? ""}; onChange={e => { const machine = machines.find(m => m.id === e.target.value); edit(s.id, { machineId: machine?.id, machine: machine?.name ?? s.machine }); }}
- L11 input: type="checkbox"; onChange={e => edit(s.id, { qcTemplateIds: e.target.checked ? [...(s.qcTemplateIds ?? []), t.id] : (s.qcTemplateIds ?? []).filter(id => id !== t.id) })}
- L11 input: value={s[key] ?? ''}; onChange={e => edit(s.id, { [key]: e.target.value })}
- L11 input: type="number"; value={s[key] ?? ''}; min="0"; step="any"; onChange={e => edit(s.id, { [key]: e.target.value === '' ? undefined : e.target.valueAsNumber })}
- L11 input Mandatory stage: type="checkbox"; onChange={e => edit(s.id, { required: e.target.checked })}

Table headers and mapped label/option arrays (includes filter/UI enums):

- L11 mapped labels/options: ['name', 'department', 'machine', 'inputUnit', 'outputUnit', 'wasteUnit', 'instructions']
- L11 mapped labels/options: ['expectedInput', 'expectedOutput', 'plannedWastePercent']

### src/pages/Login.tsx

Actions and submission/navigation handlers:

- L58 form: setUsername(e.target.value)} placeholder="you@navapack.com" icon={} required /> setPassword(e.target.value)} placeholder="Enter your password" icon={} required trailing={ setShowPassword((visible) => !visible)} className="absolute right-1 top-1/2 flex h-10 w-10 -translate-y-1/2 items-center justify-center rounded-md text-slate-400 transition hover:bg-slate-50 hover:text-navy">{showPassword ? : }} /> {MOCK_LOGIN_ENABLED && Demo mode: {finance?'finance@navapack.com':'admin@navapack.com'} / test@123{!finance&&Demo role setDemoRole(e.target.value as typeof demoRole)}>AdminAccounts / FinanceQC InspectorQC SupervisorProduction ManagerStore Keeper}} setRemember(e.target.checked)} className="h-4 w-4 rounded border-slate-300 accent-teal" /> Remember meForgot password? {error && {error}} Sign in — onSubmit={handleSubmit}
- L60 button: {showPassword ? : } — onClick={() => setShowPassword((visible) => !visible)}; type="button"; aria-label={showPassword ? "Hide password" : "Show password"}
- L62 a: Forgot password? — href="mailto:support@navapack.com?subject=Password%20reset"
- L66 Link: {finance?'Operations login':'Separate Finance login'} — to={finance?'/login':'/finance/login'}

Form fields and binding/validation evidence:

- L61 select Demo role: value={demoRole}; onChange={e => setDemoRole(e.target.value as typeof demoRole)}
- L62 input Remember me: type="checkbox"; onChange={(e) => setRemember(e.target.checked)}


### src/pages/Masters/MastersPage.tsx

Actions and submission/navigation handlers:

- L100 button: {item.label} — onClick={() => setSelected(masterKey)}; type="button"


### src/pages/Masters/MasterTable.tsx

Actions and submission/navigation handlers:

- L81 button: Add {title.slice(0, -1)} — onClick={openAdd}; type="button"
- L111 button: (icon/dynamic content) — onClick={closeModal}; type="button"; aria-label="Close"
- L113 form: {columns.map((column) => ( {column.label} {column.kind === "stages" ? ( {ALL_MASTER_STAGES.map((stage) => { const active = ((formValues[column.key] as Stage[] | undefined) ?? []).includes(stage); return toggleStage(stage)} className={`rounded-full border px-3 py-1.5 text-xs font-medium ${active ? "border-green bg-green/10 text-green" : "border-gray-200 text-gray-500 hover:border-navy hover:text-navy"}`}>{stage}; })} ) : ( setFormValues({ ...formValues, [column.key]: event.target.value })} className="mt-1 block w-full rounded-card border border-gray-200 px-3 py-2 text-sm text-ink focus:border-blue focus:outline-none" /> )} ))} Cancel Save — onSubmit={handleSubmit}
- L121 button: {stage} — onClick={() => toggleStage(stage)}; type="button"
- L130 button: Cancel — onClick={closeModal}; type="button"
- L131 button: Save — type="submit"

Form fields and binding/validation evidence:

- L125 input: value={String(formValues[column.key] ?? "")}; required={column.key !== "department"}; onChange={(event) => setFormValues({ ...formValues, [column.key]: event.target.value })}

Table headers and mapped label/option arrays (includes filter/UI enums):

- L5 mapped labels/options: ["Extrusion", "Printing", "Packaging", "Stock", "Ready to Sale"]
- L91 {column.label}

### src/pages/Masters/ModelManager.tsx

Actions and submission/navigation handlers:

- L12 button: Create New Custom Model — onClick={() => open()}; type="button"
- L12 button: {m.name} · Revision {m.revision ?? 1} — onClick={() => open(m)}; type="button"
- L12 form: Draft model {draft.name || '(new)'} · {draft.revision ? 'New revision' : 'Revision 1'} {(['name', 'category', 'description', 'specifications', 'dimensions', 'defaultUnit', 'billOfMaterials'] as const).map(key => {{ name: 'Model Name', category: 'Product Category', description: 'Product Description', specifications: 'Specifications', dimensions: 'Dimensions', defaultUnit: 'Default Quantity Unit', billOfMaterials: 'Recipe Description' }[key]} setDraft({ ...draft, [key]: e.target.value })} className={ENTRY_INPUT} />)} Material composition and costing defaults Recipe mode setDraft({ ...draft, recipeMode: e.target.value as Model['recipeMode'] })} className={ENTRY_INPUT}>Actual quantities per configured batchRecipe percentagesReference batch quantity setDraft({ ...draft, batchQuantity: e.target.valueAsNumber })} className={ENTRY_INPUT} />Batch unit setDraft({ ...draft, batchUnit: e.target.value })} className={ENTRY_INPUT} />Default waste % setDraft({ ...draft, wastePercent: e.target.valueAsNumber })} className={ENTRY_INPUT} />Default overhead cost setDraft({ ...draft, overheads: e.target.valueAsNumber })} className={ENTRY_INPUT} /> Cost currency setDraft({ ...draft, costingConfig: { markupPercent: 10, taxPercent: 0, ...draft.costingConfig, currency: e.target.value as 'USD' | 'UGX' } })} className={ENTRY_INPUT}>USDUGXDefault markup % setDraft({ ...draft, costingConfig: { currency: 'UGX', taxPercent: 0, ...draft.costingConfig, markupPercent: e.target.valueAsNumber } })} className={ENTRY_INPUT} />Default tax % setDraft({ ...draft, costingConfig: { currency: 'UGX', markupPercent: 10, ...draft.costingConfig, taxPercent: e.target.valueAsNumber } })} className={ENTRY_INPUT} /> setDraft({ ...draft, recipe })} /> setDraft({ ...draft, processes })} /> Default Production Processes setDraft({ ...draft, routing })} /> {error && {error}} Save reusable model revision setDraft(null)} className="rounded-card border px-4 py-2">Cancel — onSubmit={submit}
- L12 button: Save reusable model revision [implicit submit if inside form; otherwise no click handler]
- L12 button: Cancel — onClick={() => setDraft(null)}; type="button"

Form fields and binding/validation evidence:

- L12 input: value={draft[key] ?? ''}; required={['name', 'defaultUnit'].includes(key)}; onChange={e => setDraft({ ...draft, [key]: e.target.value })}
- L12 select Recipe mode: value={draft.recipeMode ?? 'quantities'}; onChange={e => setDraft({ ...draft, recipeMode: e.target.value as Model['recipeMode'] })}
- L12 input Reference batch quantity: type="number"; value={draft.batchQuantity ?? ''}; min="0"; step="any"; onChange={e => setDraft({ ...draft, batchQuantity: e.target.valueAsNumber })}
- L12 input Batch unit: value={draft.batchUnit ?? 'kg'}; onChange={e => setDraft({ ...draft, batchUnit: e.target.value })}
- L12 input Default waste %: type="number"; value={draft.wastePercent ?? ''}; min="0"; max="100"; step="any"; onChange={e => setDraft({ ...draft, wastePercent: e.target.valueAsNumber })}
- L12 input Default overhead cost: type="number"; value={draft.overheads ?? ''}; min="0"; step="any"; onChange={e => setDraft({ ...draft, overheads: e.target.valueAsNumber })}
- L12 select Cost currency: value={draft.costingConfig?.currency ?? 'UGX'}; onChange={e => setDraft({ ...draft, costingConfig: { markupPercent: 10, taxPercent: 0, ...draft.costingConfig, currency: e.target.value as 'USD' | 'UGX' } })}
- L12 input Default markup %: type="number"; value={draft.costingConfig?.markupPercent ?? 10}; min="0"; step="any"; onChange={e => setDraft({ ...draft, costingConfig: { currency: 'UGX', taxPercent: 0, ...draft.costingConfig, markupPercent: e.target.valueAsNumber } })}
- L12 input Default tax %: type="number"; value={draft.costingConfig?.taxPercent ?? 0}; min="0"; max="100"; step="any"; onChange={e => setDraft({ ...draft, costingConfig: { currency: 'UGX', markupPercent: 10, ...draft.costingConfig, taxPercent: e.target.valueAsNumber } })}

Table headers and mapped label/option arrays (includes filter/UI enums):

- L10 mapped labels/options: ['Stock', 'Ready to Sale']
- L12 mapped labels/options: ['name', 'category', 'description', 'specifications', 'dimensions', 'defaultUnit', 'billOfMaterials']
- L12 mapped labels/options: ['name', 'defaultUnit']

### src/pages/Quality/DailySchedules.tsx

Actions and submission/navigation handlers:

- L10 form: Exact subject / inspection sourceSelect existing inspection{q.inspections.map(i=>{i.number} · {i.template.name} · {i.subject.label})} Start date End date (optional) Shift identifier (per shift only) Assigned QC user ID Save inspection schedule — onSubmit={e=>{e.preventDefault();const f=new FormData(e.currentTarget);run(()=>q.addSchedule(String(f.get('source')),String(f.get('start')),String(f.get('end'))||undefined,String(f.get('shift'))||undefined,String(f.get('assignedTo'))));}}
- L10 button: Save inspection schedule [implicit submit if inside form; otherwise no click handler]
- L11 button: {s.active?'Pause':'Resume'} — onClick={()=>run(()=>q.toggleSchedule(s.id))}
- L11 button: Generate due inspection for selected date — onClick={()=>run(()=>q.generateSchedule(s.id,date))}; disabled={!scheduleDue(s,date)}
- L11 Link: {i.number} · {i.template.name} · {i.status} — to={`/qc/inspections/${i.id}`}

Form fields and binding/validation evidence:

- L9 input Inspection date: type="date"; value={date}; onChange={e=>setDate(e.target.value)}
- L10 select Exact subject / inspection source: name="source"
- L10 input Start date: name="start"; type="date"; defaultValue={date}
- L10 input End date (optional): name="end"; type="date"
- L10 input Shift identifier (per shift only): name="shift"
- L10 input Assigned QC user ID: name="assignedTo"; defaultValue={user?.id}

Table headers and mapped label/option arrays (includes filter/UI enums):

- L9 mapped labels/options: ['admin','qc_supervisor']

### src/pages/Quality/InspectionDetail.tsx

Actions and submission/navigation handlers:

- L16 Link: QC dashboard — to="/qc"
- L22 Link: Quality Control — to="/qc"
- L22 Link: Parent Job Card / manufacturing item — to={`/job-cards/${i.subject.jobCardId}?item=${i.subject.manufacturingItemId}`}
- L22 Link: Original inspection — to={`/qc/inspections/${i.previousInspectionId}`}
- L22 Link: Recycling — to="/recycling"
- L25 form: Decision{([...(['Passed', 'Failed', 'Reinspection Required'] as const), ...(i.subject.kind === 'raw' ? ['Conditionally Accepted' as const] : [])]).map(s => {s})} Review / verification remarks Record Review — onSubmit={onReview}
- L25 button: Record Review [implicit submit if inside form; otherwise no click handler]
- L26 button: Approve Quality / Release — onClick={() => run(() => q.release(id, 'quality'))}
- L27 button: Create linked reinspection — onClick={() => run(() => navigate(`/qc/inspections/${q.reinspection(id).id}`))}
- L28 form: Authorized accepted quantity ({i.subject.unit}) Authorized rejected quantity ({i.subject.unit}) Authorize Finished Goods Stock IN — onSubmit={e => { e.preventDefault(); const f = new FormData(e.currentTarget); run(() => q.release(id, 'finished_stock', Number(f.get('accepted')), Number(f.get('rejected')))); }}
- L28 button: Authorize Finished Goods Stock IN [implicit submit if inside form; otherwise no click handler]
- L30 form: Finding / failed checklist item Severity{['Minor', 'Major', 'Critical'].map(s => {s})} Create Non-Conformance Corrective action register — onSubmit={e => { e.preventDefault(); const f = new FormData(e.currentTarget); run(() => q.reportFinding(id, String(f.get('description')), String(f.get('severity')) as QCNonConformance['severity'])); }}
- L30 button: Create Non-Conformance [implicit submit if inside form; otherwise no click handler]
- L30 Link: Corrective action register — to="/qc/non-conformances"
- L31 form: Assigned QC user ID Assign inspection — onSubmit={e => { e.preventDefault(); run(() => q.assign(id, String(new FormData(e.currentTarget).get('userId')))); }}
- L31 button: Assign inspection [implicit submit if inside form; otherwise no click handler]

Form fields and binding/validation evidence:

- L25 select Decision: name="decision"
- L25 textarea Review / verification remarks: name="remarks"
- L28 input Authorized accepted quantity ( ): name="accepted"; type="number"; min="0"; max={i.subject.quantity}; step="any"
- L28 input Authorized rejected quantity ( ): name="rejected"; type="number"; min="0"; max={i.subject.quantity}; step="any"
- L30 textarea Finding / failed checklist item: name="description"
- L30 select Severity: name="severity"
- L31 input Assigned QC user ID: name="userId"; defaultValue={i.assignedTo}

Table headers and mapped label/option arrays (includes filter/UI enums):

- L20 mapped labels/options: ['production_manager', 'admin']
- L23 mapped labels/options: ['Failed', 'Reinspection Required']
- L25 mapped labels/options: ['Passed', 'Failed', 'Reinspection Required']
- L27 mapped labels/options: ['Failed', 'Reinspection Required', 'Conditionally Accepted']
- L30 mapped labels/options: ['Minor', 'Major', 'Critical']

### src/pages/Quality/InspectionForm.tsx

Actions and submission/navigation handlers:

- L29 button: Save Draft — onClick={() => run(false)}; type="button"
- L29 button: Submit Inspection — onClick={() => run(true)}; type="button"

Form fields and binding/validation evidence:

- L20 input Inspection time: type="time"; value={draft.time}; onChange={e => setDraft({ ...draft, time: e.target.value })}
- L20 select: value={draft.metadata[key] ?? ''}; onChange={e => setDraft({ ...draft, metadata: { ...draft.metadata, [key]: e.target.value } })}
- L20 input: value={draft.metadata[key] ?? ''}; onChange={e => setDraft({ ...draft, metadata: { ...draft.metadata, [key]: e.target.value } })}
- L24 input: aria-label={`${item.label} sample ${sample}`}; type={item.type === 'numeric' && response?.value !== 'NA' ? 'number' : 'text'}; value={response?.value ?? ''}; readOnly={response?.value === 'NA'}; step="any"; onChange={e => edit(item.id, sample, { value: e.target.value })}
- L24 select: aria-label={`${item.label} sample ${sample}`}; value={response?.value ?? ''}; onChange={e => edit(item.id, sample, { value: e.target.value })}
- L25 input Not Applicable (reason required): type="checkbox"; onChange={e => edit(item.id, sample, { value: e.target.checked ? 'NA' : '' })}
- L26 input: type="number"; value={response?.[key] ?? ''}; min={key === 'target' ? undefined : 0}; step="any"; onChange={e => edit(item.id, sample, { [key]: e.target.value === '' ? undefined : e.target.valueAsNumber })}
- L26 input Measurement unit: value={response?.unit ?? item.measurementUnit ?? ''}; onChange={e => edit(item.id, sample, { unit: e.target.value })}
- L27 textarea Finding comments / reason: value={response?.remarks ?? ''}; onChange={e => edit(item.id, sample, { remarks: e.target.value })}
- L28 textarea Overall comments / acceptance observations: value={draft.comments}; onChange={e => setDraft({ ...draft, comments: e.target.value })}

Table headers and mapped label/option arrays (includes filter/UI enums):

- L20 mapped labels/options: ['coa', 'tds', 'msds']
- L20 mapped labels/options: ['Available', 'Unavailable', 'Not Applicable']
- L24 mapped labels/options: ['numeric', 'text']
- L25 mapped labels/options: ['numeric', 'text']
- L26 mapped labels/options: ['target', 'lowerTolerance', 'upperTolerance']

### src/pages/Quality/NewInspection.tsx

Actions and submission/navigation handlers:

- L37 form: Template setTemplateId(e.target.value)}>{templates.map(t => {t.name} · Revision {t.revision})}Inspection dateDepartment / area t.id === templateId)?.department} className={ENTRY_INPUT} /> {category !== 'safety' ? Exact source { setSource(e.target.value); setStageId(''); }} className={ENTRY_INPUT}>Select source{category === 'raw' && rawMovements.filter(m => m.movementType === 'IN').map(m => {m.date} · {m.materialName} · {m.reference} · {m.quantity} {m.unit} · {m.id})}{category === 'production' && items.map(i => {i.jobCardNumber} · {i.product ?? i.modelName} · Item {i.id})}{category === 'machine' && machines.filter(m => m.active).map(m => {m.name} · {m.type})}{category === 'cleaning' && quality.areas.map(a => {a.name})} : Inspected area} {['raw', 'production'].includes(category) && Actual supplier / production batch number} {category === 'raw' && Receipt is physically received, not QC accepted. Supplier identity is unrecorded in existing inward data; no name matching is used.} {category === 'production' && Completed production stage setStageId(e.target.value)} className={ENTRY_INPUT}>Select checkpoint{selectedItem?.productionStages?.filter(s => s.kind === 'production' && s.required && s.status === 'Completed').map(s => {s.name} · Output {s.outputQuantity} {s.outputUnit})}Quantity represented by this QC lot ({selectedStage?.outputUnit ?? 'select stage'})Number of samples} {error && {error}} Create Draft — onSubmit={submit}
- L42 button: Create Draft [implicit submit if inside form; otherwise no click handler]

Form fields and binding/validation evidence:

- L37 select Template: value={templateId}; onChange={e => setTemplateId(e.target.value)}
- L37 input Inspection date: name="date"; type="date"; defaultValue={today()}
- L37 input Department / area: name="department"; defaultValue={templates.find(t => t.id === templateId)?.department}
- L38 select Exact source: value={source}; onChange={e => { setSource(e.target.value); setStageId(''); }}
- L38 input Inspected area: name="area"
- L39 input Actual supplier / production batch number: name="batch"
- L41 select Completed production stage: value={stageId}; onChange={e => setStageId(e.target.value)}
- L41 input Quantity represented by this QC lot ( ): name="lotQuantity"; type="number"; min="0.000001"; max={selectedStage?.outputQuantity ?? undefined}; step="any"
- L41 input Number of samples: name="samples"; type="number"; defaultValue="1"; min="1"; max="8"

Table headers and mapped label/option arrays (includes filter/UI enums):

- L39 mapped labels/options: ['raw', 'production']

### src/pages/Quality/QualityPage.tsx

Actions and submission/navigation handlers:

- L36 Link: QC Dashboard — to="/qc"
- L36 Link: {label} — to={`/qc/${key}`}
- L37 Link: {i.number} · {i.date} · {i.subject.label} — to={`/qc/inspections/${i.id}`}
- L41 button: Export Excel workbook (.xml) — onClick={exportExcel}
- L41 button: Print / Save as PDF — onClick={() => window.print()}
- L42 Link: {i.number} · {i.template.name} — to={`/qc/inspections/${i.id}`}
- L43 Link: Source inspection — to={`/qc/inspections/${n.inspectionId}`}
- L43 form: {(['assignedTo', 'immediateAction', 'correctiveAction', 'verification', 'dueDate'] as const).map(key => {{ assignedTo: "Assigned person (user ID)", immediateAction: "Immediate action", correctiveAction: "Corrective action", verification: "Verification outcome", dueDate: "Due date" }[key]})} Status{['Open', 'Assigned', 'In Progress', 'Awaiting Verification', 'Closed'].map(v => {v})} Record Action / Verification — onSubmit={e => { e.preventDefault(); const f = new FormData(e.currentTarget); run(() => q.updateFinding(n.id, { assignedTo: String(f.get('assignedTo')), immediateAction: String(f.get('immediateAction')), correctiveAction: String(f.get('correctiveAction')), dueDate: String(f.get('dueDate')), verification: String(f.get('verification')), status: String(f.get('status')) as QCNonConformance['status'] })); }}
- L43 button: Record Action / Verification [implicit submit if inside form; otherwise no click handler]

Form fields and binding/validation evidence:

- L39 input Search machine / supplier / product / Job Card / batch: value={query}; onChange={e => setQuery(e.target.value)}
- L39 select Period: value={period}; onChange={e => setRange(e.target.value)}
- L39 input From: type="date"; value={from}; onChange={e => { setFrom(e.target.value); setPeriod('custom'); }}
- L39 input To: type="date"; value={to}; min={from || undefined}; onChange={e => { setTo(e.target.value); setPeriod('custom'); }}
- L39 select Department: value={department}; onChange={e => setDepartment(e.target.value)}
- L39 select Inspector: value={inspector}; onChange={e => setInspector(e.target.value)}
- L39 select Status: value={status}; onChange={e => setStatus(e.target.value)}
- L39 select Report type: value={category}; onChange={e => setCategory(e.target.value)}
- L40 select Corrective action status: value={findingStatus}; onChange={e => setFindingStatus(e.target.value)}
- L43 input: name={key}; type={key === 'dueDate' ? 'date' : 'text'}; defaultValue={n[key]}
- L43 select Status: name="status"; defaultValue={n.status}

Table headers and mapped label/option arrays (includes filter/UI enums):

- L17 mapped labels/options: [ ['raw', 'Raw Material Inspection'], ['production', 'Production / Product Inspection'], ['machine', 'Machine Checklists'], ['cleaning', 'Factory Cleaning'], ['safety', 'Personnel Safety'], ['non-conformances', 'Non-Conformance & Corrective Actions'], ['reports', 'QC Reports'], ['templates', 'Inspection Templates'] ]
- L17 mapped labels/options: ['raw', 'Raw Material Inspection']
- L17 mapped labels/options: ['production', 'Production / Product Inspection']
- L17 mapped labels/options: ['machine', 'Machine Checklists']
- L17 mapped labels/options: ['cleaning', 'Factory Cleaning']
- L17 mapped labels/options: ['safety', 'Personnel Safety']
- L17 mapped labels/options: ['non-conformances', 'Non-Conformance & Corrective Actions']
- L17 mapped labels/options: ['reports', 'QC Reports']
- L17 mapped labels/options: ['templates', 'Inspection Templates']
- L25 mapped labels/options: ['raw', 'production', 'machine', 'cleaning', 'safety']
- L34 mapped labels/options: [['Inspections Due Today', q.inspections.filter(i => i.date === now && i.status === 'Draft').length], ['Pending Raw Material QC', rawMovements.filter(m => m.movementType === 'IN' && rawQualityStatus(q, m.id) !== 'Accepted / Released').length], ['Production QC Pending', q.inspections.filter(i => i.subject.kind === 'production' && subjectHeld(q, i.subject)).length], ['Awaiting Supervisor Approval', q.inspections.filter(i => i.status === 'Submitted' || i.status === 'Passed' || (i.subject.kind === 'production' && i.status === 'Approved/Released' && !q.releases.some(r => r.inspectionId === i.id && r.purpose === 'finished_stock'))).length], ['Failed Inspections', q.inspections.filter(i => i.status === 'Failed').length], ['Open Non-Conformances', q.nonConformances.filter(n => n.status !== 'Closed').length], ['Overdue Machine Checks', overdueMachineCount], ['Overdue Cleaning Checks', q.inspections.filter(i => i.subject.kind === 'cleaning' && i.date < now && subjectHeld(q, i.subject)).length]]
- L39 mapped labels/options: ['daily', 'weekly', 'monthly', 'custom']
- L39 mapped labels/options: ['Draft', 'Submitted', 'Passed', 'Failed', 'Reinspection Required', 'Approved/Released', 'Conditionally Accepted']
- L40 mapped labels/options: ['Open', 'Assigned', 'In Progress', 'Awaiting Verification', 'Closed']
- L43 mapped labels/options: ['assignedTo', 'immediateAction', 'correctiveAction', 'verification', 'dueDate']
- L43 mapped labels/options: ['Open', 'Assigned', 'In Progress', 'Awaiting Verification', 'Closed']
- L44 Machine
- L44 Template / type
- L44 Latest inspection
- L44 Review / warning

### src/pages/Quality/QualityTemplates.tsx

Actions and submission/navigation handlers:

- L14 button: Create New Revision — onClick={() => setDraft(structuredClone(t))}
- L14 button: Create Template from This Structure — onClick={() => setDraft({ ...structuredClone(t), id: crypto.randomUUID(), name: 'New inspection template', revision: 0, documentCode: undefined, source: 'ERP template proposed by Admin; confirm criteria with client.' })}
- L15 form: New immutable template revision {(['name', 'documentCode', 'effectiveDate', 'department', 'applicable'] as const).map(key => {{ name: "Template name", documentCode: "Paper document code (if verified)", effectiveDate: "Effective date", department: "Department", applicable: "Applicability" }[key]} setDraft({ ...draft, [key]: e.target.value })} />)}Inspection categorysetDraft({...draft,category:e.target.value as QCTemplate['category']})} className={ENTRY_INPUT}>{['raw','production','machine','cleaning','safety'].map(c=>{c})}Frequency setDraft({ ...draft, frequency: e.target.value as QCTemplate['frequency'] })} className={ENTRY_INPUT}>{QC_FREQUENCIES.map(v => {v.replaceAll("_", " ")})} setDraft({ ...draft, active: e.target.checked })} /> Active {draft.items.map((item, index) => Check wording setDraft({ ...draft, items: draft.items.map((i, n) => n === index ? { ...i, label: e.target.value } : i) })} />Response type { const type = e.target.value as ResponseType; setDraft({ ...draft, items: draft.items.map((i, n) => n === index ? { ...i, type, acceptable: optionsFor(type)[0] } : i) }); }}>{(['yes_no', 'ok_not_ok', 'tick_cross', 'pass_fail', 'numeric', 'text'] as const).map(v => {{ yes_no: 'Yes / No', ok_not_ok: 'OK / Not OK', tick_cross: 'Tick / Cross', pass_fail: 'Pass / Fail', numeric: 'Numeric measurement', text: 'Text remarks' }[v]})}Acceptable response setDraft({ ...draft, items: draft.items.map((i, n) => n === index ? { ...i, acceptable: e.target.value } : i) })}>{optionsFor(item.type).map(v => {v})}{(['required', 'allowNA', 'remarksRequired'] as const).map(key => setDraft({ ...draft, items: draft.items.map((i, n) => n === index ? { ...i, [key]: e.target.checked } : i) })} /> {{ required: "Required", allowNA: "Allow Not Applicable", remarksRequired: "Remarks required" }[key]})} setDraft({ ...draft, items: draft.items.filter(i => i.id !== item.id) })}>Remove item)} setDraft({ ...draft, items: [...draft.items, { id: crypto.randomUUID(), label: '', type: 'pass_fail', acceptable: 'Pass', required: true, allowNA: false }] })}>Add check Save Revision setDraft(null)}>Cancel — onSubmit={e => { e.preventDefault(); run(() => { q.reviseTemplate(draft); setDraft(null); }); }}
- L15 button: Remove item — onClick={() => setDraft({ ...draft, items: draft.items.filter(i => i.id !== item.id) })}; type="button"
- L15 button: Add check — onClick={() => setDraft({ ...draft, items: [...draft.items, { id: crypto.randomUUID(), label: '', type: 'pass_fail', acceptable: 'Pass', required: true, allowNA: false }] })}; type="button"
- L15 button: Save Revision [implicit submit if inside form; otherwise no click handler]
- L15 button: Cancel — onClick={() => setDraft(null)}; type="button"
- L16 form: Machine name Department Machine typeExtruderRecycle Extruder Add Machine — onSubmit={e => { e.preventDefault(); const f = new FormData(e.currentTarget); run(() => addMachine({ name: String(f.get('name')), department: String(f.get('department')), type: String(f.get('type')) as 'extruder' | 'recycle_extruder', active: true })); }}
- L16 button: Add Machine [implicit submit if inside form; otherwise no click handler]
- L16 form: Additional cleaning area Add Cleaning Area — onSubmit={e => { e.preventDefault(); run(() => q.addArea(String(new FormData(e.currentTarget).get('area')))); }}
- L16 button: Add Cleaning Area [implicit submit if inside form; otherwise no click handler]

Form fields and binding/validation evidence:

- L15 input: type={key === 'effectiveDate' ? 'date' : 'text'}; value={draft[key] ?? ''}; required={key !== 'documentCode' && key !== 'applicable'}; onChange={e => setDraft({ ...draft, [key]: e.target.value })}
- L15 select Inspection category: value={draft.category}; onChange={e=>setDraft({...draft,category:e.target.value as QCTemplate['category']})}
- L15 select Frequency: value={draft.frequency}; onChange={e => setDraft({ ...draft, frequency: e.target.value as QCTemplate['frequency'] })}
- L15 input Active: type="checkbox"; onChange={e => setDraft({ ...draft, active: e.target.checked })}
- L15 input Check wording: value={item.label}; onChange={e => setDraft({ ...draft, items: draft.items.map((i, n) => n === index ? { ...i, label: e.target.value } : i) })}
- L15 select Response type: value={item.type}; onChange={e => { const type = e.target.value as ResponseType; setDraft({ ...draft, items: draft.items.map((i, n) => n === index ? { ...i, type, acceptable: optionsFor(type)[0] } : i) }); }}
- L15 select Acceptable response: value={item.acceptable ?? ''}; disabled={['numeric', 'text'].includes(item.type)}; onChange={e => setDraft({ ...draft, items: draft.items.map((i, n) => n === index ? { ...i, acceptable: e.target.value } : i) })}
- L15 input: type="checkbox"; onChange={e => setDraft({ ...draft, items: draft.items.map((i, n) => n === index ? { ...i, [key]: e.target.checked } : i) })}
- L16 input Machine name: name="name"
- L16 input Department: name="department"
- L16 select Machine type: name="type"
- L16 input Additional cleaning area: name="area"

Table headers and mapped label/option arrays (includes filter/UI enums):

- L15 mapped labels/options: ['name', 'documentCode', 'effectiveDate', 'department', 'applicable']
- L15 mapped labels/options: ['raw','production','machine','cleaning','safety']
- L15 mapped labels/options: ['yes_no', 'ok_not_ok', 'tick_cross', 'pass_fail', 'numeric', 'text']
- L15 mapped labels/options: ['numeric', 'text']
- L15 mapped labels/options: ['required', 'allowNA', 'remarksRequired']

### src/pages/Quotations/QuotationDetail.tsx

Actions and submission/navigation handlers:

- L21 Link: Return — to="/quotations"
- L26 Link: Quotations — to="/quotations"
- L26 Link: Edit Draft — to={`/quotations/${id}/edit`}
- L26 button: Submit for Approval — onClick={() => run(() => qStore.submit(id))}
- L26 button: Approve Prices / Tax / Terms — onClick={() => run(() => qStore.approve(id))}
- L26 form: Request Changes — onSubmit={e => { e.preventDefault(); run(() => qStore.requestChanges(id, String(new FormData(e.currentTarget).get('remarks')))); }}
- L26 button: Request Changes [implicit submit if inside form; otherwise no click handler]
- L26 button: Mark Sent — onClick={() => run(() => qStore.send(id))}
- L26 button: Create New Revision — onClick={() => run(() => navigate(`/quotations/${qStore.revise(id).id}/edit`))}
- L26 button: Duplicate as New Quotation — onClick={() => run(() => navigate(`/quotations/${qStore.revise(id, true).id}/edit`))}
- L26 button: Preview / Print — onClick={() => setPreview(true)}
- L27 form: Reject internal submission — onSubmit={e=>{e.preventDefault();run(()=>qStore.reject(id,String(new FormData(e.currentTarget).get('remarks'))));}}
- L27 button: Reject internal submission [implicit submit if inside form; otherwise no click handler]
- L28 Link: Edit and Resubmit (reviewed changes return to approval) — to={`/quotations/${id}/edit`}
- L33 form: Response{['Pending', 'Accepted', 'Rejected', 'Revision Requested'].map(v => {v})} Response date Responded by Supporting reference Remarks Record Response for Revision {q.revision} — onSubmit={e => { e.preventDefault(); const f = new FormData(e.currentTarget); run(() => qStore.respond(id, { response: String(f.get('response')) as QuotationResponse['response'], date: String(f.get('date')), respondedBy: String(f.get('respondedBy')), remarks: String(f.get('remarks')), reference: String(f.get('reference')) })); }}
- L33 button: Record Response for Revision {q.revision} [implicit submit if inside form; otherwise no click handler]
- L35 form: Confirmed customer masterSelect/link exact existing customer{customers.filter(c => !sourceCustomerId || c.id === sourceCustomerId).map(c => {c.name})} {q.lines.some(l => l.type === 'custom') && Manufacturing required delivery date} Convert to Sales Order Explicit prospect/customer promotion — onSubmit={e => { e.preventDefault(); const f = new FormData(e.currentTarget); run(() => navigate(`/sales-orders/${qStore.convert(id, String(f.get('customerId')), String(f.get('requiredDate') ?? ''))}`)); }}
- L35 button: Convert to Sales Order — disabled={!!stale} [implicit submit if inside form; otherwise no click handler]
- L35 Link: Explicit prospect/customer promotion — to="/quotations/settings"
- L35 Link: Sales Order {related.orderNumber} — to={`/sales-orders/${related.id}`}
- L36 Link: {n.number} revision {n.revision} — to={`/quotations/${n.id}`}

Form fields and binding/validation evidence:

- L26 input: name="remarks"; aria-label="Reviewer change remarks"
- L27 input: name="remarks"; aria-label="Internal rejection remarks"
- L33 select Response: name="response"
- L33 input Response date: name="date"; type="date"; defaultValue={today()}; max={today()}
- L33 input Responded by: name="respondedBy"
- L33 input Supporting reference: name="reference"
- L33 textarea Remarks: name="remarks"
- L35 select Confirmed customer master: name="customerId"; defaultValue={sourceCustomerId ?? ''}
- L35 input Manufacturing required delivery date: name="requiredDate"; type="date"; min={today()}

Table headers and mapped label/option arrays (includes filter/UI enums):

- L26 mapped labels/options: ['Converted to Sales Order', 'Superseded']
- L29 mapped labels/options: ['Approved','Sent','Accepted']
- L33 mapped labels/options: ['Pending', 'Accepted', 'Rejected', 'Revision Requested']
- L35 mapped labels/options: ['admin', 'receptionist']

### src/pages/Quotations/QuotationEditor.tsx

Actions and submission/navigation handlers:

- L21 Link: View / create an authorized revision — to={`/quotations/${id}`}
- L31 Link: Quotation detail — to={`/quotations/${draft.id}`}
- L31 form: Document detailsQuotation number setDraft({ ...draft, number: e.target.value })} className={ENTRY_INPUT} />Document type setDraft({ ...draft, documentType: e.target.value as Quotation['documentType'] })} className={ENTRY_INPUT}>Sales QuotationProforma InvoiceQuotation date { try { setDraft({ ...draft, date: e.target.value, validUntil: addDays(e.target.value, draft.validityDays) }); } catch { setDraft({ ...draft, date: e.target.value }); } }} className={ENTRY_INPUT} />Validity (days) { const days = e.target.valueAsNumber; try { setDraft({ ...draft, validityDays: days, validUntil: addDays(draft.date, days) }); } catch { setDraft({ ...draft, validityDays: days }); } }} className={ENTRY_INPUT} />Valid untilDelivery lead time (days, optional) setDraft({ ...draft, deliveryDays: e.target.value === '' ? undefined : e.target.valueAsNumber })} className={ENTRY_INPUT} />Currency setDraft({ ...draft, currency: e.target.value })} className={ENTRY_INPUT} />VAT rate % setDraft({ ...draft, taxRate: e.target.valueAsNumber })} className={ENTRY_INPUT} />Unit price VAT basis setDraft({ ...draft, taxMode: e.target.value as Quotation['taxMode'] })} className={ENTRY_INPUT}>InclusiveExclusiveSales representative setDraft({ ...draft, salesRepresentative: e.target.value })} className={ENTRY_INPUT} />Changing tax basis/rate requires explicit price review. Validity and delivery lead time are separate. Customer / prospectExisting party selectParty(e.target.value)} className={ENTRY_INPUT}>Select customer or prospect{customers.map(c => {c.name})}{prospects.map(p => {p.name})}{([['name', 'Customer name'], ['contactPerson', 'Contact person'], ['telephone', 'Telephone'], ['email', 'Email'], ['tin', 'Customer TIN'], ['billingAddress', 'Billing address'], ['deliveryAddress', 'Delivery address']] as const).map(([key, label]) => {label} setDraft({ ...draft, customer: { ...draft.customer, [key]: e.target.value } })} className={ENTRY_INPUT} />)}Customer type setDraft({ ...draft, customer: { ...draft.customer, customerType: e.target.value as 'B2B' | 'B2C' } })} className={ENTRY_INPUT}>B2BB2CProspects / company / terms settingsContact edits are document snapshots; they do not create duplicate master records. Commercial items{draft.lines.map((l, index) => Item {index + 1}Item source updateLine(l.id, { type: e.target.value as QuotationLine['type'], productId: undefined, modelId: undefined, modelRevision: undefined, unit: '', unitPrice: 0, description: '' }, true)} className={ENTRY_INPUT}>Existing ProductCustomized Product{l.type === 'stock' ? Product variant { const p = FINISHED_GOODS.find(p => p.id === e.target.value); updateLine(l.id, { productId: p?.id, description: p ? finishedGoodLabel(p) : '', unit: p?.unit ?? '', unitPrice: 0 }); }} className={ENTRY_INPUT}>Select exact variant{FINISHED_GOODS.map(p => {finishedGoodLabel(p)})} : Model revision { const m = models.find(m => `${m.id}:${m.revision}` === e.target.value); updateLine(l.id, { modelId: m?.id, modelRevision: m?.revision, description: m?.name ?? '', specifications: m?.specifications ?? '', unit: m?.defaultUnit ?? '' }, true); }} className={ENTRY_INPUT}>Select current model revision{models.map(m => {m.name} · {m.revision})}}Product group heading updateLine(l.id, { group: e.target.value })} className={ENTRY_INPUT} />Quantity updateLine(l.id, { quantity: e.target.valueAsNumber }, l.type === 'custom')} className={ENTRY_INPUT} />Unit updateLine(l.id, { unit: e.target.value }, l.type === 'custom')} className={ENTRY_INPUT} />Unit price ({draft.taxMode} VAT) updateLine(l.id, { unitPrice: e.target.valueAsNumber })} className={ENTRY_INPUT} />Particulars / multiline description updateLine(l.id, { description: e.target.value })} className={ENTRY_INPUT} />Specifications updateLine(l.id, { specifications: e.target.value }, l.type === 'custom')} className={ENTRY_INPUT} />Line total: {Number.isFinite(l.quantity * l.unitPrice) ? (Math.round(l.quantity * l.unitPrice * 100) / 100).toFixed(2) : 'Incomplete'} {draft.currency} {l.type === 'custom' && { if (save()) navigate(`/costing?quotationId=${draft.id}&quotationLineId=${l.id}`); }}>Save & Open Existing Custom CostingApply approved costing revision { const estimate = estimates.find(row => row.id === e.target.value); if (!estimate) return; try { updateLine(l.id, { estimateId: estimate.id, estimateRevision: estimate.revision, led:estimate.input.led?structuredClone(estimate.input.led):undefined,ledSnapshot:estimate.totals.led?structuredClone(estimate.totals.led):undefined, unitPrice: quotedCostPrice(estimate, draft) }); setError(''); } catch(e) { setError(e instanceof Error ? e.message : 'Unable to apply price.'); } }}>Select approved revision / reapply current tax basis{estimates.filter(e => e.status === 'Approved' && matchesQuotationCost(e, draft, l)).map(e => {e.number} · Revision {e.revision} · {e.input.currency})}Costing: {l.estimateId ?? 'Not linked'} · Revision {l.estimateRevision ?? 'Price not yet applied'}. Net public selling price and charges are reused; quotation tax is applied once. No material prices or margins enter the customer document.}{l.type==='stock'?updateLine(l.id,{led,ledSnapshot})} productId={l.productId} modelId={l.modelId} quantity={l.quantity} unit={l.unit} date={draft.date} currency={draft.currency} netSelling={l.quantity*l.unitPrice/(draft.taxMode==='inclusive'?1+draft.taxRate/100:1)}/>:l.ledSnapshot?:Custom LED policy comes from the approved costing snapshot.} setDraft({ ...draft, lines: draft.lines.filter(row => row.id !== l.id) })}>Remove draft item)} setDraft({ ...draft, lines: [...draft.lines, blankQuotationLine()] })}>Add productNo selling-price master exists for imported stock variants; enter reviewed prices. Units remain explicit with no KG/carton/piece conversion. Terms & ConditionsUse an optional terms template { const t = termsTemplates.find(t => t.name === e.target.value); if (t) setDraft({ ...draft, terms: structuredClone(t) }); }}>Keep document terms{termsTemplates.map(t => {t.name})} setDraft({ ...draft, terms })} />Discount in entered price basis setDraft({ ...draft, discount: e.target.valueAsNumber })} className={ENTRY_INPUT} />{totals && Subtotal before tax {totals.subtotalBeforeTax.toFixed(2)} · Discount before tax {totals.discountBeforeTax.toFixed(2)} · VAT {totals.tax.toFixed(2)} · Total {totals.total.toFixed(2)} {draft.currency}} Company snapshot: {draft.company.tradingName} · {draft.company.legalName} setDraft({ ...draft, company: structuredClone(company) })}>Use current company settings in this draft Save DraftReturn to detail {error && {error}} {saved && {saved}} — onSubmit={save}
- L33 Link: Prospects / company / terms settings — to="/quotations/settings"
- L35 button: Save & Open Existing Custom Costing — onClick={() => { if (save()) navigate(`/costing?quotationId=${draft.id}&quotationLineId=${l.id}`); }}; type="button"; disabled={!l.modelId || !draft.customer.name.trim()}
- L36 button: Remove draft item — onClick={() => setDraft({ ...draft, lines: draft.lines.filter(row => row.id !== l.id) })}; type="button"
- L36 button: Add product — onClick={() => setDraft({ ...draft, lines: [...draft.lines, blankQuotationLine()] })}; type="button"
- L38 button: Use current company settings in this draft — onClick={() => setDraft({ ...draft, company: structuredClone(company) })}; type="button"
- L38 button: Save Draft [implicit submit if inside form; otherwise no click handler]
- L38 Link: Return to detail — to={`/quotations/${draft.id}`}

Form fields and binding/validation evidence:

- L16 textarea: value={terms[key]}; onChange={e => onChange({ ...terms, [key]: e.target.value })}
- L16 input: type="number"; value={terms[key] ?? ''}; min="0"; max={key === 'creditDays' ? undefined : 100}; step={key === 'creditDays' ? '1' : 'any'}; onChange={e => onChange({ ...terms, [key]: e.target.value === '' ? undefined : e.target.valueAsNumber })}
- L32 input Quotation number: value={draft.number}; readOnly={user?.role !== 'admin'}; onChange={e => setDraft({ ...draft, number: e.target.value })}
- L32 select Document type: value={draft.documentType}; onChange={e => setDraft({ ...draft, documentType: e.target.value as Quotation['documentType'] })}
- L32 input Quotation date: type="date"; value={draft.date}; onChange={e => { try { setDraft({ ...draft, date: e.target.value, validUntil: addDays(e.target.value, draft.validityDays) }); } catch { setDraft({ ...draft, date: e.target.value }); } }}
- L32 input Validity (days): type="number"; value={draft.validityDays}; min="0"; max="3650"; onChange={e => { const days = e.target.valueAsNumber; try { setDraft({ ...draft, validityDays: days, validUntil: addDays(draft.date, days) }); } catch { setDraft({ ...draft, validityDays: days }); } }}
- L32 input Valid until: value={draft.validUntil}
- L32 input Delivery lead time (days, optional): type="number"; value={draft.deliveryDays ?? ''}; min="0"; onChange={e => setDraft({ ...draft, deliveryDays: e.target.value === '' ? undefined : e.target.valueAsNumber })}
- L32 input Currency: value={draft.currency}; onChange={e => setDraft({ ...draft, currency: e.target.value })}
- L32 input VAT rate %: type="number"; value={draft.taxRate}; min="0"; max="100"; step="any"; onChange={e => setDraft({ ...draft, taxRate: e.target.valueAsNumber })}
- L32 select Unit price VAT basis: value={draft.taxMode}; onChange={e => setDraft({ ...draft, taxMode: e.target.value as Quotation['taxMode'] })}
- L32 input Sales representative: value={draft.salesRepresentative}; onChange={e => setDraft({ ...draft, salesRepresentative: e.target.value })}
- L33 select Existing party: value={draft.customer.customerId ? `customer:${draft.customer.customerId}` : draft.customer.prospectId ? `prospect:${draft.customer.prospectId}` : ''}; onChange={e => selectParty(e.target.value)}
- L33 input: value={draft.customer[key]}; onChange={e => setDraft({ ...draft, customer: { ...draft.customer, [key]: e.target.value } })}
- L33 select Customer type: value={draft.customer.customerType}; onChange={e => setDraft({ ...draft, customer: { ...draft.customer, customerType: e.target.value as 'B2B' | 'B2C' } })}
- L34 select Item source: value={l.type}; onChange={e => updateLine(l.id, { type: e.target.value as QuotationLine['type'], productId: undefined, modelId: undefined, modelRevision: undefined, unit: '', unitPrice: 0, description: '' }, true)}
- L34 select Product variant: value={l.productId ?? ''}; onChange={e => { const p = FINISHED_GOODS.find(p => p.id === e.target.value); updateLine(l.id, { productId: p?.id, description: p ? finishedGoodLabel(p) : '', unit: p?.unit ?? '', unitPrice: 0 }); }}
- L34 select Model revision: value={`${l.modelId ?? ''}:${l.modelRevision ?? ''}`}; onChange={e => { const m = models.find(m => `${m.id}:${m.revision}` === e.target.value); updateLine(l.id, { modelId: m?.id, modelRevision: m?.revision, description: m?.name ?? '', specifications: m?.specifications ?? '', unit: m?.defaultUnit ?? '' }, true); }}
- L34 input Product group heading: value={l.group}; onChange={e => updateLine(l.id, { group: e.target.value })}
- L34 input Quantity: type="number"; value={l.quantity}; min="0.000001"; step="any"; onChange={e => updateLine(l.id, { quantity: e.target.valueAsNumber }, l.type === 'custom')}
- L34 input Unit: value={l.unit}; readOnly={l.type === 'stock'}; onChange={e => updateLine(l.id, { unit: e.target.value }, l.type === 'custom')}
- L34 input Unit price ( VAT): type="number"; value={l.unitPrice}; readOnly={l.type === 'custom'}; min="0"; step="any"; onChange={e => updateLine(l.id, { unitPrice: e.target.valueAsNumber })}
- L34 textarea Particulars / multiline description: value={l.description}; onChange={e => updateLine(l.id, { description: e.target.value })}
- L34 textarea Specifications: value={l.specifications}; onChange={e => updateLine(l.id, { specifications: e.target.value }, l.type === 'custom')}
- L35 select Apply approved costing revision: value=""; onChange={e => { const estimate = estimates.find(row => row.id === e.target.value); if (!estimate) return; try { updateLine(l.id, { estimateId: estimate.id, estimateRevision: estimate.revision, led:estimate.input.led?structuredClone(estimate.input.led):undefined,ledSnapshot:estimate.totals.led?structuredClone(estimate.totals.led):undefined, unitPrice: quotedCostPrice(estimate, draft) }); setError(''); } catch(e) { setError(e instanceof Error ? e.message : 'Unable to apply price.'); } }}
- L37 select Use an optional terms template: value=""; onChange={e => { const t = termsTemplates.find(t => t.name === e.target.value); if (t) setDraft({ ...draft, terms: structuredClone(t) }); }}
- L37 input Discount in entered price basis: type="number"; value={draft.discount}; min="0"; step="0.01"; onChange={e => setDraft({ ...draft, discount: e.target.valueAsNumber })}

Table headers and mapped label/option arrays (includes filter/UI enums):

- L16 mapped labels/options: [['priceValidity', 'Price validity clause'], ['deliveryPeriod', 'Delivery terms'], ['paymentTerms', 'Payment terms'], ['revisionClause', 'Price revision clause'], ['additionalTerms', 'Additional terms'], ['remarks', 'Remarks']]
- L16 mapped labels/options: ['priceValidity', 'Price validity clause']
- L16 mapped labels/options: ['deliveryPeriod', 'Delivery terms']
- L16 mapped labels/options: ['paymentTerms', 'Payment terms']
- L16 mapped labels/options: ['revisionClause', 'Price revision clause']
- L16 mapped labels/options: ['additionalTerms', 'Additional terms']
- L16 mapped labels/options: ['remarks', 'Remarks']
- L16 mapped labels/options: [['advancePercent', 'Advance payment %'], ['creditDays', 'Credit days'], ['quantityTolerance', 'Commercial quantity tolerance +/- %']]
- L16 mapped labels/options: ['advancePercent', 'Advance payment %']
- L16 mapped labels/options: ['creditDays', 'Credit days']
- L16 mapped labels/options: ['quantityTolerance', 'Commercial quantity tolerance +/- %']
- L33 mapped labels/options: [['name', 'Customer name'], ['contactPerson', 'Contact person'], ['telephone', 'Telephone'], ['email', 'Email'], ['tin', 'Customer TIN'], ['billingAddress', 'Billing address'], ['deliveryAddress', 'Delivery address']]
- L33 mapped labels/options: ['name', 'Customer name']
- L33 mapped labels/options: ['contactPerson', 'Contact person']
- L33 mapped labels/options: ['telephone', 'Telephone']
- L33 mapped labels/options: ['email', 'Email']
- L33 mapped labels/options: ['tin', 'Customer TIN']
- L33 mapped labels/options: ['billingAddress', 'Billing address']
- L33 mapped labels/options: ['deliveryAddress', 'Delivery address']

### src/pages/Quotations/QuotationEmail.tsx

Actions and submission/navigation handlers:

- L7 form: Recipient email CC (comma-separated, optional) Subject Message {q.number} · Revision {q.revision} · Attachment: customer-safe PDF, manually saved Save email draft — onSubmit={e=>{e.preventDefault();const f=new FormData(e.currentTarget);try{store.saveEmailDraft(q.id,String(f.get('to')),String(f.get('cc')),String(f.get('subject')),String(f.get('message')));setError('');}catch(err){setError(err instanceof Error?err.message:'Unable to save email draft.');}}}
- L7 button: Save email draft [implicit submit if inside form; otherwise no click handler]
- L7 a: Open email app (attach PDF manually) — href={emailMailto(d)}

Form fields and binding/validation evidence:

- L7 input Recipient email: name="to"; type="email"; defaultValue={q.customer.email}
- L7 input CC (comma-separated, optional): name="cc"
- L7 input Subject: name="subject"; defaultValue={`${q.number} — revision ${q.revision}`}
- L7 textarea Message: name="message"; defaultValue={`Please review ${q.documentType} ${q.number}, revision ${q.revision}.`}


### src/pages/Quotations/QuotationList.tsx

Actions and submission/navigation handlers:

- L22 button: Create Quotation — onClick={() => { try { navigate(`/quotations/${create().id}/edit`); } catch(e) { setError(e instanceof Error ? e.message : 'Unable to create.'); } }}
- L22 Link: Prospects / Company / Terms — to="/quotations/settings"
- L22 button: Export quotation report (CSV) — onClick={exportCsv}
- L22 Link: {q.number} · Revision {q.revision} · {q.documentType} — to={`/quotations/${q.id}`}
- L22 Link: Edit — to={`/quotations/${q.id}/edit`}
- L22 Link: Preview / Print — to={`/quotations/${q.id}?preview=1`}
- L22 button: Duplicate — onClick={() => { try { navigate(`/quotations/${revise(q.id, true).id}/edit`); } catch(e) { setError(e instanceof Error ? e.message : "Unable to duplicate."); } }}
- L22 button: Mark Sent — onClick={() => { try { send(q.id); } catch(e) { setError(e instanceof Error ? e.message : "Unable to mark sent."); } }}
- L22 Link: Record Response — to={`/quotations/${q.id}`}
- L22 Link: Convert to Sales Order — to={`/quotations/${q.id}`}
- L22 Link: Related Sales Order — to={`/sales-orders/${q.salesOrderId}`}

Form fields and binding/validation evidence:

- L22 input Quotation number: value={query}; onChange={e => setQuery(e.target.value)}
- L22 select Customer: value={customer}; onChange={e => setCustomer(e.target.value)}
- L22 select Created by: value={creator}; onChange={e => setCreator(e.target.value)}
- L22 input From: type="date"; value={from}; onChange={e => setFrom(e.target.value)}
- L22 input To: type="date"; value={to}; min={from || undefined}; onChange={e => setTo(e.target.value)}
- L22 select Status: value={status}; onChange={e => setStatus(e.target.value)}
- L22 input Include historical revisions: type="checkbox"; onChange={e => setHistory(e.target.checked)}

Table headers and mapped label/option arrays (includes filter/UI enums):

- L15 mapped labels/options: [['Draft Quotations', count('Draft')], ['Pending Approval', count('Pending Internal Approval')], ['Quotations Sent', latest.filter(q => q.events.some(e => e.type === 'Marked sent')).length], ['Awaiting Customer Response', latest.filter(q => effectiveQuotationStatus(q) === 'Sent' && !q.responses.some(r => r.response === 'Accepted' || r.response === 'Rejected' || r.response === 'Revision Requested')).length], ['Accepted Quotations', count('Accepted')], ['Expired Quotations', count('Expired')], ['Converted Quotations', converted], ['Conversion Rate', latest.length ? `${(converted / latest.length * 100).toFixed(1)}%` : 'No quotations']]
- L21 mapped labels/options: ['Quotation', 'Revision', 'Type', 'Date', 'Customer', 'Contact', 'Total', 'Currency', 'Valid until', 'Status', 'Sales Order ID', 'Created by']
- L22 mapped labels/options: ['Draft', 'Pending Internal Approval', 'Internally Rejected', 'Approved', 'Sent', 'Accepted', 'Rejected', 'Revision Requested', 'Expired', 'Converted to Sales Order', 'Superseded']

### src/pages/Quotations/QuotationPrint.tsx

Actions and submission/navigation handlers:

- L11 button: Print / Save as PDF — onClick={() => window.print()}
- L11 button: Close — onClick={onClose}

Table headers and mapped label/option arrays (includes filter/UI enums):

- L8 {label}

### src/pages/Quotations/QuotationSettings.tsx

Actions and submission/navigation handlers:

- L15 Link: Quotations — to="/quotations"
- L16 form: {[['name', 'Prospect name'], ['contact', 'Contact person'], ['phone', 'Telephone'], ['email', 'Email'], ['billing', 'Billing address'], ['delivery', 'Delivery address'], ['tin', 'TIN (optional)']].map(([key, label]) => {label})} Customer typeB2BB2C Create Prospect — onSubmit={e => { e.preventDefault(); const f = new FormData(e.currentTarget); run(() => { c.addProspect({ name: String(f.get('name')), contactPerson: String(f.get('contact')), phone: String(f.get('phone')), email: String(f.get('email')), billingAddress: String(f.get('billing')), deliveryAddress: String(f.get('delivery')), tin: String(f.get('tin')), customerType: String(f.get('type')) as 'B2B' | 'B2C' }); }); }}
- L16 button: Create Prospect [implicit submit if inside form; otherwise no click handler]
- L16 form: Explicitly create a new customer from this prospect{c.customers.map(customer => Link existing: {customer.name})} Confirm Customer Link / Promotion — onSubmit={e => { e.preventDefault(); const f = new FormData(e.currentTarget); run(() => { c.promoteProspect(p.id, String(f.get('customer')) || undefined); }); }}
- L16 button: Confirm Customer Link / Promotion [implicit submit if inside form; otherwise no click handler]
- L17 form: Reusable company settings {([['tradingName', 'Trading name'], ['legalName', 'Registered legal name'], ['logo', 'Logo asset path'], ['address', 'Company address'], ['telephone', 'Telephone'], ['email', 'Email'], ['tin', 'TIN'], ['signatory', 'Authorized signatory'], ['currency', 'Default currency']] as const).map(([key, label]) => {label} setCompany({ ...company, [key]: e.target.value })} className={ENTRY_INPUT} />)}Default VAT % setCompany({ ...company, taxRate: e.target.valueAsNumber })} className={ENTRY_INPUT} />Default validity days setCompany({ ...company, validityDays: e.target.valueAsNumber })} className={ENTRY_INPUT} />Default price VAT basis setCompany({ ...company, taxMode: e.target.value as typeof company.taxMode })} className={ENTRY_INPUT}>InclusiveExclusive Bank accounts {company.banks.map(b => {([['bank', 'Bank'], ['branch', 'Branch'], ['accountName', 'Account name'], ['accountNumber', 'Account number'], ['currency', 'Account currency']] as const).map(([key, label]) => {label} setCompany({ ...company, banks: company.banks.map(row => row.id === b.id ? { ...row, [key]: e.target.value } : row) })} className={ENTRY_INPUT} />)} setCompany({ ...company, banks: company.banks.filter(row => row.id !== b.id) })}>Remove bank from settings)} setCompany({ ...company, banks: [...company.banks, { id: crypto.randomUUID(), bank: '', branch: '', accountName: '', accountNumber: '', currency: company.currency }] })}>Add bank account Save Company Settings Changes affect future drafts/revisions; sent documents retain company/bank/signatory snapshots. No handwritten signature asset is copied. — onSubmit={e => { e.preventDefault(); run(() => c.saveSettings(company)); }}
- L17 button: Remove bank from settings — onClick={() => setCompany({ ...company, banks: company.banks.filter(row => row.id !== b.id) })}; type="button"
- L17 button: Add bank account — onClick={() => setCompany({ ...company, banks: [...company.banks, { id: crypto.randomUUID(), bank: '', branch: '', accountName: '', accountNumber: '', currency: company.currency }] })}; type="button"
- L17 button: Save Company Settings [implicit submit if inside form; otherwise no click handler]
- L18 form: Reusable optional terms template Template name setTerms({ ...terms, name: e.target.value })} className={ENTRY_INPUT} /> Save Terms Template No advance/credit/tolerance clauses are imposed automatically. Each draft explicitly selects its terms. — onSubmit={e => { e.preventDefault(); run(() => c.saveTermsTemplate(terms)); }}
- L18 button: Save Terms Template [implicit submit if inside form; otherwise no click handler]

Form fields and binding/validation evidence:

- L16 input: name={key}; required={key === 'name'}
- L16 select Customer type: name="type"
- L16 select: name="customer"
- L17 input: value={company[key]}; onChange={e => setCompany({ ...company, [key]: e.target.value })}
- L17 input Default VAT %: type="number"; value={company.taxRate}; min="0"; max="100"; step="any"; onChange={e => setCompany({ ...company, taxRate: e.target.valueAsNumber })}
- L17 input Default validity days: type="number"; value={company.validityDays}; min="0"; max="3650"; onChange={e => setCompany({ ...company, validityDays: e.target.valueAsNumber })}
- L17 select Default price VAT basis: value={company.taxMode}; onChange={e => setCompany({ ...company, taxMode: e.target.value as typeof company.taxMode })}
- L17 input: value={b[key]}; onChange={e => setCompany({ ...company, banks: company.banks.map(row => row.id === b.id ? { ...row, [key]: e.target.value } : row) })}
- L18 input Template name: value={terms.name ?? ''}; onChange={e => setTerms({ ...terms, name: e.target.value })}

Table headers and mapped label/option arrays (includes filter/UI enums):

- L16 mapped labels/options: [['name', 'Prospect name'], ['contact', 'Contact person'], ['phone', 'Telephone'], ['email', 'Email'], ['billing', 'Billing address'], ['delivery', 'Delivery address'], ['tin', 'TIN (optional)']]
- L16 mapped labels/options: ['name', 'Prospect name']
- L16 mapped labels/options: ['contact', 'Contact person']
- L16 mapped labels/options: ['phone', 'Telephone']
- L16 mapped labels/options: ['email', 'Email']
- L16 mapped labels/options: ['billing', 'Billing address']
- L16 mapped labels/options: ['delivery', 'Delivery address']
- L16 mapped labels/options: ['tin', 'TIN (optional)']
- L17 mapped labels/options: [['tradingName', 'Trading name'], ['legalName', 'Registered legal name'], ['logo', 'Logo asset path'], ['address', 'Company address'], ['telephone', 'Telephone'], ['email', 'Email'], ['tin', 'TIN'], ['signatory', 'Authorized signatory'], ['currency', 'Default currency']]
- L17 mapped labels/options: ['tradingName', 'Trading name']
- L17 mapped labels/options: ['legalName', 'Registered legal name']
- L17 mapped labels/options: ['logo', 'Logo asset path']
- L17 mapped labels/options: ['address', 'Company address']
- L17 mapped labels/options: ['telephone', 'Telephone']
- L17 mapped labels/options: ['email', 'Email']
- L17 mapped labels/options: ['tin', 'TIN']
- L17 mapped labels/options: ['signatory', 'Authorized signatory']
- L17 mapped labels/options: ['currency', 'Default currency']
- L17 mapped labels/options: [['bank', 'Bank'], ['branch', 'Branch'], ['accountName', 'Account name'], ['accountNumber', 'Account number'], ['currency', 'Account currency']]
- L17 mapped labels/options: ['bank', 'Bank']
- L17 mapped labels/options: ['branch', 'Branch']
- L17 mapped labels/options: ['accountName', 'Account name']
- L17 mapped labels/options: ['accountNumber', 'Account number']
- L17 mapped labels/options: ['currency', 'Account currency']

### src/pages/RawMaterials/RawMaterialPage.tsx

Actions and submission/navigation handlers:

- L58 Link: Raw Material Inspection — to="/qc/raw"
- L59 button: Stock IN — onClick={() => setDirection('IN')}
- L59 button: Stock OUT — onClick={() => setDirection('OUT')}
- L63 button: {label} — onClick={() => { setCategory(id); setFamily('all'); setUnit('all'); }}
- L64 button: {label} — onClick={() => setView(id)}
- L65 button: Filter {family !== 'all' || unit !== 'all' || status !== 'all' ? ' (active)' : ''} — onClick={() => setShowFilters(!showFilters)}; type="button"
- L65 button: Export CSV — onClick={exportReport}
- L66 button: Clear filters — onClick={() => { setFamily('all'); setUnit('all'); setStatus('all'); setMovementType('all'); setQuery(''); }}; type="button"

Form fields and binding/validation evidence:

- L65 input: aria-label="Search material or grade"; type="search"; value={query}; onChange={event => setQuery(event.target.value)}
- L65 select: aria-label="Movement type"; value={movementType}; onChange={event => setMovementType(event.target.value)}
- L65 input Month: aria-label="Report month"; type="month"; value={month}; onChange={event => { if (event.target.value) setMonth(event.target.value); }}
- L66 select Family: aria-label="Material family"; value={family}; onChange={event => setFamily(event.target.value)}
- L66 select Unit: aria-label="Filter unit"; value={unit}; onChange={event => setUnit(event.target.value)}
- L66 select Status: aria-label="Filter status"; value={status}; onChange={event => setStatus(event.target.value)}

Table headers and mapped label/option arrays (includes filter/UI enums):

- L14 mapped labels/options: [['levels', 'Stock Levels'], ['movements', 'Movements'], ['report', 'Monthly Report']]
- L14 mapped labels/options: ['levels', 'Stock Levels']
- L14 mapped labels/options: ['movements', 'Movements']
- L14 mapped labels/options: ['report', 'Monthly Report']
- L52 mapped labels/options: ['Material / Grade', 'Family', 'Unit', 'Opening Stock', 'Stock IN', 'Stock OUT', 'Closing Stock']
- L66 mapped labels/options: ['Stock in Hand', 'Below minimum', 'Out of stock', 'Negative balance', 'Not recorded']
- L68 mapped labels/options: ['Date', 'Material / Grade', 'Category', 'Type', 'Quantity', 'Reference', 'Remarks']
- L68 {label}
- L70 {label}
- L74 mapped labels/options: [['Category / Family', m.family], ['Opening Stock', fmt(rawMaterialBalance(m, rawMovements).openingStock)], ['Stock IN', fmt(rawMaterialBalance(m, rawMovements).stockIn)], ['Stock OUT', fmt(rawMaterialBalance(m, rawMovements).stockOut)], ['Status', statusLabel(m, rawMaterialBalance(m, rawMovements).currentStock)]]

### src/pages/Recycling/RecyclingPage.tsx

Actions and submission/navigation handlers:

- L66 button: {tab === "waste" ? "Waste Intake" : "Granules"} — onClick={() => setView(tab)}; type="button"

Table headers and mapped label/option arrays (includes filter/UI enums):

- L63 mapped labels/options: ["waste", "granules"]

### src/pages/SalesOrders/NewSalesOrderModal.tsx

Actions and submission/navigation handlers:

- L91 button: (icon/dynamic content) — onClick={onClose}; type="button"; aria-label="Close"
- L92 button: Close model editor — onClick={() => setShowModels(false)}; type="button"
- L93 form: Order No Date Customer * setDraft({ ...draft, customerName: value, customerId: undefined })} onSelect={option => setDraft({ ...draft, customerName: option.name, customerId: option.id })} onAdvance={() => focus('order-marketing')} /> Marketing Person * setDraft({ ...draft, marketingPersonName: value })} onSelect={option => setDraft({ ...draft, marketingPersonName: option.name })} onAdvance={() => focus('customer-type-B2B')} /> Customer Type *{(['B2B', 'B2C'] as const).map(type => setDraft({ ...draft, customerType: type })} onKeyDown={event => advance(event, 'order-requisition')} />{type})}{error(liveErrors.customerType)} Requisition Order setDraft({ ...draft, requisitionOrder: event.target.value })} onKeyDown={event => advance(event, `item-${draft.items[0].id}`)} className={`${ENTRY_INPUT} mt-1`} /> Currency setDraft({ ...draft, currency: e.target.value.toUpperCase() })} className={ENTRY_INPUT} />{error(liveErrors.currency)}Applicable Tax / VAT % (confirm transaction treatment) setDraft({ ...draft, taxRate: e.target.valueAsNumber })} className={ENTRY_INPUT} />{error(liveErrors.taxRate)} Items{effective.items.length} item(s) {['Item', 'Fulfillment Source', 'Quantity', 'Unit', 'Rate', 'Amount', 'Action'].map(label => {label})} {draft.items.map((item, i) => { const available = getAvailableStock(item.itemId, item.itemName, item.unit); return {item.fulfillmentSource === 'manufacturing' && !item.itemId ? updateItem(item.id, { itemName: e.target.value })} className={ENTRY_INPUT} /> : updateItem(item.id, { itemName: value, itemId: undefined, unit: '' })} onSelect={option => { const selected = FINISHED_BY_ID.get(option.id)!; updateItem(item.id, { itemId: selected.id, itemName: finishedGoodLabel(selected), unit: selected.unit }); }} onAdvance={() => focus(`quantity-${item.id}`)} />}{item.fulfillmentSource === 'manufacturing' && Existing Product Model { const model = models.find(m => m.id === e.target.value); updateItem(item.id, { modelId: model?.id, modelRevision: model?.revision, specifications: model?.specifications ?? '', unit: item.itemId ? item.unit : model?.defaultUnit ?? item.unit, itemName: item.itemId ? item.itemName : model?.description || model?.name || '' }); }} className={ENTRY_INPUT}>Select model{models.map(m => {m.name} · Revision {m.revision})} setShowModels(true)} className="text-xs text-navy underline">Create New Custom ModelSpecifications updateItem(item.id, { specifications: e.target.value })} className={ENTRY_INPUT} />Required Delivery Date updateItem(item.id, { requiredDate: e.target.value })} className={ENTRY_INPUT} />Open Costing / Estimate and create a linked draft Job Card from this line after saving the order.}{available !== undefined && Available: {available.toLocaleString('en-IN')} {item.unit}}{available !== undefined && item.quantity > available && Requested quantity exceeds currently available stock.} updateItem(item.id, { fulfillmentSource: e.target.value as SalesOrderItem['fulfillmentSource'] })} className={ENTRY_INPUT}>Select sourceExisting Finished Goods StockCustomized Product / Manufacture{error(errorFor(item, 'source'))} updateItem(item.id, { quantity: event.target.valueAsNumber })} onKeyDown={event => advance(event, `rate-${item.id}`)} className={`${ENTRY_INPUT} min-w-[100px]`} />{error(errorFor(item, 'quantity'))} updateItem(item.id, { unit: event.target.value })} className={ENTRY_INPUT}>Select{[...new Set([...FINISHED_GOODS.map(value => value.unit), ...models.map(m => m.defaultUnit).filter((unit): unit is string => !!unit), 'pcs'])].map(unit => {unit})}{error(errorFor(item, 'unit'))} updateItem(item.id, { unitPrice: event.target.valueAsNumber })} onKeyDown={event => { if (event.key === 'Enter') { event.preventDefault(); nextItem(i); } }} className={`${ENTRY_INPUT} min-w-[100px]`} />{error(errorFor(item, 'price'))} {money(lineTotal(item.quantity, item.unitPrice))} setDraft({ ...draft, items: draft.items.filter(value => value.id !== item.id) })} className="rounded-card p-2 text-gray-400 hover:bg-red-50 hover:text-red-600 disabled:opacity-30"> ; })} Item LED (client-confirmed Higher of the Two){draft.items.filter(i=>i.itemId||i.modelId).map(item=>{item.itemName}updateItem(item.id,{led,ledSnapshot})} productId={item.itemId} modelId={item.modelId} quantity={item.quantity} unit={item.unit} date={draft.date} currency={draft.currency??''} netSelling={item.quantity*item.unitPrice}/>{error(liveErrors[`${draft.items.indexOf(item)}.led`])})} Add Item{error(liveErrors.items)}Subtotal{money(summary.subtotal)}Order Total{incompleteLED?'Complete LED weight/conversion/FX inputs':`${draft.currency ?? ""} ${(totalWithLED??summary.total*(1+(draft.taxRate??0)/100)).toFixed(2)}`} {error(errors.form)} Cancel{submitting ? 'Creating…' : 'Create Order'}{effective.items.some(i => i.fulfillmentSource === 'manufacturing') && Save &amp; Open Costing / Estimate} — onSubmit={submit}
- L107 button: Create New Custom Model — onClick={() => setShowModels(true)}; type="button"
- L113 button: (icon/dynamic content) — onClick={() => setDraft({ ...draft, items: draft.items.filter(value => value.id !== item.id) })}; type="button"; disabled={draft.items.length === 1}; aria-label={`Remove Item ${i + 1}`}
- L118 button: Add Item — onClick={addItem}; type="button"
- L120 button: Cancel — onClick={onClose}; type="button"
- L120 button: {submitting ? 'Creating…' : 'Create Order'} — type="submit"; disabled={submitting}
- L120 button: Save &amp; Open Costing / Estimate — type="submit"; value="costing"; disabled={submitting}

Form fields and binding/validation evidence:

- L95 input Order No: aria-label="Order No"; value={nextOrderNumber(orders)}
- L96 input Date: aria-label="Date"; type="date"; value={draft.date}
- L97 SearchSelect: inputId="order-customer"; label="Customer"; value={draft.customerName}; onChange={value => setDraft({ ...draft, customerName: value, customerId: undefined })}; onSelect={option => setDraft({ ...draft, customerName: option.name, customerId: option.id })}
- L98 SearchSelect: inputId="order-marketing"; label="Marketing Person"; value={draft.marketingPersonName}; onChange={value => setDraft({ ...draft, marketingPersonName: value })}; onSelect={option => setDraft({ ...draft, marketingPersonName: option.name })}
- L99 input: name="customer-type"; id={`customer-type-${type}`}; type="radio"; value={type}; onChange={() => setDraft({ ...draft, customerType: type })}
- L100 input Requisition Order: id="order-requisition"; value={draft.requisitionOrder}; onChange={event => setDraft({ ...draft, requisitionOrder: event.target.value })}
- L102 input Currency: aria-label="Transaction currency"; value={draft.currency ?? ''}; onChange={e => setDraft({ ...draft, currency: e.target.value.toUpperCase() })}
- L102 input Applicable Tax / VAT % (confirm transaction treatment): aria-label="Transaction tax rate"; type="number"; value={draft.taxRate ?? ''}; min="0"; max="100"; step="any"; onChange={e => setDraft({ ...draft, taxRate: e.target.valueAsNumber })}
- L107 input: id={`item-${item.id}`}; aria-label={`Custom product ${i + 1}`}; value={item.itemName}; onChange={e => updateItem(item.id, { itemName: e.target.value })}
- L107 SearchSelect: inputId={`item-${item.id}`}; label={`Item ${i + 1}`}; value={item.itemName}; onChange={value => updateItem(item.id, { itemName: value, itemId: undefined, unit: '' })}; onSelect={option => { const selected = FINISHED_BY_ID.get(option.id)!; updateItem(item.id, { itemId: selected.id, itemName: finishedGoodLabel(selected), unit: selected.unit }); }}
- L107 select Existing Product Model: aria-label={`Product model ${i + 1}`}; value={item.modelId ?? ''}; onChange={e => { const model = models.find(m => m.id === e.target.value); updateItem(item.id, { modelId: model?.id, modelRevision: model?.revision, specifications: model?.specifications ?? '', unit: item.itemId ? item.unit : model?.defaultUnit ?? item.unit, itemName: item.itemId ? item.itemName : model?.description || model?.name || '' }); }}
- L107 textarea Specifications: aria-label={`Specifications ${i + 1}`}; value={item.specifications ?? ''}; onChange={e => updateItem(item.id, { specifications: e.target.value })}
- L107 input Required Delivery Date: type="date"; value={item.requiredDate ?? ''}; onChange={e => updateItem(item.id, { requiredDate: e.target.value })}
- L108 select: aria-label={`Fulfillment source ${i + 1}`}; value={item.fulfillmentSource ?? ''}; onChange={e => updateItem(item.id, { fulfillmentSource: e.target.value as SalesOrderItem['fulfillmentSource'] })}
- L109 input: id={`quantity-${item.id}`}; aria-label={`Quantity ${i + 1}`}; type="number"; value={Number.isNaN(item.quantity) ? '' : item.quantity}; min="0"; step="any"; onChange={event => updateItem(item.id, { quantity: event.target.valueAsNumber })}
- L110 select: aria-label={`Unit ${i + 1}`}; value={item.unit}; onChange={event => updateItem(item.id, { unit: event.target.value })}
- L111 input: id={`rate-${item.id}`}; aria-label={`Rate ${i + 1}`}; type="number"; value={Number.isNaN(item.unitPrice) ? '' : item.unitPrice}; min="0"; step="0.01"; onChange={event => updateItem(item.id, { unitPrice: event.target.valueAsNumber })}

Table headers and mapped label/option arrays (includes filter/UI enums):

- L99 mapped labels/options: ['B2B', 'B2C']
- L105 mapped labels/options: ['Item', 'Fulfillment Source', 'Quantity', 'Unit', 'Rate', 'Amount', 'Action']
- L105 {label}

### src/pages/SalesOrders/SalesInvoice.tsx

Actions and submission/navigation handlers:

- L16 form: Draft sales document. Seller details must come from your company; tax treatment requires confirmation. Invoice creation does not move stock. {fields.map(([key, label]) => {label})}Invoice Date{order.commercialPricing ? "Additional invoice discount (quoted discount apportioned automatically)" : "Discount (before tax)"}Applicable transaction VAT / Tax % Confirmed dispatches to invoice{available.map(d => {d.number} · {d.quantity} {d.unit})}{!available.length && No uninvoiced confirmed dispatches.} setFiscal(e.target.checked)} /> Configured jurisdiction uses fiscal references {fiscal && Enter authority-issued references only. This frontend does not certify fiscal documents or generate verification QR codes.Fiscal Document NumberAuthority Verification Code} {error && {error}} Create frontend invoice — onSubmit={submit}
- L16 button: Create frontend invoice — disabled={!available.length} [implicit submit if inside form; otherwise no click handler]

Form fields and binding/validation evidence:

- L16 input: name={key}; defaultValue={key === 'currency' ? order.currency : key === 'seller' ? company.legalName : key === 'sellerAddress' ? company.address : key === 'sellerTax' ? company.tin : key === 'email' ? company.email : key === 'contact' ? company.telephone : key === 'billingAddress' ? order.customerContact?.billingAddress : key === 'deliveryAddress' ? order.customerContact?.deliveryAddress : key === 'buyerTax' ? order.customerContact?.tin : key === 'paymentTerms' ? order.commercialTerms?.paymentTerms : undefined}; required={['number', 'seller', 'billingAddress', 'currency'].includes(key)}
- L16 input Invoice Date: name="date"; type="date"; defaultValue={today()}
- L16 input: name="discount"; type="number"; defaultValue="0"; readOnly={!!order.commercialPricing}; min="0"; step="0.01"
- L16 input Applicable transaction VAT / Tax %: name="taxRate"; type="number"; defaultValue={order.taxRate}; readOnly={!!order.commercialPricing}; min="0"; max="100"; step="any"
- L16 input ·: name="dispatch"; type="checkbox"; value={d.id}
- L16 input Configured jurisdiction uses fiscal references: type="checkbox"; onChange={e => setFiscal(e.target.checked)}
- L16 input Fiscal Document Number: name="fiscalNumber"
- L16 input Authority Verification Code: name="verificationCode"

Table headers and mapped label/option arrays (includes filter/UI enums):

- L10 mapped labels/options: [['number', 'Invoice Number'], ['seller', 'Seller Company Name'], ['sellerAddress', 'Seller Address'], ['sellerTax', 'Seller Tax ID'], ['email', 'Seller Email'], ['contact', 'Seller Contact'], ['billingAddress', 'Buyer Billing Address'], ['deliveryAddress', 'Buyer Delivery Address'], ['buyerTax', 'Buyer Tax ID'], ['paymentTerms', 'Payment Terms'], ['destination', 'Destination'], ['currency', 'Currency']]
- L10 mapped labels/options: ['number', 'Invoice Number']
- L10 mapped labels/options: ['seller', 'Seller Company Name']
- L10 mapped labels/options: ['sellerAddress', 'Seller Address']
- L10 mapped labels/options: ['sellerTax', 'Seller Tax ID']
- L10 mapped labels/options: ['email', 'Seller Email']
- L10 mapped labels/options: ['contact', 'Seller Contact']
- L10 mapped labels/options: ['billingAddress', 'Buyer Billing Address']
- L10 mapped labels/options: ['deliveryAddress', 'Buyer Delivery Address']
- L10 mapped labels/options: ['buyerTax', 'Buyer Tax ID']
- L10 mapped labels/options: ['paymentTerms', 'Payment Terms']
- L10 mapped labels/options: ['destination', 'Destination']
- L10 mapped labels/options: ['currency', 'Currency']
- L16 mapped labels/options: ['number', 'seller', 'billingAddress', 'currency']
- L19 mapped labels/options: ['Description', 'Quantity', 'Unit', 'Rate', 'Amount']
- L19 {label}

### src/pages/SalesOrders/SalesOrderDetail.tsx

Actions and submission/navigation handlers:

- L27 Link: Return to orders — to="/sales-orders"
- L29 Link: Sales Orders — to="/sales-orders"
- L30 Link: {c.jobCardNumber} · {c.status} — to={`/job-cards/${c.id}`}
- L30 Link: Sales Order → Trace — to={`/track-trace?orderId=${order.id}`}
- L31 Link: {order.quotationNumber} · Revision {order.quotationRevision} — to={`/quotations/${order.quotationRevisionId}`}
- L41 Link: {j.jobCardNumber} · {j.status} — to={`/job-cards/${j.parentJobCardId ?? j.id}?item=${j.id}`}
- L42 Link: Open Costing / Estimate — to={`/costing?orderId=${order.id}&itemId=${item.id}`}
- L42 button: Prepare manufacturing item — onClick={() => { const model = versions.find(m => m.id === item.modelId && m.revision === item.modelRevision); if (!model) { setError('Model revision not found.'); return; } void createLinked(order.id, item.id, model.id, item.requiredDate ?? '', item.specifications ?? '', [], item.estimateId).then(j => setNotice(`${j.jobCardNumber} created as a linked draft for PM review.`)).catch(e => setError(e instanceof Error ? e.message : 'Unable to create job.')); }}; disabled={!item.estimateId}
- L44 form: Stock batchReference stock (batch unavailable){[...new Set(ledger.movements.filter(m => m.productId === item.itemId && m.batch && m.batch !== 'reference-stock').map(m => m.batch!))].map(batch => {batch})} Allocate quantity Allocate Finished Goods — onSubmit={e => { e.preventDefault(); const data = new FormData(e.currentTarget); run(() => allocateStock(order, item, Number(data.get('quantity')), String(data.get('batch')), String(data.get('allocationId')))); }}
- L44 button: Allocate Finished Goods [implicit submit if inside form; otherwise no click handler]
- L45 form: Confirm dispatch / Stock OUT (no reservation required) BatchReference stock{[...new Set(ledger.movements.filter(m=>m.productId===item.itemId && m.batch && m.batch!=='reference-stock').map(m=>m.batch!))].map(b=>{b})}{[['quantity','Quantity','number'],['date','Dispatch date','date'],['challan','Delivery note','text'],['destination','Destination','text'],['vehicle','Vehicle','text'],['remarks','Remarks','text']].map(([key,label,type])=>{label})} Confirm physical Stock OUT — onSubmit={e=>{e.preventDefault();const f=new FormData(e.currentTarget);run(()=>directDispatch(order,item,String(f.get('batch')),{id:String(f.get('requestId')),quantity:Number(f.get('quantity')),date:String(f.get('date')),challan:String(f.get('challan')),destination:String(f.get('destination')),vehicle:String(f.get('vehicle')),remarks:String(f.get('remarks'))}));}}
- L45 button: Confirm physical Stock OUT [implicit submit if inside form; otherwise no click handler]
- L46 form: Dispatch allocation · {a.batch} · Remaining {a.quantity - a.dispatched} {item.unit} {[['quantity', 'Dispatch Quantity', 'number'], ['date', 'Dispatch Date', 'date'], ['challan', 'Delivery Note / Challan', 'text'], ['destination', 'Destination', 'text'], ['vehicle', 'Transport / Vehicle', 'text'], ['remarks', 'Remarks', 'text']].map(([name, label, type]) => {label})} Confirm Dispatch / Stock OUT — onSubmit={e => { e.preventDefault(); const f = new FormData(e.currentTarget); const dispatchId = String(f.get('dispatchId')); run(() => dispatch({ id: dispatchId, allocationId: a.id, quantity: Number(f.get('quantity')), date: String(f.get('date')), challan: String(f.get('challan')), destination: String(f.get('destination')), vehicle: String(f.get('vehicle')), remarks: String(f.get('remarks')) })); }}
- L46 button: Confirm Dispatch / Stock OUT — disabled={!canFulfill} [implicit submit if inside form; otherwise no click handler]
- L49 form: Cancel with reversal — onSubmit={e => { e.preventDefault(); const f = new FormData(e.currentTarget); run(() => reverse(d.id, String(f.get('date')), String(f.get('reason')))); }}
- L49 button: Cancel with reversal [implicit submit if inside form; otherwise no click handler]
- L49 Link: Stock transaction {m.id} — to="/stock"
- L49 Link: Job Card — to={`/job-cards/${m.jobCardId}`}
- L49 Link: Job Card {j} — to={`/job-cards/${j}`}
- L50 button: Create Invoice — onClick={() => setInvoiceOpen(!invoiceOpen)}
- L57 form: Prepare parent Job Card manufacturing item Editable draft: model BOM quantities are unavailable. Enter reviewed material requirements; no formulas are assumed. ModelSelect model{models.map(m => {m.name} · {m.billOfMaterials})} Required Delivery Date Specifications {materials.map((row, i) => setMaterials(materials.map((r, n) => n === i ? { ...r, id: e.target.value } : r))} className={ENTRY_INPUT}>Select material{RAW_MATERIALS.map(m => {m.name} ({m.unit}))} setMaterials(materials.map((r, n) => n === i ? { ...r, qty: e.target.value } : r))} className={ENTRY_INPUT} />)} setMaterials([...materials, { id: '', qty: '' }])}>Add material {saving ? 'Creating…' : 'Prepare manufacturing item'} — onSubmit={e => void submit(e)}
- L57 button: Add material — onClick={() => setMaterials([...materials, { id: '', qty: '' }])}; type="button"
- L57 button: {saving ? 'Creating…' : 'Prepare manufacturing item'} — disabled={saving} [implicit submit if inside form; otherwise no click handler]

Form fields and binding/validation evidence:

- L44 input: name="allocationId"; type="hidden"; value={`allocation-${order.id}-${item.id}-${allocations.length}`}
- L44 select Stock batch: name="batch"
- L44 input Allocate quantity: name="quantity"; type="number"; min="0.000001"; step="any"
- L45 input: name="requestId"; type="hidden"; value={`direct-${order.id}-${item.id}-${ledger.dispatches.length}`}
- L45 select Batch: name="batch"
- L45 input: name={key}; type={type}; defaultValue={key==='date'?today():undefined}; required={['quantity','date','challan','destination'].includes(key)}; min={type==='number'?'0.000001':undefined}; step="any"
- L46 input: name="dispatchId"; type="hidden"; value={`dispatch-${a.id}-${ledger.dispatches.length}`}
- L46 input: name={name}; type={type}; defaultValue={name === 'date' ? today() : undefined}; required={['quantity', 'date', 'challan', 'destination'].includes(name)}; min={name === 'quantity' ? '0.000001' : undefined}; step="any"
- L49 input: name="date"; aria-label="Reversal date"; type="date"; defaultValue={today()}
- L49 input: name="reason"; aria-label="Cancellation reason"
- L57 select Model: name="model"
- L57 input Required Delivery Date: name="date"; type="date"
- L57 textarea Specifications: name="specs"
- L57 select: aria-label={`Required material ${i + 1}`}; value={row.id}; onChange={e => setMaterials(materials.map((r, n) => n === i ? { ...r, id: e.target.value } : r))}
- L57 input: aria-label={`Material quantity ${i + 1}`}; type="number"; value={row.qty}; min="0.000001"; step="any"; onChange={e => setMaterials(materials.map((r, n) => n === i ? { ...r, qty: e.target.value } : r))}

Table headers and mapped label/option arrays (includes filter/UI enums):

- L28 mapped labels/options: ['admin', 'store_keeper', 'receptionist']
- L38 mapped labels/options: ['InProduction', 'MaterialIssued']
- L40 mapped labels/options: [['Ordered', item.quantity], ['Allocated remaining', allocated], ['In production', jobs.filter(j => !['Completed', 'ReadyForStock'].includes(j.status)).reduce((sum, j) => sum + j.qty, 0)], ['Finished goods received', received], ['Dispatched', sent], ['Remaining', item.quantity - sent]]
- L40 mapped labels/options: ['Completed', 'ReadyForStock']
- L45 mapped labels/options: [['quantity','Quantity','number'],['date','Dispatch date','date'],['challan','Delivery note','text'],['destination','Destination','text'],['vehicle','Vehicle','text'],['remarks','Remarks','text']]
- L45 mapped labels/options: ['quantity','Quantity','number']
- L45 mapped labels/options: ['date','Dispatch date','date']
- L45 mapped labels/options: ['challan','Delivery note','text']
- L45 mapped labels/options: ['destination','Destination','text']
- L45 mapped labels/options: ['vehicle','Vehicle','text']
- L45 mapped labels/options: ['remarks','Remarks','text']
- L45 mapped labels/options: ['quantity','date','challan','destination']
- L46 mapped labels/options: [['quantity', 'Dispatch Quantity', 'number'], ['date', 'Dispatch Date', 'date'], ['challan', 'Delivery Note / Challan', 'text'], ['destination', 'Destination', 'text'], ['vehicle', 'Transport / Vehicle', 'text'], ['remarks', 'Remarks', 'text']]
- L46 mapped labels/options: ['quantity', 'Dispatch Quantity', 'number']
- L46 mapped labels/options: ['date', 'Dispatch Date', 'date']
- L46 mapped labels/options: ['challan', 'Delivery Note / Challan', 'text']
- L46 mapped labels/options: ['destination', 'Destination', 'text']
- L46 mapped labels/options: ['vehicle', 'Transport / Vehicle', 'text']
- L46 mapped labels/options: ['remarks', 'Remarks', 'text']
- L46 mapped labels/options: ['quantity', 'date', 'challan', 'destination']

### src/pages/SalesOrders/SalesOrderList.tsx

Actions and submission/navigation handlers:

- L84 Link: View fulfillment — to={`/sales-orders/${order.id}`}
- L95 Link: Job card {order.jobCardIds.length > 1 ? ` ${i + 1}` : ""} — to={`/job-cards/${id}`}
- L204 button: Export CSV — onClick={() => downloadCsv(filtered)}; type="button"; disabled={filtered.length === 0}
- L212 button: New order — onClick={() => setShowNewOrder(true)}; type="button"
- L277 button: {label} {count} — onClick={() => setStatusFilter(value)}; type="button"
- L291 button: Clear filters — onClick={clearFilters}; type="button"
- L310 button: New order — onClick={() => setShowNewOrder(true)}; type="button"
- L318 button: Clear filters — onClick={clearFilters}; type="button"
- L342 Link: {order.orderNumber} — to={`/sales-orders/${order.id}`}
- L370 Link: (icon/dynamic content) — to={`/sales-orders/${order.id}`}; aria-label={`Open ${order.orderNumber}`}
- L392 button: (icon/dynamic content) — onClick={() => setPage(safePage - 1)}; type="button"; disabled={safePage === 1}; aria-label="Previous page"
- L404 button: (icon/dynamic content) — onClick={() => setPage(safePage + 1)}; type="button"; disabled={safePage === pageCount}; aria-label="Next page"

Form fields and binding/validation evidence:

- L245 input: id="so-search"; type="search"; value={query}; onChange={(e) => setQuery(e.target.value)}
- L258 select: id="so-sort"; value={sort}; onChange={(e) => setSort(e.target.value as SortKey)}

Table headers and mapped label/option arrays (includes filter/UI enums):

- L51 mapped labels/options: ["Order number", "Customer Name", "Order Date", "Marketing Person Name", "Customer Type", "Requisition Order", "Item", "Quantity", "Unit", "Per Unit Price", "Total Price", "Order Total", "Status", "Job cards"]
- L327 Order
- L328 Customer Name
- L329 Order Date
- L330 mapped labels/options: ['Marketing Person Name', 'Customer Type', 'Requisition Order', 'Item', 'Quantity', 'Unit', 'Per Unit Price', 'Total Price', 'Order Total']
- L331 {label}
- L333 Job card
- L334 Status
- L335 <span className="sr-only">Open</span>
- L351 mapped labels/options: ['itemName', 'quantity', 'unit', 'unitPrice', 'totalPrice']

### src/pages/Stocks/SalesOrderDemand.tsx

Actions and submission/navigation handlers:

- L28 Link: {item.orderNumber} — to={`/sales-orders/${orders.find(o => o.orderNumber === item.orderNumber)?.id}`}

Table headers and mapped label/option arrays (includes filter/UI enums):

- L12 mapped labels/options: ['Completed', 'Cancelled']
- L26 mapped labels/options: ['Order', 'Customer', 'Product / Variant', 'Ordered Qty', 'Available Finished Stock', 'Required Qty', 'Unit', 'Status']
- L26 {label}

### src/pages/Stocks/stocks.tsx

Actions and submission/navigation handlers:

- L93 Link: Approved Job Card receipts — to="/job-cards"
- L96 button: Stock IN — onClick={() => setDirection('IN')}; type="button"
- L96 Link: Receive Approved Batch — to="/job-cards"
- L96 button: Stock OUT — onClick={() => setDirection('OUT')}; type="button"
- L102 button: {label} — onClick={() => { setTab(id); resetList(); }}; type="button"
- L103 button: {label} — onClick={() => { setCategory(id); setBrand('all'); setUnit('all'); resetList(); }}; type="button"
- L114 button: Export CSV — onClick={exportReport}; type="button"
- L114 button: Print report — onClick={() => { setLimit(products.length); requestAnimationFrame(() => window.print()); }}; type="button"
- L120 Link: Sales Order — to={`/sales-orders/${movement.salesOrderId}`}
- L120 Link: Job Card — to={`/job-cards/${movement.jobCardId}`}
- L130 button: Daily movements — onClick={() => setExpanded(expanded === product.id ? null : product.id)}; type="button"; aria-label={`Daily movements for ${finishedGoodLabel(product)}`}
- L132 Link: Sales Order — to={`/sales-orders/${movement.salesOrderId}`}
- L132 Link: Job Card — to={`/job-cards/${movement.jobCardId}`}
- L136 button: Show more — onClick={() => setLimit(limit + 25)}; type="button"

Form fields and binding/validation evidence:

- L105 input: aria-label="Search finished goods"; type="search"; value={query}; onChange={event => { setQuery(event.target.value); resetList(); }}
- L106 select: aria-label="Brand"; value={brand}; onChange={event => { setBrand(event.target.value); resetList(); }}
- L107 select: aria-label="Unit"; value={unit}; onChange={event => { setUnit(event.target.value); resetList(); }}
- L108 input From: aria-label="Movement start date"; type="date"; value={from}; onChange={e => setFrom(e.target.value)}
- L108 input To: aria-label="Movement end date"; type="date"; value={to}; onChange={e => setTo(e.target.value)}
- L108 select: aria-label="Model filter"; value={model}; onChange={e => setModel(e.target.value)}
- L109 select: aria-label="Movement type"; value={movementType}; onChange={event => { setMovementType(event.target.value); resetList(); }}
- L110 input Month: aria-label="Report month"; type="month"; value={month}; onChange={event => { if (event.target.value) setMonth(event.target.value); setExpanded(null); }}

Table headers and mapped label/option arrays (includes filter/UI enums):

- L18 mapped labels/options: [['levels', 'Stock Levels'], ['movements', 'Movements'], ['report', 'Monthly Report']]
- L18 mapped labels/options: ['levels', 'Stock Levels']
- L18 mapped labels/options: ['movements', 'Movements']
- L18 mapped labels/options: ['report', 'Monthly Report']
- L86 mapped labels/options: ['Product ID', 'Product', 'Category', 'Customer', 'Size', 'Brand', 'Pieces', 'Packaging', 'Unit', 'Opening Stock', 'Total IN', 'Total OUT', 'Closing Stock']
- L103 mapped labels/options: ['all', 'All']
- L117 mapped labels/options: ['Date', 'Product / Variant', 'Category', 'Movement', 'Quantity', 'Unit', 'Reference', 'Customer / Destination']
- L117 {label}
- L123 mapped labels/options: ['Product / Item', 'Category', 'Size', 'Brand', 'Pieces', 'Packaging', 'Physical Stock', 'Reserved', 'Available', 'Unit', 'Status']
- L123 mapped labels/options: ['Product / Variant', 'Category', 'Opening Stock', 'Total IN', 'Total OUT', 'Closing Stock', 'Unit', 'Details']
- L123 {label}
- L132 mapped labels/options: ['Date', 'Movement', 'Quantity', 'Unit', 'Reference', 'Customer / Destination']
- L132 {label}
- L143 mapped labels/options: [['Size', product.size || '—'], ['Brand', product.brand || '—'], ['Packaging', product.packingSize || '—'], ['Customer', product.customer || '—'], ['Opening Stock', fmt(balances.get(product.id)!.openingStock)], ['Stock IN', fmt(balances.get(product.id)!.stockIn)], ['Stock OUT', fmt(balances.get(product.id)!.stockOut)], ['Status', balances.get(product.id)!.currentStock === null ? 'Not recorded' : balances.get(product.id)!.currentStock! < 0 ? 'Negative balance' : balances.get(product.id)!.currentStock === 0 ? 'Out of stock' : 'In Stock']]

### src/pages/TrackTrace/ConnectedTrace.tsx

Actions and submission/navigation handlers:

- L25 Link: {j.jobCardNumber} · {j.status} — to={`/job-cards/${j.parentJobCardId??j.id}?item=${j.id}`}
- L25 Link: {j.salesOrderNumber??j.salesOrderId} — to={`/sales-orders/${j.salesOrderId}`}
- L25 Link: Trace → Costing — to={`/costing?orderId=${j.salesOrderId}&itemId=${j.salesOrderItemId??''}`}
- L26 Link: Sales Order — to={`/sales-orders/${m.salesOrderId}`}
- L26 Link: Job Card — to={`/job-cards/${m.jobCardId}?item=${m.manufacturingItemId??m.jobCardId}`}
- L27 Link: Costing — to="/costing"
- L28 button: Legacy API / sample trace lookup — onClick={()=>setLegacy(!legacy)}

Form fields and binding/validation evidence:

- L23 select Product: value={productId}; onChange={e=>set('productId',e.target.value)}
- L23 select Job / manufacturing item: value={jobId}; onChange={e=>set('jobId',e.target.value)}
- L23 select Sales Order: value={orderId}; onChange={e=>set('orderId',e.target.value)}
- L23 input Exact batch reference: value={batch}; onChange={e=>set('batch',e.target.value)}

Table headers and mapped label/option arrays (includes filter/UI enums):

- L21 mapped labels/options: ['accounts','admin','production_manager']

### src/pages/TrackTrace/TrackTrace.tsx

Actions and submission/navigation handlers:

- L53 form: setQuery(e.target.value)} placeholder="e.g. JC-1042" className="flex-1 rounded-card border border-gray-200 px-4 py-2 text-sm focus:border-blue focus:outline-none" /> {loading ? "Searching…" : "Search"} — onSubmit={handleSearch}
- L60 button: {loading ? "Searching…" : "Search"} — type="submit"; disabled={loading}
- L72 button: {exampleId} — onClick={() => handleExampleClick(exampleId)}; type="button"

Form fields and binding/validation evidence:

- L54 input: value={query}; onChange={(e) => setQuery(e.target.value)}

Table headers and mapped label/option arrays (includes filter/UI enums):

- L71 mapped labels/options: ["SO-1042", "JC-2201", "RM-8834", "GB-0501"]
