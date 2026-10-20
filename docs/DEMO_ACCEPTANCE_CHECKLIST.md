# Hosted DEMO acceptance checklist

State legend: implemented = source present; tested = executed locally; prepared =
reviewable configuration/procedure; deployed = remote service actually running.
No deployment or hosted database migration has been performed.

## Required automated/local evidence

- [x] Independent persistent DEMO Python/SQL context; original ledger gate unchanged.
- [x] Additive migration, immutable identity, restricted runtime grants and synthetic seed.
- [x] Disposable persistent clone test: full commercial/production seed, real JWT,
  new database connections, relogin, no operational stock/QC postings, custom dump/
  independent restore and restored identity fail-closed. Initial run passed in 16.574s;
  final hardened concurrency/settings runs are recorded below.
- [x] Original synthetic compatibility focused run: 11 tests passed in 37.234s.
- [x] Frontend TypeScript, Vite build (1741 modules) and original 16 check scripts passed;
  new hosted-demo build-configuration check also passed (17 checks total).
- [x] Final complete isolated PostgreSQL regression: **308 tests PASS in 1070.929s**.
- [x] Persistent-demo clone/concurrency/security/settings/upgrade: 3 tests passed in
  194.045s; actual exporter/logical-reset extension: 1 test passed in 52.865s.
- [x] Django checks and migration drift passed: no issues / no changes detected.
- [ ] Linux Docker build/start — daemon unavailable; not claimed tested.

Commands from backend:

```sh
.venv/Scripts/python scripts/test_isolated.py --synthetic-ledger
.venv/Scripts/python scripts/test_isolated.py --synthetic-ledger tests.test_demo_environment tests.test_demo_settings tests.test_phase3e_rehearsal
.venv/Scripts/python manage.py check
.venv/Scripts/python manage.py makemigrations --check --dry-run
```

Linux uses the corresponding virtualenv Python path. Tests generate and remove only
their stamped test DBs and named demo clones; no configured application DB migrations.
Protected temporary seed password files are removed by the tests. Failure logs remain
ignored under backend/.local. Final exact counts/timings follow below.

## Manual approvals before hosting

- [ ] Approve Git diff/checkpoint and separate commit/push.
- [ ] Approve Render tier/cost/region, exact API hostname and dedicated DB identity.
- [ ] Approve backup/hash/restore evidence and exact forward migration plan.
- [ ] Approve restricted runtime role, independent synthetic accounts, secret delivery,
  scope expiry and logical-reset generation procedure.
- [ ] Approve Vercel demo project/domain/environment; preserve current live services.
- [ ] Review Docker/image digest, dependency scan and Linux runtime results.

## Hosted smoke / rendered acceptance — not executed without deployed endpoints

- [ ] `/health/` and `/ready/` healthy; expired/wrong marker readiness 503.
- [ ] HTTPS-only login/application requests, exact hosts, CORS and CSRF origins;
  rejected unapproved origins/hosts, no wildcard credential exposure.
- [ ] Real JWT login, refresh, logout/relogin, saved records after restart/refresh.
- [ ] Customer → two products → costing → draft quote → order demand → rehearsal
  route/stages → failed QC/reinspection → finished goods → simulated dispatch → draft invoice.
- [ ] Customer-free production-for-stock → finished goods; dispatch/invoice rejected.
- [ ] Two concurrent edits produce one winner; stale inputs retained; retry keys safe.
- [ ] Exact decimals, units/specifications/source hashes and immutable history retained.
- [ ] Operational ledger/balance/QC authorization/finance counts unchanged; no email sent.
- [ ] Draft watermarks on screen and every printed page; browser/PDF visual QA.
- [ ] Owner credentials absent from web service; runtime cannot change stamp/roles,
  own tables, disable triggers or execute operational inventory commands.
- [ ] Protected export restored into empty alternate DB, triggers/hashes checked,
  restored marker denied, rollback reviewed.
- [ ] Logical reset retires old synthetic accounts without deleting history.

Local browser control was disabled in the prior session; no rendered-control acceptance
is inferred from adapter tests. No hosted URL, account or resource was invented.
Production release remains NO-GO. Hosted demo release remains pending the unchecked
platform/approval/hosted acceptance gates even when local automated tests are green.

## Prepared hosted smoke command (not executed remotely)

First run read-only boundary/auth checks with the approved HTTPS URL and protected
synthetic password file:

```sh
python scripts/smoke_hosted_demo.py --api-url https://<approved-host>/api/v1 --instance <approved_uuid> --email demo-maker+demo01@example.invalid --password-file <protected_file>
```

