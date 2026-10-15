import { calculateConfiguredLED, type LEDInput, type LEDSnapshot } from './led';
import type { JobCardMaterial, Model, SalesOrder, SalesOrderItem } from '../types';
export type CostCurrency = 'USD' | 'UGX';
export interface MaterialRecipe { id: string; materialId: string; name: string; quantity: number; unit: string; currency: CostCurrency; price: number; priceUnit: string; exchangeRate: number; percentage: number; costGroup: 'material' | 'ink' }
export interface ProcessCost { stageId?: string; id: string; name: string; basis: 'per kg' | 'per piece' | 'per batch' | 'fixed'; rate: number; quantity: number; unit: string; remarks: string }
export interface CostingInput { led?: LEDInput; quotationId?: string; orderId: string; itemId: string; modelId: string; modelRevision: number; customer: string; product: string; specifications: string; quantity: number; unit: string; currency: CostCurrency; recipeMode: 'quantities' | 'percentages'; batchQuantity: number; batchUnit: string; materials: MaterialRecipe[]; processes: ProcessCost[]; wastePercent: number; wasteBasis: 'materials' | 'materials-and-processes'; overheads: number; additionalCosts: number; markupPercent: number; pricingMethod: 'markup' | 'gross-margin'; taxPercent: number; chargePercent: number; minimumCharge: number; taxOnCharges: boolean; validityDate: string; deliveryTerms: string; remarks: string }
export interface CostingTotals { led?: LEDSnapshot; materials: { id: string; quantity: number; unit: string; mixingPercent: number | null; convertedUnitCost: number; total: number }[]; materialCost: number; inkCost: number; processCosts: number[]; processCost: number; wasteCost: number; costOfProduction: number; profit: number; sellingBeforeTax: number; charges: number; tax: number; grandTotal: number; unitSellingPrice: number }
export type EstimateStatus = 'Draft' | 'Pending Review' | 'Approved' | 'Revision Required' | 'Superseded';
export interface CostEstimate { salesOrderReferences?: { orderId: string; itemId: string }[]; id: string; number: string; revision: number; previousId?: string; usedByJobCardId?: string; status: EstimateStatus; customerAcceptance: 'Pending' | 'Accepted' | 'Rejected'; input: CostingInput; totals: CostingTotals; createdAt: string; generatedAt?: string; approvedBy?: string; approvedAt?: string; reviewReason?: string }
export const MARKUP_SCENARIOS = [10, 15, 20, 25];
export const roundMoney = (n: number) => Math.round(n * 100) / 100;
const requireValue = (ok: unknown, message: string) => { if (!ok) throw new Error(message); };
export function convertQuantity(quantity: number, from: string, to: string) {
  requireValue(Number.isFinite(quantity) && quantity >= 0, 'Quantity must be finite and nonnegative.');
  if (from === to && from.trim()) return quantity;
  from = from.toLowerCase(); to = to.toLowerCase();
  const mass: Record<string, number> = { kg: 1, kgs: 1, kilo: 1, kilos: 1, kilogram: 1, kilograms: 1, g: 0.001, tonne: 1000 };
  requireValue(mass[from] && mass[to], `No configured conversion from ${from} to ${to}. Enter an explicit matching unit.`);
  return quantity * mass[from] / mass[to];
}
export function calculateCost(input: CostingInput): CostingTotals {
  requireValue(input.quantity > 0 && Number.isFinite(input.quantity) && input.unit.trim(), 'Enter order quantity and unit.');
  requireValue(input.currency === 'USD' || input.currency === 'UGX', 'Select USD or UGX.');
  requireValue(['quantities', 'percentages'].includes(input.recipeMode) && ['markup', 'gross-margin'].includes(input.pricingMethod) && ['materials', 'materials-and-processes'].includes(input.wasteBasis), 'Select valid recipe, waste and pricing bases.');
  requireValue(input.materials.length && new Set(input.materials.map(m => m.materialId)).size === input.materials.length, 'Select distinct recipe materials.');
  for (const n of [input.wastePercent, input.overheads, input.additionalCosts, input.markupPercent, input.taxPercent, input.chargePercent, input.minimumCharge]) requireValue(Number.isFinite(n) && n >= 0, 'Costs and percentages must be finite and nonnegative.');
  requireValue(input.wastePercent <= 100 && input.taxPercent <= 100 && input.chargePercent <= 100 && (input.pricingMethod !== 'gross-margin' || input.markupPercent < 100), 'Invalid percentage for the chosen calculation.');
  if (input.recipeMode === 'percentages') {
    requireValue(input.batchQuantity > 0 && Number.isFinite(input.batchQuantity), 'Enter the production batch quantity.');
    requireValue(Math.abs(input.materials.reduce((sum, m) => sum + m.percentage, 0) - 100) < 1e-6 && input.materials.every(m => Number.isFinite(m.percentage) && m.percentage > 0), 'Percentage recipe must total 100%.');
  }
  const quantities = input.materials.map(m => input.recipeMode === 'percentages' ? convertQuantity(input.batchQuantity * m.percentage / 100, input.batchUnit, m.unit) : m.quantity);
  const masses = input.materials.map((m, i) => ['kg', 'g', 'tonne'].includes(m.unit) ? convertQuantity(quantities[i], m.unit, 'kg') : null);
  const totalMass = masses.every(m => m !== null) ? masses.reduce<number>((sum, n) => sum + (n ?? 0), 0) : null;
  const materials = input.materials.map((m, i) => {
    requireValue(m.materialId && m.unit && m.priceUnit && Number.isFinite(m.price) && m.price >= 0 && quantities[i] > 0 && Number.isFinite(quantities[i]), 'Complete selected material, positive quantity, unit and purchase price.');
    requireValue(m.currency === 'USD' || m.currency === 'UGX', 'Select a purchase currency.');
    requireValue(m.currency === input.currency || (Number.isFinite(m.exchangeRate) && m.exchangeRate > 0), 'Enter target currency per one purchase currency as exchange rate.');
    const rate = m.currency === input.currency ? 1 : m.exchangeRate;
    const pricedQuantity = convertQuantity(quantities[i], m.unit, m.priceUnit);
    const convertedUnitCost = convertQuantity(1, m.unit, m.priceUnit) * m.price * rate;
    return { id: m.id, quantity: quantities[i], unit: m.unit, mixingPercent: totalMass && masses[i] !== null ? masses[i]! / totalMass * 100 : null, convertedUnitCost, total: roundMoney(pricedQuantity * m.price * rate) };
  });
  const materialCost = roundMoney(materials.filter((_, i) => input.materials[i].costGroup === 'material').reduce((s, m) => s + m.total, 0));
  const inkCost = roundMoney(materials.filter((_, i) => input.materials[i].costGroup === 'ink').reduce((s, m) => s + m.total, 0));
  const processCosts = input.processes.map(p => {
    requireValue(p.name.trim() && Number.isFinite(p.rate) && p.rate >= 0 && Number.isFinite(p.quantity) && p.quantity >= 0, 'Complete process name, quantity and nonnegative rate.');
    requireValue(['per kg', 'per piece', 'per batch', 'fixed'].includes(p.basis), 'Select process cost basis.');
    if (p.basis === 'per kg') requireValue(p.unit === 'kg', 'Per KG process quantity must be in kg.');
    if (p.basis === 'per piece') requireValue(p.unit === 'pcs', 'Per piece process quantity must be in pcs.');
    return roundMoney(p.rate * (p.basis === 'fixed' ? 1 : p.quantity));
  });
  const processCost = roundMoney(processCosts.reduce((s, n) => s + n, 0));
  const wasteCost = roundMoney((materialCost + inkCost + (input.wasteBasis === 'materials-and-processes' ? processCost : 0)) * input.wastePercent / 100);
  const costOfProduction = roundMoney(materialCost + inkCost + processCost + wasteCost + input.overheads + input.additionalCosts);
  const sellingBeforeTax = roundMoney(input.pricingMethod === 'gross-margin' ? costOfProduction / (1 - input.markupPercent / 100) : costOfProduction * (1 + input.markupPercent / 100));
  const profit = roundMoney(sellingBeforeTax - costOfProduction);
  const charges = roundMoney(Math.max(input.minimumCharge, sellingBeforeTax * input.chargePercent / 100));
  const led = calculateConfiguredLED(input.led,sellingBeforeTax,costOfProduction,input.currency);
  const tax = roundMoney((sellingBeforeTax + (input.taxOnCharges ? charges : 0) + (led?.vatOnLED ? led.selectedAmount : 0)) * input.taxPercent / 100);
  const grandTotal = roundMoney(sellingBeforeTax + charges + (led?.selectedAmount ?? 0) + tax);
  requireValue([materialCost, inkCost, processCost, wasteCost, costOfProduction, sellingBeforeTax, grandTotal].every(Number.isFinite), 'Costing amounts exceed the supported range.');
  return { led, materials, materialCost, inkCost, processCosts, processCost, wasteCost, costOfProduction, profit, sellingBeforeTax, charges, tax, grandTotal, unitSellingPrice: roundMoney(grandTotal / input.quantity) };
}
export function materialRequirements(input: CostingInput): JobCardMaterial[] {
  const totals = calculateCost(input);
  return input.materials.map((m, i) => ({ id: `requirement-${m.id}`, materialId: m.materialId, name: m.name, requiredQuantity: totals.materials[i].quantity, issuedQuantity: 0, unit: m.unit }));
}
export function newCostingForLine(source: { customer: string; orderId?: string; quotationId?: string }, item: SalesOrderItem, model: Model): CostingInput {
  let scale: number | null = null;
  if (model.batchQuantity && model.batchUnit) { try { scale = convertQuantity(item.quantity, item.unit, model.batchUnit) / model.batchQuantity; } catch { /* Different finished units need an explicit batch/yield, never an inferred conversion. */ } }
  const materials = structuredClone(model.recipe ?? []).map(m => ({ ...m, quantity: scale === null ? NaN : m.quantity * scale }));
  const processes = structuredClone(model.processes ?? []).map(p => ({ ...p, quantity: p.basis === 'fixed' ? 1 : scale === null ? NaN : p.quantity * scale }));
  return { orderId: source.orderId ?? '', quotationId: source.quotationId, itemId: item.id, modelId: model.id, modelRevision: model.revision ?? 1, customer: source.customer, product: item.itemName, specifications: item.specifications ?? model.specifications ?? '', quantity: item.quantity, unit: item.unit, currency: model.costingConfig?.currency ?? 'UGX', recipeMode: model.recipeMode ?? 'quantities', batchQuantity: scale === null ? 0 : (model.batchQuantity ?? 0) * scale, batchUnit: model.batchUnit ?? 'kg', materials, processes, wastePercent: model.wastePercent ?? 0, wasteBasis: 'materials', overheads: model.overheads ?? 0, additionalCosts: 0, markupPercent: model.costingConfig?.markupPercent ?? 10, pricingMethod: 'markup', taxPercent: model.costingConfig?.taxPercent ?? 0, chargePercent: 0, minimumCharge: 0, taxOnCharges: true, validityDate: '', deliveryTerms: '', remarks: '' };
}
export function newCostingInput(order: SalesOrder, item: SalesOrderItem, model: Model): CostingInput { return newCostingForLine({ customer: order.customerName, orderId: order.id }, item, model); }
export function estimateMatchesOrder(e: CostEstimate, orderId: string, itemId?: string) { return (e.input.orderId === orderId && (!itemId || e.input.itemId === itemId)) || !!e.salesOrderReferences?.some(r => r.orderId === orderId && (!itemId || r.itemId === itemId)); }
export function customerEstimate(estimate: CostEstimate) {
  const i = estimate.input, t = estimate.totals;
  return { number: estimate.number, revision: estimate.revision, date: (estimate.generatedAt ?? estimate.createdAt).slice(0, 10), customer: i.customer, product: i.product, modelId: i.modelId, modelRevision: i.modelRevision, specifications: i.specifications, quantity: i.quantity, unit: i.unit, unitSellingPrice: t.unitSellingPrice, led: t.led ? { selectedAmount:t.led.selectedAmount,vatOnLED:t.led.vatOnLED,method:t.led.method } : undefined, subtotal: t.sellingBeforeTax, charges: t.charges, tax: t.tax, grandTotal: t.grandTotal, currency: i.currency, validityDate: i.validityDate, deliveryTerms: i.deliveryTerms, remarks: i.remarks };
}

