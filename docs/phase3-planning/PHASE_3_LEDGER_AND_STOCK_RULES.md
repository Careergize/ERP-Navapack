# Phase 3 ledger and stock rules

## Phase 3C-1 workflow enforcement — 20 October 2026

Sealed requests/Stores verification/physical confirmation/independent review do not move stock. Only selected authorized recording invokes unchanged test-only ledger, rechecking versions/availability/coverage/approval. Receipts/returns/positive corrections or variances remain held; explicit root batch selection, no automatic allocation or order/job deduction. Original openings remain immutable; corrections use original quantity/current target/proposal/difference and compensating entries. Held-opening reductions are captured but approval blocked. Returns match original OUT line/current remaining quantity. Counts require investigation and never post directly; at most one adjustment may post per count, stale/reused counts require recount. No operational/backdated/QC release workflow. [Actual slice and limitations](PHASE_3C_IMPLEMENTATION_REPORT.md).

## Phase 3B implemented test engine — 20 October 2026

The internal synthetic engine supports OPENING/IN/OUT/TRANSFER/RETURN/ADJUSTMENT/CORRECTION/REVERSAL, with sealed source events, exact primary units, opening coverage, current-custody keys, independently bound correction evidence, deterministic locks, versions, idempotency and atomic audit. New receipts/restored quantities remain held except explicitly released synthetic opening/IN fixtures. Held transfers move held custody without release. No backdating, opening reversal/replacement, independently posted children, partial QC release, stock allocation or real workflow is enabled. Returns bind original OUT lines and outstanding quantity; corrections compensate current feasible balances and preserve original entries. Full [implemented invariants and future gates](PHASE_3B_IMPLEMENTATION_REPORT.md) supersede earlier no-engine statements; the broader operational rules below are still proposals.

Classification: **A — Proposed architecture** unless marked S/I/D. [Convention](PHASE_3_REQUIREMENTS_TRACEABILITY.md). These rules own ledger semantics for the document set.

## Authority and dimensions

Authoritative stock = sum of immutable ledger deltas belonging to completely POSTED transactions, grouped by exact item/lot/portion/location/unit/custody/quality partition. UI totals and balance projections are derivatives. No save-current-quantity endpoint. No posted line/header/source mutation; authorized compensation preserves original events. Group incompatible units separately. Supplier number, product name or recipe revision is not sufficient stock identity.

Physical stock is the sum of disjoint on-site custody partitions. WIP is a custody subset of on-site stock when material remains present, not an additional amount to add to physical stock. Externally held company material is reported separately from on-site physical custody; ownership policy D03 must determine whether included in enterprise totals. Reception and transit within the premises remain on-site.

For each custody key: `physical_known = released + awaiting_inspection + held + rejected + awaiting_rework`, using mutually exclusive **derived partitions** of disjoint portions. Held includes all active hold reasons as a union, not a sum of overlapping hold quantities. Rejected stock remains physically present until actual authorized removal. QualityHold is a restriction, not a second physical quantity. A portion with both rejection and hold is counted once (rejected classification, hold membership retained). Awaiting-rework > held > awaiting-inspection > released gives deterministic display precedence below rejected; all unsatisfied gates still retained.

`available_for_purpose = sum(known, released portions satisfying every applicable quality, identity, custody, authorization and period gate for that purpose)`. Sales approval and payment/credit may additionally gate dispatch even when quality released. WIP may be available for its authorized next operation without being FG available for dispatch. No reservation subtraction in Phase 3 baseline. If D14 approves reservations later: available-to-promise subtracts only active reservations from eligible stock; reservations do not decrease physical stock and must respect later holds.

Unknown/unreconciled opening is a completeness state, not a numeric partition or presumed zero. Return total `null`/INCOMPLETE when historical coverage unknown, plus separately labelled known receipts/movements. Never show known movement sum as complete stock. Disputed historical portions cannot issue. An independently measured, identified, released new receipt may issue under approved scope-specific coverage D06; safe initial operational gate blocks scopes with unresolved coverage until approved. Neither option authorizes negative stock.

