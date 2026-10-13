import { useAuth } from '@/context/AuthContext';
import { findWorkItem } from '@/lib/parentJobCards';
import { useJobCards } from '@/context/JobCardsContext';
import { Link } from 'react-router-dom';
import { reserved } from '@/lib/fulfillment';
import { Fragment, useEffect, useMemo, useState } from 'react';
import { ArrowDownToLine, ArrowUpFromLine, ChevronDown, Download, Printer, Search } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { ENTRY_INPUT } from '@/components/ui/SearchSelect';
import { InventoryMovementModal } from '@/components/ui/InventoryMovementModal';
import { useInventory } from '@/context/InventoryContext';
import { FINISHED_GOODS, FINISHED_BY_ID, FINISHED_CATEGORY_LABEL, finishedBalance, finishedRangeBalance, finishedGoodName, finishedGoodLabel, matchesFinishedGood, type FinishedCategory, type FinishedGood } from '@/lib/finishedGoodsData';
import { SalesOrderDemand } from './SalesOrderDemand';

type Tab = 'levels' | 'movements' | 'report';
type CategoryFilter = FinishedCategory | 'all';
const TABS: [Tab, string][] = [['levels', 'Stock Levels'], ['movements', 'Movements'], ['report', 'Monthly Report']];
const CATEGORIES = Object.entries(FINISHED_CATEGORY_LABEL) as [FinishedCategory, string][];
const fmt = (value: number | null) => value === null ? 'Not recorded' : value.toLocaleString('en-IN', { maximumFractionDigits: 2 });
const TH = 'px-4 py-3 font-medium';
const TD = 'px-4 py-3';
const BUTTON = 'flex items-center gap-2 rounded-card border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus-visible:ring-2 focus-visible:ring-navy';

function ProductCell({ product, variant = false }: { product: FinishedGood; variant?: boolean }) {
  return <div className="min-w-[180px] max-w-[300px]">
    <p className="font-medium text-gray-900" title={finishedGoodLabel(product)}>{finishedGoodName(product)}</p>
    {variant && <p className="mt-1 text-xs text-gray-500">{[product.size, product.brand, product.packingSize].filter(Boolean).join(' · ')}</p>}
    {product.customer && <p className="mt-0.5 text-xs text-gray-500">Customer: {product.customer}</p>}
    {product.itemDetails && product.category !== 'carrier-bags' && <p className="mt-0.5 text-xs text-gray-400">{product.subgroup}</p>}
    {product.dataNotes.length > 0 && <details className="mt-1 text-xs text-amber-700"><summary className="cursor-pointer">Source notes</summary><p className="mt-1">{product.dataNotes.join(' ')}</p></details>}
  </div>;
}
function StockStatus({ quantity }: { quantity: number | null }) {
  const label = quantity === null ? 'Not recorded' : quantity < 0 ? 'Negative balance' : quantity === 0 ? 'Out of stock' : 'In Stock';
  const style = quantity === null ? 'bg-gray-100 text-gray-500' : quantity <= 0 ? 'bg-red-50 text-red-700' : 'bg-emerald-50 text-emerald-700';
  return <span className={`whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-medium ${style}`}>{label}</span>;
}
function downloadCsv(filename: string, lines: (string | number | null)[][]) {
  const escape = (value: string | number | null) => {
    const text = value === null ? 'Not recorded' : String(value);
    const safe = typeof value === 'string' && /^[=+@-]/.test(text) ? `'${text}` : text;
    return `"${safe.replace(/"/g, '""')}"`;
  };
  const url = URL.createObjectURL(new Blob([lines.map(line => line.map(escape).join(',')).join('\n')], { type: 'text/csv;charset=utf-8' }));
  const link = document.createElement('a'); link.href = url; link.download = filename; link.click(); URL.revokeObjectURL(url);
}

