# Existing ERP frontend/backend integration

21 October 2026, Asia/Calcutta. Local development implementation, not operational approval.

## Scope and preservation

Existing React application, routes, shell and design retained. Backend forms were made
reusable inside existing module screens; no new ERP application or parallel set of
module routes was introduced. `/commercial`, `/admin/inventory` and `/rehearsal` remain
compatible legacy entry points. Demo sessions retain their existing screens. Real
sessions use API data and cannot fall back to demo records on these connected routes.

Initial unrelated changes were preserved: root/backend ignore files, Render environment
documents, the untracked Render template/test and initialization/checklist documents.
No staging, commit, push, deployment, historical migration edit or configured application
database migration was performed. New recycling persistence extends existing immutable
rehearsal snapshots/revisions rather than introducing another ledger or balance model.

Read repository/application guidance, architecture and decision documentation, client
source review, Phase 3/4 implementation reports and one-day ERP report. Re-extracted
the main XML of all 18 SOP originals read-only and checked their recorded SHA256s.
The SOP effective date remains 1 November 2026; no operational adoption is inferred.

## Route and integration matrix

- `/login`, `/finance/login`: existing JWT login, profile restore, refresh and server
  logout. Finance login now uses the same real identity without fabricated Finance rights.
- `/`: existing Dashboard route renders persisted scoped rehearsal aggregates, permitted
  master counts, draft commercial summaries, currency-separated estimates and synthetic
  output/waste. No sample totals for real sessions. Requires report capability and active
  development context; unavailable values are not replaced with zero.
- `/masters`: API-backed customer/prospect/supplier/product/variant/material/consumable/
  unit/department/machine/area/specification catalog. Capability-filtered tabs; search,
  active filter, pagination, create, patch, detail, references, server validation,
  stable retry keys and record versions. Source identities/native units remain immutable.
- Masters specifications: sealed revision list/details and additive revision creation
  against the current parent version. Advanced recipe/route/process entries currently
  use validated API-field JSON arrays, not a polished visual line editor.
- Masters warehouses/locations: reuse existing inventory configuration forms, identity
  registration and scoped audit history.
- Masters employees: only the server Master Admin designation plus explicit employee
  capability exposes the directory. List/search/pagination/create/edit/detail use the
  current protected employee API. Account creation grants no password or business role.
  Full role-policy publication/access-reset/status UI remains follow-up work.
- Masters governed imports: staging CSV/values-only XLSX, paginated source evidence,
  explicit JSON field mappings/row decisions, canonical review and current-plan apply.
  Existing source-kind, target-capability, uniqueness and stale-plan guards remain.
  No client workbook was imported by this sprint. Apply is disabled for demo sources.
- `/costing`: existing route uses the persisted commercial costing editor. Exact-string
  material/process components, native units/currency, loss assumptions, markup,
  immutable cost snapshots and supported backend per-kg/per-ctr estimates. No inferred FX.
- `/quotations`, `/quotations/:id`, `/quotations/:id/edit`: persisted commercial drafts,
  reference selectors, multiple lines, prices/discount, marketing references where
  permitted, dates/specifications, costing revisions, edit/review/reopen/cancel,
  derivation/history/comparison and watermarked draft print previews.
- `/quotations/settings`: existing route now shows the governed policy/decision registry
  for real sessions instead of suggesting that local company/tax defaults are adopted.
- `/sales-orders`, `/sales-orders/new`, `/sales-orders/:id`: same persisted commercial
  service, filtered to Sales Order drafts, with draft demand explicitly unconfirmed.
  Order creation and derivation never reserve/deduct stock.
- `/stock`, `/raw-materials`, `/consumables`: existing routes use exact item-type custody
  filters, balances, held/released partitions, movement pagination and UTC month filter.
  Existing IN/OUT/opening/correction/transfer/return/count/adjustment evidence forms
  are embedded. Warehouse scope, physical-source line and multi-actor checks remain.
  Evidence/reference UUID entry still needs more selector/scanner UX.
- `/job-cards`, `/job-cards/:id`: persisted rehearsal jobs, order/costing origins,
  product-specific routes, estimated requirements, synthetic review/issue, operator/
  machine/stage quantities, waste/rejection, QC, finish, history and version conflicts.
  Rehearsal is not operational production posting.
