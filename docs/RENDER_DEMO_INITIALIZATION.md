# New Render demo database initialization

Prepared operator runbook; none of these provisioning or database commands were
executed. No hosted identity is approved by this document. Use together with
RENDER_DEMO_ENVIRONMENT_CHECKLIST.md and backend/.env.render.example.

Order: new DB identity → secrets → backup/clone rehearsal/plan approval → migrations
→ restricted role → immutable stamp → grants → optional approved seed → runtime
verification → deployment. Stamping before migrations cannot work: the stamping
command queries tables created by those migrations. Never insert the marker by SQL.

## 1. Render Dashboard — approve and create a NEW database

Approve resource cost/region, PostgreSQL major version (16+), unique database name,
owner, restricted runtime role, 30-day demo lifetime, backup/restore evidence,
source revision and migration procedure before provisioning. Keep the web service
undeployed until bootstrap finishes; do not put owner credentials in its runtime.

In New → Postgres choose the approved region, version and plan; explicitly set
the **Database** field to e.g. `navapack_demo_client_20261021`. This is not the
Render service Name. Record the actual immutable database name, owner username,
external operator hostname and internal web-service hostname. New database must
be separate from all production resources. No existing database is renamed,
reset, restored over or migrated by this procedure.

Render's Database/User fields are chosen at creation and cannot subsequently be
changed in the dashboard. If already provisioned under a noncompliant name, stop
and obtain approval for a compliant new database; do not relax the name guard.
Source: https://render.com/docs/postgresql-creating-connecting

Operator connections below use the direct EXTERNAL hostname, with authorized
network access limited to the operator. The Render web service uses the direct
INTERNAL hostname in the same region. Do not use a transaction pooler. Both
endpoints must resolve to this same newly approved database. Use sslmode=require;
encryption required, full certificate identity verification not provided.

## 2. Local PowerShell operator terminal — identity and fresh secrets

Run from the reviewed checkout with its production dependencies installed and
matching/newer PostgreSQL client tools available as psql/pg_dump/pg_restore.
Review local uncommitted changes; pin the source revision before migration.
Owner credentials are used in this operator process only, not in the Render web
service, Git, command-line connection URLs or shell transcript. Stop transcript
recording and use the approved secret store. Replace the illustrative DB name
with the exact approved newly provisioned name in BOTH variables.

```powershell
Set-Location F:\WORK\Navapack-ERP\backend
$Python = (Resolve-Path .venv/Scripts/python.exe).Path
& $Python -m pip install -r requirements/production.txt
if ($LASTEXITCODE -ne 0) { throw 'Production dependencies unavailable' }
git status --short
git rev-parse HEAD
$env:PYTHON_DOTENV_DISABLED = '1'
$env:DJANGO_SETTINGS_MODULE = 'config.settings.render_demo'
$env:APP_ENV = 'DEMO'
$env:DJANGO_DEBUG = 'false'
$env:DEMO_DATABASE_NAME = 'navapack_demo_client_20261021'
$env:POSTGRES_DB = $env:DEMO_DATABASE_NAME
$env:POSTGRES_HOST = Read-Host 'Approved NEW demo database direct EXTERNAL hostname'
$env:POSTGRES_USER = Read-Host 'Approved migration-owner username'
$OwnerRole = $env:POSTGRES_USER
$OwnerPassword = Read-Host 'Migration-owner password' -AsSecureString
$env:POSTGRES_PASSWORD = [System.Net.NetworkCredential]::new('', $OwnerPassword).Password
$env:POSTGRES_PORT = '5432'
$env:POSTGRES_SSLMODE = 'require'
$env:DJANGO_ALLOWED_HOSTS = Read-Host 'Exact approved Render API hostname, without https://'
$env:CORS_ALLOWED_ORIGINS = Read-Host 'Exact approved frontend HTTPS origin, no trailing slash'
$env:CSRF_TRUSTED_ORIGINS = $env:CORS_ALLOWED_ORIGINS
$env:TRUST_PROXY_HTTPS = 'true'
$env:LOG_LEVEL = 'INFO'
$env:DJANGO_SECRET_KEY = & $Python -c 'import secrets; print(secrets.token_hex(32))'
$env:JWT_SIGNING_KEY = & $Python -c 'import secrets; print(secrets.token_hex(32))'
$env:DEMO_EXECUTION_SECRET = & $Python -c 'import secrets; print(secrets.token_hex(32))'
$env:DEMO_INSTANCE_ID = & $Python -c 'import uuid; print(uuid.uuid4())'
$RuntimeRole = 'navapack_demo_runtime'
$ApprovalRef = Read-Host 'Actual approved change/reference ID'
$BackupRef = Read-Host 'Actual verified backup/provisioning and restore-evidence reference'
if (-not $ApprovalRef -or -not $BackupRef) { throw 'Approval and backup evidence required' }
if ($env:POSTGRES_DB -cnotmatch '^navapack_demo_[a-z0-9_]{8,48}$') { throw 'Invalid DEMO identity' }
$env:PGHOST = $env:POSTGRES_HOST
$env:PGPORT = $env:POSTGRES_PORT
$env:PGDATABASE = $env:POSTGRES_DB
$env:PGUSER = $env:POSTGRES_USER
$env:PGPASSWORD = $env:POSTGRES_PASSWORD
$env:PGSSLMODE = 'require'
```

