# Reproducible Phase 2 / 2.1 release plan

20 October 2026. Preparation only. No staging, commit, push, remote edit or deployment
was performed. All pre-existing working-tree changes were retained.

## Current release state

Branch main; HEAD and cached origin/main at
800dd00ba2f103c440130c8ae597ad0c4d8dc283. Remote is
https://github.com/Careergize/ERP-Navapack-frontend.git. This monorepo uses that existing
identity; do not rename/remap it silently. No fetch was performed, so the cached remote
tracking ref is not a live remote verification. core.autocrlf=true on this Windows host.

Phase 2 accounts extensions, domain apps/migrations, tests and documentation were
already largely untracked at remediation start. Remediation builds on that working
tree. HEAD alone cannot reproduce Phase 2. Git status must be reviewed as a whole,
not only `git diff` (which omits untracked files). No final release SHA exists yet.

## Reviewable sequence requiring approval before Git writes

1. Preserve/copy the working tree and record status, HEAD, remote identity and an
   approved source manifest. Compare Phase 1 migrations with HEAD; retain all applied
   Phase 2 migrations byte-for-byte. Review all modified and untracked source files.
2. Confirm the intended repository owner/remote, branch protection and frontend
   deployment branch/root configuration with the owner. See MONOREPO_MIGRATION.md.
   Do not trigger a build/deployment or remote/branch cutover during review.
3. Review Phase 2 baseline plus Phase 2.1 as separate logical change groups. Because
   baseline work was never committed, obtain its owner's explicit review; do not
   attribute all dirty files to remediation. Include every app, __init__.py, migration,
   config registration, backend test, docs and scripts/test_isolated.py in the approved
   release manifest. Leave unrelated existing work intact.
4. In a clean isolated checkout created only after approval, install backend locked
   requirements and frontend `npm ci` independently. Supply private test configuration
   outside version control. Run the checks below against a dedicated local PostgreSQL
   cluster; never point the isolated runner at production or share its DB role.
5. After review, request explicit approval to stage/commit the agreed manifest. Inspect
   the index and secret scan before commit; never use broad `git add .`. Capture the
   immutable commit SHA and checks from a clean checkout. Pushing and deployment need
   separate authorization. Until then this is a working-tree candidate, not a release.

## Independent verification commands

From backend (Python environment installed from requirements/lock.txt):

```powershell
.venv/Scripts/python manage.py check --settings=config.settings.test
.venv/Scripts/python manage.py makemigrations --check --dry-run --settings=config.settings.test
.venv/Scripts/python manage.py migrate --plan --settings=config.settings.test
.venv/Scripts/python scripts/test_isolated.py
.venv/Scripts/python scripts/test_isolated.py tests.test_phase21_imports tests.test_role_capabilities
```

The runner checks local PostgreSQL, allocates a UUID-named absent test DB and lets
Django create/migrate/destroy only that test DB. It does not migrate the configured
application DB. Interactive creation prevents automatic deletion if an external
process unexpectedly races database creation. Inspect failure output before cleanup;
never destroy an arbitrary pre-existing test DB. Release checks must also rehearse
upgrade from the prior migration state on a disposable copy before deployment.

From frontend (no source edits needed):

```powershell
node ./node_modules/typescript/bin/tsc --noEmit
npm run build
Get-ChildItem scripts/check-*.mjs | Sort-Object Name | ForEach-Object {
  node $_.FullName
  if ($LASTEXITCODE -ne 0) { throw "Failed $($_.Name)" }
}
```

Run production settings `check --deploy` using explicitly approved deployment
configuration and trusted DB TLS before release. A synthetic settings check is not
deployment verification. No root package manager or combined deployment is introduced.

## Forward migration and operational gates

New accounts 0004/0005 and imports 0005/0006 must follow existing migration history.
They add review/version fields and append-only guards; they do not seed grants/users
or rewrite existing audit, source rows or openings. Existing reviewed imports have
no canonical review and must be reviewed again. Existing applied imports are retained
as legacy evidence; no applied plan is fabricated retrospectively.

No automatic grant of new governance permissions to existing administrators. Arrange
explicitly approved trusted account provisioning/maintenance for at least two distinct
Master Admins and verified delegation ceilings. Inventory legacy roles without current
assignment policies; review/migrate before operational release. Use governed revision
APIs for changes to live business roles. Restrict runtime database rights; trusted
out-of-band catalog writers must acquire catalog lock 70462027 and admin writers
70462026 in their transaction, before row locks. Direct DBA/SQL writes are privileged
maintenance, not a supported unaudited substitute for API commands.

Keep .env/secrets, .venv, .local/PostgreSQL data, node_modules, dist, logs, temporary
probes and .migration-backup excluded. Verify with git check-ignore and inspect the
approved index. Do not seed mock reference stock. Backup/restore, append-only guard
permissions, rollback/recovery, TLS/ingress and migration rehearsal require operational
approval. Prefer forward repair; never edit historical migrations or delete evidence.

The frontend adapter corrections remain a separate authorized scope. Do not release
the current frontend as integrated with these APIs. Client SOP/authority/source and
inventory policy gates in the remediation report remain open before Phase 3.
