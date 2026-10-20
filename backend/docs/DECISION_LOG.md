# Decision log — 15 October 2026

- D001 Implement only explicitly requested Phase 1 in the existing empty backend sibling.
  Preserve frontend source/demo behavior. Source: current user request.
- D002 Django 5.2 LTS on Python 3.11; exact installed dependencies in requirements/lock.txt.
  PostgreSQL only, with psycopg 3. No SQLite concurrency substitution.
- D003 Email-only login uses email request field. Frontend username adapter is proposed
  separately. No guessed receptionist fallback or public account registration.
- D004 Roles grant Django permissions through multiple server-managed memberships;
  no seeded business matrix or tenant schema. The audit's proposed mappings are unapproved.
- D005 Access 5 minutes, refresh 8 hours; rotate and blacklist refresh; serialize refresh
  and logout. Logout does not immediately revoke access or other sessions. These defaults
  need operational approval before production.
- D006 Generic server-resolved command scope permits future company/action/aggregate
  mapping; not a tenancy implementation. Retain successful idempotency results indefinitely
  pending an approved retry window and retention policy.
- D007 Append-only audit enforced through ORM and PostgreSQL mutation trigger, plus
  restricted runtime DB privileges. No claim of protection from a privileged DBA.
- D008 Production rejects debug, wildcard/implicit hosts, shared signing secrets, HTTP
  origins and database TLS weaker than verify-full. Trusted ingress and certificates
  require deployment configuration.
- D009 Throttling uses PostgreSQL fixed windows, avoiding process-local cache races;
  ingress must supply trustworthy REMOTE_ADDR and additional abuse controls.
- D010 Move the existing frontend Git metadata to the parent workspace and include both
  applications in one repository, retaining history and origin. Keep application builds
  independent and coordinate Vercel Root Directory frontend separately from local work.
  Source: user-requested monorepo migration and user-executed metadata move.

## Outstanding decisions

Obtain controlled SOP originals, role/action/object authority and maker/checker rules;
company/tenancy and warehouse scope; browser refresh storage and revocation breadth;
deployment domains/ingress/TLS/secret management; runtime DB grants and migration ownership;
audit reason/evidence privacy, retention/export and idempotency retention; MFA/SSO/recovery;
authoritative account provisioning/delegation. No production approval is implied.

Phase 2 should establish approved masters, stable source identities and import staging
with provenance/null openings, explicit authorization and safe adapters. Obtain original
reference workbooks/photos and reconcile variants/units before importing operational
stock. No stock, QC, commercial or financial posting should be added implicitly.

## Phase 2 — 20 October 2026

- D011 User explicitly authorizes Phase 2 masters/specifications/import staging only.
  Backend AGENTS Phase 1 boundary is superseded only for this scope. Preserve Phase 1
  migrations and infrastructure; no frontend edits or transaction/posting domains.
- D012 Separate generic Product, exact ProductVariant and Material identities. Retain
  governed source_system/source_id; never resolve parties/variants by name alone.
  Nonblank codes unique case-insensitively. Source pairs and master unit identities
  immutable; corrections needing another identity create a new master.
- D013 All saved model revisions sealed and immutable, including child lines, through
  PostgreSQL guards. Parent lock allocates revision numbers. Snapshot master labels and
  codes alongside protected FKs. Configurable routes, no mandatory universal sequence.
- D014 NUMERIC(20,6) stores optional model defaults/quantities, not calculated costing
  or verified client precision policy. No rates, grades, balances, units or machines seeded.
- D015 Import raw evidence plus digest, filename/sheet/row; bounded data-only CSV/XLSX.
  Formula workbooks require controlled values-only export. Explicit mappings/row decisions,
  duplicate acknowledgment, target capabilities and versioned approval; all-or-none apply.
  No stock/opening ledger effect. Demo source cannot be applied; authenticity remains an
  accountable operator attestation pending controlled original storage.