## Event/state boundaries

Draft evidence has no ledger effect. Submitted content sealed; approval binds its exact hash and source revision. Authorization does not move stock. Physical confirmation records event time, measured quantity and actual personnel. PO system recording validates completed evidence, then posts all ledger/projection/source-allocation/audit/idempotency state atomically. Posting time is server UTC; occurred_at retains actual business time with site timezone evidence. Future quality events reclassify partitions with equal ± entries, never change physical totals.

| Operation | Ledger effect and preconditions |
|---|---|
| Receipt/opening | Positive custody entry only for exact approved actual quantity/unit/lot; held/awaiting partition unless required clearance and other gates satisfied. Opening requires separately approved reconciliation plan |
| Issue to Production | Equal Stores OUT/WIP custody IN of same item/unit; authorized source and acknowledgement; no inferred usage |
| Transfer | Equal source OUT/destination IN, same quantity/unit; hold/gate membership follows; no physical total change for on-site pair |
| Unused return | WIP OUT/Stores IN, capped by original outstanding issue; uncertain returned condition awaiting-QC |
| Consumption / waste generation | Later production integration only; consume from WIP once using actual evidence; separate output/waste/reject lineage, no recipe-estimated deductions |
| FG receipt | Measured production handover into Stores; external completion reference in 3, execution later; no second IN when QC clears |
| Dispatch | Later adapter: actual external handover/outbound evidence decreases on-site physical stock once; internal Stores→reception is custody transfer under D11 |
| Adjustment | Independently authorized count/investigation correction, exact stock key, no use to bypass missing normal source |
| Quality reclass | Equal partition OUT/IN within same custody key; release must satisfy all applicable restrictions; physical unchanged |
| Reversal | New compensating transaction tied to original; original still POSTED; effect shown as compensated in derived history |

S — No self-approval, evidence-backed records and mandatory QC protection follow SOP 01 §§3,6–8,03 §§4–9,11 §7. D — Negative-stock, opening coverage, backdating and exact custody timing are D06,D07,D11. Safe proposed baseline: reject negative results, reject disputed/unknown scope issue, no discretionary backdating and no operational posting before gates approved.

## Idempotency and business duplication

I — `core.commands.execute_command` uses actor+scope+action+key uniqueness, canonical JSON SHA-256, transaction.atomic(), locked idempotency row, authorize-on-replay, safe stored result and atomic audit. Quoted If-Match is enforced through existing helpers. Replay with changed payload is 409; missing version 428; stale version 412.

A — Reuse those helpers with server-resolved inventory scope. Canonical payload contains IDs, every version precondition, decimal strings, full line/evidence/source revision, occurred_at, approval references and purpose. Reuse the same intent key after timeout; no new key to “fix” an ambiguous response. Failures roll back idempotency too. Replay rechecks current access/object scope but returns historical result without re-posting/retesting old availability; a now-held lot does not cause a second ledger action.

Actor-scoped keys alone cannot prevent two employees or two keys posting the same GRN. Add a unique semantic operation token per source line/event and lock StockSourceAllocation cumulative remaining quantity. Partial receipts/dispatches have separate authorized delivery/issue event identities; the allocation cap spans all of them and source revisions. Duplicate business event returns prior authorized result or 409 already_posted; no extra stock. Retries must not reveal another user's unauthorized response data.

## PostgreSQL locking protocol

Inventory uses row locks with READ COMMITTED and stable parent gates; no reuse of catalog advisory lock **70462027** as stock-posting mutex. That lock protects Phase 2 candidate/reference phantoms, not lot availability. A final implementation must use the same ordering for receipts, holds, releases, transfers, counts and reversals:

