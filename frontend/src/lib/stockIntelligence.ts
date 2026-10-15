import { calculateLED, LED_PERCENT, LED_USD_PER_TONNE } from './led';
import { roundMoney } from './customCosting';
import type { FinishedGoodsMovement } from './finishedGoodsData';

export interface ProductConversion { id: string; productId: string; modelId?: string; unit: string; piecesPerCTR?: number; kgPerCTR: number; version: number; effectiveDate: string }
export interface QuantitySnapshot { originalQuantity: number; originalUnit: string; convertedKG: number | null; conversionId?: string; conversionVersion?: number; productId: string; modelId?: string }
export const isKG = (u: string) => ['kg', 'kgs', 'kilo', 'kilos', 'kilogram', 'kilograms'].includes(u.toLowerCase());
export const isCTR = (u: string) => ['ctr', 'ctrs', 'ctn', 'ctns', 'carton', 'cartons'].includes(u.toLowerCase());
export function validateConversion(c: ProductConversion) {
  if (!c.productId || !isCTR(c.unit) || !(c.kgPerCTR > 0) || !Number.isFinite(c.kgPerCTR) || !Number.isInteger(c.version) || c.version < 1 || !validDate(c.effectiveDate) || (c.piecesPerCTR !== undefined && (!Number.isInteger(c.piecesPerCTR) || c.piecesPerCTR <= 0))) throw new Error('Use an exact CTR product, positive KG/CTR, version and effective date.');
}
export function quantitySnapshot(productId: string, quantity: number, unit: string, date: string, rules: ProductConversion[], modelId?: string): QuantitySnapshot {
  if (!Number.isFinite(quantity) || quantity < 0) throw new Error('Quantity must be finite and nonnegative.');
  const c = rules.filter(r => r.productId === productId && r.unit === unit && r.modelId === modelId && r.effectiveDate <= date).sort((a,b) => b.effectiveDate.localeCompare(a.effectiveDate) || b.version-a.version)[0];
  if (c) validateConversion(c);
  const convertedKG = isKG(unit) ? quantity : isCTR(unit) && c ? quantity * c.kgPerCTR : null;
  if (convertedKG !== null && !Number.isFinite(convertedKG)) throw new Error('Converted quantity exceeds supported range.');
  return { productId, modelId, originalQuantity: quantity, originalUnit: unit, convertedKG, ...(c ? { conversionId: c.id, conversionVersion: c.version } : {}) };
}
export function convertedPrices(price: number, unit: string, kgPerCTR?: number) {
  if (!Number.isFinite(price) || price < 0 || (kgPerCTR !== undefined && (!Number.isFinite(kgPerCTR) || kgPerCTR <= 0))) throw new Error('Use a valid price and positive product conversion.');
  return { perKG: isKG(unit) ? price : isCTR(unit) && kgPerCTR ? price / kgPerCTR : null, perCTR: isCTR(unit) ? price : isKG(unit) && kgPerCTR ? price * kgPerCTR : null };
}
export function snapshotMovements(previous:FinishedGoodsMovement[],next:FinishedGoodsMovement[],rules:ProductConversion[]):FinishedGoodsMovement[]{
  const existing=new Set(previous.map(m=>m.id));
  return next.map(m=>{
    if(existing.has(m.id))return m;
    const original=m.reversalOf?previous.find(row=>row.id===m.reversalOf):undefined;
    const snapshot=original?original.quantitySnapshot?structuredClone(original.quantitySnapshot):{productId:m.productId,modelId:original.modelId,originalQuantity:m.quantity,originalUnit:m.unit,convertedKG:null}:quantitySnapshot(m.productId,m.quantity,m.unit,m.date,rules,m.modelId);
    return {...m,quantitySnapshot:snapshot};
  });
}
export const validDate = (d: string) => /^\d{4}-\d{2}-\d{2}$/.test(d) && Number.isFinite(Date.parse(d)) && new Date(d+'T00:00:00Z').toISOString().slice(0,10) === d;
export interface StockThreshold { productId: string; unit: string; minimum: number; critical: number; reorder: number; target: number; leadDays?: number; windowDays: number; highConsumption?: number; rapidDaily?: number; replenishmentDue?: string; replenishmentQuantity?: number }
export function validateThreshold(t: StockThreshold) {
  if (![t.minimum,t.critical,t.reorder,t.target].every(n => Number.isFinite(n) && n >= 0) || t.critical > t.minimum || t.minimum > t.reorder || t.reorder > t.target || !Number.isInteger(t.windowDays) || t.windowDays < 2 || (t.leadDays !== undefined && (!Number.isFinite(t.leadDays) || t.leadDays < 0)) || [t.highConsumption,t.rapidDaily,t.replenishmentQuantity].some(n => n !== undefined && (!Number.isFinite(n) || n < 0)) || (t.replenishmentDue && !validDate(t.replenishmentDue))) throw new Error('Require 0 ≤ critical ≤ minimum ≤ reorder ≤ target, valid consumption window and optional quantities/dates.');
}
export function stockAlert(productId: string, unit: string, current: number | null, movements: FinishedGoodsMovement[], date: string, t?: StockThreshold) {
  if (t) { validateThreshold(t); if (t.productId !== productId || t.unit !== unit) throw new Error('Threshold unit/product mismatch.'); }
  const windowDays = t?.windowDays ?? 7, end = Date.parse(date+'T00:00:00Z'), start = new Date(end - (windowDays-1)*86400000).toISOString().slice(0,10);
  const outs = movements.filter(m => m.productId === productId && m.unit === unit && m.type === 'OUT' && m.date <= date && m.date >= start && !!m.dispatchId && !movements.some(r => r.reversalOf === m.id && r.date <= date));
  const consumption = outs.reduce((s,m) => s+m.quantity,0), days = new Set(outs.map(m => m.date)).size;
  const history = days >= 2; // Observed dispatch activity only; never a sales forecast.
  const labels: string[] = [];
  if (current !== null && current <= 0) labels.push('Out of Stock');
  else if (current !== null && t && current <= t.critical) labels.push('Critical Stock');
  else if (current !== null && t && current <= t.minimum) labels.push('Low Stock');
  if (movements.some(m=>m.productId===productId&&m.unit===unit&&m.type==='OUT'&&m.date>=start&&m.date<=date)) labels.push('Recent Stock OUT');
  if (t?.highConsumption !== undefined && consumption >= t.highConsumption && outs.length) labels.push('High Stock Consumption');
  if (history && t?.rapidDaily !== undefined && consumption/windowDays >= t.rapidDaily) labels.push('Stock Depleting Rapidly');
  if (t?.replenishmentQuantity && t.replenishmentDue) labels.push('Pending Replenishment');
  return { labels, severity: labels.includes('Out of Stock') || labels.includes('Critical Stock') ? 'Critical' : labels.includes('Low Stock') || labels.includes('Stock Depleting Rapidly') ? 'Warning' : 'Info', consumption, lastOUT: movements.filter(m => m.productId === productId && m.unit === unit && m.type === 'OUT' && m.date <= date).map(m=>m.date).sort().at(-1), history: history ? 'Observed consumption' : 'Insufficient History', dailyConsumption: history ? consumption/windowDays : null, recommended: current !== null && t && current <= t.reorder ? Math.max(0,t.target-current-(t.replenishmentQuantity ?? 0)) : null };
}

