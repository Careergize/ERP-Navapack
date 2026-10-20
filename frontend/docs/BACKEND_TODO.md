# Backend Integration TODO

## Phase 3A handoff — 20 October 2026

Implemented real warehouse/location/stock-identity configuration and scoped history APIs/UI plus relevant auth/UUID/pagination/version/idempotency adapters. Pending: reviewed scope request/publication/revocation workflow and approved assignments, operational identity marking, deployment migration/browser acceptance, restricted runtime-role tests, remaining master adapters and future inventory ledger/QC/opening workflows. No actual stock posting or opening correction is enabled. Do not re-enable demo routes for real sessions as a substitute for backend integration.

## Persistent quotation drafts — 16 October 2026

Implemented durable editable draft storage and read/save endpoints using quotation view/add permissions and owner scoping. Optimistic versions plus row locking prevent stale overwrite; exact save replay is idempotent. Submitted snapshot IDs cannot be edited. Manager approval/delivery still uses immutable Quotation snapshots. Existing historical PDF snapshots without editor metadata are not automatically reconstructed as editable drafts. Full family numbering/lifecycle/conversion services remain pending.


## User roles and quotation rejection — 16 October 2026

Implemented accounts.Role (active named code and permission set), User.assigned_role, role permission backend, superuser-only /api/users/ and read-only /api/roles/. Seeded/mapped existing roles. Quotation reject action stores reason/actor/time with terminal snapshot guards; pending/all-submitted filters support the manager review inbox. Full immutable review-event history, quotation-family revision service and persistent editor drafts remain separate follow-ups.


## Editable quotation selling price — 16 October 2026

Frontend now supports explicitly entered custom selling prices with approved-source checks. The existing backend snapshot manager reviews final public prices; authoritative backend custom-cost source/override policy remains part of the pending full commercial service.


## Quotation units and line totals — 16 October 2026

Implemented erp.Unit and /api/units/ CRUD without deletion, active filtering, unique case-insensitive stable codes and default unit seed migration. Quotation snapshots validate active unit identity and store unit_id/code plus server-computed lineTotal and unitPriceInclVat. Product.unit remains the existing legacy text field; product/stock conversion services and normalized line tables are outside this change.


## Quotation manager approval and saved customers — 16 October 2026

Implemented snapshot submit, pending-manager list, manager-role/permission approval, and server-enforced delivery approval. Backend Customer now stores full quotation contact fields with generated codes/idempotent creation; quotations can link to the saved master. Full family revision/supersession, acceptance/conversion backend and production delivery configuration remain pending.


## Authentication session integration — 15 October 2026

The frontend now restores GET /auth/me/ identity and uses POST /auth/refresh/ for access expiry against the sibling Django backend. Invalid refresh credentials clear local tokens; outages retain them for retry. Mocked transport checks and browser demo refresh/logout are verified. Production authentication deployment, cross-tab refresh coordination and remote token revocation at frontend logout remain separate follow-up work.


## Implemented PDF delivery slice — 15 October 2026

The sibling `../Backend/quotations` app now exposes structured order extraction, public snapshot create/list/detail, native PDF, server PDF approval and selected-channel send endpoints. Email/WhatsApp submissions use configured SMTP/Meta transports with durable attempts and request replay protection. Setup is required before live delivery. This does not complete the proposed six-entity quotation lifecycle, backend custom-cost source checks, conversion or family revision service listed below. See `../Backend/quotations/README.md` for actual contracts.


Planned work, not implemented APIs or database design. Check items only after verified integration.

## Sales Orders

- [ ] Durable order/header/line persistence and authoritative order numbers.
- [ ] Shared customer, employee/marketing and finished-goods master integration.
- [ ] Persist requisition references, validate totals/units and define order status lifecycle.
- [ ] Link orders to job cards; decide whether external accounting export is required.

## Finished Goods Stock

- [ ] Authoritative variant master retaining source provenance and repeated identities.
- [ ] Confirm and persist optional pieces-per-package metadata independently of ledger quantities and units.
- [ ] Transactional Stock IN/OUT, validation, balances and movement audit history.
- [ ] Monthly reports and server-side demand projection.
- [ ] Reconcile unknown Packing openings/dates and ambiguous source records before import.
- [ ] Define cumulative reservations/allocation across competing orders.

## Consumables

- [ ] Persist consumable masters, categories, units, opening balances and stock movement audit history.
- [ ] Validate dates, positive quantities and posted unit/opening immutability server-side.

## Raw Material

