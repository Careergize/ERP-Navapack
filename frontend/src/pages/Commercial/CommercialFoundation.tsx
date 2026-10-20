import { FormEvent, useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { useAuth } from '@/context/AuthContext';
import { commercialPage, commercialHistory, saveCommercial, transitionCommercial, allCommercialReferences, type CommercialReference, type CostingReference, type CommercialRecord, type CommercialKind, type CommercialHistory, type Page } from '@/lib/commercialApi';
import { newCommercialInput, newLine, newMaterial, newProcess, editableCommercialInput, compareCommercial, type CommercialInput, type CommercialLine, type CostingInput } from '@/lib/commercialEditor';
import { CommercialSnapshot } from './CommercialSnapshot';
import { CommercialPolicyRegistry } from './CommercialPolicyRegistry';
import { DraftPreview } from './DraftPreview';
import { QuickCustomer } from './QuickCustomer';
import { deriveCommercial } from '@/lib/commercialApi';
import { Link } from 'react-router-dom';
const css = 'rounded border p-2 w-full';
const message = (e: unknown) => axios.isAxiosError(e) ? `${e.response?.status === 412 ? 'Stale version: reload the record; entered draft retained.' : e.response?.status === 403 ? 'Permission or approved DEMO/test environment unavailable.' : 'Request failed.'} ${JSON.stringify(e.response?.data?.error ?? 'Connection failed. Retry unchanged intent safely.')}` : e instanceof Error ? e.message : 'Request failed.';
export function CommercialFoundation() {
  const { user } = useAuth(); const allowed = !!user?.backendSession && !!user.permissions?.includes('commercial.use_foundation');
  const [kind, setKind] = useState<CommercialKind>('QUOTATION'), [draft, setDraft] = useState<CommercialInput>(newCommercialInput());
  const [party, setParty] = useState<'customer'|'prospect'|'none'>('customer');
  const [masters, setMasters] = useState<Record<string, CommercialReference[]>>({}), [costings, setCostings] = useState<CostingReference[]>([]);
  const [records, setRecords] = useState<Page<CommercialRecord>>(), [page, setPage] = useState(1), [refresh, setRefresh] = useState(0);
  const [selected, setSelected] = useState<CommercialRecord>(), [editing, setEditing] = useState<CommercialRecord>();
  const [history, setHistory] = useState<Page<CommercialHistory>>(), [historyPage, setHistoryPage] = useState(1), [compare, setCompare] = useState<CommercialHistory>();
  const [reason, setReason] = useState(''), [error, setError] = useState(''), [refError, setRefError] = useState(''), [busy, setBusy] = useState(false);
  const [preview, setPreview] = useState<CommercialRecord>();
  const [dirty, setDirty] = useState(false);
  const commandLock = useRef(false);
  const intent = useRef<{ value: string; key: string }>();
  useEffect(() => {
    if (!dirty) return;
    const protect = (e: BeforeUnloadEvent) => { e.preventDefault(); e.returnValue = ''; };
    window.addEventListener('beforeunload', protect);
    return () => window.removeEventListener('beforeunload', protect);
  }, [dirty]);
  useEffect(() => { if (!allowed) return; let live = true;
    commercialPage(page).then(d => { if (live) setRecords(d); }).catch(e => { if (live) setError(message(e)); }); return () => { live = false; };
  }, [allowed, page, refresh]);
  useEffect(() => { if (!allowed) return; let live = true; setRefError('');
    const refs = [['customers','/customers/','masters.view_customer'],['prospects','/prospects/','masters.view_prospect'],['variants','/finished-goods/','masters.view_productvariant'],['materials','/raw-materials/','masters.view_material'],['units','/units/','masters.view_unit'],['models','/model-revisions/','specifications.view_productmodelrevision'],['marketing','/commercial/references/marketing-people/','accounts.view_employee']];
    Promise.allSettled(refs.filter(([, , p]) => user?.permissions?.includes(p)).map(async ([name, url]) => [name, await allCommercialReferences<CommercialReference>(url)] as const)).then(results => {
      if (!live) return; setMasters(Object.fromEntries(results.flatMap(r => r.status === 'fulfilled' ? [r.value] : [])));
      if (results.some(r => r.status === 'rejected')) setRefError('Some permitted reference lists failed. Existing selections remain retained; reload before replacing them.');
    });
    allCommercialReferences<CostingReference>('/commercial/references/costing-revisions/').then(d => { if (live) setCostings(d); }).catch(e => { if (live) setRefError(message(e)); });
    return () => { live = false; };
  }, [allowed, refresh, user?.permissions]);
  useEffect(() => { setHistory(undefined); setCompare(undefined); if (!selected) return; let live = true;
    commercialHistory(selected.id, historyPage).then(d => { if (live) setHistory(d); }).catch(e => { if (live) setError(message(e)); }); return () => { live = false; };
  }, [selected, historyPage]);
  function key(value: unknown) { const text = JSON.stringify(value); if (intent.current?.value !== text) intent.current = { value: text, key: crypto.randomUUID() }; return intent.current.key; }
  const line = (i: number, value: CommercialLine) => setDraft(d => ({ ...d, lines: d.lines.map((l, j) => i === j ? value : l) }));
  const cost = (i: number, value: CostingInput) => setDraft(d => ({ ...d, lines: d.lines.map((l, j) => i === j ? { ...l, costing: value } : l) }));
  function reset(type = kind) { if (dirty && !window.confirm('Discard unsaved draft fields?')) return; setDirty(false); setKind(type); setEditing(undefined); setDraft(newCommercialInput(type === 'COSTING')); setParty(type === 'COSTING' ? 'none' : 'customer'); setReason(''); intent.current = undefined; }
  async function save(e: FormEvent) { e.preventDefault(); if (commandLock.current) return; commandLock.current = true; setBusy(true); setError(''); try {
    const r = await saveCommercial(kind, draft, reason, key({ kind, draft, reason, id: editing?.id, version: editing?.version }), editing);
    setDirty(false); setSelected(r); setHistoryPage(1); if (editing) setEditing(r); setRefresh(n => n + 1);
  } catch (e) { setError(message(e)); } finally { commandLock.current = false; setBusy(false); } }
  function edit() { if (!selected || selected.status !== 'DRAFT') return; try {
    if (dirty && !window.confirm('Replace unsaved fields with this saved revision?')) return;
    const d = editableCommercialInput(selected.snapshot.input); setDraft(d); setDirty(false); setKind(selected.kind); setParty(d.customer ? 'customer' : d.prospect ? 'prospect' : 'none'); setEditing(selected); setError('');
  } catch (e) { setError(message(e)); } }
  async function transition(action: 'submit'|'reopen'|'cancel') { if (!selected || commandLock.current) return; commandLock.current = true; setBusy(true); setError(''); try {
    const r = await transitionCommercial(selected, action, reason, key({ id: selected.id, version: selected.version, action, reason })); setSelected(r); if (editing?.id === r.id) setEditing(undefined); setRefresh(n => n + 1);
  } catch (e) { setError(message(e)); } finally { commandLock.current = false; setBusy(false); } }
  async function derive() { if (!selected || commandLock.current) return; commandLock.current = true; setBusy(true); setError(''); try {
    const r = await deriveCommercial(selected, reason, key({ source: selected.revision, reason, action: 'derive' }));
    setSelected(r); setHistoryPage(1); setRefresh(n => n + 1);
  } catch (e) { setError(message(e)); } finally { commandLock.current = false; setBusy(false); } }
  const options = (resource: string, value?: string, filter?: (m: CommercialReference) => boolean) => <><option value="">Unspecified / select…</option>{value && !masters[resource]?.some(m => m.id === value) && <option value={value}>Retained selection (not in current directory)</option>}{masters[resource]?.filter(filter ?? (() => true)).map(m => <option key={m.id} value={m.id}>{m.name}{m.number ? ` · revision ${m.number}` : ''}{m.code ? ` (${m.code})` : ''}</option>)}</>;
  const unit = (id: string) => { const u = masters.units?.find(u => u.id === id); return u ? `${u.name} (${u.code || 'no code'})` : 'Retained unit / unavailable in directory'; };
  const text = (label: string, value: string, change: (v: string) => void, required = false, type = 'text') => <label>{label}<input className={css} type={type} required={required} value={value} onChange={e => change(e.target.value)}/></label>;
  if (!allowed) return <main className="p-6"><h1>Commercial foundation</h1><p>Unavailable: a backend employee session and explicit commercial capability are required.</p></main>;
  const diffs = selected && compare ? compareCommercial(compare.snapshot, selected.snapshot) : [];
  return <main className="max-w-6xl p-6 space-y-6"><h1 className="text-2xl font-semibold">Commercial foundation</h1>
    <p>Isolated DEMO/test environment only. Save costing → derive draft quotation → derive draft Sales Order demand → <Link className="underline" to="/rehearsal">synthetic production rehearsal</Link>. Draft derivation never approves a quote or confirms an order. VAT, LED, final payable and customer issue/email remain unavailable. Orders never reserve or deduct stock.</p>
    {preview && <DraftPreview record={preview} close={() => setPreview(undefined)}/>}
    {records && user?.permissions?.includes('masters.add_customer') && <QuickCustomer saved={id => { setDraft(d => ({ ...d, customer: id })); setParty('customer'); setRefresh(n => n + 1); }}/ >}
    {error && <p role="alert" className="text-red-700">{error}</p>}{refError && <p role="alert">{refError}</p>}
    <button className={css} disabled={busy} onClick={() => { setError(''); setRefresh(n => n + 1); }}>Reload records and permitted references</button>
    {!records ? <p role="status">{error ? 'Commercial persistence unavailable; forms blocked.' : 'Checking commercial persistence…'}</p> : <>
    <section className="space-y-2"><h2 className="text-xl font-semibold">Saved documents</h2>{!records.count && <p>No saved documents.</p>}
      {records.results.map(r => <button className={css} key={r.id} onClick={() => { setSelected(r); setHistoryPage(1); }}>{r.kind} · {r.status} · revision {r.version} · {r.snapshot.estimate.net_estimate} {String(r.snapshot.input.currency)}</button>)}
      <button disabled={page === 1} onClick={() => setPage(n => n - 1)}>Previous</button> · <button disabled={!records.next} onClick={() => setPage(n => n + 1)}>Next</button></section>
    {selected && <section className="border rounded p-4 space-y-3"><h2>{selected.kind} · {selected.status} · revision {selected.version}</h2><CommercialSnapshot snapshot={selected.snapshot}/>
      <p className="break-all">Document: {selected.id} · immutable revision: {selected.revision}</p>
      <button disabled={busy} onClick={() => setPreview(selected)}>Draft PDF preview</button>
      {selected.kind !== 'SALES_ORDER' && selected.status !== 'CANCELLED' && <button className="ml-4" disabled={busy || !reason.trim()} onClick={derive}>Derive unapproved {selected.kind === 'COSTING' ? 'quotation' : 'Sales Order demand'} draft</button>}
      {text('Change reason', reason, setReason)}
      {selected.status === 'DRAFT' && <><button disabled={busy} onClick={edit}>Edit draft below</button> · <button disabled={busy || !reason.trim()} onClick={() => transition('submit')}>Submit for review</button> · <button disabled={busy || !reason.trim()} onClick={() => transition('cancel')}>Cancel draft</button></>}
      {selected.status === 'REVIEW' && <button disabled={busy || !reason.trim()} onClick={() => transition('reopen')}>Return to draft</button>}
      <h3>Immutable revisions and audit history</h3>{!history && <p>Loading history…</p>}{history?.results.map(r => <details key={r.id}><summary>Revision {r.number} · {r.status} · {r.at} · {r.reason}</summary><p>Actor reference: {r.actor}. Audit request: {r.audit?.request_id ?? 'Historical link unavailable'}.</p><CommercialSnapshot snapshot={r.snapshot}/><button onClick={() => setCompare(r)}>Compare with current revision</button></details>)}
      <button disabled={historyPage === 1} onClick={() => setHistoryPage(n => n - 1)}>Previous history</button> · <button disabled={!history?.next} onClick={() => setHistoryPage(n => n + 1)}>Next history</button>
      {compare && <div><h3>Revision {compare.number} → {selected.version}: {diffs.length} changed values</h3>{!diffs.length && <p>No snapshot differences; status/reason history may differ.</p>}<ul>{diffs.slice(0, 200).map((d, i) => <li key={i} className="break-words">{d.field}: {d.before} → {d.after}</li>)}</ul>{diffs.length > 200 && <p>First 200 changes shown; full snapshots remain available above.</p>}</div>}
    </section>}
    <form onSubmit={save} onChangeCapture={() => setDirty(true)} className="border rounded p-4 space-y-4"><h2 className="text-xl font-semibold">{editing ? `Edit revision ${editing.version}` : 'New draft'}</h2>{dirty && <p role="status">Unsaved draft fields. Save before leaving this workspace.</p>}<button type="button" disabled={busy} onClick={() => reset()}>Start a new draft</button>
      <div className="grid md:grid-cols-3 gap-3"><label>Document<select className={css} disabled={!!editing} value={kind} onChange={e => { if (draft.lines.some(l => l.variant || l.quantity)) { setError('Start a new draft before changing type. Entered data is retained.'); return; } reset(e.target.value as CommercialKind); }}><option value="COSTING">Costing</option><option value="QUOTATION">Quotation</option><option value="SALES_ORDER">Sales order</option></select></label>
      <label>Party type<select className={css} value={party} onChange={e => { setParty(e.target.value as typeof party); setDraft(d => { const n = { ...d }; delete n.customer; delete n.prospect; return n; }); }}><option value="customer">Existing customer</option>{kind !== 'SALES_ORDER' && <option value="prospect">Prospect</option>}{kind === 'COSTING' && <option value="none">No customer (product costing)</option>}</select></label>
      {party !== 'none' && <label>Customer / prospect<select className={css} required value={draft[party] ?? ''} onChange={e => setDraft(d => ({ ...d, [party]: e.target.value }))}>{options(party === 'customer' ? 'customers' : 'prospects', draft[party])}</select></label>}
      <label>Classification<select className={css} value={draft.classification ?? ''} onChange={e => setDraft(d => { const n = { ...d }; if (e.target.value) n.classification = e.target.value; else delete n.classification; return n; })}><option value="">Unspecified</option><option>B2B</option><option>B2C</option></select></label>
      <label>Marketing person<select className={css} value={draft.marketing_person ?? ''} onChange={e => setDraft(d => { const n = { ...d }; if (e.target.value) n.marketing_person = e.target.value; else delete n.marketing_person; return n; })}>{options('marketing', draft.marketing_person)}</select><small>Only permitted employee references are listed.</small></label>
      <label>Currency<select className={css} required value={draft.currency} onChange={e => setDraft(d => ({ ...d, currency: e.target.value }))}><option value="">Select…</option><option>UGX</option><option>USD</option></select><small>Changing currency never converts component prices.</small></label>
      <label>Monetary decimals<select className={css} value={draft.money_places} onChange={e => setDraft(d => ({ ...d, money_places: Number(e.target.value) }))}><option value={0}>0</option><option value={2}>2</option></select></label>
      <label>Rounding<select className={css} value={draft.rounding} onChange={e => setDraft(d => ({ ...d, rounding: e.target.value }))}><option>HALF_UP</option><option>HALF_EVEN</option></select></label>
      {text('Net discount', draft.discount, v => setDraft(d => ({ ...d, discount: v })), true)}
      {(['requested_delivery','validity_date'] as const).map(f => <div key={f}>{text(f === 'requested_delivery' ? 'Requested delivery' : 'Entered validity date', draft[f] ?? '', v => setDraft(d => { const n = { ...d }; if (v) n[f] = v; else delete n[f]; return n; }), false, 'date')}</div>)}
      </div>
      {draft.lines.map((l, i) => <fieldset key={i} className="border rounded p-3 space-y-3"><legend>Product {i+1}</legend><div className="grid md:grid-cols-3 gap-3">
        <label>Variant<select className={css} required value={l.variant} onChange={e => line(i, { ...l, variant: e.target.value, unit: masters.variants?.find(v => v.id === e.target.value)?.unit ?? '' })}>{options('variants', l.variant)}</select><small>Native unit: {unit(l.unit)}</small></label>
        <label>Specification revision<select className={css} value={l.model_revision ?? ''} onChange={e => { const n = { ...l }; if (e.target.value) n.model_revision = e.target.value; else delete n.model_revision; line(i, n); }}>{options('models', l.model_revision, m => m.default_unit === l.unit)}</select></label>
        {(['quantity','unit_price','specifications','customisation'] as const).map(f => <div key={f}>{text(({quantity:'Finished quantity',unit_price:'Net unit price',specifications:'Specifications',customisation:'Customisation'})[f], l[f], v => line(i, { ...l, [f]: v }), f === 'quantity' || f === 'unit_price')}</div>)}
        {text('Line requested delivery', l.requested_delivery ?? '', v => { const n = { ...l }; if (v) n.requested_delivery = v; else delete n.requested_delivery; line(i, n); }, false, 'date')}
        {kind !== 'COSTING' && <label>Costing revision<select className={css} value={l.costing_revision ?? ''} onChange={e => { const n = { ...l }; if (e.target.value) n.costing_revision = e.target.value; else delete n.costing_revision; line(i, n); }}><option value="">No costing link</option>{l.costing_revision && !costings.some(c => c.id === l.costing_revision) && <option value={l.costing_revision}>Retained historical costing</option>}{costings.filter(c => c.currency === draft.currency && c.lines.some(v => v.variant === l.variant && v.unit === l.unit)).map(c => <option key={c.id} value={c.id}>Revision {c.number} · {c.lines.map(v => `${v.variant_snapshot.name}: ${v.quantity} ${v.unit_snapshot.code}`).join('; ')} · {c.currency}</option>)}</select><small>Quantity/specification matching remains server validated. Prices are not imported automatically.</small></label>}
        {l.stock_identity && <p>Retained stock identity: {l.stock_identity}. No reservation.</p>}</div>
        {l.costing && <div className="space-y-3"><h3>Gross material consumption</h3>{l.costing.materials.map((m, j) => <fieldset key={j} className="grid md:grid-cols-4 gap-2 border p-2"><legend>Material {j+1}</legend>
          <label>Material<select className={css} required value={m.material} onChange={e => { const master = masters.materials?.find(v => v.id === e.target.value); cost(i, { ...l.costing!, materials: l.costing!.materials.map((v,k) => j === k ? { ...v, material: e.target.value, unit: master?.unit ?? '', price_unit: master?.unit ?? '' } : v) }); }}>{options('materials', m.material)}</select><small>{unit(m.unit)}</small></label>
          {(['quantity','price','currency'] as const).map(f => <div key={f}>{text(f, m[f], value => cost(i, { ...l.costing!, materials: l.costing!.materials.map((v,k) => j === k ? { ...v, [f]: value } : v) }), true)}</div>)}
          <button type="button" disabled={l.costing!.materials.length === 1} onClick={() => cost(i, { ...l.costing!, materials: l.costing!.materials.filter((_,k) => k !== j) })}>Remove material</button></fieldset>)}
          <button type="button" disabled={l.costing.materials.length >= 100} onClick={() => cost(i, { ...l.costing!, materials: [...l.costing!.materials, newMaterial(draft.currency)] })}>Add material component</button>
          <h3>Process estimates</h3>{!l.costing.processes.length && <p>No process amounts entered.</p>}{l.costing.processes.map((p,j) => <fieldset key={j} className="grid md:grid-cols-3 gap-2 border p-2"><legend>Process {j+1}</legend>{(['description','amount','currency'] as const).map(f => <div key={f}>{text(f, p[f], value => cost(i, { ...l.costing!, processes: l.costing!.processes.map((v,k) => j === k ? { ...v, [f]: value } : v) }), true)}</div>)}<button type="button" onClick={() => cost(i, { ...l.costing!, processes: l.costing!.processes.filter((_,k) => k !== j) })}>Remove process</button></fieldset>)}
          <button type="button" disabled={l.costing.processes.length >= 100} onClick={() => cost(i, { ...l.costing!, processes: [...l.costing!.processes, newProcess(draft.currency)] })}>Add process component</button>
          <div className="grid md:grid-cols-2 gap-2">{(['waste_percent','rejection_percent','markup_percent','assumption_evidence'] as const).map(f => <div key={f}>{text(({waste_percent:'Waste assumption %',rejection_percent:'Rejection assumption %',markup_percent:'Markup on cost %',assumption_evidence:'Gross input / output assumption evidence'})[f], l.costing![f], value => cost(i, { ...l.costing!, [f]: value }), true)}</div>)}</div><p>Loss assumptions do not scale gross consumption again. No BOM/yield or unit conversion is inferred.</p>
        </div>}
        <button type="button" disabled={draft.lines.length === 1} onClick={() => setDraft(d => ({ ...d, lines: d.lines.filter((_,j) => i !== j) }))}>Remove product</button>
      </fieldset>)}
      <button type="button" disabled={draft.lines.length >= 100} onClick={() => setDraft(d => ({ ...d, lines: [...d.lines, newLine(kind === 'COSTING', d.currency)] }))}>Add product</button>
      <label className="block">Terms<textarea className={css} value={draft.terms} onChange={e => setDraft(d => ({ ...d, terms: e.target.value }))} maxLength={4000}/></label>
      {text('Change reason', reason, setReason, true)}<button className={css} disabled={busy || !reason.trim()}>{busy ? 'Saving…' : editing ? 'Save new immutable revision' : 'Save new draft'}</button>
    </form></>}
    <CommercialPolicyRegistry enabled={!!records}/>
  </main>;
}