- D016 Current catalog is one explicit shared global scope behind per-resource capabilities.
  No inferred tenancy/department policy, role matrix, approval limit or independent-master
  reviewer rule. Resolve scope/authority before broad production access.
- D017 Preserve incompatible existing frontend customer adapter; document UUID, active-filter,
  retry-key and version requirements rather than weakening the backend or editing UI.
- D018 Original stock workbooks/18 SOPs/8 QC images absent; review only available secondary
  planning/code/reference evidence. No original-source import or SOP certification claimed.

See PHASE3_DEPENDENCIES.md for decisions and proposed next scope.


## Employee administration extension — 20 October 2026

- D019 User explicitly extends Phase 2 to employee accounts and Master Admin operations.
  Extend accounts via new migrations; preserve Phase 1 migrations/authentication and frontend.
- D020 Master Admin is a server-controlled designation plus explicit accounts capabilities,
  not a business role or superuser shortcut. Bootstrap command prompts for a validated
  password; grants only technical administration rights. API targets remain ordinary
  employees; self and privileged-account maintenance require trusted tooling.
- D021 Employee owns employment metadata; User owns normalized unique email/name/active
  status. Human employee_id is required, case-insensitively unique and immutable. Names
  may repeat. Department/reporting links grant no implicit authority; reporting cycles rejected.
- D022 No role is API-assignable without a trusted explicit independence policy tied to
  exact permissions. Enforce capability delegation ceilings and maker/reviewer separation
  where configured, including superusers and removals. Pending changes never grant rights.
  No client business roles/limits/mutual exclusions/permissions seeded or guessed.
- D023 Access-reset initiation stores a request only. Verified offline completion requires
  another active authorized Master Admin, current employee version and both access ceilings.
  No email transport/public token/credentials response. Independent recovery is a technical
  impersonation safeguard, not a final client business approval matrix.
- D024 Deactivation rotates to an unusable password, preserving Phase 1 fingerprint-based
  rejection after reactivation; roles/history remain. Reactivation requires a verified reset
  before login resumes. In-flight authenticated requests are not retroactively rolled back.
- D025 All administration entrypoints share a PostgreSQL advisory transaction lock, then
  row/version locks; audit and command retention are atomic. Role/policy/membership references
  are recorded in safe audit outcomes. Explicitly scoped nested objects prevent cross-employee
  assignment changes; no department/tenant policy inferred.

See EMPLOYEE_ADMIN.md for required frontend screens and remaining operational decisions.


## Phase 2.1 — 20 October 2026

- D026 Approve immutable canonical import plans, not a second interpretation of the
  source. Compare exact UUIDs, versions/state digests and full duplicate candidates;
  reject stale state and retain the applied plan. Preserve legacy evidence honestly.
- D027 Serialize cooperating catalog writes with an advisory transaction lock before
  row locks so duplicate candidates cannot appear between approval check and apply.
  Trusted external catalog writers must use the same gate. This trades master-write
  throughput for review correctness; it is not a future inventory lock design.
- D028 Every role-capability publication requires independent Master Admin review of
  the exact affected membership set and policy. This is a technical change-control
  safeguard, not a client authority matrix. Explicit capability definitions, actor
  ceilings and exclusion of technical grants/self-held/privileged roles prevent API
  escalation. Only approved immutable snapshots drive governed runtime permissions.
- D029 Configured legacy roles with drift fail closed. Legacy CLI initialization does
  not become an alternative grant/policy change path. Existing administrators are not
  silently assigned new technical permissions by migrations. Review remaining legacy
  roles before release; retain Phase 1 trusted maintenance compatibility.
- D030 Normalize nullable process stages in an explicit serializer; use DRF-safe UUID
  lookups. Keep strict DTOs, exact units, opaque UUIDs and optimistic write preconditions.
- D031 Prepare frontend corrections and an approved reproducible release separately.
  No frontend edits, commits, pushes, deployment or Phase 3 posting authorized here.
