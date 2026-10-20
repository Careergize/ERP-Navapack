# Authoritative client source review before Phase 3

Reviewed 20 October 2026. All 18 original SOP documents and both original stock
workbooks are now available under `client-reference/`. They are the authoritative
client source material for subsequent requirements work. Earlier audit statements
that originals were unavailable describe the earlier review, not current availability.
Those historical reports have not been rewritten.

This is a source review and decision register, not Phase 3 design or implementation.
No stock balance, opening transaction, inventory movement or business permission has
been approved or imported. No original file was modified. The source register and
SHA-256 digests are in [CLIENT_SOURCE_MANIFEST.json](CLIENT_SOURCE_MANIFEST.json).

## Review coverage and document control

Read the main document, tables and ancillary header/footer/footnote/endnote/comment
XML where present in every SOP DOCX. All 18 contain no embedded media or tracked
insertions/deletions. Read all populated cells, stored formulas and cached results
across all four workbook sheets; inspected units, dates, identifiers, merged headers,
candidate identity fields and formula references. No workbook was recalculated or
saved. Formula caches are historical observations, not independent recalculation or
physical reconciliation. Visually inspected all eight accompanying JPEG references.

SOPs 01–17 state version 1.0; SOP 18 states version 1.1. All state an effective date
of **1 November 2026**, later than this review. Treat their contents as the supplied
authoritative requirements, while obtaining the operational cutover/interim-rule
decision before using them as current runtime authority. Several approval tables show
typed positions/dates; SOP 04 has unfilled approval dates. No digital signature or
separate controlled-document release register was supplied or authenticated by this
review. The user's designation of these sources as authoritative is retained.

## Verified SOP requirements

The numbered references below refer to the original SOP number and section; the
manifest records each exact filename. These requirements replace assumptions in
frontend demos or earlier planning documents when they conflict.

1. **SOP 01 — Authority & Internal Controls (§§3–8).** No self-approval; separate
   request, approval, execution, receipt/inspection, record, verification and payment/
   release. Staffing overlap requires a documented independent check. Stores holds
   physical stock; Procurement updates system stock from Stores evidence; QC checks
   independently. Overrides cannot bypass mandatory holds. Monetary limits are
   explicitly deferred to the approved authority matrix. One QC covers one shift;
   off-shift checks/samples need next-available verification, and critical output
   remains held until required QC clearance. Missing critical designation requires
   Operations and QC to document an interim control before dispatch (§7.3).
2. **SOP 02 — Sales & Customer Order Management (§§4–9).** Capture enquiries and
   customer requirements; review completeness, approved prices, availability,
   feasibility and quality requirements before acceptance. Order changes need review
   and communication. Walk-in requisitions require the applicable manager's approval.
   Sales records dispatch after Stores' actual issue; Sales does not invoice or
   record payment. Carrier acknowledgement and customer receipt are separate evidence.
3. **SOP 03 — Stores & Inventory Control (§§3–9).** Stores records actual measured
   receipt/issue, GRNs, acknowledgement, locations and segregated quality status.
   Procurement records system entries from authorised receiving/issue/return/transfer/
   adjustment records. Physical receipt is separate from quality acceptance and usable
   stock. Returns reference the original issue/order. Counts do not overwrite system
   balances; differences require investigation and approval before adjustment.
   Reconciliation intervals and assigned independent reviewers are not fixed here.
4. **SOP 04 — Procurement & Supplier Management (§§4–10).** Approve requisitions
   before commitments and POs before issue. Document quotation comparisons or approved
   sourcing exceptions; no fixed quotation count is prescribed. Stores receiving and
   QC evidence support system entry; Finance independently matches PO, actual receipt/
   service completion and invoice. Independently verify changed supplier payment
   details using known contacts. No invented monetary limits.
5. **SOP 05 — Production Planning & Control (§§4–10).** Approved order/replenishment
   or other authorised requirement, current specifications and explicit per-job route
   govern production. Material issues and actual consumption are distinct records;
   record returns, waste, rejects, rework, downtime and handover acknowledgements.
   Missing/unclear routes pause work; receipt into Stores does not imply QC release.
6. **SOP 06 — Extrusion Process Control (§§4–10).** Approved material identity,
   process sheet, setup and recorded routine checks; identify affected rolls/periods
   and reconcile material/output. It explicitly does not provide temperatures, speeds,
   recipes, tolerances or sampling frequencies. Extrusion's next operation must come
   from the approved route; none is universally assumed.
