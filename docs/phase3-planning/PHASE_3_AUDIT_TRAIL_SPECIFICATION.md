# Phase 3 common audit trail specification

Current scoped-history addition: `/api/v1/inventory/history/` now implements paginated configuration history with date/actor/action/entity/request/warehouse filters and safe frontend change comparisons. It requires inventory.view_inventory_audit plus entity-view capability and warehouse scope. Global Admin history excludes inventory events. The broader system-wide role/module/transaction/approval filter contract, exports and retention remain incomplete; no transaction/approval records are invented.

## Phase 3A implementation status — resumed request

20 October 2026: the configuration subset of this contract is now implemented, superseding the earlier no-implementation statement below for Phase 3A only. Warehouse create/metadata/activation; location create/metadata/hierarchy/activity; stock identity creation/retirement use atomic core commands/audit. Events retain actor UUID, server timestamp, reason, request, entity UUID, safe before/after/version, employee reference, capability used, role UUID/approved revision and immutable scope-evidence UUIDs. Immutable scope evidence retains requester/independent approver/policy/evidence references, but no scope writes/provisioning workflow is enabled and no scope approval events are fabricated.

Inventory 401/403 emits safe structured denial with actor UUID when verified, action, correlation and denied outcome; it is separate from business audit. Core formatter permits these explicit trusted fields. No request bodies, credentials or arbitrary exception details are logged. Existing audit summary sensitive-content/size guards remain; exceeding them fails closed and rolls back the configuration command.

Inventory migrations add DB identity, hierarchy, parent/unit, deletion and scope evidence guards. Existing audit UPDATE/DELETE protection unchanged. Runtime table-owner/DBA/TRUNCATE privilege separation remains an operational verification gap. Full system-wide historical diffs, generalized policy snapshots, stock approval/correction drill-down, exports and retention remain future work; this contract must not be read as completed merely because 3A now has audit integration.

Recorded 20 October 2026, Asia/Kolkata. U = user-directed requirement; S = supplied SOP constraint; I = inspected current implementation; A = proposed implementation; D = pending policy. This is a reviewable contract, **not an implemented audit expansion**. Phase 3A is stopped at the schema/scope gate; no new events, fields, endpoints or grants have been installed.

## Existing infrastructure and gaps

I — `backend/apps/core/models.py` supplies UUID AuditEvent, protected nullable actor FK, server timestamp, action/entity identity, request UUID, JSON summary, reason and source_version. `commands.execute_command` commits mutation, audit and successful idempotency result in one atomic transaction. Replays reauthorize and do not create a second domain transition. ORM guards and core migration 0002 reject audit UPDATE/DELETE in PostgreSQL. Existing admin audit list/detail requires technical administration plus explicit audit capability; it is not a general business audit portal.

I — Current master audit summaries generally contain changed field names and success, not full old/new values. Historical employee/role/capability snapshots are not universal. Existing audit filter fields are actor/action/entity_type/entity_id/request_id; requested dates, historical role, module, warehouse, transaction and approval status are not all supported. Request logging records correlation/status/method but does not provide the requested attributable denial history. Audit UUID/timestamp/actor protection alone is insufficient for U-J.

I/D — UPDATE/DELETE triggers do not block table-owner/DBA bypass or TRUNCATE. Restricted production runtime-role grants, log retention/access and recovery are not verified. This work does not certify tamper resistance against database owners or implement cryptographic external anchoring.

## Proposed event envelope

A — Extend the existing audit infrastructure through additive migrations and a versioned typed envelope, rather than create a second competing business audit store. Existing events keep honest historical summaries; do not fabricate missing old values or past role snapshots. Mark legacy detail unavailable.

Each new envelope must include:

- schema_version, server-generated event UUID and UTC recorded timestamp; separate business effective timestamp where applicable, with timezone evidence;
- authenticated actor UUID, employee UUID/immutable employee identifier where one exists, safe historical display snapshot; authorized automated processes use a registered service identity and initiating human/correlation when applicable, never arbitrary null actors;
- exact effective capabilities used, role UUIDs and approved policy revision/digest, object scope and authority source/effective interval at decision time; client role labels are never authority;
- stable module/action/entity type/entity UUID; before_version and after_version; safe allowlisted old/new field values, with omitted/redacted markers that do not imply null or deletion;
- reason/justification; source document UUID/revision/digest and controlled evidence references; request/correlation UUID and separate server event identity (a caller may supply a correlation UUID);
- related transaction, approval request, original transaction and correction/reversal UUIDs where applicable; initiator, recorder and approver identities remain distinct;
- approval/rejection/cancellation decision, actual decision timestamp, approver's independent authority snapshot and approved content digest;
- committed outcome, or a separate denied/failed security outcome; source system/service identity and command linkage without secrets.

A — Required-versus-not-applicable is action-specific. A warehouse metadata edit has no stock transaction or approver unless a reviewed policy requires approval; record explicit applicability rather than invent them. Approval events reference the exact immutable request revision. A rejection is a successful recorded decision, never a stock posting. Every material draft edit, submit, cancel, approve, reject, deactivate, post, reverse, correction and significant configuration publication gets its own event.

