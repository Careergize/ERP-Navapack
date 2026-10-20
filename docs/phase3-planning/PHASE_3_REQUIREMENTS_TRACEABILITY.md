# Phase 3 requirements traceability

Review date: 20 October 2026, Asia/Kolkata. Planning only; no operational approval.

## Evidence convention and document ownership

Every paragraph, list or table inherits its immediately preceding classification unless an individual row supplies another classification:

- **S — Confirmed by original SOP:** supplied requirement, not certification of adoption or current operation.
- **W — Observed in workbook:** source observation, not an approved quantity.
- **I — Verified in implementation:** inspected source/committed history, not proof of deployment.
- **A — Proposed architecture:** design recommendation requiring later authorization to implement.
- **D — Pending client decision:** no approval evidenced in supplied material.

All eleven documents use this convention. The [database design](PHASE_3_DATABASE_DESIGN.md) owns entity definitions; [ledger rules](PHASE_3_LEDGER_AND_STOCK_RULES.md) own posting mathematics/locking; [QC foundation](PHASE_3_QC_FOUNDATION.md) owns quality semantics; [permission matrix](PHASE_3_SOP_PERMISSION_MATRIX.md) owns responsibility mapping; [decision register](PHASE_3_CLIENT_DECISIONS.md) owns unresolved policies. Differences must be resolved before implementation, never by choosing the least restrictive rule.

## Source control

I — Reviewed the 18 original DOCX documents, both XLSX workbooks (four sheets altogether) and eight JPEGs in `client-reference/`. All 28 path/size/SHA-256 identities match [CLIENT_SOURCE_MANIFEST.json](../CLIENT_SOURCE_MANIFEST.json); originals were read without saving/recalculation. DOCX paragraph/table text was extracted from `word/document.xml`; workbook values, formula text and stored caches were inspected separately. Images were visually inspected. Full original filenames and hashes remain in that manifest, rather than creating a second conflicting manifest.

S/D — SOPs 01–17 state v1.0; SOP 18 states v1.1; all state effective 1 November 2026. Review date precedes that date. Typed position/signature blocks and dates are supplied documentary assertions, not independently authenticated digital signatures. SOP 04 has blank preparation/review/approval fields. Obtain the controlled register, adoption evidence and approved pre-effective-date rules (D01). Earlier source-unavailability statements in historical audits describe the earlier audit state; preserve them.

## Requirement register

S — The requirement and actor/check columns below paraphrase the original numbered sections. A — Control/phase columns are proposals. D — Decision references identify remaining policy detail; they do not reopen explicit SOP responsibilities. PM = Production Manager; OM = Operations Manager; PO = Procurement Officer. The [permission matrix](PHASE_3_SOP_PERMISSION_MATRIX.md) expands request/approve/execute/record/verify separation.