7. **SOP 07 — Printing Process Control (§§5–11).** Record the approved artwork
   version, film/materials, setup and print checks. Printed-roll products may go to
   Stores after required QC. Other jobs follow their approved slit/bag/pouch route;
   post-print gusset jobs go directly to gusseting then bag making. Slitted rolls
   must not go to gusseting (§11).
8. **SOP 08 — Slitting Process Control (§§4–10).** Preserve parent-roll identity,
   approved slit requirements, output roll quantities and QC status. Slitted material
   proceeds according to the approved route, including bag/pouch making where stated.
   **Slitted rolls must never be transferred to gusseting.**
9. **SOP 09 — Gusseting Process Control (§§2,4,10).** Gusseting can be integrated
   into extrusion or performed after printing before bag making. These are different
   approved flows, not one mandatory extra stage. Reject slitted or unidentified input
   for gusseting and obtain recorded route clarification.
10. **SOP 10 — Bag & Pouch Making Process Control (§§4–10).** Verify input identity,
    approved route, artwork where applicable, dimensions/seals and start-up/routine
    checks. Record output, use/returns/waste and actual Stores transfer; goods requiring
    QC remain unavailable until clearance. No numeric acceptance values are supplied.
11. **SOP 11 — Quality Control (§§3,5–8).** Operators perform routine checks; QC
    independently verifies. QC or Production Manager initiates holds for failed/missing
    checks, uncertain traceability, deviation or incorrect routing. Release covers only
    the identified material/product/quantity/period. QC does not grant commercial
    concessions or physical dispatch. No verbal release or off-shift bypass; numeric
    tolerances/frequencies belong in approved specifications/work instructions.
12. **SOP 12 — Nonconforming Product, Rework & CAPA (§§6–11).** Contain reasonably
    suspected affected stock when scope is uncertain, including previously dispatched
    output. Disposition/rework must be authorised, retain original traceability and
    require reinspection where applicable. CAPA has owners, evidence, effectiveness
    verification and closure authority; no fixed completion period is imposed.
13. **SOP 13 — Recycling Operations (§§4–10).** Identify source/job, incoming
    material and destination; preserve permitted mixing traceability. Reconcile input,
    output, rejects, residual waste, returns, WIP and documented process loss. External
    job work needs sent/received evidence. No numeric acceptable-loss limit is given.
14. **SOP 14 — Recycling Material Procurement & Reconciliation (§§4–9).** Approve
    purchases/collections; retain actual measurement, gross/tare/net calculation where
    applicable, condition and assigned independent receipt verification. Physical
    acceptance does not imply quality or payment approval. Hold stock is unavailable;
    reconcile source through processing. No monetary or acceptable-loss limit is set.
15. **SOP 15 — Dispatch & Delivery Management (§§4–10).** Approved source request,
    actual Stores issue, sufficient identifiable physical stock, required QC release,
    invoicing/documentation and payment/authorised credit govern external release.
    Record carrier packages/quantity and acknowledgement separately from customer
    confirmation. An unsigned handover is an exception, not confirmed handover.
    Loss, carrier liability, replacement, write-off and adjustments require evidence
    and authorised decisions, not assumptions from a carrier signature.
16. **SOP 16 — Invoicing, Cash & EFRIS Controls (§§4–10).** A sale may use an
    approved **FG Requisition without a Sales Order**, including B2B; B2B is not
    automatically credit. Internal Stores issue to reception/dispatch precedes dispatch
    book/invoice preparation, but goods cannot leave until invoice/delivery documents,
    payment or approved credit, required QC and dispatch-point verification are complete.
    §5 additionally calls for a dispatch-point verifier not directly connected to Stores
    or front office; reconcile this with SOP 15's staffing-qualified independence wording.
    Verify payment provider evidence; retain auditable invoice corrections. No tax
    rate, EFRIS integration contract or outage workaround is prescribed by this review.
17. **SOP 17 — Finance, Payments & Reconciliation (§§4–9).** Independently verify
    purchase/receipt/invoice evidence, prevent duplicate payment, approve exceptions
    and verify payee changes. Separate approval/execution/reconciliation as practicable;
    retain Tally/approved finance-system links and investigate unmatched balances.
    Reconciliation frequency and monetary limits remain client decisions.
