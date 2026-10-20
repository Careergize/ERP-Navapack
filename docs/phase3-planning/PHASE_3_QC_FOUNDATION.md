# Phase 3 QC foundation

Classification key: [S/W/I/A/D](PHASE_3_REQUIREMENTS_TRACEABILITY.md). Design is **A** unless marked otherwise. Entity fields/constraints are defined once in [database design](PHASE_3_DATABASE_DESIGN.md).

## Confirmed controls

S — SOP 11 §§3,5–8 and SOP 01 §§3.3,4.3–4.4,6–7 require independent QC of production work, approved acceptance references, attributable results and scoped clearance. QC or PM initiates a hold for failed/missing checks, uncertain identity, process/route deviations or suspected nonconformity. PM controls production and containment but cannot independently grant mandatory QC clearance. Stores physically segregates and safeguards. QC does not own routine physical custody and cannot substitute for commercial/concession authorization.

S — SOP 11 §7.3 explicitly permits release of identified quantity/production period. The unresolved decision is how to identify and physically separate partial scopes, not whether scope exists. SOP 12 §§6.2,8 requires broad containment when boundaries uncertain and reinspection of authorized rework. A hold cannot disappear due to missing QC coverage. SOP 11 §8 and12 §12 describe one QC covering one shift, not a staffed QC Supervisor hierarchy.

## Versioned inspection plans

A — Template header identifies a controlled inspection family. Published revision freezes question IDs, response types, measurement units/method references, applicability conditions, required evidence, expected boolean polarity and approved tolerance/sampling/retention references. Store approval/effective dates and exact controlled specification/artwork/work-instruction versions. Do not embed executable client-supplied formula code. Required fields and conditional applicability evaluated server-side. A revision is distinct from operational approval of an individual lot.

I/A — Existing sealed ProductModelRevision may provide a historical technical reference, but `sealed=true` is not demonstrated business specification approval. Require an approved SourceDocumentRevision. Phase 2 route `checkpoint_template_ids` JSON does not become valid QC FKs automatically; reconcile explicit UUID/revision mappings before later production integration.

D09 — Client supplies actual applicable criteria, criticality, sample size/frequency and retention; no numeric defaults from images or demos. NRIL photographs require site/entity/template adoption before publication. The roll photograph's eight sample columns are layout, not mandatory universal sample count. “No objectionable odour” can pass with No, while dimension matching passes with Yes; treatment/gusset questions depend on order. N/A requires recorded applicability justification, never a substitute for a required missing result.

## Inspection lifecycle and evidence

A — Create DRAFT inspection against approved revision, exact item/lot/portion or defined production-period scope, source requirement, quantity presented/inspected and unit. Identify the actual operator and actual inspector separately. Capture sample ID, check/result/time, requirement reference, equipment/method reference where required, evidence digest and deviation. Draft saves require version/key. SUBMIT freezes result snapshot. QCReview records PASS/FAIL/INCOMPLETE and actual reviewer, independent of production executor. PASS is evidence of checks, not a stock movement or universal release.

A/D02 — One QC may perform independent inspection and record clearance of production's work. SOP no-self-approval applies to own requests/transactions/exceptions; it does not establish that every QC measurement needs a second QC employee. Where QC is also maker of a separately approvable request/concession/template change, assign independent delegated approver. Never invent `qc_supervisor` as required business authority. Confirm template publication and exception approval assignments before enabling them.

## Holds and partial release algorithm

1. A — QC/PM records hold reason and source. Scope includes exact lot/quantity/location, or source period with its affected lots. If uncertain, identify broad suspected scope and block release until boundary assessment; do not choose a smaller convenient quantity.
2. A — Under the [common locks](PHASE_3_LEDGER_AND_STOCK_RULES.md#postgresql-locking-protocol), expand affected quantity into disjoint StockPortions. A partial boundary splits a parent with conserved quantity; children inherit all existing gate memberships and source lineage. Mark ledger partition changes with equal ± deltas so physical total stays constant.
3. A — A portion can have several hold reasons. Available only when **all** applicable gates are satisfied for requested purpose. Do not sum overlapping hold quantities. If 10 units held for A and 6 of those also held for B, held union is 10; releasing A's 10 leaves B's 6 blocked. This is a test example, not client stock/tolerance.
4. A — QC reviews exact requirements, completed inspection, quantity, identity, rework/concession evidence and current holds. Release names specific hold/requirement and eligible portion quantity. Cumulative releases cannot exceed verified eligible quantity. Split if release covers part of a portion. Ledger reclassification to RELEASED occurs only if no other unsatisfied gate remains.
5. A — New hold reblocks still-present affected stock even if formerly released. Future receipts/portions falling under open period/lot scope inherit restriction. A transfer preserves hold obligations. Already dispatched scope produces traceability/escalation evidence, not a negative on-hand hold quantity or automatic recall execution.

A — Hold event, allocations, partition projection, reclassification transaction, release evidence and audit commit together. A failure leaves none partially changed. QualityRelease changes **availability**, never physical Stock IN. Rebuilding stock partitions uses QUALITY_RECLASS ledger entries and independently revalidates gate history; mismatches block reopening writes.

D09 — Client must approve physical portion/roll/container marking, scope expansion and partial-release method. If product cannot be physically identified at partial scope, hold the whole traceable lot; do not permit a percentage-based release of an indistinguishable pool. No routine override path.

## Off-shift, rejected stock and reinspection

S/A — Operators record defined process checks and required retained samples outside QC shift. PM verifies completeness and contains suspect output. Next-available QC verifies actual evidence; it cannot be backdated as if performed earlier. Critical products remain blocked until documented mandatory verification/clearance. SOP 01 §7.3 requires OM and QC to record interim controls where critical designation is undocumented; absence of a critical flag is not proof of noncritical status. Actual staffing/criticality/roster evidence is D09.

A — Rejected quantity remains a physical REJECTED partition with hold history. Authorized disposition may permit rework, supplier return, downgrade or scrap removal, but must carry exact scope, purpose, delegated management/customer evidence and QC requirements. “Released for rework” is not “released for dispatch.” Product identity downgrade requires separately approved identity/traceability mapping. Rework authorization references external controlled instruction in Phase 3; execution/CAPA administration deferred. Reinspection creates a new linked inspection with retained original failed results, actual date and applicable approved requirement revision. Failed/incomplete reinspection leaves holds active.

## Required API controls and acceptance

A — Proposed `/api/v1/quality/templates/`, `templates/{id}/revisions/`, `inspections/`, `inspections/{id}/submit/`, `inspections/{id}/reviews/`, `holds/`, `releases/` and read-only `lots/{id}/quality-status/`. Templates publish through an independently controlled command once D02 approved. Every command uses stable Idempotency-Key; existing aggregate mutations use If-Match. Release accepts IDs/evidence/scope, never a trusted client verdict or actor. GET returns satisfied/unsatisfied requirements and reasons per purpose, not a lone green batch label.

A — Acceptance covers PM hold allowed/PM required-QC release denied; operator cannot review own production as independent QC; Master Admin without business grant denied; overlapping and partial holds; reinspection history; held transfer/return; concurrent hold versus dispatch (one serially valid outcome, no unauthorized OUT after hold); prior-dispatched scope; mandatory missing evidence; no supervisor staffing assumption; off-shift unknown criticality; exact template/reference revision; mixed boolean polarity/conditional questions. Detailed PostgreSQL strategy is in [implementation plan](PHASE_3_IMPLEMENTATION_PLAN.md).
