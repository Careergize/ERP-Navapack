# Quality Control implementation and proposed backend specification

Updated 13 October 2026. Canonical QC specification for the existing ERP. This document describes implemented frontend behavior separately from proposed Django/DRF contracts. No QC endpoints, Django code, database migrations or backend authorization were implemented.

## Evidence and gap analysis

The supplied attachment contains the task transcription only. **None of the eight photographs is available for inspection.** Six described form structures are used provisionally: Personnel Safety, Extruded Roll Samples, Weekly Extruder, Weekly Recycle Extruder, Factory/General Area Cleaning, and Raw Material Receipt/Analysis. The relationship between six forms and eight photographs cannot be established. Document codes, printed revisions, effective dates, handwritten examples and machine names were not inferred. Photograph references/images must be added here after the actual files are supplied and verified. Seed template revision 1 and effective date 13 October 2026 are ERP configuration, not transcribed paper metadata.

Before editing, the repository showed shared authentication and role navigation; ModelsContext; parent/item Job Cards with costing/routing snapshots; sequential stages; raw/finished inventory ledgers; Store/Admin QC checkbox receipts; legacy Recycling data; transaction reports; and five helper check scripts. Gaps were no QC role, inspection engine/history, quality holds, independent QC review, separate final FG authorization, shared machine master, corrective actions or backend QC contracts. Existing raw inward movements have exact IDs, quantities and units but no authoritative supplier or supplier-batch relationship. Production stages contain aggregated output, not separate execution runs. The implementation preserves those limits instead of guessing source records.

## Implemented screens, roles and store boundaries

- `/qc`: QC dashboard. QC Inspector and QC Supervisor also see this dashboard at `/` after the same ERP login. Other roles keep the operations dashboard.
- `/qc/raw`, `/qc/production`, `/qc/machine`, `/qc/cleaning`, `/qc/safety`: category lists, creation/scheduling and inspection history.
- `/qc/inspections/:id`: response grid, samples/measurements, independent review, releases, findings, assignment and activity.
- `/qc/non-conformances`: assignment, correction, independent verification and closure history.
- `/qc/reports`: filtered category reports, Job Card history and monthly/full QC summary; date/department/inspector/status/source search filters.
- `/qc/templates`: exact template revisions, Admin revisions/new templates, shared-machine setup and configurable cleaning areas.

`qc_inspector` records assigned drafts, measurements/findings, submits, reports NCs and creates linked reinspections. `qc_supervisor` has the same recording permissions plus independent review, quality release and corrective-action management. Admin manages templates/assignments and may review someone else's submission. Production Manager sees production QC and separately authorizes finished-stock quantities; Store sees acceptance/release and posts the authorized receipt. Inspectors cannot approve their own submissions; even Admin review requires a different submitting user. Only QC staff/Admin can create inspection records. QC routes deny unrelated roles; QC users are redirected away from unrelated ERP routes and the internal Job Card Costing tab is hidden from QC roles. These are demonstrative frontend guards, not server authorization. No real role-mapping administration or persistent user assignment directory has been implemented; Admin assigns existing stable user IDs.

QualityProvider owns session inspection/template/release/NC state; it is placed above InventoryProvider and JobCardsProvider to supply synchronous current-state guards. InventoryProvider still owns all stock postings. ModelsContext owns new shared machine IDs alongside existing model masters; no second machine registry or inventory store is introduced. Models and production routing can choose machine IDs and mandatory QC template IDs. Model-based costing and existing route/material snapshots remain unchanged apart from these optional routing references. Recycling displays warnings from recycle-extruder inspections without posting waste or inventory.

## Template and inspection rules

Templates capture name/code, revision/effective date, category/department, frequency, applicability, active state, approval requirement, checklist items, response types and source provenance. Admin edits append revisions; historical inspections retain cloned template content. New ordinary inspections select the latest active revision. Reinspection retains the original exact template snapshot. Choice responses support Yes/No, OK/Not OK, Tick/Cross and Pass/Fail; numeric/text types and permitted Not Applicable responses share one form component. NA needs a reason; an all-NA inspection cannot pass. Required/failing findings need remarks. Measurements keep actual, target, minus tolerance, plus tolerance and unit separately; actual must be within the explicit inclusive bounds. No numeric criteria are guessed from sample handwriting or inferred unit conversion.