Store all three secrets plus UUID in the approved secret store now, without
printing env listings. These values must persist unchanged across migration,
stamp, seed, Render configuration and relogin. This generation is for a NEW
unstamped database only; never rotate a stamped identity in place. Remove stale
PGSSLROOTCERT/PGSERVICE overrides from this isolated process if inherited from
another environment, after reviewing their origin.

## 3. PostgreSQL administration — read-only target and emptiness verification

From that same local PowerShell terminal:

```powershell
@'
\set ON_ERROR_STOP on
SELECT current_database() = :'demo_database'
 AND current_database() ~ '^navapack_demo_[a-z0-9_]{8,48}$' AS target_ok \gset
\if :target_ok
SELECT current_database(), current_user, pg_get_userbyid(datdba) AS database_owner,
       inet_server_addr(), current_setting('server_version') AS version
FROM pg_database WHERE datname=current_database();
SELECT ssl, version, cipher FROM pg_stat_ssl WHERE pid=pg_backend_pid();
SELECT NOT EXISTS(SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
 WHERE n.nspname='public' AND c.relkind IN ('r','p','v','m','S','f')) AS empty_ok \gset
\if :empty_ok
\echo 'Fresh public application schema verified; confirm recorded host/owner/version/TLS.'
\else
\echo 'STOP: target is not empty. Do not reuse this initialization procedure.'
\quit 3
\endif
\else
\echo 'STOP: wrong target'
\quit 3
\endif
'@ | psql -X --no-password -v ON_ERROR_STOP=1 -v "demo_database=$env:POSTGRES_DB"
if ($LASTEXITCODE -ne 0) { throw 'Target verification failed' }
```

Confirm returned host/database/owner against the approval and ssl=true. No result
from this query authorizes migration by itself. If unexpected application schemas
other than public exist, stop for DBA review as well.

## 4. Local operator terminal — backup, rehearsal and reviewed migration plan

Use a new protected access-controlled evidence directory for the custom dump
(sensitive even when empty). The initial backup cannot use demo_backup.py yet:
that exporter requires an already stamped restricted runtime environment.

```powershell
$EvidenceDir = Read-Host 'Existing protected operator evidence directory, outside Git'
$Dump = Join-Path $EvidenceDir ('before-init-' + [guid]::NewGuid().ToString('N') + '.dump')
if (Test-Path -LiteralPath $Dump) { throw 'Refusing backup overwrite' }
pg_dump --format=custom --no-owner --no-privileges --file "$Dump"
if ($LASTEXITCODE -ne 0) { throw 'Backup failed; stop' }
Get-FileHash -Algorithm SHA256 -LiteralPath $Dump
pg_restore --list "$Dump"
if ($LASTEXITCODE -ne 0) { throw 'Backup archive invalid; stop' }
& $Python manage.py check --deploy --fail-level WARNING
if ($LASTEXITCODE -ne 0) { throw 'Settings check failed' }
& $Python manage.py migrate_demo --database $env:DEMO_DATABASE_NAME
if ($LASTEXITCODE -ne 0) { throw 'Migration plan failed' }
```