Only after explicit write-test approval, append `--exercise --approval-reference <id>`.
This verifies the authenticated DEMO instance and zero operational records before
creating a fresh two-product commercial/rehearsal journey, concurrent review conflict,
failed QC/reinspection, simulated dispatch, history and fresh-login persistence.
Refresh/logout are checked; redirects never forward credentials. No customer email,
operational stock or legal invoice is issued. No HTTPS endpoint was deployed here,
so this script is prepared rather than claimed as a hosted test pass.

GitHub manual validation workflow `.github/workflows/demo-validation.yml` is prepared,
not executed. It needs an approved `DEMO_CI_POSTGRES_PASSWORD` repository secret for
its isolated ephemeral PostgreSQL service. It never deploys. Review/pin action/image
digests before enabling online; no GitHub setting/secret was changed in this session.

## Final focused verification evidence

- `tests.test_demo_environment tests.test_demo_settings tests.test_phase3e_rehearsal`: **3 tests PASS in 194.045 seconds** (`backend/.local/demo-release-focused.log`). Verifies nonowner/no-membership runtime, seeded persisted journey, JWT/relogin/reconnect, one-winner concurrency, bad-secret readiness 503, operational gate denial, restore/trigger preservation and strict deployment settings.
- Actual protected exporter + logical reset: **1 test PASS in 52.865 seconds** (`backend/.local/demo-seed-reset-export-tests.log`). Old accounts revoked, old records retained.
- Final extended boundary test: **1 test PASS in 31.343 seconds** (`backend/.local/demo-boundary-release-tests.log`). Adds actual migration-plan controller hash refusal/application, SQL wrong-nonce denial with SQLSTATE 42501, authenticated demo status, actual protected export, restore and logical reset.
- Initial focused failures are retained, not counted as passes: missing column-level lock privilege was corrected while revision mutation triggers stayed intact; HSTS startup warnings were corrected by retaining production defaults; a nested Django test-settings override was fixed to preserve SETTINGS_MODULE and test bad-secret behavior correctly.
- `manage.py check`: no issues. `manage.py makemigrations --check --dry-run`: no changes detected. Neither applies configured DB migrations.
- Frontend TypeScript and production build passed, 1741 modules; hosted-demo build also passed with process-local HTTPS API URL, mock login false and VITE_HOSTED_DEMO=true. Original 16 scripts and new hosted config check passed (17 total). Existing large-bundle warning remains.
- Docker CLI 29.8.1 present; Linux daemon unavailable. Gunicorn 26.2.0 dependency installed; Linux image/server startup not claimed tested.
- Full regression result will be recorded below after completion. No hosted URL, configured DB migration, GitHub push, paid resource provisioning or live setting change occurred.

## Final result

Complete isolated PostgreSQL regression **308 tests PASS in 1070.929 seconds**,
exit 0 (`backend/.local/hosted-demo-full-regression.log`). Generated stamped database
`test_phase3b_357257b1425547979373ae4209da297b` was destroyed by its runner. Includes
original JWT/security, audit rollback, concurrent/idempotent commands, inventory/QC,
commercial/rehearsal HTTP adapters, populated upgrade/restore and new DEMO clone/settings tests.

Subsequent extended DEMO boundary/export/reset test also passed: **1 test in 31.343s**,
including final migration-controller/wrong-nonce/status/reset checks. All **17** frontend
scripts passed after the final config change; TypeScript and hosted-mode Vite build passed
(1741 modules, 4.99s Vite build). Django check/drift and Git whitespace checks passed.
POSIX shell syntax check passed. All 28 client originals matched SHA256 again.

Original ledger guard file has no diff; no historical migration was rewritten.
All test-owned clones, temporary restore databases, runtime roles and password files
were cleaned by their owning tests. Read-only inventory checked cleanup; no unknown
database/process was deleted. No source was staged, committed, pushed or deployed.
No configured/hosted application database was migrated or granted permissions.

**Preparation: complete for review. Local automated validation: PASS. Hosted demo
release: pending identity/cost/backup/migration approval, Linux image/runtime validation,
real Render/Vercel TLS/role setup and hosted/browser smoke acceptance. Production: NO-GO.**


Temporary Render native Python deployment: see [Render demo setup](RENDER_DEMO_SETUP.md).
Its explicit render_demo profile uses required TLS without a custom CA; the strict
demo/production and recovery profiles retain their original TLS policies.
