<<<<<<< HEAD:src/context/AuthContext.tsx
import { createContext, useContext, useEffect, useRef, useState, ReactNode } from "react";
import { currentUserRequest, loginRequest, type LoginResponse } from "@/lib/api";
import { AUTH_CLEARED_EVENT, MOCK_LOGIN_ENABLED, clearSession, readToken, saveTokens } from '@/lib/authSession';
=======
import { demoEnabled } from '@/lib/demoAuth';
import { createContext, useContext, useState, ReactNode } from "react";
import { loginRequest } from "@/lib/api";
>>>>>>> 34ecef126e16762b3c91dbf7bdf790e011046938:frontend/src/context/AuthContext.tsx
import type { Role, User } from "@/types";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
<<<<<<< HEAD:src/context/AuthContext.tsx
  sessionError: string;
  retrySession: () => void;
  login: (email: string, password: string, remember?: boolean) => Promise<void>;
=======
  login: (email: string, password: string, finance?:boolean) => Promise<void>;
>>>>>>> 34ecef126e16762b3c91dbf7bdf790e011046938:frontend/src/context/AuthContext.tsx
  loginAsDemo: (role: Role) => void;
  logout: () => void;
}

const DEMO_NAMES: Record<Role, string> = {
  qc_inspector: "QC Inspector",
  qc_supervisor: "QC Supervisor",
  receptionist: "Amara (Receptionist)",
  project_manager: "Project Manager",
  production_manager: "Kwame (Production Manager)",
  store_keeper: "Zola (Store Keeper)",
  production_operator: "Tunde (Production Operator)",
  recycling_operator: "Naledi (Recycling Operator)",
  accounts: "Femi (Accounts)",
  admin: "Admin",
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function toUser(data: NonNullable<LoginResponse['user']>): User {
  if (!data.id || !data.role || !Object.prototype.hasOwnProperty.call(DEMO_NAMES, data.role)) throw new Error('Invalid account profile.');
  return { id: String(data.id), name: data.name ?? data.username ?? '', role: data.role as Role, department: data.department };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [sessionError, setSessionError] = useState('');
  const [restoreAttempt, setRestoreAttempt] = useState(0);
  const generation = useRef(0);

<<<<<<< HEAD:src/context/AuthContext.tsx
  useEffect(() => {
    const onClear = () => { generation.current++; setUser(null); setSessionError(''); setLoading(false); };
    window.addEventListener(AUTH_CLEARED_EVENT, onClear);
    return () => window.removeEventListener(AUTH_CLEARED_EVENT, onClear);
  }, []);

  useEffect(() => {
    const attempt = ++generation.current;
    setLoading(true); setSessionError('');
    async function restore() {
      try {
        if (readToken('navapack_access') || readToken('navapack_refresh')) {
          const profile = await currentUserRequest();
          if (attempt === generation.current) setUser(toUser(profile));
        } else if (MOCK_LOGIN_ENABLED) {
          const raw = sessionStorage.getItem('navapack_demo_user');
          if (raw) {
            const demo = JSON.parse(raw) as User;
            if (demo && Object.prototype.hasOwnProperty.call(DEMO_NAMES, demo.role) && demo.id === `demo-${demo.role}`) setUser({ id: demo.id, name: DEMO_NAMES[demo.role], role: demo.role, department: 'Extrusion' });
            else sessionStorage.removeItem('navapack_demo_user');
          }
        }
      } catch {
        if (attempt === generation.current) {
          if (readToken('navapack_access') || readToken('navapack_refresh')) setSessionError('Unable to restore your session. Check that the backend is running, then retry.');
          else sessionStorage.removeItem('navapack_demo_user');
        }
      } finally { if (attempt === generation.current) setLoading(false); }
    }
    void restore();
    return () => { generation.current++; };
  }, [restoreAttempt]);

  async function login(email: string, password: string, remember = false) {
    setLoading(true);
    try {
      const data = await loginRequest({ username: email, password });
      saveTokens(data.access, data.refresh, remember);
      const profile = data.user ?? await currentUserRequest();
      generation.current++;
      setSessionError(''); setUser(toUser(profile));
=======
  async function login(email: string, password: string, finance=false) {
    setLoading(true);
    try {
      const data = await loginRequest({ username: email, password });
      if(finance&&data.user?.role!=='accounts')throw new Error('credentials');
      localStorage.setItem("navapack_access", data.access);
      localStorage.setItem("navapack_refresh", data.refresh);
      setUser({
        id: String(data.user?.id ?? email),
        name: data.user?.name ?? data.user?.username ?? email,
        role: (data.user?.role as Role) ?? "receptionist",
        department: data.user?.department,
      });
>>>>>>> 34ecef126e16762b3c91dbf7bdf790e011046938:frontend/src/context/AuthContext.tsx
    } finally {
      setLoading(false);
    }
  }

<<<<<<< HEAD:src/context/AuthContext.tsx
  // Demo identity is restored only while mock mode is explicitly enabled
  // in configuration. It never supplies a backend token.
  function loginAsDemo(role: Role) {
    if (!MOCK_LOGIN_ENABLED) throw new Error('Demo login is disabled.');
    clearSession();
    const demo = { id: `demo-${role}`, name: DEMO_NAMES[role], role, department: 'Extrusion' };
    sessionStorage.setItem('navapack_demo_user', JSON.stringify(demo));
    setUser(demo);
=======
  // Local demo identity, no backend call. Development defaults enabled unless
  // explicitly disabled; production requires explicit VITE_ENABLE_MOCK_LOGIN=true.
  function loginAsDemo(role: Role) {
    if(!demoEnabled(import.meta.env.DEV,import.meta.env.VITE_ENABLE_MOCK_LOGIN))throw new Error('Demo login is disabled.');
    localStorage.removeItem('navapack_access');localStorage.removeItem('navapack_refresh');localStorage.removeItem('navapack_token');
    setUser({ id: `demo-${role}`, name: DEMO_NAMES[role], role, department: role==='accounts'?'Finance':'Extrusion' });
>>>>>>> 34ecef126e16762b3c91dbf7bdf790e011046938:frontend/src/context/AuthContext.tsx
  }

  function logout() {
    clearSession();
  }

  return (
    <AuthContext.Provider value={{ user, loading, sessionError, retrySession: () => setRestoreAttempt(n => n + 1), login, loginAsDemo, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
