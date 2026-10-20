# Phase 4A gap analysis — before implementation

20 October 2026. Scope: synthetic development only; no operational approval.

## Evidence reviewed

README and both application guides; backend architecture, development status and decision log; Phase 3A handover and 3B–3E reports, release readiness and client decisions; masters/specification/core/account/inventory implementation and tests; React costing, quotation, commercial pricing, sales-order and authentication adapters and workflow documentation.

All 28 originals match CLIENT_SOURCE_MANIFEST.json on this review. Read original SOP 01 (authority), 02 (sales), 05 (production), 15 (dispatch), 16 (invoicing) and 17 (finance) from DOCX XML without modifying sources. Stock workbook cell mappings remain evidence of observations, not authorized stock, costing rates or commercial policy. SOP effective date is 1 November 2026; adoption remains unresolved.

## Findings and bounded response

- Backend Customer/Prospect, exact ProductVariant/Unit, immutable specification revisions, Employee, explicit capabilities, JWT, transactional command/audit, idempotency and row-version infrastructure already exist. Reuse them. Inventory identities and warehouse scopes must remain independent of commercial demand.
- No commercial backend aggregate exists. Existing quotationApi expects legacy `/quotation-drafts/` and `/quotations/` contracts absent from this repository. Historical documentation about a sibling Backend app does not establish an installed API. Add a separately namespaced foundation; do not wire incompatible demo payloads into persistence.
- Frontend has multi-line orders, versioned session costing, quotation revisions, customisation, markup versus gross margin and commercial snapshots. JavaScript Number arithmetic and role labels are unsuitable as server authority. Preserve these demos; add a real-session foundation entry point using the existing JWT transport.
- LED evidence conflicts: current request says fixed amount per 1,000 units; led.ts and dated frontend documentation say USD70 per tonne and 2.5%. The old spreadsheet commentary quotes C25 MAX(0.07,C24*2.5%). None establishes a compatible approved currency/base/conversion/FX/VAT rule. Record all interpretations, calculate no authoritative VAT/LED or final payable total.
- SOP 01 §§3.2/3.8 requires independent approval under an approved matrix, without monetary ceilings. SOP 02 requires documented requirements and governed confirmed-order changes. Existing Admin/Accounts demo roles are not approval authority. Block approval/publication and confirmed-order amendments entirely in 4A.
- Phase 3E has API acceptance but incomplete browser acceptance and unresolved operational policies. Reuse its stamped disposable environment gate; do not alter ledger, QC, reservations, dispatch or production services.

## Implementation contract selected

One commercial app with typed COSTING/QUOTATION/SALES_ORDER aggregates, immutable numbered revisions and explicit validated line snapshots. Owner-only employee access is a conservative development boundary, not an approved customer/tenant visibility policy. Decimal estimates use explicitly selected currency and rounding, no FX or unit conversion. DRAFT → REVIEW, REVIEW → DRAFT (new evidence revision), and pre-approval cancellation only; approved/customer-facing states remain unavailable. A costing link preserves an exact revision and checks source identity/quantity/unit/currency. Quotation-to-confirmed-order integration remains blocked until approval policy exists. No stock writes or operational integration.

Uncommitted Phase 3E work existed at entry and must remain preserved. No schema changes will be applied to the configured application database. Migration validation occurs only in newly created disposable PostgreSQL databases.
