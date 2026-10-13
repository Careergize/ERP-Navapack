import { attachManufacturingItem, assertCompleteManufacturingScope, findWorkItem, parentForItem, summarizeParent } from '@/lib/parentJobCards';
import { buildLinkedJob } from '@/lib/salesJob';
import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from 'react';
import { api } from '@/lib/api';
import { MOCK_JOB_CARDS } from '@/lib/mockData';
import { normalizeJobCard, approveJobCard, issueJobMaterials, updateJobStage, transferJobToStock, editJobCard, toggleJobStage, type StageUpdate, type StockReceiptOptions } from '@/lib/jobCards';
import { useInventory } from './InventoryContext';
import { useModels } from './ModelsContext';
import { useCosting } from './CostingContext';
import { materialRequirements } from '@/lib/customCosting';
import { changeRouting, reopenRouting, validateRouting } from '@/lib/productionRouting';
import { FINISHED_BY_ID } from '@/lib/finishedGoodsData';
import { useAuth } from './AuthContext';
import { useSalesOrders } from './SalesOrdersContext';
import type { JobCard } from '@/types';

interface JobCardsState {
  createLinked: (orderId: string, itemId: string, modelId: string, requiredDate: string, specifications: string, materials: NonNullable<JobCard["requiredMaterials"]>, estimateId?: string) => Promise<JobCard>;
  cards: JobCard[];
  loading: boolean;
  usingDemo: boolean;
  load: () => Promise<void>;
  loadDetail: (id: string) => Promise<void>;
  postPreparedReceipts: (id: string, productId: string) => void;
  saveRouting: (id: string, stages: NonNullable<JobCard['productionStages']>, materials: NonNullable<JobCard['requiredMaterials']>) => void;
  reviseRouting: (id: string) => void;
  recalculate: (id: string, estimateId: string) => void;
  sendForReview: (id: string) => void;
  approve: (id: string) => void;
  issue: (id: string, quantities: Record<string, number>, available: Record<string, number | null>) => void;
  updateStage: (id: string, stageId: string, update: StageUpdate) => void;
  transfer: (id: string, accepted: number, batchDate: string, receipt?: StockReceiptOptions) => void;
  edit: (id: string, change: Parameters<typeof editJobCard>[1]) => void;
  toggleStage: (id: string, stageId: string) => void;
  saveSequence: (id: string) => Promise<boolean>;
}
const Context = createContext<JobCardsState | undefined>(undefined);
const validCard = (value: JobCard) => value && typeof value.id === 'string' && typeof value.jobCardNumber === 'string' && Array.isArray(value.stages);
export function JobCardsProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const { orders, linkJob, linkFinishedProduct } = useSalesOrders();
  const { versions } = useModels();
  const { estimates, invalidate, bindJob } = useCosting();
  const { postReceipt } = useInventory();
  const orderRef = useRef(orders); orderRef.current = orders;
  const [cards, setCards] = useState<JobCard[]>([]);
  const current = useRef<JobCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [usingDemo, setUsingDemo] = useState(false);
  const request = useRef<Promise<void>>();
  const dirty = useRef(new Set<string>());
  const details = useRef(new Map<string, Promise<void>>());
  const publish = (next: JobCard[]) => { current.current = next; setCards(next); };
  const load = useCallback(() => {
    if (!request.current) request.current = api.get<JobCard[]>('/job-cards/').then(({ data }) => {
      if (!Array.isArray(data) || !data.every(validCard)) throw new Error('Invalid job card response');
      publish(data.map(card => normalizeJobCard(card, orderRef.current)));
    }).catch(() => { publish(MOCK_JOB_CARDS.map(card => normalizeJobCard(card, orderRef.current))); setUsingDemo(true); }).finally(() => setLoading(false));
    return request.current;
  }, []);
  const loadDetail = useCallback((id: string) => {
    if (!details.current.has(id)) details.current.set(id, load().then(async () => {
      if (dirty.current.has(id) || parentForItem(current.current, id)?.manufacturingItems) return;
      try {
        const { data } = await api.get<JobCard>(`/job-cards/${encodeURIComponent(id)}/`);
        if (dirty.current.has(id) || parentForItem(current.current, id)?.manufacturingItems) return;
        if (!validCard(data) || data.id !== id) throw new Error('Invalid job card detail');
        const card = normalizeJobCard(data, orderRef.current);
        publish([...current.current.filter(c => c.id !== id), card]);
      } catch {
        // Keep the known list/mock record; unknown IDs remain a genuine not-found.
      }
    }));
    return details.current.get(id)!;
  }, [load]);
  const mutate = (id: string, change: (card: JobCard) => JobCard) => {
    if (!user) throw new Error('Sign in to update job cards.');
    const card = current.current.find(c => c.id === id) ?? findWorkItem(current.current, id);
    if (!card) throw new Error('Job card not found.');
    const next = change(card);
    dirty.current.add(id);
    const parent = parentForItem(current.current, id); if (parent) dirty.current.add(parent.id);
    publish(current.current.map(c => c.id === id ? next : c.manufacturingItems?.some(i => i.id === id) ? summarizeParent(c, c.manufacturingItems.map(i => i.id === id ? next : i)) : c));
  };
  const saveSequence = async (id: string) => {
    if (!user || !['admin', 'receptionist', 'production_manager'].includes(user.role)) throw new Error('Your role cannot save stage requirements.');
    const card = findWorkItem(current.current, id);
    if (!card || card.approval || !['Draft', 'PendingApproval'].includes(card.status)) throw new Error('Completed job card stage requirements are locked.');
    let persisted = false;
    try { if (!card.estimateId && !card.parentJobCardId) { await api.patch(`/job-cards/${id}/stages/`, { stages: card.stages }); persisted = true; } } catch { /* Existing API fallback stays explicit in the UI. */ }
    mutate(id, latest => ({ ...latest, activityHistory: [...(latest.activityHistory ?? []), { id: crypto.randomUUID(), timestamp: new Date().toISOString(), action: 'Stage requirements saved', user: user.name, department: 'Production Manager', description: persisted ? 'Existing stage API accepted the request; manufacturing tracking remains frontend-only.' : 'Saved in frontend state only; stage API was unavailable.' }] }));
    return persisted;
  };
  const createLinked: JobCardsState['createLinked'] = async (orderId, itemId, modelId, requiredDate, specifications, materials, estimateId) => {
    if (!user || !['admin', 'receptionist', 'production_manager'].includes(user.role)) throw new Error('Your role cannot create job cards.');
    await load();
    const order = orderRef.current.find(o => o.id === orderId), item = order?.items?.find(i => i.id === itemId), model = versions.find(m => m.id === modelId && m.revision === (item?.modelRevision ?? versions.filter(v => v.id === modelId).at(-1)?.revision));
    if (!order || !item || item.fulfillmentSource !== 'manufacturing' || !model) throw new Error('Select a custom order item and model.');
    const existing = current.current.flatMap(c => c.manufacturingItems ?? [c]).find(c => c.salesOrderId === orderId && c.salesOrderItemId === itemId);
    if (existing) return parentForItem(current.current, existing.id) ?? existing;
    const estimate = estimates.find(e => e.id === (estimateId ?? item.estimateId));
    if (item.modelId && !estimate) throw new Error('Save the line costing estimate before creating a linked custom Job Card.');
    const card = buildLinkedJob(order, item, model, requiredDate, specifications, materials, user, current.current, estimate);
    const attached = attachManufacturingItem(current.current, order, card);
    dirty.current.add(attached.parent.id);
    dirty.current.add(attached.item.id);
    if (estimate) bindJob(estimate.id, attached.item.id);
    publish([...current.current.filter(c => c.id !== attached.parent.id), attached.parent]);
    linkJob(order.id, attached.parent.id); return attached.parent;
  };
  return <Context.Provider value={{ createLinked, cards, loading, usingDemo, load, loadDetail,
    postPreparedReceipts: (id, productId) => mutate(id, card => {
      if (!['admin', 'store_keeper'].includes(user!.role) || !card.stockReceiptPending || !card.approval || !card.stockTransfers?.length) throw new Error('Store/Admin can post QC-prepared receipts once.');
      const product = FINISHED_BY_ID.get(productId);
      if (!product || product.unit !== card.stockTransfer?.unit || card.stockTransfers.some(r => r.date < product.openingDate)) throw new Error('Choose an exact finished product with matching output unit and valid opening date. No package conversion is assumed.');
      for (const receipt of card.stockTransfers) if (receipt.quantity > 0) postReceipt({ id: receipt.id, productId: product.id, date: receipt.date, type: 'IN', quantity: receipt.quantity, unit: product.unit, salesOrderId: card.salesOrderId, salesOrderItemId: card.salesOrderItemId, jobCardId: card.parentJobCardId ?? card.id, manufacturingItemId: card.parentJobCardId ? card.id : undefined, modelId: card.modelId, modelName: card.modelName, batch: receipt.batch, reference: card.jobCardNumber, customer: card.customerName, remarks: 'QC-prepared receipt explicitly mapped by Store.' });
      if (card.salesOrderItemId) linkFinishedProduct(card.salesOrderId, card.salesOrderItemId, productId);
      const produced = card.productionStages?.filter(s => s.required && s.kind === 'production').at(-1)?.outputQuantity ?? 0;
      return { ...card, finishedProductId: productId, stockReceiptPending: false, status: (card.acceptedQuantity ?? 0) + (card.rejectedQuantity ?? 0) >= produced ? 'Completed' : 'ReadyForStock', activityHistory: [...(card.activityHistory ?? []), { id: crypto.randomUUID(), timestamp: new Date().toISOString(), action: 'Prepared Stock IN posted', user: user!.name, department: 'Store', description: `Mapped exact product ${product.id}; QC batches posted to shared frontend inventory.` }] };
    }),
    saveRouting: (id, stages, materials) => mutate(id, card => { const next = changeRouting(card, stages, materials, user!); if (card.estimateId) invalidate(card.estimateId, 'Production routing/material requirements changed. Recalculate process costs and requirements.'); return next; }),
    reviseRouting: id => mutate(id, card => { const next = reopenRouting(card, user!); if (card.estimateId) invalidate(card.estimateId, 'Routing reapproval requested.'); return next; }),
    recalculate: (id, estimateId) => mutate(id, card => {
      if (!['admin', 'production_manager'].includes(user!.role) || card.approval || !['Draft', 'PendingApproval'].includes(card.status)) throw new Error('Requirements can only be recalculated by PM/Admin before approval.');
      const estimate = estimates.find(e => e.id === estimateId);
      if (!estimate || estimate.status !== 'Approved' || estimate.input.orderId !== card.salesOrderId || estimate.input.itemId !== card.salesOrderItemId || estimate.input.modelId !== card.modelId || estimate.input.modelRevision !== card.modelRevision) throw new Error('Select an internally approved, recalculated estimate for this line and model revision.');
      bindJob(estimate.id, card.id);
      return { ...card, requiredMaterials: materialRequirements(estimate.input), estimateId: estimate.id, estimateRevision: estimate.revision, requirementsReviewRequired: false, activityHistory: [...(card.activityHistory ?? []), { id: crypto.randomUUID(), timestamp: new Date().toISOString(), action: 'Requirements recalculated', user: user!.name, department: 'Production Manager', description: `Applied ${estimate.number} revision ${estimate.revision}. Explicit recipe quantities and costs were reviewed.` }] };
    }),
    sendForReview: id => mutate(id, card => {
      if (!['admin', 'production_manager', 'receptionist'].includes(user!.role) || card.status !== 'Draft') throw new Error('Only draft jobs can be sent for PM review.');
      return { ...card, status: 'PendingApproval', activityHistory: [...(card.activityHistory ?? []), { id: crypto.randomUUID(), timestamp: new Date().toISOString(), action: 'Sent for PM review', user: user!.name, department: 'Production Manager', description: 'Draft Job Card submitted for routing and material review.' }] };
    }),
    approve: id => {
      if (!user || !['admin', 'production_manager'].includes(user.role)) throw new Error('Your role cannot approve Job Cards.');
      const parent = parentForItem(current.current, id);
      if (parent?.manufacturingItems) {
        assertCompleteManufacturingScope(parent, orderRef.current.find(o => o.id === parent.salesOrderId));
        // Validate every item before publishing any approval; no partially approved parent.
        const approved = parent.manufacturingItems.map(card => {
          if (card.estimateId) { const estimate = estimates.find(e => e.id === card.estimateId); if (!estimate || ['Revision Required', 'Superseded'].includes(estimate.status)) throw new Error('Linked costing requires recalculation/review.'); validateRouting(card.productionStages ?? []); }
          return card.approval ? card : approveJobCard(card, user!);
        });
        mutate(parent.id, () => summarizeParent(parent, approved));
      } else mutate(id, card => { if (card.estimateId) { const estimate = estimates.find(e => e.id === card.estimateId); if (!estimate || ['Revision Required', 'Superseded'].includes(estimate.status)) throw new Error('Linked costing requires recalculation/review.'); validateRouting(card.productionStages ?? []); } return approveJobCard(card, user!); });
    },
    issue: (id, quantities, available) => mutate(id, card => issueJobMaterials(card, quantities, available, user!)),
    updateStage: (id, stageId, update) => mutate(id, card => updateJobStage(card, stageId, update, user!)),
    transfer: (id, accepted, date, receipt) => mutate(id, card => {
      const next = transferJobToStock(card, accepted, date, user!, new Date().toISOString(), receipt);
      if (next === card) return card;
      if ((next.acceptedQuantity ?? 0) === 0 && next.status === 'Completed') return { ...next, stockReceiptPending: false };
      const product = FINISHED_BY_ID.get(card.finishedProductId ?? '');
      if (!product && !card.finishedProductId && card.salesOrderItemId) return { ...next, status: 'ReadyForStock', stockReceiptPending: true, activityHistory: [...(next.activityHistory ?? []), { id: crypto.randomUUID(), timestamp: new Date().toISOString(), action: 'Stock IN prepared', user: user!.name, department: 'Store', description: 'QC quantities and batches retained; choose an exact finished-goods variant/unit to post. No physical inventory change occurred.' }] };
      if (!product || product.unit !== next.stockTransfer!.unit || !card.salesOrderItemId) throw new Error('Link a finished product and Sales Order item with matching output unit before posting stock. Legacy demo cards cannot be matched by name.');
      if (accepted > 0) postReceipt({ id: receipt?.id ?? `receipt-${card.id}`, productId: product.id, date, type: 'IN', quantity: accepted, unit: product.unit, salesOrderId: card.salesOrderId, salesOrderItemId: card.salesOrderItemId, jobCardId: card.parentJobCardId ?? card.id, manufacturingItemId: card.parentJobCardId ? card.id : undefined, modelId: card.modelId, modelName: card.modelName, batch: receipt?.batch ?? `LOT-${card.jobCardNumber}`, reference: card.jobCardNumber, customer: card.customerName, remarks: 'Accepted quantity verified by Store; frontend receipt.' });
      return next;
    }),
    edit: (id, change) => mutate(id, card => {
      if (card.salesOrderItemId && (change.qty !== card.qty || change.unit !== card.unit || change.product !== card.product || change.modelName !== card.modelName)) throw new Error('Linked order quantity, product, unit and selected model are locked. Edit specifications and delivery requirements instead.');
      return editJobCard(card, change, user!);
    }),
    toggleStage: (id, stageId) => mutate(id, card => { const next = toggleJobStage(card, stageId, user!); if (card.estimateId) { invalidate(card.estimateId, 'Mandatory production stages changed.'); return { ...next, status: 'Draft', requirementsReviewRequired: true, routingRevision: (card.routingRevision ?? 1) + 1 }; } return next; }), saveSequence,
  }}>{children}</Context.Provider>;
}
export function useJobCards() {
  const value = useContext(Context);
  if (!value) throw new Error('JobCardsProvider is required');
  return value;
}
