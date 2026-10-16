import { useEffect, useState } from 'react';
import axios from 'axios';
import { api } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';
import { ENTRY_INPUT } from '@/components/ui/SearchSelect';

interface RoleRecord { id: number; name: string; code: string }
interface UserRecord { id: number; username: string; email: string; assigned_role: number | null; role_name: string; is_active: boolean }

export function UsersManager() {
  const { user } = useAuth();
  const [roles, setRoles] = useState<RoleRecord[]>([]), [users, setUsers] = useState<UserRecord[]>([]);
  const [username, setUsername] = useState(''), [email, setEmail] = useState(''), [password, setPassword] = useState(''), [role, setRole] = useState('');
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [notice, setNotice] = useState('');
  const demo = !user || user.id.startsWith('demo-');
  const fail = (e: unknown) => setError(axios.isAxiosError(e) ? e.response?.status === 403 ? 'Sign in as a Django superuser to manage users and roles.' : e.response ? JSON.stringify(e.response.data) : 'Cannot reach the user service.' : 'Unable to save user.');
  const load = async () => {
    setBusy(true); setError('');
    try {
      const collect = async <T,>(url: string) => {
        const records: T[] = [];
        for (let page = 1; ; page++) { const { data } = await api.get(url, { params: { page } }); records.push(...data.results); if (!data.next) return records; }
      };
      const [savedRoles, savedUsers] = await Promise.all([collect<RoleRecord>('/roles/'), collect<UserRecord>('/users/')]);
      setRoles(savedRoles); setUsers(savedUsers);
    } catch(e) { fail(e); } finally { setBusy(false); }
  };
  useEffect(() => { if (!demo) void load(); }, [user?.id]);
  const change = async (id: number, fields: object) => {
    setBusy(true); setError(''); setNotice('');
    try { await api.patch(`/users/${id}/`, fields); await load(); setNotice('User updated. Role changes appear after the user refreshes or signs in again.'); }
    catch(e) { fail(e); } finally { setBusy(false); }
  };
  return <section className="space-y-4"><h2 className="text-xl font-semibold">Users &amp; Roles</h2><p className="text-sm">Create a user and assign Project Manager to enable quotation review, approval and rejection. Role permissions can be managed in Django Admin → Roles.</p>
    {demo ? <p>Sign in with a real superuser account to manage users.</p> : <>
      <form className="grid gap-3 rounded border p-4 sm:grid-cols-2" onSubmit={async e => { e.preventDefault(); setBusy(true); setError(''); setNotice(''); try { await api.post('/users/', { username, email, password, assigned_role: Number(role) }); setUsername(''); setEmail(''); setPassword(''); await load(); setNotice('User created with the selected role. They can now sign in with their username.'); } catch(e) { fail(e); } finally { setBusy(false); } }}>
        <label>Username<input required disabled={busy} autoComplete="off" value={username} onChange={e => setUsername(e.target.value)} className={ENTRY_INPUT} /></label>
        <label>Email<input type="email" disabled={busy} value={email} onChange={e => setEmail(e.target.value)} className={ENTRY_INPUT} /></label>
        <label>Initial password<input required type="password" disabled={busy} autoComplete="new-password" value={password} onChange={e => setPassword(e.target.value)} className={ENTRY_INPUT} /></label>
        <label>Role<select required disabled={busy} value={role} onChange={e => setRole(e.target.value)} className={ENTRY_INPUT}><option value="">Select role</option>{roles.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}</select></label>
        <button disabled={busy || !role} className="rounded border px-4 py-2">Create User</button>
      </form>
      <button disabled={busy} className="rounded border px-4 py-2" onClick={() => void load()}>Refresh Users</button>
      <div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr><th className="p-2">Username</th><th className="p-2">Email</th><th className="p-2">Role</th><th className="p-2">Active</th></tr></thead><tbody>{users.map(u => <tr key={u.id} className="border-t"><td className="p-2">{u.username}</td><td className="p-2">{u.email}</td><td className="p-2"><select disabled={busy} aria-label={`Role for ${u.username}`} value={u.assigned_role ?? ''} onChange={e => void change(u.id, { assigned_role: Number(e.target.value) })} className="rounded border p-2"><option value="" disabled>Select role</option>{roles.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}</select></td><td className="p-2"><input type="checkbox" disabled={busy || String(u.id) === user?.id} aria-label={`Active user ${u.username}`} checked={u.is_active} onChange={e => void change(u.id, { is_active: e.target.checked })} /></td></tr>)}</tbody></table></div>
    </>}{notice && <p role="status" className="text-green-800">{notice}</p>}{error && <p role="alert" className="text-red-700">{error}</p>}</section>;
}
