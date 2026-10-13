import { FINISHED_BY_ID, finishedBalance, type FinishedGoodsMovement } from './finishedGoodsData';
import type { SalesOrder, SalesOrderItem, JobCard } from '../types';
export interface Allocation { id: string; orderId: string; itemId: string; productId: string; batch: string; quantity: number; dispatched: number; released: boolean }
export interface Dispatch { modelId?: string; modelName?: string; id: string; number: string; allocationId: string; orderId: string; itemId: string; productId: string; batch: string; quantity: number; unit: string; date: string; challan: string; destination: string; vehicle: string; remarks: string; status: 'Confirmed' | 'Cancelled' }
export interface FulfillmentLedger { movements: FinishedGoodsMovement[]; allocations: Allocation[]; dispatches: Dispatch[] }
const round = (value: number) => Math.round(value * 1e6) / 1e6;
const check = (ok: unknown, message: string) => { if (!ok) throw new Error(message); };
export const reserved = (state: FulfillmentLedger, productId: string, batch?: string) => round(state.allocations.filter(a => !a.released && a.productId === productId && (batch === undefined || a.batch === batch)).reduce((sum, a) => sum + a.quantity - a.dispatched, 0));
export function physical(state: FulfillmentLedger, productId: string) { const product = FINISHED_BY_ID.get(productId); return product ? finishedBalance(product, state.movements).currentStock : null; }
export function batchPhysical(state: FulfillmentLedger, productId: string, batch: string) {
  if (batch === 'reference-stock') { const product = FINISHED_BY_ID.get(productId); return product ? finishedBalance(product, state.movements.filter(m => !m.batch || m.batch === batch)).currentStock : null; }
  return state.movements.filter(m => m.productId === productId && m.batch === batch).reduce((sum, m) => sum + (m.type === 'IN' ? m.quantity : -m.quantity), 0);
}
export function allocate(state: FulfillmentLedger, order: SalesOrder, item: SalesOrderItem, quantity: number, batch: string, requestId: string = crypto.randomUUID()): FulfillmentLedger {
  if (state.allocations.some(a => a.id === requestId)) return state;
  const product = FINISHED_BY_ID.get(item.itemId ?? '');
  check(product && product.unit === item.unit && !['Completed', 'Cancelled'].includes(order.status) && order.items?.some(i => i.id === item.id && i.itemId === item.itemId) && !!item.fulfillmentSource, 'Select a valid product with the order unit.');
  check(Number.isFinite(quantity) && quantity > 0 && batch, 'Enter a positive quantity and select a batch.');
  const balance = physical(state, product!.id), batchBalance = batchPhysical(state, product!.id, batch);
  check(balance !== null && batchBalance !== null && quantity <= balance - reserved(state, product!.id) && quantity <= batchBalance - reserved(state, product!.id, batch), 'Allocation exceeds known unreserved stock.');
  const committed = state.allocations.filter(a => a.orderId === order.id && a.itemId === item.id).reduce((sum, a) => sum + (a.released ? a.dispatched : a.quantity), 0);
  check(quantity <= item.quantity - committed, 'Allocation exceeds the unallocated order balance.');
  return { ...state, allocations: [...state.allocations, { id: requestId, orderId: order.id, itemId: item.id, productId: product!.id, batch, quantity, dispatched: 0, released: false }] };
}
export function confirmDispatch(state: FulfillmentLedger, draft: Omit<Dispatch, 'status' | 'number' | 'orderId' | 'itemId' | 'productId' | 'batch' | 'unit'>): FulfillmentLedger {
  if (state.dispatches.some(d => d.id === draft.id)) return state;
  check(draft.id, 'Dispatch request identifier is required.');
  const a = state.allocations.find(a => a.id === draft.allocationId);
  check(a && !a.released, 'Select an active allocation.');
  const balance = physical(state, a!.productId), batchBalance = batchPhysical(state, a!.productId, a!.batch);
  check(Number.isFinite(draft.quantity) && draft.quantity > 0 && draft.quantity <= a!.quantity - a!.dispatched && balance !== null && balance >= draft.quantity && batchBalance !== null && batchBalance >= draft.quantity, 'Dispatch exceeds allocated or physical stock.');
  check(/^\d{4}-\d{2}-\d{2}$/.test(draft.date) && Number.isFinite(Date.parse(draft.date)), 'Choose a valid dispatch date.');
  const product = FINISHED_BY_ID.get(a!.productId)!;
  const batchReceipts = state.movements.filter(m => m.productId === a!.productId && m.batch === a!.batch && m.type === 'IN');
  check(a!.batch === 'reference-stock' || batchReceipts.some(m => m.date <= draft.date), 'Dispatch cannot precede batch receipt.');
  const datedBalance = finishedBalance(product, state.movements.filter(m => m.date <= draft.date)).currentStock;
  const datedBatch = batchPhysical({ ...state, movements: state.movements.filter(m => m.date <= draft.date) }, a!.productId, a!.batch);
  check(datedBalance !== null && datedBalance >= draft.quantity && datedBatch !== null && datedBatch >= draft.quantity, 'Stock was unavailable on the selected dispatch date.');
  const laterDates = [...new Set(state.movements.filter(m => m.productId === product.id && m.date > draft.date).map(m => m.date))];
  check(laterDates.every(date => (finishedBalance(product, state.movements.filter(m => m.date <= date)).currentStock ?? 0) >= draft.quantity && (batchPhysical({ ...state, movements: state.movements.filter(m => m.date <= date) }, product.id, a!.batch) ?? 0) >= draft.quantity), 'Backdated dispatch would make a later historical balance negative.');
  check(draft.date >= product.openingDate && draft.destination.trim() && draft.challan.trim(), 'Date must follow opening; destination and delivery note are required.');
  const dispatch: Dispatch = { ...draft, modelId: batchReceipts[0]?.modelId, modelName: batchReceipts[0]?.modelName, number: `DSP-${state.dispatches.length + 1}`, orderId: a!.orderId, itemId: a!.itemId, productId: a!.productId, batch: a!.batch, unit: product.unit, status: 'Confirmed' };
  return { movements: [...state.movements, { id: `out-${draft.id}`, type: 'OUT', productId: a!.productId, quantity: draft.quantity, unit: product.unit, date: draft.date, salesOrderId: a!.orderId, salesOrderItemId: a!.itemId, dispatchId: draft.id, batch: a!.batch, reference: dispatch.number, remarks: draft.remarks }], allocations: state.allocations.map(row => row.id === a!.id ? { ...row, dispatched: round(row.dispatched + draft.quantity) } : row), dispatches: [...state.dispatches, dispatch] };
}
export function reverseDispatch(state: FulfillmentLedger, id: string, date: string, reason: string): FulfillmentLedger {
  const d = state.dispatches.find(d => d.id === id);
  check(d && reason.trim() && /^\d{4}-\d{2}-\d{2}$/.test(date) && Number.isFinite(Date.parse(date)) && date >= d.date, 'Record a reversal date and reason.');
  if (d!.status === 'Cancelled') return state;
  return { ...state, movements: [...state.movements, { id: `reverse-${id}`, productId: d!.productId, quantity: d!.quantity, unit: d!.unit, date, type: 'IN', batch: d!.batch, salesOrderId: d!.orderId, salesOrderItemId: d!.itemId, dispatchId: id, reversalOf: `out-${id}`, reference: `Reversal ${d!.number}`, remarks: reason }], allocations: state.allocations.map(a => a.id === d!.allocationId ? { ...a, dispatched: round(a.dispatched - d!.quantity) } : a), dispatches: state.dispatches.map(row => row.id === id ? { ...row, status: 'Cancelled' } : row) };
}

