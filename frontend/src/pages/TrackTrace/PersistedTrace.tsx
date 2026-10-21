import { useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { rehearsalJobs, rehearsalJob, rehearsalHistory, commandRehearsal, type RehearsalJob } from '@/lib/rehearsalApi';
import type { Page, CommercialRecord } from '@/lib/commercialApi';
import { CommercialSnapshot } from '@/pages/Commercial/CommercialSnapshot';
import { RehearsalInvoicePreview } from '@/pages/Rehearsal/RehearsalInvoicePreview';
import { useAuth } from '@/context/AuthContext';

export function PersistedTrace(){
  const {user}=useAuth();const [params,setParams]=useSearchParams();const id=params.get('jobId');
  const [rows,setRows]=useState<Page<RehearsalJob>>(),[page,setPage]=useState(1),[job,setJob]=useState<RehearsalJob>();
  const [history,setHistory]=useState<Awaited<ReturnType<typeof rehearsalHistory>>>(),[historyPage,setHistoryPage]=useState(1);
  const [error,setError]=useState(''),[busy,setBusy]=useState(false),[reason,setReason]=useState(''),[preview,setPreview]=useState(false),[refresh,setRefresh]=useState(0);
  const key=useRef<{intent:string;key:string}>();const lock=useRef(false);
  const permitted=user?.permissions?.includes('rehearsal.use_simulation');
  const fail=(e:unknown)=>setError(axios.isAxiosError(e)?JSON.stringify(e.response?.data?.error??'Backend unavailable.'):'Request failed.');
  useEffect(()=>{if(!permitted)return;let live=true;setRows(undefined);rehearsalJobs(page).then(v=>{if(live)setRows(v);}).catch(fail);return()=>{live=false;};},[page,refresh,permitted,user?.id]);
  useEffect(()=>{setJob(undefined);if(!id||!permitted)return;let live=true;rehearsalJob(id).then(v=>{if(live)setJob(v);}).catch(fail);return()=>{live=false;};},[id,refresh,permitted,user?.id]);
  useEffect(()=>{setHistory(undefined);if(!job)return;let live=true;rehearsalHistory(job.id,historyPage).then(v=>{if(live)setHistory(v);}).catch(fail);return()=>{live=false;};},[job,historyPage]);
  async function dispatch(){if(!job||lock.current)return;lock.current=true;setBusy(true);setError('');try{const value=JSON.stringify({id:job.id,version:job.version,reason});if(key.current?.intent!==value)key.current={intent:value,key:crypto.randomUUID()};setJob(await commandRehearsal(job,'dispatch',{},reason,key.current.key));}catch(e){fail(e);}finally{lock.current=false;setBusy(false);}}
  return <section className="space-y-5"><h1 className="text-2xl font-semibold text-navy">Dispatch and Track &amp; Trace</h1><p>Persisted development lineage only. Synthetic material issue, QC, output and dispatch never move operational stock or issue a legal invoice.</p>
    {!permitted?<p>Rehearsal capability and approved development environment required.</p>:<><button disabled={busy} onClick={()=>{setError('');setRefresh(v=>v+1);}}>Reload persisted trace</button>{!rows&&!error&&<p role="status">Loading scoped jobs…</p>}{rows&&<><label>Job Card<select className="block rounded border p-2 w-full" value={id??''} onChange={e=>{setParams(e.target.value?{jobId:e.target.value}:{});setHistoryPage(1);}}><option value="">Select source job…</option>{id&&!rows.results.some(r=>r.id===id)&&<option value={id}>{id}</option>}{rows.results.map(r=><option key={r.id} value={r.id}>{r.id} · {r.status}</option>)}</select></label><button disabled={!rows.previous} onClick={()=>setPage(v=>v-1)}>Previous jobs</button><button disabled={!rows.next} onClick={()=>setPage(v=>v+1)}>Next jobs</button></>}
    {job&&<><article className="rounded-xl border bg-white p-4 space-y-3"><h2>Job {job.id} · {job.status}</h2><Link className="underline" to={`/job-cards/${job.id}`}>Open production controls</Link><p>Warehouse {job.warehouse} · source {job.sales_order_revision?'Sales Order draft':'Costing draft / production for stock'} revision {job.sales_order_revision??job.costing_revision}</p><CommercialSnapshot snapshot={job.snapshot.source as unknown as CommercialRecord['snapshot']}/><h3>Source material requirement estimates</h3><pre className="whitespace-pre-wrap break-all">{JSON.stringify(job.snapshot.material_requirements??[],null,2)}</pre><h3>Synthetic material issue</h3><pre className="whitespace-pre-wrap break-all">{JSON.stringify(job.snapshot.material_issue,null,2)}</pre>
    {job.snapshot.routes.map(r=><div key={r.line}><h3>Product {r.line+1} production route</h3><ol>{r.stages.map(s=><li className="border-l pl-3 my-2" key={s.name}><strong>{s.name} · {s.status}</strong><pre className="whitespace-pre-wrap break-all">{JSON.stringify(s,null,2)}</pre></li>)}</ol></div>)}<h3>Synthetic QC / reinspection / failure history</h3><pre className="whitespace-pre-wrap break-all">{JSON.stringify(job.snapshot.qc,null,2)}</pre>
    <label>Simulation dispatch reason<input className="block border rounded p-2" value={reason} onChange={e=>setReason(e.target.value)}/></label><button className="rounded border p-2" disabled={busy||job.status!=='FINISHED'||!job.sales_order_revision||!reason.trim()} onClick={dispatch}>Record simulated dispatch</button><p>Available only after finished output and passing rehearsal QC for a customer-order job.</p><button disabled title="Physical custody evidence and operational dispatch approval are required.">Operational dispatch unavailable</button>
    {job.status==='DISPATCHED'&&job.sales_order_revision&&<button className="block underline" onClick={()=>setPreview(true)}>Open linked draft invoice preview</button>}</article>
    <section><h2 className="font-semibold">Immutable event timeline</h2>{history?.results.map(r=><details className="border-l pl-3 py-2" key={r.id}><summary>Revision {r.number} · {r.at} · {r.reason}</summary><pre className="whitespace-pre-wrap break-all">{JSON.stringify(r,null,2)}</pre></details>)}<button disabled={!history?.previous} onClick={()=>setHistoryPage(v=>v-1)}>Previous events</button><button disabled={!history?.next} onClick={()=>setHistoryPage(v=>v+1)}>Next events</button></section></>}
    </>}{preview&&job&&<RehearsalInvoicePreview job={job} close={()=>setPreview(false)}/ >}{error&&<p role="alert" className="text-red-700">{error}</p>}
  </section>;
}
