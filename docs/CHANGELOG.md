# Changelog

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
