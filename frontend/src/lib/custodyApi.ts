import {api} from './api';
export type CustodyRow={id:string;stock:string;reference:string;unit:string;warehouse:string;location:string;quality:string;quantity?:string;delta?:string;event_at?:string;transaction?:string;kind?:string;explicit_containment?:boolean};
export type CustodyPage={count:number;next:string|null;previous:string|null;results:CustodyRow[]};
export type CustodyScope={stock:string;reference:string;unit:string;location:string;opening_status:'KNOWN'|'UNKNOWN';partitions:Record<'HELD'|'RELEASED',{quantity:string|null;version:number|null}>;explicit_containment:boolean;observed_at:string};
export async function custodyPage(resource:'balances'|'movements',page:number,filters:Record<string,string>){return (await api.get<CustodyPage>(`/inventory/custody/${resource}/`,{params:{page,...Object.fromEntries(Object.entries(filters).filter(([,v])=>v))}})).data;}
export async function custodyScope(stock:string,location:string){return (await api.get<CustodyScope>('/inventory/custody/scope/',{params:{stock,location}})).data;}
