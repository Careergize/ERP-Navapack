# Changelog

## Persistent quotation drafts — 16 October 2026

Connected quotation Save Draft, edit and list reload to Django database storage. Added QuotationDraft model/admin/API, source-preserving editor serialization, optimistic edit checks, submitted-draft freeze and server decision restoration. Replaced session-only save success wording for real users with confirmed database-save messages.


## User roles and quotation rejection — 16 October 2026

Added the Role master and Project Manager user assignment. Connected Masters → Users to real user/role APIs with password validation. Expanded quotation manager review to show document details and Approve/Reject actions, rejection reasons and decision history filters. Rejected quotations are blocked from email/WhatsApp delivery.


## Editable quotation selling price — 16 October 2026

Removed the custom-product unit-price read-only restriction on quotation drafts. Added decimal-friendly entry and explicit manual-price handling while retaining costing checks and manager approval.


## Real superuser login — 16 October 2026

Real Django login is now the default; demo mode requires explicit VITE_ENABLE_MOCK_LOGIN=true. Added local frontend API configuration and clearer credential/backend/throttle errors. Existing superusers carrying the inherited receptionist default are presented as admin in the authenticated profile; backend permission/manager approval rules remain enforced. No password was changed.


## Quotation units and line totals — 16 October 2026

Added backend Unit model, default units, admin/API and Masters → Units management. Quotations load units from the backend, show VAT-inclusive unit price and quantity × unit-price line totals. Server validates unit identity and computes line amounts; PDF headers explicitly state VAT basis and preserve six-decimal entered price precision.


## Quotation manager approval and saved customers — 16 October 2026

Added manager approval inbox and durable quotation submission; only the Production Manager can authorize email/WhatsApp delivery. Removed sender PDF self-approval; changed snapshots require fresh approval. Added persistent new-customer creation from quotations, extended customer fields, shared customer API loading/master editing and quotation-master links.


## 2026-10-15 — Keep login across refresh

Fixed the redirect to login caused by memory-only user state. Added startup profile restoration/loading guard, shared JWT renewal, complete invalid-session cleanup, tab/persistent Remember me behavior and guarded demo-session restoration. Verified browser refresh/logout, focused authentication checks, TypeScript and production build.


## 2026-10-15 — Reference quotation PDF and selected delivery

Added native reference-style A4 PDF, public snapshot persistence and structured sales-order extraction in the sibling Django backend. Quotation detail now offers PDF / Email / WhatsApp with independent checkboxes and editable +916282744675 recipient. Server PDF approval, SMTP attachment, Meta document-template submission and durable per-channel attempt results prevent false success and duplicate replay. Updated contact field types and photo-derived company/bank defaults. Live provider configuration remains required; existing frontend commercial records remain session-only.


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