Retain the plan's complete forward_plan and plan_sha256 with the backup digest,
actual provisioning record and tested source revision. pg_restore --list validates
archive readability, NOT a completed restore test. Before approving the hosted
apply, restore this archive into a separately approved disposable empty clone and
rehearse the same revision's forward migrations using that clone's OWN name and
plan digest. Never use --clean or restore into this target/existing database.
The current demo_restore.py intentionally requires strict verify-full recovery
settings; it is not an internal-TLS bootstrap bypass. The clone rehearsal is a
separate approved DBA/test task; its identity/credentials must not be this service.

In a SEPARATE fresh local test terminal using approved local test PostgreSQL
credentials (not any Render variables), run the existing isolated regression:

```powershell
Set-Location F:\WORK\Navapack-ERP\backend
$env:DJANGO_SETTINGS_MODULE = 'config.settings.test'
.venv/Scripts/python scripts/test_isolated.py --synthetic-ledger tests
```

This generated local database test is additional regression evidence, not proof
of the hosted target's permissions or successful restore. Complete and approve
the clone/backup evidence before proceeding. No invented approval reference counts.

## 5. Local operator terminal — apply reviewed forward migrations as owner

After explicit identity/backup/restore/revision/plan approval, in the ORIGINAL
owner terminal, set ReviewedPlan to the exact plan_sha256 printed in step 4:

```powershell
$ReviewedPlan = Read-Host 'Approved target-specific plan_sha256'
& $Python manage.py migrate_demo --database $env:DEMO_DATABASE_NAME --apply-plan $ReviewedPlan --backup-reference $BackupRef --approval-reference $ApprovalRef
if ($LASTEXITCODE -ne 0) { throw 'Migration failed; stop and preserve evidence' }
```

Do not retry blindly, replace the hash automatically, downgrade, disable triggers
or delete anything on failure. This command checks the actual current_database,
exact current forward plan digest and nonempty evidence references, then calls
the existing Django migrate operation. Approval/backup refs are evidence links;
the command does not perform a backup or independently verify external approval.

## 6. PostgreSQL administration — create a NEW restricted runtime login

As approved owner/role administrator on this verified target, create this exact
new role. Do not reuse or ALTER an unknown existing role. If role creation or
required restrictions are unsupported by the managed account, NO-GO; do not use
the managed owner as the application user.

```powershell
psql -X --no-password -v ON_ERROR_STOP=1
```

Inside psql (SQL and psql commands, not PowerShell):

```sql
SELECT current_database(), current_user;
CREATE ROLE navapack_demo_runtime LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
\password navapack_demo_runtime
SELECT rolname, rolcanlogin, rolsuper, rolcreatedb, rolcreaterole, rolinherit, rolbypassrls
FROM pg_roles WHERE rolname='navapack_demo_runtime';
SELECT count(*) AS must_be_zero FROM pg_auth_members
WHERE member=(SELECT oid FROM pg_roles WHERE rolname='navapack_demo_runtime');
\q
```

The password prompt hides the new independent runtime password. Store it securely.
It must differ from the owner password. No ALTER DEFAULT PRIVILEGES or GRANT ALL.

## 7. Local operator terminal — stamp once, then grant reviewed privileges

Remain connected as migration owner, with the same instance and execution secret:

```powershell
& $Python manage.py approve_demo_boundary --database $env:DEMO_DATABASE_NAME --instance $env:DEMO_INSTANCE_ID --runtime-role $RuntimeRole --days 30 --approval-reference $ApprovalRef --backup-reference $BackupRef
if ($LASTEXITCODE -ne 0) { throw 'Stamp failed; stop' }
psql -X --no-password -v ON_ERROR_STOP=1 -v "demo_database=$env:DEMO_DATABASE_NAME" -v "demo_runtime_role=$RuntimeRole" -f scripts/demo_runtime_grants.sql
if ($LASTEXITCODE -ne 0) { throw 'Runtime grants failed; stop' }
```

Stamp refuses preexisting marker, owner=runtime, bad runtime attributes/memberships,
wrong target/UUID, expiry outside 1–90 days or nonempty key application tables.
Expiry and identity are immutable: no manual UPDATE/DELETE or in-place extension.
The grants template preserves stock/audit/QC triggers and grants no inventory posting.

