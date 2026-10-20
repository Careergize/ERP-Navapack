# Navapack ERP Phase 2.1 remediation report

20 October 2026. Scope: verified Phase 2 exit findings F1–F7. This report follows
[the original read-only audit](PHASE_2_EXIT_AUDIT.md); that historical report is
preserved. No Phase 3 implementation, production data changes, frontend source edits,
staging, commits, pushes, deployment or remote changes were performed.

## Outcome and recommendation

Technical fixes are implemented for F1/F2/F5/F6/F7. F3 has an explicit integration
correction plan and strict contract regression; frontend integration remains pending
as requested. F4 has a reproducible release plan; the existing dirty/untracked Phase 2
working tree remains intact and no release commit exists.

**NO-GO for Phase 3 implementation or an integrated production release.** Review this
remediation candidate, approve a reproducible Phase 2 release and obtain controlled
SOP/authority/source/inventory decisions first. Backend technical remediation can be
reviewed independently; green tests do not certify missing client SOPs or live deployment.

## Findings and fixes

### F1 — Reviewed import identity and candidate drift

Added append-only ImportReview with canonical JSON plan/hash, reviewer and time. The
batch references the current immutable review and retains its legacy review projection
for existing consumers. Plans contain source digest/system/target/mapping, sheet/row,
explicit decisions, canonical proposed fields, resolved FK UUIDs and reference versions/
state hashes, exact update versions, errors and the full duplicate candidate set.
Decimal values remain strings; unknown nullable observations remain unknown.

Approval validates the stored plan/hash and compares current locked state with the
whole reviewed plan. Changed code resolution, reference contents/active status, target
version or duplicate candidates returns 409 stale_review and requires a new review.
It applies the stored proposed values, never a newly rebound proposal. applied_plan
retains that exact plan/hash/review identity and applied row target UUID/version results.
GET imports/{id}/reviews/ provides paginated review history. Old reviewed batches with
no canonical evidence require review again; already applied legacy evidence is retained
without inventing a historical applied plan.

All cooperating catalog/specification/import HTTP writes take PostgreSQL advisory
transaction lock 70462027 before row locks. This prevents candidate phantoms/reference
changes between approval validation and application. Referenced User rows are also
locked. Trusted external catalog writers must use the same gate; direct DBA writes
are privileged maintenance, outside the API guarantee. This coarse master-write gate
is a deliberate correctness tradeoff, not a future inventory concurrency design.
Master changes, result links, batch applied plan, idempotent result and audit commit
together or roll back. Approval still never creates opening balances or movements.

### F2 — Governed role-capability management

Role now has a version and approved revision pointer. New RoleCapabilityRevision
records contain immutable capability definitions, explicit employee-assignment
independence policy, affected membership/account-status snapshot, previous policy/
permission digests, maker, status and independent approval evidence. Database checks
and triggers protect review contents and terminal history. No business permission
contents, role memberships, limits or client matrix are seeded.

Implemented Master Admin APIs: empty role creation; versioned metadata editing;
capability catalogue; proposal/history; independent approval and cancellation.
Every write requires an idempotency key and detail commands require Role If-Match.
Two distinct active Master Admins with explicit technical governance permissions and
business delegation ceilings are required to publish. Maker/reviewer are checked again
at approval. Neither may change a role they hold; roles held by privileged accounts
require trusted maintenance. Unknown capabilities, technical namespace capabilities
and permissions beyond either actor's ceiling are rejected. Membership/policy drift
requires cancellation and a new proposal, rather than granting to unreviewed employees.

Capability publication always needs independent approval; that cannot be disabled by
the employee-assignment policy flag. A requested change to that flag itself goes
through independent publication. Old pending employee access requests with a different
digest/policy fail. Governed assignment independence must match its approved revision.
Runtime governed permissions come from the immutable approved snapshot, so M2M edits
cannot expand live access. Existing JWTs observe publication on later authenticated
requests. No JWT embeds a permanent role-capability grant.

Configured legacy roles fail closed on raw permission drift. The legacy policy command
can initialize a policy but refuses rebaselining changed grants, policy changes and
governed-role changes. Legacy roles without policies retain Phase 1 trusted maintenance
behavior; inventory and migrate those before release. No public route creates such
legacy roles. Database/management access remains a privileged operational boundary.

New technical capabilities are accounts.manage_role_capabilities and
accounts.approve_role_capabilities. New trusted Master Admin provisioning includes them;
migrations do not assign them to existing users. Existing admin maintenance requires
explicit approved trusted provisioning. See
[endpoint contracts and permission matrix](../backend/docs/EMPLOYEE_ADMIN.md).

### F5 — User UUID references in imports

Foreign-key resolution first attempts a UUID. Optional code resolution is attempted
only for models actually defining code. Department.manager therefore accepts a valid
User UUID without querying nonexistent User.code. Malformed/nonexistent references
remain row validation errors; inactive new references remain prohibited. User state
changes invalidate the reviewed reference snapshot. No account matching by name/email.

