import { useEffect, useState, type FormEvent } from 'react';
import axios from 'axios';
import { useAuth } from '@/context/AuthContext';
import { qualityMode, qualityPage, qualityDetail, qualityHistory, qualityCommand, type QCResource, type QCRecord, type QCPage } from '@/lib/qualityApi';

const labels:Record<QCResource,string>={plans:'Inspection plans',inspections:'Inspection queue / review','held-stock':'Held stock',holds:'Explicit containment',ncr:'NCR / CAPA register'};
const fields:Record<string,string[]>={plans:['reference','revision','applicability','material','variant','consumable','criteria','specification_reference','sampling_reference'],
  inspections:['plan','source_entry','operation','previous','quantity','balance_version','physical_evidence','observations'],
  holds:['stock','location','policy','policy_version'],ncr:['inspection','hold','classification'],
  publish:['decision'],review:['decision'],release:['policy','policy_version'],ncr_action:['kind','owner','target_at','reinspection']};
const createCaps:Record<QCResource,string>={plans:'configure_qc',inspections:'inspect_qc',holds:'hold_qc',ncr:'manage_ncr','held-stock':''};
const stepCaps:Record<string,string>={publish:'approve_qc_plan',review:'review_qc',release:'release_qc',ncr_action:'manage_ncr'};

