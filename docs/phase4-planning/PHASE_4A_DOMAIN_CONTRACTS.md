# Phase 4A domain contracts

20 October 2026. Contract `phase4a-v1`, synthetic development only.

## Boundary and reuse

Commercial estimates are separate from actual costs and custody. The additive `commercial` app uses existing JWT middleware, explicit server permissions/Employee identity, `execute_command`, `lock_versioned`, idempotency records, append-only audit/evidence and the existing catalog transaction gate. Every read/write requires the existing verified disposable PostgreSQL environment, active employee and explicit `commercial.use_foundation`; no superuser/Admin shortcut. No grants are seeded.

Documents are owner-only, including list, detail, history, commands and linked costing/quotation sources. This conservative development restriction is not a client-approved sharing, tenant or customer portal policy. Masters remain the existing shared catalog; creating a snapshot additionally requires explicit read permission for each master class. Commercial owners may read their retained historical snapshot after master access/status changes; losing the commercial capability denies access and retry.

## Persistence and immutable history

`CommercialDocument`: UUID, owner, kind (`COSTING`, `QUOTATION`, `SALES_ORDER`), state and optimistic version. `CommercialRevision`: immutable UUID, parent, unique positive revision number, actor, timestamp, reason, state, validated snapshot and canonical SHA-256. Every edit and transition appends one revision; document version equals its current revision number. No deletion/rewrite endpoint exists.

This is a bounded JSON snapshot aggregate with strict typed nested validation, not a normalized execution/order-allocation schema. Revisions retain customer/prospect identity/version/address/classification, variant/version/specification, exact Unit identity/version/dimension, optional sealed model revision, material identities/versions, entered rates, assumptions, rounding and calculation outputs. Future relational commercial lines or reporting indexes require an additive migration/contract upgrade, preserving these snapshots.

PostgreSQL guards reject unstamped writes, owner/kind changes, revision changes/deletion, unsupported states and incoherent version advances. Deferred constraints require matching immutable revision and atomic AuditEvent/AuditEvidence. Django services also preserve transactional rollback, including command keys. Application database migrations are not authorized here.

## Decimal calculation v1

All quantities/prices/percentages are nonnegative plain decimal **strings**, at most 12 integer and 6 fractional digits. Reject JSON numbers, signs, exponent notation, nonfinite values and excess precision. Output/material quantities must be positive. Use Decimal local precision 60, explicit document currency (`UGX` or `USD`), selected monetary places (`0` or `2`) and `HALF_UP` or `HALF_EVEN`; these are development choices, not approved accounting policy. Monetary results at or above 10^30 are rejected.

- Material cost = sum of entered gross consumption × price per the same exact material unit. Material and price units must match the material master; every cost component must use the document currency. No FX conversion.
- Process estimate = sum of entered currency amounts. This contract does not infer machine-hour, labour or utility rates from missing evidence.
- Estimated production cost = material + process cost. Waste/rejection percentages (each below 100%) and their evidence are retained assumptions; entered finished quantity is explicit. The engine never scales consumption by waste again or claims mass-balance/yield validation across incompatible units.
- Cost per output unit = unrounded total / explicit output quantity, then monetary rounding. `cost_per_kg` is available only for exact unit code `kg` with mass dimension; `cost_per_ctr` only for exact code `ctr` with package dimension. Otherwise null. No aliases, unit equivalence or kg↔ctr conversion is inferred.
- Suggested net selling = unrounded total × (1 + markup% / 100); suggested gross margin = (selling − cost) / selling × 100. Entered selling and entered gross margin before document discount are retained separately. Zero selling has null margin. No automatic price approval.
- Commercial line amount = round(quantity × entered net unit price); subtotal = sum of rounded lines; net estimate = subtotal − entered net monetary discount. Discount must fit the currency scale and not exceed subtotal. Discount is not silently allocated across costing lines.
- VAT, LED, final payable total and actual cost remain null; every estimate is nonauthoritative and carries blocking policy IDs. Unknown tax/levy/FX/conversion fields are rejected rather than interpreted as zero tax.

## References and workflow

