import { useEffect, useRef, useState, type FormEvent } from 'react';
import { ArrowDownToLine, ArrowUpFromLine, Plus, Search, X } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { ENTRY_INPUT } from '@/components/ui/SearchSelect';
import { InventoryMovementModal } from '@/components/ui/InventoryMovementModal';
import { useConsumables } from '@/context/ConsumablesContext';
import { CONSUMABLE_CATEGORIES, CONSUMABLE_UNITS, consumableBalance, type Consumable } from '@/lib/consumableData';

const button = 'flex items-center gap-2 rounded-card border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus-visible:ring-2 focus-visible:ring-navy';
const fmt = (value: number) => value.toLocaleString('en-IN', { maximumFractionDigits: 2 });
const categories: [string, string][] = CONSUMABLE_CATEGORIES.map(([id, label]) => [id, label]);
const categoryLabel = (item: Consumable) => categories.find(([id]) => id === item.category)![1];
const statusLabel = (item: Consumable, quantity: number) => quantity < 0 ? 'Negative balance' : quantity === 0 ? 'Out of stock' : item.minLevel !== undefined && quantity < item.minLevel ? 'Below minimum' : 'In Stock';

function ConsumableForm({ item, readOnly, posted, onClose, onSave }: { item: Consumable; readOnly: boolean; posted: boolean; onClose: () => void; onSave: (item: Consumable) => void }) {
  const [draft, setDraft] = useState(item);
  const [openingStock, setOpeningStock] = useState(String(item.openingStock));
  const [error, setError] = useState('');
  const dialog = useRef<HTMLDivElement>(null);
  const close = useRef(onClose); close.current = onClose;
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    dialog.current?.querySelector<HTMLElement>('button')?.focus();
    const keydown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { event.preventDefault(); close.current(); }
      if (event.key === 'Tab') {
        const elements = Array.from(dialog.current?.querySelectorAll<HTMLElement>('button, input:not(:disabled), select:not(:disabled)') ?? []);
        const first = elements[0], last = elements[elements.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
      }
    };
    document.addEventListener('keydown', keydown);
    return () => { document.body.style.overflow = overflow; document.removeEventListener('keydown', keydown); previous?.focus(); };
  }, []);
  const submit = (event: FormEvent) => {
    event.preventDefault();
    try { onSave({ ...draft, openingStock: Number(openingStock) }); onClose(); } catch (error) { setError(error instanceof Error ? error.message : 'Unable to save consumable'); }
  };
  return <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/35 p-4" onMouseDown={event => { if (event.target === event.currentTarget) onClose(); }}>
    <div ref={dialog} role="dialog" aria-modal="true" aria-labelledby="consumable-title" className="max-h-[90vh] w-full max-w-xl overflow-y-auto rounded-card bg-white shadow-xl">
      <div className="flex items-center justify-between border-b border-gray-200 p-5"><h2 id="consumable-title" className="text-lg font-semibold text-navy">{readOnly ? 'View' : 'Add / Edit'} Consumable</h2><button type="button" aria-label="Close" onClick={onClose}><X size={20} /></button></div>
      <form onSubmit={submit} className="space-y-4 p-5">
        <label className="block text-sm text-gray-600">Name<input required readOnly={readOnly} value={draft.name} onChange={e => setDraft({ ...draft, name: e.target.value })} className={`${ENTRY_INPUT} mt-1`} /></label>
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="text-sm text-gray-600">Category<select disabled={readOnly} value={draft.category} onChange={e => setDraft({ ...draft, category: e.target.value as Consumable['category'] })} className={`${ENTRY_INPUT} mt-1`}>{categories.map(([id, label]) => <option key={id} value={id}>{label}</option>)}</select></label>
          <label className="text-sm text-gray-600">Unit<select disabled={readOnly || posted} value={draft.unit} onChange={e => setDraft({ ...draft, unit: e.target.value as Consumable['unit'] })} className={`${ENTRY_INPUT} mt-1`}>{CONSUMABLE_UNITS.map(unit => <option key={unit}>{unit}</option>)}</select></label>
          <label className="text-sm text-gray-600">Opening Stock<input required type="number" min="0" step="any" readOnly={readOnly || posted} value={openingStock} onChange={e => setOpeningStock(e.target.value)} className={`${ENTRY_INPUT} mt-1`} /></label>
          <label className="text-sm text-gray-600">Opening Date<input required type="date" readOnly={readOnly || posted} value={draft.openingDate} onChange={e => setDraft({ ...draft, openingDate: e.target.value })} className={`${ENTRY_INPUT} mt-1`} /></label>
          <label className="text-sm text-gray-600">Minimum Level<input type="number" min="0" step="any" readOnly={readOnly} value={draft.minLevel ?? ''} onChange={e => setDraft({ ...draft, minLevel: e.target.value === '' ? undefined : Number(e.target.value) })} className={`${ENTRY_INPUT} mt-1`} /></label>
        </div>
        {posted && <p className="text-xs text-gray-500">Unit and opening balance are locked after stock movements have been recorded.</p>}
        {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
        <div className="flex justify-end gap-2"><button type="button" className={button} onClick={onClose}>{readOnly ? 'Close' : 'Cancel'}</button>{!readOnly && <button type="submit" className="rounded-card bg-navy px-4 py-2 text-sm font-medium text-white">Save Consumable</button>}</div>
      </form>
    </div>
  </div>;
}

