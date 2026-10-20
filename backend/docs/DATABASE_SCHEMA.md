# Phase 2 database schema

20 October 2026. New apps: masters, specifications, imports. Existing accounts/core
models and all Phase 1 migrations are preserved. PostgreSQL only; no data seed imports.

## Shared master identity

Master is abstract: UUID id, integer version >=1, server UTC timestamps, name, optional
code, is_active, source_system/source_id and protected created_by/updated_by account
references. Names indexed for lookup/sorting, active flags indexed, FKs indexed by
Django; nonblank case-insensitive code and exact source pair have unique indexes.
Source pair must be complete. No name uniqueness/automatic merge.

Customer and Prospect use contacts, address/delivery address, email/phone/TIN and
optional B2B/B2C type. Prospect has a protected customer linkage, promotion actor and
time; service serializes one-way linkage. Several prospects may intentionally link
the same customer. Supplier has descriptive material_supplied and phone, no invented
supplier codes or material relationships. Department retains manager-name snapshot
separately from optional protected account manager FK.

Unit has client-entered code/name and dimension mass/volume/count/package/length/other.
There are no seeded aliases/conversion ratios. Product is a generic master with category
and unit FK. ProductVariant is an exact finished-good identity with protected Product
and Unit FKs, carrier-bags/flat-bags/packing category, subgroup, customer text,
item_details/size/brand/packing_size, positive nullable pieces, source sheet/row/customer,
inherited flag, original unit and data notes. Customer text is never a resolved Customer
FK. Repeated physical descriptions can represent distinct source identities.

Material has category virgin/recycled/ink, descriptive family, protected Unit and nullable
nonnegative min_level. Consumable has imported/local category, protected Unit and nullable
nonnegative min_level. Machine has department, optional area, client classification type;
Area has optional department and description. Area/department consistency validated.
No equipment settings, stock columns or movements exist. No source record is loaded.

## Revision schema

ProductModel inherits Master; category remains descriptive. ProductModelRevision has
protected model/unit/creator FKs, model-local number (unique model+number, positive),
name, descriptive specifications/dimensions, recipe mode, nullable batch/default decimal
values, currency, legacy bill/stage text, reference snapshot and seal. Parent locking
serializes numbering and increments parent version. Immutable reference snapshots retain
labels/codes alongside protected IDs so later master renames cannot rewrite specifications.

RecipeLine has protected revision/material/unit/price_unit FKs; distinct material per
revision; nullable quantity/percentage/price/FX, currency and material/ink group.
ModelRouteStage has protected revision/department/machine/unit FKs, unique positive
revision-local sequence, source stage ID, arbitrary name, required/kind, optional planned
quantities/waste, instructions/legacy label/checkpoint IDs. Nonblank source stage IDs
are unique within the revision. ProcessCostLine has protected revision/unit/stage FKs,
name/basis/nullable rate+quantity/remarks. stage must be from the same newly-created route.

Specification decimals use NUMERIC(20,6), a technical storage precision, pending client
confirmation for future calculations. Database checks enforce nonnegative decimals and
0..100 percentage fields. No calculation, price policy or costing approval is implemented.
All saved revisions are sealed; no mutable revision CRUD. PostgreSQL triggers forbid
UPDATE/DELETE on sealed revision headers and INSERT/UPDATE/DELETE on their children;
line guards lock the header and prevent moving a line to another revision. Future
transaction FKs must PROTECT exact revision UUIDs. New revision is the correction path.

## Import schema and integrity

ImportBatch: UUID/version/timestamps, filename, globally unique content SHA-256,
source_system, source_kind, attestation, target, status, created_by, approved_by/time,
mapping and review JSON. Status/target indexed. ImportRow: UUID/version/timestamps,
protected batch, sheet, physical row_number, raw JSON text cells, nullable result UUID.
Unique batch+sheet+row. Result UUID is resolved using batch.target; it is provenance,
not an unvalidated generic domain FK. Successful application leaves per-master audit.

Batch/source evidence cannot be deleted via ordinary DML; source metadata immutable.
Source rows are immutable except one result UUID assignment during reviewed application.
Insert guard locks batch and only permits staged rows; applied batches immutable. Review
history is tracked by append-only audit/version, with latest detailed mapping retained on
batch. Previous full preview bodies are not historical snapshots; raw source is retained
and each review/apply is audited. Original binary is not retained; digest supports external
controlled-original verification. No import contains an opening-balance projection.

As with Phase 1 audit, database owner/superuser can bypass safeguards; production runtime
must not own tables or be able to disable triggers/TRUNCATE. Apply through migration owner;
restrict runtime to required DML. Schema and trigger changes are forward migrations only.


## Employee accounts extension

accounts/0001_initial is unchanged. Forward accounts/0002 adds User.is_master_admin
(default false), Employee (VersionedModel, one-to-one protected User, required active
Department, immutable case-insensitive employee_id, designation, optional protected self
reporting_manager, protected actor references), RoleAssignmentPolicy, RoleChangeRequest
and EmployeeResetRequest. User is the only stored name/email/active status. UUID profile
identity differs from human employee_id and authentication User UUID.

Role policy stores an explicitly selected independent-approval flag and exact role-permission
digest. Change requests store employee/role/add-or-remove/membership UUID/digest/required
independence/requester/reviewer/status/time. Requests persist after membership removal.
Reset requests store actor/completer/status/time and expected employee version, never a
password or reset token. Phase 1 Membership/Role behavior and initial migrations are retained.

accounts/0003 adds partial unique pending request constraints, positive reset precondition,
required applied/completed evidence and independent actor database checks. Self-reporting
is also database-rejected; longer reporting cycles are prevented under the shared admin
transaction lock. Full contracts and maintenance boundary: EMPLOYEE_ADMIN.md.


## Phase 2.1 forward additions

accounts.Role: version, updated_at, governed, approved_revision (PROTECT nullable FK).
accounts.RoleCapabilityRevision: UUID/version/timestamps, protected role/maker/reviewer,
permission_codes JSON, explicit assignment independence policy, expected Role version,
baseline JSON (raw capability digest, prior revision/policy and exact affected members),
status and applied_at. One pending proposal per role; applied requires a distinct
approver/time. PostgreSQL trigger forbids proposal-content changes/deletion and all
changes to terminal records. No grant or business-role seed migration.

imports.ImportReview: UUID, protected batch/reviewer, canonical JSON plan, SHA-256 hash,
created_at. PostgreSQL UPDATE/DELETE rejection makes review history append-only.
ImportBatch adds canonical_review PROTECT nullable FK and applied_plan nullable JSON.
Existing batch source/applied immutability and raw-row protection remain active.
Forward migrations: accounts 0004/0005 and imports 0005/0006. Existing migrations are
preserved. Legacy records remain null rather than fabricating review/applied evidence.
