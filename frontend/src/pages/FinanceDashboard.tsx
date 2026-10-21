import { QualityFoundation } from '@/pages/Inventory/QualityFoundation';
import { PersistedDashboard } from '@/pages/PersistedDashboard';
import { useAuth } from '@/context/AuthContext';
import { useInventory } from '@/context/InventoryContext';
import { useJobCards } from '@/context/JobCardsContext';
import { orderFulfillmentStatus } from '@/lib/fulfillment';
import { useQuality } from '@/context/QualityContext';
import { effectiveQuotationStatus } from '@/lib/quotations';
import { useMemo } from "react";
import { Link } from "react-router-dom";
import { ArrowDownRight, ArrowUpRight, Banknote, CircleHelp, FileClock, FileText, ReceiptText, ShoppingCart } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { useInvoices } from "@/context/InvoicesContext";
import { useQuotations } from "@/context/QuotationsContext";
import { useSalesOrders } from "@/context/SalesOrdersContext";

const money = (amount: number, currency: string) => {
  try {
    return new Intl.NumberFormat(undefined, { style: "currency", currency, maximumFractionDigits: 2 }).format(amount);
  } catch {
    return `${currency} ${amount.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
  }
};

export function FinanceDashboard() {
 const { user } = useAuth();
 return user?.backendSession ? <PersistedDashboard finance/> : <DemoFinanceDashboard/>;
}
function DemoFinanceDashboard() {
  const { invoices } = useInvoices();
  const { quotations } = useQuotations();
  const { orders } = useSalesOrders();
  const { ledger } = useInventory();const { cards } = useJobCards();

  const totalsByCurrency = useMemo(() => invoices.reduce<Record<string, number>>((totals, invoice) => {
    totals[invoice.currency] = (totals[invoice.currency] ?? 0) + invoice.total;
    return totals;
  }, {}), [invoices]);
  const currencyEntries = Object.entries(totalsByCurrency).sort(([a], [b]) => a.localeCompare(b));
  const totalSales = currencyEntries.length === 1 ? money(currencyEntries[0][1], currencyEntries[0][0]) : currencyEntries.length > 1 ? "Multiple currencies" : "—";
  const pendingQuotationCount = quotations.filter(q => !quotations.some(n=>n.rootId===q.rootId&&n.revision>q.revision) && ["Draft", "Pending Internal Approval", "Approved", "Sent"].includes(effectiveQuotationStatus(q))).length;
  const openOrderCount = orders.filter(order => !["Completed", "Dispatched", "Cancelled"].includes(orderFulfillmentStatus(order,ledger,cards))).length;

  const activities = [
    ...invoices.map(invoice => ({ date: invoice.date, title: `Invoice ${invoice.number}`, detail: `${invoice.buyer} · ${money(invoice.total, invoice.currency)}`, href: `/sales-orders/${invoice.orderId}`, kind: "Invoice" })),
    ...quotations.map(quotation => ({ date: quotation.date, title: `Quotation ${quotation.number}`, detail: `${quotation.customer.name || "Customer not selected"} · ${quotation.status}`, href: `/quotations/${quotation.id}`, kind: "Quotation" })),
    ...orders.map(order => ({ date: order.date, title: `Sales order ${order.orderNumber}`, detail: `${order.customerName} · ${order.status}`, href: `/sales-orders/${order.id}`, kind: "Sales order" })),
  ].sort((a, b) => b.date.localeCompare(a.date)).slice(0, 6);

  const maxTotal = Math.max(1, ...currencyEntries.map(([, amount]) => amount));

  return <div className="space-y-5">
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div>
        <p className="text-xs font-medium uppercase tracking-[0.16em] text-[#6b8c78]">Finance workspace</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-[#173b2d]">Finance Dashboard</h1>
      </div>
      <Link to="/quotations" className="inline-flex items-center gap-2 rounded-lg bg-[#173b2d] px-3 py-2 text-xs font-medium text-white hover:bg-[#24543a]"><FileText size={15} /> View quotations</Link>
    </div>

    <p className="rounded-lg border border-[#dcebe0] bg-white px-3 py-2 text-xs text-[#668075]">Figures use current frontend session records. Sales orders include seeded demo examples; invoices and quotations are session-only. Expenses and payment collections are not recorded here.</p>

    <section aria-label="Finance summary" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      <Metric label="Invoiced value" value={totalSales} icon={Banknote} note={invoices.length ? `${invoices.length} recorded invoice${invoices.length === 1 ? "" : "s"}` : "No invoices recorded in this session"} />
      <Metric label="Total Expenses" value="Unavailable" icon={ArrowDownRight} note="Expense records are not available" />
      <Metric label="Profit / Loss" value="Unavailable" icon={CircleHelp} note="Requires recorded sales and expenses" />
      <Metric label="Outstanding Payments" value="Unavailable" icon={ReceiptText} note="Payment collection status is not recorded" />
      <Metric label="Pending Quotations" value={String(pendingQuotationCount)} icon={FileClock} note="Draft, approval, approved, or sent" />
      <Metric label="Sales Orders" value={String(openOrderCount)} icon={ShoppingCart} note="Open frontend orders, including demo seeds" />
    </section>

    <section className="grid gap-4 xl:grid-cols-[1.2fr_1fr]">
      <Card className="border-0 bg-white p-5 shadow-sm sm:p-6">
        <div className="flex items-center gap-2"><Banknote size={17} className="text-[#35aa50]" /><h2 className="text-sm font-semibold text-[#173b2d]">Invoiced sales by currency</h2></div>
        <p className="mt-1 text-xs text-[#83968b]">Recorded invoices only; currencies are kept separate.</p>
        {currencyEntries.length ? <div className="mt-6 space-y-4">{currencyEntries.map(([currency, amount]) => <div key={currency}>
          <div className="mb-1.5 flex justify-between text-xs"><span className="font-medium text-[#557064]">{currency}</span><span className="font-semibold text-[#173b2d]">{money(amount, currency)}</span></div>
          <div className="h-2 overflow-hidden rounded-full bg-[#edf4ef]"><div className="h-full rounded-full bg-[#39b653]" style={{ width: `${Math.max(3, amount / maxTotal * 100)}%` }} /></div>
        </div>)}</div> : <div className="mt-6 rounded-xl bg-[#f7faf7] px-4 py-8 text-center"><p className="text-sm font-medium text-[#526c5e]">No invoice data yet</p><p className="mt-1 text-xs text-[#89988f]">Sales totals will appear here when invoices are recorded.</p></div>}
      </Card>

      <Card className="border-0 bg-white p-5 shadow-sm sm:p-6">
        <div className="flex items-center justify-between gap-3"><div><h2 className="text-sm font-semibold text-[#173b2d]">Recent activity</h2><p className="mt-1 text-xs text-[#83968b]">Latest orders, quotations, and invoices</p></div><ArrowUpRight size={17} className="text-[#35aa50]" /></div>
        <div className="mt-4 divide-y divide-[#edf2ee]">
          {activities.map((activity, index) => <Link key={`${activity.kind}-${activity.title}-${index}`} to={activity.href} className="flex items-start justify-between gap-3 py-3 first:pt-1 hover:bg-[#fbfdfb]">
            <div className="min-w-0"><p className="truncate text-xs font-semibold text-[#254a35]">{activity.title}</p><p className="mt-1 truncate text-[11px] text-[#7b8f83]">{activity.detail}</p></div>
            <time className="shrink-0 text-[10px] text-[#92a198]">{activity.date}</time>
          </Link>)}
          {!activities.length && <p className="py-8 text-center text-xs text-[#89988f]">No recent finance activity in this session.</p>}
        </div>
      </Card>
    </section>
  </div>;
}

function Metric({ label, value, icon: Icon, note }: { label: string; value: string; icon: typeof Banknote; note: string }) {
  return <Card className="border-0 bg-white p-4 shadow-sm">
    <div className="flex items-start justify-between gap-3"><div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#e9f6eb] text-[#36a752]"><Icon size={17} /></div><span className="rounded-full bg-[#f4f8f4] px-2 py-1 text-[9px] font-medium uppercase tracking-wide text-[#7e9385]">Session</span></div>
    <p className="mt-4 text-xs text-[#87988f]">{label}</p><p className="mt-1 text-xl font-semibold tracking-tight text-[#173b2d]">{value}</p><p className="mt-1 text-[10px] text-[#8a9a91]">{note}</p>
  </Card>;
}

export function FinanceQualityOverview(){const {user}=useAuth();return user?.backendSession?<QualityFoundation/>:<DemoFinanceQualityOverview/>;}
function DemoFinanceQualityOverview(){const q=useQuality();return <div className="space-y-4"><h1 className="text-2xl font-semibold text-navy">Finance · Quality summary</h1><p className="text-sm text-gray-500">Read-only session overview. Detailed QC records, inspection entry and quality release retain their existing role permissions.</p><Card><p>Recorded inspections: {q.inspections.length}</p><p>Awaiting review: {q.inspections.filter(i=>i.status==='Submitted').length}</p><p>Failed inspections: {q.inspections.filter(i=>i.status==='Failed').length}</p><p>Open corrective actions: {q.nonConformances.filter(n=>n.status!=='Closed').length}</p></Card><Link to="/" className="underline">Finance Dashboard</Link></div>;}
