import { createContext, useContext, useEffect, useRef, useState, ReactNode } from "react";
import { currentUserRequest, loginRequest, logoutRequest, type LoginResponse } from "@/lib/api";
import { AUTH_CLEARED_EVENT, MOCK_LOGIN_ENABLED, clearSession, readToken, saveTokens } from '@/lib/authSession';
import { demoRole } from '@/lib/demoAuth';
import { backendProfile } from '@/lib/backendProfile';
import type { Role, User } from "@/types";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  sessionError: string;
  retrySession: () => void;
  login: (email: string, password: string, remember?: boolean, finance?: boolean) => Promise<void>;
  loginAsDemo: (role: Role) => void;
  logout: () => void;
}

const DEMO_NAMES: Record<Role, string> = {
  authenticated: "Authenticated employee",
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
  return backendProfile(data);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [sessionError, setSessionError] = useState('');
  const [restoreAttempt, setRestoreAttempt] = useState(0);
  const generation = useRef(0);

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

  async function login(email: string, password: string, remember = false, finance = false) {
    setLoading(true);
    try {
      if (MOCK_LOGIN_ENABLED) {
        loginAsDemo(demoRole(email, password, 'admin', finance));
        return;
      }
      const data = await loginRequest({ email, password });
      saveTokens(data.access, data.refresh, remember);
      const profile = data.user ?? await currentUserRequest();
      const nextUser = toUser(profile);
      if (finance) { clearSession(); throw new Error('Finance backend integration is unavailable. Use the existing operations login.'); }
      generation.current++;
      setSessionError(''); setUser(nextUser);
    } finally {
      setLoading(false);
    }
  }

  function loginAsDemo(role: Role) {
    if (!MOCK_LOGIN_ENABLED || role === 'authenticated') throw new Error('Demo login is disabled for this identity.');
    clearSession();
    const demo = { id: `demo-${role}`, name: DEMO_NAMES[role], role, department: 'Extrusion' };
    sessionStorage.setItem('navapack_demo_user', JSON.stringify(demo));
    setUser(demo);
  }

  function logout() {
    if (user?.backendSession) {
      void logoutRequest().then(() => clearSession()).catch(() => setSessionError('Logout could not revoke the session. Check the connection and retry sign out.'));
    } else clearSession();
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
