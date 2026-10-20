# Phase 3 original workbook mapping and opening reconciliation

Classification key: [S/W/I/A/D](PHASE_3_REQUIREMENTS_TRACEABILITY.md). **W — Observed in workbook** for source facts/tables; **A — Proposed architecture** for target mappings/workflow. No workbook was saved/recalculated or imported. Stored caches are historical Excel results, not verified current recalculation.

## File and sheet inventory

W — Source hashes are verified against [manifest](../CLIENT_SOURCE_MANIFEST.json).

| Workbook / sheet | Used/style extent | Populated cells | Formula cells | Period / source meaning |
|---|---|---|---|---|
| `08- September 2026  Daily Raw Material Physical stock  -.xlsx` / Sheet1 |103 rows ×81 columns|856|283|Daily IN/OUT from 1 September through 1 October 2026; source unit basis unresolved |
| `09.FG Stock September .xlsx` / Carrier Bags |92×74|1,068|307|September through 1 October; F starting quantity used but header blank |
| Same / Flat Bags |253×78|2,763|848|September through 1 October; heterogeneous units/pack variants |
| Same / Packing |94×72|545|271|May 1–31 2026 despite September filename; F1 says opening as 03/05/26 |

W — All sheets visible. Both books have zero defined names, zero external workbook links, zero stored Excel error cells; formula caches inspected separately from formulas. Those checks do not establish business correctness. Styled extents are not record counts; headings, totals and blank rows must be excluded. No complete GRN/issue/approval/location/QC/lot trail is present.

## Field-by-field mapping

| Source fields / coordinates | Observed meaning | Existing / proposed target | Review rule |
|---|---|---|---|
| Raw A2 Grade; A3:A102 | Material label or family/section header | Material.name / family; approved category virgin/recycled/ink | Distinguish heading from material row, preserve actual grade/name; category is reviewed mapping, not guessed from row position alone |
| Raw B2 unit in KG; C2 unit Bag; item cells unpopulated | Labels without per-item basis or factors | Unit FK after D04; raw strings preserved in source revision | Neither authorizes kilogram assumption or standard bag weight |
| Raw D2 opening stock, D item rows | Historic starting observations, some blank/zero | OpeningBalanceReview observation, not Material.min_level or ledger | Blank != zero; unknown as-of/unit/location/lot/QC require reconciliation |
| Raw E1:BN2 and item rows | Daily paired IN/OUT with formula dates | Source observation date/direction/quantity/formula/cache; later evidence reconciliation | Not transaction IDs; do not fabricate individual GRNs/issues from daily aggregates |
| Raw BO IN / BP OUT / BQ CLOSING | BO includes opening D plus IN; BP sums OUT; BQ difference | Reconciliation check values only | Never import D and BO as separate opening/receipts; preserve formula text |
| FG sheet title / section rows | Carrier-bags/flat-bags/packing and subgroups | ProductVariant.category/subgroup | No stock movement from section headings |
| FG A Customer | Sporadic names, blanks and subgroup headings | ProductVariant.source_customer/customer; Customer FK mapping only with explicit decision | No automatic carry-forward or name-to-account match; preserve inherited flag if approved later |
| FG B Item Details | Description or blank | ProductVariant.item_details; linked generic Product UUID from reviewed mapping | Repeated/blank name not SKU identity |
| FG C3 Size (C2 on Packing); top C says Date | Size strings on item rows | ProductVariant.size original string | Do not parse as date or invent dimensional units |
| FG D Brand | Brand text | ProductVariant.brand | Grade/brand/customer distinctions retained |
| FG E Packing Size | Packing text, e.g. 50X60,150 PCS,100 pkts/Carton | ProductVariant.packing_size; pieces positive integer only after approved unambiguous extraction | Not kg↔piece/carton conversion; packing format varies |
| FG F row quantity | Blank-header starting quantity for Carrier/Flat; Packing opening-date label | Opening review quantity observation, cutoff evidence | Never seed variant opening in master import; source date interpretation unresolved |
| FG G Unit, Flat/Packing CTN/KGS | ctn,Ctn,kg,Kg,Kgs,kgs; missing cells | ProductVariant.source_unit + approved Unit FK | Alias equivalence requires reviewed unit map; do not combine package and mass |
| Carrier/Flat H2:BQ3; Packing H1:BQ2 | Daily date headings and IN/OUT subheadings | Immutable source date/direction; reconciliation movement bridge | Raw dates and formula caches retained; Packing May distinct from September |
| FG H:BQ item grid | Numeric or formula-derived daily observations | Source evidence observation only | Aggregate same-day formula != individually approved transaction |
| FG BR IN / BS OUT / BT Closing | BR includes F opening; BS OUT; BT difference | Reconciliation calculations | BR is not pure receipts; no duplicate opening |
| All workbook path/hash/sheet/row/cell | Source identity | Existing ImportBatch/ImportRow for reviewed master metadata; SourceDocumentRevision for opening evidence | Master import approval never authorizes stock; retain exact master UUID result/version mapping |
| No reliable stable item/batch IDs in grids | Names/positions are source identifiers only | InventoryItemIdentity existing master FK; StockLot only from approved actual evidence | Do not fabricate supplier lot/batch or merge rows solely by name |
| No stock location / QC allocations / approvals | Missing operational dimensions | Reconciliation unresolved fields | No location, release or approval default |

## Verified anomalies and candidate duplicates

W — Raw BO4 refers to AC5, BO5 to AC6 rather than their own row. Preserve anomalies and ask client for documented correction, never silently repair original. BQ25 caches `-0.30000000000001137`; D25 is `11.699999999999989`. This is a genuine negative source closing observation around −0.3, not a residual to erase. BQ103=`SUM(BQ3:EC102)` spans beyond closing column; cross-unit total is not meaningful approved stock. Ink/solvent rows A63:A76 have missing balances. Formula-derived zero from blanks remains unknown without evidence.

W — Carrier Bags G7 and Flat Bags G101 missing units. Flat Bags F191:F192 fractional carton observations need explicit package/unit/precision decisions. Packing F4:F52 lacks starting values; no nonzero movements found in populated grid; BR4:BT4 cached zeros come from blank inputs. F1 opening as 03/05/26 versus May 1 grid needs date/cutoff interpretation, not September import.

W — Flat Bags rows 5–9 have matching size/brand with different packing: 150,120,130,160,140 PCS; these are distinct variant candidates. Carrier rows 6 and7 repeat WHITE#15/BEST/40X50, but row7 has LAMECH and missing unit; do not merge. A normalized exact comparison of populated A/B/C/D/E/G values (trim/lower only, ignoring quantity F) flags Flat Bags row groups **190/230,198/239,199/223/225,200/222/226/237,206/244,224/240**. They are duplicate **candidates**, not proof: context, customer blank/group inheritance and source history can differ. No exact candidates under that comparison for Carrier/Packing. The row register below preserves unresolved identity fields.

W — Raw grade examples include HTA 001 HD5-EXXON MOBIL/HD5290HLFL, FJ00952-SABIC and F0146D-HMEL OQ. Keep supplier/grade specificity. Ink, solvent, recycled/crushed and additive families need approved existing-master category mapping; don't replace them with generic demo resin names. Flat unit frequencies among populated item-range G cells: ctn80,Ctn1,kg143,Kg17,Kgs1,kgs1. Carrier ctn77; Packing kg49. Counts are observations, not normalized quantities or definitive SKU counts.

