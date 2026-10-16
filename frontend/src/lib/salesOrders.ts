import { calculateConfiguredLED } from './led';
import { calculateCommercialTotals } from './commercialPricing';
import type { CustomerType, SalesOrder, SalesOrderItem } from '@/types';

export interface SalesOrderDraft extends Pick<SalesOrder, 'quotationId' | 'quotationRevisionId' | 'quotationNumber' | 'quotationRevision' | 'prospectId' | 'customerContact' | 'commercialTerms' | 'commercialPricing'> {
  taxRate?: number;
  currency?: string;
  customerId?: string;
  customerName: string;
  date: string;
  marketingPersonName: string;
  customerType: CustomerType | '';
  requisitionOrder: string;
  items: SalesOrderItem[];
}
export const today = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};
export const lineTotal = (quantity: number, price: number) => Math.round(quantity * price * 100) / 100;
export const orderTotal = (items: SalesOrderItem[]) => Math.round(items.reduce((sum, item) => sum + lineTotal(item.quantity, item.unitPrice), 0) * 100) / 100;
export function validateOrder(draft: SalesOrderDraft) {
  const errors: Record<string, string> = {};
  if (!draft.customerName.trim()) errors.customerName = 'Customer name is required.';
  if (!draft.marketingPersonName.trim()) errors.marketingPersonName = 'Marketing person is required.';
  if (!['B2B', 'B2C'].includes(draft.customerType)) errors.customerType = 'Select B2B or B2C.';
  if (!draft.date || !Number.isFinite(Date.parse(draft.date))) errors.date = 'A valid order date is required.';
  if (draft.taxRate !== undefined && (!Number.isFinite(draft.taxRate) || draft.taxRate < 0 || draft.taxRate > 100)) errors.taxRate = 'Tax rate must be between 0 and 100.';
  if (!draft.items.length) errors.items = 'Add at least one item.';
  if (!draft.currency?.trim()) errors.currency = 'Enter the transaction currency.';
  if (draft.taxRate === undefined) errors.taxRate = 'Confirm the transaction tax rate (0 for no tax).';
  draft.items.forEach((item, i) => {
    if (!['stock', 'manufacturing'].includes(item.fulfillmentSource ?? '')) errors[`${i}.source`] = 'Select a fulfillment source.';
    if ((!item.itemId && !(item.fulfillmentSource === 'manufacturing' && item.modelId)) || !item.itemName.trim()) errors[`${i}.item`] = 'Select an item.';
    if (item.modelId && (!item.requiredDate || !Number.isFinite(Date.parse(item.requiredDate)) || item.requiredDate < draft.date)) errors[`${i}.item`] = 'Enter a required delivery date on or after the order date.';
    if(item.led?.applies){try{const expected=calculateConfiguredLED(item.led,item.quantity*item.unitPrice,undefined,draft.currency??'');if(JSON.stringify(expected)!==JSON.stringify(item.ledSnapshot)||item.ledSnapshot?.conversion?.originalQuantity!==item.quantity||item.ledSnapshot?.conversion?.originalUnit!==item.unit||item.ledSnapshot?.conversion?.productId!==(item.itemId??''))throw new Error();}catch{errors[`${i}.led`]='LED MAX needs valid weight/conversion, FX and a refreshed snapshot.';}}
    if (!Number.isFinite(item.quantity) || item.quantity <= 0) errors[`${i}.quantity`] = 'Quantity must be greater than 0.';
    if (!item.unit.trim()) errors[`${i}.unit`] = 'Select a unit.';
    if (!Number.isFinite(item.unitPrice) || item.unitPrice < 0) errors[`${i}.price`] = 'Price must be 0 or greater.';
    if (Number.isFinite(item.quantity) && Number.isFinite(item.unitPrice) && !Number.isFinite(lineTotal(item.quantity, item.unitPrice))) errors[`${i}.price`] = 'The line total is too large.';
  });
  if (draft.commercialPricing) { try { calculateCommercialTotals(draft.items, draft.commercialPricing.discount, draft.taxRate ?? 0, draft.commercialPricing.taxMode); } catch { errors.items = 'Invalid commercial tax/discount snapshot.'; } }
  if (draft.items.every(item => Number.isFinite(item.quantity) && Number.isFinite(item.unitPrice)) && !Number.isFinite(orderTotal(draft.items))) errors.items = 'The order total is too large.';
  return errors;
}
export const nextOrderNumber = (existing: SalesOrder[]) => `SO-${Math.max(0, ...existing.map(order => Number(order.orderNumber.replace(/^SO-/, '')) || 0)) + 1}`;
export const orderSummary = (items: SalesOrderItem[]) => { const subtotal = orderTotal(items.filter(item => Number.isFinite(item.quantity) && Number.isFinite(item.unitPrice))); return { subtotal, total: subtotal }; };
// Future: backend may export/sync Sales Orders with Tally.
export function buildSalesOrder(draft: SalesOrderDraft, existing: SalesOrder[]): SalesOrder {
  if (Object.keys(validateOrder(draft)).length) throw new Error('Please correct the highlighted fields.');
  return {
    ...draft, id: `so-${crypto.randomUUID()}`, orderNumber: nextOrderNumber(existing),
    customerName: draft.customerName.trim(), marketingPersonName: draft.marketingPersonName.trim(),
    requisitionOrder: draft.requisitionOrder.trim(), customerType: draft.customerType as CustomerType,
    items: draft.items.map(item => ({ ...item, totalPrice: lineTotal(item.quantity, item.unitPrice) })),
    commercialPricing:draft.commercialPricing??(draft.items.some(i=>i.ledSnapshot)?{taxMode:'exclusive',discount:0,roundingPolicy:'LED and VAT rounded to 2 decimals; frozen per-line MAX snapshots.'}:undefined),
    orderTotal: draft.commercialPricing ? calculateCommercialTotals(draft.items, draft.commercialPricing.discount, draft.taxRate ?? 0, draft.commercialPricing.taxMode).total : draft.items.some(i=>i.ledSnapshot)?calculateCommercialTotals(draft.items,0,draft.taxRate??0,'exclusive').total:lineTotal(orderTotal(draft.items), 1 + (draft.taxRate ?? 0) / 100), status: 'Draft', jobCardIds: [],
  };
}

