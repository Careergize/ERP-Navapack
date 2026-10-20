# Employee accounts and Master Admin contract

20 October 2026. Implemented extension to Phase 2 in apps/accounts. Frontend unchanged.
No business roles, client authority mappings, approval limits or real employee accounts
are seeded. Existing Phase 1 accounts are preserved; profiles are not inferred by name.

## Trust boundary and schema

User gains is_master_admin (default false, server-controlled). Master Admin is a trusted
account designation, not a role code, department, is_staff flag or superuser alias.
Administrative API access requires a fresh active Master Admin plus the action's explicit
accounts capability. A superuser lacking the designation is denied. Roles never grant
the designation and the employee APIs never accept direct/group permissions or flags.

Employee has UUID id, version, UTC timestamps, immutable human employee_id (case-insensitive
unique), protected one-to-one User, protected Department, required designation, optional
protected reporting_manager Employee, created_by and updated_by. Name/email/is_active
live on User, so there is no conflicting profile status. Email is normalized and unique;
names are required and may repeat for different people. New manager assignments require
active employees; self/recursive reporting chains are rejected. Department must be active.
Department/manager links do not imply permission grants or client-approved authority.

RoleAssignmentPolicy binds a Role to its current permission digest and an explicitly
chosen requires_independent_approval boolean. Missing/stale policies fail closed.
RoleChangeRequest retains target employee, role, add/remove operation, membership UUID,
permission digest, required independence, requester, reviewer, status and application time.
Membership remains the Phase 1 effective grant table; pending requests do not grant access.
Applied removal deletes only the membership and preserves its UUID in request/audit history.

EmployeeResetRequest retains employee, requested_by, expected employee version, pending/
completed/superseded status, independent completed_by and completion time. It contains no
password, reset token or email body. Employee and request versions are positive; partial
unique constraints allow one pending role change per employee/role and one pending reset
per employee. Database checks reject self-approved independent role changes and self-
completed resets, and require reviewer/time/evidence on completed changes.

Self and privileged targets (Master Admin, staff or superuser) cannot be mutated through
these APIs. Privileged account maintenance remains a controlled offline operation, not a
way to acquire administration rights through the directory. New API employees are ordinary
active accounts with unusable passwords; they cannot sign in before verified reset completion.
There is no registration endpoint, credential response or generated shared password.

## Trusted operator commands

Run from backend using .venv/Scripts/python. Substitute approved values; commands do not
create a guessed department. An existing approved active Department UUID is required.
For a fresh installation, provision that department through trusted Phase 2 tooling first.

```powershell
.venv/Scripts/python manage.py provision_master_admin --email '<approved-email>' --name '<approved-name>' --employee-id '<approved-employee-id>' --department '<department-uuid>' --designation '<approved-designation>'
```

Password and confirmation are read only with getpass, validated using configured Django
validators and hashed with the configured hasher. No password argument/environment default,
credential output or hardcoded password exists. User/profile/technical grants/audit are one
transaction. Existing emails/IDs are rejected, not upgraded. This creates a new Master Admin
without is_superuser/is_staff or business permissions. No command was run to create a real
account during implementation; provisioning was verified only in disposable test databases.
Provision a second authorized Master Admin for independent recovery/approval operations.

Provision grants only the accounts technical capabilities listed below. Business capabilities
must be approved and provisioned through trusted existing permission tooling before any
administrator may delegate them. Master Admin does not automatically mean all business access.

```powershell
.venv/Scripts/python manage.py configure_employee_role --operator '<master-admin-user-uuid>' --role '<existing-role-uuid>' --independent-approval yes
```

Use yes/no only from the approved role policy. This records a policy/digest and audit,
not role permissions or memberships. Operator needs manage_employee_roles and all the
role's capabilities. Accounts/auth/contenttypes/sessions/token_blacklist/core permissions
are not delegable employee roles. Role permission editing has no API. Trusted direct
permission/group/superuser/role changes are security operations outside this module;
they must follow an approved runbook and use the same administration lock when concurrent.
The module does not promise control over privileged DBA or arbitrary shell mutations.