## Opening-stock workflow (A)

1. Management approves cutoff/timezone/scope, counters/reviewer/approver and source set (D02,D06,D12). Retain manifest hashes; originals read-only. Do not assume book filename is stock date.
2. Stage row-level **observations**: raw values, formula text, cached values, explicit blank/zero/negative flags, date/header context and source cells. Separately review exact master/unit identities and candidate duplicates; unresolved mappings remain unresolved.
3. Resolve raw unit basis, packaging, missing units, F header meanings, May/September/October boundaries, cross-row formulas, negative observations and suspect totals with client evidence. Preserve proposed corrected value beside original with reason/approver; never rewrite source.
4. Perform controlled physical count by approved item/location/lot/unit/quality portion. Identify ownership and WIP/off-site goods; unknown observations cannot become zero. Use approved freeze or traced movement bridge to cutoff. Measure actual stock; do not use generated UI reference-stock as a batch.
5. Reconcile snapshot + independently evidenced intervening movements against count. Explain variance, duplicate source event and cutover overlap. Either approved opening-at-cutoff plus only later events, or explicit approved history bridge; never both opening-inclusive totals and original movements.
6. Independent reviewer checks units, identities, cutoff, full/partial coverage and QC status; unresolved lines excluded from operational approval and displayed INCOMPLETE. QC clears only required quality scope; quality approval alone not opening approval.
7. Client delegated independent approver signs exact canonical opening plan/hash and source evidence; maker cannot approve own plan. Any change requires re-review. This task supplies **no** opening approval.
8. In a later explicitly authorized implementation, PO posts approved scope once through OPENING command, unique scope/cutoff/event keys and allocation locks; ledger/audit/projection commit together. Retain approved zero coverage evidence without inventing nonzero entry. Reject negative approved openings under proposed safe baseline.
9. Independently compare ledger rebuild, physical records and approved plan; verify unapproved/unknown scope remains blocked. Only then roll out approved scope; retain historical snapshots for audit, never represent them as live inventory.

## Row identity observation register

W/A — The following appendix enumerates source labels/identity-bearing rows to support field review. It is **not** a SKU catalog, deduplicated import or approved mapping. Raw family headers are explicitly unclassified candidates. FG A includes both customer and subgroup text; blanks remain blank. Header/total/formula-only rows are omitted. `∅` means no recorded cell. Every listed row remains pending D13 unless separately approved outside this review. Movement/date mapping is column-driven as above; sample formulas/anomalies remain identified above.

### 08- September 2026  Daily Raw Material Physical stock  -.xlsx / Sheet1

| Row | A grade/family raw label | Identity treatment |
|---|---|---|
| 3 | HDPE | Material/family candidate; review D13; unit unresolved |
| 4 | HTA 001 HD5-EXXON MOBIL/HD5290HLFL | Material/family candidate; review D13; unit unresolved |
| 5 | FJ00952-SABIC | Material/family candidate; review D13; unit unresolved |
| 6 | F0146D-HMEL OQ | Material/family candidate; review D13; unit unresolved |
| 7 | HD OQ HDF 5211 | Material/family candidate; review D13; unit unresolved |
| 8 | HD BASF F6095 | Material/family candidate; review D13; unit unresolved |
| 9 | PP | Material/family candidate; review D13; unit unresolved |
| 10 | PP RB707CF | Material/family candidate; review D13; unit unresolved |
| 11 | LDPE | Material/family candidate; review D13; unit unresolved |
| 12 | LDPE SABIC (HP2022 JN/ HP 2025JN) | Material/family candidate; review D13; unit unresolved |
| 13 | LDPE FD0274-LOTRENE | Material/family candidate; review D13; unit unresolved |
| 14 | LDPE-100AC- BR-EXXONMOBILE | Material/family candidate; review D13; unit unresolved |
| 15 | LDPE 160AT-EXXONMOBILE | Material/family candidate; review D13; unit unresolved |
| 16 | LDPE FT6236-BOROUGE | Material/family candidate; review D13; unit unresolved |
| 17 | LDPE TASNEE(4025AS) | Material/family candidate; review D13; unit unresolved |
| 18 | LDPE TASNEE(1925AS) | Material/family candidate; review D13; unit unresolved |
| 19 | Enable 2705-MC | Material/family candidate; review D13; unit unresolved |
| 20 | Lotrene FE 8000 | Material/family candidate; review D13; unit unresolved |
| 21 | LDPE OFF GRADE | Material/family candidate; review D13; unit unresolved |
| 22 | LDPE CLEAR ABACUS | Material/family candidate; review D13; unit unresolved |
| 23 | LD ABACUS BROWN | Material/family candidate; review D13; unit unresolved |
| 24 | LLDPE | Material/family candidate; review D13; unit unresolved |
| 25 | Q1018H-LOTRENE | Material/family candidate; review D13; unit unresolved |
| 26 | 118WJ-SABIC | Material/family candidate; review D13; unit unresolved |
| 27 | F2001S-OPELENE | Material/family candidate; review D13; unit unresolved |
| 28 | LLD Shell 18F 1B2 | Material/family candidate; review D13; unit unresolved |
| 29 | LLD Exon 1001BU | Material/family candidate; review D13; unit unresolved |
| 30 | LLD Cefor | Material/family candidate; review D13; unit unresolved |
| 31 | LLD0Q/FI801SA | Material/family candidate; review D13; unit unresolved |
| 32 | MASTER BATCH | Material/family candidate; review D13; unit unresolved |
| 33 | BLACK (EFPE 0025C) | Material/family candidate; review D13; unit unresolved |
| 34 | BLACK 3030 | Material/family candidate; review D13; unit unresolved |
| 35 | BLACK (E41J ) | Material/family candidate; review D13; unit unresolved |
| 36 | BLACK PL 30BL | Material/family candidate; review D13; unit unresolved |
| 37 | BLACK MB2038B | Material/family candidate; review D13; unit unresolved |
| 38 | BLACK PE 20 | Material/family candidate; review D13; unit unresolved |
| 39 | BLACK (1087) | Material/family candidate; review D13; unit unresolved |
| 40 | BLACK | Material/family candidate; review D13; unit unresolved |
| 41 | WHITE (219440108) | Material/family candidate; review D13; unit unresolved |
| 42 | BLUE (487) | Material/family candidate; review D13; unit unresolved |
| 43 | GREEN (298) | Material/family candidate; review D13; unit unresolved |
| 44 | RED | Material/family candidate; review D13; unit unresolved |
| 45 | YELLOW 12157 | Material/family candidate; review D13; unit unresolved |
| 46 | ORANGE | Material/family candidate; review D13; unit unresolved |
| 47 | LIGHT GREEN | Material/family candidate; review D13; unit unresolved |
| 48 | BIEGE KRISHNA(04004) | Material/family candidate; review D13; unit unresolved |
| 49 | MB LEMON GREEN219770051 | Material/family candidate; review D13; unit unresolved |
| 50 | GREEN (10894) | Material/family candidate; review D13; unit unresolved |
| 51 | GREEN MB42141G | Material/family candidate; review D13; unit unresolved |
| 52 | PURPLE | Material/family candidate; review D13; unit unresolved |
| 53 | Coffee Brown | Material/family candidate; review D13; unit unresolved |
| 54 | ADDITIVES | Material/family candidate; review D13; unit unresolved |
| 55 | DESSICANT /DEFOAMER | Material/family candidate; review D13; unit unresolved |
| 56 | FILLER | Material/family candidate; review D13; unit unresolved |
| 57 | ANTIBLOCK (04001) | Material/family candidate; review D13; unit unresolved |
| 58 | BRIGHTNER | Material/family candidate; review D13; unit unresolved |
| 59 | FILLER SPO (6151) | Material/family candidate; review D13; unit unresolved |
| 60 | FILLER PE4600 | Material/family candidate; review D13; unit unresolved |
| 61 | FILLER SP6121 | Material/family candidate; review D13; unit unresolved |
| 62 | INKS & SOLVENTS | Material/family candidate; review D13; unit unresolved |
| 63 | BUTANOL | Material/family candidate; review D13; unit unresolved |
| 64 | POLYTOP BRIGHT WHITE | Material/family candidate; review D13; unit unresolved |
| 65 | POLYTOP BLOOD RED | Material/family candidate; review D13; unit unresolved |
| 66 | POLYTOP PRO BLACK | Material/family candidate; review D13; unit unresolved |
| 67 | POLYTOP KILIMBIRO BLUE | Material/family candidate; review D13; unit unresolved |
| 68 | POLYTOP DIARY GREEN | Material/family candidate; review D13; unit unresolved |
| 69 | POLYTOP PROCESS YELLOW | Material/family candidate; review D13; unit unresolved |
| 70 | POLYTOP PURPLE | Material/family candidate; review D13; unit unresolved |
| 71 | POLYTOP PROCESS CYAN | Material/family candidate; review D13; unit unresolved |
| 72 | POLYTOP PROCESS MAGENTA | Material/family candidate; review D13; unit unresolved |
| 73 | POLYTOP ORANGE | Material/family candidate; review D13; unit unresolved |
| 74 | POLYTOP HOMEMADE BROWN | Material/family candidate; review D13; unit unresolved |
| 75 | POLYTOP CREAM | Material/family candidate; review D13; unit unresolved |
| 76 | Mixed Brown | Material/family candidate; review D13; unit unresolved |
| 77 | RECYCLE MATERIAL | Material/family candidate; review D13; unit unresolved |
| 78 | HDPE BLACK NAIROBI | Material/family candidate; review D13; unit unresolved |
| 79 | HDPE BLACK In-house | Material/family candidate; review D13; unit unresolved |
| 80 | HDPE YELLOW INHOUSE | Material/family candidate; review D13; unit unresolved |
| 81 | HDPE-WHITE RP | Material/family candidate; review D13; unit unresolved |
| 82 | HD CLEAR RP | Material/family candidate; review D13; unit unresolved |
| 83 | BLACK PIPE | Material/family candidate; review D13; unit unresolved |
| 84 | PVC PIPE | Material/family candidate; review D13; unit unresolved |
| 85 | LDPE CLEAR INHOUSE | Material/family candidate; review D13; unit unresolved |
| 86 | LDPE BLACK INHOUSE | Material/family candidate; review D13; unit unresolved |
| 87 | LD Blue RP | Material/family candidate; review D13; unit unresolved |
| 88 | LD BROWN | Material/family candidate; review D13; unit unresolved |
| 89 | LD GREEN | Material/family candidate; review D13; unit unresolved |
| 90 | LD RP (WATEYA) | Material/family candidate; review D13; unit unresolved |
| 91 | TANK | Material/family candidate; review D13; unit unresolved |
| 92 | LD Pure clear | Material/family candidate; review D13; unit unresolved |
| 93 | HRP | Material/family candidate; review D13; unit unresolved |
| 94 | HDPE_Yellow Jerrican | Material/family candidate; review D13; unit unresolved |
| 95 | CRUSHED MATERIAL | Material/family candidate; review D13; unit unresolved |
| 96 | HDPE_Black Jerrican | Material/family candidate; review D13; unit unresolved |
| 97 | HD Crushed Clear | Material/family candidate; review D13; unit unresolved |
| 98 | Crushed Abacus | Material/family candidate; review D13; unit unresolved |
| 99 | HD Pure White | Material/family candidate; review D13; unit unresolved |
| 100 | HD BLUE JERRICAN | Material/family candidate; review D13; unit unresolved |
| 101 | HD White jerrycan (Clear) | Material/family candidate; review D13; unit unresolved |
| 102 | POA Tank | Material/family candidate; review D13; unit unresolved |

