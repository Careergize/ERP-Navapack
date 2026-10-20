# Phase 3A configuration API

20 October 2026. Technical foundation only; no quantity or posting API.

## Routes and contracts

All routes use JWT and `/api/v1/inventory/`:

- `warehouses/` and `{uuid}/`: GET list/detail, POST create, PATCH metadata/activity. Requires explicit inventory.view_warehouse for reads and inventory.configure_warehouses for writes. Creation additionally requires company-wide scope; editing requires target scope.
- `locations/` and `{uuid}/`: GET/list/detail, POST, PATCH. inventory.view_storagelocation, add_storagelocation, change_storagelocation respectively, plus warehouse scope. Warehouse membership immutable; parent may change only within warehouse without cycles. Classification is descriptive text, not quality clearance.
- `identities/` and `{uuid}/`: GET/list/detail, POST and retirement-only PATCH. inventory.view_stockidentity, add_stockidentity, change_stockidentity respectively, plus warehouse scope. Exactly one material/variant/consumable UUID and its primary unit. Backend assigns UUID/reference. All provenance/owner/parent/location fields immutable. Operational status always unavailable. No quantity fields.
- `history/` and `{audit-event-uuid}/`: read-only paginated history, requires inventory.view_inventory_audit AND corresponding view capability AND current warehouse scope. Filters actor, action, entity_type, entity_id, request_id, warehouse, date_from/date_to (ISO datetime), and ordering timestamp/action. Old/new values are safe configuration snapshots; no stock approvals/transactions exist yet. The global technical Admin audit endpoint excludes these events to prevent scope leakage.

Lists use count/next/previous/results, default 25/max100 page_size. Search warehouses/locations by code/name; identities by generated reference/source/supplier batch/physical mark. Filters warehouses is_active; locations warehouse,parent,is_active,classification; identities warehouse,location,kind,ownership,lifecycle,parent. Stable UUID ordering. No PUT/delete/action posting routes.

POST/PATCH require printable stable Idempotency-Key and reason. PATCH requires quoted positive If-Match version. Successful responses return record version and ETag. Same authorized payload/key retries replay without duplicate audit or identity; changed payload409, missing version428, stale412, validation400, permission403, hidden UUID404. Safe validation/request-ID envelope retained. Never generate a new retry key merely because the network timed out.

Warehouse fields code/name/description/is_active/custody_department (optional existing Department UUID) are configurable. Department mapping is proposed Stores accountability, grants no access and is unresolved if blank. Codes are case-insensitively globally unique, a technical catalog convention that can be revisited before rollout. Whitespace stripped by serializers. No real warehouses seeded. Deactivation rejects active children or registered identities; retire identities and deactivate bottom-up. No hard deletion through any API; DB rejects deletion.

Stock identity requires warehouse, exactly one typed item FK, unit, kind BATCH/ROLL/CONTAINER/PORTION, source_system and source_reference (stable identity/line token, unique together). source_document_reference is a separate reusable original document reference; multiple identities may share it. Optional supplier UUID/supplier_batch are separate; supplier batch is not unique. ownership defaults UNRESOLVED; COMPANY/OTHER require ownership_evidence; CUSTOMER/SUPPLIER also require the corresponding existing owner_customer/owner_supplier UUID. Evidence is a controlled external reference, not an uploaded/public attachment or a claim of approved live ownership. No new organization model. Parent and child must match warehouse/item/unit/ownership and parent must be registered. Physical_reference may remain blank; even a nonblank mark does not prove approved physical segregation. Creation is registration, never a quantity split or receipt. Retiring a parent does not erase its child traceability; no quantity interpretation exists.

## Authorization/provisioning boundary

User must be active and have an Employee profile. Existing governed RBAC resolves explicit capabilities; no superuser/Admin/Master Admin automatic capability or scope shortcut. WarehouseScope records separately evidenced independent approval/expiry and optional company-wide oversight. Scope alone never grants a capability. Department/title does not grant scope.

**No public or trusted grant-provisioning command is supplied.** Scope lifecycle is a blocked feature: existing role publication does not bind scope changes. Before real use, add minimal independent proposal/publication/revocation with policy/content/membership snapshots, ceilings, replay/locking and atomic audit. Do not insert live scopes with SQL/ORM as a workaround. Only synthetic tests create scopes. Empty lists for accounts without approved scope are honest unavailable configuration, not zero stock. No role/membership/scope/data seeds or data migrations.

## Protections and limits

UUIDs, typed protected FKs, exact-item/owner shape, generated reference/source uniqueness, lifecycle choices and same-warehouse/cycle/parent/unit guards. API writes lock existing administration gate then dedicated configuration gate before version/reference rows. The DB trigger also takes the configuration gate. Future stock operations need their own reviewed lock protocol; this is not a posting engine. Privileged external writers must follow governance locks too.

Atomic existing core commands retain actor, correlation, server time, reason, old/new safe snapshots, versions, employee identity and role revision/digest/capability/scope evidence in AuditEvent. Inventory denial logs carry verified actor/action/correlation without bodies/secrets; they are not successful business audit. Existing protected audit machinery retained. No claim of complete legacy-module audit, DBA tamper protection, restricted production runtime-role verification, evidence file storage, retention/export or full common audit filter set.

## Frontend and deployment

Existing email login/session maps plural backend roles/capabilities without selecting a business role. `/admin/inventory` is the integrated configuration area; real accounts cannot enter unintegrated demo routes. Optional demo login remains separate. /api/v1 defaults and normalization of legacy /api configuration preserve .env; backend logout revokes refresh before clearing session and reports failure. Management forms persist backend responses with retry/version handling; no local mock success. Identity viewer shows persisted references/status and scoped change history. Opening correction is explicitly unavailable until its original ledger/independent workflow exist.

Application DB migration/deployment is not authorized by implementation. inventory0001–0005 apply only in disposable tests for verification. Follow separate reviewed release/migration/runtime grants and browser acceptance before enabling actual employee use. See ../../docs/phase3-planning/PHASE_3_TEST_REPORT.md for commands/results and exclusions.
