import {useEffect,useState,type FormEvent} from 'react';
import axios from 'axios';
import {useAuth} from '@/context/AuthContext';
import {operationMode} from '@/lib/inventoryOperationsApi';
import {custodyPage,custodyScope,type CustodyPage,type CustodyScope} from '@/lib/custodyApi';

export function InventoryCustody({initialItemType=''}:{initialItemType?:string}){
 const {user}=useAuth();const readable=user?.permissions?.includes('inventory.view_synthetic_custody');
 const [enabled,setEnabled]=useState<boolean>();const [resource,setResource]=useState<'balances'|'movements'>('balances');
 const [filters,setFilters]=useState({warehouse:'',location:'',stock:'',item_type:initialItemType,month:''});const [page,setPage]=useState(1);
 const [data,setData]=useState<CustodyPage>();const [scope,setScope]=useState<CustodyScope>();const [error,setError]=useState('');const [refresh,setRefresh]=useState(0);
 const fail=(cause:unknown)=>setError(axios.isAxiosError(cause)?JSON.stringify(cause.response?.data?.error??'Connection unavailable. Retry read.'):'Read unavailable.');
 useEffect(()=>{let live=true;operationMode().then(v=>{if(live)setEnabled(v.synthetic_enabled);}).catch(fail);return()=>{live=false;};},[]);
 useEffect(()=>{let live=true;setData(undefined);setError('');setScope(undefined);if(enabled&&readable)custodyPage(resource,page,filters).then(v=>{if(live)setData(v);}).catch(fail);return()=>{live=false;};},[enabled,readable,resource,page,filters,refresh,user?.id]);
 async function inspect(event:FormEvent){event.preventDefault();setScope(undefined);setError('');try{setScope(await custodyScope(filters.stock,filters.location));}catch(cause){fail(cause);}}
 return <section className="space-y-4"><h2 className="text-xl font-semibold">Stock balances and custody history</h2><p>Isolated synthetic observations only. Each quantity has its own item, primary unit, location and quality partition. RELEASED is not a reservation or a guarantee of issue eligibility; posting checks current holds, ownership, coverage and authority again.</p>
 {enabled===undefined?<p role="status">Checking backend availability…</p>:!enabled?<p role="status">Unavailable outside an authorized disposable test environment. Unknown stock is not zero.</p>:!readable?<p>Explicit custody view capability is required.</p>:<>
 <nav><button onClick={()=>{setResource('balances');setPage(1);}}>Balances</button><button onClick={()=>{setResource('movements');setPage(1);}}>Movement history</button></nav>
 <form onSubmit={inspect} className="space-y-2">{resource==='movements'&&<label className="block">Movement month (UTC)<input type="month" value={filters.month} onChange={e=>{setFilters({...filters,month:e.target.value});setPage(1);}}/></label>}{['warehouse','stock','location'].map(field=><label className="block" key={field}>{field} UUID filter<input className="ml-2 border p-2" value={filters[field as 'warehouse'|'stock'|'location']} onChange={e=>{setFilters({...filters,[field]:e.target.value});setPage(1);}}/></label>)}
 <label>Item type<select value={filters.item_type} onChange={e=>{setFilters({...filters,item_type:e.target.value});setPage(1);}}><option value="">All item identities</option><option value="variant">Finished goods</option><option value="material">Raw materials</option><option value="consumable">Consumables</option></select></label>
 <button disabled={!filters.stock||!filters.location}>Inspect opening coverage and exact custody</button><button type="button" onClick={()=>setRefresh(v=>v+1)}>Refresh persisted custody</button></form>
 {scope&&<article className="border p-3"><h3>Opening coverage: {scope.opening_status}</h3><p>Observed {scope.observed_at}; unit {scope.unit}. Explicit containment: {scope.explicit_containment?'YES':'no recorded root hold'}.</p>{(['HELD','RELEASED']as const).map(q=><p key={q}>{q}: {scope.partitions[q].quantity??'UNKNOWN'} · version {scope.partitions[q].version??'unknown'}</p>)}</article>}
 {!data?<p role="status">Loading persisted custody…</p>:<><p>{data.count} exact {resource} records. No cross-unit totals.</p>{!data.results.length&&<p>No visible records. Absence is not proof of zero stock or known opening coverage.</p>}{data.results.map(row=><article className="border p-3" key={row.id}><p>{row.reference} · {row.quality} · {resource==='balances'?'quantity '+row.quantity:'movement '+row.delta}</p><p>Stock {row.stock} · unit {row.unit} · warehouse {row.warehouse} · location {row.location}</p>{row.explicit_containment&&<p>Explicit containment: unavailable pending disposition.</p>}{row.transaction&&<p>Transaction {row.transaction} · {row.kind} · {row.event_at}</p>}</article>)}<button disabled={!data.previous} onClick={()=>setPage(v=>v-1)}>Previous custody page</button><button disabled={!data.next} onClick={()=>setPage(v=>v+1)}>Next custody page</button></>}
 </>}{error&&<p role="alert">{error}</p>}</section>;
}