### 09.FG Stock September .xlsx / Carrier Bags

| Row | A customer/subgroup raw | B detail | C size | D brand | E pack | G unit |
|---|---|---|---|---|---|---|
| 4 | ∅ | WHITE#12-LG | ∅ | UNIVERSAL | 50X60 | ctn |
| 5 | ∅ | WHITE#12-HG | ∅ | UNIVERSAL II | 50X50 | ctn |
| 6 | ∅ | WHITE#15 | ∅ | BEST | 40X50 | ctn |
| 7 | LAMECH | WHITE#15 | ∅ | BEST | 40X50 | ∅ |
| 8 | ∅ | WHITE#22 | ∅ | BEST | 35X40 | ctn |
| 9 | ∅ | WHITE#25 | ∅ | BEST | 50X20 | ctn |
| 10 | ∅ | WHITE#15 | ∅ | UNIVERSAL-I | 40X50 | ctn |
| 11 | ∅ | WHITE#22 | ∅ | UNIVERSAL-I | 35X40 | ctn |
| 12 | ∅ | WHITE#25 | ∅ | UNIVERSAL-I | 25X30 | ctn |
| 13 | ∅ | WHITE#15 | ∅ | UNIVERSAL-II | 40X50 | ctn |
| 14 | BROT BAKERS | WHITE #15 | ∅ | UVIVERSAL -II | 40X50 | ctn |
| 15 | ∅ | WHITE #22 | ∅ | UNIVERSAL-II | 35X40 | ctn |
| 16 | BROT BAKERS | WHITE #22 | ∅ | UNIVERSAL-II | 35X40 | ctn |
| 17 | KENJOY SUPERMARKET | WHITE#22 | ∅ | UNIVERSAL-II | 35X40 | ctn |
| 18 | ∅ | WHITE#25 | ∅ | UNIVERSAL-II | 25X30 | ctn |
| 19 | ∅ | WHITE#28 | ∅ | UNIVERSAL-II | 30X20 | ctn |
| 20 | ANARPOURNA | WHITE#22 | ∅ | PLAIN | ∅ | ctn |
| 21 | ∅ | BLUE#12-LG | ∅ | UNIVERSAL | 50X60 | ctn |
| 22 | ∅ | BLUE#12-HG | ∅ | UNIVERSAL | 50X50 | ctn |
| 23 | ∅ | BLUE#15 | ∅ | UNIVERSAL | 50X40 | ctn |
| 24 | ∅ | BLUE#15 | ∅ | BEST | 40X50 | ctn |
| 25 | PATRICK | BLUE#15 | ∅ | PLAIN | 40x50 | ctn |
| 26 | ∅ | BLUE#22 | ∅ | BEST | 35X40 | ctn |
| 27 | ∅ | BLUE#22 | ∅ | BEST | 50X40 | ctn |
| 28 | PATRICK | BLUE#22 | ∅ | PLAIN | 40X50 | ctn |
| 29 | ∅ | BLUE#25 | ∅ | BEST | 50X20 | ctn |
| 30 | ∅ | BLUE#25 | ∅ | BEST | 30X25 | ctn |
| 31 | ∅ | BLUE#25 | ∅ | BEST | 20X30 | ctn |
| 32 | ∅ | BLUE#35 | ∅ | BEST | 20X25 | ctn |
| 33 | ∅ | BLUE#25 | ∅ | UNIVERSAL | 25X30 | ctn |
| 34 | ∅ | BLUE#25 | ∅ | UNIVERSAL | 30X20 | ctn |
| 35 | PATRICK | BLUE#25 | ∅ | NO LABEL | 50X20 | ctn |
| 36 | ∅ | PURPLE#12 | ∅ | BEST | 50X60 | ctn |
| 37 | ∅ | PURPLE#15 | ∅ | BEST | 40X50 | ctn |
| 38 | ∅ | PURPLE#22 | ∅ | BEST | 35X40 | ctn |
| 39 | ∅ | ORANGE#12 | ∅ | BEST | 50X60 | ctn |
| 40 | ∅ | ORANGE#15 | ∅ | BEST | 40X50 | ctn |
| 41 | ∅ | ORANGE#22 | ∅ | BEST | 35X40 | ctn |
| 42 | ∅ | GREEN#12 - LG | ∅ | BEST | 50X60 | ctn |
| 43 | ∅ | GREEN#12-HG | ∅ | BEST | 50X50 | ctn |
| 44 | ∅ | GREEN#22 | ∅ | BEST | 50X40 | ctn |
| 45 | ∅ | GREEN#25 | ∅ | BEST | 46X20 | ctn |
| 46 | SIMON | GREEN #25(Lemon green) | ∅ | BEST | 44X20 | ctn |
| 47 | ARYOUS | GREEN #25 | ∅ | BEST | 44X20 | ctn |
| 48 | JOSEPH MANDE | GREEN#25 | ∅ | BEST | 40X20 | ctn |
| 49 | KIZZA | GREEN | ∅ | PLAIN | 10X30 | ctn |
| 50 | ∅ | RED#12 | ∅ | BEST | 50X60 | ctn |
| 51 | ∅ | YELLOW#22 | ∅ | BEST | 35X40 | ctn |
| 52 | PRINCE KAYEMBA | WHITE#22 | ∅ | PLAIN | 80X50 | ctn |
| 53 | Lamech | BLACK#15 | ∅ | ∅ | 72X50 | ctn |
| 54 | MAAMA CHARLES | BLACK#15 | ∅ | SUPER | 60X100 | ctn |
| 55 | ∅ | BLACK#12-LG | ∅ | BEST | 50X60 | ctn |
| 56 | ∅ | BLACK#12-HG | ∅ | BEST | 50X50 | ctn |
| 57 | ∅ | BLACK#15 | ∅ | BEST | 30X60 | ctn |
| 58 | WALTER | BLACK#15 | ∅ | BEST | 40X50 | ctn |
| 59 | OKELLO SIMON | BLACK# 15 | ∅ | BEST | 50X50 | ctn |
| 60 | OKELLO SIMON | BLACK#15 | ∅ | BEST | 42X50 | ctn |
| 61 | ∅ | BLACK#15 | ∅ | BEST | 44X50 | ctn |
| 62 | ∅ | BLACK#15 | ∅ | BEST | 46X50 | ctn |
| 63 | ∅ | BLACK#15-LG | ∅ | BEST | 50X50 | ctn |
| 64 | ∅ | BLACK#15-HG | ∅ | BEST | 40X50 | ctn |
| 65 | ∅ | BLACK# 15 | ∅ | BEST | 44X50 | ctn |
| 66 | ARYOUS | BLACK#15 ( double) | ∅ | BEST | 40X50 | ctn |
| 67 | Lamech | BLACK#22 | ∅ | ∅ | 100X50 | ctn |
| 68 | MAAMA CHARLES | BLACK#22 | ∅ | SUPER | ∅ | ctn |
| 69 | ∅ | BLACK#22-LG | ∅ | BEST | 50X40 | ctn |
| 70 | ∅ | BLACK#22 | ∅ | BEST | 46X40 | ctn |
| 71 | WALTER | BLACK#22 | ∅ | BEST | 80X40 | ctn |
| 72 | ∅ | BLACK#22- LG | ∅ | BEST | 35X40 | ctn |
| 73 | ∅ | BLACK#22-HG | ∅ | BEST | 35X40 | ctn |
| 74 | ARYOUS | BLACK#22 (Double) | ∅ | BEST | 40X40 | ctn |
| 75 | ∅ | BLACK#25-LG | ∅ | BEST | 25X40 | ctn |
| 76 | ∅ | BLACK#25-HG | ∅ | BEST | 25X40 | ctn |
| 77 | ∅ | BLACK#28 | ∅ | BEST | 25X40 | ctn |
| 78 | PASCALINE | BLACK#15 ( Double ) | ∅ | BEST | 50X50 | ctn |
| 79 | IKUNDA | BLACK#15 | ∅ | BEST | 42X50(double) | ctn |
| 80 | IKUNDA | BLACK#22 | ∅ | BEST | ∅ | ctn |
| 81 | ∅ | BLACK#35 | ∅ | BEST | 20X25 | ctn |

