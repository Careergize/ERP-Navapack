import { useEffect, useRef, useState, type FormEvent } from 'react';
import axios from 'axios';
import { useAuth } from '@/context/AuthContext';
import { masterPage, masterSchema, masterDetail, saveMaster, type MasterRecord, type MasterField } from '@/lib/mastersApi';
import type { Page } from '@/lib/commercialApi';
import { InventoryFoundation } from '@/pages/Inventory/InventoryFoundation';
import { EmployeeManager } from './EmployeeManager';
import { GovernedImports } from './GovernedImports';
import { SpecificationRevision } from './SpecificationRevision';
import { api } from '@/lib/api';

const resources = [
  ['customers','Customers','masters.customer'], ['prospects','Prospects','masters.prospect'],
  ['suppliers','Suppliers','masters.supplier'], ['products','Products','masters.product'],
  ['finished-goods','Product variants','masters.productvariant'], ['raw-materials','Materials','masters.material'],
  ['consumables','Consumables','masters.consumable'], ['units','Units','masters.unit'],
  ['models','Product specifications','specifications.productmodel'], ['departments','Departments','masters.department'],
  ['machines','Machines','masters.machine'], ['areas','Areas','masters.area'],
] as const;
const immutable = new Set(['source_system','source_id','unit','product','dimension']);
const relations: Record<string, string> = {unit:'units',product:'products',department:'departments',area:'areas'};
const failure = (e: unknown) => axios.isAxiosError(e) ? `${e.response?.status === 412 ? 'Version conflict. Your fields are retained. Reload the saved record and reconcile before retrying.' : 'Backend request failed.'} ${JSON.stringify(e.response?.data?.error ?? 'Connection unavailable; retry unchanged intent.')}` : e instanceof Error ? e.message : 'Request failed.';