The safety form contains the seven checks in the task. It records compliance observations, not diagnoses or employee medical histories. Extruded-roll samples contain the nine described checks plus actual width/thickness fields, with one to eight independent sample columns/sets. **Objectionable odour has acceptable answer No**; other positive checks have acceptable answer Yes. The standard extruder and recycle-extruder templates keep their different six-component lists. Machine records are separate per stable machine ID and displayed in a consolidated matrix. Cleaning activities are separate per configured area/date/time, with method, chemicals/instruments, cleaner and independent checker/review; the digital observations field is a proposed ERP field, not a verified printed row. Raw inspections retain the exact IN receipt/material ID, procured quantity/unit, manually recorded supplier lot, grade, sampled quantity, COA/TDS/MSDS availability, appearance/colour/packaging and acceptance observations. Supplier ID remains unrecorded where the inward record does not supply it; there is no supplier-name matching.

Draft → Submitted → independent Passed/Failed/Reinspection Required decision → Quality release. Raw review also supports Conditionally Accepted, which stays held until a successful linked reinspection and release. Inspector submission records a derived Pass/Fail but creates neither a release nor stock. Drafts may be edited only by assigned QC staff/Admin; submitted answers cannot be overwritten. Review appends attributable approval records. Failed checks cannot be reviewed as Passed. Reinspection creates a new inspection linked to the original; repeated correction chains retain every failed result. Open NCs for the same subject prevent quality release, including when the passing record is a reinspection. Closing an NC does not itself pass an inspection or release stock.

Cleaning statuses are presented through this generic lifecycle: Draft is a scheduled activity; Submitted is completed/pending verification; released Passed is verified; Failed/Reinspection Required requires recleaning and a linked new activity. Machine resolution likewise requires independent passing review and quality release; editing a checklist or merely creating a later inspection does not automatically erase earlier equipment warnings.

## Production, receipt and inventory integration

Raw receipt and inspection are distinct. Physical raw IN balances are retained, including rejected/pending quantities. Raw quality status distinguishes pending, held/rejected, conditionally accepted/held and accepted/released. Ordinary Job Card issue and raw OUT compare usable stock against physical balance minus unreleased receipt quantities. Unknown balances with pending QC cannot be issued. Existing opening balances have no receipt/batch QC provenance and are not represented as inspected/accepted. Historical IN references are not fabricated as accepted; reconciliation with authoritative batch balances is needed before production use. This conservative frontend calculation is not a batch-consumption ledger and does not record supplier returns.

QC production lots are registered with stable UUIDs on the existing manufacturing item, exact completed stage, actual lot number, output quantity/unit and creation time. Lots at a stage cannot total more than its recorded output; repeating the same lot returns its original identity and rejects changed quantities. These are **inspection lot partitions of existing stage output**, not new manufacturing runs. Separate execution runs/stage quantities remain a future production integration requirement. A production inspection links parent Job Card → manufacturing item → model/revision → completed stage → QC lot. No name-based product linking is used.

Approved stage routing determines mandatory template IDs. Advancing a stage validates released QC coverage of the prior mandatory checkpoint's full output, separately per unit and unique lot; multiple inspections/reinspections cannot double-count the same lot. Any unresolved QC record or open NC holds the affected item, not other items on its parent. Existing previous-stage completion guards remain. Since execution stages are currently item-wide, a batch hold conservatively blocks advancement of that item; independent advancement of multiple runs within the same item is not implemented. A linked machine needs a verified record without unresolved warnings before stage updates; unlinked legacy machine text is not treated as a verified machine ID. Schedules are recorded by dated drafts; no background scheduler or authoritative compliance calendar is implied.