Changing a role's permission set invalidates its assignment policy and pending approvals.
Policy reconfiguration does not approve old requests with changed permission digests or
independence. Cancel stale requests and submit again. Existing Phase 1 memberships use
live role permissions; do not alter an in-use role outside a reviewed access-change
process. The policy command is not a blanket approval of a client authority matrix.

```powershell
.venv/Scripts/python manage.py complete_employee_password_reset --operator '<different-master-admin-user-uuid>' --request '<reset-request-uuid>' --identity-verified
```

After offline employee identity verification, a different currently authorized Master
Admin completes the pending reset. Both requester and completer must remain active
Master Admins with initiate_employee_reset and at least the target's retained access.
The target must be an active ordinary employee and its version must match initiation.
Any intervening profile/access/status change makes the request stale; initiate again.
The command prompts/validates twice (before and under locks), stores only a password hash,
advances versions, completes the request and audits atomically. Never expose this command
through a generic web terminal, task runner or a client-supplied operator field.
Password distribution/employee-controlled reset delivery, expiry and MFA/SSO require a
separate approved transport/recovery design. This module sends no email or notifications.

## API conventions

Base /api/v1/, bearer JWT, JSON snake_case, UUIDs, Phase 1 error envelope, standard paginated
{count,next,previous,results}. Default page_size 25, maximum 100. All administrative responses
have Cache-Control: no-store. No hard employee/user/role deletion or generic permission editor.

Every mutation requires Idempotency-Key. Existing-employee mutations require its current
If-Match: "version". Missing = 428; stale = 412; conflicting retry payload/state = 409;
validation = 400; authenticated denial = 403; wrong employee/assignment/request = 404.
Commands scope nested IDs to the persisted employee and rerun current admin authorization
on replay. Exact retries return retained snapshots, not a fresh directory state.

Employee GET/PATCH/create responses use employee version and ETag. Access/reset command
responses use id/version for the request plus employee_version; their ETag is the employee
version for the next employee command. All transitions advance the employee version.

## Implemented routes and request bodies

- GET/POST employees/: GET paginated directory; POST body employee_id, name, email,
  department UUID, designation, optional reporting_manager Employee UUID/null.
  Returns 201 Employee plus Location. No caller-supplied User ID or access flags.
- GET/PATCH employees/{employee_uuid}/: detail or partial profile update. Name/email/
  department/designation/reporting_manager writable. employee_id may be resent unchanged;
  changing it is rejected. Activation/roles/privileged flags/actor/version/password fields
  rejected. Email changes require target access within the administrator's ceiling.
- POST employees/{id}/activate/ and deactivate/: empty body. Activation requires target
  retained capabilities within actor's ceiling. Deactivation clears usable authentication
  data and changes password fingerprint; it keeps roles/history and makes all subsequent
  access/refresh/login fail under Phase 1 rules. Reactivation does not revive the old
  password/JWTs; initiate verified reset to restore login. Already-in-progress requests
  are not retroactively undone by deactivation.
- POST employees/{id}/password-reset/: empty body. Creates pending reset and supersedes
  previous pending reset. Requires active ordinary target and target access ceiling.
  Returns 201 request metadata and employee_version. Initiation alone does not revoke
  current sessions; completion or deactivation does. No token/email-send claim.
- GET roles/ and roles/{id}/: ID/code/name, sorted capability strings and assignment_policy
  (null if missing; otherwise version/independence/current digest match). Read-only.
- POST employees/{id}/role-assignments/: body {"role":"role-uuid"}. Returns 201 change
  request, pending when independent review is configured, otherwise applied. Nonconfigured
  roles, stale policies, duplicate roles/requests and capabilities outside actor's own
  delegation ceiling are rejected. Grants require an active employee. Multiple memberships
  are supported; no speculative mutually-exclusive-role or role-limit rules are seeded.
- DELETE employees/{id}/role-assignments/{membership_uuid}/: empty body. Returns 200 removal
  change request. Independence applies to removals too: pending removal preserves effective
  access until an independent reviewer applies it. Deactivate for immediate suspension.
  Reviewed removals can be applied while the target is inactive; no privilege is granted.