export function QualityFoundation(){
  const {user}=useAuth();const permissions=user?.permissions??[];
  const [mode,setMode]=useState<Awaited<ReturnType<typeof qualityMode>>>();
  const [resource,setResource]=useState<QCResource>('inspections');const [page,setPage]=useState(1);const [rows,setRows]=useState<QCPage>();
  const [selected,setSelected]=useState<QCRecord>();const [history,setHistory]=useState<Awaited<ReturnType<typeof qualityHistory>>>();const [historyPage,setHistoryPage]=useState(1);
  const [step,setStep]=useState<string>();const [form,setForm]=useState<Record<string,string>>({});const [key,setKey]=useState('');
  const [error,setError]=useState('');const [busy,setBusy]=useState(false);const [revision,setRevision]=useState(0);
  const can=(cap:string)=>permissions.includes('inventory.'+cap);
  const permissionKey=permissions.join('|');
  const fail=(cause:unknown)=>{setError(axios.isAxiosError(cause)?JSON.stringify(cause.response?.data?.error??'Connection unavailable; retry unchanged input if outcome is uncertain.'):'Unable to complete QC request.');};
  useEffect(()=>{let live=true;qualityMode().then(v=>{if(live)setMode(v);}).catch(fail);return()=>{live=false;};},[]);
  useEffect(()=>{setSelected(undefined);setHistory(undefined);setStep(undefined);},[user?.id,permissionKey]);
  useEffect(()=>{let live=true;setRows(undefined);if(mode?.synthetic_enabled&&can('view_qc'))qualityPage(resource,page).then(v=>{if(live)setRows(v);}).catch(fail);return()=>{live=false;};},[mode,resource,page,revision,user?.id,permissionKey]);
  function start(next:string,record?:QCRecord){setSelected(record);setStep(next);setHistory(undefined);setForm({reason:'',evidence_reference:''});setKey(crypto.randomUUID());setError('');}
  async function detail(record:QCRecord){setBusy(true);setStep(undefined);setHistory(undefined);try{setSelected(await qualityDetail(resource,record.id));}catch(cause){fail(cause);}finally{setBusy(false);}}
  async function showHistory(nextPage=1){if(!selected)return;try{setHistory(await qualityHistory(resource,selected.id,nextPage));setHistoryPage(nextPage);}catch(cause){fail(cause);}}
  async function submit(event:FormEvent){
    event.preventDefault();setBusy(true);setError('');
    try{
      const body:Record<string,unknown>={};for(const [field,value]of Object.entries(form)){if(value!=='')body[field]=['criteria','observations'].includes(field)?JSON.parse(value):['revision','balance_version','policy_version'].includes(field)?Number(value):value;}
      await qualityCommand(resource,body,key,selected,step===resource?undefined:step);
      setStep(undefined);setRevision(v=>v+1);if(selected)setSelected(await qualityDetail(resource,selected.id));
    }catch(cause){fail(cause);}finally{setBusy(false);}
  }
  if(!user?.backendSession)return <p>QC requires the existing authenticated backend session.</p>;
  return <section className="space-y-4"><h1 className="text-2xl font-semibold">Quality control foundation</h1>
    <p>{mode?.message??'Checking isolated QC availability…'}</p>
    <p>Inspection acceptance is evidence only. Release requires a separate successful, conserved ledger transition. Operational release is disabled.</p>
    <p>One whole physically identified root per inspection. Partial release within an indistinguishable lot, mixed custody and rejected-stock disposition are unavailable. NCR closure does not remove containment.</p>
    {!mode?.synthetic_enabled?<p role="status">QC workflows unavailable outside an authorized disposable test environment.</p>:!can('view_qc')?<p>QC view capability required.</p>:<>
      <nav className="flex flex-wrap gap-3">{(Object.keys(labels)as QCResource[]).map(r=><button key={r} onClick={()=>{setResource(r);setPage(1);setSelected(undefined);setStep(undefined);setHistory(undefined);}}>{labels[r]}</button>)}</nav>
      <h2>{labels[resource]}</h2>
      {resource!=='held-stock'&&can(createCaps[resource])&&<button onClick={()=>start(resource)}>Create {labels[resource]}</button>}
      {rows?<><p>{rows.count} persisted records</p><ul>{rows.results.map(row=><li key={row.id} className="border p-3"><button onClick={()=>detail(row)}>{String(row.reference??row.stock??row.id)}</button> · {String(row.status??row.decision??'Recorded evidence')} · {row.created_at}</li>)}</ul>
        <button disabled={!rows.previous} onClick={()=>setPage(v=>v-1)}>Previous</button><span> Page {page} </span><button disabled={!rows.next} onClick={()=>setPage(v=>v+1)}>Next</button></>:<p>Loading…</p>}
      {selected&&<article className="space-y-3 border p-3"><h3>Persisted detail: {selected.id}</h3><pre className="whitespace-pre-wrap break-all">{JSON.stringify(selected,null,2)}</pre>
        {(resource==='plans'?['publish']:resource==='inspections'?['review','release']:resource==='ncr'?['ncr_action']:[]).map(action=>(can(stepCaps[action])||action==='ncr_action'&&can('close_ncr'))&&<button disabled={busy} key={action} onClick={()=>start(action,selected)}>{action==='release'?'Request synthetic QC release':action==='ncr_action'?'Record NCR action':action}</button>)}
        {can('view_qc_history')&&resource!=='held-stock'&&<button onClick={()=>showHistory()}>Inspection / decision audit history</button>}
      </article>}
      {history&&<article><h3>Audit history</h3>{history.results.map(row=><div className="border p-3" key={row.id}><p>{row.action} · {row.actor} · {row.timestamp}</p><p>{row.reason}</p><pre className="whitespace-pre-wrap break-all">{JSON.stringify(row.summary,null,2)}</pre></div>)}<button disabled={!history.previous} onClick={()=>showHistory(historyPage-1)}>Previous events</button><button disabled={!history.next} onClick={()=>showHistory(historyPage+1)}>Next events</button></article>}
      {step&&<form onSubmit={submit} className="space-y-3 border p-3"><h3>{step}</h3>
        <p>Use controlled references and exact quantity strings. Criteria/results are structured JSON; no sample values or acceptance limits are prefilled.</p>
        {[...fields[step],'reason','evidence_reference'].map(field=><label className="block" key={field}>{field}<textarea className="block w-full border p-2" value={form[field]??''} onChange={event=>{setForm(v=>({...v,[field]:event.target.value}));setKey(crypto.randomUUID());}}/></label>)}
        {step==='ncr_action'&&<p>CLOSE additionally requires close_ncr capability and independent effectiveness evidence. Containment remains active.</p>}
        <button disabled={busy||step==='ncr_action'&&!can(form.kind==='CLOSE'?'close_ncr':'manage_ncr')}>Submit evidence to backend</button><button type="button" onClick={()=>setStep(undefined)}>Cancel</button>
      </form>}
    </>}{error&&<p role="alert" className="break-all text-red-700">{error}</p>}
  </section>;
}
