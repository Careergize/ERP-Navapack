import { useEffect, useRef, useState, type FormEvent } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import { allCommercialReferences, type CommercialRecord, type Page } from '@/lib/commercialApi';
import { inventoryPage, type InventoryRecord } from '@/lib/inventoryApi';
import { commandRehearsal, createRehearsal, productionStages, rehearsalDashboard, rehearsalHistory, rehearsalJob, rehearsalJobs, type RehearsalAction, type RehearsalJob, type RehearsalRevision } from '@/lib/rehearsalApi';
import { RehearsalInvoicePreview } from './RehearsalInvoicePreview';
const field = 'w-full rounded border p-2';
const showError = (e: unknown) => axios.isAxiosError(e) ? `${e.response?.status === 412 ? 'Version conflict. Reload the selected job before retrying; entered values are retained.' : e.response?.status === 403 ? 'Explicit permission, warehouse scope or approved DEMO/test database is unavailable.' : 'Request failed.'} ${JSON.stringify(e.response?.data ?? 'Check the backend connection.')}` : e instanceof Error ? e.message : 'Request failed.';
export function RehearsalWorkspace({title='Job Cards and Production',jobId}:{title?:string;jobId?:string}) {
  const { user } = useAuth();
  const [preview, setPreview] = useState(false), [dirty, setDirty] = useState(false);
  const [orders, setOrders] = useState<CommercialRecord[]>([]), [warehouses, setWarehouses] = useState<InventoryRecord[]>([]);
  const [purpose, setPurpose] = useState<'SALES_ORDER' | 'COSTING'>('SALES_ORDER');
  const [orderId, setOrderId] = useState(''), [warehouse, setWarehouse] = useState(''), [routes, setRoutes] = useState<string[][]>([]);
  const [jobs, setJobs] = useState<Page<RehearsalJob>>(), [page, setPage] = useState(1), [job, setJob] = useState<RehearsalJob>();
  const [history, setHistory] = useState<Page<RehearsalRevision>>(), [historyPage, setHistoryPage] = useState(1);
  const [dashboard, setDashboard] = useState<Record<string, unknown>>(), [error, setError] = useState(''), [busy, setBusy] = useState(false), [refresh, setRefresh] = useState(0);
  const [reason, setReason] = useState(''), [action, setAction] = useState<Exclude<RehearsalAction,'recycle'>>('review');
  const [line, setLine] = useState(0), [stage, setStage] = useState<string>('EXTRUSION');
  const [values, setValues] = useState({machine: 'synthetic:machine', operator: 'synthetic:operator', input_quantity: '', output_quantity: '', waste: '0', rejection: '0', remarks: '', quantity: '', available_quantity: '', outcome: 'PASS'});
  const lock = useRef(false), intent = useRef<{value: string; key: string}>();
  useEffect(()=>{if(!user?.backendSession||!jobId)return;let live=true;rehearsalJob(jobId).then(v=>{if(live)setJob(v);}).catch(e=>{if(live)setError(showError(e));});return()=>{live=false;};},[jobId,user?.id]);
  const selectedOrder = orders.find(o => o.id === orderId && o.kind === purpose);
  const permitted = user?.permissions?.includes('rehearsal.use_simulation');
  const actionAllowed = !job || (action === 'dispatch' && !job.sales_order_revision) ? false : ({review: ['DRAFT'], issue: ['REVIEWED'], start: ['ISSUED','PRODUCTION'], complete: ['ISSUED','PRODUCTION'], qc: ['PRODUCTION','QC_FAILED'], finish: ['QC_PASSED'], dispatch: ['FINISHED']}[action]).includes(job.status);
  const currentStage = job?.snapshot.routes.find(r => r.line === line)?.stages.find(s => s.name === stage);
  const productName = (item: Record<string, unknown>) => String((item.variant_snapshot as {name?: string} | undefined)?.name ?? item.variant ?? 'Unknown product');
  const sourceLines = (selectedOrder?.snapshot.input.lines ?? []) as Record<string, unknown>[];
  const key = (value: unknown) => { const serialized = JSON.stringify(value); if (intent.current?.value !== serialized) intent.current = {value: serialized, key: crypto.randomUUID()}; return intent.current.key; };
  useEffect(() => { if (!user?.backendSession) return; let live = true;
    Promise.allSettled([allCommercialReferences<CommercialRecord>('/commercial/documents/'), (async () => { const rows: InventoryRecord[] = []; for (let page = 1; ; page++) { const data = await inventoryPage('warehouses', '', '', page); rows.push(...data.results); if (!data.next) return rows; } })()]).then(results => {
      if (!live) return;
      if (results[0].status === 'fulfilled') setOrders(results[0].value.filter(o => ['SALES_ORDER','COSTING'].includes(o.kind) && o.status !== 'CANCELLED'));
      if (results[1].status === 'fulfilled') setWarehouses(results[1].value.filter(w => w.is_active !== false));
      const failure = results.find(r => r.status === 'rejected'); if (failure?.status === 'rejected') setError(showError(failure.reason));
    }); return () => { live = false; };
  }, [user?.backendSession]);
  useEffect(() => { if (!user?.backendSession) return; let live = true;
    rehearsalJobs(page).then(v => { if (live) setJobs(v); }).catch(e => { if (live) setError(showError(e)); });
    rehearsalDashboard().then(v => { if (live) setDashboard(v); }).catch(e => { if (live) setError(showError(e)); });
    return () => { live = false; };
  }, [user?.backendSession, page, refresh]);
  useEffect(() => { if (!job) return; let live = true; setHistory(undefined);
    rehearsalHistory(job.id, historyPage).then(v => { if (live) setHistory(v); }).catch(e => { if (live) setError(showError(e)); }); return () => { live = false; };
  }, [job, historyPage]);
  useEffect(() => { if (!job) return; const route = job.snapshot.routes.find(r => r.line === line) ?? job.snapshot.routes[0]; if (!route) return; setLine(route.line); if (!route.stages.some(s => s.name === stage)) setStage(route.stages[0]?.name ?? ''); }, [job, line, stage]);
  useEffect(() => { const protect = (e: BeforeUnloadEvent) => { if (dirty) { e.preventDefault(); e.returnValue = ''; } }; window.addEventListener('beforeunload', protect); return () => window.removeEventListener('beforeunload', protect); }, [dirty]);
  async function mutate(work: () => Promise<RehearsalJob>) { if (lock.current) return; lock.current = true; setBusy(true); setError('');
    try { setJob(await work()); setDirty(false); setHistoryPage(1); setRefresh(n => n + 1); intent.current = undefined; } catch (e) { setError(showError(e)); } finally { lock.current = false; setBusy(false); }
  }
  function create(e: FormEvent) { e.preventDefault(); if (!selectedOrder) return;
    const body = {...(purpose === 'COSTING' ? {costing_revision: selectedOrder.revision} : {sales_order_revision: selectedOrder.revision}), warehouse, routes: routes.map((stages, line) => ({line, stages})), reason};
    void mutate(() => createRehearsal(body, key(body)));
  }
  function execute(e: FormEvent) { e.preventDefault(); if (!job) return;
    const data: Record<string, unknown> = action === 'issue' ? {quantity: values.quantity, available_quantity: values.available_quantity} : action === 'qc' ? {outcome: values.outcome, remarks: values.remarks} : action === 'start' ? {line, stage, machine: values.machine, operator: values.operator, input_quantity: values.input_quantity, remarks: values.remarks} : action === 'complete' ? {line, stage, output_quantity: values.output_quantity, waste: values.waste, rejection: values.rejection, remarks: values.remarks} : {};
    void mutate(() => commandRehearsal(job, action, data, reason, key({id: job.id, version: job.version, action, data, reason})));
  }
  if (!user?.backendSession) return <div className="p-6"><h1>Development ERP journey</h1><p>Sign in with a real backend session. The separate legacy demo remains available in its existing screens.</p></div>;
  return <main className="p-4 md:p-6 space-y-5 max-w-6xl mx-auto">
    <h1 className="text-2xl font-semibold text-navy">{title}</h1>
    {!permitted && <p role="alert" className="rounded border border-amber-500 p-3">Your profile does not expose rehearsal.use_simulation. An explicit capability and warehouse scope are required; the backend enforces both.</p>}
    <div className="rounded border border-amber-400 bg-amber-50 p-4"><strong>SYNTHETIC SIMULATION — NO OPERATIONAL AUTHORITY</strong><p>Draft commercial demand links to immutable production rehearsal records in a guarded DEMO/test database. Review, material issue, QC, finished goods and dispatch here are synthetic events. No stock, operational QC release, financial posting or customer communication occurs.</p><p><Link className="underline" to="/sales-orders">Create customer-linked costings, quotations and multi-product sales order drafts in Commercial</Link>.</p></div>
    {error && <div role="alert" className="border border-red-500 rounded p-3 break-words">{error}</div>}
    {dashboard && <section className="border rounded p-4 space-y-2"><h2 className="text-lg font-semibold">Persisted commercial and production reports</h2>
      <div className="grid sm:grid-cols-3 gap-3">{Object.entries((dashboard.parties ?? {}) as Record<string, number | null>).map(([label, count]) => <p key={label}>{label}: {count ?? 'Read permission unavailable'}</p>)}
      {Object.entries(((dashboard.commercial as {counts?: Record<string, number>})?.counts ?? {})).map(([label, count]) => <p key={label}>Draft {label.replaceAll('_',' ')} documents: {count}</p>)}
      {Object.entries((dashboard.stages ?? {}) as Record<string, number>).map(([label, count]) => <p key={label}>Production stages {label}: {count}</p>)}
      {Object.entries((dashboard.estimated_cost_by_currency ?? {}) as Record<string, string>).map(([currency, amount]) => <p key={currency}>Current draft estimated production cost: {amount} {currency}</p>)}</div>
      {((dashboard.production_by_unit ?? []) as {unit: string; code: string; output_quantity: string; waste: string; rejection: string}[]).map(row => <p key={row.unit}>Synthetic final-stage output: {row.output_quantity} {row.code} · recorded stage waste: {row.waste} · rejection: {row.rejection}</p>)}
      <p>Output is a simulation metric, not available stock. Financial payable totals are unavailable. Operational inventory remains in the separate guarded inventory workspace.</p>
    </section>}
    <section className="border rounded p-4 space-y-2"><h2 className="text-lg font-semibold">Persisted simulation summary</h2>{dashboard ? <div className="grid grid-cols-2 md:grid-cols-4 gap-3"><div className="rounded bg-slate-50 p-3"><p className="text-2xl font-semibold">{String(dashboard.jobs ?? 0)}</p><p>Synthetic Job Cards</p></div>{Object.entries((dashboard.statuses ?? {}) as Record<string, number>).map(([status, count]) => <div className="rounded bg-slate-50 p-3" key={status}><p className="text-2xl font-semibold">{count}</p><p>{status.replaceAll('_',' ')}</p></div>)}</div> : <p>Loading simulation summary…</p>}</section>
    <form data-dirty={dirty} onChange={() => setDirty(true)} onSubmit={create} className="border rounded p-4 space-y-3"><h2 className="text-lg font-semibold">Create multi-line synthetic Job Card</h2>
      <label className="block">Production purpose<select className={field} value={purpose} onChange={e => { setPurpose(e.target.value as typeof purpose); setOrderId(''); setRoutes([]); }}><option value="SALES_ORDER">Sales order manufacturing demand</option><option value="COSTING">Production for stock from draft costing</option></select></label><p>Production-for-stock uses a retained costing revision without inventing customer demand; it ends at synthetic finished goods and cannot dispatch or invoice.</p><label className="block">Persisted {purpose === 'COSTING' ? 'costing source' : 'sales order demand'}<select className={field} required value={orderId} onChange={e => { setOrderId(e.target.value); const order = orders.find(o => o.id === e.target.value); setRoutes(((order?.snapshot.input.lines ?? []) as unknown[]).map(() => ['PACKING'])); }}><option value="">Select draft demand</option>{orders.filter(o => o.kind === purpose).map(o => <option key={o.id} value={o.id}>{o.id} · revision {o.version} · {o.status}</option>)}</select></label>
      <label className="block">Scoped warehouse<select className={field} required value={warehouse} onChange={e => setWarehouse(e.target.value)}><option value="">Select warehouse</option>{warehouses.map(w => <option key={w.id} value={w.id}>{w.code} {w.name}</option>)}</select></label>
      {!warehouses.length && <p>No permitted warehouse references loaded. Explicit warehouse access is required.</p>}
      {sourceLines.map((item, i) => <fieldset key={i} className="border rounded p-3"><legend>Demand line {i + 1} · {String(item.quantity ?? '')} · {productName(item)}</legend><p>Select only applicable stages; execution follows this manufacturing order.</p><div className="flex flex-wrap gap-4">{productionStages.map(s => <label key={s}><input type="checkbox" checked={routes[i]?.includes(s) ?? false} onChange={e => setRoutes(previous => previous.map((route, index) => index !== i ? route : productionStages.filter(name => name === s ? e.target.checked : route.includes(name))))}/> {s}</label>)}</div></fieldset>)}
      <label className="block">Reason / evidence<input className={field} required value={reason} onChange={e => setReason(e.target.value)}/></label><button className="rounded bg-blue-700 text-white px-4 py-2 disabled:opacity-50" disabled={busy || !permitted || !selectedOrder || !warehouse || routes.some(r => !r.length)}>Persist synthetic Job Card</button>
    </form>
    <section className="border rounded p-4 space-y-2"><h2 className="text-lg font-semibold">Saved synthetic Job Cards</h2>{!jobs ? <p>Loading…</p> : !jobs.results.length ? <p>No saved jobs.</p> : jobs.results.map(j => <button className="block underline break-all text-left" key={j.id} disabled={busy} onClick={() => { setJob(j); setHistoryPage(1); }}>{j.id} · {j.status} · v{j.version}</button>)}<div className="flex gap-4"><button disabled={page === 1 || busy} onClick={() => setPage(p => p - 1)}>Previous</button><span>Page {page}</span><button disabled={!jobs?.next || busy} onClick={() => setPage(p => p + 1)}>Next</button></div></section>
    {job && <section className="border rounded p-4 space-y-4"><h2 className="text-lg font-semibold">Synthetic job {job.id}</h2><p>{job.status} · version {job.version} · {job.sales_order_revision ? 'Sales order source revision' : 'Production-for-stock costing revision'} {job.sales_order_revision ?? job.costing_revision}</p><button className="underline" disabled={busy} onClick={() => void mutate(() => rehearsalJob(job.id))}>Reload latest version (retain entered fields)</button>
      <section className="border rounded p-3"><h3 className="font-semibold">Estimated material requirements</h3><p>Retained gross-consumption estimates from the source costing. No reservation or material issue is implied.</p>
        {((job.snapshot.material_requirements ?? []) as {line: number; material: string; quantity: string; unit: string}[]).map((item, index) => <p key={index}>Product line {item.line + 1} · material {item.material} · {item.quantity} · exact unit {item.unit}</p>)}
        {!((job.snapshot.material_requirements ?? []) as unknown[]).length && <p>No costing-linked material estimates are available for this source.</p>}
      </section>
      <div className="grid md:grid-cols-2 gap-3">{job.snapshot.routes.map(route => <div className="border rounded p-3" key={route.line}><h3>Line {route.line + 1}</h3><ol>{route.stages.map(s => <li className="border-t py-2" key={s.name}><strong>{s.name}: {s.status}</strong><p>Machine {String(s.machine ?? 'unassigned')} · Operator {String(s.operator ?? 'unassigned')}</p><p>Input {String(s.input_quantity ?? '—')} · Output {String(s.output_quantity ?? '—')} · Waste {String(s.waste ?? '—')} · Rejection {String(s.rejection ?? '—')}</p><p>Start {typeof s.started_at === 'string' ? new Date(s.started_at).toLocaleString() : 'pending'} · Complete {typeof s.completed_at === 'string' ? new Date(s.completed_at).toLocaleString() : 'pending'}</p>{!!s.remarks && <p>{String(s.remarks)}</p>}</li>)}</ol></div>)}</div>
      <section className="rounded bg-slate-50 p-3"><h3 className="font-semibold">Synthetic material and QC evidence</h3><p>Material issue: {job.snapshot.material_issue ? 'Recorded as scenario evidence; stock was not posted.' : 'Not recorded.'}</p>{job.snapshot.qc.length === 0 ? <p>No synthetic QC outcome recorded.</p> : job.snapshot.qc.map((entry, i) => { const q = entry as {outcome?: string; remarks?: string; at?: string; reinspection?: boolean}; return <p key={i}>{q.reinspection ? 'Reinspection' : 'Inspection'} {i + 1}: {q.outcome} · {q.at ? new Date(q.at).toLocaleString() : ''} · {q.remarks}</p>; })}</section><p>Progression requires synthetic review, sufficient synthetic material evidence, ordered stage completion, passing synthetic QC and finished-goods completion. Backend validation displays blocking reasons; failed QC blocks completion.</p>
      <form data-dirty={dirty} onChange={() => setDirty(true)} onSubmit={execute} className="space-y-3"><label className="block">Synthetic action<select className={field} value={action} onChange={e => setAction(e.target.value as Exclude<RehearsalAction,'recycle'>)}>{(['review','issue','start','complete','qc','finish','dispatch'] as RehearsalAction[]).map(a => <option key={a} value={a}>{a}</option>)}</select></label>
        {['start','complete'].includes(action) && <><div className="grid md:grid-cols-2 gap-3"><label>Demand line<select className={field} value={line} onChange={e => { const n = Number(e.target.value); setLine(n); setStage(job.snapshot.routes.find(r => r.line === n)?.stages[0]?.name ?? ''); }}>{job.snapshot.routes.map(r => <option key={r.line} value={r.line}>Line {r.line + 1}</option>)}</select></label><label>Stage<select className={field} value={stage} onChange={e => setStage(e.target.value)}>{job.snapshot.routes.find(r => r.line === line)?.stages.map(s => <option key={s.name} value={s.name}>{s.name}</option>)}</select></label></div><div className="grid md:grid-cols-2 gap-3">{(action === 'start' ? ['machine','operator','input_quantity'] as const : ['output_quantity','waste','rejection'] as const).map(name => <label key={name}>{name.replaceAll('_',' ')}<input className={field} value={values[name]} required onChange={e => setValues(v => ({...v, [name]: e.target.value}))}/></label>)}</div><p>Recorded stage input: {String(currentStage?.input_quantity ?? 'Not started')} · Machine: {String(currentStage?.machine ?? 'Unassigned')} · Operator: {String(currentStage?.operator ?? 'Unassigned')}</p><p>Times are recorded by the server when commands succeed. Decimal quantities remain exact strings.</p></>}
        {action === 'issue' && <div className="grid md:grid-cols-2 gap-3">{(['available_quantity','quantity'] as const).map(name => <label key={name}>Synthetic {name.replaceAll('_',' ')} (scenario quantity only)<input className={field} required value={values[name]} onChange={e => setValues(v => ({...v, [name]: e.target.value}))}/></label>)}</div>}
        {action === 'qc' && <label className="block">Synthetic inspection outcome<select className={field} value={values.outcome} onChange={e => setValues(v => ({...v, outcome: e.target.value}))}><option>PASS</option><option>FAIL</option></select></label>}
        <label className="block">Remarks<textarea maxLength={500} className={field} value={values.remarks} onChange={e => setValues(v => ({...v, remarks: e.target.value}))}/></label><label className="block">Command reason<input required maxLength={500} className={field} value={reason} onChange={e => setReason(e.target.value)}/></label>{!actionAllowed && <p role="status">Blocked: {action} is unavailable while this job is {job.status}. Complete the preceding synthetic workflow step.</p>}<button className="rounded bg-blue-700 text-white px-4 py-2 disabled:opacity-50" disabled={busy || !actionAllowed || !permitted}>Persist synthetic {action}</button>
      </form>
      <details><summary>Immutable source mapping, material issue, QC and event history</summary><pre className="whitespace-pre-wrap break-words text-sm">{JSON.stringify(job.snapshot, null, 2)}</pre></details>
      <section className="border border-amber-400 p-3"><h3 className="font-semibold">DEVELOPMENT PREVIEW — NOT APPROVED FOR CUSTOMER ISSUE</h3>{job.status === 'DISPATCHED' && job.sales_order_revision ? <><p>Synthetic invoice example · no legal invoice number or financial posting.</p><button className="underline" onClick={() => setPreview(true)}>Open invoice preview / save draft PDF</button><p>Currency: {job.invoice_preview?.currency ?? 'Unavailable'} · Net estimate: {job.invoice_preview?.net_estimate ?? 'Unavailable'}</p></> : <p>{job.sales_order_revision ? 'Invoice example is blocked until synthetic dispatch completes.' : 'Production-for-stock does not support dispatch or invoice previews.'}</p>}<p>VAT: unavailable · LED: unavailable · Final payable: unavailable pending verified policies.</p></section>
      <h3 className="font-semibold">Append-only revision history</h3>{history?.results.map((h, i) => <details key={h.id ?? i}><summary>Revision {h.number} · {h.at} · {h.reason}</summary><pre className="whitespace-pre-wrap break-words text-sm">{JSON.stringify(h, null, 2)}</pre></details>)}<div className="flex gap-4"><button disabled={historyPage === 1 || busy} onClick={() => setHistoryPage(p => p - 1)}>Previous history</button><button disabled={!history?.next || busy} onClick={() => setHistoryPage(p => p + 1)}>Next history</button></div>
    </section>}
    {preview && job && <RehearsalInvoicePreview job={job} close={() => setPreview(false)}/>}
  </main>;
}





