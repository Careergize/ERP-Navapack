# Phase 3 controlled implementation and acceptance plan

## Phase 3C-1 bounded implementation authorization — 20 October 2026

The user's new request authorizes safe synthetic workflow development after3B, superseding the earlier blanket3C stop only for this isolated slice. Actual request/evidence/review/confirmation/recording APIs and frontend are implemented; all data/action routes/service writes require the existing verified disposable test context. Review [Phase3C report](PHASE_3C_IMPLEMENTATION_REPORT.md), test evidence and release-source preservation. Stop before3D/3E. Operational intake/posting still NO-GO pending authority/scope/QC/opening/custody/period/upgrade/browser gates; no migration deployment authorized.

## Phase 3B authorized bounded result — 20 October 2026

User separately authorized audit remediation, identity/custody contract and synthetic internal ledger development. The audit regression gate passed before ledger work. This slice now implements additive immutable posting evidence, scoped service contracts, test-only gates, projections/rebuild, compensation and PostgreSQL tests. See [Phase 3B implementation report](PHASE_3B_IMPLEMENTATION_REPORT.md) for exact verified results. Earlier no-3B authorization/status statements are historical.

Stop after Phase 3B. No Phase 3C/3D/3E or live stock actions. Phase 3C operational work is NO-GO until governed warehouse scope lifecycle, physical/source evidence and independent authority/QC/custody/opening/period rules are approved. Further bounded synthetic development requires separate authorization. Rehearse an approved populated upgrade and establish restricted runtime credentials before any migration deployment; current application migrations have not been applied.

## Resumed technical authorization and boundary

20 October 2026: the attached resume request supersedes the earlier combined 3A stop below. Implemented independently safe warehouse/location configuration, typed immutable identity/ownership/quantity-free lineage, scoped authorization enforcement, real APIs/UI and atomic audit. See progress and test reports for actual inventory and results. Scope lifecycle/publication is specifically isolated and blocked pending compatible governed proposals/revocation; no real grants. No application migrations applied.

Next work is review/acceptance and the minimal scope-governance extension with approved authority, then separately authorized migration deployment/browser acceptance. Phase 3B does not start automatically. Existing posting/QC/opening/period/authority gates still apply; synthetic 3A tests do not close them. Keep future opening correction and all quantity operations unavailable.

Classification: **A — Proposed architecture** throughout except explicit I/S/D labels. [Convention](PHASE_3_REQUIREMENTS_TRACEABILITY.md). This plan does not authorize implementation; obtain explicit user approval after relevant client decisions.

## Current authorization and stop — 20 October 2026

U — The implementation request now conditionally authorizes foundation work and verification, superseding earlier statements here that no implementation was requested. Its §11 explicitly requires stopping after documentation if Phase 3A ownership/location/identity decisions block schema. That stop applies: D03 remains unresolved for ownership/custody keys, hierarchy boundaries and access scope. No Phase 3 application code, migrations, grants or frontend commands are added. Product requirements U-A–U-J are recorded separately from management approvals.

A — First close D03 with documented scope, then review whether an independently deployable configuration-only slice can exclude custody classifications and quantities without presenting an operational stock system. Arbitrary configurable count needs no actual warehouse seed, but scope/uniqueness and authorized management access must be explicit. Reuse Material (the actual raw-material class), Consumable, ProductVariant and Unit; do not introduce competing masters. Confirm physical traceability/legacy portion scope under D05/D09 before lot schema freeze. Numeric precision and real mapping decisions gate quantity models, not warehouse count.

A — After closure: additive identity/location schema and immutable generated UUID/reference; locked hierarchy, protected historical refs and activation rules; scoped authenticated paginated/searchable APIs with strict input, idempotency and versions; atomic safe old/new audit and policy snapshots; meaningful disposable PostgreSQL tests; then real capability-driven configuration UI with auth/UUID/pagination/error/header contract fixes. Existing Admin login is reused. Review code and exact test evidence before requesting Phase 3B approval.

A — Opening corrections require separate immutable request/decision/compensation history even after original posting. Validate all later running balances, coverage, holds, source allocations and closed periods; original unchanged. All new stock starts held. Eligible suggestions must disclose exact traceable scope without FIFO/FEFO assumptions. These requirements modify future 3B–3E acceptance, not enable them now.

D — Phase 3B remains NO-GO pending 3A, D02 authority, D03 custody, D04 quantity rules, D05 physical identity, D06 openings, D07 periods/backdating, D08 WIP boundaries, D09 quality scope, D10 receipt and D11 dispatch timing. Even a synthetic-only disabled engine requires next-subphase authorization. SOP adoption D01, reconciliation/mapping D12/D13 and evidence policy D15 gate operational rollout. No existing database migration, opening import, deployment, staging or commit is authorized by this plan.

## Dependency order and rollout gates

A — **3A → 3B (non-operational engine) → 3D (QC) → 3C (operational movements/reconciliation) → 3E**. Source/evidence components of 3C can be developed alongside 3D after explicit approval. Do not enable live receipt/issue/adjustment posting before QC gates exist. This changes the suggested order because available stock cannot safely be computed without mandatory quality controls.