18. **SOP 18 — Equipment Maintenance & Downtime Control, v1.1 (§§3–11).** Senior
    Maintenance Technician/Supervisor leads maintenance; Technician and Assistant act
    within competence. Fabricator/Welder and Helper belong to Recycling and provide
    coordinated maintenance support. Record repairs, restrictions, downtime and affected
    output. Return to service needs maintenance completion, operational suitability,
    start-up and applicable QC evidence; an active machine master is not proof of fitness.

## Original workbook observations and reconciliation questions

### Raw materials workbook

`08- September 2026  Daily Raw Material Physical stock  -.xlsx`: one visible Sheet1,
103 rows × 81 columns (used/style extent), 856 populated cells and 283 formula cells.
No stored Excel errors, uncached formulas, defined names or external workbook links
were found. These facts do not establish correct formulas or approved balances.

- Sheet1!A2:D2 labels Grade, unit in KG, unit Bag and opening stock. B/C contain no
  populated per-item unit/conversion values. Do not assume D or daily IN/OUT counts
  are kilograms or apply a universal bag weight. Material labels include grouped
  polymers, master batches, additives, inks/solvents, recycled and crushed material.
- E1:BN2 spans daily IN/OUT pairs from 1 September through **1 October 2026**.
  Confirm whether October 1 belongs in this reconciliation/cutover period.
- BO2/BP2 are labelled IN/OUT but BO4 includes D4 starting stock. Importing BO as
  receipts and also D as opening would double-count the starting quantity.
- BO4 references AC5 instead of its own row's AC4; BO5 references AC6 instead of AC5.
  These are cross-item reference anomalies requiring client review, not silent repair.
- BQ25 stores approximately **−0.3**, a genuine negative source closing observation,
  not a tiny rounding residual to erase. D25 has floating-point representation effects.
- BQ103 sums BQ3:EC102, extending beyond the closing column; its range and cross-unit
  total meaning need review. Never treat this total as a reconciled opening ledger.
- Ink/solvent rows A63:A76 and other rows contain missing balances; a formula-derived
  zero elsewhere does not authorise replacing unknown observations with zero.

### Finished goods workbook

`09.FG Stock September .xlsx`: three visible sheets, no defined names or external
workbook links, no stored Excel errors or uncached formulas found:

- Carrier Bags: 92 × 74 used/style extent, 1,068 populated cells, 307 formula cells.
- Flat Bags: 253 × 78, 2,763 populated cells, 848 formula cells.
- Packing: 94 × 72, 545 populated cells, 271 formula cells.

Carrier Bags and Flat Bags date headers span 1 September–1 October 2026. Their F
column is used as a starting quantity by closing formulas, but its merged header is
blank; obtain explicit meaning/as-of confirmation. Rows distinguish customer, product
detail, size, brand, packing and unit; repeated descriptions do not establish one SKU.
Do not auto-carry blank customer cells forward or silently merge spelling/case variants.
Keep the original workbook hash/sheet/row as provenance and obtain stable master mapping.

Unit examples include ctn/Ctn and kg/Kg/Kgs. Carrier Bags!G7 and Flat Bags!G101 are
blank; Flat Bags!F191:F192 have fractional quantities while G191:G192 say ctn. These
need explicit unit/pack interpretation rather than an assumed conversion. Packing-size
strings such as 50X60, 100 PCS and 100 pkts/Carton are not universal dimensional or
weight conversion definitions. Decimal precision must be agreed before normalisation.

Packing!F1 says `opening stock as 03/05/26`, while H1:BP1 contains May 1–31, 2026
inside a September-named workbook. F4:F52 contains no starting values; no nonzero
movement quantity was found in the populated movement grid. BR4:BT4, for example,
evaluate to cached zero from blank inputs. **Unknown starting stock remains unknown**;
neither the filename nor those cached zeros approves a September balance.

None of the four sheets supplies a complete transaction-level approval trail, receiving/
issue documents, operational location/lot/QC allocation or reconciled migration cutoff.
Workbooks are authoritative source observations for staging and reconciliation; they
are not automatically authorised opening balances or an inventory movement ledger.

## Additional JPEG evidence

All eight `WhatsApp Image ...jpeg` files were visually reviewed. They show a personnel
safety checklist (NRIL/F-007), an extruded-roll sample test form (NRIL/DLY/F01-QA),
weekly extruder and recycle-extruder machine check forms (NRIL/WKLY/F10-EM and
NRIL/WKLY/F10-RM, including blank/filled examples), an area-cleaning checklist
(NRIL/F005), and a raw-material receipt/analysis record (NRIL-F2).