## Atomicity and historical authority

A — Inside existing command transaction: resolve active identity/capability and approved object scope; acquire governance/hierarchy/domain locks in the agreed order; read and snapshot prior values/version; validate preconditions/authority/independence; perform mutation; append immutable business evidence and allowlisted audit diff; persist command result; commit. Injected audit failure must roll back all mutations, approvals, projections and idempotency results. External notifications occur only after commit.

A — Role snapshots must bind to the same governed revision used for authorization. Serialize authority publication/revocation with transitions when required; reading mutable current roles after commit does not reconstruct historical authority. Employee rename/deactivation must preserve old actor snapshots and protected identity links. No-self-approval is by human User UUID, including multiple roles, superusers and Master Admins.

A — Opening correction captures initiating Admin separately from independent approver and Procurement recorder, original posted quantity, proposed quantity and exact difference, evidence digest and full historical feasibility result. The original opening/ledger entry remains unchanged. Approval does not itself post. Rejection remains visible. Subsequent corrections reference the preceding correction and original opening, avoiding ambiguous replacement quantities or double compensation. Backdating captures proposed effective time separately from actual submission/decision/posting times and affected historical balances; closed-period policy must exist first.

## Security failures and sensitive evidence

A — Authorization failures go to a dedicated structured security sink outside the rolled-back business transaction. Record server time/event UUID, verified actor when available, requested action, safe scope/target reference only when disclosure is allowed, correlation and denial reason code. Unauthenticated attempts have no invented employee. Do not emit a committed business event for a failed command. Rollback/internal failures get safe outcome codes without request bodies, SQL parameters or exception secrets.

A — Use per-action schemas for old/new values; prohibit passwords, password hashes, JWTs, signing keys, reset credentials, authorization headers, cookies and unnecessary personal data. Private attachments are referenced by opaque controlled IDs/digests, not public URLs. Attachment download checks current evidence capability and object scope. Do not expand `SAFE_SUMMARY_FIELDS` into unrestricted request-body logging. Existing reason/summary size and sensitive-content rules must be reviewed with typed validation rather than silently bypassed.

## Database and operational controls

A — Retain existing immutable audit rows. Add immutable evidence/decision guards with protected FKs and constraints; ordinary runtime role must not own tables/functions/schema, disable triggers, grant privileges, mutate/delete/truncate audit/evidence/ledger, or replace guard functions. Separate migration owner and runtime credentials; restrict schema CREATE and PUBLIC privileges appropriately. If a controlled insert function is selected, review SECURITY DEFINER ownership/search_path and grants. Domain services and database constraints complement rather than replace one another.

A/D — Test grants with a restricted nonowner runtime role and independent migration owner on disposable PostgreSQL. Explicitly test raw UPDATE/DELETE/TRUNCATE and trigger-disable denial, forged historical identity, invalid approval content and rollback. A superuser-based Django suite is not runtime-role evidence. Management/IT must approve retention, backup/restore, restricted audit export, log access and any external tamper-evident archive. DBA access remains a privileged boundary to document and monitor.

## Search and interface contract

A — Future read-only Audit History API/interface: pagination and bounded date range, actor/employee, historical role UUID, module, action, entity UUID, warehouse, transaction and approval decision filters; stable timestamp+UUID order. Expose safe change comparisons with explicit redactions and drill-down to exact source revision, approval/rejection and correction chain. No mutation/delete routes. Filters, result counts, related links, exports and attachments must all use approved object scope; seeing a transaction does not confer source/financial/employee evidence access.

A — Reuse existing authentication/error/pagination conventions. Publish typed API contracts before a real frontend; no mock success or reconstructed fictitious history. Existing Admin login is reused, but new audit-view/object/evidence capabilities must be explicitly governed, not seeded to every Admin. Database indexes on actual filter/link columns follow measured query plans; JSON-only unindexed scans are not an acceptance target.

## Coverage and acceptance

U/A — Apply the same envelope to existing masters, warehouse/location/item/lot metadata, opening requests/corrections, receipts/issues/transfers/returns, counts/reconciliation/adjustment/reversal, QC inspection/hold/release, approval/rejection and RBAC publication. Extend existing masters through separately reviewed changes before claiming system-wide compliance. Future sales/jobs/production/dispatch/invoices adopt this contract when separately authorized; no future workflow is created here.

A — Required tests: exact old/new values and versions; actor/employee/policy snapshots survive role changes; missing reason/evidence; independent approval and rejection history; self-approval rejection; atomic audit failure rollback; retry yields one transition event; restricted raw SQL denial; denied security event survives rollback without exposing target data; unauthorized audit/attachment/filter/count access; safe redaction; pagination and every required filter; correction preserves original history. Stock-specific concurrency/rebuild tests remain gated by the stock engine. No Phase 3 acceptance test is claimed executed in this documentation-only stop.
