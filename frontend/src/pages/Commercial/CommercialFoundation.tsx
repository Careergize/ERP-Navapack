import { FormEvent, useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { useAuth } from '@/context/AuthContext';
import { api } from '@/lib/api';
import { commercialPage, commercialHistory, saveCommercial, transitionCommercial, type CommercialKind, type CommercialRecord, type CommercialHistory, type Page } from '@/lib/commercialApi';

type Master = { id: string; name: string; unit?: string; code?: string };
type Entry = { variant: string; quantity: string; unit_price: string; specifications: string; customisation: string; material: string; consumption: string; material_price: string; process: string; process_description: string; waste: string; rejection: string; markup: string; assumption: string; costing_revision: string };
const emptyLine = (): Entry => ({ variant: '', quantity: '', unit_price: '', specifications: '', customisation: '', material: '', consumption: '', material_price: '', process: '0', process_description: 'Entered process estimate', waste: '0', rejection: '0', markup: '0', assumption: '', costing_revision: '' });
const control = 'rounded border p-2 w-full';
function SnapshotSummary({ snapshot }: { snapshot: CommercialRecord['snapshot'] }) {
  const input = snapshot.input;
  const party = input.party_snapshot as { name?: string } | null;
  const items = input.lines as { quantity: string; unit_price: string; specifications: string; customisation: string; variant_snapshot: { name: string }; unit_snapshot: { code: string }; costing_snapshot?: { revision: string } }[];
  const totals = snapshot.estimate as CommercialRecord['snapshot']['estimate'] & { lines: { net_amount: string; costing?: Record<string, string | null> }[] };
  const currency = String(input.currency);
  return <div className="space-y-3 p-3 text-sm"><p>{party?.name ?? 'Product costing (no customer)'} · {currency} · {String(input.money_places)} monetary decimal places · {String(input.rounding).replace('_', ' ')}</p>
    {items.map((line, i) => <article key={i} className="space-y-1 border rounded p-3"><h4 className="font-semibold">{line.variant_snapshot.name}</h4>
      <p>{line.quantity} {line.unit_snapshot.code} × {line.unit_price} {currency} = {totals.lines[i].net_amount} {currency} before discount</p>
      <p className="whitespace-pre-wrap">{line.specifications}</p>{line.customisation && <p className="whitespace-pre-wrap">Customisation: {line.customisation}</p>}
      {line.costing_snapshot && <p>Retained costing revision: {line.costing_snapshot.revision} (unapproved estimate)</p>}
      {totals.lines[i].costing && <dl className="grid sm:grid-cols-2 gap-2">{[
        ['material_cost', 'Material cost'], ['process_cost', 'Process estimate'], ['estimated_production_cost', 'Estimated production cost'],
        ['cost_per_output_unit', `Cost per ${line.unit_snapshot.code}`], ['suggested_net_selling', 'Suggested net selling'],
        ['suggested_unit_price', 'Suggested unit price'], ['gross_margin_percent', 'Suggested gross margin %'],
        ['entered_gross_margin_percent_before_discount', 'Entered gross margin % before discount'],
      ].map(([field, label]) => <div key={field}><dt className="text-slate-600">{label}</dt><dd>{totals.lines[i].costing?.[field] ?? 'Unavailable'}{field.includes('percent') ? '' : ` ${currency}`}</dd></div>)}</dl>}
    </article>)}
    <p>Discount: {String(input.discount)} {currency}. Net estimate: {snapshot.estimate.net_estimate} {currency}.</p>
    <p>VAT, LED, final payable total and actual cost: unavailable.</p>
    {typeof input.requested_delivery === 'string' && <p>Requested delivery: {input.requested_delivery}</p>}
    {typeof input.validity_date === 'string' && <p>Entered validity: {input.validity_date}</p>}
    <p className="whitespace-pre-wrap">Terms: {String(input.terms) || 'Unspecified'}</p>
  </div>;
}
export function CommercialFoundation() {
  const { user } = useAuth();
  const allowed = !!user?.backendSession && !!user.permissions?.includes('commercial.use_foundation');
  const [kind, setKind] = useState<CommercialKind>('QUOTATION');
  const [partyType, setPartyType] = useState<'customers' | 'prospects' | 'none'>('customers');
  const [party, setParty] = useState(''); const [currency, setCurrency] = useState('');
  const [places, setPlaces] = useState(2); const [rounding, setRounding] = useState('HALF_UP');
  const [discount, setDiscount] = useState('0'); const [terms, setTerms] = useState(''); const [reason, setReason] = useState('');
  const [delivery, setDelivery] = useState(''); const [validity, setValidity] = useState('');
  const [lines, setLines] = useState<Entry[]>([emptyLine()]);
  const [masters, setMasters] = useState<Record<string, Master[]>>({});
  const [records, setRecords] = useState<Page<CommercialRecord>>(); const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<CommercialRecord>(); const [history, setHistory] = useState<Page<CommercialHistory>>();
  const [editing, setEditing] = useState<CommercialRecord>();
  const [historyPage, setHistoryPage] = useState(1); const [error, setError] = useState(''); const [busy, setBusy] = useState(false); const [refresh, setRefresh] = useState(0);
  const intent = useRef<{ payload: string; key: string }>();
  const errorText = (e: unknown) => axios.isAxiosError(e) ? `Request failed (${e.response?.status ?? 'network'}): ${JSON.stringify(e.response?.data?.error ?? 'Connection unavailable. Retry unchanged input safely.')}` : 'Unable to complete request.';
  useEffect(() => {
    if (!allowed) return;
    let current = true; setRecords(undefined); setError('');
    commercialPage(page).then(d => { if (current) setRecords(d); }).catch(e => { if (current) setError(errorText(e)); });
    return () => { current = false; };
  }, [allowed, page, refresh]);
  useEffect(() => {
    if (!allowed) return;
    let current = true;
    async function load(resource: string) {
      const rows: Master[] = [];
      for (let n = 1; ; n++) {
        const { data } = await api.get<Page<Master>>(`/${resource}/`, { params: { page: n, is_active: true } });
        rows.push(...data.results); if (!data.next) return rows;
      }
    }
    const permissions: Record<string, string> = { customers: 'customer', prospects: 'prospect', variants: 'productvariant', units: 'unit', materials: 'material' };
    Promise.all(Object.keys(permissions).filter(r => user?.permissions?.includes(`masters.view_${permissions[r]}`)).map(async r => [r, await load(({ variants: 'finished-goods', materials: 'raw-materials' } as Record<string, string>)[r] ?? r)] as const))
      .then(entries => { if (current) setMasters(Object.fromEntries(entries)); }).catch(e => { if (current) setError(errorText(e)); });
    return () => { current = false; };
  }, [allowed, refresh, user?.permissions]);
  useEffect(() => {
    setHistory(undefined); if (!selected) return;
    let current = true;
    commercialHistory(selected.id, historyPage).then(d => { if (current) setHistory(d); }).catch(e => { if (current) setError(errorText(e)); });
    return () => { current = false; };
  }, [selected, historyPage]);
  if (!allowed) return <div className="p-6"><h1>Commercial foundation</h1><p>Unavailable: a backend employee session and explicit commercial capability are required.</p></div>;
  if (!records) return <main className="space-y-3 p-6"><h1 className="text-2xl font-semibold">Commercial foundation</h1>
    {error ? <p role="alert">Commercial persistence unavailable. {error}</p> : <p role="status">Checking commercial persistence…</p>}
    <p>Only a verified disposable development database supports these workflows. Approval, PDF/email, dispatch and production are unavailable.</p>
    <button onClick={() => setRefresh(n => n + 1)}>Retry connection</button></main>;
  const options = (resource: string) => <><option value="">Select…</option>{masters[resource]?.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}</>;
  const unitName = (id?: string) => masters.units?.find(u => u.id === id)?.name ?? 'Unit unavailable';
  const updateLine = (index: number, field: keyof Entry, value: string) => setLines(old => old.map((line, i) => i === index ? { ...line, [field]: value } : line));
  function keyFor(payload: unknown) {
    const value = JSON.stringify(payload);
    if (intent.current?.payload !== value) intent.current = { payload: value, key: crypto.randomUUID() };
    return intent.current.key;
  }
  async function save(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError('');
    try {
      const data = { currency, money_places: places, rounding, ...(partyType === 'none' ? {} : { [partyType === 'customers' ? 'customer' : 'prospect']: party }),
        discount, terms, ...(delivery ? { requested_delivery: delivery } : {}), ...(validity ? { validity_date: validity } : {}),
        lines: lines.map(l => {
          const variant = masters.variants?.find(v => v.id === l.variant);
          const material = masters.materials?.find(v => v.id === l.material);
          return { variant: l.variant, unit: variant?.unit, quantity: l.quantity, unit_price: l.unit_price, specifications: l.specifications, customisation: l.customisation,
            ...(kind !== 'COSTING' && l.costing_revision ? { costing_revision: l.costing_revision } : {}),
            ...(kind === 'COSTING' ? { costing: { materials: [{ material: l.material, unit: material?.unit, price_unit: material?.unit, currency, quantity: l.consumption, price: l.material_price }],
              processes: [{ description: l.process_description, currency, amount: l.process }], waste_percent: l.waste, rejection_percent: l.rejection,
              assumption_evidence: l.assumption, markup_percent: l.markup } } : {}) };
        }) };
      const record = await saveCommercial(kind, data, reason, keyFor({ kind, data, reason, editing }), editing);
      if (editing) setEditing(record);
      setSelected(record); setHistoryPage(1); setRefresh(n => n + 1);
    } catch (e) { setError(errorText(e)); } finally { setBusy(false); }
  }
  async function change(transition: 'submit' | 'reopen' | 'cancel') {
    if (!selected) return;
    setBusy(true); setError('');
    try { const record = await transitionCommercial(selected, transition, reason, keyFor({ selected, transition, reason })); setSelected(record); setEditing(undefined); setRefresh(n => n + 1); }
    catch (e) { setError(errorText(e)); } finally { setBusy(false); }
  }
  function editDraft() {
    if (!selected || selected.status !== 'DRAFT') return;
    const d = selected.snapshot.input;
    const source = d.lines as (Record<string, unknown> & { costing?: { materials: { material: string; quantity: string; price: string }[]; processes: { amount: string; description: string }[]; waste_percent: string; rejection_percent: string; markup_percent: string; assumption_evidence: string } })[];
    if (source.some(l => l.model_revision || l.stock_identity || l.requested_delivery || (l.costing && (l.costing.materials.length !== 1 || l.costing.processes.length !== 1))) || d.marketing_person || d.classification || d.quotation_revision) {
      setError('This draft contains fields supported by the API editor only. Editing here would omit them.'); return;
    }
    setEditing(selected); setKind(selected.kind); setPartyType(d.customer ? 'customers' : d.prospect ? 'prospects' : 'none'); setParty(String(d.customer ?? d.prospect ?? ''));
    setCurrency(String(d.currency)); setPlaces(Number(d.money_places)); setRounding(String(d.rounding)); setDiscount(String(d.discount)); setTerms(String(d.terms));
    setDelivery(String(d.requested_delivery ?? '')); setValidity(String(d.validity_date ?? ''));
    setLines(source.map(l => ({ ...emptyLine(), variant: String(l.variant), quantity: String(l.quantity), unit_price: String(l.unit_price), specifications: String(l.specifications), customisation: String(l.customisation),
      costing_revision: String(l.costing_revision ?? ''), ...(l.costing ? { material: l.costing.materials[0].material, consumption: l.costing.materials[0].quantity,
        material_price: l.costing.materials[0].price, process: l.costing.processes[0].amount, process_description: l.costing.processes[0].description, waste: l.costing.waste_percent,
        rejection: l.costing.rejection_percent, markup: l.costing.markup_percent, assumption: l.costing.assumption_evidence } : {}) })));
  }
  return <main className="space-y-6 p-6 max-w-6xl">
    <h1 className="text-2xl font-semibold">Commercial foundation</h1>
    <p>Disposable development estimates only. VAT, LED and final payable totals await approved rules. Approval, customer sending, PDF/email, dispatch and production are unavailable. Orders create demand without reserving or deducting stock.</p>
    {error && <p role="alert" className="text-red-700">{error}</p>}
    <button className={control} disabled={busy} onClick={() => setRefresh(n => n + 1)}>Reload saved records</button>
    {!records && !error && <p role="status">Loading saved records…</p>}
    {records && <section aria-label="Saved documents" className="space-y-2"><h2 className="text-lg font-semibold">Saved documents</h2>
      {!records.count && <p>No saved commercial documents.</p>}
      {records.results.map(r => <button key={r.id} className={control} onClick={() => { setSelected(r); setHistoryPage(1); }}>{r.kind} · {r.status} · revision {r.version} · {r.snapshot.estimate.net_estimate} {String(r.snapshot.input.currency)}</button>)}
      <button disabled={page === 1} onClick={() => setPage(n => n - 1)}>Previous</button> · <button disabled={!records.next} onClick={() => setPage(n => n + 1)}>Next</button>
    </section>}
    {selected && <section className="space-y-3 border rounded p-4"><h2 className="text-lg font-semibold">{selected.kind} — {selected.status}, revision {selected.version}</h2>
      <p>Net estimate: {selected.snapshot.estimate.net_estimate} {String(selected.snapshot.input.currency)}. Final payable total unavailable.</p>
      <label>Change reason<input className={control} value={reason} onChange={e => setReason(e.target.value)} maxLength={500}/></label>
      {selected.status === 'DRAFT' && <><button disabled={busy} onClick={editDraft}>Edit draft below</button> · <button disabled={busy || !reason} onClick={() => change('submit')}>Submit for review</button> · <button disabled={busy || !reason} onClick={() => change('cancel')}>Cancel draft</button></>}
      {selected.status === 'REVIEW' && <button disabled={busy || !reason} onClick={() => change('reopen')}>Return to draft</button>}
      <SnapshotSummary snapshot={selected.snapshot}/>
      <h3>Revision history</h3>{history?.results.map(r => <details key={r.id}><summary>Revision {r.number} · {r.status} · {r.reason}</summary><SnapshotSummary snapshot={r.snapshot}/></details>)}
      <button disabled={historyPage === 1} onClick={() => setHistoryPage(n => n - 1)}>Earlier page</button> · <button disabled={!history?.next} onClick={() => setHistoryPage(n => n + 1)}>Next history page</button>
    </section>}
    <form onSubmit={save} className="space-y-4 border rounded p-4"><h2 className="text-lg font-semibold">{editing ? `Edit draft revision ${editing.version}` : 'Create a draft'}</h2>
      {editing && <button type="button" onClick={() => setEditing(undefined)}>Create a new document instead</button>}
      <div className="grid md:grid-cols-3 gap-3">
        <label>Document<select className={control} disabled={!!editing} value={kind} onChange={e => { setKind(e.target.value as CommercialKind); if (partyType === 'none') setPartyType('customers'); }}><option value="QUOTATION">Quotation</option><option value="SALES_ORDER">Sales order</option><option value="COSTING">Costing</option></select></label>
        <label>Party type<select className={control} value={partyType} onChange={e => { setPartyType(e.target.value as typeof partyType); setParty(''); }}><option value="customers">Existing customer</option><option value="prospects">Prospective customer (quotation/costing)</option>{kind === 'COSTING' && <option value="none">Product costing without a customer</option>}</select></label>
        {partyType !== 'none' && <label>Customer / prospect<select className={control} required value={party} onChange={e => setParty(e.target.value)}>{options(partyType)}</select></label>}
        <label>Currency<select className={control} required value={currency} onChange={e => setCurrency(e.target.value)}><option value="">Select currency…</option><option>UGX</option><option>USD</option></select></label>
        <label>Money decimal places<select className={control} value={places} onChange={e => setPlaces(Number(e.target.value))}><option value={0}>0</option><option value={2}>2</option></select></label>
        <label>Rounding<select className={control} value={rounding} onChange={e => setRounding(e.target.value)}><option value="HALF_UP">Half up</option><option value="HALF_EVEN">Half even</option></select></label>
        <label>Requested delivery<input className={control} type="date" value={delivery} onChange={e => setDelivery(e.target.value)}/></label>
        <label>Quotation validity<input className={control} type="date" value={validity} onChange={e => setValidity(e.target.value)}/></label>
        <label>Discount (net estimate currency)<input className={control} required value={discount} onChange={e => setDiscount(e.target.value)}/></label>
      </div>
      {lines.map((l, index) => <fieldset key={index} className="space-y-3 border p-3"><legend>Product {index + 1}</legend><div className="grid md:grid-cols-3 gap-3">
        <label>Product<select className={control} required value={l.variant} onChange={e => updateLine(index, 'variant', e.target.value)}>{options('variants')}</select><span>{unitName(masters.variants?.find(v => v.id === l.variant)?.unit)}</span></label>
        {(['quantity', 'unit_price', 'specifications', 'customisation'] as const).map(field => <label key={field}>{({ quantity: 'Finished quantity', unit_price: 'Net unit price', specifications: 'Specifications', customisation: 'Customisation' })[field]}<input className={control} required={field === 'quantity' || field === 'unit_price'} value={l[field]} onChange={e => updateLine(index, field, e.target.value)}/></label>)}
        {kind !== 'COSTING' && <label>Costing revision reference (optional)<input className={control} value={l.costing_revision} onChange={e => updateLine(index, 'costing_revision', e.target.value)}/></label>}
        {kind === 'COSTING' && <><label>Material<select className={control} required value={l.material} onChange={e => updateLine(index, 'material', e.target.value)}>{options('materials')}</select>{unitName(masters.materials?.find(m => m.id === l.material)?.unit)}</label>
          {(['consumption', 'material_price', 'process', 'process_description', 'waste', 'rejection', 'markup', 'assumption'] as const).map(field => <label key={field}>{({ consumption: 'Gross material consumption', material_price: 'Material price per material unit', process: 'Process cost estimate', process_description: 'Process description', waste: 'Waste assumption %', rejection: 'Rejection assumption %', markup: 'Markup on cost %', assumption: 'Loss/output assumption evidence' })[field]}<input className={control} required value={l[field]} onChange={e => updateLine(index, field, e.target.value)}/></label>)}
        </>}
      </div><button type="button" disabled={lines.length === 1} onClick={() => setLines(old => old.filter((_, i) => i !== index))}>Remove product</button></fieldset>)}
      <button type="button" disabled={lines.length >= 100} onClick={() => setLines(old => [...old, emptyLine()])}>Add product</button>
      <label className="block">Terms<textarea className={control} value={terms} onChange={e => setTerms(e.target.value)} maxLength={4000}/></label>
      <label className="block">Draft reason<input className={control} required value={reason} onChange={e => setReason(e.target.value)} maxLength={500}/></label>
      <button className={control} disabled={busy}>{busy ? 'Saving…' : editing ? 'Save new revision' : 'Save new draft'}</button>
    </form>
  </main>;
}
