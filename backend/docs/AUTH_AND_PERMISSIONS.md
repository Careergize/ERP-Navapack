# Authentication and permissions

User is installed before initial migrations: UUID PK, lowercase email login,
database case-insensitive uniqueness, name, active/staff flags and server timestamps.
EmailBackend normalizes lookup and checks password/active status. PBKDF2 and Django
password validators are configured; trusted provisioning scripts must call
validate_password when accepting a human-selected password outside createsuperuser.
No public registration or password-reset API is provided.

Simple JWT uses an independent signing key, 5-minute access, 8-hour refresh, rotation
and blacklist-after-rotation. Refresh/logout validate the signed token, lock its persisted
outstanding-token row and check the blacklist again after the lock, preventing concurrent
double rotation. They require an active user and current password fingerprint. Logout
checks token ownership against the authenticated actor before revoking. Password changes
invalidate both token types. Logout revokes only the presented refresh; unexpired access
and other sessions remain valid. Immediate account-wide session revocation is not promised.

Login success/failure, successful refresh and logout generate audit events. Failed login
does not retain the attempted email/password. No access/refresh token is put in audit or
logs. Upstream Simple JWT stores outstanding tokens in its own table for blacklist
management; restrict database access and prune expired tokens. Audit append-only rules
apply to audit events, not to this upstream lifecycle table.

Roles and memberships have UUIDs and are server-managed. A user can have multiple roles;
each role grants Django Permission rows. The normal Django direct/group permissions and
superuser capability semantics remain available to trusted operators. No business roles,
capability mappings or demo accounts are seeded. The nine frontend role labels do not
grant backend authority and are not written into JWT claims.

EmailBackend resolves role capabilities along with Django permissions on each request;
me returns current roles and effective permissions. ActionPermission fails closed if
an action mapping is absent, identity is inactive, capability is missing, or object_scope
is absent. Views must explicitly map actions, scope querysets for lists/creates, call
object checks, and services must recheck locked state. There is no guessed tenant or
department boundary. Never use the permission list returned to the browser as authorization.

require_independent_actor(actor, recorded_maker_id) rejects missing makers, inactive
actors and maker==reviewer, including superusers. Apply only to operations whose policy
requires independence; no domain authority matrix has been approved. Maker must be
loaded from persisted server state, never request data. execute_command always writes
audit with its authenticated actor; callers cannot supply a substitute reviewer ID.

Operations must manage permission grants through controlled tooling; a public role editor remains out of scope. Phase 2 now adds a strictly
Master Admin-gated employee administration API (see EMPLOYEE_ADMIN.md). Tenancy, delegation, approval thresholds,
revocation breadth, MFA/SSO and token storage remain deployment/client decisions.

## Phase 2 catalog authorization

Implemented per-resource view/add/change capabilities, prospect promotion, revision
creation and import stage/review/approve capabilities. No grants or client roles seeded.
Shared catalog is explicitly the current server scope; no implicit department or tenant
rule is claimed. New references require active masters; inactive catalog entries remain
visible with read capability. Every write uses transactional command authorization,
including retry reauthorization; importer also checks all target capabilities.
See [exact action/capability matrix](PHASE2_API.md#permission-matrix).
Independence for master imports is a client decision, not a guessed role rule.


## Master Admin and employee accounts

The server-controlled User.is_master_admin flag plus explicit accounts action capability
is mandatory for employee/role administration and audit reads. Superuser status or an
accounts capability alone does not grant entry. The employee API cannot set any privileged
flag, group/direct permission, User ID, password or role permission contents. Trusted
provisioning grants only technical accounts capabilities, with validated getpass input.
No final business matrix or business capabilities are seeded.

Role grants/removals require a current explicitly configured RoleAssignmentPolicy;
required independent approval is enforced for superusers too, with fresh maker/reviewer
capabilities and matching policy digest. Self/privileged targets are denied. Reset/email/
activation paths also enforce the target access ceiling to prevent impersonation escalation.
Independent offline completion is mandatory for ordinary employee recovery. No reset email
or public reset token endpoint exists. No role editor or privilege-granting API is exposed.

Employee deactivation blocks subsequent access/refresh/login and changes the password
fingerprint, preserving invalidation after reactivation. It does not retract a request
already authenticated and in flight. Subsequent role checks use Phase 1 server-managed
memberships rather than JWT role claims. Details/permission matrix: EMPLOYEE_ADMIN.md.


## Phase 2.1 governance

Two new technical permissions, accounts.manage_role_capabilities and
accounts.approve_role_capabilities, govern role shell/metadata/proposal/cancel and
independent publication respectively. Active Master Admin flag is mandatory in addition
to the capability. No migration grants these to existing users. New trusted provisioning
includes technical administration rights only. Publication rechecks maker and reviewer,
both delegation ceilings, role ownership/privileged members and exact affected member/
policy snapshot. Every publication needs distinct actors even if employee assignments
for the approved role do not. Governed runtime capabilities resolve the immutable approved
revision; unreviewed M2M changes cannot expand access. Configured legacy roles with
permission drift fail closed. Governed assignment independence must match its published
revision. See EMPLOYEE_ADMIN.md for endpoint matrix and legacy transition boundaries.