Finished production requires QC quality release, then **separate Production Manager/Admin authorization**, then Store/Admin receipt. Production Manager is the reused managerial final authority; QC Supervisor approval alone does not permit stock posting. Client must confirm the final authority mapping. Final authorization applies only to recorded completed final-stage output, and carries accepted/rejected quantities and explicit output unit. One physical QC lot cannot receive duplicate final authorizations through multiple inspection records. It creates no stock movement. Receipt must match the exact final-stage lot, parent/item IDs, quality-release and stock-authorization IDs; cumulative accepted/rejected receipts cannot exceed the authorization or actual output. InventoryProvider validates accepted posting totals again and refuses receipt dates preceding final managerial authorization. Store's checkbox is acknowledgement only; it cannot bypass these guards. Unmapped products retain prepared receipts until exact variant/unit mapping. Historical positive transfers remain untouched, but **new transfers on legacy cards also require an explicit QC lot/review/final authorization**.

Held or failed batches cannot be posted from the production receipt path or dispatched from an existing matching production batch. Creating a new adverse inspection or NC puts the subject on hold even if it was previously released. The existing explicit reservation-based dispatch mechanism remains otherwise unchanged; the earlier no-mandatory-reservation phase is still pending. Manual unlinked reference Stock IN remains a separate Admin-only legacy/import operation, not proof of production quality release; ordinary Store staff must use authorized Job Card receipts. An active product QC hold also blocks unbatched manual IN because its source cannot prove a different safe batch. Attempts to supply Job Card/item references through the manual path are blocked. This conservative import exception is a proposed frontend policy requiring client confirmation; ordinary manufactured receipts have no exception. Backend must distinguish authorized opening/import receipts from manufactured receipts.

## Non-conformances, reports and known limits

NCs retain source inspection, source subject/batch through that inspection, description, severity, department, assignee ID, immediate action, correction, due date, verification, status and immutable activity entries. Optional affected-quantity/unit fields are prepared in the type but are not exposed as editable fields in this phase. Open → Assigned → In Progress → Awaiting Verification → Closed; failed verification can return to In Progress. Closed findings are immutable. A verifier cannot be the assigned correction owner. Separate structured corrective-action entities/evidence attachments are a backend proposal; frontend actions are recorded on the NC with an append-only event history.

Reports cover raw acceptance, product/sample results, Job Card history, machine compliance, cleaning verification, personnel safety, NC register and monthly/full summary. Daily, rolling seven-day, month-to-date and custom ranges are supported. Search accepts recorded product/Job Card/machine/supplier references; authoritative supplier data is unavailable. Excel export uses native SpreadsheetML `.xml` with explicit string/numeric cells, including measurements/specifications/tolerances; it is an Excel-readable workbook, **not `.xlsx`**. PDF export uses the browser's Print / Save as PDF dialog; no PDF service or generated PDF file is claimed. Exports follow the current filters. Source-row IDs and template revision remain available in export. Dashboard counts derive from actual QC records, pending raw IN receipts and configured machines; zero/empty states replace independent demo metrics. No inspections are seeded. Missing/overdue machine checks use a proposed seven-day frequency convention; unspecified cleaning schedules cannot imply a compliance percentage.

Frontend limitations: all QC state, templates, machine additions, lots, approvals/releases/NC history reset on refresh. Source evidence is missing. Real user assignments, supplier/batch inward masters, production runs, precision/rounding policy, attachment storage, signature identity, retention, notification schedules and audit persistence are not implemented. Conditional/raw partial-use disposition, failed-lot destruction/return/recycling, exceptions/concessions and recalls require authoritative workflows; failing lots cannot be released by an implicit exception here. No API calls are made to proposed QC endpoints.

## Proposed Django app boundaries

Dedicated `quality` app: templates/versions/items, inspections/samples/responses, reviews, NCs/corrective actions, release decisions, attachments and quality audit events.

- `production`: JobCard/JobCardItem, ProductionRun, routing checkpoints, stage records and actual outputs. Supplies exact source identity/output/version; enforces stage progression together with quality holds.
- `inventory`: RawMaterialReceipt/MaterialBatch, FinishedGoodsBatch, quantity/batch balances, quality availability projections, stock IN/OUT and reversals. Owns the inventory ledger and atomic transaction posting. A quality release is an authorization, not a stock transaction.
- `masters`: existing User/Role/Supplier/Material/Product/ProductModel/Machine/Department/Area references; no duplicate QC master records. Authoritative mappings must replace seed IDs while retaining source identity.
- `accounts`: existing estimate/invoice/costing ownership. QC records never copy confidential margins or create accounting entries.
- `reports`: filtered, permission-scoped projections and Excel/PDF outputs; opening/closing stock continues to use inventory history.
- `recycling`: separately authorized disposition/recycling transfers linked to NC/batch; rejected quantity alone must not silently post waste or raw-stock movements.

