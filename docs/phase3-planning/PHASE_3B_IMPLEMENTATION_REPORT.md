# Phase 3B implementation report

20 October 2026, Asia/Kolkata. Bounded user-authorized synthetic-only development. No operational posting, application migration, real grants, opening import, commit/push/deployment or Phase 3C–3E scope is authorized.

## Audit remediation gate — completed before ledger implementation

Core AuditEvidence now stores bounded sanitized full change payload and SHA-256 behind the existing scoped AuditEvent reader. The summary remains bounded at4000 encoded bytes; larger summaries reference durable evidence rather than truncate values. Full evidence has a256KiB application bound, structural/depth limits and a512KiB PostgreSQL representation bound, with additive append-only guards. API consumers resolve full detail only after event scope authorization. Ordinary authorization wording is valid. Sensitive keys are redacted structurally; explicit credential/header assignments and recognizable JWT/Bearer/Basic values are redacted. Free text cannot semantically identify an arbitrary unlabeled password: callers remain responsible for controlled business schemas, never arbitrary request bodies.

Permanent audit regression gate:27 tests passed in31.677s against fresh disposable PostgreSQL before ledger code began. Covers multi-role overflow/full old-new preservation/scoped reads, normal wording, actual credential redaction, evidence bounds/immutability and audit-evidence failure rolling back the entire command. No historical audit payload is fabricated or rewritten.

## Adopted identity/custody contract — recorded before ledger schema

User-directed technical decision: StockIdentity is immutable registration identity/provenance. Existing warehouse/location retain historical registration meanings and are never updated by transfers. Custody keys separately identify exact stock identity, current StorageLocation, primary Unit, immutable ownership fingerprint and quality partition. One root identity can have quantities across authorized custody locations. Parent registration relations create no quantity; independently posting child/portion registrations is blocked until a conserved split engine is approved.

Compatibility finding: Phase3A identity/history APIs scope by registration warehouse. Reusing their full serializers for destination users would either deny legitimate custody or disclose origin evidence. They will remain registration-scoped. The internal synthetic custody reader will authorize the destination warehouse and return only minimal identity plus that warehouse's custody entries; no original source/registration location or counterparty-location data. Ledger audit is a separate entity type excluded from the existing global Admin reader and from Phase3A configuration history. No public custody/posting API is planned for3B.

Scope publication/revocation remains unimplemented. Only disposable test fixtures may provide scopes, policy/approval evidence and exact synthetic quantities. No real approvals or business role grants are inferred.

The implemented ledger conservatively rejects backdated events, unknown opening coverage, unresolved owner/custody and unauthorized/held issues. Numeric storage/policy examples are test contracts, not approved client precision. Corrections/reversals compensate current history, never rewrite a posted quantity. Operational opening correction remains a future separately governed workflow.

## Actual schema and migration inventory

Core migrations0003_auditevidence and0004_protect_audit_evidence add UUID AuditEvidence, protected one-to-one AuditEvent, sanitized JSON payload, SHA-256, server timestamp, ORM append-only guards, PostgreSQL UPDATE/DELETE trigger and storage bound. Existing core0002 audit protection is reused, not rewritten. Every new record_event call creates event and evidence together; historical events remain unchanged.

Inventory0006_postingpolicy_ledgerapproval_sourceevent_and_more adds eight UUID models:

- PostingPolicy: unique synthetic reference, explicit version, synthetic-only check, rules JSON and content digest. Append-only evidence; a new policy requires a new record/reference, not editing an old rule.
- SourceEvent: system/event_key and exact intent hash; database unique physical-event pair independent of actor or retry key. One posted header per source; orphan sources cannot commit.
- LedgerApproval: independent maker/approver protected User FKs, policy, exact intent hash, decision and controlled reference. These are synthetic fixture attestations only. No approval/rejection endpoint, decision publisher or real business authority is implemented.
- LedgerTransaction: immutable posted header with source, policy, actor, optional one-use approval, kind, version1, effective timestamp, safe reason, optional original/reversal links, recorded timestamp and PostgreSQL transaction ID. Header is created only during atomic posting; a request or draft does not become a stock transaction.
- TransactionLine: sealed sequence, typed StockIdentity/Unit, source/destination locations, nonnegative exact quantity, HELD/RELEASED bucket and optional original-line reference. Positive amount except an explicit zero OPENING. Stock item is reached through existing typed identity; no generic foreign key or competing item master.
- LedgerEntry: append-only signed custody leg, header/line, sequence, stock/location/unit/ownership/quality, stable SHA-256 account key, effective and recorded times. Transfers have equal opposite legs; posted lines cannot receive late entries.
- BalanceProjection: versioned derivative per exact stock/location/unit/ownership/quality key, nonnegative quantity and last transaction. It is not a writable stock-management API.
- OpeningCoverage: versioned scope per stock/location/unit/ownership, explicit UNKNOWN or KNOWN with original opening quantity/transaction. Missing row is unknown. KNOWN evidence is immutable; a correction never replaces the opening quantity.

