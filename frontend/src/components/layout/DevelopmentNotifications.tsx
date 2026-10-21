import {useState} from 'react';
import {Link} from 'react-router-dom';
import {Bell} from 'lucide-react';
import {rehearsalDashboard} from '@/lib/rehearsalApi';
import {useAuth} from '@/context/AuthContext';
type Notice={id:string;status:string;href:string;message:string};
export function DevelopmentNotifications(){
 const {user}=useAuth();const [open,setOpen]=useState(false),[rows,setRows]=useState<Notice[]>(),[error,setError]=useState('');
 async function toggle(){setOpen(!open);if(open)return;setRows(undefined);setError('');try{const data=await rehearsalDashboard();setRows(data.notifications as Notice[]);}catch{setError('Development notifications unavailable. Check API access and the active development database.');}}
 if(!user?.backendSession||!user.permissions?.includes('rehearsal.use_simulation'))return <span className="rounded-full p-2" title="No notification capability"><Bell size={17}/></span>;
 return <div className="relative"><button aria-label="Development notifications" aria-expanded={open} onClick={toggle} className="rounded-full p-2"><Bell size={17}/></button>{open&&<section className="absolute right-0 top-10 z-40 max-h-96 w-72 overflow-auto rounded-xl border bg-white p-4 space-y-3"><h2 className="font-semibold">Development notifications</h2><p className="text-xs">Derived from your persisted synthetic jobs. No customer messages are sent.</p>{!rows&&!error&&<p role="status">Loading…</p>}{rows?.map(r=><Link className="block border-b py-2 text-sm underline" key={r.id} to={r.href} onClick={()=>setOpen(false)}>{r.message} · {r.id.slice(0,8)}</Link>)}{rows?.length===0&&<p>No actionable development jobs.</p>}{error&&<p role="alert">{error}</p>}</section>}</div>;
}
