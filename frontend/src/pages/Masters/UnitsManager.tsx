import { useState } from 'react';
import { useUnits, unitError } from '@/lib/unitsApi';
import { api } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';
import { ENTRY_INPUT } from '@/components/ui/SearchSelect';

export function UnitsManager() {
  const { units, loading, error, reload } = useUnits(false);
  const { user } = useAuth();
  const [code, setCode] = useState(''), [name, setName] = useState(''), [busy, setBusy] = useState(false), [saveError, setSaveError] = useState('');
  const demo = !user || user.id.startsWith('demo-');
  const toggle = async (id: number, active: boolean) => {
    setBusy(true); setSaveError('');
    try { await api.patch(`/units/${id}/`, { is_active: active }); reload(); }
    catch(e) { setSaveError(unitError(e)); } finally { setBusy(false); }
  };
  return <section className="space-y-4"><h2 className="text-xl font-semibold">Units</h2><p className="text-sm">Add units such as kg or ctn. Quotations load active units from this master. Units do not define quantity conversions.</p>
    <form className="flex flex-wrap items-end gap-3" onSubmit={async e => { e.preventDefault(); setBusy(true); setSaveError(''); try { await api.post('/units/', { code, name }); setCode(''); setName(''); reload(); } catch(e) { setSaveError(unitError(e)); } finally { setBusy(false); } }}>
      <label>Unit code<input required maxLength={30} value={code} onChange={e => setCode(e.target.value)} disabled={busy || demo} placeholder="kg" className={ENTRY_INPUT} /></label>
      <label>Unit name<input required maxLength={100} value={name} onChange={e => setName(e.target.value)} disabled={busy || demo} placeholder="Kilogram" className={ENTRY_INPUT} /></label>
      <button disabled={busy || demo} className="rounded border px-4 py-2">Add Unit</button>
    </form>
    <button disabled={loading || busy} onClick={reload} className="rounded border px-4 py-2">Refresh Units</button>
    {(error || saveError) && <p role="alert" className="text-red-700">{saveError || error}</p>}
    {loading ? <p role="status">Loading units…</p> : <table className="w-full text-left text-sm"><thead><tr><th className="p-2">Code</th><th className="p-2">Name</th><th className="p-2">Status</th><th className="p-2">Action</th></tr></thead><tbody>{units.map(unit => <tr key={unit.id} className="border-t"><td className="p-2">{unit.code}</td><td className="p-2">{unit.name}</td><td className="p-2">{unit.is_active ? 'Active' : 'Inactive'}</td><td><button disabled={busy} onClick={() => void toggle(unit.id, !unit.is_active)} className="underline">{unit.is_active ? 'Deactivate' : 'Activate'}</button></td></tr>)}</tbody></table>}
  </section>;
}
