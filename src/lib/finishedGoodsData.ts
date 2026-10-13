import { FINISHED_GOODS_REFERENCE, FINISHED_MOVEMENTS_REFERENCE } from './finishedGoodsReference';

export type FinishedCategory = 'carrier-bags' | 'flat-bags' | 'packing';
export const FINISHED_CATEGORY_LABEL: Record<FinishedCategory, string> = {
  'carrier-bags': 'Carrier Bags', 'flat-bags': 'Flat Bags', packing: 'Packing',
};
export interface FinishedGood {
  id: string;
  category: FinishedCategory;
  subgroup: string;
  customer: string;
  itemDetails: string;
  size: string;
  brand: string;
  packingSize: string;
  pieces?: number | null; // Optional pieces per package; never converts ledger quantities.
  unit: string;
  openingStock: number | null;
  openingDate: string;
  sourceSheet: string;
  sourceRow: number;
  sourceCustomer: string;
  customerInherited: boolean;
  sourceUnit: string;
  sourceClosingStock: number | null;
  dataNotes: string[];
}
export interface FinishedGoodsMovement {
  id: string;
  productId: string;
  date: string;
  type: 'IN' | 'OUT';
  quantity: number;
  unit: string;
  customer?: string;
  reference?: string;
  remarks?: string;
  salesOrderId?: string;
  salesOrderItemId?: string;
  jobCardId?: string;
  manufacturingItemId?: string;
  qualityReleaseId?: string;
  stockApprovalId?: string;
  modelId?: string;
  modelName?: string;
  batch?: string;
  dispatchId?: string;
  reversalOf?: string;
}
// TODO: Replace finished-goods mock data with backend inventory API.
export const FINISHED_GOODS = FINISHED_GOODS_REFERENCE;
export const FINISHED_MOVEMENTS = FINISHED_MOVEMENTS_REFERENCE;
export const FINISHED_BY_ID = new Map(FINISHED_GOODS.map(product => [product.id, product]));
const round = (value: number) => Math.round(value * 1e6) / 1e6;
export const finishedGoodName = (product: FinishedGood) => product.itemDetails || product.subgroup;
// Full identity stays visible wherever a variant is selected or referenced.
export const finishedGoodLabel = (product: FinishedGood) =>
  [finishedGoodName(product), product.size, product.brand, product.packingSize, product.customer, product.unit,
    product.dataNotes.some(note => note.startsWith('Repeated variant')) ? `Source row ${product.sourceRow}` : ''].filter(Boolean).join(' · ');
export function matchesFinishedGood(product: FinishedGood, query: string) {
  const text = [product.itemDetails, product.size, product.brand, product.packingSize, product.customer, product.subgroup, product.id].join(' ').toLowerCase();
  const normalize = (value: string) => value.toLowerCase().replace(/\s+/g, '');
  return query.trim().toLowerCase().split(/\s+/).every(word => text.includes(word)) || normalize(text).includes(normalize(query));
}
export function finishedBalance(product: FinishedGood, movements: FinishedGoodsMovement[], month?: string) {
  const ledger = movements.filter(movement => movement.productId === product.id);
  const inMonth = month ? ledger.filter(movement => movement.date.startsWith(month)) : ledger;
  const stockIn = round(inMonth.filter(movement => movement.type === 'IN').reduce((sum, movement) => sum + movement.quantity, 0));
  const stockOut = round(inMonth.filter(movement => movement.type === 'OUT').reduce((sum, movement) => sum + movement.quantity, 0));
  if (product.openingStock === null || (month && `${month}-01` < product.openingDate)) {
    return { openingStock: null, stockIn, stockOut, currentStock: null };
  }
  const openingStock = round(product.openingStock + (month ? ledger.filter(movement => movement.date < `${month}-01`)
    .reduce((sum, movement) => sum + (movement.type === 'IN' ? movement.quantity : -movement.quantity), 0) : 0));
  return { openingStock, stockIn, stockOut, currentStock: round(openingStock + stockIn - stockOut) };
}
export function findFinishedGood(itemId: string | undefined, name: string, unit: string) {
  const byId = itemId ? FINISHED_BY_ID.get(itemId) : undefined;
  if (byId) return byId;
  const normalize = (value: string) => value.toLowerCase().replace(/\s+/g, '');
  const matches = FINISHED_GOODS.filter(product => product.unit === unit &&
    (normalize(finishedGoodLabel(product)) === normalize(name) || normalize(product.itemDetails) === normalize(name)));
  // Never silently choose between different brands, customers or packing sizes.
  return matches.length === 1 ? matches[0] : undefined;
}

export function finishedRangeBalance(product: FinishedGood, movements: FinishedGoodsMovement[], from: string, to: string) {
  const ledger = movements.filter(m => m.productId === product.id && m.unit === product.unit);
  const inRange = ledger.filter(m => m.date >= from && m.date <= to);
  const stockIn = round(inRange.filter(m => m.type === 'IN').reduce((sum, m) => sum + m.quantity, 0));
  const stockOut = round(inRange.filter(m => m.type === 'OUT').reduce((sum, m) => sum + m.quantity, 0));
  if (!from || !to || to < from || product.openingStock === null || from < product.openingDate) return { openingStock: null, stockIn, stockOut, currentStock: null };
  const openingStock = round(product.openingStock + ledger.filter(m => m.date < from).reduce((sum, m) => sum + (m.type === 'IN' ? m.quantity : -m.quantity), 0));
  return { openingStock, stockIn, stockOut, currentStock: round(openingStock + stockIn - stockOut) };
}
