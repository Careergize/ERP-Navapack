import { useEffect, useRef, useState, type FormEvent } from 'react';
import { X } from 'lucide-react';
import { ENTRY_INPUT, SearchSelect } from './SearchSelect';

export interface InventoryOption { id: string; name: string; category: string; unit: string; available: number | null; openingDate?: string; detail?: string; fields?: [string, string][]; pieces?: number | null; customer?: string }
export interface InventoryEntry { movementPurpose?: 'transfer' | 'waste' | 'adjustment'; date: string; materialId: string; quantity: number; reference: string; remarks: string; customer?: string; pieces?: number }
const today = () => new Date().toLocaleDateString('en-CA');
export function InventoryMovementModal({ direction, title, options, categories, initialCategory, onClose, onSave, finishedGoods = false }: {
  direction: 'IN' | 'OUT'; title: string; options: InventoryOption[]; categories: [string, string][];
  initialCategory: string; onClose: () => void; onSave: (entry: InventoryEntry) => void; finishedGoods?: boolean;
}) {
  const [category, setCategory] = useState(initialCategory);
  const [name, setName] = useState('');
  const [materialId, setMaterialId] = useState('');
  const [date, setDate] = useState(today);
  const [quantity, setQuantity] = useState('');
  const [reference, setReference] = useState('');
  const [remarks, setRemarks] = useState('');
  const [movementPurpose,setMovementPurpose]=useState<'transfer'|'waste'|'adjustment'>('transfer');
  const [customer, setCustomer] = useState('');
  const [pieces, setPieces] = useState('');
  const [error, setError] = useState('');
  const dialog = useRef<HTMLDivElement>(null);
  const close = useRef(onClose);
  close.current = onClose;
  const locked = useRef(false);
  const selected = options.find(option => option.id === materialId);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    dialog.current?.querySelector<HTMLInputElement>('input')?.focus();
    const keydown = (event: KeyboardEvent) => {
      if (event.defaultPrevented) return;
      if (event.key === 'Escape') { event.preventDefault(); close.current(); }
      if (event.key === 'Tab') {
        const elements = Array.from(dialog.current?.querySelectorAll<HTMLElement>('button, input, select, textarea') ?? []);
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
    if (locked.current) return;
    if (!selected || !date || !Number.isFinite(Number(quantity)) || Number(quantity) <= 0) {
      setError(`Select a ${finishedGoods ? 'product' : 'material'}, a date and a quantity greater than zero.`); return;
    }
    if (selected.openingDate && date < selected.openingDate) { setError(`The reference ledger begins on ${selected.openingDate}. Choose that date or later.`); return; }
    if (finishedGoods && direction === 'IN' && pieces !== '' && (!Number.isSafeInteger(Number(pieces)) || Number(pieces) <= 0)) { setError('Pieces must be a positive whole number or left unrecorded.'); return; }
    locked.current = true;
    onSave({ movementPurpose: finishedGoods && direction==='OUT' ? movementPurpose : undefined, date, materialId, quantity: Number(quantity), reference: reference.trim(), remarks: remarks.trim(), ...(finishedGoods ? { customer: customer.trim(), ...(direction === 'IN' && pieces !== '' ? { pieces: Number(pieces) } : {}) } : {}) });
    onClose();
  };
  return <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/35 p-4" onMouseDown={event => { if (event.target === event.currentTarget) onClose(); }}>
    <div ref={dialog} role="dialog" aria-modal="true" aria-labelledby="inventory-dialog-title" className="max-h-[90vh] w-full max-w-xl overflow-y-auto rounded-card bg-white shadow-xl">
      <div className="flex items-center justify-between border-b border-gray-200 p-5"><h2 id="inventory-dialog-title" className="text-lg font-semibold text-navy">{title} — Stock {direction}</h2><button type="button" aria-label="Close" onClick={onClose}><X size={20} /></button></div>
      <form onSubmit={submit} className="space-y-4 p-5">
        <p className="text-xs text-gray-500">Frontend simulation. Entries survive navigation and reset on refresh.</p>
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="text-sm text-gray-600">Date<input type="date" required value={date} min={selected?.openingDate} onChange={event => setDate(event.target.value)} className={`${ENTRY_INPUT} mt-1`} /></label>
          <label className="text-sm text-gray-600">{finishedGoods ? 'Category' : 'Material Category'}<select value={category} onChange={event => { setCategory(event.target.value); setMaterialId(''); setName(''); setPieces(''); setCustomer(''); }} className={`${ENTRY_INPUT} mt-1`}>{categories.map(([id, label]) => <option key={id} value={id}>{label}</option>)}</select></label>
        </div>
        <div><label htmlFor="inventory-material" className="mb-1 block text-sm text-gray-600">{finishedGoods ? 'Product / Variant' : 'Material / Grade'}</label><SearchSelect inputId="inventory-material" label={finishedGoods ? 'Product / Variant' : 'Material / Grade'} value={name} options={options.filter(option => option.category === category).map(option => ({ ...option, detail: option.detail ?? option.unit }))} onChange={value => { setName(value); setMaterialId(''); setPieces(''); setCustomer(''); }} onSelect={option => { const record = options.find(item => item.id === option.id)!; setName(option.name); setMaterialId(option.id); setPieces(record.pieces == null ? '' : String(record.pieces)); setCustomer(record.customer ?? ''); }} /></div>
        {selected?.fields && <div className="grid gap-3 rounded-card bg-gray-50 p-3 sm:grid-cols-2">{selected.fields.map(([label, value]) => <label key={label} className="text-sm text-gray-600">{label}<input readOnly value={value} className={`${ENTRY_INPUT} mt-1 bg-gray-50`} /></label>)}</div>}
        {finishedGoods && <div><label className="block text-sm text-gray-600">Pieces<input type="number" min="1" step="1" readOnly={direction === 'OUT'} disabled={!selected} value={pieces} placeholder="Not recorded" onChange={event => setPieces(event.target.value)} className={`${ENTRY_INPUT} mt-1`} /></label><p className="mt-1 text-xs text-gray-500">Pieces per package, when applicable. Stock quantity remains in the selected unit.</p></div>}
        {selected && <p className="text-sm text-gray-500">{finishedGoods ? 'Current Stock' : 'Available'}: {selected.available === null ? 'Not recorded' : `${selected.available.toLocaleString('en-IN', { maximumFractionDigits: 2 })} ${selected.unit}`}</p>}
        {direction === 'OUT' && selected?.available != null && Number(quantity) > selected.available && <p role="status" className="text-xs text-amber-700">Quantity exceeds the recorded balance. This simulation allows the entry.</p>}
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="text-sm text-gray-600">Quantity<input type="number" required min="0.000001" step="any" value={quantity} onChange={event => setQuantity(event.target.value)} className={`${ENTRY_INPUT} mt-1`} /></label>
          <label className="text-sm text-gray-600">Unit<input readOnly value={selected?.unit ?? ''} className={`${ENTRY_INPUT} mt-1 bg-gray-50`} /></label>
        </div>
        {finishedGoods && direction === 'OUT' && <label className="block text-sm text-gray-600">Customer / Destination<input value={customer} onChange={event => setCustomer(event.target.value)} className={`${ENTRY_INPUT} mt-1`} /></label>}
        {finishedGoods&&direction==='OUT'&&<label className="block text-sm">Non-sales Stock OUT purpose<select className={ENTRY_INPUT} value={movementPurpose} onChange={e=>setMovementPurpose(e.target.value as typeof movementPurpose)}><option value="transfer">Transfer</option><option value="waste">Waste</option><option value="adjustment">Approved adjustment (Admin confirmation)</option></select><span className="text-xs">Customer sales must use confirmed Sales Order dispatch. Adjustments require Admin approval, reference and reason.</span></label>}
        <label className="block text-sm text-gray-600">Reference<input value={reference} onChange={event => setReference(event.target.value)} className={`${ENTRY_INPUT} mt-1`} /></label>
        <label className="block text-sm text-gray-600">Remarks<textarea value={remarks} onChange={event => setRemarks(event.target.value)} className={`${ENTRY_INPUT} mt-1`} /></label>
        {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
        <div className="flex justify-end gap-2"><button type="button" onClick={onClose} className="rounded-card border border-gray-200 px-4 py-2 text-sm">Cancel</button><button type="submit" className="rounded-card bg-navy px-4 py-2 text-sm font-medium text-white">Save Stock {direction}</button></div>
      </form>
    </div>
  </div>;
}
