# Controlled DEMO database migration plan

This procedure is prepared, not approved for any hosted database. Required approval:
exact host/database, DEMO identity, backup location/hash and successful restore,
forward plan hash, runtime role, expiry and maintenance window. No configured or
hosted application DB was migrated by this task.

## Additive schema

New migration: `core.0005_persistent_demo_boundary`, depending on commercial 0004,
rehearsal 0004 and core 0004. Adds the immutable DEMO identity table/context function
and wraps the context preambles of three commercial/rehearsal trigger functions.
Original test preambles and all transition/immutability/audit checks remain intact.
No inventory ledger trigger, historical migration or original ledger Python gate is changed.

On databases outside the approved `navapack_demo_...` namespace, the SQL context
function returns false before reading the marker. Production settings never select
the DEMO Python gate. No environment-only boolean opens a posting pathway.

## Before migration

1. Verify a newly provisioned dedicated DEMO database, never an application/production
   DB. Record actual current_database, host, owner, PostgreSQL version and TLS verification.
2. Back up the approved target using matching/newer PostgreSQL tools. Retain encrypted
   custom dump + SHA256 + operator approval in access-controlled storage. An empty
   target still needs an approved provisioning/backup record.
3. Restore into a **separate newly generated disposable clone**, apply exact source
   revision and forward plan, run persistent-demo/security/full regression, compare
   records/hashes/triggers and verify no operational stock/QC authorizations.
4. Approve code revision and this target's plan; do not reuse another DB's plan hash.

## Exact operator commands (from backend)

With approved owner credentials injected for this target and settings.demo:

```sh
python manage.py migrate_demo --database navapack_demo_<approved_suffix>
```

This is read-only and prints the forward plan and `plan_sha256`. Review it against
the tested source revision and backup. Only after explicit authorization:

```sh
python manage.py migrate_demo --database navapack_demo_<approved_suffix> --apply-plan <reviewed_sha256> --backup-reference <verified_backup_reference> --approval-reference <approval_id>
```

The digest binds exact database name and forward migration names; stale/different
plans are rejected. Builds/startup never invoke this command. Retain the console
record alongside approval and backup; migrate as owner, not runtime.

Provision a dedicated runtime login through approved DBA tooling (password supplied
securely, not an argument): NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS,
no memberships, no ownership. Grant only the reviewed template:

For PostgreSQL 16+, a non-superuser migration owner may need explicit permission to
SET ROLE to the runtime role while seeding. After approving the exact role identities,
the role administrator can grant the **runtime role to the owner** with SET TRUE and
INHERIT FALSE (two GRANT statements if needed). Never grant the owner role to runtime.
Runtime itself must have zero role memberships. Verify that the selected Render tier/
credentials permit these restrictions; inability to provision them is a release blocker,
not justification to run the service as owner. See
[PostgreSQL role membership](https://www.postgresql.org/docs/16/role-membership.html).

```sh
psql -X -v ON_ERROR_STOP=1 -v demo_database=navapack_demo_<approved_suffix> -v demo_runtime_role=<approved_role> -f scripts/demo_runtime_grants.sql
python manage.py approve_demo_boundary --database navapack_demo_<approved_suffix> --instance <approved_uuid> --runtime-role <approved_role> --days 30 --approval-reference <approval_id> --backup-reference <backup_reference>
python manage.py seed_demo --database navapack_demo_<approved_suffix> --generation demo01 --maker-password-file <protected_file> --reviewer-password-file <different_protected_file> --approval-reference <approval_id>
```

Initial stamping requires an empty application dataset. Boundary cannot be edited,
deleted or renewed in place. Seed creates synthetic users/data only; no real role
matrix, stock evidence, VAT/LED or operational authority. Runtime grant SQL permits
locked immutable reads with column-level UPDATE rights; the database guards still
reject actual revision mutations. No inventory posting privileges are granted.

Switch web environment to runtime credentials and run
`python manage.py deployment_diagnostics`; then perform HTTP/browser acceptance.

## Logical reset

Approve a new generation and new independent actor passwords, then run `seed_demo`
with that generation and `--retire-previous-generations`. Previous synthetic users
are deactivated; records and audit remain append-only. Repeat same generation is a
no-op. Full physical reset or identity/secret renewal needs a fresh approved database.
Never TRUNCATE audit, disable triggers, clean an unknown DB or reset a production name.

## Backup and restore

From a trusted operator environment with runtime read access and verified DEMO settings:

```sh
python scripts/demo_backup.py --database navapack_demo_<approved_suffix> --output <protected_path>/demo.dump
```

Creates a new custom pg_dump and SHA256 manifest, never overwrites. Backups contain
sensitive demo authentication hashes/history and may contain outstanding JWTs.
Encrypt them at rest, restrict access/retention, and never commit them. Never transfer
demo accounts/tokens into an operational production environment. Match pg_dump and
pg_restore major versions to the PostgreSQL server.

Authorize a separately created **empty alternate DEMO database** before restore:

Set the owner/operator DEMO environment to that approved target first:
`DJANGO_SETTINGS_MODULE=config.settings.demo`, `APP_ENV=DEMO`, and both
`POSTGRES_DB` and `DEMO_DATABASE_NAME` equal the alternate target, with its approved
host/TLS/owner credentials. Restore checks these values against the explicit argument.

```sh
python scripts/demo_restore.py --database navapack_demo_<different_approved_suffix> --backup <protected_path>/demo.dump --sha256 <manifest_sha256> --approval-reference <restore_approval>
```

Restore refuses source DB, wrong hash, non-DEMO target, weak TLS and nonempty target.
No `--clean`, trigger disabling, overwrite or automatic deletion. The restored stamp
is bound to the old name, so execution remains disabled. This is intentional:
backup validation is not authorization to activate a restored service. To recover
the same demo identity, the approved recovery plan must restore to its original
logical database name on an isolated replacement server and review runtime role,
secret, expiry and TLS. A different identity requires a separately designed/reviewed
re-provisioning procedure; do not alter the immutable marker manually.

Automated clone tests perform dump/restore, compare job counts, check all triggers
enabled and confirm the alternate restored database cannot execute demo commands.

## Rollback

Stop traffic on failure, preserve failed clone/logs and approved backup. Never run a
blind reverse migration on the hosted DB. Restore only under an approved isolated
recovery plan. New core migration has a reversible definition for disposable upgrade
testing; that does not authorize hosted downgrades or removal of audit history.
