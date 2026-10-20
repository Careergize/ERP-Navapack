# Phase 3 inventory architecture

## Current Phase 3C-1 synthetic workflow slice — 20 October 2026

OperationRequest, immutable OperationLine and OperationDecision now separate physical evidence/verification/investigation/confirmation/independent review from selected Procurement recording. Internal submit/transition services and guarded paginated APIs reuse the unchanged3B ledger/command/audit/scope boundaries. All requests/actions/reads are synthetic-only; authenticated mode is safe outside deployment. No QC acceptance/release, live authority matrix or fake upstream records. Real frontend forms/history embedded in existing Admin inventory session show unavailable state outside isolated context. See [implemented contracts and limits](PHASE_3C_IMPLEMENTATION_REPORT.md). Full operational architecture below remains proposed beyond this slice; no3D/3E.

## Implemented Phase 3B boundary — 20 October 2026

A synthetic-only internal ledger now exists, with immutable policy/source/approval-fixture/header/line/entry evidence, explicit opening completeness and replaceable custody projections. Registration warehouse/location remain provenance. Current custody is separate; transfer never edits identity. Existing full identity/configuration history stays registration-scoped; the internal destination reader discloses only minimal identity and destination entries. Ledger evidence is not exposed through configuration/global Admin readers. No operational routes, QC engine, upstream fake records or grants were added. See [actual implementation and limitations](PHASE_3B_IMPLEMENTATION_REPORT.md); complete domain designs below remain proposals beyond this slice.

## Current Phase 3A implementation boundary — 20 October 2026

A quantity-free inventory app now supplies warehouse/location configuration, immutable typed StockIdentity ownership/source/parent references, scope enforcement and history. Ownership is separate from custody; UNRESOLVED is explicit and all identities remain operationally unavailable. No new organization model, fake source workflow, live grant or stock quantity was created. Shared master identity/command/audit/RBAC infrastructure is reused. Scope proposal/publication/revocation is an isolated pending extension; the rest of the proposed ledger/QC architecture remains future work. See PHASE_3_IMPLEMENTATION_PROGRESS.md and ../../backend/docs/PHASE3A_API.md for actual schema/API/UI rather than treating the complete design below as implemented.

