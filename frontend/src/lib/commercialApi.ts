import { api } from './api';

export type CommercialKind = 'COSTING' | 'QUOTATION' | 'SALES_ORDER';
export interface CommercialRecord {
  id: string; kind: CommercialKind; version: number; status: 'DRAFT' | 'REVIEW' | 'CANCELLED'; revision: string; sha256: string;
  snapshot: { input: Record<string, unknown>; estimate: { net_estimate: string; payable_total: null; authoritative: false } };
}
export interface CommercialHistory { id: string; number: number; at: string; status: string; reason: string; snapshot: CommercialRecord['snapshot'] }
export interface Page<T> { count: number; next: string | null; previous: string | null; results: T[] }
export const commercialPage = async (page = 1) => (await api.get<Page<CommercialRecord>>('/commercial/documents/', { params: { page } })).data;
export const commercialHistory = async (id: string, page = 1) => (await api.get<Page<CommercialHistory>>(`/commercial/documents/${id}/history/`, { params: { page } })).data;
export async function saveCommercial(kind: CommercialKind, data: Record<string, unknown>, reason: string, key: string, record?: CommercialRecord) {
  const headers = { 'Idempotency-Key': key, ...(record ? { 'If-Match': `"${record.version}"` } : {}) };
  return (record ? await api.patch<CommercialRecord>(`/commercial/documents/${record.id}/`, { data, reason }, { headers }) :
    await api.post<CommercialRecord>('/commercial/documents/', { kind, data, reason }, { headers })).data;
}
export async function transitionCommercial(record: CommercialRecord, transition: 'submit' | 'reopen' | 'cancel', reason: string, key: string) {
  return (await api.post<CommercialRecord>(`/commercial/documents/${record.id}/transition/`, { transition, reason },
    { headers: { 'Idempotency-Key': key, 'If-Match': `"${record.version}"` } })).data;
}
