import { createContext, useContext, useState, type ReactNode } from 'react';
import { CONSUMABLE_CATEGORIES, CONSUMABLE_UNITS, type Consumable, type ConsumableMovement } from '@/lib/consumableData';

interface ConsumablesState {
  items: Consumable[];
  movements: ConsumableMovement[];
  saveItem: (item: Consumable) => void;
  addMovement: (movement: Omit<ConsumableMovement, 'id'>) => void;
}
const Context = createContext<ConsumablesState | undefined>(undefined);
export function ConsumablesProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<Consumable[]>([]);
  const [movements, setMovements] = useState<ConsumableMovement[]>([]);
  const saveItem = (item: Consumable) => {
    if (!item.name.trim() || !CONSUMABLE_CATEGORIES.some(([id]) => id === item.category) || !CONSUMABLE_UNITS.includes(item.unit) ||
      !Number.isFinite(item.openingStock) || item.openingStock < 0 || !/^\d{4}-\d{2}-\d{2}$/.test(item.openingDate) ||
      (item.minLevel !== undefined && (!Number.isFinite(item.minLevel) || item.minLevel < 0))) throw new Error('Invalid consumable');
    const existing = items.find(row => row.id === item.id);
    if (existing && movements.some(m => m.materialId === item.id) &&
      (item.unit !== existing.unit || item.openingStock !== existing.openingStock || item.openingDate !== existing.openingDate)) throw new Error('Posted inventory unit and opening balance are locked');
    setItems(current => existing ? current.map(row => row.id === item.id ? { ...item, name: item.name.trim() } : row) : [...current, { ...item, name: item.name.trim() }]);
  };
  const addMovement = (movement: Omit<ConsumableMovement, 'id'>) => {
    const item = items.find(row => row.id === movement.materialId);
    if (!item || !Number.isFinite(movement.quantity) || movement.quantity <= 0 || !['IN', 'OUT'].includes(movement.type) ||
      !/^\d{4}-\d{2}-\d{2}$/.test(movement.date) || movement.date < item.openingDate) throw new Error('Invalid consumable movement');
    setMovements(current => [...current, { ...movement, id: crypto.randomUUID() }]);
  };
  return <Context.Provider value={{ items, movements, saveItem, addMovement }}>{children}</Context.Provider>;
}
export function useConsumables() {
  const context = useContext(Context);
  if (!context) throw new Error('ConsumablesProvider is required');
  return context;
}