- POST employees/{id}/access-requests/{request_uuid}/approve/: empty body. Different current
  authorized Master Admin, same exact role policy/digest, fresh maker authority and both
  delegation ceilings required. Target active for grants. Returns applied request and
  employee_version; database checks also forbid self approval, including superusers.
- POST employees/{id}/access-requests/{request_uuid}/cancel/: empty body. Cancels pending
  changes without granting/revoking memberships; used to replace stale/obsolete requests.
- GET admin/audit-events/ and admin/audit-events/{id}/: read-only append-only audit history.
  Filters actor User UUID, action, entity_type, entity_id, request_id; ordering timestamp/
  action (default -timestamp,id). Employee timeline filter entity_type=accounts.employee
  and entity_id=employee UUID. Includes safe role/request/membership references and status,
  never password/token/source payload. Policy changes have accounts.roleassignmentpolicy
  entity references. Audit records remain protected by Phase 1 PostgreSQL safeguards.

Directory filters: is_active, department, reporting_manager, employee_id; search across
employee_id/User.name/User.email/designation; ordering employee_id/user__name/created_at/
updated_at (default -created_at,id). Detail includes User UUID, employee_id, profile fields,
User active/admin flags, effective permissions, effective memberships with IDs/role codes,
pending_access_requests, reset_requests and audit timestamps/actors. Inactive employees'
effective permissions are empty while retained memberships remain visible.

## Action capabilities and object scope

Every capability below additionally requires active server-controlled is_master_admin.
No client role string, frontend permission list, actor parameter or superuser bypass.

- Directory/detail: accounts.view_employee.
- Create ordinary account/profile: accounts.add_employee.
- Profile edit: accounts.change_employee.
- Activate/deactivate: accounts.manage_employee_status.
- Reset initiation/completion: accounts.initiate_employee_reset.
- Role directory/detail: accounts.view_role.
- Request assignment/removal/cancel: accounts.manage_employee_roles.
- Independently apply pending role changes: accounts.approve_employee_roles, plus the
  requester's continuing manage_employee_roles authority and both capability ceilings.
- Audit history: accounts.view_admin_audit.

All directory entries are one explicit shared administration scope. No department/manager
or tenant visibility rules are invented. All target writes reject self and privileged
accounts and scope assignment/request IDs to their employee. A malicious cross-employee
membership reference cannot be removed or approved. Technical role permissions and flags
cannot be delegated. Reset/email/activation cannot be used to impersonate access above the
administrator's own capabilities. Offline account/policy/security operations remain trusted.

All administrative writes serialize using one PostgreSQL advisory transaction lock, then
lock employee/User/request rows. This protects reporting-chain validation and access changes
against cooperating API/command races. State, command result and actual-actor audit commit
or roll back together. Role effects are server-resolved on subsequent authenticated requests;
existing JWTs carry no client-managed role authority.

## Future Admin Dashboard: required screens and integration plan

No frontend screen/component/Context was modified.

1. Employee directory: paginated search, department/active filters, employee number/name/email,
   designation, manager, active state and role badges. Display accounts only from backend;
   do not use frontend mock MasterUser identities or pretend role labels grant rights.
2. Add/Edit Employee: load approved Department UUIDs and active manager Employee UUIDs;
   enforce required fields, show duplicate email/ID errors. Existing ID read-only; activation,
   roles and resets are explicit separate actions. Show server ETag/version conflicts and
   refresh rather than silently overwrite. No password, is_staff or is_master_admin controls.
3. Role assignment: list backend roles with capability strings and policy status; select exact
   UUID. Show pending grant/removal distinctly from effective membership. Independent approval
   queue must prevent maker approval in UI as well as server; allow stale-request cancellation.
   Retain membership UUID for removal; never substitute role UUID in DELETE path.
4. Account status: confirm the selected employee and show deactivation's password/JWT effect;
   reactivation requires a verified reset before login resumes. Reset panel shows pending/
   completed/superseded and offline handling instructions, never claims mail was sent.
5. Permission visibility: display effective server capabilities and role membership separately;
   distinguish retained roles on inactive employees. Route entry may use auth/me's read-only
   is_master_admin flag plus capabilities, but backend remains the authorization authority.