| ID / SOP section | Requirement and responsible actor | Approval / independent verification | Inventory impact | Proposed control / phase | Status or decision |
|---|---|---|---|---|---|
| R01 / 01 §§3.1–3.2,5 | Separate significant stages; no self-approval | Another appropriate position checks overlapping duties | Prevent fabricated approvals | Actor UUID separation and approved workflow policy, 3B | S; D02 staffing |
| R02 / 01 §§3.3,3.7,4.3–4.4 | QC independent of production; PM cannot independently release required-QC stock | QC clearance; management/customer concession separately | Hold blocks use/dispatch | Separate quality and business approvals, 3D | S |
| R03 / 01 §§3.4–3.6,8 | Attributable evidence and one traceable transaction trail | Performer/checker/approver and times retained | Every posting has source | Immutable source revisions and audit, 3B | S |
| R04 / 01 §§3.8,4.1–4.2 | Follow approved delegated authority; no numeric limits supplied | Existing authorized approver/Management pending limits | No generic Admin override | Versioned policy evidence, deny undefined approval, 3B | S; D02 |
| R05 / 01 §§6–7,11 §8 | Operator checks outside single-shift QC; next-available verification | Critical output held until documented QC; OM+QC record interim control if criticality undocumented | Off-shift output unavailable where clearance required | Coverage/criticality evidence and holds, 3D | S; D09 actual plans |
| R06 / 02 §§5–7,16 §4.2 | Approved SO **or FG Requisition**, including walk-in/B2B without SO | PM/OM as applicable; commercial authority separately | Order creates demand, no physical deduction | Typed SO/requisition source; later sales adapter | S; D02 delegation |
| R07 / 03 §§3.3–3.4,4;04 §§7–8 | Stores measures/receives; PO records system stock from Stores evidence | Assigned quantity check; discrepancy approval/escalation; QC where applicable | Actual receipt distinct from acceptance | Physical evidence before recording, held custody separately, 3C | S; D10 timing |
| R08 / 03 §§4.2–4.4;04 §§6–9 | GRN records supplier, authorization, actual qty/unit, condition, delivery, receiver/checker, QC | Resolve/refer PO/delivery/GRN conflict before final entry; Finance document match | No invoice-only Stock IN | Required evidence links and discrepancy state, 3C | S |
| R09 / 03 §5 | Designated locations and identifiable released/awaiting/held/rejected/returned/rework stock | Authorized custody and QC status changes | No quality mixing | Location hierarchy separate from quality disposition, 3A/3D | S; D03 geography |
| R10 / 03 §6;05 §6 | Stores issues actual material on approved requisition/order; receiver acknowledges | Authorized approver, no self-approval; quality clearance/disposition | Stores OUT is WIP custody IN, not consumption | Issue evidence, allocation and typed production reference, 3C | S; D08 production boundary |
| R11 / 03 §7.1;05 §6 | Count/weigh unused returns; link original issue/order | Stores receives; uncertain condition held for QC | Return reduces issued WIP, no new purchase | Original issue allocation limits, 3C | S |
| R12 / 03 §7.2 | Record tracked location/status transfer, both places/date/actors | Sending/receiving evidence; delegation where needed | Equal OUT/IN, no total change | Atomic same-unit transfer; transit only if approved, 3C | S; D03,D11 |
| R13 / 03 §7.3;12 §§6–8 | Identify scrap/reject source, quantity and reason; segregate | QC assessment; authorized disposition before removal/reuse | Rejection not disappearance | Rejected partition, disposition source and later recycling interface | S; D02,D08 |
| R14 / 03 §8;05 §10;10 §10 | Production transfer/completion accompanies actual FG receipt | Stores quantity check; QC before availability where required | Exact FG variant and production lineage | FG custody receipt and separate release, 3C/3D | S; D10 separate authorization |
| R15 / 03 §§9.1–9.2;04 §8 | PO records receipts/issues/returns/transfers/approved adjustments; independent reconciliation | Checker independent of routine custody/entry where practicable; OM reviews significant variance | Physical vs system lag visible | Evidence backlog and reconciliation, 3C | S; D02,D12 frequency |
| R16 / 03 §9.3,11 | Controlled counts do not edit balances; investigate before adjustments | Management/OM assigns counters/reviewers; authority matrix approval | Variance observation distinct from ledger correction | Count snapshot, investigation, independently approved adjustment, 3C | S; D06,D12 |
| R17 / 05 §§4–5,7.1 | Approved job determines operation sequence; sender records and receiver confirms handover | PM confirms unclear route before work | WIP remains order/status identifiable | Frozen route reference, measured handover; execution deferred | S |
| R18 / 05 §§7,9–11 | Actual material usage, returns, output, waste, rejects, rework and variances recorded | PM review; QC disposition/rework verification; significant variance OM/Management | Issue != consumption != waste | Future consumption/recovery events, no recipe auto-post | S; D08 |
| R19 / 06 §§4–10 | Extrusion inputs/additives, roll output, startup waste, settings/check evidence and next authorized operation | Operator checks; independent QC; receiving acknowledgement | Input-to-roll lineage; no automatic next stage | Typed run/roll provenance, hold integration; execution later | S |
| R20 / 07 §§4–11 | Printing uses approved artwork version and issued film/inks; record rolls, waste and route | PM plus QC/management for deviations where required | Preserve film/ink lots, artwork and output relation | Revision/source snapshots; later production service | S |
| R21 / 08 §§4,10;09 §§4,10;11 §§6.4–6.5 | Slitted rolls must never transfer to gusseting | Receiving operator refuses; QC holds incorrect route; PM resolves | Illegal WIP input unavailable | Immutable slit provenance and reject gusseting input even through intermediate transfer | S; no override option |
| R22 / 09 §§4–10 | Gusset can occur in extrusion or after printing before bag making, as approved route states | PM route confirmation, operator/QC checks | Preserve route and parent material | No universal extrusion→printing→slitting→gusset chain | S |
| R23 / 10 §§4–10 | Bag/pouch input matches route, dimensions/seals/pack checks and identified completion | PM completion; QC required checks; Stores actual receipt | Roll-to-FG batch/variant lineage | Future transformation, measured FG receipt in 3C | S |
| R24 / 11 §§3,5–6 | Approved specifications/artwork/inspection plans; no invented acceptance limits | QC resolves conflicting references with PM/OM | Missing required evidence blocks release | Versioned applicable template/reference, 3D | S; D09 values/plans |
| R25 / 11 §7;12 §6 | QC or PM initiates holds for failed/missing checks or uncertain identity/route | QC release only after required checks; notify Stores | Quantity/batch/period scoped exclusion | Hold scopes expanded to disjoint stock portions, 3D | S; D09 allocation detail |
| R26 / 11 §7.3 | Release only identified material/product/quantity/period; concession has separate authority | QC records clearance; customer approval where required | Partial release must not free other held stock | Explicit allocation and gate satisfaction, 3D | S; D09 operating method |
| R27 / 12 §§6.2–6.3,7–8 | Broad suspect scope until established; trace already dispatched output; authorized rework + reinspection | PM/QC scope assessment; Management customer response; independent verification | No rework-as-new-receipt or erasure | Hold lineage search, NCR reference, new reinspection; CAPA execution later | S |
| R28 / 13 §§3.3,5–10 | Recycling source/job, actual input/output/reject/residual/WIP/loss, external acknowledgements | Assigned direct receiver/checker; QC per intended use; approved loss limits only | Waste and recovered granules distinct | Typed inbound/outbound interfaces; no recycling execution in 3 | S; D03,D08,D15 |
| R29 / 14 §§6,8–9 | Actual measurement, net-weight evidence, segregated supplier/grade, processing reconciliation | Independent quantity verification where assigned; Finance match; approved adjustments | No universal bag weight or yield factor | Evidence readings and item/unit mapping, 3C interface | S; D04,D15 |
| R30 / 15 §§4–7,10 | Approved request; Stores actual issue precedes dispatch-book entry; QC and payment/credit/documents gate external release | Stores and assigned checker; PO system record under 03; sales records dispatch | Internal handover distinct from premises OUT | Custody transfer versus external stock exit, policy D11 | S; D11 exact timing |
| R31 / 15 §9 | Carrier signed handover != customer receipt; unsigned handover not confirmed | OM documented exception and alternative evidence | No second OUT at delivery confirmation | Future dispatch/handover evidence reference | S |
| R32 / 15 §11 | Customer returns physically received before stock changes; remedies authorized | Stores receipt, QC if uncertain; finance authorization | Return references actual dispatch, no finance-driven auto-IN | Returns adapter later; held receipt foundation | S |
| R33 / 16 §§4.2,5 | FG requisition can replace SO; reception sequence and independent dispatch-point officer | Officer not directly connected to Stores/front office verifies/approves | Reception stock still physically within company | Preserve separate custody location; stricter unresolved staffing gate | S; D11 named function |
| R34 / 17 §§4–8,11 | Finance checks approved purchase + actual receipt and payment evidence; controlled corrections/access | Independent financial verification, no own-payment approval | Inventory evidence available, no payment-caused posting | Read-only evidence integration; finance execution deferred | S |
| R35 / 18 §§6–11 | Maintenance parts used traceable; affected output held; restart/first-off checks | Maintenance completion plus PM/Recycling suitability and QC where needed | Consumable issue distinct from equipment clearance | Authorized issue evidence and quality hold interface; maintenance later | S |

