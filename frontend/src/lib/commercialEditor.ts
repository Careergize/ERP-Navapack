export interface MaterialComponent { material: string; unit: string; price_unit: string; currency: string; quantity: string; price: string }
export interface ProcessComponent { description: string; currency: string; amount: string }
export interface CostingInput { materials: MaterialComponent[]; processes: ProcessComponent[]; waste_percent: string; rejection_percent: string; assumption_evidence: string; markup_percent: string }
export interface CommercialLine { variant: string; unit: string; quantity: string; unit_price: string; specifications: string; customisation: string; model_revision?: string; costing_revision?: string; stock_identity?: string; requested_delivery?: string; costing?: CostingInput }
export interface CommercialInput extends Record<string, unknown> { currency: string; money_places: number; rounding: string; customer?: string; prospect?: string; classification?: string; marketing_person?: string; quotation_revision?: string; requested_delivery?: string; validity_date?: string; terms: string; discount: string; lines: CommercialLine[] }
export const newMaterial = (currency = ''): MaterialComponent => ({ material: '', unit: '', price_unit: '', currency, quantity: '', price: '' });
export const newProcess = (currency = ''): ProcessComponent => ({ description: '', currency, amount: '' });
export const newCosting = (currency = ''): CostingInput => ({ materials: [newMaterial(currency)], processes: [], waste_percent: '0', rejection_percent: '0', assumption_evidence: '', markup_percent: '0' });
export const newLine = (costing = false, currency = ''): CommercialLine => ({ variant: '', unit: '', quantity: '', unit_price: '', specifications: '', customisation: '', ...(costing ? { costing: newCosting(currency) } : {}) });
export const newCommercialInput = (costing = false): CommercialInput => ({ currency: '', money_places: 2, rounding: 'HALF_UP', discount: '0', terms: '', lines: [newLine(costing)] });

// Only remove known server enrichment. Unknown future fields fail closed rather
// than disappearing during a replacement PATCH. Preserve every declared v1 field.
function project(raw: unknown, fields: string[], enrichment: string[], path: string): Record<string, unknown> {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) throw new Error(`Invalid ${path}.`);
  const source = raw as Record<string, unknown>;
  const unknown = Object.keys(source).filter(k => !fields.includes(k) && !enrichment.includes(k));
  if (unknown.length) throw new Error(`Editing unavailable: ${path} contains unsupported fields (${unknown.join(', ')}). Saved data remains intact.`);
  return Object.fromEntries(fields.filter(k => source[k] !== undefined).map(k => [k, structuredClone(source[k])]));
}
export function editableCommercialInput(raw: Record<string, unknown>): CommercialInput {
  const data = project(raw, ['currency', 'money_places', 'rounding', 'customer', 'prospect', 'classification', 'marketing_person', 'quotation_revision', 'requested_delivery', 'validity_date', 'terms', 'discount', 'lines'], ['party_snapshot', 'marketing_snapshot'], 'document');
  data.lines = (data.lines as unknown[]).map((rawLine, i) => {
    const line = project(rawLine, ['variant', 'unit', 'quantity', 'unit_price', 'specifications', 'customisation', 'model_revision', 'costing_revision', 'stock_identity', 'requested_delivery', 'costing'], ['variant_snapshot', 'unit_snapshot', 'model_snapshot', 'costing_snapshot', 'stock_reference_snapshot'], `product ${i+1}`);
    if (line.costing) {
      const cost = project(line.costing, ['materials', 'processes', 'waste_percent', 'rejection_percent', 'assumption_evidence', 'markup_percent'], [], 'costing');
      cost.materials = (cost.materials as unknown[]).map(m => project(m, ['material', 'unit', 'price_unit', 'currency', 'quantity', 'price'], ['master_snapshot'], 'material'));
      cost.processes = (cost.processes as unknown[]).map(p => project(p, ['description', 'currency', 'amount'], [], 'process'));
      line.costing = cost;
    }
    return line;
  });
  return data as unknown as CommercialInput;
}
export function compareCommercial(before: unknown, after: unknown, path = ''): { field: string; before: string; after: string }[] {
  if (JSON.stringify(before) === JSON.stringify(after)) return [];
  if (before && after && typeof before === 'object' && typeof after === 'object') {
    const a = before as Record<string, unknown>, b = after as Record<string, unknown>;
    return [...new Set([...Object.keys(a), ...Object.keys(b)])].sort().flatMap(k => compareCommercial(a[k], b[k], path ? `${path} / ${k}` : k));
  }
  return [{ field: path.replaceAll('_', ' '), before: before === undefined ? 'Unspecified' : String(before), after: after === undefined ? 'Unspecified' : String(after) }];
}
