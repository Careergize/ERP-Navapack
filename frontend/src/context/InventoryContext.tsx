import { useSalesOrders } from './SalesOrdersContext';
import { useAuth } from './AuthContext';
import { useQuality } from './QualityContext';
import { subjectHeld } from '@/lib/quality';
import { assertManualFinishedINQC, assertFinishedReceiptQC, rawHeldQuantity } from '@/lib/qualityIntegration';
import { rawMaterialBalance } from '@/lib/rawMaterialData';
import { createContext, useContext, useState, useRef, type ReactNode } from 'react';
import { FINISHED_MOVEMENTS, FINISHED_BY_ID, type FinishedGoodsMovement } from '@/lib/finishedGoodsData';
import { allocate, confirmDirectDispatch, confirmDispatch, reverseDispatch, reserved, physical, batchPhysical, type FulfillmentLedger } from '@/lib/fulfillment';
import type { SalesOrder, SalesOrderItem } from '@/types';
import { RAW_MATERIALS, RAW_MOVEMENTS, type RawMaterialMovement } from '@/lib/rawMaterialData';
import { snapshotMovements, validateConversion, validateThreshold, type ProductConversion, type StockThreshold } from '@/lib/stockIntelligence';

interface InventoryContextValue {
  conversions: ProductConversion[];
  thresholds: StockThreshold[];
  saveConversion: (draft: Omit<ProductConversion, 'id' | 'version'>) => void;
  saveThreshold: (draft: StockThreshold) => void;
  directDispatch: (order: SalesOrder, item: SalesOrderItem, batch: string, draft: Parameters<typeof confirmDirectDispatch>[4]) => void;
  ledger: FulfillmentLedger;
  allocateStock: (order: SalesOrder, item: SalesOrderItem, quantity: number, batch: string, requestId?: string) => void;
  dispatch: (draft: Parameters<typeof confirmDispatch>[1]) => void;
  reverse: (id: string, date: string, reason: string) => void;
  postReceipt: (movement: FinishedGoodsMovement) => void;
  finishedMovements: FinishedGoodsMovement[];
  finishedPieces: Record<string, number>;
  updateFinishedPieces: (productId: string, pieces: number) => void;
  rawMovements: RawMaterialMovement[];
  addFinishedMovement: (movement: Omit<FinishedGoodsMovement, 'id'>) => void;
  addRawMovement: (movement: Omit<RawMaterialMovement, 'id'>) => void;
}
const InventoryContext = createContext<InventoryContextValue | undefined>(undefined);
export function InventoryProvider({ children }: { children: ReactNode }) {
  const { getOrders } = useSalesOrders();
  const quality = useQuality(); const { user } = useAuth();
  const [conversions, setConversions] = useState<ProductConversion[]>([]); const conversionRef = useRef(conversions);
  const [thresholds, setThresholds] = useState<StockThreshold[]>([]);
  // Same lifecycle as SalesOrdersContext: navigation-safe frontend simulation,
  // reset on refresh. Replace seed loading and add methods with API adapters later.
  const [ledger, setLedger] = useState<FulfillmentLedger>({ movements: FINISHED_MOVEMENTS, allocations: [], dispatches: [] });
  const current = useRef(ledger);
  const publish = (next: FulfillmentLedger) => { next={...next,movements:snapshotMovements(current.current.movements,next.movements,conversionRef.current)}; current.current=next;setLedger(next); };
  const finishedMovements = ledger.movements;
  const postReceipt = (movement: FinishedGoodsMovement) => {
    const existing = current.current.movements.find(m => m.id === movement.id);
    if (existing) { if (existing.productId !== movement.productId || existing.quantity !== movement.quantity || existing.date !== movement.date || existing.unit !== movement.unit || existing.batch !== movement.batch || existing.stockApprovalId !== movement.stockApprovalId) throw new Error('Receipt request ID conflicts with an existing transaction.'); return; }
    const product = FINISHED_BY_ID.get(movement.productId);
    if (movement.jobCardId || movement.manufacturingItemId || movement.stockApprovalId || movement.qualityReleaseId) assertFinishedReceiptQC(quality.getState(), movement, current.current.movements);
    if (!product || movement.type !== 'IN' || !movement.id || !Number.isFinite(Date.parse(movement.date)) || product.unit !== movement.unit || movement.quantity <= 0 || !Number.isFinite(movement.quantity) || movement.date < product.openingDate) throw new Error('Receipt product, unit, quantity or date is invalid.');
    publish({ ...current.current, movements: [...current.current.movements, movement] });
  };
  const [finishedPieces, setFinishedPieces] = useState<Record<string, number>>({});
  const updateFinishedPieces = (productId: string, pieces: number) => {
    if (!FINISHED_BY_ID.has(productId) || !Number.isSafeInteger(pieces) || pieces <= 0) throw new Error('Invalid pieces');
    setFinishedPieces(current => ({ ...current, [productId]: pieces }));
  };
  const [rawMovements, setRaw] = useState(RAW_MOVEMENTS);
  const rawCurrent = useRef(rawMovements);
  const addFinishedMovement = (movement: Omit<FinishedGoodsMovement, 'id'>) => {
    const product = FINISHED_BY_ID.get(movement.productId);
    if (!product || product.unit !== movement.unit || !Number.isFinite(movement.quantity) || movement.quantity <= 0) throw new Error('Invalid finished goods movement');
    if (movement.type === 'IN') assertManualFinishedINQC(quality.getState(), user?.role, movement.productId);
    if (movement.jobCardId || movement.manufacturingItemId) throw new Error('Use the authorized production receipt workflow for manufactured stock.');
    if (movement.date < product.openingDate) throw new Error('Movement precedes reference opening.');
    if (movement.type === 'OUT') { if (!['admin','store_keeper'].includes(user?.role ?? '') || !['transfer','waste','adjustment'].includes(movement.movementPurpose ?? '') || !movement.reference?.trim() || !movement.remarks?.trim()) throw new Error('Store/Admin records a non-sales OUT purpose, reference and reason; use confirmed dispatch for sales.'); if (movement.movementPurpose==='adjustment' && user?.role!=='admin') throw new Error('Admin must approve and record adjustments.'); const balance = physical(current.current, product.id); if (balance === null || movement.quantity > balance - reserved(current.current, product.id) || movement.quantity > (batchPhysical(current.current, product.id, 'reference-stock') ?? 0) - reserved(current.current, product.id, 'reference-stock')) throw new Error('Stock OUT exceeds known unreserved stock.'); }
    publish({ ...current.current, movements: [...current.current.movements, { ...movement, batch: 'reference-stock', id: crypto.randomUUID() }] });
  };
  const addRawMovement = (movement: Omit<RawMaterialMovement, 'id'>) => {
    const material = RAW_MATERIALS.find(m => m.id === movement.materialId);
    if (!material || material.category !== movement.category || material.unit !== movement.unit || !Number.isFinite(movement.quantity) || movement.quantity <= 0) throw new Error('Invalid raw material movement');
    if (movement.movementType === 'OUT') { const balance = rawMaterialBalance(material, rawCurrent.current).currentStock; const held = rawHeldQuantity(quality.getState(), rawCurrent.current, material.id); if (held > 0 && (balance === null || movement.quantity > Math.max(0, balance - held))) throw new Error('Raw Material OUT cannot consume pending/rejected QC receipts. Physical receipt is not acceptance.'); }
    rawCurrent.current = [...rawCurrent.current, { ...movement, materialName: material.name, id: crypto.randomUUID() }]; setRaw(rawCurrent.current);
  };
  return <InventoryContext.Provider value={{ conversions, thresholds,
    saveConversion: draft => { if (!['admin','production_manager'].includes(user?.role ?? '')) throw new Error('Admin/Production Manager manages conversions.'); const product = FINISHED_BY_ID.get(draft.productId); if (!product || product.unit !== draft.unit) throw new Error('Select exact product/unit.'); const next = { ...draft, id: crypto.randomUUID(), version: 1 + Math.max(0,...conversionRef.current.filter(c=>c.productId===draft.productId && c.modelId===draft.modelId).map(c=>c.version)) }; validateConversion(next); conversionRef.current=[...conversionRef.current,next]; setConversions(conversionRef.current); },
    saveThreshold: draft => { if (!['admin','store_keeper','production_manager'].includes(user?.role ?? '')) throw new Error('Your role cannot configure stock thresholds.'); if (FINISHED_BY_ID.get(draft.productId)?.unit !== draft.unit) throw new Error('Use exact stock unit.'); validateThreshold(draft); setThresholds(list=>[...list.filter(t=>t.productId!==draft.productId), structuredClone(draft)]); },
    directDispatch: (order,item,batch,draft) => { if (!['admin','store_keeper','receptionist'].includes(user?.role ?? '')) throw new Error('Your role cannot dispatch stock.'); const stored=getOrders().find(o=>o.id===order.id),line=stored?.items?.find(i=>i.id===item.id);if(!stored||!line)throw new Error('Select a current Sales Order line.'); const held=current.current.movements.some(m=>m.productId===line.itemId && m.batch===batch && m.manufacturingItemId && quality.getState().inspections.some(i=>i.subject.manufacturingItemId===m.manufacturingItemId && i.subject.batchNumber===batch && subjectHeld(quality.getState(),i.subject))); if(held) throw new Error('A QC hold prevents dispatch of this batch.'); publish(confirmDirectDispatch(current.current,stored,line,batch,draft)); },
    ledger, postReceipt, allocateStock: (order, item, quantity, batch, requestId) => publish(allocate(current.current, order, item, quantity, batch, requestId)), dispatch: draft => {
    const a = current.current.allocations.find(a => a.id === draft.allocationId);
    if (a && current.current.movements.some(m => m.productId === a.productId && m.batch === a.batch && m.manufacturingItemId && quality.getState().inspections.some(i => i.subject.manufacturingItemId === m.manufacturingItemId && i.subject.batchNumber === a.batch && subjectHeld(quality.getState(), i.subject)))) throw new Error('A QC hold prevents dispatch of this batch.');
    publish(confirmDispatch(current.current, draft));
  }, reverse: (id, date, reason) => publish(reverseDispatch(current.current, id, date, reason)), finishedMovements, finishedPieces, updateFinishedPieces, rawMovements, addFinishedMovement, addRawMovement }}>{children}</InventoryContext.Provider>;
}
export function useInventory() {
  const context = useContext(InventoryContext);
  if (!context) throw new Error('InventoryProvider is required');
  return context;
}