1. Begin `execute_command` atomic scope; resolve active actor/capability/object authority. Existing account/catalog governance gates, if needed, precede all inventory locks. For reference validation use ordered `FOR SHARE` locks on exact active identity/unit/location/actor policy rows to prevent concurrent deactivation/change until commit; avoid whole-catalog gate for every stock movement. Never request a governance/catalog lock after stock locks. Dedicated policy snapshot/gate protocol must also serialize capability revocation where transition policy requires it.
2. Acquire the per-command idempotency row (existing executor); then source document/workflow aggregate and source allocation rows in UUID order. No service acquires another command's idempotency record later. Multi-source commands sort all sources first.
3. Lock affected StockLot parents in UUID order. This serializes same-lot new balance keys, portion splits and broad/partial hold creation. Source lines assigning new lots resolve/create them before sorted stock locks using unique identity conflict handling, then retry clean transaction on race.
4. Under lot locks materialize missing projection keys with unique INSERT/ON CONFLICT, then lock all affected stock keys sorted by lot, portion, location, unit, custody, partition. A missing projection row cannot escape locking because every writer must first lock its stable lot parent. No skip_locked for available stock.
5. Lock quality requirements/hold allocations/inspection release evidence in stable UUID order after lot/stock keys. New hold or receipt subject to broad hold must take same lot parent; no phantom “no hold found” race. For period-wide holds spanning not-yet-created lots, use a stable affected-scope gate (source production-period registry or approved scope row) **before** lot locks. No operational period hold supported until that scope is representable. Mark uncertain new stock held, not accidentally released.
6. Recheck locked workflow versions, frozen approved content, actors' authority/independence, source remainder, active refs, opening completeness, period policy, exact unit, quality eligibility and every affected balance. Reject if any result negative or gate unresolved. Append full ledger, update projections/allocations/header versions, append business decisions and core audit; retain idempotent result in same commit. No external effects before commit.

Deadlock/serialization failure rolls back whole command; bounded retry uses identical payload/key and fresh authorization. Do not auto-refresh a stale client's If-Match. All approved out-of-band writers must use the same protocol; runtime SQL privileges prevent bypass through direct DML functions/tables as chosen in implementation. Restricted runtime and database owner boundaries must be tested, not claimed solved by ORM overrides.

## Corrections, chronology and reconciliation

Full reversal only initially: identify original posting, reason/evidence and independent authorized reviewer; lock original/all downstream keys. Permit only if compensating effects remain valid and nonnegative and no consumed/returned/dispatched dependent allocation becomes impossible. Reverse dependent mistakes in controlled reverse dependency order, or use approved real return/correction; never restore released status merely because original receipt was once released. Restored material re-enters required current QC gates. One full reversal per original; retry cannot produce second compensation. A reversal of reversal requires a new approved correction chain, not deleting flags. Partial corrections use separately authorized bounded compensating lines and explicit allocations, with design approval before enabling.

Maintain happened_at, recorded_at and posted_at separately. Ledger append order is immutable; not arbitrary user-edited ordering. D07 decides permitted backdating/closed periods/timezone/cutoff. Baseline disallows occurrence times that would precede valid source/receipt or alter an approved closed cutoff. If backdating later enabled, validate **all subsequent running balances**, QC eligibility at event time and current unresolved holds, source chronology and affected reconciliations; current positive balance alone is insufficient. Preserve late-entry flags. No retroactive QC release invented to authorize historical use.

Counts compare a frozen ledger snapshot to actual observed stock with documented movement bridges. Count never updates balance. Reconciliation explains mismatch; correct missing legitimate transaction through its own source before deciding residual adjustment. Unknown count/identity/unit produces unresolved variance, not zero. Approvals are invalidated on evidence/version/cutoff drift. Source dates and data errors are preserved with linked corrections.

Projection rebuild streams all committed ledger lines into shadow generation by stock key; compare exact decimal balances, partition totals, allocation conservation and source uniqueness. Establish write exclusion or ledger watermark plus captured delta catch-up under final gate before swap. Sequence allocation order alone is not commit order; a maximum UUID/sequence without in-flight transaction exclusion is unsafe. Audit rebuild actor/watermark/generation and differences; rebuild cannot authorize missing opening stock or remove holds.
