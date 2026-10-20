# Frontend integration correction plan — Phase 2.1

20 October 2026. Contract preparation only; no frontend source was edited.
Read actual src/lib/api.ts, customersApi.ts, unitsApi.ts, context/AuthContext.tsx,
types and existing mapping documents. Frontend verification scripts use mocks and
cannot establish compatibility with Django. Preserve backend validation and controls.

## Authentication work for a separately authorized frontend phase

1. Configure VITE_API_BASE_URL to the environment's `/api/v1` URL; current defaults
   and example use `/api`. Coordinate proxy/CORS/HTTPS deployment separately.
2. Change LoginRequest to `{email:string,password:string}`. Backend rejects username.
   Login/me User DTO uses UUID string id, email/name, roles[], permissions[] and
   is_master_admin. Inspect backend accounts/serializers.py for the exact role shape.
3. Replace singular demo Role in real-session user state with those server fields.
   Do not select the first role, infer a role from email/name, or map unknown roles
   to admin. Multiple role membership is supported. Route/action visibility should
   test explicit capabilities; backend authorization remains authoritative.
4. Preserve existing refresh rotation/concurrent-refresh safeguards and query me
   after restoration/access changes. Use backend logout with the retained refresh
   token before clearing local session state; always clear local state on completion
   or failure, expose failed remote revocation honestly, never claim all sessions
   were revoked. No password/token payload logging or credentials in error reports.
5. Disable real backend saves in demo sessions. Demo role labels are not business
   permission assignments. Replace the finance login's singular role gate only after
   client approval of required capabilities; do not invent that matrix here.

## Master DTO and command changes

CustomerRecord.id and UnitRecord.id become UUID strings. Preserve UUIDs as opaque
identities; do not parseInt or enforce db:\\d+. Prefer a separate backendId/sourceId
mapping in UI state; existing mock/reference IDs remain source provenance until an
approved import mapping exists. See FRONTEND_MAPPING.md for entity field mappings.

Customer fields retain their established semantics: contactPerson -> contact_person,
billingAddress -> address, deliveryAddress -> delivery_address, customerType ->
customer_type. Do not infer B2B where the source is unknown. Product is a generic
identity; finished-goods references a separate ProductVariant and its Product UUID.
Unit labels/codes resolve to approved Unit UUIDs. Do not infer conversions or openings.

Use `is_active=true`, not `active=true`, for customer/unit filters. Lists are paginated
{count,next,previous,results}; load all requested pages or render server pagination.
Read version/ETag and retain them with editable objects. POST and PATCH send a stable
Idempotency-Key header per user intent, reused with identical payload/precondition
after ambiguous transport failure. Remove body creation_key. PATCH sends If-Match
with the last read quoted version; on 412 reload and ask the user to reconcile.
Do not silently resubmit a stale edit with a new version. Handle 400/403/404/409/412/428
using the structured error envelope and request_id. Decimal quantities/rates remain
strings at the transport boundary; conversion/display must not lose precision.

## Import/Admin screens and acceptance criteria

Import review must show canonical_review, canonical proposed UUIDs/reference versions,
full duplicate candidates, source sheet/row, errors and explicit decisions. Read
`imports/{uuid}/reviews/` for immutable historical plans; successful approval exposes
applied_plan with reviewed plan/hash and row result UUID/version mappings. A 409
stale_review requires a new review. Approval never posts openings or movements.
Legacy reviews without a canonical snapshot must be reviewed again.

Implement the employee directory, profile forms, status/reset requests, effective
memberships/pending changes, permission visibility and audit history described in
EMPLOYEE_ADMIN.md. Add role catalogue, capability proposals, affected membership diff,
independent approval and cancellation using the governed endpoints. Show Role ETags
separately from Employee and capability revision versions. No UI to edit protected
Master Admin/staff/superuser flags or technical capabilities.

Before integration signoff, run browser-to-Django acceptance with synthetic fixtures
in an isolated environment: email login/me, multiple/no roles, permitted/denied actions,
revoked refresh/logout, deactivation, paginated UUID masters, retry after network loss,
stale edits, malformed references, independent approvals and stale import candidates.
Existing check-*.mjs scripts must adopt real DTOs and contract fixtures; green mock
scripts alone are insufficient. No frontend acceptance/integration is claimed here.
