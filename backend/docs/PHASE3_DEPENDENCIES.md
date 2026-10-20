# Phase 3 dependencies and client decisions

20 October 2026. Phase 2 supplies master identities, immutable specifications and source
staging. It does not approve SOP, import company stock, establish usable stock, authorize
production or certify pricing/tax/quality rules.

## Sources actually reviewed

Reviewed backend README, AGENTS, architecture, API conventions, auth/permissions,
decision log and development status. Reviewed frontend planning data models, database
blueprint, API blueprint and SOP gap analysis, plus actual types/index.ts,
ModelsContext, CommercialContext, InventoryContext, ConsumablesContext, CostingContext,
productModels, customCosting and productionRouting; inspected finishedGoodsData,
rawMaterialData, consumableData, mockData, generated reference samples,
finished-goods-reference notes, customersApi and extraction scripts.

No original XLSX/XLS/CSV/PDF client source was present in tracked repository discovery.
Originals named by secondary code evidence only:

- `09.FG Stock September .xlsx` (generated FG reference/notes/extractor available).
- `08- September 2026  Daily Raw Material Physical stock  -.xlsx`
  (generated raw reference/extractor available).

Neither original workbook was opened/reviewed or imported. No controlled original of
the 18 SOPs, eight QC photos, quotation/proforma/Sales Order originals or signed authority
matrix was available. Generated arrays and prior transcriptions cannot prove compliance.
All fixture values in tests are synthetic and live only in disposable test databases.

## Decisions needed before authoritative source application

1. Confirm original workbook ownership/version, effective dates, corrected/inferred units,
   approved variant groupings and duplicate resolution. Supply explicit product/variant,
   raw grade, consumable, customer/supplier and source-ID mappings. Confirm repeated
   descriptions represent duplicate identities or separate variants; never infer from names.
2. Approve Unit names/codes/dimensions and exact usage, including ctn/pcs/kg/Each/Both/
   Litres/Kilos. Approve any explicit future conversions separately; pieces per package
   does not establish mass. Confirm decimal precision for future costing/stock arithmetic.
3. Assign capabilities through trusted provisioning. Approve shared-catalog access or
   specify company/tenant/department object boundaries before broader deployment.
   Decide prospect promotion authority, who may approve imports and whether independent
   maker/checker is mandatory. No business roles, limits or independence policy seeded.
4. Confirm equipment/area/department identities, machine classifications and optional
   manufacturing routes; approve specification defaults/rates/currencies and revision
   governance. Missing costs/settings/tolerances remain absent.
5. Establish original-binary evidence storage, file review/malware controls, retention,
   audit export and idempotency retention. Current staging stores parsed cells and digest.
   Specify retention for previous full review previews if required; audit retains events,
   not complete past source/mapping snapshots. Production DB runtime must be restricted.
6. Approve a separate frontend UUID/header adapter scope. Current customer persistence
   code assumes numeric IDs and an incompatible retry/version contract. No frontend
   integration was silently changed in this phase.

## Recommended next implementation scope

Phase 3 should begin with approved warehouse/location, batch/lot and stock-unit identities,
source reconciliation and separately governed opening-balance evidence. Keep unknown
opening quantities unknown and block availability-dependent commands when facts are
missing. Do not manufacture openings from blank cells or demo movements.

After written workflow/authority decisions, implement a narrowly scoped immutable
inventory ledger and balance projection with receipt/adjustment/reversal commands,
source uniqueness, version locks, backdating/unknown/negative-stock policy and PostgreSQL
concurrency/rollback/reconciliation tests. An approved master import must remain separate
from a later separately authorized opening/ledger command. Determine raw receipt QC hold
boundaries before describing any material as usable. Stock posting needs explicit scope.

Subsequent phases can reference exact ProductVariant/Material/Unit and ProductModelRevision
UUIDs for Sales Orders, estimate snapshots, Job Cards, production routes/runs, QC and
dispatch. Each needs its own approved SOP/state/actor matrix and atomic acceptance tests.
No Sales Order, Job Card, stock movement, opening transaction, run, QC release, dispatch,
invoice or costing calculation was implemented in Phase 2.


Employee extension: approve named Master Admin operators, business delegation ceilings,
role-permission policies and independence choices before using employee role APIs. Recovery
transport/verification/expiry, privileged-account maintenance, employee numbering/privacy,
MFA/SSO and scoped directory access remain operational/client decisions. Existing source/SOP
availability findings are unchanged. See EMPLOYEE_ADMIN.md for implemented technical safeguards.


## Phase 2.1 readiness note

Canonical import review and governed role-capability publication address technical
exit-audit defects. Phase 3 remains gated by an approved reproducible release, controlled
SOP originals, client authority/membership matrix, actual source workbooks and explicit
inventory/QC/location/lot/opening/concurrency policy. No ledger or posting work began.
See ../../docs/PHASE_2_1_REMEDIATION_REPORT.md and PHASE21_FRONTEND_CONTRACT_PLAN.md.