## Proposed model contract (not implemented schema)

Use UUID primary keys for new server entities. Existing source IDs must resolve to authoritative source foreign keys or a unique explicit legacy-ID mapping, never names. Common mutable-record audit fields: created_at/by, updated_at/by, integer version; immutable actions additionally have action timestamp, actor FK, request/idempotency ID and source-version snapshot. Use fixed-precision decimal quantities with required unit FK/code; specify decimal precision/rounding before implementation. Foreign-key deletion policy must preserve audit/source history; submitted records and referenced template versions must not be hard-deleted.

### QCInspectionTemplate

PK UUID; required name, category enum raw/production/machine/cleaning/safety, active flag; current_version FK to QCInspectionTemplateVersion; optional verified document code and source attachment references. Unique stable template key (document code is not assumed globally unique when unreadable). Lifecycle create → append version → activate/deactivate; deactivate prevents new ordinary use without deleting versions. Admin writes; scoped QC users read. Common audit fields/version.

### QCInspectionTemplateVersion

PK UUID; template FK, positive revision, effective date, department FK, frequency/configuration, applicable machine type/material/product criteria, approval policy, source provenance and immutable content snapshot. Unique (template, revision). Effective date must be valid; approval policies cannot grant inspector stock rights. Draft configuration becomes immutable when activated/referenced. Admin publishes versions; all permitted readers can resolve historical versions. Created_at/by and publication audit.

### QCInspectionItem

PK UUID; template_version FK; stable item key, sequence, label, response_type enum, acceptable response/polarity, required flag, remarks rule, NA permission, measurement specification/unit configuration. Unique (template_version, item_key) and sequence within version. Choice acceptance must belong to its response options; numeric target and nonnegative tolerances are distinct fields/configuration; no Yes-count inference. Immutable with its template version; Admin authors, QC records responses. Created_at/by.

### QCInspection

PK UUID; template_version FK and exact JSON content snapshot; category; inspection date/time/department; inspector FK, assigned_to FK; source FKs with category validation: raw_receipt/material_batch/supplier, or job_card_item/production_run/production_stage/product_model/finished_batch, or machine, or area. Required subject must resolve to one applicable source group and belong to the selected template/model revision. Parent Job Card is derived from item and checked against supplied references. Preserve physical receipt quantity/output version/unit. Required status enum Draft/Submitted/Passed/Failed/Reinspection Required/Conditionally Accepted/Approved-Released, derived result, comments, sample count; previous_inspection FK for reinspection. Unique request ID; source may have several attributable inspections, so no unique product/name constraint. Sample count 1–8 for samples, one for non-sample records. Draft edits → submission freeze → independent review → release references; corrections create linked records. QC Inspector writes assigned drafts/submits; QC Supervisor/Admin reviews; production/store have source-scoped read. Common audits, submitted_at/by and immutable post-submit snapshot.

### QCInspectionSample

PK UUID; inspection FK, sample number 1–8, optional sample label/location. Unique (inspection, number). Numeric sample counts must fit the template/inspection. Mutable only in assigned draft; frozen on submission. QC Inspector records; reviewer reads. Common audit fields before freeze.

### QCInspectionResponse

PK UUID; inspection/sample/item FKs; response value/NA flag; separate decimal actual, target, lower_tolerance, upper_tolerance and measurement unit; finding remarks/observations. Unique (sample, inspection_item). Item must belong to inspection's frozen version; required checks cannot be omitted; NA requires permission/reason; numeric values finite and unit-compatible, tolerances nonnegative; failed/required findings require remarks. Status follows inspection, not an independent approval flag. Assigned draft editing only; freeze with inspection; no retrospective answer rewriting. Created/updated audit and submission snapshot.

