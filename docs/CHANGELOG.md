# Changelog

## Confirmed LED MAX / Finance demo — 2026-10-15

- Made client-confirmed Higher of the Two the default for applicable LED; centralized 2.5% versus USD 70/tonne × saved FX with mandatory weight/conversion validation and configurable pending percentage base.
- Connected frozen LED calculations/FX through costing, stock analysis, quotations, Sales Orders and partial invoices without double VAT.
- Connected the existing finance workspace to separate demo login/accounts entry, home navigation and read-only quality summary; preserved real authentication and QC permissions.
- Added focused MAX/tax/snapshot/demo regression coverage and updated existing costing/tax/backend/report documentation; no backend or automatic commit.

## Integrated operations — 2026-10-15

- Added versioned product/model KG–CTR conversions, stock VAT/LED/markup/margin/COP snapshots, evidence-based actual totals and product alert policies.
- Added confirmed dispatch without prior reservation, preserving dated/batch/QC guards and reversal history; classified new non-sales OUT.
- Replaced static operational dashboard aggregates with six current-state sections; added shared sales summary, connected ID-based trace navigation, stage timelines and multiple execution runs.
- Added source-idempotent quotation generation, reviewer rejection/change comparison and customer-safe email drafts/mailto without delivery claims.
- Added configurable QC frequencies, explicit idempotent schedules/daily counts and inactive KSEC placeholder. Updated report/backend requirements and integrated regression coverage; all state remains session-only.

## Quotations / Proforma Invoice — 2026-10-13

- Added dedicated commercial quotation screens, approvals, customer responses, immutable revisions, A4 preview and accepted-revision order conversion.
- Reused costing before an order exists; adopted approved source references into real order/job flows without duplicate pricing or fake orders.
- Shared customer/prospect/company/bank/terms settings and explicit VAT/discount snapshots; preserved basis through converted orders/partial invoices.
- Added live quotation metrics/CSV, focused regressions and report/backend specification; missing reference documents/layout verification and all backend persistence remain outstanding. No dependencies or automatic commit.

## Quality Control — 2026-10-13

- Added same-login QC roles, dashboard/navigation and category/template/inspection/review/action/report screens.
- Added versioned checklist snapshots, negative-answer/numeric sample validation, immutable review and correction history.
- Connected raw receipt holds, mandatory production QC/machine guards, separate quality/final-stock authorization and traceable Store receipts/held-batch dispatch.
- Added Excel-readable XML/browser PDF printing, focused QC regressions and canonical proposed Django/DRF quality architecture/contracts; no backend implementation or new dependencies.
- Source photographs were not present; templates remain provisional and all state resets on refresh.

## 2026-10-13

- New manufacturing lines share one parent Job Card per Sales Order, retaining independent costing, routes, materials, units, tracking and batches.
- Parent list/detail show separate item progress and combined history; approval requires complete manufacturing scope and completion requires all items.
- Preserve historical cards; retain parent/item references on new receipts. Add focused regression coverage.
- Partial client-workflow delivery: amendment, internal production, additional issues, FG authority, unreserved dispatch, exports and dashboard phases remain pending (see sales-fulfillment.md).

## Unreleased

### Added

- Job Card manufacturing tracking: calculated summaries and filters, five detail tabs, approval/material issues, data-driven stage updates and handovers, waste/activity history, delay warnings and frontend stock confirmation. Existing sample cards and routes retained.

- Consumables navigation and frontend Add/Edit/View, category/unit filters, Stock IN/OUT and movement history.
- Raw Material Filter/reset controls with combined family/unit/status/search filtering, Stock in Hand wording and selected-record details in both stock forms.
- Finished Goods Brand → Pieces → Packaging columns and CSV export; optional pieces per package entered on Stock IN and prefilled on Stock OUT without changing inventory calculations.
- Code-verified documentation baseline for architecture, business rules, frontend models, development status and backend integration work.
- Agent instructions requiring targeted documentation maintenance alongside meaningful changes.

### Changed

- Corrected README claims about module placeholders, backend integration and Android packaging to match the current repository.

This baseline does not assign release dates or reconstruct feature history. Existing finished-goods source interpretation remains in finished-goods-reference.md.

## 2026-10-09

- Added manual per-line sales fulfillment, linked manufacturing drafts and shared QC receipt batches.
- Added reservations, partial dispatch/reversal history, configurable invoices, trace links and reserved/available stock with custom history ranges.
- Added fulfillment regression checks; all transactions remain session-only. See sales-fulfillment.md.

## 2026-10-09 — Custom costing and routing

Added shared revisioned custom models, per-line USD/UGX costing and markup comparisons, printable redacted estimates, separate approval/customer response, linked draft jobs and PM-controlled dynamic routing/reapproval. Added QC-prepared receipt mapping and explicit unavailable actual costing. Workbook ambiguities stay configurable. New regression checks cover costing/model/estimate/routing behavior; existing stock/sales checks remain passing. See [implementation notes](custom-costing-routing.md).
