# Phase 3 release readiness

20 October 2026. **CONDITIONAL GO for synthetic development closure; NO-GO for production posting or QC release.** The automated integration/recovery evidence is complete; browser acceptance remains incomplete because local browser use is disabled. Passing tests are not management or production authorization.

## Verified development evidence

- Final complete PostgreSQL regression: 251 passed, including the 11 JWT/API acceptance cases and one populated upgrade/recovery case.
- Django checks and schema drift pass; TypeScript/build/all 13 frontend scripts pass.
- All 28 client originals preserved. Existing audit, exact decimal, physical-source, authorization, concurrency and synthetic guards retained.
- No application migrations applied. Final configured plan equals baseline: 20 pending. No new Phase 3E migrations.
- Disposable databases and temporary runtime/synthetic roles absent at cleanup; project browser backend/Vite/test cluster stopped, unrelated services preserved.

## Configured pending dependency order

The following topological sequence was rehearsed in disposable PostgreSQL. It is a plan, not authorization to execute it on the application database:

1. `accounts.0004_alter_role_options_role_governed_role_updated_at_and_more`
2. `accounts.0005_immutable_capability_reviews`
3. `core.0003_auditevidence`
4. `core.0004_protect_audit_evidence`
5. `imports.0005_importbatch_applied_plan_importreview_and_more`
6. `imports.0006_immutable_reviews`
7. `inventory.0001_initial`
8. `inventory.0002_configuration_guards`
9. `inventory.0003_warehouse_custody_department`
10. `inventory.0004_alter_warehouse_options`
11. `inventory.0005_stockidentity_source_document_reference_and_more`
12. `inventory.0006_postingpolicy_ledgerapproval_sourceevent_and_more`
13. `inventory.0007_synthetic_ledger_guards`
14. `inventory.0008_operationrequest_operationline_operationdecision_and_more`
15. `inventory.0009_operation_guards`
16. `inventory.0010_operationrequest_cutoff_basis_physicalsourcedocument_and_more`
17. `inventory.0011_physical_source_guards`
18. `inventory.0012_qc_foundation`
19. `inventory.0013_qc_guards`
20. `inventory.0014_qc_action_evidence`

Use Django's dependency graph on the final reviewed source; do not manually reorder SQL or rewrite immutable migrations. Another valid topological order may exist. The recorded `showmigrations --plan` is the configured database evidence.

## Reproducible disposable rehearsal

From `backend/`, use existing local PostgreSQL configuration, a loopback-only isolated cluster and a disposable-test database owner with CREATEDB. Never substitute production credentials. Run `.venv/Scripts/python scripts/test_isolated.py --synthetic-ledger tests.test_phase3e_rehearsal`; the runner generates an absent random database, installs migrations and stamps its nonce. The test validates clean install, representative historical data upgrade, conserved QC/stock state, enabled protection triggers and independent restore fingerprints normalized to UTC. Both databases are removed. Run the full runner without labels for all 251 tests. Existing dependencies include PostgreSQL 16 tools `pg_dump`/`pg_restore`; no new packages were installed.

For browser acceptance use `scripts/serve_synthetic_acceptance.py --help`, then its mandatory `--disposable-synthetic-only` flag and bounded lifetime. It accepts neither an existing database nor an externally supplied nonce. Bind Vite/Django to loopback, set mock login false for that process, use only fixture accounts, and stop through the generated stop file. Do not persist synthetic environment settings in operational configuration. Browser testing is still outstanding.

## Future upgrade and recovery checklist — not executed on production

- First authorize a reviewed source checkpoint, migration window, responsible DBA and release owner. Preserve untracked files; no staging/commit is authorized by this report.
- Back up the actual target with schema, data, roles/grants and deployment configuration; protect backup credentials/evidence. Prove restoration into an isolated instance before change. Approve retention, recovery objectives and audit retention/export separately.
- Inspect the target's real data against all new uniqueness/check constraints and role/audit assumptions. The synthetic legacy sample does not certify every populated target. Check locks, table sizes and available storage. Never fabricate missing historic approvals or evidence.
- Separate migration-owner privileges from a nonowner runtime role. Migrations require schema/table/sequence/function/trigger creation and appropriate ownership; runtime must have only required reads/inserts/allowed updates, not schema ownership, superuser, TRUNCATE, trigger-disable or audit/ledger UPDATE/DELETE rights. Validate actual grants in a staging clone using the maintained restricted-role tests and PostgreSQL ACL inspection. Production roles were not provisioned here.
- Quiesce application writes for a consistent backup/migration boundary; apply the approved graph using a migration identity, then run health/readiness, drift, constraints, immutable audit and authorization checks. Keep synthetic execution disabled and do not create a test stamp in the application database.
- If migration/release validation fails, preserve failure evidence and restore the approved backup to an isolated recovery target; validate normalized row fingerprints, audit chain/history, projections, grants and triggers before a separately approved cutover. Do not reverse populated immutable ledger migrations as a recovery shortcut.
- No operational posting feature flag may be enabled merely because schema installation succeeds. A future operational engine/release requires explicit policy, security and application approval beyond this synthetic foundation.

## Client and deployment gates

- **Client decision:** named independent inventory/QC authorities, delegations/ceilings and separation of Stores, Procurement, QC, managerial/commercial approval.
- **Client decision:** warehouse ownership/custody, offsite locations and governed employee warehouse-scope provisioning/revocation.
- **Client decision:** reconciled opening cutoff, quantities/evidence and approval; item units and any actual approved conversions.
- **Client decision:** inspection specifications/criteria/sampling; physical lot/portion marking and segregation; disposition/concession authority; safe future partial/split/merge rules.
- **Client decision:** authoritative upstream source/document-line registry, allocation policy, backdating/period close and historical count reconciliation.
- **Client decision:** documented operational SOP adoption/cutover; originals retain 1 November 2026 effective dates.
- **Deployment readiness:** complete browser acceptance for all workflow/error/role/history states, reviewed reproducible Git checkpoint, nonowner runtime role and migration-owner separation, TLS/secrets, backup/recovery/retention, monitoring and immutable audit export.

Do not begin Phase 4 or live pilot posting under this recommendation. Close the browser acceptance gap in a disposable environment and obtain the relevant approvals before claiming unconditional Phase 3 closure or production readiness.
