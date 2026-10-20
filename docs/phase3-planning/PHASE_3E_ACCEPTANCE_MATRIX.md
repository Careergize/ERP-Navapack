# Phase 3E acceptance matrix

20 October 2026. Classification is per capability, not production approval. **Verified synthetic-only** means automated PostgreSQL/JWT evidence exists. Browser acceptance is separately limited as recorded below.

## Scenarios A–I

- **A — Verified synthetic-only:** receipt → HELD → inspection → independent review → RELEASED → physical OUT. `Phase3EAcceptanceTests.test_a_receipt_held_inspection_release_actual_issue_and_history`; exact quantity/history assertions. No issue at request/approval alone.
- **B — Verified synthetic-only:** rejected inspection → root hold → NCR investigation/CAPA → reinspection and independent closure; closure never releases. `test_b_failed_inspection_ncr_capa_reinspection_never_auto_releases`.
- **C — Verified synthetic-only:** opening remains held; inspector cannot independently approve own review; independent QC path required. `test_c_opening_remains_held_until_independent_qc`.
- **D — Verified synthetic-only:** transfer conserves quantities and immutable identity; HELD remains HELD, destination cannot inherit unsupported inspection clearance. `test_d_held_transfer_preserves_identity_quality_and_clearance_gate`.
- **E — Verified synthetic-only:** concurrent authorized OUT postings have one winner when combined demand exceeds available quantity. `test_e_concurrent_authorized_out_records_cannot_over_issue` and existing ledger concurrency tests.
- **F — Verified synthetic-only:** physical-source receipt deduplication, same-intent retry, cross-actor duplication, repeated approval and release cannot create quantity twice. `test_f_receipt_approval_release_retries_and_cross_actor_duplicates` plus existing physical-source concurrency tests.
- **G — Verified synthetic-only:** foreign warehouse list filtering, local movement legs, denied foreign exact custody, denied mutations and source-evidence boundaries. `test_g_scoped_reads_writes_and_foreign_source_evidence`.
- **H — Verified synthetic-only:** stale If-Match, changed custody/stock and superseded QC plan fail closed. `test_h_stale_versions_balances_and_superseded_plans`.
- **I — Verified synthetic-only rejection boundaries; unsupported flows deferred by design:** UNKNOWN is not zero; unsegregated partial release, rejected disposition and inherited clearance remain unavailable; disabled synthetic mode rejects calls. `test_i_unknown_coverage_partial_disposition_and_default_disabled` and D. Existing separately identified root/portion decisions remain within Phase 3D's approved technical contract; no new split/merge was implemented.

## Capability classifications

- Warehouse/location configuration and immutable identity: **implemented, automated API-verified; not fully browser accepted**. Scenario J creates configuration and a server-generated identity, asserts no quantity, posts a synthetic opening, independently corrects it and preserves the original. Existing Phase 3A tests cover identity constraints and audited permission boundaries. Actual configuration functionality uses the existing approved configuration API; it does not authorize physical custody or posting.
- Custody balances and movement reader: **verified synthetic-only**. Scenarios A, D, G, I cover exact partitions, scope, identity preservation and unknown coverage. No exposure of origin documents; no reservation/availability guarantee. Browser screen remains unaccepted.
- Stock IN / Stock OUT: **verified synthetic-only**, A/E/F/H. Physically evidenced confirmation is distinct from ledger posting; no automatic request deduction. Full browser transitions not accepted.
- Opening and Admin correction: **verified synthetic-only**, C/J; existing Admin login, independent authority, immutable original and compensating correction. Named production approvers/opening amounts are **blocked by client decision**.
- Transfers / returns: **verified synthetic-only**, D/K. Returns enter HELD; transfer does not rewrite registration warehouse. Inherited QC clearance is **deferred by design**.
- Counts / reconciliation / adjustments: **verified synthetic-only**, K and remediation regression suite. Source-line identity, investigation and independent approval precede recording; historical reconciliation/count-freeze is **blocked by client policy**, not approximated with current balances.
- QC plan publication, inspection/review, whole identified quantity release and holds: **verified synthetic-only**, A/B/C/H and existing QC suite. Sampling/tolerances, operational inspectors/reviewers and actual physical segregation are **blocked by client decision**.
- NCR/CAPA evidence, assigned actions, reinspection and independent closure: **verified synthetic-only**, B and QC tests. NCR closure is not disposition/release. Rejected disposition is **deferred by design**.
- Audit evidence/history and rollback, immutable ledger, precision, idempotency, restricted-runtime database protections: **verified synthetic-only**, complete 251-case regression. Production runtime grants, owner separation, retention/export and monitoring are **blocked by deployment readiness**.
- Source registry: **verified synthetic-only technical deduplication**. Authoritative upstream event/document-line provisioning is **blocked by source-governance approval**. Random UUIDs alone are not physical-event proof.
- Production-stage QC, manufacturing execution, dispatch/invoicing and future upstream module integration: **deferred by design**; no fabricated source records.

## Browser and frontend acceptance boundaries

- Existing JWT login/navigation: exercised in interrupted browser session against the disposable backend; limited recorded acceptance.
- Warehouse validation/create: observed backend 400/201 and reload 200 from browser actions; final post-save visual state not recovered.
- Location management, identity registration, balances/movements, IN/OUT, opening/corrections, transfers/returns, count/adjustment, QC plan/inspection/review/release, NCR history: **implemented but not fully browser accepted**. API tests cover persisted backend state; they do not prove React interactions.
- Loading/empty/validation/conflict/unauthorized/retry/success/history across every screen and role-based UI: **not fully browser accepted**. Frontend source and 13 scripts cover selected contracts only.
- Resume blocker: local browser use disabled in Work settings. Do not label automated API tests or mocked Axios adapter checks as browser acceptance. Completing this matrix requires an authorized browser-enabled disposable session; no production trial is appropriate.

Unique final backend count: **251**, including **11** Phase 3E JWT/API scenarios and **1** recovery case. Independent repeat runs overlap. Frontend typecheck/build/13 scripts pass. **CONDITIONAL GO** for synthetic development closure; full frontend acceptance remains open. **NO-GO** for production operation.
