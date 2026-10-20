import { QualityFoundation } from './QualityFoundation';
import { FormEvent, useEffect, useState } from 'react';
import axios from 'axios';
import { InventoryOperations } from './InventoryOperations';
import { useAuth } from '@/context/AuthContext';
import { inventoryPage, inventoryHistory, saveInventory, type InventoryRecord, type InventoryPage, type InventoryAudit, type Resource } from '@/lib/inventoryApi';

const labels: Record<Resource,string> = {warehouses:'Warehouse Management', locations:'Storage Location Management', identities:'Stock Identity / Lot References'};
export function InventoryFoundation() {
  const [operations,setOperations]=useState(false);
  const [quality,setQuality]=useState(false);
  const {user} = useAuth();
  const [resource,setResource] = useState<Resource>('warehouses');
  const [search,setSearch] = useState(''); const [warehouse,setWarehouse] = useState('');
  const [page,setPage] = useState(1); const [data,setData] = useState<InventoryPage>();
  const [error,setError] = useState(''); const [loading,setLoading] = useState(false);
  const [revision,setRevision] = useState(0); const [record,setRecord] = useState<InventoryRecord>();
  const [editing,setEditing] = useState(false); const [form,setForm] = useState<Record<string,string>>({});
  const [key,setKey] = useState(''); const [saving,setSaving] = useState(false);
  const [historyRecord,setHistoryRecord]=useState<InventoryRecord>(); const [historyPage,setHistoryPage]=useState(1);
  const [history,setHistory]=useState<{count:number;next:string|null;previous:string|null;results:InventoryAudit[]}>();
  const permissions=user?.permissions ?? [];
  const model=resource==='warehouses'?'warehouse':resource==='locations'?'storagelocation':'stockidentity';
  const readable=permissions.includes(`inventory.view_${model}`);
  const writable=resource==='warehouses'?permissions.includes('inventory.configure_warehouses'):
    permissions.includes(`inventory.${record?'change':'add'}_${model}`);
  useEffect(()=>{
    let current=true;setHistory(undefined);
    if(historyRecord)inventoryHistory(historyRecord,historyPage).then(value=>{if(current)setHistory(value);}).catch(cause=>{if(current)setError(message(cause));});
    return ()=>{current=false;};
  },[historyRecord,historyPage]);
  useEffect(() => {
    let current=true; setData(undefined); setError(''); setLoading(false);
    if (!user?.backendSession || !readable) return;
    setLoading(true);
    inventoryPage(resource,search,warehouse,page).then(value=>{if(current)setData(value);})
      .catch(cause=>{if(current)setError(message(cause));}).finally(()=>{if(current)setLoading(false);});
    return ()=>{current=false;};
  },[resource,search,warehouse,page,revision,readable,user?.backendSession]);
  function message(cause: unknown) {
    if (!axios.isAxiosError(cause)) return 'Unable to complete the request.';
    const e=cause.response?.data?.error;
    return e ? `${e.message} ${JSON.stringify(e.fields ?? {})} (request ${e.request_id})` : 'Connection unavailable. Retry the same unchanged request if its outcome is uncertain.';
  }
  function edit(value?: InventoryRecord) {
    setRecord(value); setForm(value?{code:value.code??'',name:value.name??'',description:value.description??'',
      warehouse:value.warehouse??'',custody_department:value.custody_department??'',parent:value.parent??'',classification:value.classification??'',is_active:String(value.is_active),reason:''}:
      {code:'',name:'',description:'',warehouse:'',parent:'',classification:'',is_active:'true',reason:''});
    setKey(crypto.randomUUID());setEditing(true);setError('');
  }
  async function submit(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError('');
    const body: Record<string,unknown>={code:form.code,name:form.name,is_active:form.is_active==='true',reason:form.reason};
    if(resource==='warehouses'){body.description=form.description;body.custody_department=form.custody_department||null;}
    else {body.classification=form.classification;body.parent=form.parent||null;if(!record)body.warehouse=form.warehouse;}
    try {await saveInventory(resource,body,key,record);setEditing(false);setRevision(n=>n+1);}
    catch(cause){setError(message(cause));} finally{setSaving(false);}
  }
  if(!user?.backendSession)return <p>Inventory configuration requires a real authenticated backend session.</p>;
  return <section className="space-y-5">
    <nav className="flex gap-3"><button onClick={()=>{setOperations(false);setQuality(false);}}>Configuration</button><button onClick={()=>{setOperations(true);setQuality(false);}}>Inventory workflows / Opening Stock</button><button onClick={()=>setQuality(true)}>Quality control / NCR</button></nav>
    {quality?<QualityFoundation/>:operations?<InventoryOperations/>:<>
    <h1 className="text-2xl font-semibold">Inventory foundation</h1>
    <p>Configuration and identity references only. Workflow evidence is separate; operational stock posting and QC release remain unavailable.</p>
    <nav className="flex flex-wrap gap-3" aria-label="Inventory configuration">{(Object.keys(labels) as Resource[]).map(r=><button className="rounded border bg-white p-3" key={r} onClick={()=>{setResource(r);setPage(1);setEditing(false);setRecord(undefined);setHistoryRecord(undefined);}}>{labels[r]}</button>)}</nav>
    <h2 className="text-xl">{labels[resource]}</h2>
    {!readable?<p>You do not have the required view capability.</p>:<>
      <div className="flex flex-wrap gap-3"><input aria-label="Search records" className="rounded border p-2" value={search} placeholder="Search" onChange={e=>{setSearch(e.target.value);setPage(1);}}/>
      {resource!=='warehouses'&&<input aria-label="Filter warehouse UUID" className="rounded border p-2" value={warehouse} placeholder="Warehouse UUID filter" onChange={e=>{setWarehouse(e.target.value);setPage(1);}}/>}
      <button className="rounded border p-2" onClick={()=>setRevision(n=>n+1)}>Refresh</button>
      {resource!=='identities'&&writable&&<button className="rounded border p-2" onClick={()=>edit()}>Create</button>}</div>
      <p>Results are limited to your approved warehouse scopes. Admin status grants no automatic scope. Scope assignment publication is pending controlled provisioning; empty results do not mean stock is zero.</p>
      {loading&&<p role="status">Loading persisted records…</p>}
      {data&&<><p>{data.count} matching records</p><ul className="space-y-3">{data.results.map(row=><li key={row.id} className="rounded border bg-white p-4">
        <p className="font-medium">{row.code??row.reference} {row.name}</p><p className="break-all text-sm">UUID: {row.id} · version {row.version}</p>
        {permissions.includes('inventory.view_inventory_audit')&&<button className="rounded border p-2" onClick={()=>{setHistoryRecord(row);setHistoryPage(1);}}>View change history</button>}
        {resource==='identities'?<><p>{row.kind} · ownership {row.ownership} · {row.lifecycle}</p><p className="break-all">Item: {row.material??row.variant??row.consumable} · unit {row.unit}</p><p className="break-all">Warehouse {row.warehouse} · parent {row.parent??'none'} · physical mark {row.physical_reference||'unidentified'}</p><p className="break-all">Source {row.source_system}: {row.source_reference} · document {row.source_document_reference||'unrecorded'} · supplier batch {row.supplier_batch||'unrecorded'}</p><p className="break-all">Owner reference {row.owner_customer??row.owner_supplier??row.ownership_evidence??'unresolved'}</p><p>{row.operational_status}</p></>:
        <><p>{row.is_active?'Active':'Inactive'} {row.classification} {row.parent&&`· parent ${row.parent}`}</p>{(resource==='warehouses'?permissions.includes('inventory.configure_warehouses'):permissions.includes('inventory.change_storagelocation'))&&<button className="mt-2 rounded border p-2" onClick={()=>edit(row)}>Edit metadata / activation</button>}</>}
      </li>)}</ul><div className="flex gap-3"><button disabled={!data.previous} onClick={()=>setPage(n=>n-1)}>Previous</button><span>Page {page}</span><button disabled={!data.next} onClick={()=>setPage(n=>n+1)}>Next</button></div></>}
    </>}
    {error&&<p role="alert" className="break-all text-red-700">{error}</p>}
    {historyRecord&&<section className="space-y-3 rounded border bg-white p-4"><h3>Change history: {historyRecord.code??historyRecord.reference}</h3>
      <button onClick={()=>setHistoryRecord(undefined)}>Close history</button>
      {!history?<p role="status">Loading history…</p>:<><p>{history.count} events</p>{history.results.map(event=>{
        const before=event.summary.outcome?.before;const after=event.summary.outcome?.after??{};
        return <article className="rounded border p-3" key={event.id}><p>{event.action} · {new Date(event.timestamp).toLocaleString()}</p><p>Actor {event.actor} · {event.reason}</p>
          <dl>{Object.entries(after).filter(([field,value])=>!['created_at','updated_at','version'].includes(field)&&JSON.stringify(before?.[field])!==JSON.stringify(value)).map(([field,value])=><div className="break-all" key={field}><dt className="font-medium">{field}</dt><dd>{before?JSON.stringify(before[field]):'Not previously registered'} → {JSON.stringify(value)}</dd></div>)}</dl></article>;
      })}<div className="flex gap-3"><button disabled={!history.previous} onClick={()=>setHistoryPage(n=>n-1)}>Previous events</button><span>Page {historyPage}</span><button disabled={!history.next} onClick={()=>setHistoryPage(n=>n+1)}>Next events</button></div></>}
    </section>}
    {editing&&resource!=='identities'&&<form className="space-y-3 rounded border bg-white p-4" onSubmit={submit}>
      <h3>{record?'Edit persisted record':'Create record'}</h3>
      {(resource==='warehouses'?['code','name','description','custody_department','reason']:record?['code','name','parent','classification','reason']:['code','name','warehouse','parent','classification','reason']).map(field=><label className="block" key={field}>{field==='parent'?'Parent location UUID (optional)':field==='warehouse'?'Warehouse UUID':field==='custody_department'?'Stores department UUID (optional; unresolved if blank)':field}<input className="ml-3 rounded border p-2" disabled={saving} required={['code','name','warehouse','reason'].includes(field)} value={form[field]??''} onChange={e=>{setForm({...form,[field]:e.target.value});setKey(crypto.randomUUID());}}/></label>)}
      <label className="block">Active <input type="checkbox" disabled={saving} checked={form.is_active==='true'} onChange={e=>{setForm({...form,is_active:String(e.target.checked)});setKey(crypto.randomUUID());}}/></label>
      <p>Changes need current capabilities, warehouse scope and record version. Repeated unchanged submissions reuse the request key. A version conflict requires refreshing and reviewing the record.</p>
      <button className="rounded border p-2" disabled={saving||!writable}>{saving?'Saving…':'Save to backend'}</button><button type="button" className="ml-3 rounded border p-2" disabled={saving} onClick={()=>setEditing(false)}>Cancel</button>
    </form>}
    </>}
  </section>;
}
