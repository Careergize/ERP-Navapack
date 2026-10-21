import { CommercialFoundation } from '@/pages/Commercial/CommercialFoundation';
import { useAuth } from '@/context/AuthContext';
import { StockIntelligence } from '@/components/StockIntelligence';
import { CustomCosting } from './CustomCosting';
import { useSearchParams } from 'react-router-dom';
import { FormEvent, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { MOCK_COSTING_RECORDS, MOCK_EXCHANGE_RATES } from "@/lib/mockData";
import { Card } from "@/components/ui/Card";
import type { CostingRecord, ExchangeRate } from "@/types";

type View = "costing" | "rates" | "custom";
type Currency = "USD" | "NGN" | "GHS" | "ZAR";

const formatNumber = (value: number) => value.toLocaleString("en-IN");
const formatDate = (date: string) =>
  new Date(`${date}T00:00:00`).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });

export function CostingPage() {
  const { user } = useAuth();
  return user?.backendSession ? <CommercialFoundation initialKind="COSTING" title="Costing" /> : <DemoCostingPage />;
}

function DemoCostingPage() {
  const [params] = useSearchParams();
  const [view, setView] = useState<View>(params.has("orderId") ? "custom" : "costing");
  useEffect(() => { if (params.has("orderId")) setView("custom"); }, [params]);
  const [records, setRecords] = useState<CostingRecord[]>([]);
  const [rates, setRates] = useState<ExchangeRate[]>([]);
  const [loadingRecords, setLoadingRecords] = useState(true);
  const [loadingRates, setLoadingRates] = useState(true);
  const [currency, setCurrency] = useState<Currency>("USD");
  const [rate, setRate] = useState("");
  const [date, setDate] = useState("2026-09-24");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    api
      .get<CostingRecord[]>("/costing/")
      .then(({ data }) => {
        if (!Array.isArray(data)) throw new Error("Costing API returned an invalid response");
        setRecords(data);
      })
      .catch(() => setRecords(MOCK_COSTING_RECORDS))
      .finally(() => setLoadingRecords(false));

    api
      .get<ExchangeRate[]>("/costing/exchange-rates/")
      .then(({ data }) => {
        if (!Array.isArray(data)) throw new Error("Exchange rates API returned an invalid response");
        setRates(data);
      })
      .catch(() => setRates(MOCK_EXCHANGE_RATES))
      .finally(() => setLoadingRates(false));
  }, []);

  async function handleLogRate(event: FormEvent) {
    event.preventDefault();
    const parsedRate = Number(rate);
    if (!parsedRate || parsedRate <= 0 || !date) return;

    const newRate: ExchangeRate = {
      id: `fx-${Date.now()}`,
      currency,
      rate: parsedRate,
      date,
      enteredBy: "Current user (Accounts)",
    };

    setSubmitting(true);
    try {
      await api.post("/costing/exchange-rates/", newRate);
    } catch {
      // Demo mode has no backend; the local rate history remains authoritative.
    } finally {
      setRates((current) => [newRate, ...current]);
      setRate("");
      setSubmitting(false);
    }
  }

  const latestRate = rates[0];

  return (
    <div>
      <h1 className="text-2xl font-semibold text-navy">Costing</h1>
      <p className="mt-1 text-sm text-gray-500">Review item costs and maintain the manual exchange rates used by Accounts.</p>

      <section aria-label="Costing summary" className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2">
        <Card className="p-4">
          <p className="text-sm text-gray-500">Items costed this month</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums text-navy">{records.length}</p>
        </Card>
        <Card className="p-4">
          <p className="text-sm text-gray-500">Latest exchange rate</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums text-navy">
            {latestRate ? `1 ${latestRate.currency} = ₦${formatNumber(latestRate.rate)}` : "—"}
          </p>
        </Card>
      </section>

      <div className="mt-6 inline-flex rounded-full bg-gray-100 p-1" role="tablist" aria-label="Costing views">
        {(["costing", "custom", "rates"] as const).map((tab) => {
          const active = view === tab;
          return (
            <button
              key={tab}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => setView(tab)}
              className={`rounded-full px-4 py-2 text-sm font-medium transition-colors ${active ? "bg-white text-navy shadow-sm" : "text-gray-500 hover:text-navy"}`}
            >
              {tab === "costing" ? "Item/Model Costing" : tab === "custom" ? "Custom Costing & Estimates" : "Exchange Rates"}
            </button>
          );
        })}
      </div>

      <details className="mt-4"><summary>Stock cost / VAT / LED / KG / CTR analysis</summary><StockIntelligence/></details>
      {view === "custom" && <div className="mt-4"><CustomCosting /></div>}
      {view === "costing" && (
        <div className="mt-4">
          {loadingRecords && <p className="text-sm text-gray-500">Loading costing records…</p>}
          {!loadingRecords && (
            <Card className="overflow-hidden p-0">
              <div className="overflow-x-auto">
                <table className="w-full min-w-[980px] text-left text-sm">
                  <thead className="bg-navy text-xs text-white">
                    <tr>
                      <th className="px-4 py-3 font-medium">Item/Model</th>
                      <th className="px-4 py-3 text-right font-medium">Raw Material Cost</th>
                      <th className="px-4 py-3 text-right font-medium">Production Cost</th>
                      <th className="px-4 py-3 text-right font-medium">Other Cost</th>
                      <th className="px-4 py-3 font-medium">Currency</th>
                      <th className="px-4 py-3 text-right font-medium">Exchange Rate Used</th>
                      <th className="px-4 py-3 text-right font-medium">Total (local currency)</th>
                      <th className="px-4 py-3 font-medium">Last Updated</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {records.map((record) => (
                      <tr key={record.id} className="text-gray-600">
                        <td className="whitespace-nowrap px-4 py-3 font-medium text-navy">{record.itemOrModel}</td>
                        <td className="px-4 py-3 text-right tabular-nums">{formatNumber(record.rawMaterialCost)}</td>
                        <td className="px-4 py-3 text-right tabular-nums">{formatNumber(record.productionCost)}</td>
                        <td className="px-4 py-3 text-right tabular-nums">{formatNumber(record.otherCost)}</td>
                        <td className="px-4 py-3">{record.currency}</td>
                        <td className="px-4 py-3 text-right tabular-nums">{formatNumber(record.exchangeRateUsed)}</td>
                        <td className="px-4 py-3 text-right font-semibold tabular-nums text-navy">₦{formatNumber(record.totalCostLocal)}</td>
                        <td className="whitespace-nowrap px-4 py-3">{formatDate(record.lastUpdated)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </div>
      )}

      {view === "rates" && (
        <div className="mt-4 space-y-4">
          <Card>
            <form onSubmit={handleLogRate}>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-[1fr_1fr_1fr_auto] md:items-end">
                <label className="text-sm text-gray-600">
                  Currency
                  <select value={currency} onChange={(event) => setCurrency(event.target.value as Currency)} className="mt-1 block w-full rounded-card border border-gray-200 bg-white px-3 py-2 text-sm text-ink focus:border-blue focus:outline-none">
                    {(["USD", "NGN", "GHS", "ZAR"] as const).map((option) => <option key={option} value={option}>{option}</option>)}
                  </select>
                </label>
                <label className="text-sm text-gray-600">
                  Rate
                  <input type="number" min="0" step="0.01" required value={rate} onChange={(event) => setRate(event.target.value)} placeholder="e.g. 1552" className="mt-1 block w-full rounded-card border border-gray-200 px-3 py-2 text-sm text-ink focus:border-blue focus:outline-none" />
                </label>
                <label className="text-sm text-gray-600">
                  Date
                  <input type="date" required value={date} onChange={(event) => setDate(event.target.value)} className="mt-1 block w-full rounded-card border border-gray-200 px-3 py-2 text-sm text-ink focus:border-blue focus:outline-none" />
                </label>
                <button type="submit" disabled={submitting} className="rounded-card bg-navy px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-60">
                  {submitting ? "Logging…" : "Log rate"}
                </button>
              </div>
            </form>
          </Card>

          <Card className="overflow-hidden p-0">
            {loadingRates ? <p className="p-5 text-sm text-gray-500">Loading exchange rates…</p> : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[620px] text-left text-sm">
                  <thead className="bg-navy text-xs text-white">
                    <tr>
                      <th className="px-4 py-3 font-medium">Currency</th>
                      <th className="px-4 py-3 text-right font-medium">Rate</th>
                      <th className="px-4 py-3 font-medium">Date</th>
                      <th className="px-4 py-3 font-medium">Entered by</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {rates.map((entry) => (
                      <tr key={entry.id} className="text-gray-600">
                        <td className="px-4 py-3 font-medium text-navy">{entry.currency}</td>
                        <td className="px-4 py-3 text-right tabular-nums">{formatNumber(entry.rate)}</td>
                        <td className="px-4 py-3">{formatDate(entry.date)}</td>
                        <td className="px-4 py-3">{entry.enteredBy}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>
      )}
    </div>
  );
}