Quantities use PostgreSQL numeric(20,6). Services accept nonnegative plain decimal strings only, reject floats/exponents/excess scale/overflow and require the exact registered primary Unit. Immutable synthetic policy declares scale0–6; this is not approval of actual item precision, rounding or conversions.

Inventory0007_synthetic_ledger_guards depends on inventory0006 and core0004. It adds database test-context guards, append-only guards, same-XID line/entry sealing, ownership/unit/fingerprint checks, deferred source/header/audit/full-evidence/line/leg/coverage/projection/reversal checks, and on-hand custody protection for warehouse/location deactivation and identity retirement. Existing Phase3A registration triggers remain intact. No applied migration was edited.

## Internal service contracts and transaction behavior

Only internal Python entry points exist in backend/apps/inventory/ledger.py:

- post_transaction(actor, intent, key, request_id): authenticated employee, explicit post_synthetic_transaction capability, current warehouse scopes, exact intent schema and version map. Returns the existing command tuple (safe result, response status, replay flag). Result includes immutable transaction UUID/version and resulting custody-key quantities/versions.
- custody_history(actor, stock_id, warehouse_id): explicit view_synthetic_custody plus requested warehouse scope and local custody proof. Returns minimal immutable ID/reference/unit and only that warehouse's entry legs. Does not reveal registration location, original document, other location, policy/approval or full source audit.
- rebuild_projection(actor, key, request_id): explicit rebuild_synthetic_projection and company-wide scope; exclusive posting/rebuild gate; replay-safe audited rebuild from immutable entries plus explicit zero opening lines. Full before/after projection details are retained, including removed derivative keys.

Intent fields are kind, policy UUID/version, source_system/source_event, timezone-aware effective_at, reason, lines and expected_versions; optional approval/reverses/related/quality_reference. Lines contain stock/unit UUIDs, decimal-string quantity, source/destination UUIDs, quality and optional original_line. Missing version keys produce428, stale versions412, duplicate physical events409. Validation raises controlled errors and rolls back mutations. These are internal contracts; no network status route is installed.

Supported synthetic kinds: OPENING, IN, OUT, TRANSFER, RETURN, ADJUSTMENT, CORRECTION and REVERSAL. None is a live operational workflow. All balances must have known opening scope before non-opening movement; explicit zero must be posted, never inferred. All roots must have synthetic provenance, physical identification, resolved ownership and active primary master/unit; locations/warehouses must be active and have custody department evidence. Actual designation/management approval of that department is still not semantically verified by Phase3A.

New receipts and returns default held. Only explicit synthetic policy/evidence allows released OPENING/IN fixtures. Held stock cannot issue; held transfers preserve the hold. No real hold/release workflow or numeric QC specification is implemented. An OUT request cannot exceed the exact released account and never allocates FIFO/FEFO. Same root lot may span locations without changing registration fields.

RETURN binds an original non-reversed OUT line, exact identity/source custody and cumulative outstanding quantity; returns remain held. ADJUSTMENT/CORRECTION/REVERSAL require independent immutable synthetic evidence bound to exact request hash, maker, policy and current approver capability/scope. CORRECTION links the original and compensates current feasible stock; original ledger/coverage remains unchanged. This does not implement Admin opening-correction request, Stores investigation, Procurement recording or management approval workflows.

REVERSAL exactly inverts original physical legs, has a unique original reference and cannot duplicate. Restored stock is HELD; a reversal does not resurrect QC permission. Consumed receipts cannot reverse into negative balances. Opening reversal, reversal-of-reversal and reversing an issue with outstanding returns are blocked. Backdated events are conservatively blocked per identity, future/closed dates rejected. Operational historical feasibility policy remains pending rather than simulated.

## Concurrency, atomicity and integrity

Lock order: shared existing administration/catalog/configuration advisory gates; shared ledger gate (exclusive for rebuild); existing per-actor idempotency row; unique physical source row; related/original headers sorted by UUID; stock root rows sorted by UUID; exact projection rows sorted by digest. Stock root locks serialize creation of absent projections and opposing issues. Two independent source issues cannot both consume the same quantity. Governance writers retain exclusive existing gates; stock posting does not replace existing governance.

