# Phase 4B policy proposal and decision registry

21 October 2026, Asia/Kolkata. Synthetic-only development. Proposals are evidence, never executable authority.

## Reuse and domain separation

Existing RoleCapabilityRevision publishes effective employee permissions and therefore cannot be repurposed as inactive commercial policy. CommercialDocument is a commercial estimate/order aggregate, not policy authority. The new reusable GovernanceRecord/GovernanceRevision pair uses the existing VersionedModel, append-only queryset, explicit Employee/RBAC checks, stamped synthetic environment, catalog transaction gate, execute_command, row-version locks, idempotency and AuditEvent/AuditEvidence. It introduces no alternative authentication, audit store or policy evaluator.

GovernanceRecord has stable UUID, immutable owner/kind/key, optimistic version and timestamps. POLICY keys identify one of nine policy types; DECISION keys are P4-01 through P4-08, unique per owner. Multiple policy families may have the same type; each retains its own UUID/history. GovernanceRevision holds immutable number, author, creation timestamp, status, complete content, change reason and canonical SHA-256. A policy revision contains title, draft JSON object, evidence references/descriptions and optional proposed effective date. A decision revision contains unverified answer, evidence and optional exact owned policy-revision reference with frozen source content/hash.

Policy status is always PROPOSED_UNVERIFIED; answer status is always PENDING_VERIFICATION. Responses explicitly report approved=false, active=false and authority=false. There is no approved-by, activation date, effective-policy pointer, publisher, scheduled activation, policy evaluator or publication endpoint. Proposed dates and approval claims inside draft JSON have no effect.

## Supported policy types

- PRICING_DISCOUNT — pricing and discount authority proposals.
- APPROVAL_MATRIX — commercial approver/delegation proposals.
- CURRENCY_ROUNDING — currency, precision, FX/rounding proposals.
- VAT_LED — applicability, base, rates, denominator and sequencing proposals.
- CUSTOMER_ACCEPTANCE — customer identity/acceptance evidence proposals.
- DOCUMENT_NUMBERING — numbering/template governance proposals.
- QUOTATION_VALIDITY — validity/expiry proposals.
- ORDER_AMENDMENT — confirmed-order amendment/cancellation proposals.
- COSTING_UNIT_GOVERNANCE — consumption/output/unit/conversion governance proposals.

No proposal grants a capability, fills an unresolved rate, approves a conversion, allocates a document number or changes quotation validity automatically.

## Decision metadata and evidence

Versioned server catalog `phase4b-v1` retains P4-01–P4-08 departments, required evidence, questions and baseline status from PHASE_4_CLIENT_DECISIONS.md. P4-07 retains CONFIRMED_PRINCIPLES_DEFERRED; other baselines remain OPEN. Recording an answer changes only that owner's displayed submission status to PENDING_VERIFICATION. Baseline status remains visible, review_performed remains false and immutable answer history grows. No answer or reference marks a decision resolved. The history is a submission/review-preparation trail, not evidence that independent review occurred.

P4-01 preserves three separate evidence entries: the Phase 4A request's fixed amount per 1,000 units; frontend 2.5% versus USD70/tonne with kg/FX; and historical C25 MAX(0.07,C24×2.5%) commentary without an original costing workbook. VAT 18% remains an unverified rule claim. These descriptions are not merged into a guessed formula. Registry text and referenced documents are never parsed into executable policy.

## APIs and access

Base `/api/v1/commercial/`, existing JWT. Every operation requires active Employee, explicit commercial.use_foundation and the original disposable database/name/nonce/settings checks. Policy/answer records additionally require explicit commercial.manage_proposals. No real grant is provisioned; no superuser shortcut. Record list/detail/history/write/linkage is owner-only. Losing the capability denies replay. The static decision catalog is readable with commercial.use_foundation; retained private answers require the additional proposal capability.

- GET `decision-registry/`: eight metadata entries, own permitted latest submissions, statuses, immutable policy link, review-history counts and independent-review-unavailable flag.
- GET/POST `policy-proposals/`; GET/PATCH `policy-proposals/{uuid}/`; GET `policy-proposals/{uuid}/history/`.
- Equivalent `decision-submissions/` list/create/detail/replace/history routes.
- Writes: `{data, reason}`, Idempotency-Key; replacements also require quoted If-Match. All semantic input, identity and version are hashed. Stale 412; conflicting retry 409; missing version 428; validation 400; hidden owner/source 404; unavailable context/capability 403. No PUT, DELETE, approve, publish or resolve action exists.

