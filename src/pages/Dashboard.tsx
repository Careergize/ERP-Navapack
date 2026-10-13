import { QuotationMetrics } from '@/pages/Quotations/QuotationList';
import { QUOTATION_VIEW_ROLES } from '@/lib/quotations';
import type { ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Card } from "@/components/ui/Card";
import { useAuth } from "@/context/AuthContext";
import { BarChart3, Leaf, MoreHorizontal, Plus } from "lucide-react";

// ---------------------------------------------------------------------------
// Demo-mode placeholder data — replace with real aggregates once the backend is live.
// ---------------------------------------------------------------------------

type IconName = "orders" | "jobcard" | "check" | "bolt" | "alert" | "recycle" | "doc" | "stock" | "waste" | "currency";
type Priority = "high" | "medium" | "low";
type Trend = "up" | "down" | "flat";
type SectionKey = "workflow" | "attention" | "activity" | "production" | "stock" | "waste" | "costing" | "recycling";

interface Widget {
  label: string;
  value: string;
  icon: IconName;
  delta?: string;
  trend?: Trend;
  spark?: number[];
}

interface Task {
  title: string;
  meta: string;
  priority: Priority;
}

const CURRENCY = "₹";
const USD_RATE = 83.2; // entered by Accounts; applied to all USD raw-material purchases

// Each role sees only the widgets and sections relevant to what they need to act on today.
const ROLE_WIDGETS: Record<string, Widget[]> = {
  receptionist: [
    { label: "Open sales orders", value: "2", icon: "orders", delta: "+1 today", trend: "up", spark: [1, 1, 2, 1, 2, 2, 2] },
    { label: "Orders without a job card", value: "0", icon: "jobcard", delta: "All allocated", trend: "flat", spark: [2, 1, 1, 0, 1, 0, 0] },
  ],
  production_manager: [
    { label: "Job cards awaiting my approval", value: "1", icon: "check", delta: "Oldest: 2 days", trend: "down", spark: [0, 2, 1, 3, 2, 1, 1] },
    { label: "In production, my department", value: "1", icon: "bolt", delta: "On schedule", trend: "flat", spark: [1, 1, 2, 2, 1, 1, 1] },
    { label: "Waste this month (kg)", value: "180", icon: "waste", delta: "-8%", trend: "down", spark: [240, 230, 215, 205, 200, 190, 180] },
  ],
  store_keeper: [
    { label: "Approved, awaiting material issue", value: "1", icon: "check", delta: "+1 today", trend: "up", spark: [0, 0, 1, 0, 2, 1, 1] },
    { label: "Low stock raw materials", value: "3", icon: "alert", delta: "+2 this week", trend: "up", spark: [1, 1, 1, 2, 2, 3, 3] },
  ],
  production_operator: [
    { label: "My stages in progress", value: "1", icon: "bolt", delta: "On schedule", trend: "flat", spark: [1, 2, 1, 1, 2, 1, 1] },
    { label: "Output logged today", value: "2,400 pcs", icon: "stock", delta: "+320 pcs", trend: "up", spark: [1800, 2100, 1900, 2200, 2050, 2300, 2400] },
  ],
  recycling_operator: [
    { label: "Waste awaiting recycling", value: "180 kg", icon: "recycle", delta: "+24 kg", trend: "up", spark: [90, 110, 105, 140, 150, 165, 180] },
    { label: "Granules produced this month", value: "1,240 kg", icon: "recycle", delta: "+12%", trend: "up", spark: [700, 820, 900, 980, 1050, 1160, 1240] },
  ],
  accounts: [
    { label: "Costing pending review", value: "2", icon: "doc", delta: "Same as last week", trend: "flat", spark: [3, 2, 2, 3, 2, 2, 2] },
    { label: "USD rate in use", value: `${CURRENCY}${USD_RATE.toFixed(2)}`, icon: "currency", delta: "Updated today", trend: "flat", spark: [82.6, 82.9, 83.0, 83.1, 83.0, 83.3, 83.2] },
  ],
  admin: [
    { label: "Open sales orders", value: "2", icon: "orders", delta: "+1 today", trend: "up", spark: [1, 1, 2, 1, 2, 2, 2] },
    { label: "Job cards in production", value: "1", icon: "bolt", delta: "On schedule", trend: "flat", spark: [1, 1, 2, 2, 1, 1, 1] },
    { label: "Waste this month (kg)", value: "180", icon: "waste", delta: "-8%", trend: "down", spark: [240, 230, 215, 205, 200, 190, 180] },
    { label: "Granules in stock", value: "500 kg", icon: "recycle", delta: "+240 kg", trend: "up", spark: [260, 300, 380, 420, 450, 480, 500] },
  ],
};

