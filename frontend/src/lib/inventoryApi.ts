import { api } from './api';
export type InventoryRecord = {
  id: string; version: number; code?: string; name?: string; description?: string;
  is_active?: boolean; warehouse?: string; parent?: string | null; classification?: string;
  custody_department?: string | null;
  reference?: string; kind?: string; ownership?: string; lifecycle?: string;
  material?: string | null; variant?: string | null; consumable?: string | null;
  unit?: string; source_reference?: string; physical_reference?: string; operational_status?: string;
  source_system?: string; source_document_reference?: string; supplier_batch?: string;
  owner_customer?: string | null; owner_supplier?: string | null; ownership_evidence?: string;
};
export type Resource = 'warehouses' | 'locations' | 'identities';
export type InventoryPage = {count: number; next: string | null; previous: string | null; results: InventoryRecord[]};
export type InventoryAudit = {id:string;actor:string;action:string;timestamp:string;reason:string;
  summary:{outcome?:{before?:Record<string,unknown>|null;after?:Record<string,unknown>}}};
export async function inventoryHistory(record: InventoryRecord, page: number) {
  return (await api.get<{count:number;next:string|null;previous:string|null;results:InventoryAudit[]}>('/inventory/history/',{params:{entity_id:record.id,page}})).data;
}
export async function inventoryPage(resource: Resource, search: string, warehouse: string, page: number) {
  const {data} = await api.get<InventoryPage>(`/inventory/${resource}/`, {params: {search, page, ...(warehouse && resource !== 'warehouses' ? {warehouse} : {})}});
  return data;
}
export async function saveInventory(resource: Resource, body: Record<string, unknown>, key: string, record?: InventoryRecord) {
  const config = {timeout:15000, headers: {'Idempotency-Key': key, ...(record ? {'If-Match': `"${record.version}"`} : {})}};
  return record ? (await api.patch<InventoryRecord>(`/inventory/${resource}/${record.id}/`, body, config)).data
    : (await api.post<InventoryRecord>(`/inventory/${resource}/`, body, config)).data;
}