### 09.FG Stock September .xlsx / Flat Bags

| Row | A customer/subgroup raw | B detail | C size | D brand | E pack | G unit |
|---|---|---|---|---|---|---|
| 4 | HDPE FLAT PLAIN BAGS | ∅ | ∅ | ∅ | ∅ | ∅ |
| 5 | ∅ | ∅ | 5x8 | BEST | 150 PCS | ctn |
| 6 | ∅ | ∅ | 5X8 | BEST | 120 PCS | ctn |
| 7 | ∅ | ∅ | 5X8 | BEST | 130 PCS | ctn |
| 8 | ∅ | ∅ | 5x8 | BEST | 160 PCS | ctn |
| 9 | ∅ | ∅ | 5x8 | BEST | 140 PCS | ctn |
| 10 | ∅ | ∅ | 5x8 | BEST | 124 PCS | ctn |
| 11 | ∅ | ∅ | 5x8 | BEST | 100PCS | ctn |
| 12 | ∅ | ∅ | 5x8 | BEST | 114 Pcs | ctn |
| 13 | ∅ | ∅ | 5x8 | Range( GREEN) | 120 Pcs | ctn |
| 14 | ∅ | ∅ | 6X12 | BEST | 124 PCS | ctn |
| 15 | ∅ | ∅ | 6X12 | BEST | 116 PCS | ctn |
| 16 | ∅ | ∅ | 6x12 | BEST | 100 Pcs | ctn |
| 17 | Jorem | ∅ | 4X8 | BEST | 160 PCS | ctn |
| 18 | Solomon | ∅ | 7x12 | PLAIN | 56 PCS | Ctn |
| 19 | Aryous | ∅ | 7X12 | BEST | 110 PCS | ctn |
| 20 | ∅ | ∅ | 7X12 | BEST | 100 PCS | ctn |
| 21 | ∅ | ∅ | 7X12 | BEST | 90 PCS | ctn |
| 22 | ∅ | ∅ | 7X12(H2O) | BEST | 70 PCS | ctn |
| 23 | ∅ | ∅ | 7X12 | BEST | 130 PCS | ctn |
| 24 | ∅ | ∅ | 7X12 | BEST | 150 PCS | ctn |
| 25 | r | ∅ | 7X12 | BEST | 120 PCS | ctn |
| 26 | ∅ | ∅ | 7x12 | BEST | 160 PCS | ctn |
| 27 | ∅ | ∅ | 7X12 | PASSION -I | 70 PCS | ctn |
| 28 | ∅ | ∅ | 7x12 | PASSION -II | ∅ | ctn |
| 29 | ∅ | ∅ | 7X12-HG | PASSION | ∅ | ctn |
| 30 | ∅ | ∅ | 7X12 | STARLEX - I | 60 PCS | ctn |
| 31 | ∅ | ∅ | 7x12 | STARLEX -II | ∅ | ctn |
| 32 | ∅ | ∅ | 7X12-HG | STARLEX | ∅ | ctn |
| 33 | ∅ | ∅ | 7X12 | RANGE[6X10.5] | 70 PCS | ctn |
| 34 | Solomon | ∅ | 7X12 | RANGE[5.75X11.5] | 70 PCS | ctn |
| 35 | ∅ | ∅ | 7x12 | Best | 80 Pcs | ctn |
| 36 | Justine-Congo | ∅ | 7X12 | Range( RED) | 90 Pcs | ctn |
| 37 | ∅ | ∅ | 7x12 | RANGE (RED) | 70 Pcs | ctn |
| 38 | ∅ | ∅ | 7x12 | RANGE(RED) | 60 Pcs | ctn |
| 39 | ∅ | ∅ | 7x12 | RANGE(RED) | 68 Pcs | ctn |
| 40 | ∅ | ∅ | 7x12 -HG | RANGE | ∅ | ctn |
| 41 | Gayaza | ∅ | 7x12 | BEST | ∅ | ctn |
| 42 | Ikunda | ∅ | 7x12 | BEST | 114 Pcs | ctn |
| 43 | Zafar | ∅ | 7x12 | BEST | 74pcs | ctn |
| 44 | Justine-congo | ∅ | 7x12 -H2O | Range (GREEN)6.5x11.5 | ∅ | ctn |
| 45 | Zafar | ∅ | 7x12 | RANGE (RED) | 74 Pcs | ctn |
| 46 | solomon | ∅ | 7X12 | RANGE (RED) | 74 Pcs | ctn |
| 47 | solomon | ∅ | 7x12 | RANGE (RED) | 72 Pcs | ctn |
| 48 | Zafar | ∅ | 7X12 | RANGE (RED) | 72 Pcs | ctn |
| 49 | ∅ | ∅ | 9X15 | BEST | 110 PCS | ctn |
| 50 | ∅ | ∅ | 9X15 | BEST | 126 PCS | ctn |
| 51 | ∅ | ∅ | 9x15 | BEST | 120 PCS | ctn |
| 52 | ∅ | ∅ | 9X15 | BEST | 86 PCS | ctn |
| 53 | ∅ | ∅ | 9x15 | BEST | 100 PCS | ctn |
| 54 | ∅ | ∅ | 9X15 | BEST | 150 PCS | ctn |
| 55 | Zafar | ∅ | 9x15 | BEST | 80 Pcs | ctn |
| 56 | ∅ | ∅ | 9x15 | RANGE | 86 Pcs | ctn |
| 57 | Hakim | ∅ | 8x13 | PLAIN | 94 Pcs | ctn |
| 58 | Kzza | HD Flat Bags- Green | 10X30 | PLAIN | 50 PCS | ctn |
| 59 | ∅ | HD Flat Bags- Green | 9X15-H2O | BEST | 100 PCS | ctn |
| 60 | Beatrice | HD Flat Bags | 7X10-HD | PLAIN | 100 Pcs | kg |
| 61 | Graphic  Systems | HD Flat Bags- (100 pkts / Carton) | 15.6X25.6-HD | PLAIN | 100PCS | ctn |
| 62 | Get Rich Investment | HD White Bags | 3.5x4 | Real Coffee | 200 PCS | kg |
| 63 | ∅ | HD Yellow Bags | 3.5x4 | Real Coffee | 200 Pcs | kg |
| 64 | Pargati Plastic | HD White Bags | 8.5x16 | PLAIN | 100 Pcs | kg |
| 65 | Pargati Plastic | HD White Bags | 7.5X13 | PLAIN | 100 Pcs | kg |
| 66 | Pargati Plastic | HD White Bags | 8X10 | PLAIN | 100 Pcs | kg |
| 67 | Transbala Company Ltd | HD White Bags | 3x4 | Rido Coffee | 200 Pcs | kg |
| 68 | ∅ | HD Yellow Bags | 3x4 | Rido Coffee | 200 Pcs | kg |
| 69 | Getahead | HD Plain Bags | 5x7 | PLAIN | ∅ | kg |
| 70 | Abu- Nateete | HD Plain Bags | 7.5x12x45g | PLAIN | 60 Pcs | kg |
| 71 | Mulungi Best Coffee | HD Yellow Bags | 3X4 | Uganda's coffee | 200 Pcs | kg |
| 72 | Fresh | HD Plain Bags | 2.75x12 | ∅ | ∅ | kg |
| 73 | Fresh | HD Plain Bags | 4X12 | ∅ | ∅ | Kg |
| 74 | Fresh | HD Plain Bags | 2.5x10 | ∅ | ∅ | kg |
| 75 | Fresh | HD Plain Bags | 6X13 | ∅ | ∅ | kg |
| 76 | Fresh | HD Plain Bags | 6x18 | ∅ | ∅ | kg |
| 77 | Furaha | HD printed bags | 16x20 | ∅ | ∅ | kg |
| 78 | LD PLAIN BAGS | ∅ | ∅ | ∅ | ∅ | ∅ |
| 79 | ∅ | LD Flat Bags- Red | 9X15-LD | BEST | 200 PCS | ctn |
| 80 | Amina-Kikuubo | LD Flat bags-Red | 9x15 | BEST | 170 Pcs | ctn |
| 81 | ∅ | LD Flat Bags- Green Normal | 9X15-LD | BEST | 200 PCS | ctn |
| 82 | Hakim | LD Flat Bags- Green | 9X15- LD | GREEN | 200 PCS | kg |
| 83 | ∅ | Plain Bread Wrappers | 9X15-LD | ∅ | 100 PCS | kg |
| 84 | ∅ | LD Plain bags | 9x16- LD | ∅ | 100 Pcs | kg |
| 85 | ∅ | Plain Bread Wrappers | 11X18 | ∅ | 100 PCS | kg |
| 86 | ∅ | Plain Bread Wrappers | 11.5X20.5 | ∅ | 100 PCS | kg |
| 87 | Hakim | Plain Bread Wrappers | 8.5X14-LD | ∅ | 100 PCS | kg |
| 88 | Nelson / Herzriya | ∅ | 30X50-LD | PLAIN | ∅ | kg |
| 89 | Wateya | ∅ | 16X19-LD | PLAIN | ∅ | kg |
| 90 | Isaac | ∅ | 7X18-LD | PLAIN | ∅ | kg |
| 91 | Amir / Brian | ∅ | 3X5-LD | BEST | 90 Pcs | ctn |
| 92 | Amir / Brian | ∅ | 4X6-LD | BEST | 90 PCS | ctn |
| 93 | Titan | ∅ | 16"X1Mtr | PLAIN | ∅ | kg |
| 94 | City-City | LD coloured nursery bags | 14x14 | PLAIN | ∅ | kg |
| 95 | City-City | LD coloured nursery bags | 10X10 | PLAIN | ∅ | kg |
| 96 | ∅ | LD White nursery bags | 30x32 | PLAIN | ∅ | Kgs |
| 97 | ∅ | LD Black nursery bags | 12x12 | PLAIN | ∅ | kg |
| 98 | Bhatia | LD Plain bags | 12.5X16 | PLAIN | ∅ | kg |
| 99 | Graphic  Systems | LD Plain bags | 8x13 | PLAIN | 100 Pcs | kg |
| 100 | Bhatia | LD Plain bags | 12x14 | PLAIN | 100 Pcs | kg |
| 101 | ∅ | LD Plain bags | 14x20 | PLAIN | ∅ | ∅ |
| 102 | ∅ | LD Plain bags | 16x20 | PLAIN | ∅ | kg |
| 103 | Jurose Organic | LD Plain bags | 12x32 | PLAIN | 25 Pcs | kg |
| 104 | ∅ | LD Plain bags | 15x22 | PLAIN | ∅ | kg |
| 105 | ∅ | LD Plain roll | 8.5x60g | PLAIN | ∅ | kg |
| 106 | ∅ | LD white bags | 8x12 | ∅ | ∅ | kg |
| 107 | ∅ | LD printed bags | 7x12 | ∅ | ∅ | kg |
| 108 | ∅ | LD printed bags | 9x32 | ∅ | ∅ | kg |
| 109 | Patel /Cored Packaging | LD Plain bags | 13x18 | PLAIN | ∅ | kg |
| 110 | Nagrace Investment | LD  Grade ll soap | 3.5x20 | Morning star bar soap | ∅ | kg |
| 111 | ∅ | LD Plain bags | 8x18 | PLAIN | ∅ | kg |
| 112 | ∅ | LD Printed bags | ∅ | Pharmacy | ∅ | kg |
| 113 | BW Investment | LD Printed rolls | 5x200g | BW Daddies | ∅ | kg |
| 114 | Sangam Restaurant | LD Plain bags | 15x22 | PLAIN | ∅ | kg |
| 115 | Tumwine | LD white printed exam bags | 12x16 | Exam bags | ∅ | kg |
| 116 | Pharmacy Packing Bags | LD whitebags | 8x12 | ∅ | ∅ | kg |
| 117 | Asante Dry Cleaners | LD white | 26x42 | ∅ | ∅ | kg |
| 118 | Maries Special | LD printed rolls | 5x200g | Daddies | ∅ | kg |
| 119 | Maries Special | LD Plain rolls | 6X200 g | Plain | ∅ | kg |
| 120 | Titan Industies Ltd | LD Printed bags | 2.5x31x120g | PLAIN | ∅ | kg |
| 121 | VIP Boutique | LD white printed D-Punch Bags | 15x20x360g | ∅ | ∅ | kg |
| 122 | Herzirya | LD  Plain bags | 23x27.5 | ∅ | ∅ | kg |
| 123 | Titan | LD Clear plain | 11.5x3 | ∅ | ∅ | kgs |
| 124 | ∅ | LD plain bags | 3x9 | Plain | ∅ | ctn |
| 125 | Titan | LD Clear plain bags | 3x11.5 | Plain | ∅ | kg |
| 126 | ∅ | LD Clear plain bags | 9x16 | Plain | ∅ | kg |
| 127 | Getahead | LD Clear plain | 11.5x80 | ∅ | ∅ | kg |
| 128 | Nyebwa | LD Clear printed | 7x10 | ∅ | ∅ | kg |
| 129 | Fresh | LD Plain bags | 28x57 | ∅ | ∅ | kg |
| 130 | Othieno | LD Plain bags | 21x68 | ∅ | ∅ | kg |
| 131 | Othieno | LD Plain bags | 12.5x23 | ∅ | ∅ | kg |
| 132 | Karuka Agencies | LD printed bags | 14x20 | ∅ | ∅ | kg |
| 133 | PP PLAIN BAGS | ∅ | ∅ | ∅ | ∅ | ∅ |
| 134 | Josa | PP Flat Bags | 4X19 | ∅ | 100 PCS | kg |
| 135 | Doma | LD Flat bags | 4x19 | ∅ | 100 PCS | kg |
| 136 | Pex | PP Flat Bags | 4X19 | ∅ | 100 PCS | kg |
| 137 | RK | PP Flat Bags | 4X19 | ∅ | 100 PCS | kg |
| 138 | RK | PP Flat Bags | 3.75X19 | ∅ | 100 PCS | kg |
| 139 | ∅ | PP Flat Bags | 8x14 | ∅ | 100 PCS | Kg |
| 140 | Pure Wash | PP Flat Bags | 4X19 | ∅ | 100 PCS | kg |
| 141 | Malaika Supermarket | PP Flat Bags | 7X11 | ∅ | 100 PCS | Kg |
| 142 | Hajjat | PP Flat Bags | 8x10 | Plain | 100 Pcs | kg |
| 143 | Shabba Crunchy | PP Flat Bags (Rolls) | 5x200g | Shabba Crunchy | ∅ | kg |
| 144 | Iz Best Enterprises | PP Flat Bags (Rolls) | 4.5x200g | Daddies | ∅ | kg |
| 145 | Iz Best Enterprises | PP Flat Bags (Rolls) | 6X200 g | Cake | ∅ | kg |
| 146 | Cored Packaging | PP Flat Bags | 7x11 | PLAIN | 100 Pcs | kg |
| 147 | Cored Packaging | PP Flat Bags | 6x10 | PLAIN | 100 Pcs | kg |
| 148 | Cored Packaging | PP Flat Bags | 8x11 | PLAIN | 100 Pcs | kg |
| 149 | Cored Packaging | PP Flat Bags | 5x7 | PLAIN | 100 Pcs | kg |
| 150 | Jjajja Bites | PP Flat rolls | 4x200g | Jjajja bites | ∅ | kg |
| 151 | Shoe Bill Co . LTD | PP Flat Bags | 8x13 | Chicken Tack | 100 Pcs | kg |
| 152 | Shoe Bill Co . LTD | PP Flat Bags | 8x12 | Masaka Rice | 100 Pcs | kg |
| 153 | Shoe Bill Co . LTD | PP Flat Bags | 6x9 | Masaka Rice | 100 Pcs | kg |
| 154 | Nedia Foods | PP Flat Bags | 4x5 | ∅ | ∅ | kg |
| 155 | Maries Special | PP Flat Bags | 6x8 | ∅ | ∅ | kg |
| 156 | Maries Special | PP Flat Bags | 7x10 | ∅ | ∅ | kg |
| 157 | ∅ | PP Flat Bags | 8x10 | ∅ | ∅ | kg |
| 158 | AK MD Bakery | PP Printed rolls | 5x200g | ∅ | ∅ | kg |
| 159 | ∅ | PP Printed rolls | 4.5x200g | ∅ | ∅ | kg |
| 160 | ∅ | PP Printed rolls | 4.5X100g | ∅ | ∅ | kg |
| 161 | GARBAGE BAGS | ∅ | ∅ | ∅ | ∅ | ∅ |
| 162 | ∅ | HD -Black | 30X36 | BEST | 20X25 | ctn |
| 163 | ∅ | LD- Black | 30X36 | BEST | 20X25 | ctn |
| 164 | ∅ | HD- Black | 30X46 | BEST | 20X25 | ctn |
| 165 | ∅ | HD-Yellow | 30X36 | BEST | 20X25 | ctn |
| 166 | ∅ | HD -Yellow | 30x46 | BEST | 20X25 | ctn |
| 167 | ∅ | HD-Red | 30X36 | BEST | 20X25 | ctn |
| 168 | ∅ | HD -Red | 30x46 | BEST | 20X25 | ctn |
| 169 | ∅ | HD Black | 26x36 | BEST | 20X25 | ctn |
| 170 | ∅ | HD Red | 26x36 | BEST | 20X25 | ctn |
| 171 | ∅ | HD Yellow | 26x36 | BEST | 20X25 | ctn |
| 172 | ∅ | HD-Brown | 26X36 | BEST | 20X25 | ctn |
| 173 | ∅ | HD-Brown | 30X36 | BEST | 20X25 | ctn |
| 174 | Zahil Investment | HD Black | 19X24 | PLAIN | 50X20 | ctn |
| 175 | Zahil Investment | HD-Red | 22x35 | ∅ | ∅ | ctn |
| 176 | Zahil Investment | HD-Black | 22x35 | ∅ | ∅ | ctn |
| 177 | ∅ | HD-Brown | 22x35 | ∅ | ∅ | ctn |
| 178 | LAUNDRY BAGS | ∅ | ∅ | ∅ | ∅ | ∅ |
| 179 | ∅ | LD-CLEAR | 26X40 | PLAIN | 20X25 | kg |
| 180 | ∅ | LD-CLEAR | 26X52 | PLAIN | 20X25 | kg |
| 181 | ∅ | LD- CLEAR (long) | 26X62 | PLAIN | 20X25 | kg |
| 182 | ∅ | LD-DARK BLUE | 26X40 | PLAIN | 20X25 | kg |
| 183 | ∅ | LD-LIGHT BLUE | 26X40 | PLAIN | 20X25 | kg |
| 184 | ∅ | LD-WHITE | 26X40 | PLAIN | 20X25 | kg |
| 185 | ∅ | LD-TINTED BLUE | 26X40 | PLAIN | 20X25 | kg |
| 186 | Apple Dry Cleaners | LD-LIGHT BLUE | 26X40 | PRINTED | 20X25 | kg |
| 187 | LD PRINTED BREAD WRAPPERS | ∅ | ∅ | ∅ | ∅ | ∅ |
| 188 | Iz Best Enterprises | LD printed bread wrappers | 9x16 | white sweet bread | 100 pcs | kg |
| 189 | ∅ | LD printed bread wrappers | 8X15 | Mandazi /Donuts | 100 pcs | kg |
| 190 | ∅ | LD printed bread wrappers | 11x18 | Sweet white bread | 100 pcs | kg |
| 191 | Mom and Son | LD printed bread wrappers | 11x18 | Yellow bread | 100 pcs | ctn |
| 192 | ∅ | LD printed bread wrappers | 11x18 | Sweet Brown | 100 pcs | ctn |
| 193 | ∅ | LD printed bread wrappers | 12x20 | Sweet Brown | 100 pcs | ctn |
| 194 | Sweet Haven | LD printed bread wrappers | 11x18 | sweet white bread | 100 pcs | kg |
| 195 | Maries Special | LD printed bread wrappers | 9x16 | white sweet bread | 100 pcs | kg |
| 196 | ∅ | LD printed bread wrappers | 9x16 | Milk Bread | 100 pcs | kg |
| 197 | ∅ | LD printed bread wrappers | 11x18 | Sweet white bread buns | 100 pcs | Kg |
| 198 | ∅ | LD printed bread wrappers | 11x18 | white sweet bread | 100 pcs | Kg |
| 199 | ∅ | LD printed bread wrappers | 11x18 | Milk Bread | 100 pcs | Kg |
| 200 | ∅ | LD printed bread wrappers | 11x18 | Coconut Bread | 100 pcs | Kg |
| 201 | ∅ | LD printed bread wrappers | 11x18 | Cake Bread | 100 pcs | Kg |
| 202 | ∅ | LD printed bread wrappers | 11x18 | Brown sweet bread | 100 Pcs | kg |
| 203 | ∅ | LD printed bread wrappers | 11x18 | Fruit Bread | 100 Pcs | kg |
| 204 | ∅ | LD printed bread wrappers | 9x15 | Brown sweet bread | 100 Pcs | kg |
| 205 | ∅ | LD printed bread wrappers | 9x16 | Mandazi /Donuts (6 Pcs) | 100 pcs | Kg |
| 206 | ∅ | LD printed bread wrappers | 9x16 | Coconut Bread | 100 pcs | Kg |
| 207 | ∅ | LD printed bread wrappers | 9x16 | Yellow sweet  bread | 100 Pcs | kg |
| 208 | ∅ | LD printed bread wrappers | 9x16 | Cake Bread | 100 Pcs | kg |
| 209 | ∅ | LD printed bread wrappers | 11X18 | yellow sweet  bread | 100 pcs | Kg |
| 210 | ∅ | LD printed bread wrappers | 6x14 | Cake Bread | 100 Pcs | kg |
| 211 | ∅ | LD printed bread wrappers | 7X5 | Cake Bread | 100 Pcs | kg |
| 212 | ∅ | LD printed bread wrappers | 7x5 | white sweet bread | 100 P cs | kg |
| 213 | ∅ | LD printed bread wrappers | 8x15 | Mandazi/Donuts (400g) | ∅ | kg |
| 214 | Brot Bakers | LD printed bread wrappers | 11x18 | white sweet bread | 100 pcs | Kg |
| 215 | ∅ | LD printed bread wrappers | 11x18 | Sweet brown berad | 100 Pcs | kg |
| 216 | Francis Snacks | LD printed bread wrappers | 11x18 | white sweet bread | 100 pcs | Kg |
| 217 | Kiddawalime | LD printed bread wrappers | 12x17 | kiddawalime Sweet white bread buns | 100 Pcs | Kg |
| 218 | ∅ | LD printed bread wrappers | 12x17 | Delicious sweet white bread buns | 100 Pcs | kg |
| 219 | ∅ | LD printed bread wrappers | 12x20 | Delicious sweet white bread | 100 Pcs | kg |
| 220 | ∅ | LD printed bread wrappers | 9x16 | Delicious sweet bread | 100 Pcs | kg |
| 221 | Amen | LD printed bread wrappers | 11X18 | white sweet bread | 100 Pcs | Kg |
| 222 | ∅ | LD printed bread wrappers | 11x18 | Coconut Bread | 100 pcs | kg |
| 223 | ∅ | LD printed bread wrappers | 11x18 | Milk Bread | 100 Pcs | kg |
| 224 | ∅ | LD printed bread wrappers | 9X16 | white sweet bread | 100 Pcs | Kg |
| 225 | ∅ | LD printed bread wrappers | 11x18 | Milk Bread | 100 Pcs | kg |
| 226 | ∅ | LD printed bread wrappers | 11X18 | Coconut Bread | 100 Pcs | kg |
| 227 | ∅ | LD printed bread wrappers | 11x18 | Yellow bread | 100 Pcs | kg |
| 228 | 2t's Bakery | LD printed bread wrappers | 11X18 | Mandazi/Donuts | 100 Pcs | Kg |
| 229 | Tuwelane Bakery | LD printed bread wrappers | 11X18 | Buns | 100 Pcs | kg |
| 230 | ∅ | LD printed bread wrappers | 11x18 | Sweet white bread | 100 Pcs | kg |
| 231 | ∅ | LD printed bread wrappers | 9x16 | Sweet white bread | 100 Pcs | kg |
| 232 | ∅ | LD printed bread wrappers | 8x16 | Mandazi | 100 Pcs | kg |
| 233 | Refresh Hiper Café | LD printed bread wrappers | 11x18 | white sweet bread | 100 Pcs | kg |
| 234 | Refresh Hiper Café | LD printed bread wrappers | 9x16 | white sweet bread | 100 Pcs | kg |
| 235 | City Joy | LD printed bread wrappers | 11x18 | Yellow sweet  bread | 100 Pcs | kg |
| 236 | ∅ | LD printed bread wrappers | 11x18 | Buns | 100 Pcs | kg |
| 237 | ∅ | LD printed bread wrappers | 11x18 | Coconut Bread | 100 Pcs | kg |
| 238 | ∅ | LD printed bread wrappers | 11x18 | Brown bread | 100 Pcs | kg |
| 239 | ∅ | LD printed bread wrappers | 11x18 | white sweet bread | 100 Pcs | kg |
| 240 | ∅ | LD printed bread wrappers | 9x16 | white sweet bread | 100 Pcs | kg |
| 241 | ∅ | LD printed bread wrappers | 9x16 | Brown bread | 100 Pcs | kg |
| 242 | ∅ | LD printed bread wrappers | 9x16 | Buns | 100 Pcs | kg |
| 243 | ∅ | LD printed bread wrappers | 9x16 | Yellow bread | 100 pcs | kg |
| 244 | ∅ | LD printed bread wrappers | 9x16 | Coconut Bread | 100 Pcs | kg |
| 245 | Purpose | LD printed bread wrappers | 11x20 | Sweet white bread | 100 Pcs | kg |
| 246 | Swaika | LD printed bread wrappers | 11x18 | white sweet bread | 100 Pcs | kg |
| 247 | ∅ | LD printed bread wrappers | 11x18 | Milk Flavoured,Sweet Yellow bread | 100 Pcs | kg |
| 248 | Home Delight | LD printed bread wrappers | 11x18 | White bread | 100 Pcs | kg |
| 249 | Elite | LD printed bread wrappers | 11x18 | Sweet white bread | 100 Pcs | kg |
| 250 | AK MD Bakery | LD printed bread wrappers | 9x16 | ∅ | 100 Pcs | kg |
| 251 | De Master Confectijnaries | LD printed bread wrappers | 11x18 | Sweet White bread | 100 Pcs | kg |
| 252 | ∅ | ∅ | 9x16 | white sweet bread | 100 Pcs | kg |
| 253 | Wise Miracle | LD printed bread wrappers | 8x15 | Sweet white bread | 100 Pcs | kg |

