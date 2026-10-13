import { useCommercial } from '@/context/CommercialContext';
import { useNavigate } from 'react-router-dom';
import { useModels } from '@/context/ModelsContext';
import { ModelManager } from '@/pages/Masters/ModelManager';
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react';
import { Plus, Trash2, X } from 'lucide-react';
import { MOCK_USERS } from '@/lib/mockData';
import { FINISHED_GOODS, FINISHED_BY_ID, FINISHED_CATEGORY_LABEL, findFinishedGood, finishedBalance, finishedGoodLabel } from '@/lib/finishedGoodsData';
import { reserved } from '@/lib/fulfillment';
import { useInventory } from '@/context/InventoryContext';
import { lineTotal, nextOrderNumber, orderSummary, today, validateOrder, type SalesOrderDraft } from '@/lib/salesOrders';
import { useSalesOrders } from '@/context/SalesOrdersContext';
import { ENTRY_INPUT, SearchSelect } from '@/components/ui/SearchSelect';
import type { SalesOrderItem } from '@/types';

const newItem = (): SalesOrderItem => ({ id: crypto.randomUUID(), itemName: '', quantity: NaN, unit: '', unitPrice: NaN, totalPrice: 0 });
const untouched = (item: SalesOrderItem) => !item.itemName && !item.itemId && !item.unit && Number.isNaN(item.quantity) && Number.isNaN(item.unitPrice);
const money = (value: number) => `${(Number.isFinite(value) ? value : 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
export function NewSalesOrderModal({ onClose, onCreated }: { onClose: () => void; onCreated: (number: string) => void }) {
  const navigate = useNavigate();
  const { customers: customerMaster } = useCommercial();
  const { models } = useModels();
  const [showModels, setShowModels] = useState(false);
  const { orders, createSalesOrder } = useSalesOrders();
  const { finishedMovements, ledger } = useInventory();
  const getAvailableStock = (itemId: string | undefined, name: string, unit: string) => {
    const product = findFinishedGood(itemId, name, unit);
    return product && product.unit === unit ? (finishedBalance(product, finishedMovements).currentStock === null ? undefined : finishedBalance(product, finishedMovements).currentStock! - reserved(ledger, product.id)) : undefined;
  };
  const [draft, setDraft] = useState<SalesOrderDraft>(() => ({ customerName: '', date: today(), marketingPersonName: '', customerType: '', requisitionOrder: '', items: [newItem()] }));
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [attempted, setAttempted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const locked = useRef(false);
  const dialog = useRef<HTMLDivElement>(null);
  const close = useRef(onClose);
  close.current = onClose;
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    dialog.current?.querySelector<HTMLInputElement>('#order-customer')?.focus();
    const keydown = (event: globalThis.KeyboardEvent) => {
      if (event.defaultPrevented) return;
      if (event.key === 'Escape') { event.preventDefault(); close.current(); }
      if (event.key === 'Tab') {
        const elements = Array.from(dialog.current?.querySelectorAll<HTMLElement>('button:not(:disabled), input:not([readonly]), select, textarea') ?? []);
        const first = elements[0], last = elements[elements.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
      }
    };
    document.addEventListener('keydown', keydown);
    return () => { document.body.style.overflow = overflow; document.removeEventListener('keydown', keydown); previous?.focus(); };
  }, []);
  const focus = (id: string) => dialog.current?.querySelector<HTMLElement>(`[id="${id}"]`)?.focus();
  const advance = (event: KeyboardEvent, id: string) => { if (event.key === 'Enter') { event.preventDefault(); focus(id); } };
  const updateItem = (id: string, change: Partial<SalesOrderItem>) => setDraft(current => ({ ...current, items: current.items.map(item => item.id === id ? { ...item, ...change } : item) }));
  const addItem = () => {
    const item = newItem();
    setDraft(current => ({ ...current, items: [...current.items, item] }));
    requestAnimationFrame(() => focus(`item-${item.id}`));
  };
  const nextItem = (index: number) => {
    if (draft.items[index + 1]) focus(`item-${draft.items[index + 1].id}`);
    else if (!untouched(draft.items[index])) addItem();
  };
  const effective = { ...draft, items: draft.items.filter(item => !untouched(item)) };
  const liveErrors = attempted ? validateOrder(effective) : {};
  const errorFor = (item: SalesOrderItem, field: string) => liveErrors[`${effective.items.findIndex(value => value.id === item.id)}.${field}`];
  const summary = orderSummary(effective.items);
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (locked.current) return;
    setAttempted(true);
    if (Object.keys(validateOrder(effective)).length) return;
    locked.current = true; setSubmitting(true);
    try { const order = createSalesOrder(effective); onCreated(order.orderNumber); if ((event.nativeEvent as SubmitEvent).submitter?.getAttribute('value') === 'costing') { const item = order.items?.find(i => i.fulfillmentSource === 'manufacturing'); if (item) navigate(`/costing?orderId=${order.id}&itemId=${item.id}`); } }
    catch (error) { setErrors({ form: error instanceof Error ? error.message : 'Unable to create order.' }); locked.current = false; setSubmitting(false); }
  };
  const customers = customerMaster.map(c => ({ id: c.id, name: c.name }));
  const staff = MOCK_USERS.map(user => ({ id: user.id, name: user.name, detail: user.role.replaceAll('_', ' ') }));
  const items = FINISHED_GOODS.map(item => { const available = getAvailableStock(item.id, finishedGoodLabel(item), item.unit); return { id: item.id, name: finishedGoodLabel(item), detail: `${FINISHED_CATEGORY_LABEL[item.category]} · Source row ${item.sourceRow} · ${available === undefined ? 'Stock not recorded' : `Available: ${available.toLocaleString('en-IN')} ${item.unit}`}` }; });
  const error = (text?: string) => text && <p role="alert" className="mt-1 text-xs text-red-600">{text}</p>;
  return <div className="fixed inset-0 z-50 flex items-center justify-center bg-navy/30 p-2 sm:p-4" role="dialog" aria-modal="true" aria-labelledby="new-order-title">
    <div ref={dialog} className="max-h-[95vh] w-full max-w-6xl overflow-y-auto rounded-card bg-white p-4 shadow-xl sm:p-6">
      <div className="flex items-center justify-between"><div><h2 id="new-order-title" className="text-lg font-semibold text-navy">New Sales Order</h2><p className="mt-1 text-xs text-gray-500">Search to select · Tab to move · Enter on Rate for the next item</p></div><button type="button" onClick={onClose} aria-label="Close" className="rounded-full p-1 text-gray-400 hover:bg-gray-100"><X size={18} /></button></div>
      {showModels && <div className="mt-4"><ModelManager onSaved={() => setShowModels(false)} /><button type="button" onClick={() => setShowModels(false)}>Close model editor</button></div>}
      <form onSubmit={submit} noValidate className="mt-5 space-y-5">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <label className="text-sm text-gray-600">Order No<input aria-label="Order No" readOnly tabIndex={-1} value={nextOrderNumber(orders)} className={`${ENTRY_INPUT} mt-1 bg-gray-50`} /></label>
          <label className="text-sm text-gray-600">Date<input aria-label="Date" type="date" readOnly tabIndex={-1} value={draft.date} className={`${ENTRY_INPUT} mt-1 bg-gray-50`} /></label>
          <div className="text-sm text-gray-600"><label htmlFor="order-customer" className="mb-1 block">Customer *</label><SearchSelect label="Customer" inputId="order-customer" value={draft.customerName} options={customers} error={liveErrors.customerName} onChange={value => setDraft({ ...draft, customerName: value, customerId: undefined })} onSelect={option => setDraft({ ...draft, customerName: option.name, customerId: option.id })} onAdvance={() => focus('order-marketing')} /></div>
          <div className="text-sm text-gray-600"><label htmlFor="order-marketing" className="mb-1 block">Marketing Person *</label><SearchSelect label="Marketing Person" inputId="order-marketing" value={draft.marketingPersonName} options={staff} error={liveErrors.marketingPersonName} onChange={value => setDraft({ ...draft, marketingPersonName: value })} onSelect={option => setDraft({ ...draft, marketingPersonName: option.name })} onAdvance={() => focus('customer-type-B2B')} /></div>
          <fieldset><legend className="mb-1 text-sm text-gray-600">Customer Type *</legend><div className="flex gap-2">{(['B2B', 'B2C'] as const).map(type => <label key={type} className={`flex cursor-pointer items-center gap-2 rounded-card border px-4 py-2 text-sm ${draft.customerType === type ? 'border-navy bg-navy/5 text-navy' : 'border-gray-200 text-gray-600'}`}><input id={`customer-type-${type}`} type="radio" name="customer-type" value={type} checked={draft.customerType === type} onChange={() => setDraft({ ...draft, customerType: type })} onKeyDown={event => advance(event, 'order-requisition')} />{type}</label>)}</div>{error(liveErrors.customerType)}</fieldset>
          <label className="text-sm text-gray-600">Requisition Order<input id="order-requisition" value={draft.requisitionOrder} onChange={event => setDraft({ ...draft, requisitionOrder: event.target.value })} onKeyDown={event => advance(event, `item-${draft.items[0].id}`)} className={`${ENTRY_INPUT} mt-1`} /></label>
        </div>
        <div className="flex gap-4"><label>Currency<input aria-label="Transaction currency" required value={draft.currency ?? ''} onChange={e => setDraft({ ...draft, currency: e.target.value.toUpperCase() })} className={ENTRY_INPUT} />{error(liveErrors.currency)}</label><label>Applicable Tax / VAT % (confirm transaction treatment)<input aria-label="Transaction tax rate" required type="number" min="0" max="100" step="any" value={draft.taxRate ?? ''} onChange={e => setDraft({ ...draft, taxRate: e.target.valueAsNumber })} className={ENTRY_INPUT} />{error(liveErrors.taxRate)}</label></div>
        <section aria-label="Order items" className="rounded-card border border-gray-200">
          <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3"><h3 className="font-medium text-navy">Items</h3><span className="text-xs text-gray-500">{effective.items.length} item(s)</span></div>
          <div className="overflow-x-auto"><table className="w-full min-w-[850px] text-left text-sm"><thead className="bg-gray-50 text-xs text-gray-500"><tr>{['Item', 'Fulfillment Source', 'Quantity', 'Unit', 'Rate', 'Amount', 'Action'].map(label => <th key={label} scope="col" className="px-3 py-3 font-medium">{label}</th>)}</tr></thead>
            <tbody className="divide-y divide-gray-100">{draft.items.map((item, i) => { const available = getAvailableStock(item.itemId, item.itemName, item.unit); return <tr key={item.id} className="align-top">
              <td className="w-[35%] px-3 py-3">{item.fulfillmentSource === 'manufacturing' && !item.itemId ? <input id={`item-${item.id}`} aria-label={`Custom product ${i + 1}`} value={item.itemName} onChange={e => updateItem(item.id, { itemName: e.target.value })} className={ENTRY_INPUT} /> : <SearchSelect inputId={`item-${item.id}`} label={`Item ${i + 1}`} value={item.itemName} options={items} error={errorFor(item, 'item')} onChange={value => updateItem(item.id, { itemName: value, itemId: undefined, unit: '' })} onSelect={option => { const selected = FINISHED_BY_ID.get(option.id)!; updateItem(item.id, { itemId: selected.id, itemName: finishedGoodLabel(selected), unit: selected.unit }); }} onAdvance={() => focus(`quantity-${item.id}`)} />}{item.fulfillmentSource === 'manufacturing' && <div className="mt-3 space-y-2"><label>Existing Product Model<select aria-label={`Product model ${i + 1}`} value={item.modelId ?? ''} onChange={e => { const model = models.find(m => m.id === e.target.value); updateItem(item.id, { modelId: model?.id, modelRevision: model?.revision, specifications: model?.specifications ?? '', unit: item.itemId ? item.unit : model?.defaultUnit ?? item.unit, itemName: item.itemId ? item.itemName : model?.description || model?.name || '' }); }} className={ENTRY_INPUT}><option value="">Select model</option>{models.map(m => <option key={m.id} value={m.id}>{m.name} · Revision {m.revision}</option>)}</select></label><button type="button" onClick={() => setShowModels(true)} className="text-xs text-navy underline">Create New Custom Model</button><label>Specifications<textarea aria-label={`Specifications ${i + 1}`} value={item.specifications ?? ''} onChange={e => updateItem(item.id, { specifications: e.target.value })} className={ENTRY_INPUT} /></label><label>Required Delivery Date<input type="date" value={item.requiredDate ?? ''} onChange={e => updateItem(item.id, { requiredDate: e.target.value })} className={ENTRY_INPUT} /></label><p className="text-xs text-gray-500">Open Costing / Estimate and create a linked draft Job Card from this line after saving the order.</p></div>}{available !== undefined && <p className="mt-1 text-xs text-gray-500">Available: {available.toLocaleString('en-IN')} {item.unit}</p>}{available !== undefined && item.quantity > available && <p role="status" className="mt-1 text-xs text-amber-700">Requested quantity exceeds currently available stock.</p>}</td>
              <td className="px-3 py-3"><select required aria-label={`Fulfillment source ${i + 1}`} value={item.fulfillmentSource ?? ''} onChange={e => updateItem(item.id, { fulfillmentSource: e.target.value as SalesOrderItem['fulfillmentSource'] })} className={ENTRY_INPUT}><option value="">Select source</option><option value="stock">Existing Finished Goods Stock</option><option value="manufacturing">Customized Product / Manufacture</option></select>{error(errorFor(item, 'source'))}</td>
              <td className="px-3 py-3"><input id={`quantity-${item.id}`} aria-label={`Quantity ${i + 1}`} type="number" step="any" min="0" value={Number.isNaN(item.quantity) ? '' : item.quantity} onChange={event => updateItem(item.id, { quantity: event.target.valueAsNumber })} onKeyDown={event => advance(event, `rate-${item.id}`)} className={`${ENTRY_INPUT} min-w-[100px]`} />{error(errorFor(item, 'quantity'))}</td>
              <td className="px-3 py-3"><select aria-label={`Unit ${i + 1}`} value={item.unit} onChange={event => updateItem(item.id, { unit: event.target.value })} className={ENTRY_INPUT}><option value="">Select</option>{[...new Set([...FINISHED_GOODS.map(value => value.unit), ...models.map(m => m.defaultUnit).filter((unit): unit is string => !!unit), 'pcs'])].map(unit => <option key={unit}>{unit}</option>)}</select>{error(errorFor(item, 'unit'))}</td>
              <td className="px-3 py-3"><input id={`rate-${item.id}`} aria-label={`Rate ${i + 1}`} type="number" min="0" step="0.01" value={Number.isNaN(item.unitPrice) ? '' : item.unitPrice} onChange={event => updateItem(item.id, { unitPrice: event.target.valueAsNumber })} onKeyDown={event => { if (event.key === 'Enter') { event.preventDefault(); nextItem(i); } }} className={`${ENTRY_INPUT} min-w-[100px]`} />{error(errorFor(item, 'price'))}</td>
              <td className="whitespace-nowrap px-3 py-5 font-medium tabular-nums text-navy"><output aria-label={`Amount ${i + 1}`} aria-live="polite">{money(lineTotal(item.quantity, item.unitPrice))}</output></td>
              <td className="px-3 py-3"><button type="button" disabled={draft.items.length === 1} aria-label={`Remove Item ${i + 1}`} onClick={() => setDraft({ ...draft, items: draft.items.filter(value => value.id !== item.id) })} className="rounded-card p-2 text-gray-400 hover:bg-red-50 hover:text-red-600 disabled:opacity-30"><Trash2 size={16} /></button></td>
            </tr>; })}</tbody>
          </table></div>
        </section>
        <div className="flex flex-col justify-between gap-4 sm:flex-row"><div><button type="button" onClick={addItem} className="inline-flex items-center gap-1 rounded-card border border-gray-200 px-3 py-2 text-sm text-navy"><Plus size={16} /> Add Item</button>{error(liveErrors.items)}</div><dl className="w-full space-y-3 rounded-card bg-gray-50 p-4 sm:w-72"><div className="flex justify-between text-sm text-gray-600"><dt>Subtotal</dt><dd>{money(summary.subtotal)}</dd></div><div className="flex justify-between border-t border-gray-200 pt-3 font-semibold text-navy"><dt>Order Total</dt><dd><output aria-live="polite">{`${draft.currency ?? ""} ${(summary.total * (1 + (draft.taxRate ?? 0) / 100)).toFixed(2)}`}</output></dd></div></dl></div>
        {error(errors.form)}
        <div className="flex justify-end gap-2 border-t border-gray-200 pt-4"><button type="button" onClick={onClose} className="rounded-card border border-gray-200 px-4 py-2 text-sm text-gray-600">Cancel</button><button type="submit" disabled={submitting} className="rounded-card bg-navy px-4 py-2 text-sm font-medium text-white disabled:opacity-50">{submitting ? 'Creating…' : 'Create Order'}</button>{effective.items.some(i => i.fulfillmentSource === 'manufacturing') && <button type="submit" value="costing" disabled={submitting} className="rounded-card border border-navy px-4 py-2 text-sm text-navy">Save &amp; Open Costing / Estimate</button>}</div>
      </form>
    </div>
  </div>;
}