const ROLE_SECTIONS: Record<string, SectionKey[]> = {
  receptionist: ["workflow", "attention", "activity"],
  production_manager: ["workflow", "attention", "production", "waste", "activity"],
  store_keeper: ["workflow", "attention", "stock", "activity"],
  production_operator: ["production", "attention", "waste"],
  recycling_operator: ["recycling", "attention", "waste"],
  accounts: ["costing", "stock", "attention", "activity"],
  admin: ["workflow", "attention", "activity", "production", "stock", "waste", "costing", "recycling"],
};

const ROLE_ACTION: Record<string, string> = {
  receptionist: "New sales order",
  production_manager: "Review job cards",
  store_keeper: "Issue materials",
  production_operator: "Log stage output",
  recycling_operator: "Record recycling batch",
  accounts: "Update USD rate",
  admin: "New sales order",
};

const ROLE_ACTION_PATH: Record<string, string> = {
  receptionist: "/sales-orders/new",
  production_manager: "/job-cards",
  store_keeper: "/stock",
  production_operator: "/job-cards",
  recycling_operator: "/recycling",
  accounts: "/costing",
  admin: "/sales-orders/new",
};

const ROLE_TASKS: Record<string, Task[]> = {
  receptionist: [
    { title: "Allocate a job card to SO-1042", meta: "Sales order saved without a job card", priority: "high" },
    { title: "Review new enquiry from Apex Packaging", meta: "Received 2 hours ago", priority: "medium" },
  ],
  production_manager: [
    { title: "Approve job card JC-0318", meta: "Raised from SO-1042 · waiting 2 days", priority: "high" },
    { title: "Check bag making output for JC-0316", meta: "Output lower than input by 3.4%", priority: "medium" },
  ],
  store_keeper: [
    { title: "Issue material for JC-0318", meta: "Approved · HDPE resin 250 kg", priority: "high" },
    { title: "Reorder LDPE resin", meta: "Below minimum level", priority: "medium" },
  ],
  production_operator: [
    { title: "Record output for bag making on JC-0317", meta: "Started 09:40 · input 1,200 pcs", priority: "medium" },
  ],
  recycling_operator: [
    { title: "Start grinding batch W-092", meta: "180 kg of waste waiting", priority: "medium" },
    { title: "Dispatch 500 kg granules to Shree Polymers", meta: "Sale order confirmed", priority: "high" },
  ],
  accounts: [
    { title: "Review costing for JC-0315", meta: "Production complete", priority: "high" },
    { title: "Enter today's USD exchange rate", meta: "Needed for the resin purchase in USD", priority: "medium" },
  ],
  admin: [
    { title: "Approve job card JC-0318", meta: "Waiting 2 days", priority: "high" },
    { title: "Reorder LDPE resin", meta: "Below minimum level", priority: "medium" },
    { title: "Review costing for JC-0315", meta: "Production complete", priority: "low" },
  ],
};

// Sales Order → Job Card → Production Manager Approval → Store Issue
const WORKFLOW = [
  { stage: "Sales order", count: 2, note: "Created by Reception" },
  { stage: "Job card", count: 1, note: "Materials filled in automatically" },
  { stage: "Manager approval", count: 1, note: "Waiting on Production Manager" },
  { stage: "Store issue", count: 1, note: "Waiting on Store Keeper" },
];

// Points/Model → Job Card → Finishing Machine → Bag Making → Next Level → Stock Keeping
type StageStatus = "Running" | "Completed" | "Waiting";
const PRODUCTION: { stage: string; jobCard: string; input: string; output: string; status: StageStatus }[] = [
  { stage: "Finishing machine", jobCard: "JC-0316", input: "2,500 pcs", output: "2,480 pcs", status: "Completed" },
  { stage: "Bag making", jobCard: "JC-0316", input: "2,480 pcs", output: "2,395 pcs", status: "Running" },
  { stage: "Next production level", jobCard: "JC-0317", input: "1,200 pcs", output: "—", status: "Waiting" },
  { stage: "Stock keeping", jobCard: "JC-0314", input: "3,000 pcs", output: "3,000 pcs", status: "Completed" },
];

