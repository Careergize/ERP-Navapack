import type { JobCard, SalesOrder } from '../types';

// Mixed-order assumption: only manually selected manufacturing lines require work.
export const manufacturingLines = (order: SalesOrder) => (order.items ?? []).filter(i => i.fulfillmentSource === 'manufacturing');
export const workItems = (card: JobCard): JobCard[] => card.manufacturingItems ?? [card];
export const findWorkItem = (cards: JobCard[], id: string) => cards.flatMap(workItems).find(i => i.id === id);
export const parentForItem = (cards: JobCard[], id: string) => cards.find(c => c.id === id || c.manufacturingItems?.some(i => i.id === id));

export function summarizeParent(parent: JobCard, items: JobCard[]): JobCard {
  if (!items.length || items.some(i => i.manufacturingItems || i.parentJobCardId !== parent.id || i.salesOrderId !== parent.salesOrderId || !i.salesOrderItemId) || new Set(items.map(i => i.id)).size !== items.length || new Set(items.map(i => i.salesOrderItemId)).size !== items.length) throw new Error('Parent manufacturing items must have distinct stable item and order-line references.');
  const status = items.every(i => i.status === 'Completed') ? 'Completed'
    : items.some(i => i.status === 'Draft' || i.status === 'PendingApproval') ? 'PendingApproval'
    : items.some(i => i.status === 'OnHold') ? 'OnHold'
    : items.every(i => ['ReadyForStock', 'Completed'].includes(i.status)) ? 'ReadyForStock'
    : items.some(i => i.status === 'InProduction' || i.status === 'Completed' || i.status === 'ReadyForStock') ? 'InProduction'
    : items.some(i => i.status === 'MaterialIssued' || i.status === 'Issued') ? 'MaterialIssued' : 'StoreIssuePending';
  const events = items.flatMap(i => (i.activityHistory ?? []).map(e => ({ ...e, jobCardId: parent.id, manufacturingItemId: i.id })));
  const ownEvents = (parent.activityHistory ?? []).filter(e => !e.manufacturingItemId);
  return { ...parent, manufacturingItems: items, status, department: 'See manufacturing items',
    requiredDate: items.map(i => i.requiredDate).filter((d): d is string => !!d).sort()[0],
    activityHistory: [...ownEvents, ...events].sort((a, b) => a.timestamp.localeCompare(b.timestamp)) };
}

export function attachManufacturingItem(cards: JobCard[], order: SalesOrder, item: JobCard): { parent: JobCard; item: JobCard } {
  if (!manufacturingLines(order).some(line => line.id === item.salesOrderItemId)) throw new Error('Only manufacturing lines belong in a parent Job Card.');
  const linked = cards.filter(c => c.salesOrderId === order.id);
  if (linked.some(c => !c.manufacturingItems) || linked.length > 1) throw new Error('Historical Job Cards are preserved. An authorized migration of existing references is required before adding manufacturing items.');
  const existing = linked[0];
  const duplicate = existing?.manufacturingItems?.find(i => i.salesOrderItemId === item.salesOrderItemId);
  if (duplicate) return { parent: existing!, item: duplicate };
  if (existing?.manufacturingItems?.some(i => i.approval || !['Draft', 'PendingApproval'].includes(i.status))) throw new Error('Manufacturing items cannot be added after approval. Request an authorized order amendment.');
  const parent: JobCard = existing ?? { id: crypto.randomUUID(), jobCardNumber: item.jobCardNumber,
    origin: 'sales_order', salesOrderId: order.id, salesOrderNumber: order.orderNumber, customerName: order.customerName,
    modelName: 'Multiple manufacturing items', qty: 0, status: 'PendingApproval', department: 'Production Manager', stages: [],
    createdDate: item.createdDate, activityHistory: [] };
  const child = { ...item, parentJobCardId: parent.id, origin: 'sales_order' as const, jobCardNumber: parent.jobCardNumber };
  return { parent: summarizeParent(parent, [...(existing?.manufacturingItems ?? []), child]), item: child };
}

export function assertCompleteManufacturingScope(parent: JobCard, order?: SalesOrder) {
  if (!parent.manufacturingItems) return;
  if (!order || manufacturingLines(order).length !== parent.manufacturingItems.length || manufacturingLines(order).some(line => !parent.manufacturingItems!.some(i => i.salesOrderItemId === line.id && i.qty === line.quantity && i.unit === line.unit))) throw new Error('Prepare every manufacturing line with its ordered quantity and unit before approving the parent Job Card.');
}