- `/qc`, `/qc/:section`, `/qc/inspections/:id`: existing routes use Phase 3 QC forms,
  plans, inspections/review, held stock, containment and NCR/CAPA/history. The detail
  route loads the requested inspection. Legacy cleaning/safety/machine scheduling
  screens do not have equivalent operational APIs and are not claimed as integrated.
  Rehearsal QC remains separately visible in job/trace records.
- `/track-trace`, `/dispatch`: persisted job selection, exact commercial source revision,
  estimated materials, synthetic issue/stages/QC, immutable timeline, guarded simulated
  dispatch and linked draft invoice preview. Operational dispatch remains disabled.
- `/recycling`: persisted development batches within rehearsal revisions. Completed
  stage source, PROCESS_WASTE/REJECTED_OUTPUT classification, intake/recovered/rejected/
  disposed amounts, exact source unit, synthetic batch reference and immutable source
  revision. Conservation, remaining-source allocation, owner/warehouse scope,
  optimistic version and idempotency enforced. No recovered available-stock credit.
  External waste procurement, multi-source reprocessing and operational recycling remain.
- `/finance`: currency/party/document-kind separated draft estimates, known snapshotted
  production costs and estimated margin only when every line supplies a cost. Draft
  kinds overlap and must not be summed into revenue. Invoice examples remain on trace.
- `/finance/quality`: real sessions use permission-checked QC records rather than
  session-only finance counts.
- Header notifications: internal notifications derived from owned scoped persisted
  synthetic job statuses. No customer messaging or authoritative notification delivery.
- Unknown paths: visible unavailable-page message instead of silently landing in rehearsal.

## Backend mappings and changes

- Existing `/api/v1/auth/{login,me,refresh,logout}/` unchanged.
- Master routes `/customers/`, `/prospects/`, `/suppliers/`, `/products/`, `/finished-goods/`,
  `/raw-materials/`, `/consumables/`, `/units/`, `/departments/`, `/machines/`, `/areas/`,
  `/models/`: list/detail/create/PATCH. New capability-checked `schema/` describes
  writable fields/choices/nullability without enumerating protected related directories.
- `/models/{id}/revisions/`, `/employees/`, `/imports/` and import rows/review/approve:
  reused existing services and permissions.
- `/commercial/documents/`: owner/development guards preserved; added validated `kind`
  filtering before pagination. Existing detail/history/transition/derive endpoints reused.
- `/inventory/{warehouses,locations,identities,history,operations,custody,quality}/`:
  reused existing endpoints. Custody movements now validate optional `month=YYYY-MM`
  and apply a UTC half-open month range before pagination and after scope filtering.
- `/rehearsal/jobs/` and detail/history/command/dashboard: reused command executor,
  source locks, audit, sealed revisions and guards. Added `recycle` command and permitted
  catalog/party/cost/margin/recycling aggregates plus synthetic status notifications.

## Bugs addressed

- Removed the real-session three-route redirect and restricted sidebar.
- Stopped legacy quotation/customer providers from requesting incompatible APIs for
  real sessions; connected modules use their typed current adapters.
- Added a collapsible mobile module menu.
- Added direct persisted document/job/inspection reads for existing detail routes.
- Filtered commercial records on the server before pagination, avoiding mixed module lists.
- Preserved decimal strings throughout new adapters/forms; no quantity Number conversion.
- Retained failed form values and unchanged retry intent, with visible API failures.
- Added duplicate-submit locks to new master/employee/import/recycling/dispatch forms.
- Added unsaved-field confirmation on sidebar navigation for marked master/commercial/job
  forms; browser unload protection remains. This is not yet comprehensive SPA/back-button
  protection for every embedded form.
- Protected employee navigation with the server designation and capability, not role labels.

## Local database and storage

React remains `http://localhost:5173`; Django acceptance API is `http://127.0.0.1:8000/api/v1`.
Local frontend `.env` (ignored) disables mock login and targets localhost:8000/api/v1.
The configured database is not a valid substitute for guarded development execution.

