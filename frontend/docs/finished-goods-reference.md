# Finished-goods frontend reference

`09.FG Stock September .xlsx` is a development reference only. The browser uses
`src/lib/finishedGoodsReference.ts`; it does not open, upload or parse Excel.

The importer reads all three sheets: 78 Carrier Bags variants, 244 Flat Bags
variants and 46 Packing variants. Merged section headings and formula-only empty
rows are excluded. Zero-stock variants are retained. Packing is kept as its own
category with the sheet's four packing subgroups and kg units.

Run `python scripts/extract-finished-goods.py <workbook.xlsx>` with openpyxl
available to regenerate the reference. Run `node scripts/check-finished-goods.mjs`
to check identities, source balances, search and ledger calculations.

## Source interpretation

- Daily formula cells use their saved numeric results. A numeric text entry is
  converted to a number. Totals are recomputed from opening plus daily IN minus
  daily OUT, and compared with recorded source closing balances.
- Carrier and Flat Bags date headers begin September 1, 2026. Flat Bags row 80
  has 6 IN and 10 OUT under October 1, so its September closing is 4 ctn and its
  October closing is 0 ctn. These entries are not reassigned to September.
- Packing headers cover May 2026, while its opening label says `03/05/26`.
  All opening quantities and daily movements are blank. Its calculated zeros
  come from an empty template, so the frontend displays unknown balances. The
  header dates are retained; actual opening quantity/date need client confirmation
  before backend import.
- Carrier customer blanks interleave general variants with named custom
  variants and are not forward-filled. The Flat Bags bread-wrapper section uses
  customer groups; blank cells continue the most recent customer until the next
  named customer. Inspected coffee colour pairs, RK size continuation and the
  AK MD printed-roll block also retain their customer grouping. The original
  customer cell and an inheritance flag remain on each master record.
- Carrier row 7 has a blank unit, inferred as ctn from matching adjacent
  WHITE#15/BEST/40X50 variants. Flat Bags row 101 is inferred as kg from nearby
  LD Plain bags. The original blank unit and a source note are preserved.
- Unit spelling/case is normalized to ctn or kg. Size uses uppercase X; packing
  text is uppercased. Names and brand spellings are retained. Brand filters group
  capitalization variants without combining product records.
- IDs hash category, subgroup, customer, item details, size, brand, packing and
  unit. Four records share a repeated identity; they retain a source-row suffix
  and note rather than being silently merged. Source sheet and row remain on
  every variant.

## Frontend state and backend replacement

`InventoryContext` owns finished-goods and raw-material movements separately.
Entries survive route navigation and reset on refresh, matching the existing
Sales Orders Context. No inventory API calls or durable persistence are added.

Current stock is opening plus all IN minus all OUT. Monthly opening carries
forward movements before the selected month, and monthly totals include only
that month's dates. Unknown opening balances stay unknown. Units are never
summed together; summary cards count variants and recorded out-of-stock items.

Sales order creation selects this master by variant ID. Demand compares each
open-order line with current physical stock; Required Qty means the shortage.
It does not reserve or deduct stock. Legacy names are matched only when unique;
ambiguous/unmatched items are marked Not linked. Unit mismatches are explicit.

For backend integration, replace reference/master loading and Context add methods
with inventory APIs. Keep stable variant references on order lines, validate
quantities/dates/units server-side, reconcile the source notes, and define actual
reservation, production and dispatch rules before enabling real transactions.
