import { createContext, useContext, useRef, useState, type ReactNode } from 'react';
import { useAuth } from './AuthContext';
import { useCommercial } from './CommercialContext';
import { useModels } from './ModelsContext';
import { useCosting } from './CostingContext';
import { useSalesOrders } from './SalesOrdersContext';
import { createQuotation, submitQuotation, approveQuotation, sendQuotation, recordQuotationResponse, quotationEvent, validateQuotation, validateQuotationSources, reviseQuotation, quotationConversionDraft, QUOTATION_EDIT_ROLES, QUOTATION_APPROVE_ROLES, type Quotation, type QuotationResponse } from '@/lib/quotations';
import { FINISHED_BY_ID } from '@/lib/finishedGoodsData';
interface Value { quotations: Quotation[]; create: () => Quotation; edit: (draft: Quotation) => void; linkEstimate: (id: string, lineId: string, estimateId: string) => void; submit: (id: string) => void; approve: (id: string) => void; requestChanges: (id: string, remarks: string) => void; send: (id: string) => void; respond: (id: string, response: Omit<QuotationResponse, 'id' | 'revision'>) => void; revise: (id: string, duplicate?: boolean) => Quotation; convert: (id: string, customerId: string, requiredDate: string) => string }
const Context = createContext<Value | undefined>(undefined);
export function QuotationsProvider({ children }: { children: ReactNode }) {
  const [quotations, setQuotations] = useState<Quotation[]>([]); const current = useRef(quotations);
  const { user } = useAuth(); const { company, customers, prospects, promoteProspect } = useCommercial(); const { versions } = useModels(); const { estimates, bindQuotationOrder } = useCosting(); const { getOrders, createSalesOrder } = useSalesOrders();
  const publish = (next: Quotation[]) => { current.current = next; setQuotations(next); };
  const actor = (roles = QUOTATION_EDIT_ROLES) => { if (!user || !roles.includes(user.role)) throw new Error('Your role cannot perform this quotation action.'); return user; };
  const get = (id: string) => { const q = current.current.find(q => q.id === id); if (!q) throw new Error('Quotation not found.'); return q; };
  const replace = (q: Quotation) => publish(current.current.map(row => row.id === q.id ? q : row));
  const check = (q: Quotation) => { if (!(q.customer.customerId && customers.some(c => c.id === q.customer.customerId)) && !(q.customer.prospectId && prospects.some(p => p.id === q.customer.prospectId))) throw new Error('Select an exact existing customer/prospect before approval.'); validateQuotation(q); validateQuotationSources(q, estimates, versions); if (q.lines.some(l => l.type === 'stock' && FINISHED_BY_ID.get(l.productId ?? '')?.unit !== l.unit)) throw new Error('Use the exact existing product unit; no carton/piece conversion is inferred.'); };
  return <Context.Provider value={{ quotations,
    create: () => { const q = createQuotation(company, current.current, actor()); publish([...current.current, q]); return q; },
    edit: draft => { const u = actor(); const previous = get(draft.id); if (previous.status !== 'Draft' || draft.rootId !== previous.rootId || draft.revision !== previous.revision) throw new Error('Revise approved/sent documents; their commercial content is immutable.'); if (u.role !== 'admin' && previous.number !== draft.number) throw new Error('Admin alone can change draft quotation numbers.'); if (current.current.some(q => q.rootId !== draft.rootId && q.number.toLowerCase() === draft.number.toLowerCase())) throw new Error('Quotation number belongs to another document.'); validateQuotation(draft, false); replace({ ...structuredClone(draft), status: 'Draft', approval: undefined, responses: previous.responses, events: [...previous.events, quotationEvent(u, 'Draft edited', 'Commercial draft updated; no inventory/production action.')], createdBy: previous.createdBy, createdById: previous.createdById }); },
    linkEstimate: (id, lineId, estimateId) => { const u = actor(['admin', 'accounts', 'receptionist', 'production_manager']); const q = get(id); if (q.status !== 'Draft' || !q.lines.some(l => l.id === lineId && l.type === 'custom')) throw new Error('Quotation costing can link only to a draft custom line.'); replace({ ...q, lines: q.lines.map(l => l.id === lineId ? { ...l, estimateId, estimateRevision: undefined } : l), events: [...q.events, quotationEvent(u, 'Costing linked', `Draft costing ${estimateId}; explicitly apply the approved price before quotation approval.`)] }); },
    submit: id => { const q = get(id); check(q); replace(submitQuotation(q, estimates, versions, actor())); },
    approve: id => { const q = get(id); check(q); replace(approveQuotation(q, estimates, versions, actor(QUOTATION_APPROVE_ROLES))); },
    requestChanges: (id, remarks) => { const u = actor(QUOTATION_APPROVE_ROLES); const q = get(id); if (q.status !== 'Pending Internal Approval' || !remarks.trim()) throw new Error('Request changes to a pending revision with remarks.'); replace({ ...q, status: 'Draft', events: [...q.events, quotationEvent(u, 'Changes requested', remarks)] }); },
    send: id => { const q = get(id); check(q); replace(sendQuotation(q, estimates, versions, actor())); },
    respond: (id, response) => replace(recordQuotationResponse(get(id), response, actor())),
    revise: (id, duplicate = false) => { const u = actor(); const old = get(id); const next = reviseQuotation(old, current.current, company, u, duplicate); publish([...current.current.map(q => !duplicate && q.id === id ? { ...q, status: 'Superseded' as const, events: [...q.events, quotationEvent(u, 'Superseded', `New revision ${next.revision}; original prices/terms/acceptance retained.`)] } : q), next]); return next; },
    convert: (id, customerId, requiredDate) => {
      const u = actor(['receptionist', 'admin']); const q = get(id); const existing = getOrders().find(o => o.quotationId === q.rootId); if (existing) return existing.id;
      if (current.current.some(n => n.rootId === q.rootId && n.revision > q.revision)) throw new Error('Convert only the latest accepted revision.');
      check(q);
      const linkedCustomer = q.customer.customerId ?? prospects.find(p => p.id === q.customer.prospectId)?.linkedCustomerId;
      if (!customers.some(c => c.id === customerId) || (linkedCustomer && customerId !== linkedCustomer)) throw new Error('Select the exact customer master linked to this quotation/prospect.');
      const draft = quotationConversionDraft(q, customerId, requiredDate, getOrders(), estimates, versions); if (q.customer.prospectId && !linkedCustomer) promoteProspect(q.customer.prospectId, customerId); const order = createSalesOrder(draft);
      for (const item of order.items ?? []) if (item.estimateId) bindQuotationOrder(item.estimateId, order.id, item.id);
      replace({ ...q, status: 'Converted to Sales Order', salesOrderId: order.id, events: [...q.events, quotationEvent(u, 'Converted', `Existing Sales Order ${order.orderNumber}; costing adopted without changing its approved financial snapshot. No Job Card or stock action created.`)] }); return order.id;
    },
  }}>{children}</Context.Provider>;
}
export function useQuotations() { const value = useContext(Context); if (!value) throw new Error('QuotationsProvider required'); return value; }
