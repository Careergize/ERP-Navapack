// Client-confirmed comparison and rates. Applicability, percentage base and VAT
// treatment remain explicit per-record choices; historical snapshots are not repriced.
export const LED_PERCENT = 2.5;
export const LED_USD_PER_TONNE = 70;
export interface LEDInput { applies: boolean; percentageBase?: 'net-selling' | 'production-cost'; eligibleWeightKG: number | null; usdToUGX?: number; fxDate?: string; vatOnLED: boolean; conversion?: { productId: string; modelId?: string; originalQuantity: number; originalUnit: string; convertedKG: number | null; conversionId?: string; conversionVersion?: number } }
export interface LEDSnapshot { method: 'higher'; percentageBase: NonNullable<LEDInput['percentageBase']>; baseAmount: number; eligibleWeightKG: number; percentageRate: number; usdPerTonne: number; usdToUGX: number; fxDate: string; percentageAmount: number; weightAmount: number; selectedUnrounded: number; selectedAmount: number; selected: 'percentage' | 'weight' | 'equal'; vatOnLED: boolean; conversion?: LEDInput['conversion'] }
const money=(n:number)=>Math.round(n*100)/100;
export function calculateLED(base:number,weightKG:number|null,usdToUGX:number|undefined,fxDate:string|undefined,percentageBase:LEDInput['percentageBase'],vatOnLED=false):LEDSnapshot {
 if(!['net-selling','production-cost'].includes(percentageBase??''))throw new Error('Choose the LED percentage base; final client base clarification is pending.');
 if(!Number.isFinite(base)||base<0)throw new Error('LED percentage base must be finite and nonnegative.');
 if(weightKG===null||!Number.isFinite(weightKG)||weightKG<0)throw new Error('LED MAX comparison requires eligible KG. Configure an exact product/model CTR conversion; percentage-only fallback is not permitted.');
 if(!usdToUGX||!Number.isFinite(usdToUGX)||usdToUGX<=0||!fxDate||!/^\d{4}-\d{2}-\d{2}$/.test(fxDate)||!Number.isFinite(Date.parse(fxDate))||new Date(fxDate+'T00:00:00Z').toISOString().slice(0,10)!==fxDate)throw new Error('LED MAX comparison requires a saved positive USD→UGX exchange rate and valid rate date.');
 const percentage=base*LED_PERCENT/100,weight=weightKG/1000*LED_USD_PER_TONNE*usdToUGX;
 if(![percentage,weight].every(Number.isFinite))throw new Error('LED exceeds the supported amount range.');
 return {method:'higher',percentageBase:percentageBase!,baseAmount:base,eligibleWeightKG:weightKG,percentageRate:LED_PERCENT,usdPerTonne:LED_USD_PER_TONNE,usdToUGX,fxDate,percentageAmount:money(percentage),weightAmount:money(weight),selectedUnrounded:Math.max(percentage,weight),selectedAmount:money(Math.max(percentage,weight)),selected:Math.abs(percentage-weight)<=Number.EPSILON*Math.max(1,percentage,weight)*8?'equal':percentage>weight?'percentage':'weight',vatOnLED};
}
export function calculateConfiguredLED(input:LEDInput|undefined,netSelling:number,productionCost:number|undefined,currency:string):LEDSnapshot|undefined {
 if(!input?.applies)return;
 if(currency!=='UGX')throw new Error('LED is calculated in UGX. Use an UGX costing/quotation; no implicit document currency conversion.');
 const base=input.percentageBase==='production-cost'?productionCost:netSelling;
 if(base===undefined)throw new Error('Production-cost LED base requires an approved costing source.');
 return {...calculateLED(base,input.eligibleWeightKG,input.usdToUGX,input.fxDate,input.percentageBase,input.vatOnLED),conversion:input.conversion?structuredClone(input.conversion):undefined};
}
