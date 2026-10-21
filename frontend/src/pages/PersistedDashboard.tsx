import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { rehearsalDashboard } from '@/lib/rehearsalApi';
import { RehearsalSummary } from './Rehearsal/RehearsalSummary';
import { useAuth } from '@/context/AuthContext';
import axios from 'axios';
import { InventoryCustody } from './Inventory/InventoryCustody';

export function PersistedDashboard({finance=false}:{finance?:boolean}){
  const {user}=useAuth();const [data,setData]=useState<Record<string,unknown>>(),[error,setError]=useState(''),[refresh,setRefresh]=useState(0);
  const [stockOpen,setStockOpen]=useState(false);
  const permitted=user?.permissions?.includes('rehearsal.use_simulation');
  useEffect(()=>{if(!permitted)return;let live=true;setError('');setData(undefined);rehearsalDashboard().then(v=>{if(live)setData(v);}).catch(e=>{if(live)setError(axios.isAxiosError(e)?JSON.stringify(e.response?.data?.error??'Backend unavailable.'): 'Report unavailable.');});return()=>{live=false;};},[permitted,user?.id,refresh]);
  const estimates=data?.commercial_by_party as {party:string;kind:string;currency:string;documents:number;net_estimate:string;estimated_production_cost:string|null;estimated_margin:string|null}[]|undefined;
  return <section className="space-y-5"><h1 className="text-2xl font-semibold text-navy">{finance?'Finance estimates and draft documents':'Operations dashboard'}</h1><p>Source: Django /rehearsal/jobs/dashboard/ · current authorized development database. Commercial values are unapproved drafts; production and dispatch are synthetic. No accounting entries or legal invoices.</p>
    <nav className="flex gap-4 flex-wrap"><Link className="underline" to="/masters">Masters</Link><Link className="underline" to="/costing">Costing</Link><Link className="underline" to="/quotations">Quotations</Link><Link className="underline" to="/sales-orders">Sales Order drafts</Link><Link className="underline" to="/job-cards">Production</Link><Link className="underline" to="/track-trace">Dispatch / draft invoices</Link></nav>
    {!permitted?<p>No rehearsal report capability. Other modules remain available according to your explicit permissions.</p>:<><button className="rounded border p-2" onClick={()=>setRefresh(v=>v+1)}>Refresh backend reports</button>{!data&&!error&&<p role="status">Loading persisted aggregates…</p>}{data&&<>
    <section className="rounded-xl border bg-white p-4"><h2 className="font-semibold">Permitted master counts · global catalog</h2><dl className="grid gap-3 sm:grid-cols-3">{Object.entries({...data.parties as object,...data.catalog as object}).map(([name,value])=><div key={name}><dt>{name}</dt><dd>{value===null?'View permission unavailable':String(value)}</dd></div>)}</dl></section>
    <RehearsalSummary data={data}/>
    <section className="rounded-xl border bg-white p-4"><h2 className="font-semibold">Estimated production cost by exact currency</h2>{Object.entries((data.estimated_cost_by_currency??{}) as Record<string,string>).map(([c,v])=><p key={c}>{v} {c} · persisted costing estimates</p>)}</section>
    <section><h2 className="font-semibold">Customer / prospect commercial summaries</h2><p>Each document kind is reported separately. Costings, quotations and Sales Order drafts overlap and must not be added into revenue. Margin means net draft estimate less snapshotted estimated production cost, where every line supplies a cost.</p>{estimates?.map((r,i)=><article className="border-b py-3" key={i}><p>Party reference {r.party} · {r.kind} · {r.documents} drafts</p><p>Net estimate {r.net_estimate} {r.currency}</p><p>Estimated production cost {r.estimated_production_cost??'Unavailable'} · estimated margin {r.estimated_margin??'Unavailable'} {r.currency}</p></article>)}</section>
    <section><h2 className="font-semibold">Synthetic recycling by exact unit</h2>{((data.recycling_by_unit??[]) as Record<string,unknown>[]).map(r=><p key={String(r.unit)}>Unit {String(r.unit)} · batches {String(r.batches)} · intake {String(r.intake)} · recovered {String(r.recovered)} · rejected {String(r.rejected)} · disposed {String(r.disposed)} · no available stock credit</p>)}</section>
    {!finance&&user?.permissions?.includes('inventory.view_synthetic_custody')&&<section className="rounded-xl border bg-white p-4"><button className="font-semibold underline" aria-expanded={stockOpen} onClick={()=>setStockOpen(v=>!v)}>Finished Goods / Raw Materials / Consumables custody</button>{stockOpen&&<InventoryCustody/>}</section>}
    <p>Operational available stock, VAT, LED, FX conversions, final payable, actual cost, receivables and payment posting remain unavailable. Open Stock, Raw Materials or Consumables for permitted exact-unit synthetic custody records.</p>
    </>}</>}{error&&<p role="alert" className="text-red-700 break-words">{error}</p>}
  </section>;
}