export function BackendMasters() {
  const { user } = useAuth(); const permissions = user?.permissions ?? [];
  const permitted = resources.filter(([, , model]) => permissions.includes(model.replace('.', '.view_')));
  const [resource, setResource] = useState<string>(permitted[0]?.[0] ?? '');
  const config = resources.find(([r]) => r === resource);
  const isImmutable = (field: string) => immutable.has(field) || resource === 'units' && field === 'code';
  const capability = (verb: string) => !!config && permissions.includes(config[2].replace('.', `.${verb}_`));
  const [data,setData] = useState<Page<MasterRecord>>(), [schema,setSchema] = useState<Record<string,MasterField>>({});
  const [page,setPage] = useState(1), [search,setSearch] = useState(''), [active,setActive] = useState('');
  const [record,setRecord] = useState<MasterRecord>(), [detail,setDetail] = useState<MasterRecord>();
  const [form,setForm] = useState<Record<string,string>>({}), [editing,setEditing] = useState(false);
  const [error,setError] = useState(''), [notice,setNotice] = useState(''), [busy,setBusy] = useState(false), [refresh,setRefresh] = useState(0);
  const [references,setReferences] = useState<Record<string, MasterRecord[]>>({});
  const [revisions,setRevisions] = useState<Page<MasterRecord>>(), [revisionPage,setRevisionPage] = useState(1);
  const intent = useRef<{body: string; key: string}>(); const lock = useRef(false);
  useEffect(() => { let live=true; setData(undefined); setError(''); setSchema({});
    if (!config || !capability('view')) return;
    Promise.all([masterPage(resource,page,search,active),masterSchema(resource)]).then(([rows,fields])=>{if(live){setData(rows);setSchema(fields);}}).catch(e=>{if(live)setError(failure(e));});
    return ()=>{live=false;};
  },[resource,page,search,active,refresh,user?.id]);
  useEffect(()=>{if(!editing)return; let live=true;
    Promise.all(Object.entries(relations).filter(([field,target])=>schema[field] && resources.some(([r,,m])=>r===target&&permissions.includes(m.replace('.', '.view_')))).map(async ([field,target])=>{
      const rows: MasterRecord[]=[];
      for(let p=1;;p++){const response=await masterPage(target,p,'','true');rows.push(...response.results);if(!response.next)break;}
      return [field,rows] as const;
    })).then(rows=>{if(live)setReferences(Object.fromEntries(rows));}).catch(e=>{if(live)setError(failure(e));});
    return()=>{live=false;};
  },[editing,resource,schema,user?.id]);
  useEffect(()=>{if(resource!=='models'||!detail)return;let live=true;
    if(!permissions.includes('specifications.view_productmodelrevision'))return;
    api.get<Page<MasterRecord>>(`/models/${detail.id}/revisions/`,{params:{page:revisionPage}}).then(r=>{if(live)setRevisions(r.data);}).catch(e=>{if(live)setError(failure(e));});return()=>{live=false;};
  },[resource,detail,revisionPage]);
  useEffect(()=>{if(!editing)return;const protect=(e:BeforeUnloadEvent)=>{e.preventDefault();e.returnValue='';};window.addEventListener('beforeunload',protect);return()=>window.removeEventListener('beforeunload',protect);},[editing]);
  function start(value?: MasterRecord){setRecord(value);setForm(Object.fromEntries(Object.entries(schema).filter(([,f])=>!f.read_only).map(([k,f])=>[k,value?.[k] == null ? f.type==='boolean' ? String(k==='is_active') : '' : typeof value[k]==='object'?JSON.stringify(value[k]):String(value[k])])));setEditing(true);setNotice('');intent.current=undefined;}
  function switchResource(next:string){if(editing&&!window.confirm('Discard unsaved master fields?'))return;setResource(next);setPage(1);setSearch('');setActive('');setEditing(false);setDetail(undefined);setRevisions(undefined);setNotice('');}
  async function save(e:FormEvent){e.preventDefault();if(lock.current)return;lock.current=true;setBusy(true);setError('');try{
    const body:Record<string,unknown>={};
    for(const [field,meta] of Object.entries(schema)){
      if(meta.read_only || record && isImmutable(field))continue;
      const value=form[field]??'';
      if(!record&&!value&&!meta.required)continue;
      if(record && String(record[field]??'')===value)continue;
      body[field]=meta.type==='boolean'?value==='true':meta.type==='json'?JSON.parse(value||'[]'):value===''&&meta.allow_null?null:value;
    }
    const serialized=JSON.stringify({resource,id:record?.id,version:record?.version,body});
    if(intent.current?.body!==serialized)intent.current={body:serialized,key:crypto.randomUUID()};
    const saved=await saveMaster(resource,body,intent.current.key,record);setDetail(saved);setEditing(false);setRefresh(v=>v+1);setNotice('Saved to PostgreSQL through the backend API.');
  }catch(e){setError(failure(e));}finally{lock.current=false;setBusy(false);}}
  return <section className="space-y-5"><h1 className="text-2xl font-semibold text-navy">Masters</h1><p>Persisted reference data · explicit capabilities · immutable units and source identities.</p>
    <nav className="flex flex-wrap gap-2" aria-label="Master data types">{permitted.map(([r,label])=><button className={`rounded-xl border px-3 py-2 ${resource===r?'bg-navy text-white':'bg-white'}`} key={r} onClick={()=>switchResource(r)}>{label}</button>)}{permissions.includes('inventory.view_warehouse')&&<button className="rounded border p-2" onClick={()=>switchResource('inventory')}>Warehouses / locations</button>}{user?.isMasterAdmin&&permissions.includes('accounts.view_employee')&&<button className="rounded border p-2" onClick={()=>switchResource('employees')}>Employees</button>}{permissions.includes('imports.view_importbatch')&&<button className="rounded border p-2" onClick={()=>switchResource('imports')}>Governed imports</button>}</nav>
    {resource==='employees'?<EmployeeManager/>:resource==='imports'?<GovernedImports/>:resource==='inventory'?<InventoryFoundation/>:!config?<p>No master view capabilities are assigned to this account.</p>:<>
    <h2 className="text-xl">{config[1]}</h2><div className="flex flex-wrap gap-3"><input className="rounded border p-2" aria-label="Search masters" placeholder="Search name / code / source" value={search} onChange={e=>{setSearch(e.target.value);setPage(1);}}/><select aria-label="Active filter" value={active} onChange={e=>{setActive(e.target.value);setPage(1);}}><option value="">All statuses</option><option value="true">Active</option><option value="false">Inactive</option></select><button disabled={busy} onClick={()=>setRefresh(v=>v+1)}>Refresh</button>{capability('add')&&<button className="rounded border p-2" disabled={!data||busy} onClick={()=>start()}>Create {config[1]}</button>}</div>
    {!data&&!error&&<p role="status">Loading persisted masters…</p>}{data&&<><p>{data.count} records · page {page}</p><div className="overflow-x-auto"><table className="w-full text-left"><thead><tr><th>Name</th><th>Code</th><th>Active</th><th>Version</th><th>Actions</th></tr></thead><tbody>{data.results.map(row=><tr className="border-b" key={row.id}><td>{row.name}</td><td>{row.code}</td><td>{row.is_active===false?'Inactive':'Active'}</td><td>{row.version}</td><td><button className="p-2 underline" onClick={()=>{masterDetail(resource,row.id).then(v=>{setDetail(v);setRevisionPage(1);}).catch(e=>setError(failure(e)));}}>Detail</button>{capability('change')&&<button className="p-2 underline" onClick={()=>start(row)}>Edit</button>}</td></tr>)}</tbody></table></div>{!data.count&&<p>No matching persisted records.</p>}<div className="flex gap-3"><button disabled={!data.previous||busy} onClick={()=>setPage(p=>p-1)}>Previous</button><button disabled={!data.next||busy} onClick={()=>setPage(p=>p+1)}>Next</button></div></>}
    {detail&&<details open className="rounded border bg-white p-4"><summary>Saved detail · {detail.name} · version {detail.version}</summary><dl>{Object.entries(detail).map(([k,v])=><div className="break-words py-1" key={k}><dt className="text-sm text-gray-500">{k.replaceAll('_',' ')}</dt><dd>{typeof v==='object'?JSON.stringify(v):String(v??'Unspecified')}</dd></div>)}</dl>{revisions&&<><h3>Immutable specification revisions</h3>{revisions.results.map(r=><details key={r.id}><summary>Revision {String(r.number)} · {r.name}</summary><pre className="overflow-auto whitespace-pre-wrap">{JSON.stringify(r,null,2)}</pre></details>)}<button disabled={!revisions.previous} onClick={()=>setRevisionPage(p=>p-1)}>Previous revisions</button><button disabled={!revisions.next} onClick={()=>setRevisionPage(p=>p+1)}>Next revisions</button></>}</details>}
    {resource==='models'&&detail&&permissions.includes('specifications.add_productmodelrevision')&&<SpecificationRevision key={`${detail.id}:${detail.version}`} model={detail} saved={()=>{masterDetail(resource,detail.id).then(setDetail).catch(e=>setError(failure(e)));setRefresh(v=>v+1);setNotice('Immutable specification revision saved.');}}/>}
    {editing&&<form data-dirty="true" onSubmit={save} className="rounded-xl border bg-white p-4 space-y-4"><h3>{record?'Edit':'Create'} {config[1]}</h3><div className="grid gap-3 md:grid-cols-2">{Object.entries(schema).filter(([,m])=>!m.read_only).map(([field,meta])=><label className="block" key={field}>{meta.label??field}{meta.required?' *':''}{meta.type==='boolean'?<input className="ml-2" type="checkbox" disabled={busy} checked={form[field]==='true'} onChange={e=>setForm({...form,[field]:String(e.target.checked)})}/>:meta.choices||references[field]?<select className="block w-full rounded border p-2" disabled={busy||!!record&&isImmutable(field)} value={form[field]??''} required={meta.required} onChange={e=>setForm({...form,[field]:e.target.value})}><option value="">Select…</option>{form[field]&&references[field]&&!references[field].some(r=>r.id===form[field])&&<option value={form[field]}>Retained reference {form[field]}</option>}{meta.choices?.map(c=><option key={c.value} value={c.value}>{c.display_name}</option>)}{references[field]?.map(r=><option key={r.id} value={r.id}>{r.name} {r.code}</option>)}</select>:<input className="block w-full rounded border p-2" disabled={busy||!!record&&isImmutable(field)} required={meta.required} maxLength={meta.max_length} type={meta.type==='email'?'email':'text'} inputMode={['decimal','integer'].includes(meta.type)?'decimal':undefined} value={form[field]??''} onChange={e=>setForm({...form,[field]:e.target.value})}/>}</label>)}</div><p>Amounts stay decimal strings. Unit, product, dimension and source identity changes require a new master.</p><button className="rounded border p-2" disabled={busy}>{busy?'Saving…':'Save to backend'}</button><button className="ml-3" type="button" disabled={busy} onClick={()=>{if(window.confirm('Discard unsaved master fields?'))setEditing(false);}}>Cancel</button></form>}
    </>}{error&&<p role="alert" className="break-words text-red-700">{error}</p>}{notice&&<p role="status">{notice}</p>}
  </section>;
}