## 8. Optional approved seed — local owner terminal only

An empty backend can pass readiness but has no login accounts or demo journey.
For the existing synthetic accounts and complete journey, obtain separate seed
approval and prepare two distinct strong password files in an approved private
directory outside Git. The command requires actual files containing passwords;
do not pass passwords as CLI arguments. No createsuperuser or Admin grants.

On PostgreSQL 16+, the seed owner must be able to SET ROLE to runtime. If it cannot,
the role administrator may grant runtime TO owner (never the reverse):

```powershell
@'
GRANT :"demo_runtime_role" TO :"demo_owner_role" WITH SET TRUE, INHERIT FALSE;
'@ | psql -X --no-password -v ON_ERROR_STOP=1 -v "demo_runtime_role=$RuntimeRole" -v "demo_owner_role=$OwnerRole"
if ($LASTEXITCODE -ne 0) { throw 'Owner SET ROLE grant failed' }
$MakerFile = Read-Host 'Protected synthetic maker password file path'
$ReviewerFile = Read-Host 'Protected synthetic reviewer password file path'
& $Python manage.py seed_demo --database $env:DEMO_DATABASE_NAME --generation demo01 --maker-password-file $MakerFile --reviewer-password-file $ReviewerFile --approval-reference $ApprovalRef
if ($LASTEXITCODE -ne 0) { throw 'Seed failed; stop' }
```

Seed generation must be lowercase letters/digits, 1–16 chars; same generation is
a no-op. Accounts are demo-maker+demo01@example.invalid and
demo-reviewer+demo01@example.invalid, with explicit bounded capabilities and
independent scopes. Runtime itself must STILL have zero role memberships.
Follow the approved handling procedure for temporary password files; never commit.
PostgreSQL role membership syntax: https://www.postgresql.org/docs/16/sql-grant.html

## 9. Local terminal — switch to runtime and verify actual gates

```powershell
$RuntimePassword = Read-Host 'Approved runtime password' -AsSecureString
$env:POSTGRES_USER = $RuntimeRole
$env:POSTGRES_PASSWORD = [System.Net.NetworkCredential]::new('', $RuntimePassword).Password
$env:PGUSER = $env:POSTGRES_USER
$env:PGPASSWORD = $env:POSTGRES_PASSWORD
psql -X --no-password -v ON_ERROR_STOP=1 -c "SELECT current_database(), current_user, environment, database_name, instance_id, runtime_role, expires_at, expires_at > CURRENT_TIMESTAMP AS unexpired, approval_reference, backup_reference FROM core_demoboundary WHERE singleton;"
if ($LASTEXITCODE -ne 0) { throw 'Runtime marker read failed' }
& $Python manage.py deployment_diagnostics
if ($LASTEXITCODE -ne 0) { throw 'Runtime readiness guard failed' }
& $Python manage.py shell -c "from apps.core.demo import require_demo_environment; require_demo_environment(); print('DEMO database identity, secret, expiry and restricted-role checks passed')"
if ($LASTEXITCODE -ne 0) { throw 'Runtime boundary failed' }
psql -X --no-password -v ON_ERROR_STOP=1 -c "SELECT has_schema_privilege(current_user,'public','CREATE') AS must_be_false, has_table_privilege(current_user,'inventory_ledgerentry','INSERT') AS ledger_insert_must_be_false, has_table_privilege(current_user,'core_demoboundary','UPDATE') AS stamp_update_must_be_false;"
if ($LASTEXITCODE -ne 0) { throw 'Privilege read failed' }
```

Inspect all three privilege results: false required. deployment_diagnostics checks
pending migrations and the actual full Python boundary, including no DB/schema/
public-table ownership, no memberships/admin flags, exact secret hash and UUID.
Do not print require_demo_environment()'s return value: it is the execution secret.
Do not treat a bare SQL navapack_demo_context()=false as failure: its transaction
nonce is intentionally absent outside a controlled demo command.

## 10. Render Dashboard — runtime environment, start and health/readiness

