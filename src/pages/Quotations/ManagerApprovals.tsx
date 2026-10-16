import { useEffect, useState } from 'react';
import axios from 'axios';
import { api } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';
import { Card } from '@/components/ui/Card';
import { QUOTE_BUTTON } from './QuotationPrint';

interface PendingQuote { id: string; approved: boolean; rejected_at: string | null; rejection_reason: string; reviewed_by: string | null; document: { number: string; revision: number; customer: { name: string; contactPerson: string; email: string; telephone: string; billingAddress: string }; currency: string; taxRate: string; taxMode: string; totals: { taxableAmount: string; tax: string; total: string }; validUntil: string; lines: { description: string; quantity: string; unit: string; unitPrice: string; lineTotal?: string }[]; terms: Record<string, string | number> } }

function approvalError(error: unknown) {
  if (axios.isAxiosError(error)) return error.response?.data?.detail ?? 'Unable to reach the approval service. Check your backend connection and quotation permissions.';
  return error instanceof Error ? error.message : 'Unable to process approval.';
}

export function ManagerApprovals() {
  const { user } = useAuth();
  const [rows, setRows] = useState<PendingQuote[]>([]), [error, setError] = useState(''), [busy, setBusy] = useState(false);
  const [pendingOnly, setPendingOnly] = useState(true), [selected, setSelected] = useState<string | null>(null);
  const [reasons, setReasons] = useState<Record<string, string>>({}), [notice, setNotice] = useState('');
  const isManager = user?.role === 'project_manager' || user?.role === 'production_manager';
  const reload = async () => {
    setBusy(true); setError('');
    try {
      const records: PendingQuote[] = [];
      for (let page = 1; ; page++) {
        const { data } = await api.get('/quotations/', { params: { ...(pendingOnly ? { pending: 'true' } : { submitted: 'true' }), page } });
        records.push(...data.results);
        if (!data.next) break;
      }
      setRows(records);
    } catch(e) { setError(approvalError(e)); } finally { setBusy(false); }
  };
  useEffect(() => { if (isManager && user && !user.id.startsWith('demo-')) void reload(); }, [user?.id, pendingOnly]);
  if (!isManager || !user) return null;
  const approve = async (id: string) => {
    setBusy(true); setError('');
    try { await api.post(`/quotations/${id}/approve/`); setNotice('Quotation approved. Authorized staff can now send it through their selected channels.'); await reload(); }
    catch(e) { setError(approvalError(e)); } finally { setBusy(false); }
  };
  const reject = async (id: string) => {
    setBusy(true); setError(''); setNotice('');
    try { await api.post(`/quotations/${id}/reject/`, { reason: reasons[id] ?? '' }); setNotice('Quotation rejected. Email and WhatsApp sending are blocked until a revised quotation is approved.'); await reload(); }
    catch(e) { setError(approvalError(e)); } finally { setBusy(false); }
  };
  const preview = async (id: string) => {
    setBusy(true); setError('');
    try {
      const { data } = await api.get(`/quotations/${id}/pdf/`, { responseType: 'blob' });
      const url = URL.createObjectURL(data); const link = document.createElement('a');
      link.href = url; link.download = 'quotation-review.pdf'; link.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 10000);
    } catch(e) { setError(approvalError(e)); } finally { setBusy(false); }
  };
  return <Card className="space-y-3"><h2 className="text-lg font-semibold">Manager Approval Inbox</h2>
    <p className="text-sm">Review submitted PDFs before approving. Approval enables selected email/WhatsApp delivery; it does not send automatically.</p>
    {user.id.startsWith('demo-') ? <p className="text-sm">Sign in with a real manager account to review saved submissions.</p> : <>
      <div className="flex flex-wrap gap-3"><label>Show<select value={pendingOnly ? 'pending' : 'all'} disabled={busy} onChange={e => { setPendingOnly(e.target.value === 'pending'); setSelected(null); }} className="ml-2 rounded border p-2"><option value="pending">Pending approval</option><option value="all">All submitted quotations</option></select></label><button disabled={busy} className={QUOTE_BUTTON} onClick={() => void reload()}>Refresh Quotations</button></div>
      {!busy && !rows.length && <p>No quotations awaiting manager approval.</p>}
      {rows.map(q => <div key={q.id} className="space-y-3 border-t pt-3"><p className="font-medium">{q.document.number} · Revision {q.document.revision} · {q.document.customer.name}</p><p>{q.document.currency} {q.document.totals.total} · Valid until {q.document.validUntil} · {q.rejected_at ? 'Rejected' : q.approved ? 'Approved' : 'Pending approval'}</p><div className="flex gap-2"><button className={QUOTE_BUTTON} onClick={() => setSelected(selected === q.id ? null : q.id)}>{selected === q.id ? 'Close Details' : 'View Quotation'}</button><button disabled={busy} className={QUOTE_BUTTON} onClick={() => void preview(q.id)}>Review PDF</button></div>
        {selected === q.id && <section className="space-y-3 rounded border bg-gray-50 p-4"><p>{q.document.customer.contactPerson} · {q.document.customer.telephone} · {q.document.customer.email}</p><p className="whitespace-pre-wrap">{q.document.customer.billingAddress}</p><div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr>{['Item', 'Quantity', 'Unit', 'Unit price', 'Line total'].map(h => <th key={h} className="p-2">{h}</th>)}</tr></thead><tbody>{q.document.lines.map((l, i) => <tr key={i}><td className="p-2">{l.description}</td><td className="p-2">{l.quantity}</td><td className="p-2">{l.unit}</td><td className="p-2">{l.unitPrice}</td><td className="p-2">{l.lineTotal ?? (Number(l.quantity) * Number(l.unitPrice)).toFixed(2)}</td></tr>)}</tbody></table></div><p>VAT {q.document.taxRate}% · {q.document.taxMode} pricing · VAT amount {q.document.totals.tax}</p><p className="font-semibold">Total: {q.document.currency} {q.document.totals.total}</p>{Object.entries(q.document.terms).filter(([, v]) => v !== '').map(([k, v]) => <p key={k} className="whitespace-pre-wrap text-sm">{k}: {v}</p>)}
          {q.rejected_at ? <p>Rejected by {q.reviewed_by}: {q.rejection_reason}</p> : q.approved ? <p>Approved by {q.reviewed_by}</p> : <><button disabled={busy} className="rounded-card border border-green-700 bg-green-700 px-4 py-2 text-sm font-medium text-white hover:bg-green-800 focus-visible:outline-green-700 disabled:cursor-not-allowed disabled:opacity-40" onClick={() => void approve(q.id)}>Approve Quotation</button><form className="space-y-2" onSubmit={e => { e.preventDefault(); void reject(q.id); }}><label className="block">Rejection reason<textarea required maxLength={2000} disabled={busy} value={reasons[q.id] ?? ''} onChange={e => setReasons({ ...reasons, [q.id]: e.target.value })} className="mt-1 block w-full rounded border p-2" /></label><button disabled={busy || !reasons[q.id]?.trim()} className={QUOTE_BUTTON}>Reject Quotation</button></form></>}
        </section>}
      </div>)}
    </>}{notice && <p role="status" className="text-green-800">{notice}</p>}{error && <p role="alert" className="text-red-700">{error}</p>}</Card>;
}
