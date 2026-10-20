import { FormEvent, useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { useAuth } from '@/context/AuthContext';
import { decisionRegistry, proposalRecords, saveProposal, proposalHistory, type DecisionRegistry, type ProposalRecord } from '@/lib/commercialGovernanceApi';
const css = 'rounded border p-2 w-full';
export function CommercialPolicyRegistry({ enabled }: { enabled: boolean }) {
  const { user } = useAuth(); const writable = !!user?.permissions?.includes('commercial.manage_proposals');
  const [registry, setRegistry] = useState<DecisionRegistry>(), [policies, setPolicies] = useState<ProposalRecord[]>([]), [answers, setAnswers] = useState<ProposalRecord[]>([]);
  const [kind, setKind] = useState<'POLICY'|'DECISION'>('POLICY'), [key, setKey] = useState(''), [title, setTitle] = useState(''), [payload, setPayload] = useState('{}'), [answer, setAnswer] = useState(''), [date, setDate] = useState(''), [linked, setLinked] = useState('');
  const [evidence, setEvidence] = useState([{ reference: '', description: '' }]), [reason, setReason] = useState(''), [editing, setEditing] = useState<ProposalRecord>(), [history, setHistory] = useState<Awaited<ReturnType<typeof proposalHistory>>>([]);
  const [error, setError] = useState(''), [busy, setBusy] = useState(false), [refresh, setRefresh] = useState(0);
  const intent = useRef<{ value: string; key: string }>();
  useEffect(() => { if (!enabled) return; let live = true;
    decisionRegistry().then(d => { if (live) setRegistry(d); }).catch(() => { if (live) setError('Decision registry unavailable.'); });
    if (writable) Promise.all([proposalRecords('POLICY'), proposalRecords('DECISION')]).then(([p, a]) => { if (live) { setPolicies(p); setAnswers(a); } }).catch(() => { if (live) setError('Proposal records unavailable; check capability and disposable context.'); });
    return () => { live = false; };
  }, [enabled, writable, refresh]);
  useEffect(() => { setHistory([]); if (!editing) return; let live = true;
    proposalHistory(editing).then(d => { if (live) setHistory(d); }).catch(() => { if (live) setError('Proposal history unavailable.'); }); return () => { live = false; };
  }, [editing]);
  function select(r: ProposalRecord) {
    setEditing(r); setKind(r.kind); setKey(r.key); setTitle(String(r.content.title ?? '')); setPayload(JSON.stringify(r.content.draft_payload ?? {}, null, 2)); setAnswer(String(r.content.answer ?? '')); setDate(String(r.content.proposed_effective_date ?? '')); setLinked(String(r.content.linked_policy_revision ?? '')); setEvidence(r.content.evidence as typeof evidence); setReason('');
  }
  async function save(e: FormEvent) { e.preventDefault(); setBusy(true); setError(''); try {
    const data: Record<string, unknown> = kind === 'POLICY' ? { policy_type: key, title, draft_payload: JSON.parse(payload), evidence, ...(date ? { proposed_effective_date: date } : {}) } : { decision_id: key, answer, evidence, ...(linked ? { linked_policy_revision: linked } : {}) };
    const value = JSON.stringify({ kind, data, reason, id: editing?.id, version: editing?.version }); if (intent.current?.value !== value) intent.current = { value, key: crypto.randomUUID() };
    const r = await saveProposal(kind, data, reason, intent.current.key, editing); setEditing(r); setRefresh(n => n + 1);
  } catch (e) { setError(axios.isAxiosError(e) ? `Proposal not saved (${e.response?.status ?? 'network'}). ${JSON.stringify(e.response?.data?.error ?? 'Retry unchanged input safely.')}` : 'Enter a valid JSON object for the draft payload.'); } finally { setBusy(false); } }
  if (!enabled) return null;
  return <section className="border rounded p-4 space-y-4"><h2 className="text-xl font-semibold">Policy proposals and client decision registry</h2><p>Unverified evidence only. Proposed dates, answers and files referenced here never approve policy, resolve a decision or enable commercial actions. Independent verification remains unavailable.</p>
    {error && <p role="alert">{error}</p>}{!registry && <p>Loading registry…</p>}
    {registry?.results.map(d => <details key={d.decision_id}><summary>{d.decision_id} · {d.department} · {d.status}</summary><p>Baseline: {d.baseline_status}. {d.review_history_count} unverified answer revisions. No independent review performed.</p><h3>Required evidence</h3><ul>{d.required_evidence.map(v => <li key={v}>{v}</li>)}</ul><h3>Conflicting evidence (retained separately)</h3><ul>{d.conflicting_evidence.map(v => <li key={v.reference}>{v.reference}: {v.interpretation}</li>)}</ul><h3>Outstanding questions</h3><ul>{d.outstanding_questions.map(v => <li key={v}>{v}</li>)}</ul>{d.latest_submission && <button onClick={() => select(d.latest_submission!)}>View/edit unverified answer history</button>}</details>)}
    {!writable ? <p>Proposal editing unavailable: explicit commercial proposal capability required.</p> : <>
      <h3>Owned proposals and answers</h3>{!policies.length && !answers.length && <p>No proposal records.</p>}{[...policies, ...answers].map(r => <button className={css} key={r.id} onClick={() => select(r)}>{r.key} · revision {r.version} · {r.status}</button>)}
      <form onSubmit={save} className="space-y-3"><h3>{editing ? 'Record a new unverified revision' : 'Record a proposal / client answer'}</h3>
        <button type="button" onClick={() => { setEditing(undefined); setKey(''); setTitle(''); setPayload('{}'); setAnswer(''); setLinked(''); setDate(''); setEvidence([{ reference: '', description: '' }]); setReason(''); }}>New proposal record</button>
        <label>Record type<select className={css} disabled={!!editing} value={kind} onChange={e => { setKind(e.target.value as typeof kind); setKey(''); }}><option value="POLICY">Policy proposal</option><option value="DECISION">Unverified client answer</option></select></label>
        <label>{kind === 'POLICY' ? 'Policy type' : 'Decision'}<select className={css} required disabled={!!editing} value={key} onChange={e => setKey(e.target.value)}><option value="">Select…</option>{(kind === 'POLICY' ? registry?.policy_types : registry?.results.map(r => r.decision_id))?.map(v => <option key={v}>{v}</option>)}</select></label>
        {kind === 'POLICY' ? <><label>Proposal title<input className={css} required value={title} onChange={e => setTitle(e.target.value)} maxLength={240}/></label><label>Draft payload (JSON object; never executed)<textarea className={css} required rows={5} value={payload} onChange={e => setPayload(e.target.value)}/></label><label>Proposed effective date (does not activate)<input className={css} type="date" value={date} onChange={e => setDate(e.target.value)}/></label></> : <><label>Unverified client answer<textarea className={css} required value={answer} onChange={e => setAnswer(e.target.value)} maxLength={8000}/></label><label>Linked proposed policy revision<select className={css} value={linked} onChange={e => setLinked(e.target.value)}><option value="">Unlinked</option>{linked && !policies.some(p => p.revision === linked) && <option value={linked}>Retained historical policy revision</option>}{policies.map(p => <option key={p.revision} value={p.revision}>{String(p.content.title)} · {p.key} · revision {p.version}</option>)}</select></label></>}
        {evidence.map((v, i) => <fieldset className="border p-2" key={i}><legend>Evidence reference {i+1}</legend><label>Source reference<input className={css} required maxLength={500} value={v.reference} onChange={e => setEvidence(old => old.map((v, j) => i === j ? { ...v, reference: e.target.value } : v))}/></label><label>Description / interpretation<textarea className={css} required maxLength={1000} value={v.description} onChange={e => setEvidence(old => old.map((v, j) => i === j ? { ...v, description: e.target.value } : v))}/></label><button type="button" disabled={evidence.length === 1} onClick={() => setEvidence(old => old.filter((_, j) => i !== j))}>Remove evidence reference</button></fieldset>)}
        <button type="button" disabled={evidence.length >= 20} onClick={() => setEvidence(old => [...old, { reference: '', description: '' }])}>Add evidence reference</button>
        <label>Change reason<input className={css} required maxLength={500} value={reason} onChange={e => setReason(e.target.value)}/></label><button className={css} disabled={busy}>{busy ? 'Saving…' : 'Save unverified evidence'}</button>
      </form>
      {history.length > 0 && <div><h3>Unverified revision history — no independent review</h3>{history.map(r => <details key={r.id}><summary>Revision {r.number} · {r.status} · {r.created_at} · {r.reason}</summary><p>Author reference: {r.author}</p><p>{String(r.content.answer ?? r.content.title ?? '')}</p><pre className="whitespace-pre-wrap break-words text-xs">{JSON.stringify(r.content, null, 2)}</pre></details>)}</div>}
    </>}
  </section>;
}
