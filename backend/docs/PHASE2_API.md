# Phase 2 implemented API contract

20 October 2026. This document describes implemented behavior. Older frontend planning
blueprints remain proposals. Base `/api/v1/`; bearer JWT; snake_case; trailing slash.

## Resources

The following collections support GET list, POST create, GET `{uuid}/` and PATCH
`{uuid}/`: customers, prospects, suppliers, departments, units, products,
finished-goods, raw-materials, consumables, machines, areas and models.
PUT and DELETE are not authorized. Deactivate with PATCH `is_active=false`.
IDs, versions, timestamps and actor references are server-managed and rejected on input.
Names are required but deliberately not unique. Nonblank codes are case-insensitively
unique per resource. Nonblank `(source_system,source_id)` pairs are unique per resource
and immutable; supply both or neither. No auto numbering or source identifiers invented.

All writes require `Idempotency-Key` (1–200 printable nonspace ASCII). PATCH and detail
commands also require `If-Match: "1"`. Same actor/action/key and payload replay the stored
result, including the original version. Different payload returns 409. A new command
against a stale version returns 412; missing precondition returns 428. GET detail and
mutation responses provide ETag; create provides Location. Refresh with GET after replay
when a current version is needed. Errors use the Phase 1 envelope.

List pagination: page, page_size (25 default, 100 maximum). Search across name/code/source_id;
ordering allowlist name, code, created_at, updated_at; default -created_at,id. Exact filters
is_active, source_system, and category/unit/product/department/area/family/linked_customer
where those fields exist. IDs in relationship fields are UUIDs, units are governed FKs.
No balance fields are accepted or synthesized. Inactive masters remain readable and
editable by authorized users; new references to inactive masters are rejected. An existing
unchanged inactive reference may be retained during metadata correction. Master unit
identity cannot be changed; unit code/dimension cannot be changed after creation.

## Explicit commands

POST `prospects/{id}/promote/`: send exactly one of
`{"existing_customer_id":"uuid"}` or `{"create_customer":true}`. The first links an
explicit active customer; the second copies party fields into a new customer. Names
never resolve identities. The locked prospect accepts one linkage; use the original
key to retry. Promotion stores actor/time, increments prospect version and audits both
creation (if applicable) and promotion. Customer code/source identity are not copied.

GET/POST `models/{id}/revisions/`: GET returns paginated sealed history, newest number
first. POST locks model version, assigns next number, validates and creates all nested
lines, seals revision and advances model version. Response includes `model_version`;
its ETag refers to the returned immutable revision, not the model. Fetch model for its
current ETag before another revision. Revision creation is a complete specification,
not a PATCH or an automatic clone of prior data.

GET `model-revisions/` and `model-revisions/{id}/`: sealed revisions only. Filter model,
number; search name/description/specifications; order created_at/number. No edit/delete.

Revision input requires name, default_unit and recipe_mode (`quantities`/`percentages`).
Optional description/specifications/dimensions, batch_unit/batch_quantity,
waste_percent/overheads/currency/markup_percent/tax_percent, bill_of_materials,
legacy_stages and arrays recipe/processes/routing. Decimals are strings (20 digits,
6 decimals); omitted unknown cost defaults stay null. These are specification defaults,
not calculated costs, verified rates or approvals. USD/UGX reflect the current model
frontend contract; no tax or markup defaults are seeded.

Recipe lines: material, unit, cost_group; optional source_id, quantity, percentage,
currency, price, price_unit, exchange_rate. Exact active material unit required;
quantities must be positive in quantity mode; positive percentages total exactly 100
in percentage mode with positive batch quantity and exact batch unit. No inferred
conversion. Materials distinct per revision. Prices nonnegative, FX positive when given.

Route lines: name, sequence, kind, department, input_unit/output_unit/waste_unit;
optional source_id, required, machine, expected_input/output, planned_waste_percent,
remarks, instructions, legacy_stage, checkpoint_template_ids. Sequences are unique,
positive and need not be contiguous. Route order is configurable; empty specification
routes are permitted and convey no production authority. Kinds include frontend
production/stock plus quality/transfer/other. Machine must belong to department.
Checkpoint IDs are provisional source strings, not validated QC release/template FKs.
No universal route or machine settings are seeded.