export function buildEstimateRevision(input: CostingInput, all: CostEstimate[], existingId?: string, now = new Date().toISOString()): CostEstimate {
  const existing = existingId ? all.find(e => e.id === existingId) : undefined;
  if (existingId && (!existing || !((existing.input.orderId === input.orderId && existing.input.itemId === input.itemId && existing.input.quotationId === input.quotationId) || (!input.quotationId && existing.salesOrderReferences?.some(r => r.orderId === input.orderId && r.itemId === input.itemId))))) throw new Error('Estimate revision belongs to another line.');
  const frozen = !!existing && (existing.status === 'Approved' || existing.status === 'Superseded' || !!existing.generatedAt || !!existing.approvedAt || !!existing.usedByJobCardId);
  const number = existing?.number ?? `EST-${new Set(all.map(e => e.number)).size + 1}`;
  const revision = existing ? frozen ? Math.max(...all.filter(e => e.number === number).map(e => e.revision)) + 1 : existing.revision : 1;
  return { id: !frozen && existing ? existing.id : crypto.randomUUID(), number, revision, previousId: frozen ? existing?.id : existing?.previousId, status: 'Draft', customerAcceptance: 'Pending', input: structuredClone(input), totals: calculateCost(input), createdAt: now };
}
export function transitionEstimate(estimate: CostEstimate, status: EstimateStatus, user: { name: string; role: string }, now = new Date().toISOString()): CostEstimate {
  if (status === 'Approved') {
    if (!['admin', 'accounts'].includes(user.role) || estimate.status !== 'Pending Review') throw new Error('Accounts/Admin can approve an estimate sent for review.');
    return { ...estimate, status, approvedBy: user.name, approvedAt: now };
  }
  if (status === 'Pending Review' && estimate.status === 'Draft') return { ...estimate, status, reviewReason: undefined };
  if (status === 'Revision Required' && ['Pending Review', 'Approved'].includes(estimate.status)) return { ...estimate, status, reviewReason: 'Reviewer requested a revision.' };
  throw new Error('Invalid costing status transition. Recalculate/save a new draft before resubmitting.');
}

export function transitionEstimateLedger(all: CostEstimate[], id: string, status: EstimateStatus, user: { name: string; role: string }): CostEstimate[] {
  const estimate = all.find(e => e.id === id); if (!estimate) throw new Error('Estimate not found.');
  const next = transitionEstimate(estimate, status, user);
  return all.map(row => row.id === id ? next : status === 'Approved' && row.number === estimate.number && (row.status === 'Approved' || !!row.approvedAt || !!row.generatedAt) ? { ...row, status: 'Superseded' } : row);
}
