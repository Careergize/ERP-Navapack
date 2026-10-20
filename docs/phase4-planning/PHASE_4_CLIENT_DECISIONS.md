# Phase 4 client decisions

20 October 2026. User authorizes Phase 4A synthetic foundation only. No production policy is approved by this document. Existing Phase 3 D01–D15 decisions remain open where previously open.

## P4-01 — Tax and levy interpretation (OPEN, Finance/Management)

Evidence conflict: this Phase 4A request describes VAT at 18% and LED as the higher of a percentage calculation or fixed amount per 1,000 units. The existing `frontend/src/lib/led.ts` and 15 October frontend notes encode 2.5% versus USD70/tonne × eligible KG × dated USD→UGX. Earlier costing notes describe C25 MAX(0.07, C24×2.5%) with ambiguous local/USD basis. The two original supplied stock workbooks do not settle a costing/levy rule. No independent original costing workbook is present in the designated source manifest.

Required: authoritative adopted rule/evidence and effective date; applicability/product exemptions; precise percentage base; fixed amount, currency and denominator (1,000 what units versus tonne); inclusion/exclusion of discount/process costs/levy in VAT; inclusive/exclusive selling-price treatment; jurisdiction/legal review by the responsible client advisers. An 18% example is not authority to calculate/pay tax. Interim: null VAT/LED/final payable total; reject user-provided tax-rule overrides. No external legal validity claim.

## P4-02 — Currency, FX and monetary rounding (OPEN, Finance)

Approve allowed document currencies, precision per currency, rounding mode and line/subtotal/discount/tax rounding sequence. If FX is allowed, identify rate source, direction, valuation date, approval/version and treatment of later revisions. Interim: one explicitly selected UGX or USD currency; no FX, mixed-currency components or automatic repricing. Development 0/2 places and half-up/even are selectable assumptions, not policy.

## P4-03 — Unit, consumption and yield rules (OPEN, Production/QC/Finance)

Confirm exact material and finished-product units, permitted quantity scales, gross/net recipe interpretation, waste/rejection sequence, recoverable scrap credit and measured output evidence. Approve item/model-specific kg↔ctr conversion only with versioned evidence. Interim: gross consumption and explicit output quantity; no inferred conversion, automatic loss scaling, scrap value or actual consumption. Exact unit mismatch fails.

## P4-04 — Commercial authority and amendments (OPEN, Management/OM/Finance)

Approve named positions, explicit capabilities, scope, monetary/discount/credit ceilings, independent reviewer requirements, review routing and delegation expiry. Define confirmed-order price/specification/date/quantity changes, cancellations and escalation. SOP 01 §§3.2/3.8 supplies no monetary limits; SOP 02 §§4–5 requires documented review. Interim: all commercial approval, order confirmation and customer-facing transitions blocked, including for technical superusers. Receptionist creation is represented by an employee with explicitly provisioned development capability, not a role label grant.

## P4-05 — Customer access and customer acceptance (OPEN, Sales/Management/IT)

Approve company/tenant/customer boundaries, team visibility, marketing-person assignments, prospective-customer onboarding and conversion, acceptance/rejection evidence, validity/expiry and quote-to-order linkage rules. Interim: owner-only commercial records; explicit existing master references; no customer portal, customer email, automatic conversion or customer acceptance state.

## P4-06 — Commercial document standards (OPEN, Sales/Finance)

Approve quotation/order numbering, legal/company identity, customer-facing templates, signatories, terms, delivery promises, discounts and retention. Existing demo templates and sample photos do not establish approved reusable documents. Interim: UUID identity and immutable revision reasons/history; no approved customer template, PDF renderer or outbound email transport.

## P4-07 — Later production and fulfilment contracts (CONFIRMED PRINCIPLES; implementation deferred)

Confirmed by current task: orders contain multiple products; stock and/or manufacturing can fulfil an order; creation/approval does not deduct stock; only confirmed physical dispatch reduces stock; no automatic reservation; governed confirmed changes; one Job Card may cover an entire order; stock manufacturing may exist independently of orders. These do not approve a Job Card execution, dispatch, invoicing or operational inventory engine. Phase 3 ownership/scope/opening/QC/period/dispatch policies remain prerequisites. Interim: immutable references and demand only, no stock movements or capacity commitments.

## P4-08 — Release and acceptance (OPEN, Management/IT)

Close Phase 3 browser acceptance gaps, accept Phase 4 form/error/retry/visibility/history behavior in a browser, review restricted runtime DB grants, stage a separately authorized migration/recovery rehearsal and approve a reproducible source checkpoint. No application migration, grants, commit/push or deployment is authorized by development test success. Formal SOP adoption remains unresolved before its stated 1 November 2026 date.

Record future answers as dated evidence linked to these IDs; do not replace conflicting evidence silently. Policy publication must use immutable revisions and independent authority, not client-supplied booleans.
