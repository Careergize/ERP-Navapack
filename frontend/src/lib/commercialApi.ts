import { api } from './api';

export type CommercialKind = 'COSTING' | 'QUOTATION' | 'SALES_ORDER';
export interface CommercialRecord {
  id: string; kind: CommercialKind; version: number; status: 'DRAFT' | 'REVIEW' | 'CANCELLED'; revision: string; sha256: string;
  snapshot: { input: Record<string, unknown>; estimate: { net_estimate: string; payable_total: null; authoritative: false } };
}
export interface CommercialHistory { id: string; number: number; at: string; actor: string; status: string; reason: string; snapshot: CommercialRecord['snapshot']; audit?: { id: string; actor: string; at: string; request_id: string; revision: string | null } }
export interface Page<T> { count: number; next: string | null; previous: string | null; results: T[] }
export const commercialPage = async (page = 1) => (await api.get<Page<CommercialRecord>>('/commercial/documents/', { params: { page } })).data;
export const commercialHistory = async (id: string, page = 1) => (await api.get<Page<CommercialHistory>>(`/commercial/documents/${id}/history/`, { params: { page } })).data;
export const deriveCommercial = async (record: CommercialRecord, reason: string, key: string) => (await api.post<CommercialRecord>(`/commercial/documents/${record.id}/derive/`, { source_revision: record.revision, reason }, { headers: { 'Idempotency-Key': key } })).data;
export async function saveCommercial(kind: CommercialKind, data: Record<string, unknown>, reason: string, key: string, record?: CommercialRecord) {
  const headers = { 'Idempotency-Key': key, ...(record ? { 'If-Match': `"${record.version}"` } : {}) };
  return (record ? await api.patch<CommercialRecord>(`/commercial/documents/${record.id}/`, { data, reason }, { headers }) :
    await api.post<CommercialRecord>('/commercial/documents/', { kind, data, reason }, { headers })).data;
}
export async function transitionCommercial(record: CommercialRecord, transition: 'submit' | 'reopen' | 'cancel', reason: string, key: string) {
  return (await api.post<CommercialRecord>(`/commercial/documents/${record.id}/transition/`, { transition, reason },
    { headers: { 'Idempotency-Key': key, 'If-Match': `"${record.version}"` } })).data;
}

export interface CommercialReference { id: string; name: string; unit?: string; code?: string; version?: number; default_unit?: string; specifications?: string; number?: number }
export interface CostingReference { id: string; document: string; number: number; currency: string; lines: { variant: string; unit: string; quantity: string; specifications: string; customisation: string; model_revision?: string; variant_snapshot: { name: string }; unit_snapshot: { code: string } }[] }
export async function allCommercialReferences<T>(resource: string): Promise<T[]> {
  const result: T[] = [];
  for (let page = 1; ; page++) {
    const { data } = await api.get<Page<T>>(resource, { params: { page } });
    result.push(...data.results); if (!data.next) return result;
  }
}
