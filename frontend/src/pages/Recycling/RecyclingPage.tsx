import { PersistedRecycling } from '@/pages/Recycling/PersistedRecycling';
import { useAuth } from '@/context/AuthContext';
import { useQuality } from '@/context/QualityContext';
import { subjectHeld } from '@/lib/quality';
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { MOCK_GRANULES_BATCHES, MOCK_WASTE_ENTRIES } from "@/lib/mockData";
import { Card } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/StatusBadge";
import type { GranulesBatch, WasteEntry } from "@/types";

type View = "waste" | "granules";

const formatDate = (date: string) =>
  new Date(`${date}T00:00:00`).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });

export function RecyclingPage() {
 const { user } = useAuth();
 return user?.backendSession ? <PersistedRecycling/> : <DemoRecyclingPage/>;
}
function DemoRecyclingPage() {
  const quality = useQuality();
  const [view, setView] = useState<View>("waste");
  const [wasteEntries, setWasteEntries] = useState<WasteEntry[]>([]);
  const [granulesBatches, setGranulesBatches] = useState<GranulesBatch[]>([]);
  const [loadingWaste, setLoadingWaste] = useState(true);
  const [loadingGranules, setLoadingGranules] = useState(true);

  useEffect(() => {
    api
      .get<WasteEntry[]>("/recycling/waste/")
      .then(({ data }) => {
        if (!Array.isArray(data)) throw new Error("Waste API returned an invalid response");
        setWasteEntries(data);
      })
      .catch(() => setWasteEntries(MOCK_WASTE_ENTRIES))
      .finally(() => setLoadingWaste(false));

    api
      .get<GranulesBatch[]>("/recycling/granules/")
      .then(({ data }) => {
        if (!Array.isArray(data)) throw new Error("Granules API returned an invalid response");
        setGranulesBatches(data);
      })
      .catch(() => setGranulesBatches(MOCK_GRANULES_BATCHES))
      .finally(() => setLoadingGranules(false));
  }, []);

  const awaitingQty = wasteEntries.filter((entry) => !entry.sentToRecycling).reduce((total, entry) => total + entry.wasteQty, 0);
  const producedQty = granulesBatches.reduce((total, batch) => total + batch.granulesProducedKg, 0);

  return (
    <div>
      <h1 className="text-2xl font-semibold text-navy">Recycling</h1><Card className="mt-3"><h2 className="font-semibold">Recycling extruder QC warnings</h2>{quality.inspections.filter(i => i.subject.machineType === "recycle_extruder" && subjectHeld(quality, i.subject)).map(i => <p key={i.id} className="text-sm text-amber-700">{i.subject.label} · {i.number} · {i.status} · Verification / corrective action required</p>)}<p className="text-xs text-gray-500">Machine checks are separate from recycling stock transactions. QC staff review the machine-specific records in Quality Control.</p></Card>
      <p className="mt-1 text-sm text-gray-500">Track production waste through recycling and back into raw material stock.</p>

      <section aria-label="Recycling summary" className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2">
        <Card className="p-4">
          <p className="text-sm text-gray-500">Waste awaiting recycling this month</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums text-navy">{awaitingQty} kg</p>
        </Card>
        <Card className="p-4">
          <p className="text-sm text-gray-500">Granules produced this month</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums text-navy">{producedQty} kg</p>
        </Card>
      </section>

      <div className="mt-6 inline-flex rounded-full bg-gray-100 p-1" role="tablist" aria-label="Recycling views">
        {(["waste", "granules"] as const).map((tab) => {
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
              {tab === "waste" ? "Waste Intake" : "Granules"}
            </button>
          );
        })}
      </div>

      <div className="mt-4 space-y-3">
        {view === "waste" && (
          <>
            {loadingWaste && <p className="text-sm text-gray-500">Loading waste intake…</p>}
            {wasteEntries.map((entry) => (
              <Card key={entry.id} className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                    <p className="font-medium text-navy">{entry.jobCardNumber}</p>
                    <span className="text-sm text-gray-500">{entry.stage}</span>
                  </div>
                  <p className="mt-1 text-sm text-gray-500">{entry.wasteType} · {formatDate(entry.date)}</p>
                </div>
                <div className="flex items-center justify-between gap-4 sm:justify-end">
                  <p className="font-medium tabular-nums text-ink">{entry.wasteQty} {entry.unit}</p>
                  <StatusBadge status={entry.sentToRecycling ? "Sent to Recycling" : "Awaiting Pickup"} />
                </div>
              </Card>
            ))}
          </>
        )}

        {view === "granules" && (
          <>
            {loadingGranules && <p className="text-sm text-gray-500">Loading granules batches…</p>}
            {granulesBatches.map((batch) => (
              <Card key={batch.id}>
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <p className="font-medium text-navy">{batch.batchNumber}</p>
                    <p className="mt-1 text-sm text-gray-500">{formatDate(batch.date)}</p>
                  </div>
                  <p className="text-sm tabular-nums text-gray-600">
                    {batch.inputWasteQty} kg waste <span className="mx-1 text-gray-300">→</span> <span className="font-semibold text-navy">{batch.granulesProducedKg} kg granules</span>
                  </p>
                </div>
                <div className="mt-4 border-t border-gray-100 pt-3 text-sm text-gray-600">
                  {batch.reEnteredQty ? <p><span className="font-medium text-teal">{batch.reEnteredQty} kg</span> → back into Raw Material Stock</p> : null}
                  {batch.soldQty ? <p className={batch.reEnteredQty ? "mt-1" : ""}><span className="font-medium text-blue">{batch.soldQty} kg</span> sold to {batch.soldTo ?? "external customer"}</p> : null}
                </div>
              </Card>
            ))}
          </>
        )}
      </div>
    </div>
  );
}