Classification key: [S/W/I/A/D](PHASE_3_REQUIREMENTS_TRACEABILITY.md#evidence-convention-and-document-ownership). Date: 20 October 2026. All design below is **A — Proposed architecture** unless stated otherwise.

## Boundaries and reuse

I — Existing Django apps are accounts, core, masters, specifications and imports. Reuse UUID User/Employee, governed Role/Membership, ActionPermission, `require_independent_actor`, `execute_command`, version/ETag helpers, AuditEvent, Unit, Material, Consumable, ProductVariant, Supplier and immutable ProductModelRevision. Product is generic; ProductVariant is exact FG identity. ProductModel is a specification/recipe identity, not a stock SKU. Area/Machine describe organization/equipment, not approved custody locations. Global shared catalog does not establish tenancy or location authorization.

A — Add `inventory` for identities, lots, custody portions, evidence, ledger and reconciliation; add `quality` for controlled templates, inspections and gate decisions. Keep one Django project/PostgreSQL transaction boundary. No new accounts/master/import implementations and no root build manager. Source-reference contracts enable later procurement, production, sales, dispatch, recycling and maintenance apps without inventing operational records now.

## Custody and quantity design

Use three independent axes: item identity; physical custody/location; quality/authorization gates. A lot can span locations and contain multiple disjoint portions. Quality is not encoded solely by warehouse name or one mutable batch status. InventoryItemIdentity points to exactly one existing Material, Consumable or ProductVariant; future WIP identity needs approved specification/stage identity, not a fake FG variant. Base units are frozen once used; conversion transactions deferred until exact item-specific factors are approved.

Unknown opening coverage is explicit per item/location/unit/cutoff. It is not a zero ledger entry. Independently evidenced new receipt portions can be known, but overall stock remains incomplete; consuming disputed historical portions is blocked. Balances always carry completeness and coverage metadata. See [ledger rules](PHASE_3_LEDGER_AND_STOCK_RULES.md).

## Raw-material lifecycle

S — SOP 03 §§4,6–9,04 §§7–8,05 §§6–10 establish the following responsibilities.

A — Physical receipt → Stores measured GRN evidence (supplier, approved purchase/requisition reference, actual quantity/unit, delivery/condition, receiver and checker) → discrepancy resolution → PO recording of actual custody receipt → required-QC awaiting/held partition → independent QC inspection/clearance → available raw portion → authorized issue and receiving acknowledgement → separately tracked WIP custody → later actual consumption, unused return, waste or reject disposition.

Receiving into physical custody while awaiting QC must remain visible without becoming usable. D10 must approve whether a held receipt can be finalized as custody stock or stays in an unposted physical-evidence queue pending resolution of “accepted quantity.” No conflict may be silently finalized; backlog is explicit and reconciled. QC clearance never creates another receipt.

An issue moves material, unchanged identity/unit, from Stores custody to a separately approved production custodian/location. It does not consume material or create FG. Phase 3 can record externally authorized issue/return evidence once D08 is resolved; it cannot invent a Job Card, run or production order. If no valid source/evidence exists, block issue. WIP execution, conversion/yield, actual consumption, extra issue planning and waste-generation engine are later scope. Additional issues are separately authorized source allocations, not increases to an already posted issue.

Unused returns link issue line and remaining issued quantity. Uncertain condition enters awaiting-QC, irrespective of the original issue’s released status. Return does not reverse historical consumption or count as a supplier delivery. Legitimate return is a real movement; a reversal corrects an erroneous recording and needs separate approval.

## Finished-goods lifecycle

S — SOP 03 §8,05 §10,10 §10,11 §§6.7,7 require identified completion/transfer, measured Stores receipt and QC before dispatch where required. They allow custody of goods awaiting QC. A blanket separate final-stock managerial signature is not specified; D10 determines where delegated policy requires it.

A — Future production completion with exact ProductVariant/approved revision and batch lineage → QC inspection/release of identified scope → separate managerial/commercial authorization where required → actual Stores receiving acknowledgement → PO system Stock IN → available only when all applicable gates are satisfied. If actual custody occurs earlier, record held custody or evidence backlog under D10, rather than fabricating event order or released quantity. No duplicate IN on later clearance.

Partial receipt lines allocate a bounded quantity from the same completion/transfer source; later receipt uses remaining authorized quantity. Partial external dispatch similarly consumes remaining authorized FG requisition/SO line quantity and exact released portions. A new Sales Order creates demand only. Reservations are deferred; current UI allocations do not establish approved reservation policy.

S/D — SOP 16 §5 puts reception handover before invoice/payment and external exit, and requires an officer unconnected to Stores/front office. SOP 15 §9 qualifies dispatch-entry independence with staffing where possible. D11 resolves staffing and tracked custody/stock-OUT timing without weakening mandatory clearance.

A — Recommended distinction: Stores→reception is an internal tracked transfer; premises→customer/carrier is company physical OUT. Reporting may show Stores custody OUT separately. Never subtract company physical stock twice. Enable external dispatch posting only in a separately authorized later dispatch module after document/payment/credit/checker controls are available; Phase 3 provides ledger contracts and controlled evidence interfaces, not a sales execution shortcut.

## Production and recycling interfaces

S — SOPs 05–10 specify route per job. Slitted rolls cannot go to gusseting (08 §10,09 §§4,10,11 §§6.4–6.5). Preserve parent-roll and operation provenance across splits/transfers. A generic configurable route in Phase 2 does not enforce this prohibition.

A — Future adapters validate approved route/revision and actual input provenance; moving a slit roll through another location cannot clear its slit history. Unknown route/roll identity is held. Lineage edges name input/output lot/portion, source run and measured quantities/units; no equation equates kg input to pieces output without approved transformation accounting. Recycling interfaces expose authorized waste/scrap issues, external custody dispatch/return, recovered granule receipts, and input/output/reject/loss/WIP reconciliation evidence. No recycling scheduler, yield limit, mixing instruction or execution workflow in Phase 3.

## Trust and integration boundaries

All state-changing commands are authenticated, capability scoped and server attributed; no trusted client actor/approver IDs. Separate evidence submission, business authorization, physical execution, system recording and independent verification. Bind approvals to exact content hash/source revision; edits invalidate approval. Versioned and immutable evidence prevents reference drift. Technical Master Admin never bypasses independence or QC.

Use protected private evidence storage with digest, uploader, captured date, media type and retention policy; database metadata/decisions are atomic, external blobs uploaded before references become usable. Commit notifications only after commit; no network effects within stock transactions. Publication retry requires an outbox only if external delivery becomes authorized. No external integration is assumed here.

See [database design](PHASE_3_DATABASE_DESIGN.md), [QC design](PHASE_3_QC_FOUNDATION.md), [frontend blueprint](PHASE_3_FRONTEND_INTEGRATION.md) and [implementation plan](PHASE_3_IMPLEMENTATION_PLAN.md).