## Reference-image reconciliation

I — All eight photos were viewed. Names below are suffixes of `WhatsApp Image 2026-10-13 at …jpeg` in the manifest:

| Filename time suffix | Observed form | Design implication (A); adoption remains D09/D15 |
|---|---|---|
| 12.46.24 PM (1) | NRIL/F-007 personnel safety checklist | Personnel evidence is not lot QC release |
| 12.46.24 PM | NRIL/DLY/F01-QA extruded-roll sample checks, eight sample columns | Per-question polarity, conditional treatment/gusset checks; no universal eight-sample rule |
| 12.46.25 PM (1) | NRIL/WKLY/F10-EM filled extruder check | Equipment/period evidence; no stock acceptance inferred |
| 12.46.25 PM (2) | NRIL/F005 area cleaning checklist | Area is not automatically warehouse |
| 12.46.25 PM (3) | NRIL/WKLY/F10-RM filled recycling-machine check with screen-changer note | Historical defect note not current machine restriction/closure |
| 12.46.25 PM | NRIL/WKLY/F10-RM blank form | Template evidence, no performed check |
| 12.46.26 PM (1) | NRIL-F2 raw-material receipt/analysis: supplier/type/grade/batch/received qty/docs/sampled qty/condition/acceptance | Keep measured receipt and inspection separate; sample bags/kg not conversion authority |
| 12.46.26 PM | NRIL/WKLY/F10-RM blank form | Separate source file, not another completed inspection |

D — NRIL/Nova Recycling Industries form identity differs from Navapack SOP identity. Confirm entity/site applicability, approved versions and adoption before publishing templates. Do not provision pictured names/signatures as ERP actors.

## Coverage limits

I — No inventory/QC backend apps or posting tests exist. Existing UI workflows are not evidence that R01–R35 are implemented. [Readiness report](PHASE_3_READINESS_REPORT.md) distinguishes source verification, implementation inspection, prior tests and unexecuted operational acceptance.
