import { api } from './api';
import type { Page } from './commercialApi';
export interface MasterRecord { id: string; version: number; name?: string; code?: string; [field: string]: unknown }
export interface MasterField { type: string; required: boolean; read_only: boolean; allow_null?: boolean; label?: string; max_length?: number; choices?: {value: string; display_name: string}[] }
export const masterPage = async (resource: string, page: number, search: string, active: string) =>
  (await api.get<Page<MasterRecord>>(`/${resource}/`, {params: {page, search, ...(active ? {is_active: active} : {})}})).data;
export const masterSchema = async (resource: string) => (await api.get<{fields: Record<string, MasterField>}>(`/${resource}/schema/`)).data.fields;
export const masterDetail = async (resource: string, id: string) => (await api.get<MasterRecord>(`/${resource}/${id}/`)).data;
export async function saveMaster(resource: string, body: Record<string, unknown>, key: string, record?: MasterRecord) {
  const config = {timeout: 15000, headers: {'Idempotency-Key': key, ...(record ? {'If-Match': `"${record.version}"`} : {})}};
  return (record ? await api.patch<MasterRecord>(`/${resource}/${record.id}/`, body, config) : await api.post<MasterRecord>(`/${resource}/`, body, config)).data;
}
