export function RehearsalSummary({data}: {data: Record<string, unknown>}) {
  const commercial = data.commercial as {counts?: Record<string, number>; statuses?: Record<string, number>} | undefined;
  const production = (data.production_by_unit ?? []) as {unit: string; code: string; output_quantity: string; waste: string; rejection: string}[];
  const counts = (value: Record<string, number> | undefined) => Object.entries(value ?? {}).map(([name, count]) => <div className="rounded bg-slate-50 p-3" key={name}><p className="text-2xl font-semibold">{count}</p><p>{name.replaceAll('_',' ')}</p></div>);
  return <div className="space-y-4"><div className="grid grid-cols-2 md:grid-cols-4 gap-3"><div className="rounded bg-slate-50 p-3"><p className="text-2xl font-semibold">{String(data.jobs ?? 0)}</p><p>Synthetic Job Cards</p></div>{counts(data.statuses as Record<string, number> | undefined)}</div>
    {commercial && <section><h3 className="font-semibold">Owned persisted commercial drafts — unapproved estimates</h3><div className="grid grid-cols-2 md:grid-cols-3 gap-3">{counts(commercial.counts)}</div></section>}
    {!!data.stages && <section><h3 className="font-semibold">Synthetic manufacturing stages</h3><div className="grid grid-cols-3 gap-3">{counts(data.stages as Record<string, number>)}</div></section>}
    {!!production.length && <section><h3 className="font-semibold">Synthetic production by exact unit</h3><p>Units are kept separate. These totals are simulation output and do not change operational stock.</p><div className="grid md:grid-cols-2 gap-3">{production.map(row => <div key={row.unit} className="border rounded p-3"><strong>{row.code}</strong><p>Output: {row.output_quantity}</p><p>Waste: {row.waste} · Rejection: {row.rejection}</p></div>)}</div></section>}
  </div>;
}
