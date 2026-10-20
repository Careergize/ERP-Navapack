import { api } from './api';
export type QCResource = 'plans'|'inspections'|'holds'|'held-stock'|'ncr';
export type QCRecord = {id:string;version:number;created_at:string;[key:string]:unknown};
export type QCPage = {count:number;next:string|null;previous:string|null;results:QCRecord[]};
export async function qualityMode(){return (await api.get<{synthetic_enabled:boolean;operational_posting:false;message:string}>('/inventory/quality/mode/')).data;}
export async function qualityPage(resource:QCResource,page:number){return (await api.get<QCPage>(`/inventory/quality/${resource}/`,{params:{page}})).data;}
export async function qualityDetail(resource:QCResource,id:string){return (await api.get<QCRecord>(`/inventory/quality/${resource}/${id}/`)).data;}
export async function qualityHistory(resource:QCResource,id:string,page:number){return (await api.get<{count:number;next:string|null;previous:string|null;results:{id:string;actor:string;action:string;reason:string;timestamp:string;summary:unknown}[]}>(`/inventory/quality/${resource}/${id}/history/`,{params:{page}})).data;}
export async function qualityCommand(resource:QCResource,body:Record<string,unknown>,key:string,record?:QCRecord,step?:string){
  const path=record&&step?`/inventory/quality/${resource}/${record.id}/${step}/`:`/inventory/quality/${resource}/`;
  return (await api.post<QCRecord>(path,body,{headers:{'Idempotency-Key':key,...(record?{'If-Match':`"${record.version}"`}:{})},timeout:15000})).data;
}
