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

Operations must manage permission grants through controlled tooling; a public role editor
or user administration API is out of scope. Tenancy, delegation, approval thresholds,
revocation breadth, MFA/SSO and token storage remain deployment/client decisions.