### QCApproval

PK UUID; inspection FK; actor FK; decision enum Passed/Failed/Reinspection Required/Conditionally Accepted; timestamp, required remarks and inspected-version/result snapshot. Unique approval action request ID. A Passed decision cannot contradict derived failing checks; conditional raw acceptance remains held unless explicit concession rules are separately approved. Actor must be QC Supervisor/Admin with source scope and different from submitter. Append-only; a changed decision is a separate authorized action/reinspection, not overwrite. No inventory mutation.

### QCNonConformance

PK UUID; source_inspection FK and optional response FK; source category/subject/batch references; reference number; description, severity enum Minor/Major/Critical; optional affected_quantity with mandatory matching unit; department, assignee FK, immediate action, due date, status enum Open/Assigned/In Progress/Awaiting Verification/Closed. Unique server reference and create request ID. Source response must belong to inspection; quantities cannot exceed known subject without explicit rationale. Retain original finding and chronology. QC staff report; QC Supervisor/Admin assign/verify/close; closed records immutable; reopening needs separate attributable server policy. Common audit/version and closed_at/by.

### QCCorrectiveAction

PK UUID; NC FK, assigned person/department FKs; immediate/corrective action, cause/plan, due date, evidence attachments, progress status, verifier FK/date/outcome. Unique action request ID; multiple actions per NC permitted. Owner cannot verify own closure; all required actions must be verified before NC closes. Open → assigned → performed → awaiting independent verification → verified/rework. QC Supervisor/Admin assign/close; permitted assigned staff update progress (frontend currently reuses manager-only NC action controls). Common audits plus completion/verification snapshots.

### QCRelease

PK UUID; inspection FK, quality_approval FK, source batch/receipt FKs; purpose enum quality/finished_stock; prior_quality_release FK for finished_stock; accepted/rejected quantity/unit when applicable; actor FK, timestamp, reason and source versions. Unique (inspection, purpose), globally unique request/idempotency key plus canonical payload hash. Quality release requires independent passing review and no unresolved source NC/holds. Finished-stock authorization requires quality release, completed exact source run/stage, managerial role and quantities bounded by actual inspected output. No duplicate allocations across multiple authorizations of the same physical lot; server must lock and reconcile batch-level cumulative quantities, not just per-inspection totals. Records are append-only; later adverse inspection/disposition creates a hold/withdrawal history rather than deleting release. QC Supervisor/Admin quality-release permission; separately mapped Supervisor/Production Manager/Admin final authorization. Neither action posts stock.

### QCAttachment

PK UUID; explicit owner FK (template version/inspection/NC/action), storage key, content type/size/hash, source description, uploader/time and access policy. Unique storage key; validate allowed size/type, scan untrusted content, preserve submitted evidence; avoid diagnoses/unnecessary personal medical data. Permission follows parent record; audit upload/view/remove policy. Frontend upload/storage is not implemented; photo references remain outstanding.

### Quality audit events

Append-only server event UUID; related inspection/NC/release and source item IDs, actor, department, event type, timestamp, description and related transaction/request ID. Unique action-event request tuple prevents retry duplication. Never trust a client-supplied actor or action time as the sole audit source. May use the existing shared audit subsystem rather than a duplicate QCEvent model. Frontend event arrays demonstrate the required chronology.

## Proposed DRF API contracts (no existing endpoints)

All paths below are future `/api/qc/` contracts. Use the existing authentication service; do not add QC login. Server derives actor, permissions and scope. UUID examples are illustrative, not real database records. Return decimals as strings with explicit units. List endpoints use page/page_size (default 25, maximum 100) and `{count,next,previous,results}`. Filters: from/to dates, department_id, inspector_id, assigned_to_id, category, status, template_id/revision, receipt_id, supplier_id, product_id, job_card_id, job_card_item_id, production_run_id, batch_id, machine_id, area_id and ordering; validate ranges and scope every row and aggregate. Inspector visibility is assigned/owned/relevant history; QC Supervisor/Admin see authorized QC scope; Store sees material/FG decisions and Production Manager sees job-item decisions. The current frontend has broader read visibility within QC roles; backend must enforce the agreed scopes.

