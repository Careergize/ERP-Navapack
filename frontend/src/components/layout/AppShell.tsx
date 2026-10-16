import { QC_VIEW_ROLES, isQCRole } from '@/lib/quality';
import { QC_SECTIONS } from '@/pages/Quality/QualityPage';
import { NavLink, Outlet } from "react-router-dom";
import {
  LayoutDashboard,
  FileText,
  ClipboardList,
  Boxes,
  Package,
  Recycle,
  Calculator,
  Search,
  Settings,
  LogOut,
  Bell,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import type { Role } from "@/types";

interface NavItem {
  to: string;
  label: string;
  icon: typeof LayoutDashboard;
  roles: Role[];
}

const NAV_ITEMS: NavItem[] = [
  { to: "/quotations", label: "Quotations", icon: FileText, roles: ["project_manager", "receptionist", "accounts", "production_manager", "admin"] },
  { to: "/qc", label: "Quality Control", icon: ClipboardList, roles: QC_VIEW_ROLES },
  { to: "/", label: "Dashboard", icon: LayoutDashboard, roles: ["project_manager", "receptionist", "production_manager", "store_keeper", "production_operator", "recycling_operator", "accounts", "admin"] },
  { to: "/sales-orders", label: "Sales Orders", icon: FileText, roles: ["receptionist", "admin"] },
  { to: "/job-cards", label: "Job Cards", icon: ClipboardList, roles: ["receptionist", "production_manager", "store_keeper", "production_operator", "admin"] },
  { to: "/stock", label: "Stock", icon: Boxes, roles: ["store_keeper", "admin"] },
  { to: "/raw-materials", label: "Raw Material", icon: Package, roles: ["store_keeper", "admin"] },
  { to: "/consumables", label: "Consumables", icon: Package, roles: ["store_keeper", "admin"] },
  { to: "/recycling", label: "Recycling", icon: Recycle, roles: ["recycling_operator", "admin"] },
  { to: "/costing", label: "Costing", icon: Calculator, roles: ["accounts", "admin"] },
  { to: "/track-trace", label: "Track & Trace", icon: Search, roles: ["receptionist", "production_manager", "store_keeper", "production_operator", "recycling_operator", "accounts", "admin"] },
  { to: "/masters", label: "Masters", icon: Settings, roles: ["admin"] },
];

const FINANCE_NAV_ITEMS: NavItem[] = [
  { to: "/", label: "Finance Dashboard", icon: LayoutDashboard, roles: ["accounts"] },
  { to: "/consumables", label: "Consumables", icon: Package, roles: ["accounts"] },
  { to: "/costing", label: "Costing", icon: Calculator, roles: ["accounts"] },
  { to: "/masters", label: "Masters", icon: Settings, roles: ["accounts"] },
  { to: "/finance/quality", label: "Quality summary", icon: ClipboardList, roles: ["accounts"] },
  { to: "/quotations", label: "Quotations", icon: FileText, roles: ["accounts"] },
  { to: "/raw-materials", label: "Raw Materials", icon: Package, roles: ["accounts"] },
  { to: "/recycling", label: "Recycling", icon: Recycle, roles: ["accounts"] },
  { to: "/sales-orders", label: "Sales Orders", icon: FileText, roles: ["accounts"] },
  { to: "/stock", label: "Stocks", icon: Boxes, roles: ["accounts"] },
  { to: "/track-trace", label: "Track & Trace", icon: Search, roles: ["accounts"] },
];

export function AppShell() {
  const { user, logout } = useAuth();
  const items: NavItem[] = isQCRole(user?.role) ? [{ to: "/qc", label: "QC Dashboard", icon: LayoutDashboard, roles: QC_VIEW_ROLES }, ...QC_SECTIONS.map(([key, label]) => ({ to: `/qc/${key}`, label, icon: ClipboardList, roles: QC_VIEW_ROLES }))] : user?.role === "accounts" ? FINANCE_NAV_ITEMS : NAV_ITEMS.filter((item) => !user || item.roles.includes(user.role));

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_72%_0%,#2dbb4c_0%,#16803d_42%,#0b3c2a_100%)] p-3 sm:p-5">
      <div className={`flex min-h-[calc(100vh-2rem)] overflow-hidden rounded-[24px] bg-[#f5f8f5] shadow-2xl shadow-emerald-950/25 ${isQCRole(user?.role) ? "flex-col sm:flex-row" : ""}`}>
      <aside className={`flex shrink-0 flex-col bg-[#102d24] text-white ${isQCRole(user?.role) ? "w-full sm:w-[230px]" : "w-[230px]"}`}>
        <div className="flex items-center gap-2 px-5 py-6">
          <img src="/assets/Nava-logo.png" alt="NavaPack" className="h-8 w-auto max-w-[155px] object-contain" />
        </div>

        <div className="mx-4 mb-5 rounded-xl border border-white/10 bg-white/5 px-3 py-2">
          <p className="text-[10px] uppercase tracking-wider text-white/45">Active workspace</p>
          <p className="mt-1 text-xs font-medium text-white/90">{user?.role==='accounts'?'NavaPack Finance':'NavaPack Operations'}</p>
        </div>

        <nav className="flex-1 space-y-1 px-3">
          <p className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-white/35">Navigation</p>
          {items.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/" || to === "/qc"}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-3 py-2.5 text-[13px] font-medium transition-colors ${
                  isActive ? "bg-[#b7efbd] text-[#123b29]" : "text-white/65 hover:bg-white/10 hover:text-white"
                }`
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-white/10 px-5 py-4">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-white/15 text-xs font-semibold">{user?.name?.slice(0, 1)}</div>
            <div className="min-w-0">
              <p className="truncate text-xs font-medium text-white">{user?.name}</p>
              <p className="truncate text-[10px] capitalize text-white/45">{user?.role.replace("_", " ")}</p>
            </div>
          </div>
          <button
            onClick={logout}
            className="mt-4 flex items-center gap-2 text-xs text-white/45 hover:text-white"
          >
            <LogOut size={14} /> Sign out
          </button>
        </div>
      </aside>

      <main className="min-w-0 flex-1 overflow-y-auto bg-[#f5f8f5]">
        <div className="flex items-center justify-end gap-4 border-b border-[#e6eee8] px-5 py-4 sm:px-8">
          <button className="relative rounded-full p-2 text-[#668075] hover:bg-white" aria-label="Notifications"><Bell size={17} /><span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-[#40bd5b]" /></button>
          <div className="h-7 w-px bg-[#dce8df]" />
          <span className="text-xs text-[#668075]">Operations overview</span>
        </div>
        <div className="p-5 sm:p-8"><Outlet /></div>
      </main>
      </div>
    </div>
  );
}
