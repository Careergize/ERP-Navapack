import type { CommercialRecord } from '@/lib/commercialApi';
export function CommercialSnapshot({ snapshot }: { snapshot: CommercialRecord['snapshot'] }) {
  const d = snapshot.input;
  const lines = d.lines as { quantity: string; unit_price: string; specifications: string; customisation: string; variant_snapshot: { name: string }; unit_snapshot: { code: string } }[];
  const totals = snapshot.estimate as CommercialRecord['snapshot']['estimate'] & { lines: { net_amount: string; costing?: Record<string, string | null> }[] };
  return <div className="space-y-3"><p>{(d.party_snapshot as { name: string } | null)?.name ?? 'Product costing without customer'} · {String(d.currency)} · {String(d.money_places)} decimals · {String(d.rounding)}</p>
    {lines.map((l, i) => <article key={i} className="border rounded p-3 space-y-2"><h4>{l.variant_snapshot.name}</h4><p>{l.quantity} {l.unit_snapshot.code} × {l.unit_price} = {totals.lines[i].net_amount} {String(d.currency)}</p><p className="whitespace-pre-wrap">{l.specifications}</p><p>{l.customisation}</p>
      {totals.lines[i].costing && <dl className="grid sm:grid-cols-2 gap-2">{['material_cost', 'process_cost', 'estimated_production_cost', 'cost_per_output_unit', 'cost_per_kg', 'cost_per_ctr', 'suggested_unit_price', 'gross_margin_percent', 'entered_gross_margin_percent_before_discount'].map(k => <div key={k}><dt>{k.replaceAll('_', ' ')}</dt><dd>{totals.lines[i].costing?.[k] ?? 'Unavailable'}</dd></div>)}</dl>}</article>)}
    <p>Net estimate: {snapshot.estimate.net_estimate} {String(d.currency)}. Discount: {String(d.discount)}.</p><p>VAT, LED, final payable and actual cost: unavailable.</p><p className="whitespace-pre-wrap">Terms: {String(d.terms) || 'Unspecified'}</p>
  </div>;
}
