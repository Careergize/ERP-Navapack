import { demoRole as resolveDemoRole } from '@/lib/demoAuth';
import { FormEvent, useRef, useState } from "react";
import axios from 'axios';
import { Eye, EyeOff, LockKeyhole, Mail } from "lucide-react";
import { Navigate, useNavigate } from "react-router-dom";
import { MOCK_LOGIN_ENABLED } from '@/lib/authSession';
import { useAuth } from "@/context/AuthContext";
import { BrandPanel } from "@/components/login/BrandPanel";
import { Button } from "@/components/login/Button";
import { TextField } from "@/components/login/TextField";

export function Login({ finance = false }: { finance?: boolean }) {
  const { user, login, loginAsDemo, loading, sessionError, retrySession } = useAuth();
  const navigate = useNavigate();
  const usernameRef = useRef<HTMLInputElement>(null);
  const [demoRole, setDemoRole] = useState<"project_manager" | "admin" | "qc_inspector" | "qc_supervisor" | "production_manager" | "store_keeper" | "accounts">("admin");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [shake, setShake] = useState(false);
  const [success, setSuccess] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (!username.trim() || !password) {
      setError("Enter your username or email and password to continue.");
      usernameRef.current?.focus();
      return;
    }
    try {
      if (MOCK_LOGIN_ENABLED) {
        loginAsDemo(resolveDemoRole(username, password, demoRole, finance));
      } else await login(username.trim(), password, remember, finance);
      if (remember) localStorage.setItem("navapack_remember", "true");
      setSuccess(true);
      window.setTimeout(() => navigate("/"), 520);
    } catch (cause) {
      if (axios.isAxiosError(cause)) {
        setError(!cause.response ? 'Cannot reach Django. Start the backend on port 8000 and try again.'
          : cause.response.status === 401 ? 'That username or password does not match. Use your Django username (for example admin).'
          : cause.response.status === 429 ? 'Too many login attempts. Wait a minute and try again.'
          : 'The backend could not complete login. Check the Django server output.');
      } else setError(cause instanceof Error && cause.message === 'credentials' ? 'Those demo credentials do not match.' : 'Unable to load your account profile. Try signing in again.');
      setShake(true);
      usernameRef.current?.focus();
      window.setTimeout(() => setShake(false), 400);
    }
  }

  if (loading && !success) return <p role="status" className="p-8">Checking your session…</p>;
  if (user && !success) return <Navigate to="/" replace />;
  return (
    <main className="min-h-screen bg-surface lg:flex">
      <BrandPanel />
      <section className="flex min-h-screen w-full flex-col px-5 py-6 [padding-bottom:calc(1.5rem+env(safe-area-inset-bottom))] sm:px-10 sm:py-10 lg:w-[45%] lg:justify-center lg:px-14 xl:px-24">
        <div className="mb-12 flex items-center justify-between lg:hidden"><img src="/assets/Nava-logo.png" alt="Nava Pack" className="h-9 w-auto max-w-[175px] object-contain" /><span className="rounded-full bg-navy/5 px-3 py-1 text-[10px] font-semibold uppercase tracking-widest text-navy">ERP Portal</span></div>
        <div className={`mx-auto w-full max-w-md animate-rise-in ${shake ? "animate-shake-once" : ""}`}>
          <div className="mb-9"><p className="mb-3 text-xs font-semibold uppercase tracking-[.2em] text-teal">Welcome back</p><h1 className="text-3xl font-semibold tracking-tight text-navy sm:text-4xl">{finance?'Sign in to Finance':'Sign in to Nava Pack'}</h1><p className="mt-3 text-sm leading-6 text-slate-500">{finance?'Access your finance dashboard, quotations, costing and invoice summaries.':'Access production, stock, orders, and traceability from one place.'}</p></div>
          <form onSubmit={handleSubmit} className="space-y-5" noValidate>
            {sessionError && <div role="alert"><p>{sessionError}</p><button type="button" onClick={retrySession} className="underline">Retry session restoration</button></div>}
            <TextField ref={usernameRef} label="Username or email" type="text" autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} placeholder="you@navapack.com" icon={<Mail className="h-4 w-4" />} required />
            <TextField label="Password" type={showPassword ? "text" : "password"} autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Enter your password" icon={<LockKeyhole className="h-4 w-4" />} required trailing={<button type="button" aria-label={showPassword ? "Hide password" : "Show password"} onClick={() => setShowPassword((visible) => !visible)} className="absolute right-1 top-1/2 flex h-10 w-10 -translate-y-1/2 items-center justify-center rounded-md text-slate-400 transition hover:bg-slate-50 hover:text-navy">{showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}</button>} />
            {MOCK_LOGIN_ENABLED && <div><p className="-mt-2 text-xs text-slate-400">Demo mode: {finance ? 'finance@navapack.com' : 'admin@navapack.com'} / test@123</p>{!finance && <label className="text-xs text-slate-500">Demo role<select className="mt-1 block w-full rounded-lg border p-2" value={demoRole} onChange={e => setDemoRole(e.target.value as typeof demoRole)}><option value="admin">Admin</option><option value="accounts">Accounts / Finance</option><option value="qc_inspector">QC Inspector</option><option value="qc_supervisor">QC Supervisor</option><option value="project_manager">Project Manager</option><option value="production_manager">Production Manager</option><option value="store_keeper">Store Keeper</option></select></label>}</div>}
            <div className="flex items-center justify-between pt-1 text-sm"><label className="flex min-h-11 cursor-pointer items-center gap-2 text-slate-600"><input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} className="h-4 w-4 rounded border-slate-300 accent-teal" /> Remember me</label><a href="mailto:support@navapack.com?subject=Password%20reset" className="font-medium text-blue transition hover:text-navy">Forgot password?</a></div>
            {error && <p role="alert" aria-live="polite" className="rounded-lg border border-red-100 bg-red-50 px-4 py-3 text-sm leading-5 text-red-700">{error}</p>}
            <Button type="submit" loading={loading} success={success} disabled={loading || success}>Sign in</Button>
          </form>
          <Link className="mt-5 inline-block text-sm text-blue underline" to={finance?'/login':'/finance/login'}>{finance?'Operations login':'Separate Finance login'}</Link>
          <p className="mt-10 border-t border-slate-200 pt-5 text-xs leading-5 text-slate-400">Need access? Contact your department manager or Nava Pack administrator.</p>
        </div>
        <footer className="mx-auto mt-auto flex w-full max-w-md justify-between pt-12 text-xs text-slate-400 lg:absolute lg:bottom-7 lg:right-14 lg:max-w-md xl:right-24"><span>© Nava Pack</span><span>v0.1.0 · Secure operations portal</span></footer>
      </section>
    </main>
  );
}