export function ConsumablesPage() {
  const { items, movements, saveItem, addMovement } = useConsumables();
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('all');
  const [unit, setUnit] = useState('all');
  const [view, setView] = useState<'levels' | 'movements'>('levels');
  const [editing, setEditing] = useState<{ item: Consumable; readOnly: boolean } | null>(null);
  const [direction, setDirection] = useState<'IN' | 'OUT' | null>(null);
  const [notice, setNotice] = useState('');
  const filtered = items.filter(item => item.name.toLowerCase().includes(query.trim().toLowerCase()) && (category === 'all' || item.category === category) && (unit === 'all' || item.unit === unit));
  const ids = new Set(filtered.map(item => item.id));
  const ledger = movements.filter(m => ids.has(m.materialId)).sort((a, b) => b.date.localeCompare(a.date));
  return <div className="space-y-6">
    <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"><div><h1 className="text-2xl font-semibold text-navy">Consumables</h1><p className="mt-1 text-sm text-gray-500">Imported and local spares, stock levels and movements.</p></div><div className="flex flex-wrap gap-2"><button className={button} onClick={() => setEditing({ item: { id: crypto.randomUUID(), name: '', category: 'imported', unit: 'Each', openingStock: 0, openingDate: new Date().toLocaleDateString('en-CA') }, readOnly: false })}><Plus size={16} />Add Consumable</button><button className={button} onClick={() => setDirection('IN')}><ArrowDownToLine size={16} />Stock IN</button><button className={button} onClick={() => setDirection('OUT')}><ArrowUpFromLine size={16} />Stock OUT</button></div></header>
    <section className="grid grid-cols-2 gap-4 lg:grid-cols-4" aria-label="Consumables summary">{[['Consumables', items.length], ['Imported Spare', items.filter(item => item.category === 'imported').length], ['Local Spare', items.filter(item => item.category === 'local').length], ['Below Minimum', items.filter(item => item.minLevel !== undefined && consumableBalance(item, movements).currentStock < item.minLevel).length]].map(([label, value]) => <Card key={label}><p className="text-sm text-gray-500">{label}</p><p className="mt-1 text-2xl font-semibold text-navy">{value}</p></Card>)}</section>
    {notice && <p role="status" className="rounded-card bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{notice}</p>}
    <div role="tablist" aria-label="Consumables views" className="flex gap-6 border-b border-gray-200">{(['levels', 'movements'] as const).map(id => <button key={id} role="tab" aria-selected={view === id} aria-controls={`consumables-${id}`} id={`consumables-tab-${id}`} onClick={() => setView(id)} className={`-mb-px border-b-2 pb-3 text-sm font-medium ${view === id ? 'border-navy text-navy' : 'border-transparent text-gray-500'}`}>{id === 'levels' ? 'Stock Levels' : 'Movements'}</button>)}</div>
    <div className="flex flex-wrap gap-3"><div className="relative min-w-[220px] flex-1"><Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" /><input aria-label="Search consumables" type="search" value={query} onChange={e => setQuery(e.target.value)} placeholder="Search consumables" className={`${ENTRY_INPUT} pl-9`} /></div><select aria-label="Consumable category filter" value={category} onChange={e => setCategory(e.target.value)} className={`${ENTRY_INPUT} !w-auto`}><option value="all">All categories</option>{categories.map(([id, label]) => <option key={id} value={id}>{label}</option>)}</select><select aria-label="Consumable unit filter" value={unit} onChange={e => setUnit(e.target.value)} className={`${ENTRY_INPUT} !w-auto`}><option value="all">All units</option>{CONSUMABLE_UNITS.map(value => <option key={value}>{value}</option>)}</select><button className={button} onClick={() => { setQuery(''); setCategory('all'); setUnit('all'); }}>Clear filters</button></div>
    <div role="tabpanel" id={`consumables-${view}`} aria-labelledby={`consumables-tab-${view}`} className="overflow-x-auto rounded-card border border-gray-200 bg-white"><table className="w-full min-w-[900px] text-left text-sm"><thead className="border-b border-gray-200 bg-gray-50 text-xs text-gray-500"><tr>{(view === 'levels' ? ['Name', 'Category', 'Opening Stock', 'Stock IN', 'Stock OUT', 'Current Stock', 'Unit', 'Status', 'Actions'] : ['Date', 'Name', 'Category', 'Type', 'Quantity', 'Unit', 'Reference', 'Remarks']).map(label => <th scope="col" key={label} className="px-4 py-3 font-medium">{label}</th>)}</tr></thead><tbody className="divide-y divide-gray-100">
      {view === 'levels' ? filtered.map(item => { const balance = consumableBalance(item, movements); return <tr key={item.id} className="hover:bg-gray-50"><td className="px-4 py-3 font-medium text-gray-900">{item.name}</td><td className="px-4 py-3">{categoryLabel(item)}</td>{[item.openingStock, balance.stockIn, balance.stockOut, balance.currentStock].map((value, index) => <td key={index} className="px-4 py-3 tabular-nums">{fmt(value)}</td>)}<td className="px-4 py-3">{item.unit}</td><td className="px-4 py-3">{statusLabel(item, balance.currentStock)}</td><td className="px-4 py-3"><div className="flex gap-3"><button className="text-navy hover:underline" aria-label={`View ${item.name}`} onClick={() => setEditing({ item, readOnly: true })}>View</button><button className="text-navy hover:underline" aria-label={`Edit ${item.name}`} onClick={() => setEditing({ item, readOnly: false })}>Edit</button></div></td></tr>; }) : ledger.map(m => { const item = items.find(item => item.id === m.materialId)!; return <tr key={m.id} className="hover:bg-gray-50">{[m.date, item.name, categoryLabel(item), m.type, fmt(m.quantity), item.unit, m.reference || '—', m.remarks || '—'].map((value, index) => <td key={index} className="px-4 py-3">{value}</td>)}</tr>; })}
      {!(view === 'levels' ? filtered.length : ledger.length) && <tr><td colSpan={view === 'levels' ? 9 : 8} className="p-10 text-center text-gray-500">{items.length ? 'No records match your filters.' : 'No consumables yet. Add a consumable to begin tracking stock.'}</td></tr>}
    </tbody></table></div>
    <p className="text-xs text-gray-500">Frontend entries survive navigation and reset on refresh. Quantities are tracked separately in each item's unit.</p>
    {editing && <ConsumableForm item={editing.item} readOnly={editing.readOnly} posted={movements.some(m => m.materialId === editing.item.id)} onClose={() => setEditing(null)} onSave={item => { saveItem(item); setNotice(`Consumable saved: ${item.name.trim()}.`); }} />}
    {direction && <InventoryMovementModal title="Consumables" direction={direction} categories={categories} initialCategory={category === 'all' ? 'imported' : category} options={items.map(item => ({ ...item, available: consumableBalance(item, movements).currentStock, fields: [['Opening Stock', fmt(item.openingStock)], ['Stock IN', fmt(consumableBalance(item, movements).stockIn)], ['Stock OUT', fmt(consumableBalance(item, movements).stockOut)], ['Status', statusLabel(item, consumableBalance(item, movements).currentStock)]] }))} onClose={() => setDirection(null)} onSave={entry => { addMovement({ materialId: entry.materialId, date: entry.date, type: direction, quantity: entry.quantity, reference: entry.reference, remarks: entry.remarks }); setNotice(`Stock ${direction} recorded for ${items.find(item => item.id === entry.materialId)!.name}.`); }} />}
  </div>;
}