- `GET /api/qc/dashboard/`: permission-scoped due/pending/failed/NC/hold counts, source queues, assigned inspections, machine/cleaning schedules and recent records; use real source data and units. No fabricated counts.
- `GET /api/qc/templates/`: latest active templates by default; optional include_versions/template_id/revision; historical inspection versions remain retrievable. Admin-only proposed POST template and POST template-version actions publish revisions, never mutate referenced content.
- `GET /api/qc/inspections/`: paginated inspection summaries and source filters.
- `POST /api/qc/inspections/`: create/schedule assigned draft; validate current active template and exact receipt or production-run/item/stage/batch relationships. Return 201 with inspection UUID/version and frozen template snapshot.
- `GET /api/qc/inspections/{id}/`: exact template snapshot, samples/responses, immutable approvals/releases, linked correction/reinspection history, source quality state and allowable actions.
- `PATCH /api/qc/inspections/{id}/`: assigned draft-only answers/metadata; requires current version/If-Match. Never accept status/actor/release mutation through generic PATCH. Return 200/new version or 409 if stale/frozen.
- `POST /api/qc/inspections/{id}/submit/`: validate all required responses/samples/measurements/source versions, freeze answers, derive result, append audit and enforce hold; no stock mutation.
- `POST /api/qc/inspections/{id}/approve/`: independent QC review of passing result, with remarks; create QCApproval only. Does not imply stock receipt or final managerial authorization.
- `POST /api/qc/inspections/{id}/reject/`: independent Failed or conditional raw hold decision with required reason; enforce affected batch hold without silently subtracting physical quantity.
- `POST /api/qc/inspections/{id}/reinspect/`: create a new linked draft using the preserved version or an explicitly authorized new version; retain original results/approvals and enforce source identity. Return 201/new record.
- `GET /api/qc/non-conformances/`, `POST /api/qc/non-conformances/`: paginated source-scoped register/create findings; idempotent create with validated affected quantities.
- Proposed `PATCH /api/qc/non-conformances/{id}/` and action/verify/close endpoints: explicit authorized lifecycle transitions with concurrency checks and original failure retained. Only draft/action-progress fields are writable; closure needs independent evidence verification.
- `POST /api/qc/releases/`: purpose quality or finished_stock; separate roles, immutable QCRelease and source/quantity validations. Returns 201/reference (or existing successful response on exact retry); never posts inventory.
- `GET /api/qc/reports/`: permission-scoped report type raw_acceptance/product_samples/job_card_history/machine_compliance/cleaning/safety/non_conformance/monthly_summary; common filters plus period/date range and output json/xlsx/pdf. Report exports are proposed server outputs; frontend exports are XML/browser printing only.
- Proposed source-policy/master-assignment/attachment operations must reuse authoritative masters and storage services; the exact endpoints need backend design approval. No fake frontend network calls are issued for any of these paths.

### Illustrative requests and responses

Create draft, using a real source relationship resolved by the server:

```json
{
  "request_id": "a2bc4000-0000-4000-8000-000000000001",
  "template_version_id": "a2bc4000-0000-4000-8000-000000000002",
  "category": "production",
  "job_card_item_id": "a2bc4000-0000-4000-8000-000000000003",
  "production_run_id": "a2bc4000-0000-4000-8000-000000000004",
  "production_stage_id": "a2bc4000-0000-4000-8000-000000000005",
  "batch_id": "a2bc4000-0000-4000-8000-000000000006",
  "inspection_date": "2026-10-13",
  "inspection_time": "09:30:00",
  "sample_count": 2
}
```

Response 201 includes `id`, `number`, `version: 1`, `status: Draft`, `template_version_id`, `template_snapshot`, resolved `source`, `samples`, `responses`, `approvals`, `releases` and audit timestamps. Draft measurement PATCH uses the version/If-Match and exact item/sample IDs:

```json
{
  "version": 1,
  "responses": [{
    "sample_number": 1,
    "inspection_item_id": "a2bc4000-0000-4000-8000-000000000007",
    "actual": "50.00", "target": "50.00",
    "lower_tolerance": "2.00", "upper_tolerance": "2.00",
    "unit": "micron", "remarks": "Within approved specification"
  }]
}
```