Process lines: name, basis (`per kg`, `per piece`, `per batch`, `fixed`), unit;
optional source_id, rate, quantity, remarks and source_stage_id (a source_id in this
new revision's route). Foreign revision stage IDs are rejected. Production runtime
fields, run quantities, handovers, operators and QC decisions are not specifications.

## Import staging and review

GET/POST `imports/`, GET `imports/{id}/`, GET `imports/{id}/rows/` (paginated source rows),
POST `imports/{id}/review/`, POST `imports/{id}/approve/`. List filters status, target,
source_system, source_kind; search filename/source_system; order created_at/updated_at/filename.
Batch read includes mapping, proposed values, errors, candidate IDs and recorded decisions.

1. POST multipart file, target (one master collection name), source_system,
   source_kind (`client` or `demo`), source_attestation. Source bytes are SHA-256 hashed;
   identical content cannot be staged twice, even under another filename/target. Retry
   the original command or use existing batch. Data rows retain sheet and actual row.
2. Accept UTF-8 CSV or data-only XLSX, at most 5 MiB, 2000 rows, 100 columns;
   expanded XLSX <=100 MiB/300 entries/100000 cells. Headers must be unique/nonblank.
   XLS, macros, external links and formula cells are rejected. Export values-only data
   explicitly and preserve the original externally. Dates must be supplied as ISO strings;
   Excel serial dates are not guessed. Sheet headings/merged register layouts must be
   normalized explicitly; this is not a workbook-specific extraction engine.
3. Review payload: `mapping` maps API fields to exact column headers, and `decisions`
   maps ImportRow UUIDs to `{action:"create"|"update"|"skip"}`. source_id must be mapped.
   Updates additionally require target_id UUID and current integer expected_version.
   Duplicates require acknowledge_duplicates=true. Candidates use exact case-insensitive
   names/codes and source pairs, including within-batch duplicates; no fuzzy merge.
   Unique source IDs/codes still cannot be duplicated even after acknowledgment.
4. Foreign references accept UUID or exact case-insensitive governed code during import;
   preview shows resolved UUIDs. Units do not use inferred aliases/conversions. Validate
   required columns, decimals, categories, active references and current target versions.
   Unmapped opening/closing/date cells remain raw evidence, including blanks; no stock
   quantity is created. Invalid/undecided rows block approval unless explicitly skipped.
5. Approval has an empty JSON body and batch version. It uses the persisted reviewed
   mapping/decisions, locks batch, revalidates current targets and references, and applies
   all selected master changes plus per-master audit and batch audit in one transaction.
   A changed target/version or invalid row rejects everything. Demo source is blocked.
   At least one master change is required. Exact retries replay once; competing keys
   serialize and stale versions fail. Approval never creates opening balances/movements.

Raw source rows, digest, provenance and attestation are database-protected from edits;
rows cannot be appended after review. Mapping can be reviewed again before application,
with a new version/audit. Applied batches are immutable. The database retains parsed
source values and a content hash, not the uploaded binary. Keep originals in controlled
client storage. Attestation is an authorized operator assertion, not independent proof
that uploaded data is authentic. No repository seed/reference array is imported.

## Permission matrix

No role grants or approval limits are seeded. All catalog data is explicitly a single
shared scope; department ownership/tenant boundaries are not inferred. Provision only
authorized users until the client defines a narrower deployment scope.

- Ordinary list/detail: `<app>.view_<model>`.
- Ordinary create: `<app>.add_<model>`.
- Ordinary PATCH, including activation/deactivation: `<app>.change_<model>`.
- Master resources use app `masters`: customer, prospect, supplier, department, unit,
  product, productvariant, material, consumable, machine, area.
- models uses `specifications` and productmodel.
- Read revisions: specifications.view_productmodelrevision.
- Create revision: specifications.add_productmodelrevision.
- Promotion: masters.promote_prospect plus masters.add_customer for creation or
  masters.view_customer for explicit linkage. Additional grants rechecked on retry.
- Stage: imports.add_importbatch. Read batch/rows: imports.view_importbatch.
- Review: imports.review_importbatch plus target masters.view_<model>.
- Apply: imports.approve_importbatch plus target masters.view_<model> and add/change
  for every selected decision, including replay. No independent reviewer rule is
  invented; granting approval capability is an explicit operational authority decision.

Active server identity and capabilities are checked in views and command authorization.
Lists expose only the shared catalog behind the resource read capability. Significant
changes, revisions, source staging/review/application and promotion are audited with
actual actor, request ID, versions and safe changed-field names, never raw source PII.


## Phase 2.1 import and validation corrections

Batch responses add canonical_review (latest immutable review UUID) and applied_plan
(null until successful new approval). GET imports/{id}/reviews/ requires
imports.view_importbatch and paginates {id,plan,plan_hash,reviewed_by,created_at}.
Review creates a new append-only history record; plan.schema_version=1, source_digest,
source_system, target, mapping and rows. Each row retains decisions, canonical proposed
fields, complete duplicate candidates, errors and references (field/model/id/version/
state_hash). Decimal fields remain strings. State hashes do not expose raw User secret
fields. UUID resolution precedes optional code lookup; User has no code lookup.

Approval requires existing approval/view/target write capabilities, current batch
If-Match and empty body. It checks the saved hash, compares the entire canonical plan
against current locked references/targets/candidates, and returns 409 stale_review
when any differ. A fresh review and new If-Match/key are then required. Initial invalid
review rows remain 400. Successful approval applies reviewed proposed values exactly;
applied_plan contains {review_id,plan_hash,plan,results:[{row_id,target_id,version}]}.
Retries return the retained success once; transaction failure retains no partial masters,
row results, applied plan, command result or audit. Applied batches and reviews cannot
be updated/deleted. Legacy reviewed batches require review again; already applied
legacy batches stay unchanged without fabricated canonical evidence. No inventory effect.

Process write fields are explicit: source_id/name/basis/rate/quantity/unit/remarks,
optional source_stage_id, and stage only when null. Null means no external stage and
cannot produce duplicate constructor arguments. Nonnull stage UUIDs are not an input
linkage mechanism. Response stage is the actual immutable route UUID or null.

Governed role administration is implemented under roles, with empty shell creation,
versioned metadata and independently approved capability revisions. See
[employee and role contracts](EMPLOYEE_ADMIN.md#phase-21-governed-role-capabilities).
[Frontend correction plan](PHASE21_FRONTEND_CONTRACT_PLAN.md) prepares the required
integration changes; no compatibility aliases or weaker validation were introduced.
