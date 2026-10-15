import { calculateCommercialTotals } from './commercialPricing';
import type { SalesOrder } from '../types';
import type { Dispatch } from './fulfillment';
export interface Invoice { led?: number; taxMode?: 'inclusive' | 'exclusive'; quotationDiscount?: number; roundingAdjustment?: number; id: string; number: string; orderId: string; orderNumber: string; date: string; dispatchIds: string[]; dispatchNumbers?: string[]; seller: string; sellerAddress: string; sellerTax: string; email: string; contact: string; buyer: string; billingAddress: string; deliveryAddress: string; buyerTax: string; po: string; paymentTerms: string; destination: string; challans: string; currency: string; discount: number; taxRate: number; subtotal: number; tax: number; total: number; fiscalNumber?: string; verificationCode?: string; items: { itemId: string; description: string; quantity: number; unit: string; rate: number; amount: number; ledSnapshot?: import('./led').LEDSnapshot }[] }
export type InvoiceDraft = Omit<Invoice, 'id' | 'orderId' | 'orderNumber' | 'buyer' | 'po' | 'challans' | 'items' | 'subtotal' | 'tax' | 'total'>;
const money = (value: number) => Math.round(value * 100) / 100;
export function createInvoice(draft: InvoiceDraft, order: SalesOrder, dispatches: Dispatch[], existing: Invoice[]): Invoice {
  if (!draft.number.trim() || existing.some(i => i.number === draft.number) || !draft.seller.trim() || !draft.currency.trim() || !draft.billingAddress.trim() || !draft.date || !Number.isFinite(Date.parse(draft.date))) throw new Error('Complete unique invoice number, seller, currency, date and billing address.');
  if (!Number.isFinite(draft.taxRate) || draft.taxRate < 0 || draft.taxRate > 100 || !Number.isFinite(draft.discount) || draft.discount < 0) throw new Error('Invalid tax rate or discount.');
  if (order.currency && draft.currency !== order.currency) throw new Error('Invoice currency must match the order; currency conversion is not configured.');
  const selected = dispatches.filter(d => draft.dispatchIds.includes(d.id));
  if (!selected.length || selected.length !== new Set(draft.dispatchIds).size || selected.some(d => d.orderId !== order.id || d.status !== 'Confirmed' || d.date > draft.date || existing.some(i => i.dispatchIds.includes(d.id)))) throw new Error('Select confirmed, uninvoiced dispatches dated on or before the invoice.');
  const items = (order.items ?? []).flatMap(item => { const quantity = selected.filter(d => d.itemId === item.id).reduce((sum, d) => sum + d.quantity, 0); return quantity ? [{ itemId: item.id, description: item.itemName, quantity, unit: item.unit, rate: item.unitPrice, amount: money(quantity * item.unitPrice),ledSnapshot:item.ledSnapshot?{...structuredClone(item.ledSnapshot),baseAmount:item.ledSnapshot.baseAmount*quantity/item.quantity,selectedUnrounded:item.ledSnapshot.selectedUnrounded*quantity/item.quantity,selectedAmount:money(item.ledSnapshot.selectedAmount*quantity/item.quantity),percentageAmount:money(item.ledSnapshot.percentageAmount*quantity/item.quantity),weightAmount:money(item.ledSnapshot.weightAmount*quantity/item.quantity),eligibleWeightKG:item.ledSnapshot.eligibleWeightKG*quantity/item.quantity}:undefined }] : []; });
  const subtotal = money(items.reduce((sum, i) => sum + i.amount, 0));
  if (draft.discount > subtotal) throw new Error('Discount exceeds subtotal.');
  let led:number|undefined;
  let discount = draft.discount, taxMode = 'exclusive' as 'inclusive' | 'exclusive', quotationDiscount: number | undefined, roundingAdjustment: number | undefined;
  let tax = money((subtotal - discount) * draft.taxRate / 100), total = money(subtotal - discount + tax);
  if (order.commercialPricing) {
    if (draft.taxRate !== order.taxRate || draft.discount !== 0) throw new Error('Quoted VAT is frozen and the accepted discount is apportioned automatically. Additional invoice adjustments need a separate authorized workflow.');
    taxMode = order.commercialPricing.taxMode;
    const full = calculateCommercialTotals(order.items ?? [], order.commercialPricing.discount, order.taxRate ?? 0, taxMode);
    const prior = existing.filter(i => i.orderId === order.id);
    const fullyInvoiced = (order.items ?? []).every(item => { const billed = prior.reduce((sum, invoice) => sum + invoice.items.filter(i => i.itemId === item.id).reduce((s, i) => s + i.quantity, 0), 0) + items.filter(i => i.itemId === item.id).reduce((sum, i) => sum + i.quantity, 0); return Math.abs(billed - item.quantity) <= Number.EPSILON * Math.max(1, item.quantity) * 8; });
    const alreadyDiscounted = prior.reduce((sum, i) => sum + (i.quotationDiscount ?? 0), 0);
    quotationDiscount = fullyInvoiced ? money(full.discount - alreadyDiscounted) : Math.min(money(full.discount * (full.subtotal ? subtotal / full.subtotal : 0)), money(full.discount - alreadyDiscounted));
    discount = quotationDiscount;
    const calculated = calculateCommercialTotals(items.map(i => ({ quantity: i.quantity, unitPrice: i.rate,ledSnapshot:i.ledSnapshot })), discount, draft.taxRate, taxMode);
    tax = calculated.tax; total = calculated.total; led=calculated.led;
    if (fullyInvoiced) {
      const reconciled = money(full.total - prior.reduce((sum, i) => sum + i.total, 0));
      if(full.led!==undefined)led=money(full.led-prior.reduce((n,i)=>n+(i.led??0),0));
      roundingAdjustment = money(reconciled - total); total = reconciled;
      tax = money(full.tax - prior.reduce((sum, i) => sum + i.tax, 0));
    }
  }
  if (![subtotal, tax, total].every(Number.isFinite)) throw new Error('Invoice amounts exceed the supported range.');
  return { ...draft, led, discount, taxMode, quotationDiscount, roundingAdjustment, id: crypto.randomUUID(), orderId: order.id, orderNumber: order.orderNumber, buyer: order.customerName, dispatchNumbers: selected.map(d => d.number), po: order.requisitionOrder ?? '', challans: selected.map(d => d.challan).join(', '), items, subtotal, tax, total };
}
export function amountInWords(amount: number, currency: string) {
  const ones = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen'];
  const tens = ['', '', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety'];
  const words = (n: number): string => n < 20 ? ones[n] : n < 100 ? tens[Math.floor(n / 10)] + (n % 10 ? ` ${ones[n % 10]}` : '') : n < 1000 ? `${ones[Math.floor(n / 100)]} hundred${n % 100 ? ` ${words(n % 100)}` : ''}` : [...[[1e12, 'trillion'], [1e9, 'billion'], [1e6, 'million'], [1000, 'thousand']] as [number, string][]].filter(([v]) => n >= v).slice(0, 1).map(([v, label]) => `${words(Math.floor(n / v))} ${label}${n % v ? ` ${words(n % v)}` : ''}`).join('');
  if (amount >= 1e15) return 'Amount exceeds supported words range';
  const cents = Math.round(amount * 100); return `${currency} ${words(Math.floor(cents / 100))} and ${String(cents % 100).padStart(2, '0')}/100 only`;
}