Submit/review actions carry a unique request ID, current record version and required review remarks; the server ignores supplied actor fields. Separate final release example:

```json
{
  "request_id": "a2bc4000-0000-4000-8000-000000000008",
  "inspection_id": "a2bc4000-0000-4000-8000-000000000009",
  "purpose": "finished_stock",
  "prior_quality_release_id": "a2bc4000-0000-4000-8000-000000000010",
  "accepted_quantity": "90.000", "rejected_quantity": "10.000", "unit": "kg",
  "source_version": 3
}
```

Response contains `release_id`, purpose/source references, actor/timestamp and quantities; `inventory_transaction_id` remains absent until inventory independently confirms receipt. Inventory's future receipt operation must accept final release/request references, validate remaining authorization and atomically create its transaction. Do not reuse the QC release endpoint as a stock endpoint.

Validation error 400 example: `{"code":"required_measurement","errors":{"responses.0.actual":["Actual measurement is required."]}}`. Missing authentication 401; unauthorized role/scope 403; missing/out-of-scope record 404 according to disclosure policy; stale version, conflicting idempotency payload or already frozen/invalid transition 409 with current version/allowed actions. Failing checks produce a recorded Fail, not a successful Passed decision. No silent fallback success after server failure.

## Backend transaction boundaries and retries

1. Raw receipt commits physical quantity/batch and pending-QC availability in inventory together. Inspection submission/review references that immutable receipt/batch. Receipt does not imply acceptance; rejection creates a hold/disposition without an OUT or supplier return.
2. Submission atomically validates template/source versions, required answers, samples/units, freezes content, derives result and writes the source hold/audit. Previous required stage completion remains a production constraint.
3. Review atomically locks the inspection and relevant source-quality state; validates independent reviewer, unchanged snapshot and derived result; appends QCApproval/audit. Failed checks cannot be silently approved. Scope is the exact item/run/batch, never the entire parent card by name.
4. Quality release locks inspection, subject/batch, open NCs and current holds; verifies latest applicable requirements and successful correction chain; appends release and updates availability projection. Does not change quantity. A new adverse finding/inspection atomically reinstates hold even after prior release.
5. Final finished-stock authorization locks the exact completed production run/stage/batch, quality-release policy and cumulative authorized quantities. Validate managerial mapping, mandatory routing QC, units, accepted/rejected limits and duplicate lot reservations. Append authorization only; no inventory write yet.
6. Inventory receipt locks authorization/batch and posting balance, rechecks quality hold and managerial authority, checks unposted accepted quantity, and atomically writes Stock IN, accepted/rejected accounting, source references and audit/outbox. Unique posting request prevents replay; retries cannot duplicate stock. If quality state changes concurrently, receipt fails rather than posting a held batch. Reversal/disposition is separately authorized and append-only.
7. Confirmed dispatch alone creates Stock OUT. Inventory locks batch/order-line remaining demand and quality state; validates physical/released availability, units and outstanding customer quantity, writes OUT/dispatch/audit atomically. Draft or inspected/released forms do not deduct stock. Mandatory advance reservation is not a client requirement; the current frontend legacy allocation step awaits its separate implementation phase.
8. Corrective verification/NC closure locks NC/actions and validates independent verification. Closure does not automatically rewrite failed inspections or release the subject; retain reinspection and approval history. Recycling/returns/destruction require separate inventory-owned transactions linked to disposition, never inferred from rejection.

For every write, store a unique request ID and payload fingerprint. Exact successful retry returns the original record/transaction; changed payload for the same key returns 409. Reject stale record/source versions before writes. Roll back related database changes on failure. Publish cross-app notifications through a transactional outbox/after-commit mechanism; retry notifications separately from ledger writes. Client reloads authoritative state after success/conflict and displays errors after failure; in-memory fallback must never claim durable acceptance or stock posting.

## Open client decisions and verification