export function StockPage() {
  const { user } = useAuth();
  const { ledger, finishedMovements, addFinishedMovement, finishedPieces, updateFinishedPieces } = useInventory();
  const { cards, load } = useJobCards();
  useEffect(() => { void load(); }, [load]);
  const [tab, setTab] = useState<Tab>('levels');
  const [category, setCategory] = useState<CategoryFilter>('all');
  const [query, setQuery] = useState('');
  const [brand, setBrand] = useState('all');
  const [unit, setUnit] = useState('all');
  const [month, setMonth] = useState('2026-09');
  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');
  const [model, setModel] = useState('all');
  const [movementType, setMovementType] = useState('all');
  const [limit, setLimit] = useState(25);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [direction, setDirection] = useState<'IN' | 'OUT' | null>(null);
  const [notice, setNotice] = useState('');
  const balances = useMemo(() => new Map(FINISHED_GOODS.map(product => [product.id, finishedBalance(product, finishedMovements)])), [finishedMovements]);
  const report = useMemo(() => new Map(FINISHED_GOODS.map(product => [product.id, from && to ? finishedRangeBalance(product, finishedMovements, from, to) : finishedBalance(product, finishedMovements, month)])), [finishedMovements, month, from, to]);
  const inCategory = FINISHED_GOODS.filter(product => category === 'all' || product.category === category);
  const brands = [...new Map(inCategory.filter(product => product.brand).map(product => [product.brand.toLowerCase(), product.brand])).values()].sort((a, b) => a.localeCompare(b));
  const units = [...new Set(inCategory.map(product => product.unit))].sort();
  const products = inCategory.filter(product => matchesFinishedGood(product, query) && (brand === 'all' || product.brand.toLowerCase() === brand.toLowerCase()) && (unit === 'all' || product.unit === unit) && (model === 'all' || finishedMovements.some(m => m.productId === product.id && (m.modelName ?? findWorkItem(cards, m.manufacturingItemId ?? m.jobCardId ?? '')?.modelName) === model)));
  const ids = new Set(products.map(product => product.id));
  const movements = finishedMovements.filter(movement => ids.has(movement.productId) && (movementType === 'all' || movement.type === movementType) && (!from || movement.date >= from) && (!to || movement.date <= to) && (model === 'all' || (movement.modelName ?? findWorkItem(cards, movement.manufacturingItemId ?? movement.jobCardId ?? '')?.modelName) === model))
    .sort((a, b) => b.date.localeCompare(a.date) || b.id.localeCompare(a.id));
  const outOfStock = [...balances.values()].filter(balance => balance.currentStock !== null && balance.currentStock <= 0).length;
  const kpis = [
    { label: 'Finished Goods', value: `${FINISHED_GOODS.length} variants`, hint: 'Distinct source variants · ctn and kg tracked separately' },
    { label: 'Carrier Bags', value: `${FINISHED_GOODS.filter(product => product.category === 'carrier-bags').length} variants`, hint: 'Brands, packing sizes and customer configurations' },
    { label: 'Flat Bags', value: `${FINISHED_GOODS.filter(product => product.category === 'flat-bags').length} variants`, hint: 'Includes plain, printed, garbage and laundry bags' },
    { label: 'Out of Stock', value: String(outOfStock), hint: 'Recorded balances at or below zero · minimums not supplied' },
  ];
  const resetList = () => { setLimit(25); setExpanded(null); };
  const exportReport = () => downloadCsv(`finished-goods-${category}-${month}.csv`, [
    ['Product ID', 'Product', 'Category', 'Customer', 'Size', 'Brand', 'Pieces', 'Packaging', 'Unit', 'Opening Stock', 'Total IN', 'Total OUT', 'Closing Stock'],
    ...products.map(product => {
      const row = report.get(product.id)!;
      return [product.id, finishedGoodName(product), FINISHED_CATEGORY_LABEL[product.category], product.customer, product.size, product.brand, finishedPieces[product.id] ?? product.pieces ?? null, product.packingSize, product.unit, row.openingStock, row.stockIn, row.stockOut, row.currentStock];
    }),
  ]);
  const count = tab === 'movements' ? movements.length : products.length;
  return <div className="space-y-6"><Card><p className="text-sm text-navy">Manufactured Stock IN requires independent QC release and final manager authorization, then an exact batch receipt from Job Cards.</p><p className="text-xs text-gray-500">Manual unbatched reference imports are restricted to Admin and cannot bypass an active product QC hold.</p><Link to="/job-cards" className="text-sm underline">Approved Job Card receipts</Link></Card>
    <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between print:hidden">
      <div><h1 className="text-2xl font-semibold text-navy">Stock</h1><p className="mt-1 text-sm text-gray-500">Finished goods inventory, stock movements and monthly reports.</p></div>
      <div className="flex items-center gap-2">{user?.role === "admin" ? <button type="button" onClick={() => setDirection('IN')} className={BUTTON}><ArrowDownToLine size={16} />Stock IN</button> : <Link to="/job-cards" className={BUTTON}><ArrowDownToLine size={16} />Receive Approved Batch</Link>}<button type="button" onClick={() => setDirection('OUT')} className="flex items-center gap-2 rounded-card bg-navy px-4 py-2 text-sm font-medium text-white hover:opacity-90 focus-visible:ring-2 focus-visible:ring-navy"><ArrowUpFromLine size={16} />Stock OUT</button></div>
    </header>
    <section aria-label="Stock summary" className="grid grid-cols-2 gap-4 lg:grid-cols-4 print:hidden">{kpis.map(card => <Card key={card.label}><p className="text-sm text-gray-500">{card.label}</p><p className="mt-1 text-2xl font-semibold text-navy">{card.value}</p><p className="mt-1 text-xs text-gray-500">{card.hint}</p></Card>)}</section>
    {notice && <p role="status" className="rounded-card bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{notice}</p>}
    <SalesOrderDemand />
    <div role="tablist" aria-label="Stock views" className="flex gap-6 border-b border-gray-200 print:hidden">{TABS.map(([id, label]) => <button key={id} type="button" role="tab" id={`stock-tab-${id}`} aria-selected={tab === id} aria-controls={`stock-panel-${id}`} onClick={() => { setTab(id); resetList(); }} className={`-mb-px border-b-2 pb-3 text-sm font-medium ${tab === id ? 'border-navy text-navy' : 'border-transparent text-gray-500 hover:text-navy'}`}>{label}</button>)}</div>
    <div role="group" aria-label="Finished goods categories" className="inline-flex flex-wrap rounded-card bg-gray-100 p-1 print:hidden">{([['all', 'All'], ...CATEGORIES] as [CategoryFilter, string][]).map(([id, label]) => <button key={id} type="button" aria-pressed={category === id} onClick={() => { setCategory(id); setBrand('all'); setUnit('all'); resetList(); }} className={`rounded-md px-3 py-1.5 text-sm font-medium ${category === id ? 'bg-white text-navy shadow-sm' : 'text-gray-600 hover:text-navy'}`}>{label}</button>)}</div>
    <div className="flex flex-wrap items-end gap-3 print:hidden">
      <div className="relative min-w-[220px] flex-1"><Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" /><input aria-label="Search finished goods" type="search" placeholder="Search finished goods..." value={query} onChange={event => { setQuery(event.target.value); resetList(); }} className={`${ENTRY_INPUT} pl-9`} /></div>
      <select aria-label="Brand" value={brand} onChange={event => { setBrand(event.target.value); resetList(); }} className={`${ENTRY_INPUT} !w-auto max-w-[220px]`}><option value="all">All brands</option>{brands.map(value => <option key={value}>{value}</option>)}</select>
      <select aria-label="Unit" value={unit} onChange={event => { setUnit(event.target.value); resetList(); }} className={`${ENTRY_INPUT} !w-auto`}><option value="all">All units</option>{units.map(value => <option key={value}>{value}</option>)}</select>
      {(tab === 'movements' || tab === 'report') && <><label>From<input aria-label="Movement start date" type="date" value={from} onChange={e => setFrom(e.target.value)} className={ENTRY_INPUT} /></label><label>To<input aria-label="Movement end date" type="date" value={to} onChange={e => setTo(e.target.value)} className={ENTRY_INPUT} /></label><select aria-label="Model filter" value={model} onChange={e => setModel(e.target.value)} className={ENTRY_INPUT}><option value="all">All models (includes unlinked stock)</option>{[...new Set(finishedMovements.map(m => m.modelName ?? findWorkItem(cards, m.manufacturingItemId ?? m.jobCardId ?? '')?.modelName).filter((name): name is string => !!name))].map(name => <option key={name}>{name}</option>)}</select></>}
      {(tab === 'movements' || tab === 'report') && <select aria-label="Movement type" value={movementType} onChange={event => { setMovementType(event.target.value); resetList(); }} className={`${ENTRY_INPUT} !w-auto`}><option value="all">IN and OUT</option><option value="IN">IN only</option><option value="OUT">OUT only</option></select>}
      {tab === 'report' && <label className="flex items-center gap-2 text-sm text-gray-500">Month<input aria-label="Report month" type="month" value={month} onChange={event => { if (event.target.value) setMonth(event.target.value); setExpanded(null); }} className={ENTRY_INPUT} /></label>}
    </div>
    <p className="text-xs text-gray-500">Packing retains the workbook’s packing stock groups in kg, separately from packed bag variants in cartons. Its May 2026 template has no recorded quantities. Carrier and Flat Bag movements are dated September, with two Flat Bag entries on October 1.</p>
    <div role="tabpanel" id={`stock-panel-${tab}`} aria-labelledby={`stock-tab-${tab}`} className="space-y-4">
      {tab === 'report' && <div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="font-semibold text-navy">Finished goods — {from && to ? `${from} to ${to}` : month}</h2><p className="mt-1 text-xs text-gray-500">Closing = Opening + Total IN − Total OUT. Expand a product for daily movements. IN/OUT filter narrows details; balance totals always include both.</p></div><div className="flex gap-2 print:hidden"><button type="button" onClick={exportReport} className={BUTTON}><Download size={16} />Export CSV</button><button type="button" onClick={() => { setLimit(products.length); requestAnimationFrame(() => window.print()); }} className={BUTTON}><Printer size={16} />Print report</button></div></div>}
      <div className="overflow-x-auto rounded-card border border-gray-200 bg-white">
        {tab === 'movements' ? <table className="w-full min-w-[900px] text-left text-sm">
          <thead className="border-b border-gray-200 bg-gray-50 text-xs text-gray-500"><tr>{['Date', 'Product / Variant', 'Category', 'Movement', 'Quantity', 'Unit', 'Reference', 'Customer / Destination'].map(label => <th key={label} scope="col" className={TH}>{label}</th>)}</tr></thead>
          <tbody className="divide-y divide-gray-100">{movements.slice(0, limit).map(movement => {
            const product = FINISHED_BY_ID.get(movement.productId)!;
            return <tr key={movement.id} className="hover:bg-gray-50"><td className={`${TD} whitespace-nowrap text-gray-500`}>{movement.date}</td><td className={TD}><ProductCell product={product} variant /></td><td className={TD}>{FINISHED_CATEGORY_LABEL[product.category]}</td><td className={TD}><span className={`rounded-full px-2.5 py-1 text-xs font-medium ${movement.type === 'IN' ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'}`}>{movement.type}</span></td><td className={`${TD} text-right tabular-nums`}>{fmt(movement.quantity)}</td><td className={TD}>{movement.unit}</td><td className={TD}>{movement.reference || '—'}{movement.salesOrderId && <Link className="ml-2 underline" to={`/sales-orders/${movement.salesOrderId}`}>Sales Order</Link>}{movement.jobCardId && <Link className="ml-2 underline" to={`/job-cards/${movement.jobCardId}`}>Job Card</Link>}{movement.batch && <p className="text-xs">{movement.batch}</p>}{movement.remarks && <p className="mt-1 text-xs text-gray-400">{movement.remarks}</p>}</td><td className={TD}>{movement.customer || '—'}</td></tr>;
          })}{!movements.length && <tr><td colSpan={8} className="p-10 text-center text-gray-500">No finished-goods movements match your filters.</td></tr>}</tbody>
        </table> : <table className="w-full min-w-[850px] text-left text-sm">
          <thead className="border-b border-gray-200 bg-gray-50 text-xs text-gray-500"><tr>{(tab === 'levels' ? ['Product / Item', 'Category', 'Size', 'Brand', 'Pieces', 'Packaging', 'Physical Stock', 'Reserved', 'Available', 'Unit', 'Status'] : ['Product / Variant', 'Category', 'Opening Stock', 'Total IN', 'Total OUT', 'Closing Stock', 'Unit', 'Details']).map(label => <th key={label} scope="col" className={TH}>{label}</th>)}</tr></thead>
          <tbody className="divide-y divide-gray-100">{products.slice(0, limit).map(product => {
            const row = tab === 'report' ? report.get(product.id)! : balances.get(product.id)!;
            const daily = finishedMovements.filter(movement => movement.productId === product.id && (from && to ? movement.date >= from && movement.date <= to : movement.date.startsWith(month)) && (movementType === 'all' || movement.type === movementType)).sort((a, b) => a.date.localeCompare(b.date) || a.id.localeCompare(b.id));
            return <Fragment key={product.id}>
              <tr className="hover:bg-gray-50"><td className={TD}><ProductCell product={product} variant={tab === 'report'} /></td><td className={`${TD} text-gray-500`}>{FINISHED_CATEGORY_LABEL[product.category]}</td>
                {tab === 'levels' ? <><td className={TD}>{product.size || '—'}</td><td className={TD}>{product.brand || '—'}</td><td className={TD}>{fmt(finishedPieces[product.id] ?? product.pieces ?? null)}</td><td className={TD}>{product.packingSize || '—'}</td></> : [row.openingStock, row.stockIn, row.stockOut].map((value, index) => <td key={index} className={`${TD} text-right tabular-nums text-gray-600`}>{fmt(value)}</td>)}
                <td className={`${TD} text-right font-semibold tabular-nums text-navy`}>{fmt(row.currentStock)}</td>{tab === 'levels' && <><td className={TD}>{fmt(reserved(ledger, product.id))}</td><td className={TD}>{fmt(row.currentStock === null ? null : row.currentStock - reserved(ledger, product.id))}</td></>}<td className={TD}>{product.unit}</td><td className={TD}>{tab === 'levels' ? <StockStatus quantity={row.currentStock} /> : <button type="button" aria-expanded={expanded === product.id} aria-controls={`daily-${product.id}`} aria-label={`Daily movements for ${finishedGoodLabel(product)}`} onClick={() => setExpanded(expanded === product.id ? null : product.id)} className="flex items-center gap-1 whitespace-nowrap text-xs font-medium text-navy hover:underline"><ChevronDown size={14} />Daily movements</button>}</td>
              </tr>
              {tab === 'report' && expanded === product.id && <tr><td colSpan={8} id={`daily-${product.id}`} className="bg-gray-50 p-4"><p className="mb-2 text-xs text-gray-500">Source: {product.sourceSheet}, row {product.sourceRow}. Reference opening: {product.openingDate}.</p>{daily.length ? <table aria-label={`Daily movements for ${finishedGoodLabel(product)}`} className="w-full text-left text-xs"><thead><tr>{['Date', 'Movement', 'Quantity', 'Unit', 'Reference', 'Customer / Destination'].map(label => <th scope="col" key={label} className="px-3 py-2 font-medium text-gray-500">{label}</th>)}</tr></thead><tbody>{daily.map(movement => <tr key={movement.id}><td className="px-3 py-2">{movement.date}</td><td className="px-3 py-2">{movement.type}</td><td className="px-3 py-2">{fmt(movement.quantity)}</td><td className="px-3 py-2">{movement.unit}</td><td className="px-3 py-2">{movement.reference || '—'}{movement.salesOrderId && <Link className="ml-2 underline" to={`/sales-orders/${movement.salesOrderId}`}>Sales Order</Link>}{movement.jobCardId && <Link className="ml-2 underline" to={`/job-cards/${movement.jobCardId}`}>Job Card</Link>}{movement.batch && <p className="text-xs">{movement.batch}</p>}</td><td className="px-3 py-2">{movement.customer || '—'}</td></tr>)}</tbody></table> : <p className="text-sm text-gray-500">No daily movements in this month.</p>}</td></tr>}
            </Fragment>;
          })}{!products.length && <tr><td colSpan={tab === 'levels' ? 11 : 8} className="p-10 text-center text-gray-500">No finished goods match your filters.</td></tr>}</tbody>
        </table>}
        <div className="flex items-center justify-between border-t border-gray-200 px-4 py-3 text-sm text-gray-500 print:hidden"><p aria-live="polite">Showing {Math.min(limit, count)} of {count}</p>{limit < count && <button type="button" onClick={() => setLimit(limit + 25)} className="font-medium text-navy hover:underline">Show more</button>}</div>
      </div>
    </div>
    <p className="text-xs text-gray-500">Frontend entries survive navigation and reset on refresh. Unrecorded opening balances remain unknown; sales orders do not deduct physical stock.</p>
    {direction && <InventoryMovementModal finishedGoods direction={direction} title="Finished Goods" categories={CATEGORIES} initialCategory={category === 'all' ? 'carrier-bags' : category}
      options={FINISHED_GOODS.map(product => ({ id: product.id, name: finishedGoodLabel(product), category: product.category, unit: product.unit, openingDate: product.openingDate, available: balances.get(product.id)!.currentStock === null ? null : balances.get(product.id)!.currentStock! - reserved(ledger, product.id),
        pieces: finishedPieces[product.id] ?? product.pieces, customer: product.customer,
        fields: [['Size', product.size || '—'], ['Brand', product.brand || '—'], ['Packaging', product.packingSize || '—'], ['Customer', product.customer || '—'], ['Opening Stock', fmt(balances.get(product.id)!.openingStock)], ['Stock IN', fmt(balances.get(product.id)!.stockIn)], ['Stock OUT', fmt(balances.get(product.id)!.stockOut)], ['Status', balances.get(product.id)!.currentStock === null ? 'Not recorded' : balances.get(product.id)!.currentStock! < 0 ? 'Negative balance' : balances.get(product.id)!.currentStock === 0 ? 'Out of stock' : 'In Stock']],
        detail: `${FINISHED_CATEGORY_LABEL[product.category]} · ${product.subgroup} · Source row ${product.sourceRow}` }))}
      onClose={() => setDirection(null)} onSave={entry => {
        const product = FINISHED_BY_ID.get(entry.materialId)!;
        addFinishedMovement({ productId: product.id, date: entry.date, type: direction, quantity: entry.quantity, unit: product.unit, reference: entry.reference, remarks: entry.remarks, customer: entry.customer });
        if (direction === 'IN' && entry.pieces !== undefined) updateFinishedPieces(product.id, entry.pieces);
        setNotice(`Stock ${direction} recorded: ${fmt(entry.quantity)} ${product.unit} · ${finishedGoodLabel(product)}.`);
      }} />}
  </div>;
}