export type LEDMode = 'percentage' | 'weight' | 'higher' | 'lower';
export interface PricePolicy { vatRate: number; vatMode: 'inclusive' | 'exclusive'; ledApplies: boolean; ledMode: LEDMode; selectionConfirmed: boolean; ledRate: number; usdPer1000KG: number; usdToUGX?: number; fxDate?: string; percentageBase: 'net-selling' | 'production-cost'; vatOnLED: boolean; profitMethod: 'markup' | 'gross-margin'; profitPercent: number }
export const EXAMPLE_PRICE_POLICY: PricePolicy = { vatRate:18,vatMode:'inclusive',ledApplies:false,ledMode:'higher',selectionConfirmed:false,ledRate:LED_PERCENT,usdPer1000KG:LED_USD_PER_TONNE,percentageBase:'net-selling',vatOnLED:false,profitMethod:'markup',profitPercent:0 };
export function sellingCostBreakdown(amount: number, kg: number | null, p: PricePolicy) {
  if (!Number.isFinite(amount) || amount < 0 || ![p.vatRate,p.ledRate,p.usdPer1000KG,p.profitPercent].every(n=>Number.isFinite(n)&&n>=0) || p.vatRate>100 || p.ledRate>100 || (p.profitMethod==='gross-margin'&&p.profitPercent>=100) || (kg!==null&&(!Number.isFinite(kg)||kg<0)) || !['inclusive','exclusive'].includes(p.vatMode) || !['markup','gross-margin'].includes(p.profitMethod) || !['net-selling','production-cost'].includes(p.percentageBase) || !['percentage','weight','higher','lower'].includes(p.ledMode)) throw new Error('Invalid financial calculation configuration.');
  if(p.ledApplies && p.ledMode==='higher' && (p.ledRate!==LED_PERCENT || p.usdPer1000KG!==LED_USD_PER_TONNE))throw new Error('Confirmed MAX rates are 2.5% and USD 70 per metric tonne.');
  if (p.ledApplies && !p.selectionConfirmed) throw new Error('Confirm LED applicability and select the configurable percentage base before calculation. Higher of the Two is client-confirmed.');
  const v=p.vatRate/100, rate=p.ledRate/100, costFactor=p.profitMethod==='markup'?1/(1+p.profitPercent/100):1-p.profitPercent/100;
  const needsWeight=p.ledApplies&&p.ledMode!=='percentage';
  if (needsWeight && (kg===null || !p.usdToUGX || !Number.isFinite(p.usdToUGX) || !p.fxDate || !validDate(p.fxDate))) throw new Error('Weight-based LED requires valid KG and a saved positive USD→UGX rate/date.');
  const weight=kg!==null&&p.usdToUGX&&validDate(p.fxDate??'')?kg/1000*p.usdPer1000KG*p.usdToUGX:null;
  const levy=(net: number) => { const percentage=net*(p.percentageBase==='production-cost'?costFactor:1)*rate; if (!p.ledApplies) return 0; return p.ledMode==='higher'?calculateLED(net*(p.percentageBase==='production-cost'?costFactor:1),kg,p.usdToUGX,p.fxDate,p.percentageBase,p.vatOnLED).selectedUnrounded:p.ledMode==='percentage'?percentage:p.ledMode==='weight'?weight!:Math.min(percentage,weight!); };
  // Entered amount includes LED; inclusive mode also includes VAT. Solve a monotone
  // gross-price equation, including VAT-on-LED and cost-based levy, rather than subtracting assumed percentages.
  const gross=(net:number)=>net+levy(net)+v*(net+(p.vatOnLED?levy(net):0));
  const equation=(net:number)=>p.vatMode==='inclusive'?gross(net):net+levy(net);
  if (equation(0)>amount+0.0000001) throw new Error('Selling amount cannot cover the configured fixed weight levy.');
  let low=0,high=amount; for(let i=0;i<100;i++){const mid=(low+high)/2;if(equation(mid)>amount)high=mid;else low=mid;}
  const net=(low+high)/2, led=levy(net), vat=v*(net+(p.vatOnLED?led:0)), cost=net*costFactor;
  const result={ netSelling:roundMoney(net), vat:roundMoney(vat), percentageLED:p.ledApplies?roundMoney(net*(p.percentageBase==='production-cost'?costFactor:1)*rate):0, weightLED:weight===null?null:roundMoney(weight), selectedLED:roundMoney(led), selectedCalculation:p.ledApplies&&p.ledMode==='higher'?calculateLED(net*(p.percentageBase==='production-cost'?costFactor:1),kg,p.usdToUGX,p.fxDate,p.percentageBase,p.vatOnLED).selected:'legacy / not applicable', profit:roundMoney(net-cost), estimatedCOP:roundMoney(cost), finalPrice:p.vatMode==='inclusive'?roundMoney(amount):roundMoney(amount+vat), eligibleKG:kg, policy:structuredClone(p) };
  if (!Object.values(result).filter(v=>typeof v==='number').every(Number.isFinite)) throw new Error('Amounts exceed supported range.');
  return result;
}
export interface StockPriceSnapshot { id: string; productId: string; modelId?: string; batch: string; revision: number; date: string; quantity: number; unit: string; amount: number; conversion: QuantitySnapshot; policy: PricePolicy; breakdown: ReturnType<typeof sellingCostBreakdown>; actualCOP?: number; actualReference?: string; actor: string; createdAt: string }