Copy the complete checklist's nonsecret values and secrets from the secret store.
POSTGRES_USER/PASSWORD are the RESTRICTED RUNTIME login, never the migration owner.
Use the direct internal host; DB name, UUID and all three secrets must match the
operator process/stamp exactly. Keep APP_ENV=DEMO and SSLMODE=require. Never add
SYNTHETIC_LEDGER flags. Configure the source revision including render_demo.py.

```text
Root Directory: backend
Branch: main (verify the approved deployed SHA)
PYTHON_VERSION: 3.12.12
Build: pip install -r requirements/production.txt && python scripts/check_render_demo.py
Start: waitress-serve --listen=0.0.0.0:$PORT --url-scheme=https config.wsgi:application
Health Check Path: /api/v1/ready/
Auto-deploy: off
```

The offline build check validates dummy config, not service runtime credentials.
After all GO criteria below and explicit deployment approval, manually deploy the
reviewed commit. A failing ready check is a blocker; do not change it to liveness
merely to obtain a green deployment.

Local PowerShell, after deployment (replace hostname):

```powershell
$Api = 'https://navapack-demo-api.onrender.com'
curl.exe --fail --show-error "$Api/api/v1/health/"
if ($LASTEXITCODE -ne 0) { throw 'Liveness failed' }
curl.exe --fail --show-error "$Api/api/v1/ready/"
if ($LASTEXITCODE -ne 0) { throw 'Readiness failed' }
```

Expect HTTP 200 and {"status":"ok"}/{"status":"ready"}. If approved seed completed,
run the existing smoke test using the SAME UUID and protected maker password file:

```powershell
& $Python scripts/smoke_hosted_demo.py --api-url "$Api/api/v1" --instance $env:DEMO_INSTANCE_ID --email 'demo-maker+demo01@example.invalid' --password-file $MakerFile
if ($LASTEXITCODE -ne 0) { throw 'JWT/demo identity smoke failed' }
```

This verifies JWT, demo identity, operational-record isolation, refresh and logout;
authentication writes token/throttle records. The full synthetic journey adds
persisted demo data and needs separate explicit exercise approval:

```powershell
$ExerciseApproval = Read-Host 'Approved synthetic full-journey exercise reference'
if (-not $ExerciseApproval) { throw 'Exercise approval required' }
& $Python scripts/smoke_hosted_demo.py --api-url "$Api/api/v1" --instance $env:DEMO_INSTANCE_ID --email 'demo-maker+demo01@example.invalid' --password-file $MakerFile --exercise --approval-reference $ExerciseApproval
if ($LASTEXITCODE -ne 0) { throw 'Synthetic journey smoke failed' }
```

Complete rendered UI acceptance as well. No health endpoint proves full ERP workflow
acceptance. None of these HTTP tests has been executed against a hosted target.

## Final GO / NO-GO before redeployment

- [ ] Approved NEW database host/name/owner/region/cost; no existing or production DB.
- [ ] Exact reviewed code revision; complete secret-store environment; distinct keys.
- [ ] Initial backup digest and successful disposable clone restore/rehearsal evidence.
- [ ] Approved target-specific forward-plan hash applied successfully as owner.
- [ ] Restricted runtime role, no ownership/memberships/admin flags; grants reviewed.
- [ ] Immutable stamp matches actual DB, runtime, UUID and secret; expiry sufficient.
- [ ] Full runtime deployment_diagnostics and explicit permission checks pass.
- [ ] Synthetic seed/accounts approved if client login/journey is required.
- [ ] Owner credentials absent from Render web environment; internal endpoint selected.
- [ ] Explicit release approval for exact commit, with failure/backup recovery plan.

Any unchecked prerequisite is NO-GO. After authorized deployment, both endpoints
must pass and JWT/browser acceptance must complete before declaring client-demo GO.
This never grants production, stock, QC release, tax, dispatch or invoicing authority.

Preparation validation: inspected migrate_demo, approve_demo_boundary, seed_demo,
demo_runtime_grants.sql, deployment_diagnostics, the Python/SQL boundary and Render
settings. Queried actual management-command and smoke-script --help for argument
names. git diff --check passed. No creation/migration/stamping/grant/seed/backup,
hosted HTTP request, deployment, commit or push was executed in preparing this guide.