| Subphase | Scope / proposed apps and models | Dependencies / decisions | Future additive migrations and proposed API | Capabilities | Tests / acceptance / exclusions |
|---|---|---|---|---|---|
| 3A Identity/location | inventory: InventoryLocation, InventoryItemIdentity, StockLot; reuse masters Unit/Material/Consumable/ProductVariant and specification refs | Approved Phase2.1 baseline; D03–D05,D08,D09 scope; explicit user authorization | Identity/location/lot constraints, protected refs and indexes; GET/POST inventory/items/,locations/,lots/ versioned commands | inventory.view_*, manage_location/manage_lot identity capabilities proposed, grants D02 | Exactly-one-master constraint; UUIDs/unit freeze; no machine warehouses; inactive refs/history. Accept only approved identity/scope design. No quantities/openings/postings |
| 3B Engine, disabled operationally | inventory: source revisions/attachments/approvals, portions/lineage, transaction/lines/source allocation, ledger/projection; quality eligibility interface fails closed until3D | 3A; D02,D04–D11 key posting decisions; common lock protocol | Append-only guards, conservation/uniqueness, posting constraints, source allocation and projection indexes; read balances/,ledger/,traceability/; internal post/reverse service; no public arbitrary ledger INSERT | inventory.view_ledger, view_balance, proposed purpose-specific post/approve/reverse | PostgreSQL races/replay/rollback/rebuild; runtime DB privileges; source uniqueness across keys/users. No live movement enablement or production execution |
| 3D QC foundation | quality: template/revision, inspection/result/review, hold/allocation/release; inventory quality reclassification/gates | 3A/3B source/portion/locks; D02,D09,D15 adopted plans/forms | Quality constraints/immutable events and indexes; templates/revisions/,inspections/submit/reviews/,holds/,releases/, quality-status/ | quality.manage_template, publish_template, inspect, review, place_hold, release, view_evidence, scoped to function | PM can contain but cannot required-QC clear; partial/overlap gates/reinspection/off-shift/races; no invented supervisor/tolerances. CAPA, scheduler and production execution excluded |
| 3C Controlled stock workflows | inventory: receipt/issue/transfer/return/adjustment/count/reconciliation/opening review/coverage; bounded external evidence adapters | 3B+3D proven; D01–D13,D15 operational gates and approved restricted actor assignments | Add workflow tables/checks/triggers; receipts/,issues/,returns/,transfers/,counts/,reconciliations/,opening-reviews/ and explicit submit/approve/physical-confirm/post commands | Distinct capture_evidence/authorize/record/verify/approve_opening/approve_adjustment capabilities per matrix | Actual receipt vs QC, PO vs Stores, issue≠consumption, return cap, count snapshot, unknown openings, approved compensation. No stock migration until separate approved opening plan; external dispatch/production/recycling execution excluded |
| 3E Frontend + acceptance | React API adapters/DTO/session/multi-capability navigation; workflow/evidence/quality/reconciliation views | Backend contracts stable; D02 memberships; browser fixtures, operational training and approved rollout scope | No domain schema expansion by UI; correct `/api/v1`, UUID strings/decimal strings/headers/pagination | Server capabilities reflected per action/context; no role-name bypass | typecheck/build/all check scripts + browser-to-Django acceptance, retry/stale/auth/quality/unknown coverage; Android only when native scope exists. No implicit production deployment |

A — Migration checklist per future subphase: new files only; depend on actual prior leaf migrations; inspect SQL/checks/indexes; fresh PostgreSQL install; upgrade from Phase2 and2.1 disposable copies; rollback via forward repair/restore plan rather than rewriting applied history; verify existing references and Phase1/2 suite. No role/quantity seeds, no mock data and no trigger bypass for production runtime. D04 numeric/scale and D03 ownership/scope choices must be resolved before final stock-key migrations.

## PostgreSQL verification design

A — Use Django TransactionTestCase with real PostgreSQL, separate thread/process connections, explicit barriers/events and finite timeouts. Close/reopen connections per worker; never share connection objects. Avoid TestCase outer-transaction masking and SQLite substitution. Assert final committed database rows from a fresh connection, not only HTTP status or mocked helper calls. Repeat race scheduling for both event orders deterministically, not flaky timing sleeps. Capture SQLSTATE/deadlock behavior, enforce bounded retries and verify consistent lock ordering for multi-lot transfers.

A — Future test runner uses a fresh absent UUID-named dedicated local test DB and restricted credentials; inspect `backend/scripts/test_isolated.py` before reusing. Tests may create/apply schema only in separately authorized disposable DB. No application database migration/posting during this planning task. Prior foundation concurrency tests are examples, not stock-engine coverage.

