import { useEffect, useRef, useState, type FormEvent } from 'react';
import { useAuth } from '@/context/AuthContext';
import { rehearsalJobs, rehearsalJob, commandRehearsal, rehearsalHistory, type RehearsalJob } from '@/lib/rehearsalApi';
import type { Page } from '@/lib/commercialApi';
import axios from 'axios';

export function PersistedRecycling(){
  const {user}=useAuth();const permitted=user?.permissions?.includes('rehearsal.use_simulation');
  const [rows,setRows]=useState<Page<RehearsalJob>>(),[page,setPage]=useState(1),[job,setJob]=useState<RehearsalJob>();
  const [source,setSource]=useState(''),[form,setForm]=useState({classification:'PROCESS_WASTE',intake:'',recovered:'',rejected:'',disposed:'',batch_reference:'',reason:''});
  const [busy,setBusy]=useState(false),[error,setError]=useState(''),[refresh,setRefresh]=useState(0);
  const [history,setHistory]=useState<Awaited<ReturnType<typeof rehearsalHistory>>>(),[historyPage,setHistoryPage]=useState(1);
  const intent=useRef<{body:string;key:string}>();const lock=useRef(false);
  const fail=(e:unknown)=>setError(axios.isAxiosError(e)?`${e.response?.status===412?'Version conflict. Fields retained; reload the source job. ':''}${JSON.stringify(e.response?.data?.error??'Connection unavailable.')}`:'Request failed.');
  useEffect(()=>{if(!permitted)return;let live=true;setRows(undefined);rehearsalJobs(page).then(v=>{if(live)setRows(v);}).catch(fail);return()=>{live=false;};},[permitted,page,refresh,user?.id]);
  useEffect(()=>{if(!job)return;let live=true;setHistory(undefined);rehearsalHistory(job.id,historyPage).then(v=>{if(live)setHistory(v);}).catch(fail);return()=>{live=false;};},[job,historyPage]);
  const stages=job?.snapshot.routes.flatMap(r=>r.stages.filter(s=>s.status==='COMPLETE').map(s=>({line:r.line,stage:s.name,waste:String(s.waste??'0'),rejection:String(s.rejection??'0')})))??[];
  const selected=stages.find(s=>`${s.line}:${s.stage}`===source);
  async function save(e:FormEvent){e.preventDefault();if(!job||!selected||lock.current)return;lock.current=true;setBusy(true);setError('');try{
    const lines=(job.snapshot.source as {input:{lines:{unit:string}[]}}).input.lines;
    const {reason,...values}=form;const body={...values,line:selected.line,stage:selected.stage,unit:lines[selected.line].unit};
    const text=JSON.stringify({id:job.id,version:job.version,body,reason});if(intent.current?.body!==text)intent.current={body:text,key:crypto.randomUUID()};
    setJob(await commandRehearsal(job,'recycle',body,reason,intent.current.key));setRefresh(v=>v+1);setHistoryPage(1);
    setForm({...form,intake:'',recovered:'',rejected:'',disposed:'',batch_reference:'',reason:''});
  }catch(e){fail(e);}finally{lock.current=false;setBusy(false);}}
  return <section className="space-y-5"><h1 className="text-2xl font-semibold text-navy">Recycling</h1><p>Persisted development batches linked to exact completed production-stage waste. Synthetic records never credit operational stock. All recovered output remains unavailable for issue.</p>
    {!permitted?<p>Rehearsal capability and an approved development database are required.</p>:<>
    <button disabled={busy} onClick={()=>{setRefresh(v=>v+1);if(job)rehearsalJob(job.id).then(setJob).catch(fail);}}>Reload persisted sources</button>
    {!rows&&!error&&<p role="status">Loading production sources…</p>}{rows&&<><label>Production source<select className="block w-full rounded border p-2" value={job?.id??''} disabled={busy} onChange={e=>{const next=rows.results.find(r=>r.id===e.target.value);if(!form.intake||window.confirm('Discard unsaved recycling fields?')){setJob(next);setSource('');}}}><option value="">Select job…</option>{job&&!rows.results.some(r=>r.id===job.id)&&<option value={job.id}>{job.id}</option>}{rows.results.map(r=><option value={r.id} key={r.id}>{r.id} · {r.status}</option>)}</select></label><button disabled={!rows.previous||busy} onClick={()=>setPage(v=>v-1)}>Previous jobs</button><button disabled={!rows.next||busy} onClick={()=>setPage(v=>v+1)}>Next jobs</button></>}
    {job&&<><form onSubmit={save} className="rounded-xl border bg-white p-4 space-y-3"><h2>Record a synthetic processing batch</h2><label>Completed source stage<select className="block w-full border p-2" required value={source} disabled={busy} onChange={e=>setSource(e.target.value)}><option value="">Select…</option>{stages.map(s=><option key={`${s.line}:${s.stage}`} value={`${s.line}:${s.stage}`}>Line {s.line+1} · {s.stage} · waste {s.waste} · rejection {s.rejection}</option>)}</select></label><label>Waste classification<select className="block border p-2" value={form.classification} disabled={busy} onChange={e=>setForm({...form,classification:e.target.value})}><option>PROCESS_WASTE</option><option>REJECTED_OUTPUT</option></select></label><div className="grid gap-3 md:grid-cols-2">{(['intake','recovered','rejected','disposed','batch_reference','reason'] as const).map(k=><label key={k}>{k.replaceAll('_',' ')}<input required className="block w-full border rounded p-2" disabled={busy} value={form[k]} onChange={e=>setForm({...form,[k]:e.target.value})} placeholder={k==='batch_reference'?'synthetic:batch-reference':undefined}/></label>)}</div><p>Recovered + rejected + disposed must equal intake. The backend rejects over-allocation, changed units and stale versions.</p><button className="rounded border p-2" disabled={!selected||busy}>{busy?'Saving…':'Save processing batch'}</button></form>
    <h2 className="font-semibold">Processing history</h2>{((job.snapshot.recycling??[]) as Record<string,unknown>[]).map((r,i)=><article className="rounded border bg-white p-3" key={i}><h3>{String(r.batch_reference)} · {String(r.at)}</h3><p>Line {Number(r.line)+1} · {String(r.stage)} · {String(r.classification)}</p><p>Intake {String(r.intake)} · recovered {String(r.recovered)} · rejected {String(r.rejected)} · disposed {String(r.disposed)} · exact unit {String(r.unit)}</p><p>Immutable source revision {String(r.source_revision)} · available stock credit: none.</p></article>)}
    <h3>Immutable job revisions</h3>{history?.results.map(r=><details key={r.id}><summary>Revision {r.number} · {r.at} · {r.reason}</summary><pre className="whitespace-pre-wrap break-all">{JSON.stringify(r.snapshot,null,2)}</pre></details>)}<button disabled={!history?.previous} onClick={()=>setHistoryPage(v=>v-1)}>Previous history</button><button disabled={!history?.next} onClick={()=>setHistoryPage(v=>v+1)}>Next history</button></>}
    </>}{error&&<p role="alert" className="text-red-700 break-words">{error}</p>}
  </section>;
}