### F6 — Nullable process stage

Replaced dynamic field injection with an explicit ProcessSerializer schema. stage:null
is normalized out before creation; omitted stage remains unlinked. Nonnull stage UUIDs
are rejected as input linkage; source_stage_id resolves only within the new revision's
route. This eliminates duplicate stage keyword arguments without weakening historical
route identity. Stage output remains an actual route UUID or null.

### F7 — Malformed UUID handling

Master, import, specification and employee service lookups now use DRF's UUID-aware
get_object_or_404. Malformed path identities return the normal 404 envelope with
request_id rather than leaking a Django ValidationError as 500. Body FK UUID errors
remain 400 or explicit staged-row errors. Existing missing/stale If-Match behavior
remains 428/412 and authorization is still checked before mutations.

### F3 — Frontend contract corrections prepared

[PHASE21_FRONTEND_CONTRACT_PLAN.md](../backend/docs/PHASE21_FRONTEND_CONTRACT_PLAN.md)
specifies the exact future changes: /api/v1 base, email login, plural roles/capabilities,
real logout revocation, UUID DTOs, is_active filters, version/ETag retention, retry headers,
decimal transport and Admin/import screens. Actual api.ts/AuthContext/customer/unit
adapters were inspected. Permanent backend regression proves email/plural-role semantics
and rejects the current username payload. No numeric alias, unversioned write or body
creation_key exception was added. The current frontend remains incompatible for live
integration; successful mock verification is not an integration signoff.

### F4 — Release reproducibility prepared

See [PHASE_2_RELEASE_PLAN.md](PHASE_2_RELEASE_PLAN.md). Branch main and HEAD/cached
origin/main remain 800dd00ba2f103c440130c8ae597ad0c4d8dc283, with existing remote
https://github.com/Careergize/ERP-Navapack-frontend.git. No fetch/live remote verification
or Git configuration change was performed. Phase 2 was already substantially untracked;
the release plan requires reviewing both tracked diffs and the full untracked source
manifest, explicit approval before staging/commit, and checks from a clean approved
checkout. No new release SHA or deployment readiness is claimed.

## Files changed by remediation

Existing files changed relative to the 258-file start-of-remediation hash baseline:

- accounts: models.py, backends.py, employee_services.py, employee_serializers.py,
  employee_views.py, admin_urls.py and management/commands/configure_employee_role.py.
- core/api.py; masters/views.py; specifications/views.py;
  imports/models.py and imports/views.py.
- tests/test_phase2.py: stale reviewed target approval now expects 409 stale_review
  rather than the old generic 400; all existing test cases are retained.
- Backend docs: ARCHITECTURE, API_CONVENTIONS, PHASE2_API, AUTH_AND_PERMISSIONS,
  EMPLOYEE_ADMIN, DATABASE_SCHEMA, DECISION_LOG, DEVELOPMENT_STATUS, FRONTEND_MAPPING,
  FRONTEND_ADAPTER and PHASE3_DEPENDENCIES.

New remediation files:

- apps/accounts/role_views.py.
- accounts migrations 0004_alter_role_options_role_governed_role_updated_at_and_more.py
  and 0005_immutable_capability_reviews.py.
- imports migrations 0005_importbatch_applied_plan_importreview_and_more.py and
  0006_immutable_reviews.py.
- tests/test_phase21_imports.py and tests/test_role_capabilities.py.
- scripts/test_isolated.py; backend/docs/PHASE21_FRONTEND_CONTRACT_PLAN.md;
  docs/PHASE_2_RELEASE_PLAN.md and this report.

Some existing files above were already untracked/modified before this task; this list
describes remediation changes, not ownership of the whole Phase 2 Git diff. No baseline
file was deleted; no existing migration changed; all frontend file hashes are unchanged.
Phase 1 migration files and the historical exit audit remain byte-for-byte preserved.
Ignored environments, database files, logs and frontend build output are not deliverables.

## Verification evidence

All test data was synthetic in fresh uniquely named local PostgreSQL databases. No
application DB migration, production data change or destructive pre-existing DB cleanup
was performed. The existing local PostgreSQL 16 cluster on 127.0.0.1:55432 was started
for verification. The checked-in isolated runner checks DB-name absence, allocates a
UUID test name and delegates only that database's lifecycle to Django.

From backend:

```powershell
.venv/Scripts/python scripts/test_isolated.py
.venv/Scripts/python scripts/test_isolated.py tests.test_phase21_imports tests.test_role_capabilities
.venv/Scripts/python manage.py check --settings=config.settings.test
.venv/Scripts/python manage.py makemigrations --check --dry-run --settings=config.settings.test
.venv/Scripts/python manage.py migrate --plan --settings=config.settings.test
```

- Initial full suite: **119 tests passed in 169.657s**, including all 93 prior tests
  and the then-current 26 regressions. Test DB test_phase21_69cfc8e0473e4100bf8cd790af6c76b7
  created and destroyed by Django.
