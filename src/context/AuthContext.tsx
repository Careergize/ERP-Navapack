import { createContext, useContext, useState, ReactNode } from "react";
import { loginRequest } from "@/lib/api";
import type { Role, User } from "@/types";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  loginAsDemo: (role: Role) => void;
  logout: () => void;
}

const DEMO_NAMES: Record<Role, string> = {
  qc_inspector: "QC Inspector",
  qc_supervisor: "QC Supervisor",
  receptionist: "Amara (Receptionist)",
  production_manager: "Kwame (Production Manager)",
  store_keeper: "Zola (Store Keeper)",
  production_operator: "Tunde (Production Operator)",
  recycling_operator: "Naledi (Recycling Operator)",
  accounts: "Femi (Accounts)",
  admin: "Admin",
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(false);

  async function login(email: string, password: string) {
    setLoading(true);
    try {
      const data = await loginRequest({ username: email, password });
      localStorage.setItem("navapack_access", data.access);
      localStorage.setItem("navapack_refresh", data.refresh);
      setUser({
        id: String(data.user?.id ?? email),
        name: data.user?.name ?? data.user?.username ?? email,
        role: (data.user?.role as Role) ?? "receptionist",
        department: data.user?.department,
      });
    } finally {
      setLoading(false);
    }
  }

  // Dev-only: signs in locally with a fake user, no backend call.
  // Lets you demo the UI before the Django API exists. Not shipped in
  // production builds — guarded by import.meta.env.DEV.
  function loginAsDemo(role: Role) {
    setUser({ id: `demo-${role}`, name: DEMO_NAMES[role], role, department: "Extrusion" });
  }

  function logout() {
    localStorage.removeItem("navapack_token");
    localStorage.removeItem("navapack_access");
    localStorage.removeItem("navapack_refresh");
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, loginAsDemo, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