- [ ] Master with specific Virgin Material grades, Recycled Granules and Ink.
- [ ] Durable Stock IN/OUT, balances, movement history and monthly reports.
- [ ] Confirm unknown openings, minimum levels and treatment of legacy demo granules.
- [ ] Link confirmed store issues/production consumption and recycling output to movements.

## Job Cards and Production

- [ ] Verify existing frontend read/stage-write expectations with actual server contracts.
- [ ] Persist per-card model/points routing, requiredMaterials, dynamic productionStages, approvals, handovers and stage waste.
- [ ] Supply authoritative BOM/points requirements and availability; define partial issue and replenishment rules.
- [ ] Enforce role permissions, chronology, immutable completed stages, units/conversions and transactional lifecycle transitions server-side.
- [ ] Persist durable activity history and prevent duplicate/replayed material issues or stock transfers.
- [ ] Resolve finished-goods variant references and post accepted quantity as Stock IN with job/sales-order/customer/model/product/batch references.
- [ ] Connect stage waste/recycling quantities to real Recycling transactions; keep quantities and units reconciled.

## Recycling

- [ ] Durable waste intake, collection, granule production and disposition records.
- [ ] Confirm restock/external sale rules and reconcile batch quantities with raw inventory.
- [ ] Supply accurate filtered summaries.

## Costing

- [ ] Durable costing records and manually entered exchange-rate history.
- [ ] Confirm local currency, cost/rate effective dates and authoritative calculation rules.
- [ ] Report write failures accurately; decide how rate changes affect existing records.

## Masters, Dashboard, Trace and Authentication

- [ ] Shared durable item/model/customer/supplier/department/user masters and validated relationships.
- [ ] Live role-scoped dashboard metrics; remove independent demo values.
- [ ] Trace history linked to real order/job/material/granule events.
- [ ] Verify real authentication, session restoration, token expiry/refresh and complete 401 cleanup.
- [ ] Enforce permissions server-side; navigation filtering is insufficient.
- [ ] Replace fallback/local success paths with explicit production error handling.

## Important Inventory Decision

Confirm the authoritative workflow before implementation:
Sales Order -> Job Card -> Production -> Store Issue -> Finished Goods -> Dispatch.

This is a decision checklist, not a proven posting sequence. Determine event ordering, exactly when demand becomes reservation, when raw materials are deducted, when finished goods are received/deducted, and how cancellation/reversal avoids duplicate posting.
Sales Order creation itself must not deduct stock. Current demand comparison creates no reservations.

## Sales fulfillment frontend boundary

[Sales fulfillment](sales-fulfillment.md) now demonstrates linked demand/jobs/receipts/reservations/dispatches/invoices in session state. Backend work must supply atomic posting and reversal operations, idempotency, reservation locking, authoritative numbering/master identity, persistent invoice snapshots and server permissions. No new endpoints or API contracts are claimed. Confirm QC/locations/BOM yields/tax/credit notes/cancellations and partial stage rules before production use.

## Custom costing and routing integration

Persist revisioned models, line-linked estimates and immutable financial/routing snapshots with independent customer response. Enforce role/revision/concurrency checks server-side. Integrate atomic raw-material issue/consumption, actual process/expense costing and exact finished-variant configuration. Persist idempotent QC receipts and approved stage history without losing the frontend references. No new endpoint or schema was implemented. See [detailed boundaries](custom-costing-routing.md).

## Client-confirmed target — 12 October 2026

One parent Job Card per Sales Order with durable item-level references and independent routes/units. Persist and enforce parent uniqueness, complete manufacturing scope, atomic approvals, audit history, item-level costing revisions and inventory source references. Migrate historical multi-card orders only through an authorized trace-preserving procedure. Manufacturing-only inclusion for mixed orders requires client confirmation. Frontend parent/item state is demonstrative.

The confirmed posting sequence is demand → parent Job Card → PM approval → material issue → sequential production → Supervisor/Manager finished approval → Finished Goods IN → confirmed dispatch/OUT. Production for stock requires no fabricated Sales Order. Reservations are not mandatory. Replace earlier reservation/QC decision placeholders with these confirmed rules when implementing their pending frontend/backend phases. Persist additional issues, batch/run history, authorized excess decisions, order amendments and atomic idempotent Stock IN/OUT with server roles and concurrency validation. No API/schema changes were made in this phase.

## Dedicated quality app — proposed contracts, not implemented