The roll form has eight sample columns and mixed question polarity: a Yes can be
conforming for a dimension check while No is expected for objectionable odour;
treatment and gusset checks depend on the order. Eight columns do not impose eight
samples on every future inspection. Weekly machine headings are evidence for those
forms, not a universal sampling or maintenance schedule. Blank forms are templates,
not completed checks. A handwritten defect/correction note is historical evidence,
not a current equipment restriction or closure decision to import automatically.

These photographs bear Nova Recycling Industries Ltd/NRIL identifiers, whereas the
SOPs identify Navapack Solutions. Confirm the applicable site/entity, controlled
template versions and adoption/cross-reference. Do not turn historical signatures,
sample measurements or sample bag-to-kg observations into current users, approval
assignments, tolerances, unit factors or stock acceptance.

## Decisions still needed before Phase 3 design is approved

1. **Operational cutover:** confirm 1 November effective-date transition, interim rules,
   current document register, and treatment of SOP 04's unfilled approval fields.
2. **Authority and staffing:** supply the actual delegated financial/commercial matrix,
   named employee memberships, approved business capability mapping, independent
   reconciler/quantity-checker assignments and compensating checks for overlapping duties.
   Technical Master Admin status does not confer operational approval or QC authority.
3. **Dispatch verification:** name the independent dispatch-point function and clarify
   SOP 16 §5 versus SOP 15 §9 staffing qualification. Separate internal custody transfer
   to reception from external goods release; do not require a Sales Order for every sale.
4. **Opening reconciliation:** nominate reconciliation date/cutoff, counters/reviewer/
   approver, source document evidence and treatment of unknown/negative/disputed balances.
   Resolve May/September/October coverage and all workbook anomalies before approving
   quantities. Decide how intervening movements are evidenced without double posting.
5. **Master and units:** approve each material/variant/customer mapping, duplicate
   resolution, item units, package hierarchy, exact conversion factors and precision.
   Confirm the raw-material quantity basis and the fractional carton/missing-unit rows.
6. **Physical scope/traceability:** provide sites, Stores/reception/recycling areas and
   tracked locations, ownership/customer-dedicated stock, lot/roll/container identifiers,
   split/merge rules, required traceability depth and off-site job-work custody.
7. **Quality:** supply current specifications, artwork/work instructions, inspection
   applicability, measurable limits, actual sampling/retention plans, critical designations,
   QC coverage roster and interim-control records. Define quantity/lot/period hold scope,
   partial release and customer concession evidence without bypassing mandatory clearance.
8. **Inventory policy:** decide negative-stock prevention, unknown-stock handling,
   reservations/availability, backdating/period locks, partial receipts/issues/returns,
   count reconciliation frequency, approved corrections and loss/disposition authority.
   SOP controls establish approval/evidence needs but do not specify every ERP rule.
9. **Recycling/maintenance:** confirm direct receiving/checker assignments, ownership of
   job-work material, approved yield/loss limits where needed, active equipment register,
   work instructions, maintenance schedules/competence and return-to-service restrictions.
10. **Records and external systems:** agree retention/access/privacy, numbering, offline
    evidence and attachments, Tally/EFRIS integration boundaries, payment verification
    and outage procedures. Tax/finance implementation requires its own verified scope.

The existing Phase 2 foundation is not thereby certified as implementing these SOPs.
For later design review, distinguish a sealed specification from operational approval,
a generic configurable route from the explicit slitting/gusseting prohibition, a master
is_active flag from quality/maintenance clearance, and technical RBAC administration
from business segregation of duties. These are requirements to carry forward, not
implemented Phase 3 controls or permission assignments.

Original-source availability is now resolved. The remaining gates concern the decisions
above and separately authorised Phase 3 scope/release review. No Phase 3 schema,
transactions, permissions or opening postings have been implemented by this review.

## Preservation and verification

SHA-256 hashes were captured before extraction and checked again after review for all
28 source files (18 DOCX, two XLSX, eight JPEG); all matched the manifest. Only
derived review documentation and ignored local extraction files were created. Originals
were never saved, recalculated, renamed or moved. The pre-existing staged .gitignore
change and the client's ignored source-directory policy were preserved. No database,
frontend or backend application changes were made; application tests were not rerun
for this documentation-only review. Git whitespace validation was run separately.
