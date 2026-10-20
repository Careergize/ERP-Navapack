import { FormEvent, useRef, useState } from 'react';
import { api } from '@/lib/api';

export function QuickCustomer({ saved }: { saved: (id: string) => void }) {
  const [name, setName] = useState(''), [type, setType] = useState(''), [error, setError] = useState(''), [busy, setBusy] = useState(false);
  const intent = useRef<{ value: string; key: string }>();
  async function submit(e: FormEvent) {
    e.preventDefault(); if (busy) return; setBusy(true); setError('');
    const data = { name: name.trim(), customer_type: type };
    const value = JSON.stringify(data);
    if (intent.current?.value !== value) intent.current = { value, key: crypto.randomUUID() };
    try { const r = await api.post<{ id: string }>('/customers/', data, { headers: { 'Idempotency-Key': intent.current.key } }); saved(r.data.id); setName(''); intent.current = undefined; }
    catch { setError('Customer was not confirmed saved. Check permissions and connection; retrying unchanged fields reuses the request key.'); }
    finally { setBusy(false); }
  }
  return <details><summary>Create customer in development master catalog</summary><form onSubmit={submit} className="flex flex-wrap gap-3 border p-3">
    <label>Name<input required maxLength={240} className="block border p-2" value={name} onChange={e => setName(e.target.value)}/></label>
    <label>Classification<select className="block border p-2" value={type} onChange={e => setType(e.target.value)}><option value="">Unknown</option><option>B2B</option><option>B2C</option></select></label>
    <button disabled={busy || !name.trim()}>{busy ? 'Saving…' : 'Save customer'}</button>{error && <p role="alert">{error}</p>}
  </form></details>;
}