| Scenario | Concrete arrangement / required outcome |
|---|---|
| Duplicate posting / idempotency replay | Same source and key concurrently: one posting, one audit domain event, same authorized result. Changed payload same key409. Different actor/key same source: no second posting; bounded allocation catches duplicates |
| Concurrent OUT / negative prevention | Synthetic known released10; two independent requests issue7 each through separate connections; exactly one succeeds, remaining3, no partial ledger/audit/idempotency residue. This is a test fixture, not client quantity |
| Unknown opening | Blank starting observation plus movements does not become zero/complete; disputed scope cannot issue. Approved new receipt scope only enabled if D06 permits, with incomplete aggregate labelled |
| Unit mismatch and precision | kg item with carton line denied before ledger insert; fractional/excess-scale/overflow follows approved unit scale, never implicit rounding |
| Batch/variant traceability | Same labels differing variant/customer/pack remain distinct; receipt→portion split→transfer→return traces source and exact unit/lot. Missing/invalid historical refs rejected, old inactive refs readable |
| QC hold versus dispatch/issue | Synchronize hold and OUT after shared scope lock; OUT after committed hold denied. OUT that commits before new hold remains historical and scope escalates as already dispatched; no retroactive deletion |
| Partial/overlap release | Two overlapping holds; release A does not clear B. Concurrent releases cannot exceed eligible remaining quantity; new child/transferred portion retains gates |
| Independent approval | Same User in multiple roles, superuser or Master Admin still cannot approve own transaction or independently QC-review own production. Missing delegated approval fails closed |
| Unauthorized adjustment/reversal | PO without approval cannot post adjustment; count alone does not mutate; missing reason/source/approval or stale approved hash denied. Full reversal unique; downstream insufficient quantity blocks invalid compensation |
| Audit rollback | Inject core audit failure after ledger/projection writes; all stock/source allocation/header/quality/idempotency changes rolled back. Repeat with source/line constraint failure |
| Stale preconditions | Missing428, invalid400, stale412; unchanged retry after successful commit returns saved result under current authorization. Revoked capability blocks replay access |
| Projection rebuild | Corrupt disposable derivative only, rebuild shadow from immutable committed ledger/gates; exact equality restored. In-flight posting exclusion/catch-up prevents missed commit; no opening completeness fabricated |
| Backdating | Earlier than receipt/source denied; closed cutoff denied; if D07 permits historical movement, test later running negative balance despite positive current balance, late hold/release chronology and cutoff bridge |
| Issue vs consumption | Issue transfers custody only; no consumption/output/waste auto-post. Returns bounded by issued remainder; later actual usage separate typed source event |
| Reconciliation | Count captured at snapshot; concurrent movements frozen or explicitly bridged; variance preserved/investigated; approval binds exact count/evidence. Approved adjustment once; unknown identity/unit cannot resolve as zero |
| Inactive masters and races | New movement referencing inactive item/unit/location denied; concurrently deactivate vs post serialized by reference locks; existing ledger still readable. Renames cannot rewrite snapshots |
| Raw SQL/privileges | UPDATE/DELETE/TRUNCATE immutable ledger/evidence blocked under runtime role; cross-row conservation/posted state and FK mismatch rejected by deferred guards. Owner bypass recorded as operational boundary |
| Migration/release | Fresh install+forward upgrade preserve Phase1/2 data/guards; legacy review re-review required; runtime technical grants unchanged; no implicit business capabilities seeded |

## Operational acceptance scenarios

A — Store Keeper receives measured quantity and condition, flags discrepancy/awaiting-QC, uploads/links receiving evidence, obtains assigned quantity check and sees custody/backlog without released availability. Cannot use ordinary custody rights to post unrestricted adjustment or clear QC. Records actual issue only against valid authorization; recipient acknowledgement and source remain visible.

A — Procurement Officer records exact authorized Stores source using current versions/idempotency; duplicate click or timeout does not duplicate stock. Conflicting PO/GRN evidence blocks finalization. Cannot claim physical custody or independently verify own recording. Can reconcile source backlog without entering arbitrary stock totals.

A — QC uses approved applicable revision, records actual independent measurements, contains suspect quantity and partially releases only identified eligible scope. Another hold stays effective. Reinspection preserves failed result. Off-shift missing evidence cannot be marked retrospectively passed. Quality clearance does not approve a concession or managerial/commercial release.

A — Production Manager requests material, confirms receipt/route, reports unused returns and contains suspect WIP. No auto-consumption from issue or BOM. Cannot clear mandatory QC or route slit rolls into gusseting. Missing job/source/route authority blocks the operation rather than creating fake work orders.

A — Master Admin governs technical role proposals with independent publication, sees permitted audit evidence and configures approved permissions only within delegation. Has no implicit receipt/adjustment/reversal/QC release rights and cannot self-approve business actions by changing role labels. Membership drift invalidates governance proposals as current Phase2.1 requires.

## Release acceptance and stopping rule

A — Each subphase requires reviewed schema/contract, closed relevant decision IDs, successful PostgreSQL tests, regression checks and named functional acceptance. Operational release additionally needs controlled SOP effective-date adoption, trained staffing/independent coverage, approved location/unit/lot/quality plans, opening reconciliation, migration/restore rehearsal, restricted DB rights, monitored evidence backlog and explicit deployment authorization. Green mock/backend tests alone are insufficient.

D — Until P0 decisions and explicit implementation authorization arrive, only further architecture/decision validation can begin. 3A is the first implementation candidate after its gates; there is no authorized code/migration work in this task. Deployment and stock migration require their own approval after reviewable results exist.