Existing execute_command reauthorizes idempotent retries. Exact same actor/key/payload replays one result without stock/audit duplication. Reusing a physical source under another key or actor fails globally. Different content under an existing command key conflicts. Source/header/lines/entries/coverage/projection/audit/full evidence/idempotency result commit or roll back together. Injected audit failure leaves no business or retry residue.

Database guards reject UPDATE/DELETE of posted evidence even via raw SQL, and reject appending entries to previously sealed headers. Deferred checks require matching audit event with full AuditEvidence and exact line legs/projection totals before commit. Ordinary runtime ACLs must additionally prohibit TRUNCATE, schema/function ownership, trigger disabling and DDL. Table-owner/superuser control remains privileged: this is not cryptographic protection against a DBA.

## Operational posting restrictions

SYNTHETIC_LEDGER_ENABLED is False in base settings and is not enabled from an environment variable. Every service entry and fixture-write context requires config.settings.test, local PostgreSQL, an exact generated test_phase3b_<32hex> database, matching current_database and a nonce in a test-runner-created stamp. scripts/test_isolated.py --synthetic-ledger creates/migrates a brand-new absent UUID database, then stamps/enables it. Normal test mode never enables the engine. No pre-existing database is reused.

Database triggers independently reject ledger writes outside the stamped test database or without the transaction-local nonce. Merely flipping a Python setting cannot enable application/production posting. API/Admin/management-command/job callers have no posting adapter and must pass the same service boundary if added later. A malicious database owner or arbitrary code execution can remove controls; production restriction depends additionally on separate migration/runtime credentials and deployment access. No production-enabled route, opening import, data seed or real employee grant was created.

## Audit and permission coverage

Successful action inventory.post_synthetic_transaction uses entity inventory.ledgertransaction, source_version1. Full evidence includes actor/server time/correlation, kind/effective time, physical source event identity/hash linkage, stock/location/unit/quantity lines, per-key old/new quantity/version, policy UUID/version/digest, employee and role-revision/capability/scope snapshots for every custody warehouse, independent approver/decision/reference/hash and reversal/correction links. Header/protected FKs preserve identities; actual approval publishing remains deferred. Rebuild action inventory.rebuild_synthetic_projection records full per-key before/after and actor authority. Secret keys and recognizable credential strings are sanitized by shared audit infrastructure.

Capabilities defined only, with no grants: inventory.post_synthetic_transaction, inventory.approve_synthetic_transaction, inventory.view_synthetic_custody, inventory.rebuild_synthetic_projection. No Admin/Master Admin/superuser inventory authority shortcut. Replays recheck current scope and permission. Registration scope is also required for opening; destination-only users can read permitted minimal custody and issue there when explicitly scoped/capable. Existing inventory configuration and global technical Admin audit readers exclude ledger entities.

Permission failures in the posting command emit safe inventory.security denials outside business commit; failed commands do not create successful audit rows. Fixture rejected approvals are immutable evidence and cannot post; no approval/rejection workflow events are invented. Existing configuration audit regression covers scope isolation and old/new history. Full cross-module audit UI filters, historical master diffs, retention/export controls and attachment access workflows remain incomplete.

## Migration/deployment status and future upgrade

Connected read-only showmigrations reports13 pending application migrations: accounts0004/0005, core0003/0004, imports0005/0006 and inventory0001–0007. Previous9 plus four additive audit/ledger migrations. No migrate command was run against configured navapack database. PostgreSQL16.3 local owner-capable test role was used for database creation; restricted-role behavior was tested separately.

Clean-install migrations execute through the disposable runner. Future upgrade must first preserve/reconcile the exact source snapshot and review current schema/data, backups and maintenance plan; obtain deployment authorization; use separate migration-owner/runtime credentials; apply Django's dependency plan through account/import review guards, audit evidence and inventory foundation/schema/protection migrations; verify pending count/drift, ACLs, trigger presence and approved browser/configuration acceptance. Keep operational ledger disabled even after migrations. Do not copy test stamps/policies/approvals/quantities to an application database.

No populated application-database upgrade rehearsal was performed. Additive new tables need no stock backfill, but new custody activity triggers assume new projection schema exists; audit app changes need core0003/0004 before serving new mutations. Old audit rows lack full evidence and must remain honestly legacy. Rollback/removing protective migrations after evidence exists requires a separately reviewed recovery plan, not an automatic production downgrade. Existing account/import pending migrations retain their own populated-data compatibility and authority checks.

