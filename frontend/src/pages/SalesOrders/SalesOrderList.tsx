import { CommercialFoundation } from '@/pages/Commercial/CommercialFoundation';
import { useAuth } from '@/context/AuthContext';
import { SalesSummary } from '@/components/SalesSummary';
import { useInventory } from '@/context/InventoryContext';
import { useJobCards } from '@/context/JobCardsContext';
import { orderFulfillmentStatus } from '@/lib/fulfillment';
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ChevronLeft, ChevronRight, Download, FileText, Info, Plus, Search, X } from "lucide-react";
import { useSalesOrders } from '@/context/SalesOrdersContext';
import { NewSalesOrderModal } from './NewSalesOrderModal';
import { useLocation } from 'react-router-dom';

import { Card } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/StatusBadge";
import type { SalesOrder } from "@/types";

const PAGE_SIZE = 8;

type SortKey = "newest" | "oldest" | "customer" | "jobcards";

const SORT_LABELS: Record<SortKey, string> = {
  newest: "Newest first",
  oldest: "Oldest first",
  customer: "Customer (A–Z)",
  jobcards: "Most job cards",
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const toTime = (d: string) => {
  const t = Date.parse(d);
  return Number.isNaN(t) ? 0 : t;
};

const formatDate = (d: string) => {
  const t = Date.parse(d);
  return Number.isNaN(t)
    ? d
    : new Date(t).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
};

const isThisMonth = (d: string) => {
  const t = new Date(d);
  const now = new Date();
  return !Number.isNaN(t.getTime()) && t.getMonth() === now.getMonth() && t.getFullYear() === now.getFullYear();
};

function downloadCsv(rows: SalesOrder[]) {
  const escape = (v: string | number) => `"${String(v).replace(/"/g, '""')}"`;
  const header = ["Order number", "Customer Name", "Order Date", "Marketing Person Name", "Customer Type", "Requisition Order", "Item", "Quantity", "Unit", "Per Unit Price", "Total Price", "Order Total", "Status", "Job cards"];
  const lines = rows.flatMap((o) => (o.items?.length ? o.items : [undefined]).map((item) => [
    o.orderNumber, o.customerName, o.date, o.marketingPersonName ?? "", o.customerType ?? "", o.requisitionOrder ?? "",
    item?.itemName ?? "", item?.quantity ?? "", item?.unit ?? "", item?.unitPrice ?? "", item?.totalPrice ?? "",
    o.orderTotal ?? "", o.status, o.jobCardIds.length,
  ].map(escape).join(",")));
  const blob = new Blob([[header.map(escape).join(","), ...lines].join("\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `sales-orders-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

// ---------------------------------------------------------------------------
// Small pieces
// ---------------------------------------------------------------------------

function Stat({ label, value, hint, alert = false }: { label: string; value: number; hint: string; alert?: boolean }) {
  return (
    <Card>
      <p className="text-sm text-gray-500">{label}</p>
      <p className={`mt-1 text-3xl font-semibold tracking-tight ${alert && value > 0 ? "text-amber-600" : "text-navy"}`}>{value}</p>
      <p className="mt-1 text-xs text-gray-500">{hint}</p>
    </Card>
  );
}

// The Job Card is reachable straight from the Sales Order. With none allocated yet, offer to allocate one.
function JobCardLinks({ order }: { order: SalesOrder }) {
  if (order.jobCardIds.length === 0) {
    return (
      <Link
        to={`/sales-orders/${order.id}`}
        className="inline-flex items-center gap-1 rounded-md bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700 ring-1 ring-inset ring-amber-600/20 hover:bg-amber-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-navy"
      >
        <Plus size={12} /> View fulfillment
      </Link>
    );
  }
  return (
    <div className="flex flex-wrap gap-1.5">
      {order.jobCardIds.map((id, i) => (
        <Link
          key={id}
          to={`/job-cards/${id}`}
          className="inline-flex items-center gap-1 rounded-md bg-gray-100 px-2.5 py-1 text-xs font-medium text-navy hover:bg-gray-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-navy"
        >
          <FileText size={12} />
          Job card{order.jobCardIds.length > 1 ? ` ${i + 1}` : ""}
        </Link>
      ))}
    </div>
  );
}

function TableSkeleton() {
  return (
    <div className="divide-y divide-gray-100" aria-hidden="true">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="flex items-center gap-6 px-4 py-4">
          <div className="h-4 w-24 animate-pulse rounded bg-gray-100" />
          <div className="h-4 w-48 animate-pulse rounded bg-gray-100" />
          <div className="ml-auto h-6 w-20 animate-pulse rounded-full bg-gray-100" />
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export function SalesOrderList() {
  const { user } = useAuth();
  return user?.backendSession ? <CommercialFoundation initialKind="SALES_ORDER" title="Sales Order drafts" /> : <DemoSalesOrderList />;
}

function DemoSalesOrderList() {
  const { orders: sourceOrders } = useSalesOrders();
  const { ledger } = useInventory();
  const { cards, load } = useJobCards();
  useEffect(() => { void load(); }, [load]);
  const orders = useMemo(() => sourceOrders.map(order => ({ ...order, status: orderFulfillmentStatus(order, ledger, cards) })), [sourceOrders, ledger, cards]);
  const location = useLocation();
  const [showNewOrder, setShowNewOrder] = useState(location.pathname === '/sales-orders/new');
  const [success, setSuccess] = useState('');
  const loading = false;
  const usingDemoData = true;
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [sort, setSort] = useState<SortKey>("newest");
  const [page, setPage] = useState(1);

  useEffect(() => setPage(1), [query, statusFilter, sort]);

  // Status filters are built from the data, so new statuses appear without code changes.
  const statusCounts = useMemo(() => {
    const counts = new Map<string, number>();
    orders.forEach((o) => counts.set(o.status, (counts.get(o.status) ?? 0) + 1));
    return [...counts.entries()];
  }, [orders]);

  const stats = useMemo(
    () => ({
      total: orders.length,
      awaitingJobCard: orders.filter((o) => o.items?.some(i => i.fulfillmentSource === 'manufacturing') && o.jobCardIds.length === 0).length,
      withJobCards: orders.filter((o) => o.jobCardIds.length > 0).length,
      thisMonth: orders.filter((o) => isThisMonth(o.date)).length,
    }),
    [orders],
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const rows = orders.filter(
      (o) =>
        (statusFilter === "all" || o.status === statusFilter) &&
        (!q || o.orderNumber.toLowerCase().includes(q) || o.customerName.toLowerCase().includes(q) || o.marketingPersonName?.toLowerCase().includes(q)),
    );
    return rows.sort((a, b) => {
      switch (sort) {
        case "oldest":
          return toTime(a.date) - toTime(b.date);
        case "customer":
          return a.customerName.localeCompare(b.customerName);
        case "jobcards":
          return b.jobCardIds.length - a.jobCardIds.length;
        default:
          return toTime(b.date) - toTime(a.date);
      }
    });
  }, [orders, query, statusFilter, sort]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, pageCount);
  const start = (safePage - 1) * PAGE_SIZE;
  const visible = filtered.slice(start, start + PAGE_SIZE);
  const filtersActive = query !== "" || statusFilter !== "all";

  const clearFilters = () => {
    setQuery("");
    setStatusFilter("all");
  };

  return (
    <div className="space-y-6">
      {showNewOrder && <NewSalesOrderModal onClose={() => setShowNewOrder(false)} onCreated={(number) => { setShowNewOrder(false); setSuccess(`${number} created successfully.`); setQuery(''); setStatusFilter('all'); setSort('newest'); setPage(1); }} />}
      {success && <p role="status" className="rounded-card border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{success}</p>}
      {/* Header */}
      <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-navy">Sales Orders</h1>
          <p className="mt-1 text-sm text-gray-500">Track every order from creation to job card, approval and store issue.</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => downloadCsv(filtered)}
            disabled={filtered.length === 0}
            className="flex items-center gap-2 rounded-card border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-navy disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Download size={16} /> Export CSV
          </button>
          <button
            type="button" onClick={() => setShowNewOrder(true)}
            className="flex items-center gap-2 rounded-card bg-navy px-4 py-2 text-sm font-medium text-white hover:opacity-90 focus:outline-none focus-visible:ring-2 focus-visible:ring-navy focus-visible:ring-offset-2"
          >
            <Plus size={16} /> New order
          </button>
        </div>
      </header>

      {usingDemoData && (
        <div role="status" className="flex items-start gap-2 rounded-card border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-800">
          <Info size={16} className="mt-0.5 shrink-0" />
          Frontend demo orders. Changes are shared with Stock during this session and reset on browser refresh.
        </div>
      )}

      <SalesSummary/>
      {/* Summary */}
      <section aria-label="Order summary" className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="Total orders" value={stats.total} hint="All time" />
        <Stat label="Awaiting job card" value={stats.awaitingJobCard} hint="Need a job card allocated" alert />
        <Stat label="With job cards" value={stats.withJobCards} hint="Moving through production" />
        <Stat label="Created this month" value={stats.thisMonth} hint="New orders" />
      </section>

      {/* Toolbar */}
      <section aria-label="Filters" className="space-y-3">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <div className="relative flex-1">
            <label htmlFor="so-search" className="sr-only">
              Search orders
            </label>
            <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              id="so-search"
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by order number, customer or marketing person"
              className="w-full rounded-card border border-gray-200 bg-white py-2 pl-9 pr-3 text-sm text-gray-900 placeholder:text-gray-400 focus:border-navy focus:outline-none focus:ring-1 focus:ring-navy"
            />
          </div>
          <div className="flex items-center gap-2">
            <label htmlFor="so-sort" className="text-sm text-gray-500">
              Sort by
            </label>
            <select
              id="so-sort"
              value={sort}
              onChange={(e) => setSort(e.target.value as SortKey)}
              className="rounded-card border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 focus:border-navy focus:outline-none focus:ring-1 focus:ring-navy"
            >
              {(Object.keys(SORT_LABELS) as SortKey[]).map((k) => (
                <option key={k} value={k}>
                  {SORT_LABELS[k]}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {[["all", "All", orders.length] as const, ...statusCounts.map(([s, n]) => [s, s, n] as const)].map(([value, label, count]) => {
            const active = statusFilter === value;
            return (
              <button
                key={value}
                type="button"
                aria-pressed={active}
                onClick={() => setStatusFilter(value)}
                className={`rounded-full px-3 py-1 text-sm font-medium transition focus:outline-none focus-visible:ring-2 focus-visible:ring-navy ${
                  active ? "bg-navy text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
              >
                {label} <span className={active ? "text-white/70" : "text-gray-400"}>{count}</span>
              </button>
            );
          })}
          {filtersActive && (
            <button
              type="button"
              onClick={clearFilters}
              className="ml-1 inline-flex items-center gap-1 text-sm text-gray-500 hover:text-navy focus:outline-none focus-visible:ring-2 focus-visible:ring-navy"
            >
              <X size={14} /> Clear filters
            </button>
          )}
        </div>
      </section>

      {/* Table */}
      <section aria-label="Sales orders" className="overflow-hidden rounded-card border border-gray-200 bg-white">
        {loading ? (
          <TableSkeleton />
        ) : orders.length === 0 ? (
          <div className="px-6 py-12 text-center">
            <p className="font-medium text-navy">No sales orders yet</p>
            <p className="mt-1 text-sm text-gray-500">Create an order and allocate a job card to send it to the Production Manager.</p>
            <button type="button" onClick={() => setShowNewOrder(true)} className="mt-4 inline-flex items-center gap-2 rounded-card bg-navy px-4 py-2 text-sm font-medium text-white hover:opacity-90">
              <Plus size={16} /> New order
            </button>
          </div>
        ) : filtered.length === 0 ? (
          <div className="px-6 py-12 text-center">
            <p className="font-medium text-navy">No orders match your filters</p>
            <p className="mt-1 text-sm text-gray-500">Try a different search or status.</p>
            <button type="button" onClick={clearFilters} className="mt-4 rounded-card border border-gray-200 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
              Clear filters
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[1600px] text-left text-sm">
              <thead className="border-b border-gray-200 bg-gray-50 text-xs text-gray-500">
                <tr>
                  <th scope="col" className="px-4 py-3 font-medium">Order</th>
                  <th scope="col" className="px-4 py-3 font-medium">Customer Name</th>
                  <th scope="col" className="px-4 py-3 font-medium">Order Date</th>
                  {['Marketing Person Name', 'Customer Type', 'Requisition Order', 'Item', 'Quantity', 'Unit', 'Per Unit Price', 'Total Price', 'Order Total'].map(label => (
                    <th key={label} scope="col" className="whitespace-nowrap px-4 py-3 font-medium">{label}</th>
                  ))}
                  <th scope="col" className="px-4 py-3 font-medium">Job card</th>
                  <th scope="col" className="px-4 py-3 font-medium">Status</th>
                  <th scope="col" className="px-4 py-3"><span className="sr-only">Open</span></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {visible.map((order) => (
                  <tr key={order.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <Link to={`/sales-orders/${order.id}`} className="font-medium text-navy hover:underline focus:outline-none focus-visible:underline">
                        {order.orderNumber}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-gray-700">{order.customerName}</td>
                    <td className="whitespace-nowrap px-4 py-3 text-gray-500">{formatDate(order.date)}</td>
                    <td className="px-4 py-3 text-gray-700">{order.marketingPersonName || '—'}</td>
                    <td className="px-4 py-3 text-gray-700">{order.customerType || '—'}</td>
                    <td className="px-4 py-3 text-gray-700">{order.requisitionOrder || '—'}</td>
                    {(['itemName', 'quantity', 'unit', 'unitPrice', 'totalPrice'] as const).map(field => (
                      <td key={field} className="px-4 py-3 align-top text-gray-700">
                        {order.items?.length ? order.items.map(item => (
                          <div key={item.id} className="whitespace-nowrap py-1 tabular-nums">
                            {field === 'unitPrice' || field === 'totalPrice'
                              ? item[field].toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                              : item[field]}
                          </div>
                        )) : '—'}
                      </td>
                    ))}
                    <td className="whitespace-nowrap px-4 py-3 font-semibold tabular-nums text-navy">{order.orderTotal === undefined ? '—' : order.orderTotal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                    <td className="px-4 py-3">
                      <JobCardLinks order={order} />
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={order.status} />
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Link
                        to={`/sales-orders/${order.id}`}
                        aria-label={`Open ${order.orderNumber}`}
                        className="inline-flex rounded-md p-1 text-gray-400 hover:bg-gray-100 hover:text-navy focus:outline-none focus-visible:ring-2 focus-visible:ring-navy"
                      >
                        <ChevronRight size={18} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {!loading && filtered.length > 0 && (
          <div className="flex items-center justify-between border-t border-gray-200 px-4 py-3 text-sm text-gray-500">
            <p aria-live="polite">
              Showing {start + 1}–{Math.min(start + PAGE_SIZE, filtered.length)} of {filtered.length}
            </p>
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => setPage(safePage - 1)}
                disabled={safePage === 1}
                aria-label="Previous page"
                className="rounded-md p-1.5 hover:bg-gray-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-navy disabled:cursor-not-allowed disabled:opacity-40"
              >
                <ChevronLeft size={18} />
              </button>
              <span className="px-2 tabular-nums">
                {safePage} / {pageCount}
              </span>
              <button
                type="button"
                onClick={() => setPage(safePage + 1)}
                disabled={safePage === pageCount}
                aria-label="Next page"
                className="rounded-md p-1.5 hover:bg-gray-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-navy disabled:cursor-not-allowed disabled:opacity-40"
              >
                <ChevronRight size={18} />
              </button>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
