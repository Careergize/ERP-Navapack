export const CONSUMABLE_CATEGORIES = [['imported', 'Imported Spare'], ['local', 'Local Spare']] as const;
export const CONSUMABLE_UNITS = ['Each', 'Both', 'Litres', 'Kilos'] as const;
export interface Consumable {
  id: string;
  name: string;
  category: typeof CONSUMABLE_CATEGORIES[number][0];
  unit: typeof CONSUMABLE_UNITS[number];
  openingStock: number;
  openingDate: string;
  minLevel?: number;
}
export interface ConsumableMovement {
  id: string;
  materialId: string;
  date: string;
  type: 'IN' | 'OUT';
  quantity: number;
  reference: string;
  remarks: string;
}
export function consumableBalance(item: Consumable, movements: ConsumableMovement[]) {
  const ledger = movements.filter(m => m.materialId === item.id);
  const round = (value: number) => Math.round(value * 1e6) / 1e6;
  const stockIn = round(ledger.filter(m => m.type === 'IN').reduce((sum, m) => sum + m.quantity, 0));
  const stockOut = round(ledger.filter(m => m.type === 'OUT').reduce((sum, m) => sum + m.quantity, 0));
  return { stockIn, stockOut, currentStock: round(item.openingStock + stockIn - stockOut) };
}