### 09.FG Stock September .xlsx / Packing

| Row | A customer/subgroup raw | B detail | C size | D brand | E pack | G unit |
|---|---|---|---|---|---|---|
| 4 | ∅ | ∅ | 11X18 | Plain | ∅ | kg |
| 5 | ∅ | ∅ | 8x18 | Plain | ∅ | kg |
| 6 | ∅ | ∅ | 8x14 | Plain | ∅ | kg |
| 7 | ∅ | ∅ | 9x15 | Plain | ∅ | kg |
| 8 | ∅ | ∅ | 7X12 | Red | 200 Pcs | kg |
| 9 | ∅ | ∅ | 7X12 | Green | 100 Pcs | kg |
| 10 | ∅ | ∅ | 7X12 | Blue | 100 Pcs | kg |
| 11 | ∅ | ∅ | 9x15 | Red | 200 Pcs | kg |
| 12 | ∅ | ∅ | 9x15 | Green | 100 Pcs | kg |
| 13 | ∅ | ∅ | 6X12 | Blue | 200 Pcs | kg |
| 14 | ∅ | ∅ | 5X8 | Green | 200 Pcs | kg |
| 15 | ∅ | ∅ | 4X6 | Green | 200 Pcs | kg |
| 16 | ∅ | ∅ | 4X6 - LD | Best | ∅ | kg |
| 17 | ∅ | ∅ | 3X5 - LD | Best | ∅ | kg |
| 18 | ∅ | ∅ | 3x5 - Green | Best | ∅ | kg |
| 19 | ∅ | ∅ | 7X12 | Range -New | ∅ | kg |
| 20 | ∅ | ∅ | 7X12 | Range -old | ∅ | kg |
| 21 | ∅ | ∅ | 7X12 | Passion | ∅ | kg |
| 22 | ∅ | ∅ | 7X12 | Starlex | ∅ | kg |
| 23 | ∅ | ∅ | Garbage | 30x46 | 25 Pcs | kg |
| 24 | ∅ | ∅ | Garbage | 30X36 | 25 Pcs | kg |
| 25 | ∅ | ∅ | Garbage | 26X36 | 25 Pcs | kg |
| 26 | CARRIER BAGS | ∅ | ∅ | ∅ | ∅ | kg |
| 27 | ∅ | ∅ | # 25 | Best | 25 Pcs | kg |
| 28 | ∅ | ∅ | # 28 | Best | 25 Pcs | kg |
| 29 | ∅ | ∅ | # 35 | Best | 25 Pcs | kg |
| 30 | ∅ | ∅ | # 15 | Universal | 40 Pcs | kg |
| 31 | ∅ | ∅ | # 15 | Universal | 30 Pcs | kg |
| 32 | ∅ | ∅ | # 28 | Universal | 30 Pcs | kg |
| 33 | ∅ | ∅ | # 25 | Universal | 25 Pcs | kg |
| 34 | ∅ | ∅ | # 25 | Universal | 50 Pcs | kg |
| 35 | ∅ | ∅ | # 12 | Universal | 50 Pcs | kg |
| 36 | ∅ | ∅ | # 22 | Universal | 35 Pcs | kg |
| 37 | ∅ | ∅ | # 12 | Best | 50 Pcs | kg |
| 38 | ∅ | ∅ | # 22 | Best | 35 Pcs | kg |
| 39 | ∅ | ∅ | # 22 | Best | 50 Pcs | kg |
| 40 | ∅ | ∅ | # 15 | Best | 40 Pcs | kg |
| 41 | ∅ | ∅ | # 15 | Best | 50 Pcs | kg |
| 42 | ∅ | ∅ | # 15 | Super | ∅ | kg |
| 43 | ∅ | ∅ | # 15 -Green | Best | 40 Pcs | kg |
| 44 | HARD PLAIN OUTER PACKING | ∅ | ∅ | ∅ | ∅ | kg |
| 45 | ∅ | ∅ | 18x25 | ∅ | ∅ | kg |
| 46 | ∅ | ∅ | # 12 | ∅ | ∅ | kg |
| 47 | ∅ | ∅ | 14x24 | Starlex & Passion | ∅ | kg |
| 48 | ∅ | ∅ | 3X5 - LD | ∅ | ∅ | kg |
| 49 | ∅ | ∅ | 4x6 | ∅ | ∅ | kg |
| 50 | ∅ | HARD PRINTED OUTER PACKING | ∅ | ∅ | ∅ | kg |
| 51 | ∅ | ∅ | 7X12- Old | Range | ∅ | kg |
| 52 | ∅ | ∅ | 7x12 - New | Range | ∅ | kg |