// Month-end stock in kg. Closing stock is calculated, not stored.
const MONTHLY_STOCK = [
  { item: "HDPE resin", opening: 1800, inward: 2500, outward: 2350 },
  { item: "LDPE resin", opening: 900, inward: 600, outward: 1050 },
  { item: "Master batch", opening: 210, inward: 150, outward: 180 },
  { item: "Printing ink", opening: 85, inward: 40, outward: 62 },
];

const WASTE_BY_ITEM = [
  { item: "Model A bag", waste: 62, output: 2400 },
  { item: "Model B bag", waste: 74, output: 2150 },
  { item: "Model C bag", waste: 44, output: 1900 },
];

// Cost per 1,000 pcs, in local currency. USD purchases are converted at USD_RATE first.
const COSTING = [
  { model: "Model A", raw: 4200, production: 1300, other: 500 },
  { model: "Model B", raw: 5600, production: 1500, other: 700 },
  { model: "Model C", raw: 3100, production: 900, other: 400 },
];

const RECYCLING = { received: 1420, produced: 1240, sold: 1000, openingStock: 260 };

const ACTIVITY = [
  { who: "Priya S.", what: "created job card JC-0318 from SO-1042", when: "10 min ago" },
  { who: "Ravi K.", what: "issued 120 kg HDPE to JC-0316", when: "1 hr ago" },
  { who: "Anita M.", what: "completed recycling batch W-091", when: "3 hrs ago" },
  { who: "Suresh P.", what: "dispatched 500 kg granules to Shree Polymers", when: "Yesterday" },
];

// ---------------------------------------------------------------------------
// Small presentational helpers
// ---------------------------------------------------------------------------

const ICON_PATHS: Record<IconName, string> = {
  orders:
    "M2.25 3h1.386c.51 0 .955.343 1.087.835l.383 1.437M7.5 14.25a3 3 0 00-3 3h15.75m-12.75-3h11.218c1.121-2.3 2.1-4.684 2.924-7.138a60.114 60.114 0 00-16.536-1.84M7.5 14.25L5.106 5.272M6 20.25a.75.75 0 11-1.5 0 .75.75 0 011.5 0zm12.75 0a.75.75 0 11-1.5 0 .75.75 0 011.5 0z",
  jobcard:
    "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 012-2h2a2 2 0 012 2M9 5a2 2 0 002 2h2a2 2 0 002-2",
  check: "M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
  bolt: "M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z",
  alert:
    "M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z",
  recycle:
    "M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99",
  doc: "M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z",
  stock: "M21 7.5l-9-5.25L3 7.5m18 0l-9 5.25m9-5.25v9l-9 5.25M3 7.5l9 5.25M3 7.5v9l9 5.25m0-9v9",
  waste:
    "M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0",
  currency:
    "M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
};

function Icon({ name, className = "h-5 w-5" }: { name: IconName; className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true">
      <path d={ICON_PATHS[name]} />
    </svg>
  );
}

