# Phase 4B frontend and integration acceptance

21 October 2026, Asia/Kolkata. Development acceptance only; not customer or operational approval.

## Implemented UI

Existing backend-session `/commercial` now supports up to 100 products, 100 material components and 100 process components per costing line. Quantities/prices remain strings. Forms expose native unit, explicit document/component currency, rounding, gross input/output assumptions, markup, classification, customer/prospect, requested dates, sealed specification revision, permitted marketing person and exact owned costing revision. Prices never convert/import automatically. Unit/currency/source mismatches remain server validations.

The editor projects every declared Phase 4A input field from saved snapshots and removes only known server enrichment. It retains multiple components, model/costing/stock identity references, marketing person, classification and line/document dates. Unknown future fields block editing rather than disappear. Current master and costing choices use authenticated paginated APIs. Unavailable retained references remain visible; they are not silently replaced. Ordinary employee selection is self-only under explicit employee-read capability; full name/reference directory remains behind the existing Master Admin boundary. No HR details are projected.

Draft create/edit, submit, return to draft and pre-approval cancellation use server persistence, immutable history, full semantic retry keys and If-Match. History includes actor/time/reason/audit request/revision linkage. Comparison shows current versus any loaded historical snapshot; at most 200 differences are displayed with an explicit total. Full snapshots remain available in history. Demo contexts/pages remain separate.

The proposal panel displays eight decision IDs, departments, required/conflicting evidence, questions, baseline versus pending status and immutable submission history. Explicit proposal capability controls writes. Policy and answer payloads have no publication/approval controls or executable effect. PDF/email, customer issue/acceptance, confirmation, fiscal totals and fulfilment remain unavailable.

## Automated acceptance

`check-commercial-hardening.mjs` verifies lossless advanced editor projection, exact decimal strings, multi-component preservation, unknown-field rejection, comparisons, proposal headers/routes and error propagation. Its live mode uses actual JWT and the production React Axios/editor functions against disposable Django/PostgreSQL: multi-component costing; advanced draft edit/history; stale edit; two distinct product variants in quotation/order; customer/specification/employee/costing selectors; proposal/answer history and retry; forbidden approval/tax overrides; historical costing after master change; foreign-owner denial; and no stock/balance changes.

Real adapter test `tests.test_phase4b_transport` passed independently: 1 test in 10.422 seconds. Existing Phase 4A transport is also retained. All 15 frontend validation scripts, TypeScript noEmit and production build passed; large-bundle warning remains. These automated checks do not alone establish visual acceptance.

## Real browser acceptance — exercised

The browser is enabled in this session, unlike the earlier Phase 3/4A report. First navigation timed out because Vite was running inside command network isolation. The Django loopback health endpoint responded; restarting only the task's Vite server outside that isolation, still bound to 127.0.0.1, resolved the connection. No firewall or other security configuration was changed.

Harness: `scripts/serve_commercial_acceptance.py --disposable-synthetic-only`, freshly generated/stamped PostgreSQL, loopback Django 8014 and Vite 5174, mock login false for that process only, bounded lifetime, existing synthetic employee accounts. No configured application database is used.

Verified through rendered React controls:

- JWT login, navigation, loading and empty saved-record/registry states.
- Customer-independent costing: two material components and two process components; explicit kg/UGX, sealed specification, waste/rejection assumptions and markup.
- Saved material estimate 4.01, process 3.00, production estimate 7.01, cost/kg 2.34, cost/ctr unavailable, suggested gross margin 20.000000%; VAT/LED/final payable unavailable.
- Saved/reloaded advanced edit retained second material `[quantity=1, price=2, currency=UGX]` and second process `[description=Synthetic process B, amount=2, currency=UGX]`; immutable new revision and review → return to draft reached revision 4.
- Two-product quotation used customer, marketing-person, sealed specification and historical costing selectors. Full page refresh restored the backend session and both saved products (3 kg × 2 and 5 kg × 3, net estimate 21.00 UGX).
- Two-product order persisted and followed DRAFT → REVIEW → DRAFT → CANCELLED at revision 4. No confirmation/dispatch control appeared.
- VAT_LED proposal containing `approved:true` in its draft JSON remained PROPOSED_UNVERIFIED. Linked P4-01 answer remained PENDING_VERIFICATION, baseline OPEN, with all three LED interpretations visible and no independent review claimed.
- Two separate browser tabs edited the same quotation. The winning tab produced revision 2; the stale tab received structured 412 and retained its unsaved terms exactly (`Retain this unsaved draft during a conflict`).
- A second owner's JWT login displayed no saved documents and no proposal records from the first owner.

Screenshots in ignored evidence folder: `backend/.local/phase4b/browser-policy-registry.jpg` and `browser-stale-conflict.jpg`. Browser actions do not approve business rules or external documents. The harness verifies ledger/balance row counts at teardown; final cleanup results are recorded in the implementation report.

## Remaining acceptance limits

This is sampled desktop browser acceptance, not exhaustive visual certification. Automated tests cover additional invalid references, unauthorized review, capability loss/replay, rollback, Decimal bounds and concurrent commands. Full keyboard/accessibility, mobile/Capacitor, all pagination sizes, network interruption, every permission combination and operational runtime environment remain unaccepted. No PDF/email/customer-delivery, production, dispatch, invoicing or live inventory acceptance is claimed.
