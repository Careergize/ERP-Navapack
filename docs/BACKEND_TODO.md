# Backend Integration TODO

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