- [ ] Implement the canonical eleven QC entities/action audits and source FKs described in [quality.md](quality.md), reusing production/inventory/masters/accounts/reports/recycling ownership.
- [ ] Provide authoritative raw supplier/batch/receipt and production run/stage/finished-batch identity; preserve template snapshots and submitted findings.
- [ ] Enforce QC Inspector/Supervisor assignment scope, independent review, NC verification and separately mapped final FG managerial authority on the server.
- [ ] Implement atomic raw holds/releases, production checkpoint guards, cumulative batch authorization and inventory-owned idempotent Stock IN/OUT with concurrent hold rechecks.
- [ ] Implement proposed DRF actions, paging/filters/errors/version conflicts/idempotency and evidence/report storage; no QC endpoints are called by the frontend.
- [ ] Reconcile historical raw receipt QC/opening availability, seed IDs and manual import receipts before production deployment; never assume rejected material was returned or discarded.
- [ ] Supply eight photographs and resolve sampling/concession/partial-disposition/schedule/role/retention policies; implement native XLSX/PDF exports and scoped report scheduling if required.

The QC frontend now separates independent quality release, Production Manager/Admin FG authorization and Store stock posting. Earlier notes treating Store confirmation alone as acceptance describe superseded frontend behavior. All new states/actions are session-only; see quality.md for transaction boundaries and retry behavior.

## Quotation business logic in future sales app

- [ ] Persist the six quotation entities and immutable source/company/customer/terms/price/tax snapshots in [quotations.md](quotations.md), reusing Customer/Prospect/Product/Model/CostEstimate/SalesOrder/User/CompanySettings.
- [ ] Enforce exact revision/source/expiry/approval/customer-response policy and authorized numbering/manual prices on the server; printing/sending must not imply acceptance.
- [ ] Implement proposed DRF contracts, paging/filters/version conflicts and immutable public document projection; no quotation endpoints currently exist or are called by the frontend.
- [ ] Make conversion atomic and idempotent with one order per quotation family, adopted costing references, explicit prospect/customer linkage and audit/outbox. Never create Job Cards/stock/invoices at quote creation or conversion.
- [ ] Preserve inclusive/exclusive VAT/discount/rounding through order and partial/final invoice workflows using server decimals; define quantity/currency precision and adjustment/credit-note policy.
- [ ] Verify the two missing reference documents, company/bank/TIN/signatory, terms/credit/tolerance/expiry/acceptance evidence and conversion KPI policy; supply durable PDF/report/communications services if required.

## Integrated operations contract requirements — 15 October 2026

See the existing [integrated report](sales-fulfillment.md#future-backend-ownership-requirements-and-transaction-boundaries) for the canonical incremental contract, domain ownership and transaction boundaries. No new server endpoints/schema are claimed. Required capabilities: versioned product/model conversions, exact-unit thresholds and alerts/observed consumption; immutable pricing/LED/FX/VAT/profit snapshots and actual-cost evidence; grouped sales/operational aggregates; stable-ID trace lineage/exceptions; atomic execution-run accumulation/stage handover; source-idempotent quotation generation/review history; secure expiring/revocable revision-specific customer links; customer-safe PDF/email outbox/provider/status/retry history; QC schedule and occurrence generation/assignment.

Server must independently authorize actors, validate IDs/expected versions/request keys, recalculate decimal amounts/KG/balances, lock affected order/batch/stage/quality records and atomically publish ledger/audit changes once. Freeze historical financial/conversion snapshots. Failed dispatch/receipt/run/release/conversion must roll back. Durable QC holds and separate final stock authority cannot rely on React. Email uses authorized senders/provider idempotency/webhooks, never draft success as delivery. Customer access is narrowly projected and logged. Recurrence needs authoritative calendars/shifts/assignment and unique schedule/date/shift. Real raw consumption, material-batch allocation, expenses and confirmed order status/amendments remain gaps.

## Confirmed LED MAX / finance follow-up

Enforce client-confirmed `MAX(base×0.025, eligibleKG/1000×70×savedFX)` centrally. Percentage-base definition remains pending; keep explicit versioned configuration, product scope and VAT-on-LED. Reject missing weight/conversion/FX/date; no percentage fallback. Snapshot both alternatives/selected branch/rates/FX/date/conversion/base with costing revisions and accepted quotation/order records. Preserve history; allocate original LED across partial invoices with final Decimal reconciliation and no double VAT. Authoritatively validate source versions and permissions; do not trust client snapshots or migrate old financial amounts silently. Finance demo adds no backend: provision accounts credentials/permissions and real session handling through existing authentication integration. See the canonical report for details.
