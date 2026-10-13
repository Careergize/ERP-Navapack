import { matchesQuotationCost, type Quotation } from '@/lib/quotations';
import { createContext, useContext, useRef, useState, type ReactNode } from 'react';
import { buildEstimateRevision, transitionEstimateLedger, MARKUP_SCENARIOS, type CostingInput, type CostEstimate, type EstimateStatus } from '@/lib/customCosting';
import { useAuth } from './AuthContext';
import { useSalesOrders } from './SalesOrdersContext';
import { useModels } from './ModelsContext';
import { RAW_MATERIALS } from '@/lib/rawMaterialData';
interface State { saveForQuotation: (input: CostingInput, quotation: Quotation, existingId?: string) => CostEstimate; bindQuotationOrder: (estimateId: string, orderId: string, itemId: string) => void; bindJob: (id: string, jobCardId: string) => void; estimates: CostEstimate[]; save: (input: CostingInput, existingId?: string) => CostEstimate; setStatus: (id: string, status: EstimateStatus) => void; accept: (id: string, accepted: boolean) => void; generate: (id: string) => void; invalidate: (id: string, reason: string) => void }
const Context = createContext<State | undefined>(undefined);
export function CostingProvider({ children }: { children: ReactNode }) {
  const [estimates, setEstimates] = useState<CostEstimate[]>([]); const current = useRef(estimates);
  const { user } = useAuth(); const { orders, getOrders, linkEstimate } = useSalesOrders(); const { versions } = useModels();
  const publish = (next: CostEstimate[]) => { current.current = next; setEstimates(next); };
  const checkEditor = () => { if (!user || !['admin', 'accounts', 'receptionist', 'production_manager'].includes(user.role)) throw new Error('Your role cannot change costing estimates.'); };
  const change = (id: string, edit: (e: CostEstimate) => CostEstimate) => { checkEditor(); const e = current.current.find(e => e.id === id); if (!e) throw new Error('Estimate not found.'); publish(current.current.map(row => row.id === id ? edit(e) : row)); };
  const save = (input: CostingInput, existingId?: string) => {
    checkEditor();
    const order = orders.find(o => o.id === input.orderId), item = order?.items?.find(i => i.id === input.itemId);
    if (!item || item.fulfillmentSource !== 'manufacturing' || input.quantity !== item.quantity || input.unit !== item.unit || (item.modelId && (input.modelId !== item.modelId || input.modelRevision !== item.modelRevision)) || !versions.some(m => m.id === input.modelId && m.revision === input.modelRevision)) throw new Error('Costing must reference the custom order line quantity, unit and a known model revision.');
    if (!['admin', 'accounts'].includes(user!.role) && (!MARKUP_SCENARIOS.includes(input.markupPercent) || input.pricingMethod !== 'markup')) throw new Error('Accounts/Admin authorization is required for a custom markup or gross-margin method.');
    if (input.materials.some(m => !RAW_MATERIALS.some(raw => raw.id === m.materialId && raw.unit === m.unit))) throw new Error('Select recipe materials with their configured inventory units.');
    const estimate = buildEstimateRevision(input, current.current, existingId);
    publish([...current.current.filter(e => e.id !== estimate.id), estimate]); linkEstimate(input.orderId, input.itemId, estimate.id); return estimate;
  };
  const setStatus: State['setStatus'] = (id, status) => { checkEditor(); publish(transitionEstimateLedger(current.current, id, status, user!)); };
  return <Context.Provider value={{ estimates,
    saveForQuotation: (input, quotation, existingId) => {
      checkEditor(); const line = quotation.lines.find(l => l.id === input.itemId);
      const provisional = { input } as CostEstimate;
      if (quotation.status !== 'Draft' || !quotation.customer.name.trim() || !line || line.type !== 'custom' || !matchesQuotationCost(provisional, quotation, line) || input.orderId || !versions.some(m => m.id === input.modelId && m.revision === input.modelRevision)) throw new Error('Costing must reference a saved draft quotation line/model, exact quantity and unit. No Sales Order is required.');
      if (!['admin', 'accounts'].includes(user!.role) && (!MARKUP_SCENARIOS.includes(input.markupPercent) || input.pricingMethod !== 'markup')) throw new Error('Accounts/Admin must authorize custom markup or margin.');
      if (input.materials.some(m => !RAW_MATERIALS.some(raw => raw.id === m.materialId && raw.unit === m.unit))) throw new Error('Select exact materials and inventory units.');
      const e = buildEstimateRevision(input, current.current, existingId); publish([...current.current.filter(row => row.id !== e.id), e]); return e;
    },
    bindQuotationOrder: (estimateId, orderId, itemId) => {
      checkEditor(); const e = current.current.find(e => e.id === estimateId), order = getOrders().find(o => o.id === orderId), item = order?.items?.find(i => i.id === itemId);
      if (!e || e.status !== 'Approved' || !item || e.input.quotationId !== order?.quotationId || e.input.itemId !== item.quotationLineId || e.input.quantity !== item.quantity || e.input.unit !== item.unit || e.input.modelId !== item.modelId || e.input.modelRevision !== item.modelRevision) throw new Error('Adopt only exact approved quotation costing into its converted order line.');
      if (e.salesOrderReferences?.some(r => r.orderId === orderId && r.itemId === itemId)) return;
      publish(current.current.map(row => row.id === e.id ? { ...row, salesOrderReferences: [...(row.salesOrderReferences ?? []), { orderId, itemId }] } : row));
    }, bindJob: (id, jobCardId) => { const e = current.current.find(e => e.id === id); if (!e || (e.usedByJobCardId && e.usedByJobCardId !== jobCardId)) throw new Error('Estimate is already linked to another Job Card.'); publish(current.current.map(row => row.id === id ? { ...row, usedByJobCardId: jobCardId } : row)); }, save, setStatus, accept: (id, accepted) => change(id, e => { if (!e.generatedAt || e.status !== 'Approved') throw new Error('Only a generated internally approved estimate can record customer response.'); return { ...e, customerAcceptance: accepted ? 'Accepted' : 'Rejected' }; }), generate: id => change(id, e => { if (!e.input.validityDate || !Number.isFinite(Date.parse(e.input.validityDate))) throw new Error('Enter estimate validity date.'); return { ...e, generatedAt: e.generatedAt ?? new Date().toISOString() }; }), invalidate: (id, reason) => { const e = current.current.find(e => e.id === id); if (!e) throw new Error('Linked estimate not found.'); publish(current.current.map(row => row.id === id ? { ...row, status: 'Revision Required', reviewReason: reason } : row)); } }}>{children}</Context.Provider>;
}
export function useCosting() { const value = useContext(Context); if (!value) throw new Error('CostingProvider required'); return value; }