Quotations require exactly one existing active Customer or Prospect. Sales orders require Customer; prospect promotion reuses the separate existing master workflow. Product costing may have no party, allowing estimates for stock without inventing a customer or order. A costing may optionally identify one Customer or Prospect. Optional B2B/B2C requires a party and must agree with a known master classification; unknown remains unknown. Optional marketing person uses active Employee with explicit employee-read permission. Requested delivery and quotation validity dates are entered dates, not approved commitments. Multiple exact product lines carry quantities, units, net prices, customisation and specifications; optional model revision must be sealed and match the output unit.

Costing links point to one immutable owned COSTING revision. Currency, variant, unit, quantity, specifications, customisation and model revision must match exactly and unambiguously. The linked source snapshot/hash is retained; it is explicitly an unapproved estimate. Changing master values or later costing revisions does not change historical quote/order prices. A quotation reference on an order resolves only an owned quotation revision, then fails closed because approved quotation linkage is unavailable in v1.

Optional stock identity references reuse existing StockIdentity/warehouse scope checks and explicit inventory read capability. Variant, unit and company/customer ownership must match; the snapshot contains identity/version/warehouse and `reservation:false`. This is a reference, never a stock availability, allocation, QC-release or fulfilment promise. Warehouse/inventory identity schema and guards are unchanged.

Implemented transitions:

- DRAFT → REVIEW (`submit`).
- REVIEW → DRAFT (`reopen`), retaining the submitted snapshot as a separate historical revision.
- DRAFT → CANCELLED (`cancel`), terminal. Review must be returned to draft before cancellation.
- Only DRAFT accepts commercial edits. Every edit requires the latest quoted version and a reason.

Reserved future concepts: APPROVED/CONFIRMED, customer-facing SENT/ACCEPTED/REJECTED, governed confirmed amendments/cancellation and supersession. No endpoint can enter these states. Authority policy, independent review roles, discount/credit ceilings, operational feasibility checks and customer acceptance evidence must be approved and separately implemented before enabling them. Job Cards may later cover whole orders; production for stock may have no order. Neither is executed here.

## HTTP contracts

Base `/api/v1/commercial/documents/`, existing JWT bearer authentication and structured errors.

- GET list: existing pagination (`count`, `next`, `previous`, `results`); GET `/{uuid}/`: exact current snapshot and ETag.
- POST: `{kind, data, reason}` with `Idempotency-Key`.
- PATCH `/{uuid}/`: `{data, reason}`, complete replacement of declared editable document input, with `Idempotency-Key` and `If-Match: "N"`.
- POST `/{uuid}/transition/`: `{transition, reason}`, same two headers.
- GET `/{uuid}/history/`: paginated immutable full revisions, actor, timestamp, reason and hash.

Declared `data` fields: currency, money_places, rounding, customer OR prospect, optional classification/marketing_person/quotation_revision/requested_delivery/validity_date, terms, discount, lines. Each line: variant, unit, quantity, unit_price, specifications, customisation; optional model_revision/costing_revision/stock_identity/requested_delivery. COSTING lines require `costing` with materials, processes, waste_percent, rejection_percent, assumption_evidence and markup_percent. Material inputs: material, unit, price_unit, currency, quantity, price. Process inputs: description, currency, amount. Each list is bounded to 100 lines/components. Unknown fields fail validation. Snapshot-only fields are never accepted as editable input.

Creates return 201; successful edits/transitions 200. Same actor/key/payload replays the saved response; conflicting intent 409. All semantic inputs and version preconditions are hashed. Authorization and owner scope are rechecked on replay; lookup/calculation is not rerun against changed masters. Missing precondition 428, stale version 412, unavailable transition 409, validation 400, absent/foreign owner 404 and denied/unstamped context 403. Concurrent writers serialize on catalog/aggregate locks; only one edit wins a given version. No email/provider call, PDF renderer, reservation, ledger posting or job engine is invoked.

## Frontend boundary

`/commercial` is reachable for backend sessions via the existing shell. Existing demo costing/quotations/orders are preserved separately. The new page uses existing JWT Axios transport, string amounts, server snapshots, create/edit/review/reopen/cancel, paginated records/history and unchanged-intent retry keys; it displays unavailable approval, tax totals, PDF/email, dispatch and production. A bounded basic editor supports one material and process amount per costing line; the API supports multiple. Advanced API-created drafts with fields the form cannot preserve are refused by that editor. UUID revision entry and detailed snapshot history are development controls, not a client-approved customer template. API adapter acceptance does not establish browser visual acceptance.
