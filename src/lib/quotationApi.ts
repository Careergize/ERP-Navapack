import { api } from './api';
import { COMPANY_DEFAULTS, publicQuotation, quotationTotals, type Quotation } from './quotations';

export interface SavedDraft {
  id: string; version: number; editor_data: Quotation; created_by: string; created_by_name: string; updated_at: string;
  review: { id: string; submitted_at: string | null; approved: boolean; approved_at: string | null; rejected_at: string | null; rejection_reason: string; reviewed_by: string | null; deliveries: { status: string }[] } | null;
}

export function quotationFromDraft(record: SavedDraft): Quotation {
  const data = record.editor_data;
  const terms = { ...data.terms };
  for (const key of ['advancePercent', 'creditDays', 'quantityTolerance'] as const) if (terms[key] !== undefined) terms[key] = Number(terms[key]);
  const q: Quotation = {
    ...data, draftVersion: record.version, taxRate: Number(data.taxRate), discount: Number(data.discount), terms,
    company: { ...COMPANY_DEFAULTS, ...data.company, currency: data.currency, taxRate: Number(data.taxRate), taxMode: data.taxMode, validityDays: data.validityDays, banks: data.company.banks.map((b, i) => ({ ...b, id: b.id ?? `bank-${i}` })) },
    lines: data.lines.map(l => ({ ...l, quantity: Number(l.quantity), unitPrice: Number(l.unitPrice) })),
    status: 'Draft', createdBy: record.created_by_name, createdById: record.created_by,
    approval: undefined, responses: [], events: [],
  };
  const review = record.review;
  if (review?.rejected_at) q.status = 'Rejected';
  else if (review?.approved) {
    q.status = review.deliveries.some(d => d.status === 'accepted') ? 'Sent' : 'Approved';
    q.approval = { id: review.id, user: review.reviewed_by ?? 'Manager', userId: '', at: review.approved_at ?? '', totals: quotationTotals(q), roundingPolicy: 'Server-approved quotation snapshot' };
  } else if (review?.submitted_at) q.status = 'Pending Internal Approval';
  q.events = [{ id: `saved-${record.version}`, at: record.updated_at, user: record.created_by_name, userId: record.created_by, type: 'Saved', description: 'Draft restored from the database.' }];
  if (review?.rejected_at) q.events.push({ id: `rejected-${review.id}`, at: review.rejected_at, user: review.reviewed_by ?? 'Manager', userId: '', type: 'Manager rejected', description: review.rejection_reason });
  return q;
}

export async function saveQuotationDraft(quotation: Quotation): Promise<SavedDraft> {
  const { data } = await api.post<SavedDraft>('/quotation-drafts/', { editor_data: quotation, expected_version: quotation.draftVersion ?? 0 });
  return data;
}

export async function loadQuotationDrafts(): Promise<Quotation[]> {
  const result: Quotation[] = [];
  for (let page = 1; ; page++) {
    const { data } = await api.get<{ results: SavedDraft[]; next: string | null }>('/quotation-drafts/', { params: { page } });
    result.push(...data.results.map(quotationFromDraft));
    if (!data.next) break;
  }
  return result.map(q => result.some(other => other.rootId === q.rootId && other.revision > q.revision) ? { ...q, status: 'Superseded' } : q);
}

export async function saveQuotationSnapshot(quotation: Quotation) {
  const customerId = quotation.customer.customerId;
  const { data } = await api.post('/quotations/', {
    ...publicQuotation(quotation), source_id: quotation.id, discount: quotation.discount,
    ...(customerId?.startsWith('db:') ? { customer_id: Number(customerId.slice(3)) } : {}),
  });
  return data;
}