Supply all eight photographs to verify printed wording, codes, revision/date metadata and source image references. Confirm final Supervisor/Manager role mapping; permitted concessions/conditional raw use and partial acceptance; sampling frequencies/specifications/tolerances; mandatory model/stage checkpoints; machine/area master identity and schedules; assigned inspector scope; independent verification rules; actual production-run/lot identity; supplier receipt/batch master fields; signatures/evidence retention; NC severity/escalation and rejected-material disposition. Reuse confirmed unit-conversion, recycling/waste and USD/UGX costing rules; QC does not revise them.

Validation commands: `node ./node_modules/typescript/bin/tsc --noEmit`, `npm run build`, `node scripts/check-quality.mjs`, and all five existing `check-sales-fulfillment`, `check-job-cards`, `check-custom-costing`, `check-finished-goods`, `check-inventory-workflows` scripts, plus `git diff --check`. QC domain regressions cover six template structures/eight sample validation, negative polarity, explicit tolerances/NA, snapshots, immutable submission, roles/self-review, exact holds, checkpoint coverage, separate/idempotent releases, receipt bounds, unchanged inventory, linked reinspection, raw pending/release, equipment checks, NC transitions and XML escaping/exports. Existing suites passed. Browser smoke verification was attempted but localhost timed out in the in-app browser and Chrome was unavailable. UI interaction, mobile layout and browser PDF printing must still be verified on an accessible browser; helper/build checks are not end-to-end evidence. Vite retains its bundle-size warning. No automatic Git commit.

## QC implementation file inventory

- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/BACKEND_TODO.md`
- `docs/BUSINESS_RULES.md`
- `docs/CHANGELOG.md`
- `docs/DATA_MODELS.md`
- `docs/DEVELOPMENT_STATUS.md`
- `docs/custom-costing-routing.md`
- `docs/quality.md`
- `docs/sales-fulfillment.md`
- `scripts/check-quality.mjs`
- `src/App.tsx`
- `src/components/layout/AppShell.tsx`
- `src/context/AuthContext.tsx`
- `src/context/InventoryContext.tsx`
- `src/context/JobCardsContext.tsx`
- `src/context/ModelsContext.tsx`
- `src/context/QualityContext.tsx`
- `src/index.css`
- `src/lib/finishedGoodsData.ts`
- `src/lib/quality.ts`
- `src/lib/qualityIntegration.ts`
- `src/lib/qualityReports.ts`
- `src/lib/qualityTemplates.ts`
- `src/pages/JobCards/JobCardDetail.tsx`
- `src/pages/JobCards/JobCardForms.tsx`
- `src/pages/JobCards/RoutingFields.tsx`
- `src/pages/Login.tsx`
- `src/pages/Quality/InspectionDetail.tsx`
- `src/pages/Quality/InspectionForm.tsx`
- `src/pages/Quality/NewInspection.tsx`
- `src/pages/Quality/QualityPage.tsx`
- `src/pages/Quality/QualityTemplates.tsx`
- `src/pages/RawMaterials/RawMaterialPage.tsx`
- `src/pages/Recycling/RecyclingPage.tsx`
- `src/pages/Stocks/stocks.tsx`
- `src/types/index.ts`

Changes are scoped to QC, existing role/navigation/source integration, the focused regression script and relevant documentation. Dependencies, backend code/endpoints, schemas and existing sample/reference ledgers are unchanged.

## Daily inspections / scheduling enhancement — 15 October 2026

Template frequency now includes daily/per-shift/monthly/on-demand while retaining per-receipt/per-batch/weekly/per-activity. Existing weekly templates remain weekly. KSEC is an inactive configurable placeholder, not an invented acronym/checklist. QC Supervisor/Admin configures exact-subject schedules from an existing inspection/latest active template; explicit date generation deduplicates schedule/date/shift, supports pause/resume and assigns a stable QC user ID. Raw/production physical lots cannot recur as daily subjects. Daily dashboard counts and existing form/review/NC/release/hold behavior reuse QualityContext. Submission/review/generation never posts stock. Full field/recurrence/calendar/assignment/backend limits and transactions are in [the integrated report](sales-fulfillment.md#qc-daily-inspections-and-configurable-schedules); no background scheduler/service exists.