6. Audit history: scoped timeline by employee UUID; actor UUID, action, request ID, version,
   safe change names, role/request/membership references and timestamps. Paginate server data;
   do not recreate history from frontend state. Policy configuration audit is separately visible.

Frontend work must be separately scoped: build typed DTO/UUID adapters for the above responses,
use the existing real JWT session flow, add retry headers and If-Match from the employee ETag,
reuse retry keys across ambiguous transport failures, handle 400/403/404/409/412/428 explicitly,
and reload Employee/roles/audit after commands. Store no credentials in browser logs or audit.
No public registration or privileged-account editor should be added. A separately scoped role-capability editor must use the Phase 2.1 governed revision endpoints below.

## Decisions still required

Approve named administrators and their business delegation ceiling, real employee numbering,
Department/manager mappings, role permission contents and independent-review policy per role,
tenancy/data privacy scope, recovery delivery/verification/expiry, MFA/SSO, privileged-account
maintenance and security-event retention. No final client business authority matrix or SOP
compliance is claimed. Master Admin provisioning and independent recovery safeguards are
technical boundaries, not a guess about who holds client operational authority.


## Phase 2.1 governed role capabilities

Roles now expose version, governed and approved_revision. POST `/api/v1/roles/`
accepts only code/name and creates an empty governed shell. PATCH accepts only those
metadata fields, with If-Match; it cannot edit permissions. No role deletion API exists.
GET `/api/v1/roles/capability-catalog/` paginates the caller's held nontechnical
capability definitions. This is a delegation ceiling, not an approved client matrix.

POST `/api/v1/roles/{id}/capability-revisions/` accepts exactly permission_codes
(a sorted, unique array of existing `app.codename` strings) and an explicit boolean
requires_independent_approval (employee assignment policy). All capability revisions
require a different Master Admin to approve, regardless of that assignment boolean.
GET on the same URL returns paginated immutable proposal/approval history.
POST `.../capability-revisions/{revision_id}/approve/` or `/cancel/` takes an empty
body. All writes require Idempotency-Key; detail writes require the current Role
If-Match. Responses include role_version; their ETag refers to that Role version.
A proposal advances Role version, publication/cancellation advances it again.

Permission matrix: GET roles uses accounts.view_role; create/edit/propose/cancel/catalog
uses accounts.manage_role_capabilities; approve uses accounts.approve_role_capabilities.
Every operation additionally requires active is_master_admin. Approval rechecks maker
and reviewer grants, current delegation ceilings, exact membership/status snapshot,
underlying permission digest and assignment policy version. Both actors are excluded
from roles they hold; roles held by staff, superusers or Master Admins require trusted
maintenance. Technical accounts/auth/core capabilities cannot be delegated here.
400 means invalid definition, 403 denied/self approval, 404 malformed/missing UUID,
409 stale_review means cancel and propose again, 412 stale Role If-Match, 428 missing
If-Match. No pending proposal changes effective permissions. Atomic publication applies
the exact reviewed capability set to the exact affected membership set and audits it.
Old pending employee access requests fail when their capability digest/policy differs.

Governed roles resolve permissions from their immutable approved revision, not mutable
M2M rows. Out-of-band M2M additions cannot expand their access. Configured legacy roles
fail closed if the raw permission digest no longer matches the trusted assignment
policy. Legacy roles without policies retain Phase 1 trusted maintenance behavior;
review and migrate those roles before release, never use them as a public editing path.
The legacy configure_employee_role command can initialize a legacy policy but refuses
policy changes or governed-role updates; it cannot rebaseline changed grants.
Approved governed assignment independence must match the published revision.

New trusted Master Admin provisioning includes the two new technical governance
capabilities. Forward migrations do not assign them to existing users. Explicitly
approved trusted account maintenance is required for existing administrators; do not
seed business permissions to make the editor usable. At least two independently
provisioned authorized administrators with explicitly approved business ceilings are
needed to publish a business role. No account or matrix is created by these changes.

Future dashboard: add capability catalogue selection, proposal diff, exact affected
employee list, policy flag, pending/cancelled/applied history and independent approval
queue. Display stale review failures and require a fresh diff/approval; never replay
an old draft automatically with new members. The current frontend has none of this.