## Remaining limitations and next-phase decision

**CONDITIONAL GO for review/acceptance of the synthetic Phase3B slice. NO-GO for operational Phase3C or live posting.** No further phase is started by this report.

Required management/client decisions remain: named ownership/off-site custody/warehouse assignments; physical mark/portion segregation; actual primary precision/conversion versions; opening date/quantities/coverage/source reconciliation; Stores evidence/investigation, independent authority/delegations and Procurement recording; event boundaries, returns and WIP; QC templates/gates/independence and separate commercial permissions; opening correction/backdating/closed periods; scope publication/rejection/revocation; SOP adoption at go-live versus original1 November2026 effective date. Synthetic fixture evidence approves none of these.

Technical release gates: governed scope lifecycle, deployed restricted runtime ACLs, release source capture, populated upgrade rehearsal, browser-to-real-backend acceptance, full scoped ledger/audit access design and bounded large projection rebuild. Root identity serialization favors safety over throughput and requires later load testing. No reservations, general additional holds, quantity-scoped QC release, conserved split/merge, WIP workflow, physical-source reconciliation or source-document approval service exists. Numeric envelopes and synthetic released fixtures are test-only. Large rebuild evidence exceeding256KiB rolls back atomically; no evidence is truncated. A production engine requires separately approved controls/migrations to replace the deliberately synthetic-only restrictions.

## Verification and source preservation

Final commands/results, exact task-relative changed paths and cleanup are recorded below after verification completes. Earlier Phase3A handover and original client SOP/workbook files remain unchanged. Local logs/manifests/build output are ignored verification artifacts, not release source.

### Executed test evidence

Commands from backend using .venv/Scripts/python: manage.py check and manage.py makemigrations --check --dry-run passed connected with no issues/drift. Read-only manage.py showmigrations --plan confirmed13 pending migrations.

Audit prerequisite: scripts/test_isolated.py tests.test_audit_remediation tests.test_core tests.test_inventory —27 passed in31.677s before ledger implementation. First ledger integration run passed34 cases in82.195s (included13 imported Phase3A cases; imported TestCase duplication subsequently removed).

Full regression: scripts/test_isolated.py --synthetic-ledger — **170 passed in320.005s**, no skips/failures, disposable PostgreSQL database test_phase3b_bfd9fc4dbd03487e9742c7628e14def0. Final changed-boundary run: scripts/test_isolated.py --synthetic-ledger tests.test_ledger tests.test_audit_remediation — **28 passed in73.245s**, database test_phase3b_502c2d3006bb497e84976ab0a0160358. Both destroyed. The final28 overlap the170; not198 unique tests. Final suite adds5 audit regressions and23 ledger/gate cases to142 existing cases.

Real PostgreSQL concurrency proved one of two competing issues wins with remaining quantity3, one committed stock/audit outcome and no failed source residue. Tests also cover global cross-actor source deduplication, append-only/sealed posting, exact units/precision, held/unknown stock, ownership/custody isolation, transfer/reversal conservation, current-feasible original-preserving correction, bound returns, independent/rejected/mismatched approvals, closed dates/backdating, audit rollback, rebuild and default-disabled access.

Temporary nonowner runtime role probe actually executed: service IN succeeded with explicit restricted grants, then SET CONSTRAINTS ALL IMMEDIATE executed deferred validation while still under that role. Raw UPDATE/DELETE/TRUNCATE history, ALTER DISABLE TRIGGER, schema CREATE and audit TRUNCATE denied. Role/grants/data were enclosed in rollback-only transaction; no permanent grant or role remains. This does not certify deployed credentials or a complete production ACL specification. Most other integration tests use owner-capable local test credentials.

Frontend source unchanged: node ./node_modules/typescript/bin/tsc -b --pretty false, npm run build and all13 scripts/check-*.mjs passed. Existing large-bundle warning persists. These include demo-only workflow checks and do not certify real workflow integration. No new frontend/API routes were added.

Tests not executed: populated upgrade rehearsal, real deployed runtime identity, browser-to-live-Django acceptance, load/scale, real inventory/approval/QC/period/correction workflows. These remain limitations, not passing evidence. See PHASE_3_TEST_REPORT.md for commands, database IDs and overlap details. Local raw logs: backend/.local/phase3b/audit-gate.log, ledger-tests.log, full-tests.log, final-focused-tests.log and migration-state.log (ignored).