Policy data: `{policy_type,title,draft_payload,evidence:[{reference,description}],proposed_effective_date?}`. Decision data: `{decision_id,answer,evidence:[{reference,description}],linked_policy_revision?}`. Unknown outer fields (including status/approved/active) are rejected. Evidence is 1–20 bounded text references, not an upload or retrieval feature. JSON nesting is bounded to eight levels, containers to 100 members/items, strings to 8000 characters, entered content to 32 KiB and complete linked evidence to 64 KiB. Proposed payloads may describe a future rule, including approval claims; they are never trusted as authority.

Additive database guards enforce immutable identity, sequential versions, append-only revisions, unverified-only kind/key/status, stamp context, bounds and matching atomic audit revision/hash/reason. Actual database owners remain trusted administrators; runtime ACL deployment is still a release gate.

## Future approval contracts — NON-EXECUTABLE

The following are proposed command contracts only. **No route or service implements them in Phase 4B.** They are not authorization to implement them. Independent policy adoption, named capability/scope/ceilings, client evidence and a separately authorized subphase must precede implementation.

Common proposed request:

```json
{
  "aggregate_id": "uuid",
  "expected_version": 4,
  "source_revision_id": "uuid",
  "source_sha256": "canonical snapshot hash",
  "policy_revision_ids": {"authority": "approved immutable revision", "pricing": "approved immutable revision"},
  "evidence_references": ["controlled evidence identity"],
  "reason": "bounded business reason"
}
```

JWT determines actor; stored source history determines maker. Client-supplied maker, actor, status or approval flags must never authorize anything. Future commands require Idempotency-Key and If-Match; authorize scope on replay; lock exact source, governing policy revisions and affected aggregate; validate source hash/version/evidence; enforce independent maker/checker; write immutable decision, audit and state in one transaction. Reject 403 authority/independence, 404 hidden source, 409 policy/evidence/state conflict, 412 stale version and 428 missing precondition. Audit failure must roll back every write. Proposed successful response: `{id,version,state,source_revision_id,approval_evidence_id,policy_revision_ids,authority_snapshot}`. No production stock effect belongs in these commercial responses.

- **Independent costing approval:** requires exact cost inputs/output units, currency/rounding and consumption policy, independent reviewer and approved scope. Proposed DRAFT/REVIEW → COSTING_APPROVED; approval freezes cost/selling assumptions, never actual production cost. Zero/negative margin exceptions need client-approved delegation, not inferred ceilings.
- **Quotation approval:** requires approved pricing/discount/authority/tax/levy/validity policies, exact costing sources where applicable and reviewed customer/specification/terms. Proposed REVIEW → QUOTATION_APPROVED. Any financial or commitment change needs a new reviewed revision; no mutable master can rewrite it.
- **Customer-facing issue:** requires the exact approved offer, valid date, adopted numbering/template/signatory, authorized recipient and delivery evidence. Proposed QUOTATION_APPROVED → SENT. Future external effects occur after commit via separately designed outbox; PDF/email transport is absent now.
- **Customer acceptance/rejection:** requires verified customer identity/scope, exact issued offer revision/hash and controlled response evidence/date. Proposed SENT → ACCEPTED or CUSTOMER_REJECTED. Employee-entered text, carrier acknowledgement, a file or a sent email alone does not prove customer acceptance.
- **Approved quotation conversion:** requires governed approval plus verified acceptance, exact line/currency/unit/price/specification bindings, customer identity and validity. Preserve the accepted snapshot in the resulting draft order. One-to-one versus partial/multiple-order conversion cardinality remains a client decision; fail closed until defined. Idempotency must additionally protect the adopted source conversion identity, without inventing a cardinality policy now.
- **Sales Order confirmation:** requires delegated commercial approval and operational feasibility/required QC specification review, exact requested commitments and immutable agreed-price evidence. Proposed REVIEW → CONFIRMED. It must create no reservation, ledger entry, consumption, Job Card or dispatch record.
- **Confirmed-order amendment:** proposed separate amendment request pins the old confirmed version/hash and a complete replacement proposal. Independent affected-position approvals apply the exact reviewed revision atomically; before approval, the old confirmation remains effective. Never edit confirmed price/quantity/specification/date silently. Future downstream work dependencies and price renegotiation remain explicit policy gates.
- **Confirmed-order cancellation:** proposed cancellation request pins the confirmed source and documents independent authorization plus downstream status checks. Proposed CONFIRMED → CANCELLED only under adopted rules. Never reverse physical stock, manufacturing or financial records automatically; executed downstream records require their own governed contracts. The current pre-approval draft cancellation is not this future command.

All these state names remain absent from executable Phase 4B transitions. One Job Card may later cover an entire multi-product order; stock manufacturing may exist without any order. Neither principle activates an engine.