- Expanded focused run: **31 tests passed in 51.604s**. Test DB
  test_phase21_c0a264c517cb4286a5e0f65b3c707049 created and destroyed by Django.
- Final full suite: **128 tests passed in 206.046s**, all 93 existing tests plus
  35 regression cases. Test DB test_phase21_60cfbef719f94640b1f57c073f96c96c created
  and destroyed by Django. After the final within-batch candidate display correction,
  **46 Phase 2/import tests passed in 92.356s** in fresh test DB
  test_phase21_702afe69f9ca4cb1b02c70ca44a1f006, also created/destroyed by Django.
  That run used `scripts/test_isolated.py tests.test_phase2 tests.test_phase21_imports`.
  The repository now contains **36 new permanent regressions** (15 import/contract,
  21 role governance); all were exercised successfully across these final runs.
  The final source's complete suite has 129 cases; it was not rerun as one 129-case
  command after the last narrowly scoped display correction.
- System checks: no issues. Migration drift: no changes detected. Read-only application
  migration plan lists only the four new forward migrations. Fresh test DBs applied
  the complete migration graph, including the new PostgreSQL guards, successfully.
- Production `check --deploy`: no issues using process-only synthetic hosts/origins
  erp.example.invalid, DJANGO_DEBUG=false and POSTGRES_SSLMODE=verify-full. These values
  were not persisted. This validates settings guards only; actual deployment ingress,
  DB TLS/privileges, migration rehearsal and client operations remain unverified.

An initial focused development run had six test-helper TypeErrors (missing data argument);
the helper was corrected. Its remaining 20 tests passed. No unresolved application
failure is hidden by that earlier run. Initial offline migration generation reported
a local connection warning; subsequent PostgreSQL drift/plan checks passed after the
local test cluster was started. Rollback regressions deliberately inject an audit
failure and assert 500 plus complete rollback; those expected errors appear in test logs.

Permanent scenarios include canonical/reference UUID rebinding, direct reference edits,
new duplicate candidates despite prior acknowledgement, symmetric within-batch candidate
visibility, review history/DB immutability,
exact applied plan/replay, User UUID/status errors, legacy rereview, concurrent reference
write versus apply, nullable stages, malformed paths, strict auth contracts, empty role
creation, catalogue ceilings, protected metadata, holder/privileged-role/self approval
denials, unknown/technical/above-ceiling grants, maker revocation, member/policy drift,
independence tampering, stale pending employee access, existing-JWT revocation, cross-role
scope, concurrent approval retries, database immutability and audit rollback.

From frontend:

```powershell
node ./node_modules/typescript/bin/tsc --noEmit
npm run build
Get-ChildItem scripts/check-*.mjs | Sort-Object Name | ForEach-Object {
  node $_.FullName
  if ($LASTEXITCODE -ne 0) { throw "Failed $($_.Name)" }
}
```

Type check passed. Build passed (1720 modules); existing >500 kB chunk-size warning
remains (main JS 1,172.12 kB / 249.35 kB gzip). All **12** verification scripts passed:
auth, custom-costing, customers, finished-goods, integrated-operations, inventory-workflows,
job-cards, led-finance, quality, quotation-persistence, quotations and sales-fulfillment.
These validate preserved browser behavior/mocks, not implemented Django posting modules.
No browser-to-live-Django integration acceptance was performed.

Git diff --check passed. SHA-256 comparison of all baseline files confirms no deletion,
unchanged frontend and unchanged pre-existing migrations. git check-ignore confirms
.env, .venv, .local, frontend/node_modules and frontend/dist remain ignored. No index
or history changes were made. Final PostgreSQL catalogue verification found no
remaining test_phase21_* databases; the local cluster started for this task was stopped.

## Remaining client and operational decisions

Original controlled SOPs 01/03/05/11/15 and the original stock workbooks are still
unavailable in the repository; source inventory found no original PDF/DOCX/XLS/XLSX.
Reviewed evidence is the original exit audit, actual implementation/tests, backend
contracts and frontend source/planning/reference transcriptions. No original SOP
compliance or workbook reconciliation is certified. Mock/generated reference stock
was not imported as authoritative data.

Obtain the final named authority/delegation/membership matrix, assignment independence
rules, controlled SOP versions, actual source register mappings/units and opening
reconciliation evidence. Approve warehouse/location/lot identity, physical versus held/
reserved/available definitions, returns/consumption/corrections, negative/unknown/
backdated policy and QC/release boundaries before Phase 3 design is frozen. Approve
administrator onboarding, recovery/retention/privacy/MFA, DB runtime restrictions and
out-of-band maintenance controls. Review legacy roles before exposing live governance.

Recommended next action: review this Phase 2.1 diff and test evidence, approve the
release manifest and separately scope frontend contract integration. After client
decisions and repeat exit signoff, Phase 3 may be proposed as a narrow inventory design
and implementation task. No ledger, stock movement, QC posting, Sales Order, Job Card,
production or dispatch implementation is included here.
