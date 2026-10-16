import { useState } from 'react';
import axios from 'axios';
import { api } from '@/lib/api';
import { type Quotation } from '@/lib/quotations';
import { saveQuotationSnapshot } from '@/lib/quotationApi';
import { ENTRY_INPUT } from '@/components/ui/SearchSelect';
import { QUOTE_BUTTON } from './QuotationPrint';

interface Delivery { id: string; channel: string; recipient: string; status: string; detail: string }
interface SavedQuotation { id: string; approved: boolean; rejected_at?: string | null; rejection_reason?: string; deliveries: Delivery[] }

function message(error: unknown) {
  if (axios.isAxiosError(error)) {
    if (!error.response) return 'Unable to reach the backend. If sending was interrupted, keep the same request and check history before retrying.';
    return typeof error.response.data?.detail === 'string'
      ? `${error.response.data.detail}${error.response.data.channels ? ` ${JSON.stringify(error.response.data.channels)}` : ''}`
      : JSON.stringify(error.response.data);
  }
  return error instanceof Error ? error.message : 'Unable to process quotation.';
}

export function QuotationDelivery({ quotation, onClose, canSend }: { quotation: Quotation; onClose: () => void; canSend: boolean }) {
  const [email, setEmail] = useState(quotation.customer.email);
  const [phone, setPhone] = useState('+916282744675');
  const [useEmail, setUseEmail] = useState(false), [useWhatsapp, setUseWhatsapp] = useState(false);
  const [saved, setSaved] = useState<SavedQuotation | null>(null), [requestId, setRequestId] = useState(() => crypto.randomUUID());
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [notice, setNotice] = useState('');
  const changed = () => { setRequestId(crypto.randomUUID()); setNotice(''); };
  const persist = async () => {
    if (saved) return saved;
    const data = await saveQuotationSnapshot(quotation);
    setSaved(data);
    return data;
  };
  const run = async (operation: () => Promise<void>) => {
    setBusy(true); setError(''); setNotice('');
    try { await operation(); } catch (e) { setError(message(e)); } finally { setBusy(false); }
  };
  const download = () => run(async () => {
    const record = await persist();
    const { data } = await api.get(`/quotations/${record.id}/pdf/`, { responseType: 'blob' });
    const url = URL.createObjectURL(data); const anchor = document.createElement('a');
    anchor.href = url; anchor.download = `${quotation.number.replace(/[^a-z0-9_.-]/gi, '-')}.pdf`; anchor.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 10000);
    setNotice('PDF downloaded. The server adds a DRAFT label until the PDF snapshot is approved.');
  });
  const refresh = () => run(async () => {
    const record = await persist();
    const { data } = await api.get<SavedQuotation>(`/quotations/${record.id}/`);
    setSaved(data); setNotice('Server status and delivery history refreshed.');
  });
  const send = () => run(async () => {
    const record = await persist();
    const channels = [...(useEmail ? ['email'] : []), ...(useWhatsapp ? ['whatsapp'] : [])];
    const { data } = await api.post<{ results: Delivery[]; replayed: boolean }>(`/quotations/${record.id}/send/`, {
      request_id: requestId, channels, ...(useEmail ? { email } : {}), ...(useWhatsapp ? { phone } : {}),
    });
    const history = await api.get<SavedQuotation>(`/quotations/${record.id}/`); setSaved(history.data);
    setNotice(data.results.map(r => `${r.channel}: ${r.status} — ${r.detail}`).join('\n') + (data.replayed ? '\nExisting request returned; no duplicate message submitted.' : ''));
  });

  return <div className="fixed inset-0 z-[70] overflow-y-auto bg-navy/40 p-4" role="dialog" aria-modal="true" aria-label="Quotation PDF and delivery">
    <section className="mx-auto max-w-2xl space-y-4 rounded-card bg-white p-6 shadow-xl">
      <h2 className="text-xl font-semibold">Quotation PDF &amp; Send</h2>
      <p>{quotation.number} · Revision {quotation.revision} · {quotation.customer.name}</p>
      <p className="text-sm">Submit to Manager on the quotation detail page first. After approval, refresh the server status here and choose how to send it. Only checked channels receive the document.</p>
      <div className="grid gap-3 sm:grid-cols-2">
        <label>Customer phone<input readOnly value={quotation.customer.telephone} className={ENTRY_INPUT} /></label>
        <label>Customer email<input type="email" value={email} onChange={e => { setEmail(e.target.value); changed(); }} disabled={busy} className={ENTRY_INPUT} /></label>
        <label className="sm:col-span-2">WhatsApp recipient (country code required)<input type="tel" value={phone} onChange={e => { setPhone(e.target.value); changed(); }} disabled={busy} className={ENTRY_INPUT} /><span className="text-xs">Default: +91 6282744675. Change this to the intended customer’s WhatsApp number before sending.</span></label>
      </div>
      <form className="space-y-4" onSubmit={e => { e.preventDefault(); void send(); }}>
        <fieldset disabled={busy} className="flex gap-6"><legend className="mb-2 font-medium">Send using</legend>
          <label className="flex items-center gap-2"><input type="checkbox" checked={useEmail} onChange={e => { setUseEmail(e.target.checked); changed(); }} />Email PDF</label>
          <label className="flex items-center gap-2"><input type="checkbox" checked={useWhatsapp} onChange={e => { setUseWhatsapp(e.target.checked); changed(); }} />WhatsApp PDF</label>
        </fieldset>
        {useEmail && !email.trim() && <p className="text-sm text-amber-700">Enter the customer email address.</p>}
        <div className="flex flex-wrap gap-2">
          <button type="button" disabled={busy} className={QUOTE_BUTTON} onClick={() => void download()}>Download PDF</button>

          <button type="button" disabled={busy} className={QUOTE_BUTTON} onClick={() => void refresh()}>Check Manager Approval / History</button>
          <button disabled={busy || !canSend || !saved?.approved || (!useEmail && !useWhatsapp) || (useEmail && !email.trim()) || (useWhatsapp && !/^\+[1-9]\d{7,14}$/.test(phone.replace(/[\s()-]/g, '')))} className={QUOTE_BUTTON}>{busy ? 'Processing…' : 'Send Selected'}</button>
        </div>
      </form>
      <p className="text-xs text-gray-600">Sending requires a current approved quotation, server permission, SMTP settings and/or WhatsApp Business settings. Provider acceptance does not confirm customer delivery. Download and send use saved public fields; private costing is excluded.</p>
      {!canSend && <p className="text-sm text-amber-700">Resolve source review before sending. Superseded and converted quotations cannot be sent from this screen.</p>}
      {notice && <p role="status" className="whitespace-pre-wrap rounded bg-green-50 p-3 text-sm">{notice}</p>}
      {error && <p role="alert" className="whitespace-pre-wrap rounded bg-red-50 p-3 text-sm text-red-700">{error}</p>}
      {saved && <div className="space-y-2 border-t pt-3"><p className="text-sm">Manager approval: {saved.rejected_at ? `Rejected: ${saved.rejection_reason}` : saved.approved ? 'Approved' : 'Awaiting approval'} · Saved ID: {saved.id}</p><h3 className="font-semibold">Delivery history</h3>{saved.deliveries.length ? saved.deliveries.map(d => <p key={d.id} className="text-sm">{d.channel} · {d.recipient} · <strong>{d.status}</strong> · {d.detail}</p>) : <p className="text-sm">No delivery attempts.</p>}{saved.deliveries.length > 0 && <button disabled={busy} className={QUOTE_BUTTON} onClick={() => { changed(); setNotice('New send request prepared. Select only failed channels to avoid repeating a successful delivery.'); }}>Prepare New Send Request</button>}</div>}
      <button disabled={busy} className={QUOTE_BUTTON} onClick={onClose}>Close</button>
    </section>
  </div>;
}
