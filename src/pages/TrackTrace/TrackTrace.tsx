import { FormEvent, useState } from "react";
import { Search } from "lucide-react";
import { api } from "@/lib/api";
import { MOCK_TRACE_RESULTS } from "@/lib/mockData";
import { Card } from "@/components/ui/Card";
import { StatusBadge } from "@/components/ui/StatusBadge";
import type { TraceResult } from "@/types";

export function LegacyTrace() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<TraceResult | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function searchTrace(value: string) {
    const normalizedQuery = value.trim().toUpperCase();
    if (!normalizedQuery) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const { data } = await api.get<TraceResult>(`/trace/${encodeURIComponent(normalizedQuery)}/`);
      setResult(data);
    } catch {
      const mockResult = MOCK_TRACE_RESULTS[normalizedQuery];
      if (mockResult) {
        setResult(mockResult);
      } else {
        setError(`No record found for “${normalizedQuery}”.`);
      }
    } finally {
      setLoading(false);
    }
  }

  function handleSearch(e: FormEvent) {
    e.preventDefault();
    void searchTrace(query);
  }

  function handleExampleClick(exampleId: string) {
    setQuery(exampleId);
    void searchTrace(exampleId);
  }

  return (
    <div className="max-w-xl">
      <h1 className="text-2xl font-semibold text-navy">Track & Trace</h1>
      <p className="mt-1 text-sm text-gray-500">
        Enter any Sales Order, Job Card, or batch number to see where it is and where it's been.
      </p>

      <form onSubmit={handleSearch} className="mt-6 flex gap-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g. JC-1042"
          className="flex-1 rounded-card border border-gray-200 px-4 py-2 text-sm focus:border-blue focus:outline-none"
        />
        <button
          type="submit"
          disabled={loading}
          className="flex items-center gap-2 rounded-card bg-navy px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-60"
        >
          <Search size={16} /> {loading ? "Searching…" : "Search"}
        </button>
      </form>

      <div className="mt-3 flex flex-wrap items-center gap-2" aria-label="Example trace IDs">
        <span className="text-xs text-gray-500">Try an example:</span>
        {["SO-1042", "JC-2201", "RM-8834", "GB-0501"].map((exampleId) => (
          <button
            key={exampleId}
            type="button"
            onClick={() => handleExampleClick(exampleId)}
            className="rounded-full border border-gray-200 bg-white px-2.5 py-1 text-xs font-medium text-gray-600 hover:border-navy hover:text-navy"
          >
            {exampleId}
          </button>
        ))}
      </div>

      {error && <p className="mt-4 text-sm text-red-600">{error}</p>}

      {result && (
        <Card className="mt-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-navy">{result.traceId}</p>
              <p className="text-sm text-gray-500">{result.type.replace(/([A-Z])/g, " $1").trim()}</p>
            </div>
            <StatusBadge status={result.currentStatus} />
          </div>

          {result.currentStage && (
            <p className="mt-3 text-sm text-gray-500">
              Currently at: <span className="font-medium text-teal">{result.currentStage}</span>
            </p>
          )}

          <div className="mt-5 space-y-3 border-t border-gray-100 pt-4">
            {result.history.map((h, i) => (
              <div key={i} className="flex items-center justify-between text-sm">
                <span className="text-ink">{h.label}</span>
                <span className="text-gray-400">{h.timestamp}</span>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