`backend/scripts/serve_full_erp_acceptance.py --disposable-synthetic-only --port 8000
--seconds 3600` creates/migrates/stamps only a new `test_phase3b_<uuid>` database.
It combines existing synthetic commercial/production and inventory/QC fixtures, with
fixture-only account capabilities/scopes. It binds loopback, accepts the local Vite
origin and destroys only its own generated database on bounded shutdown. Metadata
and synthetic sign-in details are ignored under `.local/full-interface/browser-fixtures.json`.
Do not run this concurrently with another server bound to port 8000.

Records survive refresh/logout/relogin during that active database session. They are
intentionally not retained after teardown. Persistent local development provisioning
has NOT been authorized/executed; see LOCAL_DEVELOPMENT_DATABASE_PROVISIONING_PLAN.md.

## Verification

- Initial Masters/JWT/PostgreSQL batch: 33 tests passed in a freshly stamped database.
- Commercial/rehearsal/recycling/finance focused batch: 36 tests passed.
- Final new Masters React-to-Django JWT HTTP transport, metadata permissions, recycling,
  finance estimates and month filter: 8 tests passed in another fresh stamped database.
- All 16 pre-existing frontend check scripts passed; new check-masters-api.mjs passed.
- TypeScript noEmit passed; production build passed. Existing large bundle warning remains.
- Django check: no issues. Migration drift: no changes detected. No new migration required.
- Full isolated PostgreSQL regression: **320 tests passed**, 1234.698 seconds,
  followed by destruction of its generated database. This includes existing commercial,
  inventory/QC, concurrency, restore/migration, role-governance, rehearsal and HTTP tests.
- The new Masters HTTP test was added after main-suite discovery; the separate 8-test
  final transport run passed. A further 3-test final metadata run also passed, including
  JSON type/nullability and no related-directory enumeration.
- Final run of all **17** frontend validation scripts, TypeScript noEmit and production
  build passed (`ALL_FRONTEND_CHECKS_PASSED`). Existing bundle-size warning remains.
- Rendered browser acceptance: real JWT sign-in; full sidebar; customer create/edit;
  preserved customer/version after refresh, server logout and reauthentication; exact
  Sales Order quantity `2.000001` persisted with revision history; scoped raw-material
  HELD/RELEASED balances; QC queue; navigation to every sidebar module; exact recycling
  intake `0.500001` saved with immutable source revision and no stock credit; finance
  estimates; internal status notifications; dispatch-linked watermarked invoice preview.
- Responsive navigation checked at 390 × 844: mobile module menu expands/collapses;
  desktop viewport restored. No claim of exhaustive visual/device testing.
- Final Django check and migration drift inspection passed; Git diff whitespace check
  passed. No configured application migrations were run.

Local ignored evidence: backend/.local/full-interface-regression.log,
full-interface-focused.log, full-interface-transport-final.log,
full-interface-schema-final.log, full-interface-frontend-final.log and
full-interface-browser-final.log. Browser snapshot evidence is stored outside Git under
this chat's visualization directory. The first acceptance database was gracefully
stopped/destroyed before launching the final fresh session; browser-created records
from that first session were intentionally disposable, not persistent storage.

## Remaining policy and implementation work

No legal invoice, payment/accounting posting, tax/levy/FX rule, commercial acceptance/
approval/confirmation, operational dispatch or recovered-stock availability was invented.
Missing approved authority, physical evidence, QC criteria and rollout/cutover decisions
continue to block those commands. No customer email was sent.

This is a broad local integration with advanced JSON/UUID forms in several modules,
not completion of every legacy visual control or operational SOP. Further work includes
friendly import/specification editors, full employee access-governance UI, external
recycling procurement, unsupported QC schedules, comprehensive navigation draft recovery,
server report coverage for all operational domains and production-scale query/performance QA.

## Render prerequisites

Deployment is separate and was not executed. Review the existing Render/demo documents;
authorize a persistent database and exact forward migrations, least-privilege runtime
grants, independent secrets, HTTPS/CORS domains, backups/restore and expiry controls.
Vite API URL must point to the reviewed backend and mock login must stay disabled.
Use the approved persistent DEMO boundary where applicable, never the disposable harness
or a synthetic-ledger flag as a production switch. Operational policy approval remains
separate from successful hosting.