### Git and preservation evidence

Start branch main, HEAD0823b2065e6e01dc670c5b09f5b622bbfadf8eb2, dirty pre-existing3A worktree and empty index. Before edits captured304 tracked/nonignored source hashes in ignored backend/.local/phase3b/source-before.json and initial Git status. During execution HEAD advanced externally to82a32a1410ebbc13207b39f1325f8ddff4d64301, which tracks earlier3A and audit-remediation files. This task did not stage, commit, reset, push or deploy. Do not infer authorship of that commit from the current diff.

All28 original client source sizes/hashes match the unchanged source manifest. No baseline files were removed, frontend source and historical3A handover unchanged. Task-relative changed files below include audit changes now tracked by the external commit. New ledger/report source remains untracked and must be explicitly captured by a separately authorized release process; a checkout of HEAD alone does not reproduce3B.

Cleanup verified exact project data directory, no test databases/temporary runtime roles and zero other clients, then restored the cluster to its initial stopped state using pg_ctl fast stop (exit0). No operational database migration/data change, real stock/grant/import or deletion occurred. No Phase3C–3E began.

### Exact task-relative changed paths

Paths below are measured against the pre-change manifest, not merely the later HEAD. They include this report and documentation updates. Ignored verification/build artifacts are excluded.

- `F:/WORK/Navapack-ERP/backend/apps/accounts/employee_views.py`
- `F:/WORK/Navapack-ERP/backend/apps/core/audit.py`
- `F:/WORK/Navapack-ERP/backend/apps/core/migrations/0003_auditevidence.py`
- `F:/WORK/Navapack-ERP/backend/apps/core/migrations/0004_protect_audit_evidence.py`
- `F:/WORK/Navapack-ERP/backend/apps/core/models.py`
- `F:/WORK/Navapack-ERP/backend/apps/inventory/ledger.py`
- `F:/WORK/Navapack-ERP/backend/apps/inventory/ledger_guard.py`
- `F:/WORK/Navapack-ERP/backend/apps/inventory/ledger_models.py`
- `F:/WORK/Navapack-ERP/backend/apps/inventory/migrations/0006_postingpolicy_ledgerapproval_sourceevent_and_more.py`
- `F:/WORK/Navapack-ERP/backend/apps/inventory/migrations/0007_synthetic_ledger_guards.py`
- `F:/WORK/Navapack-ERP/backend/apps/inventory/models.py`
- `F:/WORK/Navapack-ERP/backend/config/settings/base.py`
- `F:/WORK/Navapack-ERP/backend/docs/DEVELOPMENT_STATUS.md`
- `F:/WORK/Navapack-ERP/backend/scripts/test_isolated.py`
- `F:/WORK/Navapack-ERP/backend/tests/test_audit_remediation.py`
- `F:/WORK/Navapack-ERP/backend/tests/test_ledger.py`
- `F:/WORK/Navapack-ERP/docs/phase3-planning/PHASE_3B_IMPLEMENTATION_REPORT.md`
- `F:/WORK/Navapack-ERP/docs/phase3-planning/PHASE_3_AUDIT_TRAIL_SPECIFICATION.md`
- `F:/WORK/Navapack-ERP/docs/phase3-planning/PHASE_3_CLIENT_DECISIONS.md`
- `F:/WORK/Navapack-ERP/docs/phase3-planning/PHASE_3_DATABASE_DESIGN.md`
- `F:/WORK/Navapack-ERP/docs/phase3-planning/PHASE_3_IMPLEMENTATION_PLAN.md`
- `F:/WORK/Navapack-ERP/docs/phase3-planning/PHASE_3_IMPLEMENTATION_PROGRESS.md`
- `F:/WORK/Navapack-ERP/docs/phase3-planning/PHASE_3_INVENTORY_ARCHITECTURE.md`
- `F:/WORK/Navapack-ERP/docs/phase3-planning/PHASE_3_LEDGER_AND_STOCK_RULES.md`
- `F:/WORK/Navapack-ERP/docs/phase3-planning/PHASE_3_READINESS_REPORT.md`
- `F:/WORK/Navapack-ERP/docs/phase3-planning/PHASE_3_SOP_PERMISSION_MATRIX.md`
- `F:/WORK/Navapack-ERP/docs/phase3-planning/PHASE_3_TEST_REPORT.md`

Final git diff --check passed; index empty.27 task-relative source/document files changed (including newly created files). No unrelated baseline file removed.