export function orderFulfillmentStatus(order: SalesOrder, state: FulfillmentLedger, cards: JobCard[]): SalesOrder['status'] {
  if (order.status === 'Cancelled' || !order.items?.length) return order.status;
  const dispatched = (itemId: string) => state.dispatches.filter(d => d.orderId === order.id && d.itemId === itemId && d.status === 'Confirmed').reduce((sum, d) => sum + d.quantity, 0);
  if (order.items.every(i => dispatched(i.id) >= i.quantity)) return 'Dispatched';
  if (order.items.some(i => dispatched(i.id) > 0)) return 'Partially Dispatched';
  if (state.allocations.some(a => a.orderId === order.id && !a.released && a.quantity > a.dispatched)) return 'Reserved';
  if (state.movements.some(m => m.salesOrderId === order.id && m.jobCardId && m.type === 'IN')) return 'Stock Received';
  const jobs = cards.filter(c => c.salesOrderId === order.id).flatMap(c => c.manufacturingItems ?? [c]);
  if (jobs.some(j => j.status === 'ReadyForStock')) return 'Ready for Stock';
  if (jobs.some(j => ['MaterialIssued', 'InProduction', 'OnHold'].includes(j.status))) return 'In Production';
  if (jobs.some(j => j.approval)) return 'Approved';
  return 'Draft';
}