function Sparkline({ data, className = "" }: { data: number[]; className?: string }) {
  const w = 96;
  const h = 32;
  const min = Math.min(...data);
  const range = Math.max(...data) - min || 1;
  const points = data.map((v, i) => `${(i / (data.length - 1)) * w},${h - 4 - ((v - min) / range) * (h - 8)}`).join(" ");
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className={`h-8 w-24 ${className}`} aria-hidden="true">
      <polyline points={points} fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

const PRIORITY_STYLE: Record<Priority, { chip: string; label: string }> = {
  high: { chip: "bg-red-50 text-red-700 ring-red-600/20", label: "Urgent" },
  medium: { chip: "bg-amber-50 text-amber-700 ring-amber-600/20", label: "Today" },
  low: { chip: "bg-emerald-50 text-emerald-700 ring-emerald-600/20", label: "Can wait" },
};

const STATUS_STYLE: Record<StageStatus, string> = {
  Running: "bg-sky-50 text-sky-700 ring-sky-600/20",
  Completed: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
  Waiting: "bg-amber-50 text-amber-700 ring-amber-600/20",
};

const TREND_STYLE: Record<Trend, string> = {
  up: "text-emerald-600",
  down: "text-amber-600",
  flat: "text-gray-500",
};

const fmt = (n: number) => n.toLocaleString("en-IN");
const initials = (name: string) =>
  name
    .split(" ")
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

function Panel({ title, subtitle, right, children }: { title: string; subtitle?: string; right?: ReactNode; children: ReactNode }) {
  return (
    <Card>
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-navy">{title}</h2>
          {subtitle && <p className="mt-0.5 text-xs text-gray-500">{subtitle}</p>}
        </div>
        {right}
      </div>
      <div className="mt-4">{children}</div>
    </Card>
  );
}

// Two panels side by side (3/5 + 2/5); a lone panel takes the full width so nothing leaves a gap.
function Pair({ left, right }: { left: ReactNode | null; right: ReactNode | null }) {
  if (!left && !right) return null;
  const both = Boolean(left && right);
  return (
    <section className="grid grid-cols-1 gap-4 lg:grid-cols-5">
      {left && <div className={both ? "lg:col-span-3" : "lg:col-span-5"}>{left}</div>}
      {right && <div className={both ? "lg:col-span-2" : "lg:col-span-5"}>{right}</div>}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Sections
// ---------------------------------------------------------------------------

function WorkflowSection() {
  return (
    <Panel title="Order workflow" subtitle="Sales order to store issue, with what is waiting at each step">
      <ol className="flex flex-col gap-3 md:flex-row md:items-stretch">
        {WORKFLOW.map((s, i) => (
          <li key={s.stage} className="flex flex-1 items-center gap-3">
            <div className="flex-1 rounded-lg border border-gray-200 p-4">
              <p className="text-sm text-gray-500">{s.stage}</p>
              <p className="mt-1 text-2xl font-semibold text-navy">{s.count}</p>
              <p className="mt-1 text-xs text-gray-500">{s.note}</p>
            </div>
            {i < WORKFLOW.length - 1 && (
              <svg viewBox="0 0 24 24" className="hidden h-5 w-5 shrink-0 text-gray-300 md:block" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden="true">
                <path d="M9 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            )}
          </li>
        ))}
      </ol>
    </Panel>
  );
}

function AttentionSection({ tasks }: { tasks: Task[] }) {
  return (
    <Panel title="Needs your attention" right={<span className="text-xs text-gray-500">{tasks.length} open</span>}>
      {tasks.length === 0 ? (
        <p className="text-sm text-gray-500">Nothing waiting on you right now.</p>
      ) : (
        <ul className="divide-y divide-gray-100">
          {tasks.map((t) => (
            <li key={t.title} className="flex items-center justify-between gap-4 py-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-gray-900">{t.title}</p>
                <p className="mt-0.5 truncate text-xs text-gray-500">{t.meta}</p>
              </div>
              <span className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${PRIORITY_STYLE[t.priority].chip}`}>
                {PRIORITY_STYLE[t.priority].label}
              </span>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}

function ActivitySection() {
  return (
    <Panel title="Recent activity">
      <ul className="space-y-4">
        {ACTIVITY.map((a) => (
          <li key={a.what} className="flex items-start gap-3">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gray-100 text-xs font-semibold text-gray-600">{initials(a.who)}</div>
            <p className="min-w-0 flex-1 text-sm text-gray-700">
              <span className="font-medium text-gray-900">{a.who}</span> {a.what}
            </p>
            <span className="shrink-0 text-xs text-gray-400">{a.when}</span>
          </li>
        ))}
      </ul>
    </Panel>
  );
}

function ProductionSection() {
  return (
    <Panel title="Production flow" subtitle="Each stage records input, output and status; output moves to the next department">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[520px] text-left text-sm">
          <thead className="text-xs text-gray-500">
            <tr>
              <th className="pb-2 font-medium">Stage</th>
              <th className="pb-2 font-medium">Job card</th>
              <th className="pb-2 text-right font-medium">Input</th>
              <th className="pb-2 text-right font-medium">Output</th>
              <th className="pb-2 pl-4 font-medium">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {PRODUCTION.map((r) => (
              <tr key={r.stage}>
                <td className="py-3 font-medium text-gray-900">{r.stage}</td>
                <td className="py-3 text-gray-600">{r.jobCard}</td>
                <td className="py-3 text-right tabular-nums text-gray-600">{r.input}</td>
                <td className="py-3 text-right tabular-nums text-gray-600">{r.output}</td>
                <td className="py-3 pl-4">
                  <span className={`rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${STATUS_STYLE[r.status]}`}>{r.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}

function StockSection({ monthLabel }: { monthLabel: string }) {
  return (
    <Panel
      title="Raw material stock"
      subtitle={`${monthLabel} · kg · closing stock is calculated automatically`}
      right={
        <Link to="/stock" className="text-xs font-medium text-navy hover:underline">
          View full stock
        </Link>
      }
    >
      <div className="overflow-x-auto">
        <table className="w-full min-w-[420px] text-left text-sm">
          <thead className="text-xs text-gray-500">
            <tr>
              <th className="pb-2 font-medium">Item</th>
              <th className="pb-2 text-right font-medium">Opening</th>
              <th className="pb-2 text-right font-medium">Inward</th>
              <th className="pb-2 text-right font-medium">Outward</th>
              <th className="pb-2 text-right font-medium">Closing</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {MONTHLY_STOCK.map((r) => (
              <tr key={r.item}>
                <td className="py-3 font-medium text-gray-900">{r.item}</td>
                <td className="py-3 text-right tabular-nums text-gray-600">{fmt(r.opening)}</td>
                <td className="py-3 text-right tabular-nums text-emerald-700">+{fmt(r.inward)}</td>
                <td className="py-3 text-right tabular-nums text-amber-700">-{fmt(r.outward)}</td>
                <td className="py-3 text-right font-semibold tabular-nums text-navy">{fmt(r.opening + r.inward - r.outward)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}

function WasteSection() {
  const rows = WASTE_BY_ITEM.map((r) => ({ ...r, pct: (r.waste / r.output) * 100 }));
  const maxPct = Math.max(...rows.map((r) => r.pct));
  return (
    <Panel title="Waste by item" subtitle="Waste recorded during production, as a share of output">
      <ul className="space-y-4">
        {rows.map((r) => (
          <li key={r.item}>
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-700">{r.item}</span>
              <span className="tabular-nums text-gray-500">
                {r.waste} kg · <span className="font-medium text-navy">{r.pct.toFixed(1)}%</span>
              </span>
            </div>
            <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-gray-100">
              <div className="h-full rounded-full bg-amber-500" style={{ width: `${(r.pct / maxPct) * 100}%` }} />
            </div>
          </li>
        ))}
      </ul>
    </Panel>
  );
}

function CostingSection() {
  const totals = COSTING.map((c) => c.raw + c.production + c.other);
  const max = Math.max(...totals);
  const parts = [
    { key: "raw", label: "Raw material", color: "bg-navy" },
    { key: "production", label: "Production", color: "bg-sky-500" },
    { key: "other", label: "Other", color: "bg-gray-300" },
  ] as const;

  return (
    <Panel
      title="Costing by model"
      subtitle="Per 1,000 pcs · USD purchases converted at the rate below"
      right={
        <span className="shrink-0 rounded-md bg-gray-100 px-2 py-1 text-xs font-medium text-gray-700">
          1 USD = {CURRENCY}
          {USD_RATE.toFixed(2)}
        </span>
      }
    >
      <ul className="space-y-4">
        {COSTING.map((c, i) => (
          <li key={c.model}>
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium text-gray-900">{c.model}</span>
              <span className="tabular-nums font-semibold text-navy">
                {CURRENCY}
                {fmt(totals[i])}
              </span>
            </div>
            <div className="mt-1 flex h-2.5 overflow-hidden rounded-full bg-gray-100" style={{ width: `${(totals[i] / max) * 100}%` }}>
              {parts.map((p) => (
                <div key={p.key} className={p.color} style={{ width: `${(c[p.key] / totals[i]) * 100}%` }} title={`${p.label}: ${CURRENCY}${fmt(c[p.key])}`} />
              ))}
            </div>
          </li>
        ))}
      </ul>
      <div className="mt-4 flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500">
        {parts.map((p) => (
          <span key={p.key} className="inline-flex items-center gap-1.5">
            <span className={`h-2 w-2 rounded-full ${p.color}`} />
            {p.label}
          </span>
        ))}
      </div>
    </Panel>
  );
}

function RecyclingSection() {
  const closing = RECYCLING.openingStock + RECYCLING.produced - RECYCLING.sold;
  const yieldPct = Math.round((RECYCLING.produced / RECYCLING.received) * 100);
  const stats = [
    { label: "Waste received", value: `${fmt(RECYCLING.received)} kg` },
    { label: "Granules produced", value: `${fmt(RECYCLING.produced)} kg` },
    { label: "Sold or transferred", value: `${fmt(RECYCLING.sold)} kg` },
    { label: "Closing granules stock", value: `${fmt(closing)} kg` },
  ];
  return (
    <Panel title="Recycling this month" subtitle="Waste in, granules out, and what has been sold">
      <dl className="grid grid-cols-2 gap-3">
        {stats.map((s) => (
          <div key={s.label} className="rounded-lg border border-gray-200 p-3">
            <dt className="text-xs text-gray-500">{s.label}</dt>
            <dd className="mt-1 text-lg font-semibold tabular-nums text-navy">{s.value}</dd>
          </div>
        ))}
      </dl>
      <div className="mt-4">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-700">Waste converted to granules</span>
          <span className="font-medium text-navy">{yieldPct}%</span>
        </div>
        <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-gray-100">
          <div className="h-full rounded-full bg-emerald-500" style={{ width: `${yieldPct}%` }} />
        </div>
      </div>
    </Panel>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const role = user?.role ?? "";
  const widgets = ROLE_WIDGETS[role] ?? [];
  const tasks = ROLE_TASKS[role] ?? [];
  const sections = new Set(ROLE_SECTIONS[role] ?? []);
  const has = (k: SectionKey) => sections.has(k);

  const now = new Date();
  const today = now.toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long" });
  const monthLabel = now.toLocaleDateString("en-IN", { month: "long", year: "numeric" });

  return (
    <div className="space-y-6">
      {/* Header */}
      <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.16em] text-[#6b8577]">{monthLabel} · sustainability operations</p>
          <h1 className="mt-1 text-3xl font-semibold tracking-tight text-[#173b2d]">Good morning, {user?.name.split(" ")[0] ?? "there"}</h1>
          <p className="mt-1 text-sm text-[#7c9186]">Here’s the latest pulse across your packaging operation.</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="hidden rounded-full bg-white px-3 py-2 text-xs font-medium text-[#678074] shadow-sm sm:inline">{today}</span>
          {ROLE_ACTION[role] && (
            <button type="button" onClick={() => navigate(ROLE_ACTION_PATH[role])} className="inline-flex items-center gap-2 rounded-xl bg-[#163d2f] px-4 py-2.5 text-xs font-semibold text-white shadow-sm transition hover:bg-[#245741]">
              <Plus size={15} /> {ROLE_ACTION[role]}
            </button>
          )}
        </div>
      </header>

      {QUOTATION_VIEW_ROLES.includes(user?.role ?? "") && <div className="mb-6"><h2 className="mb-3 font-semibold text-navy">Quotation pipeline (session records)</h2><QuotationMetrics /></div>}

      {/* KPI widgets */}
      <section aria-label="Key numbers" className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {widgets.map((w, index) => (
          <Card key={w.label} className={`overflow-hidden border-0 p-4 shadow-sm ${index === 0 ? "bg-[#102d24] text-white" : "bg-white"}`}>
            <div className="flex items-start justify-between gap-3">
              <div className={`flex h-9 w-9 items-center justify-center rounded-xl ${index === 0 ? "bg-[#285e42] text-[#83e997]" : "bg-[#e9f6eb] text-[#36a752]"}`}><Icon name={w.icon} className="h-4 w-4" /></div>
              {w.spark && <Sparkline data={w.spark} className={index === 0 ? "text-[#6cdb7d]" : w.trend ? TREND_STYLE[w.trend] : "text-gray-400"} />}
            </div>
            <p className={`mt-5 text-xs ${index === 0 ? "text-white/60" : "text-[#87988f]"}`}>{w.label}</p>
            <p className={`mt-1 text-2xl font-semibold tracking-tight ${index === 0 ? "text-white" : "text-[#173b2d]"}`}>{w.value}</p>
            {w.delta && <p className={`mt-1 text-[11px] font-medium ${index === 0 ? "text-[#81e193]" : w.trend ? TREND_STYLE[w.trend] : "text-gray-500"}`}>{w.trend === "up" && "↗ "}{w.trend === "down" && "↘ "}{w.delta}</p>}
          </Card>
        ))}
      </section>

      <section className="grid grid-cols-1 gap-4 xl:grid-cols-[1.65fr_1fr]">
        <Card className="border-0 bg-white p-5 shadow-sm sm:p-6">
          <div className="flex items-start justify-between">
            <div><div className="flex items-center gap-2"><BarChart3 size={16} className="text-[#3ab958]" /><h2 className="text-sm font-semibold text-[#173b2d]">Production flow</h2></div><p className="mt-1 text-xs text-[#8a9a91]">Output across the last 8 working weeks</p></div>
            <button className="rounded-lg p-1 text-[#8a9a91] hover:bg-[#f2f7f3]" aria-label="More production options"><MoreHorizontal size={18} /></button>
          </div>
          <div className="mt-5 flex h-40 items-end gap-2 rounded-xl bg-[#fbfdfb] px-3 pb-3 pt-5 sm:gap-3">
            {[42, 55, 38, 70, 54, 82, 67, 91, 76, 87, 68, 96, 82, 100, 88, 94].map((height, i) => <div key={i} className={`flex-1 rounded-t-md ${i > 7 ? "bg-[#43c45b]" : "bg-[#ccebd1]"}`} style={{ height: `${height}%` }} />)}
          </div>
          <div className="mt-3 flex justify-between text-[10px] text-[#9aaa9f]"><span>W1</span><span>W2</span><span>W3</span><span>W4</span><span>W5</span><span>W6</span><span>W7</span><span>W8</span></div>
        </Card>

        <Card className="border-0 bg-[#e2f3e5] p-5 shadow-sm sm:p-6">
          <div className="flex items-start justify-between"><div><p className="text-xs text-[#71917a]">Circularity score</p><p className="mt-2 text-4xl font-semibold tracking-tight text-[#173b2d]">{Math.round((RECYCLING.produced / RECYCLING.received) * 100)}<span className="text-lg font-normal text-[#6b9175]">%</span></p></div><div className="rounded-xl bg-white/70 p-2 text-[#36ad51]"><Leaf size={19} /></div></div>
          <p className="mt-2 text-xs font-medium text-[#43a45a]">↗ 12% from last month</p>
          <div className="mt-6 space-y-3"><div className="flex items-center justify-between text-xs text-[#557561]"><span>Waste converted to granules</span><span className="font-semibold">{fmt(RECYCLING.produced)} kg</span></div><div className="h-2 overflow-hidden rounded-full bg-white/80"><div className="h-full rounded-full bg-[#35b653]" style={{ width: `${Math.round((RECYCLING.produced / RECYCLING.received) * 100)}%` }} /></div><div className="grid grid-cols-2 gap-3 pt-1"><div><p className="text-[10px] text-[#73917c]">Received this month</p><p className="mt-1 text-sm font-semibold text-[#173b2d]">{fmt(RECYCLING.received)} kg</p></div><div><p className="text-[10px] text-[#73917c]">Granules in stock</p><p className="mt-1 text-sm font-semibold text-[#173b2d]">{fmt(RECYCLING.openingStock + RECYCLING.produced - RECYCLING.sold)} kg</p></div></div></div>
        </Card>
      </section>

      <Pair left={has("attention") ? <AttentionSection tasks={tasks} /> : null} right={has("activity") ? <ActivitySection /> : null} />
      <Pair left={has("stock") ? <StockSection monthLabel={monthLabel} /> : null} right={has("waste") ? <WasteSection /> : null} />
      <Pair left={has("costing") ? <CostingSection /> : null} right={has("recycling") ? <RecyclingSection /> : null} />
      {has("workflow") && <WorkflowSection />}
      {has("production") && <ProductionSection />}
    </div>
  );
}
