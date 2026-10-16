import { ITEMS, MOVEMENTS } from './stockData';
import { REFERENCE_MATERIALS, REFERENCE_MOVEMENTS } from './rawMaterialReference';

export type RawCategory = 'virgin' | 'recycled' | 'ink';
export const RAW_CATEGORY_LABEL: Record<RawCategory, string> = {
  virgin: 'Virgin Material', recycled: 'Recycled Granules', ink: 'Ink',
};
export interface RawMaterial {
  id: string;
  name: string;
  family: string;
  category: RawCategory;
  unit: string;
  openingStock: number | null;
  openingDate: string;
  minLevel?: number;
  sourceRow?: number;
  sourceClosingStock?: number | null;
}
export interface RawMaterialMovement {
  id: string;
  date: string;
  materialId: string;
  materialName: string;
  category: RawCategory;
  movementType: 'IN' | 'OUT';
  quantity: number;
  unit: string;
  reference: string;
  remarks: string;
}
// Keep the existing granule demo ledger, distinct from the company's grade records.
const granules = Object.entries(ITEMS).filter(([, item]) => item.category === 'granules');
export const RAW_MATERIALS: RawMaterial[] = [
  ...REFERENCE_MATERIALS,
  ...granules.map(([name, item]) => ({ id: `legacy-${name}`, name, family: 'Existing demo granules',
    category: 'recycled' as const, unit: item.unit, openingStock: 0, openingDate: '2026-07-01', minLevel: item.minLevel })),
];
export const RAW_MOVEMENTS: RawMaterialMovement[] = [
  ...REFERENCE_MOVEMENTS,
  ...MOVEMENTS.filter(m => m.category === 'granules').map(m => ({ id: `legacy-${m.id}`, date: m.date,
    materialId: `legacy-${m.item}`, materialName: m.item, category: 'recycled' as const,
    movementType: m.type === 'in' ? 'IN' as const : 'OUT' as const, quantity: m.qty,
    unit: ITEMS[m.item].unit, reference: m.ref, remarks: m.party })),
];
const round = (n: number) => Math.round(n * 1e6) / 1e6;
// A missing source opening balance stays unknown until a real master supplies it.
// Known movement totals remain visible, without implying an unknown balance is zero.
export function rawMaterialBalance(material: RawMaterial, movements: RawMaterialMovement[], month?: string) {
  const ledger = movements.filter(m => m.materialId === material.id);
  const applicable = month ? ledger.filter(m => m.date.startsWith(month)) : ledger;
  const stockIn = round(applicable.filter(m => m.movementType === 'IN').reduce((sum, m) => sum + m.quantity, 0));
  const stockOut = round(applicable.filter(m => m.movementType === 'OUT').reduce((sum, m) => sum + m.quantity, 0));
  if (material.openingStock === null || (month && `${month}-01` < material.openingDate)) {
    return { openingStock: null, stockIn, stockOut, currentStock: null };
  }
  const openingStock = round(material.openingStock + (month ? ledger.filter(m => m.date < `${month}-01`)
    .reduce((sum, m) => sum + (m.movementType === 'IN' ? m.quantity : -m.quantity), 0) : 0));
  return { openingStock, stockIn, stockOut, currentStock: round(openingStock + stockIn - stockOut) };
}
