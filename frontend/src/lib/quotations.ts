import { calculateConfiguredLED, type LEDInput, type LEDSnapshot } from './led';
import type { CustomerType, Model, SalesOrder, User } from '../types';
import { customerEstimate, type CostEstimate } from './customCosting';
import { calculateCommercialTotals, COMMERCIAL_ROUNDING, type CommercialTotals, type TaxMode } from './commercialPricing';
import { today, type SalesOrderDraft } from './salesOrders';
export interface BankAccount { id: string; bank: string; accountName: string; accountNumber: string; currency: string; branch: string }
export interface CompanySettings { tradingName: string; legalName: string; logo: string; address: string; telephone: string; email: string; tin: string; signatory: string; banks: BankAccount[]; currency: string; taxRate: number; taxMode: TaxMode; validityDays: number }
export interface QuotationCustomer { customerId?: string; prospectId?: string; name: string; billingAddress: string; deliveryAddress: string; contactPerson: string; telephone: string; email: string; customerType: CustomerType; tin: string }
export interface QuotationTerms { name?: string; priceValidity: string; deliveryPeriod: string; paymentTerms: string; advancePercent?: number; creditDays?: number; revisionClause: string; quantityTolerance?: number; additionalTerms: string; remarks: string }
export interface QuotationLine { id: string; manualPriceOverride?: boolean; unitId?: number; led?: LEDInput; ledSnapshot?: LEDSnapshot; type: 'stock' | 'custom'; productId?: string; modelId?: string; modelRevision?: number; description: string; group: string; specifications: string; quantity: number; unit: string; unitPrice: number; estimateId?: string; estimateRevision?: number }
export type QuotationStatus = 'Internally Rejected' | 'Revision Requested' | 'Draft' | 'Pending Internal Approval' | 'Approved' | 'Sent' | 'Accepted' | 'Rejected' | 'Expired' | 'Converted to Sales Order' | 'Superseded';
export interface QuotationEvent { id: string; at: string; user: string; userId: string; type: string; description: string }
export interface QuotationResponse { id: string; response: 'Accepted' | 'Rejected' | 'Revision Requested' | 'Pending'; date: string; respondedBy: string; remarks: string; reference: string; revision: number }
export interface Quotation { generationKey?: string; emailDrafts?: import('./quotationReview').QuotationEmailDraft[]; id: string; draftVersion?: number; rootId: string; number: string; revision: number; previousId?: string; documentType: 'Sales Quotation' | 'Proforma Invoice'; date: string; validityDays: number; validUntil: string; deliveryDays?: number; currency: string; taxRate: number; taxMode: TaxMode; discount: number; customer: QuotationCustomer; company: CompanySettings; terms: QuotationTerms; salesRepresentative: string; lines: QuotationLine[]; status: QuotationStatus; createdBy: string; createdById: string; approval?: { id: string; user: string; userId: string; at: string; totals: CommercialTotals; roundingPolicy: string }; responses: QuotationResponse[]; events: QuotationEvent[]; salesOrderId?: string }
export const QUOTATION_VIEW_ROLES = ['project_manager', 'receptionist', 'accounts', 'production_manager', 'admin'];
export const QUOTATION_EDIT_ROLES = ['receptionist', 'accounts', 'admin'];
export const QUOTATION_APPROVE_ROLES = ['project_manager', 'production_manager'];
export const EMPTY_TERMS: QuotationTerms = { priceValidity: '', deliveryPeriod: '', paymentTerms: '', revisionClause: '', additionalTerms: '', remarks: '' };
export const COMPANY_DEFAULTS: CompanySettings = { tradingName: 'NAVAPACK', legalName: 'Nova Recycling Industries Ltd', logo: '/assets/Nava-logo.png', address: 'Plot 22, Ring Road\nNalukolongo Industrial Area\nKampala', telephone: '0753349228', email: 'novarecyclingindltd@gmail.com', tin: '1017362107', signatory: '', banks: [{ id: 'dfcu-reference', bank: 'DFCU Bank', branch: 'Ndeeba Branch', accountName: 'Nova Recycling Industries Ltd.', accountNumber: '01450016576735', currency: 'UGX' }, { id: 'dtb-reference', bank: 'Diamond Trust Bank', branch: 'Ndeeba Branch', accountName: 'Nova Recycling Industries Ltd.', accountNumber: '0272021001', currency: 'UGX' }], currency: 'UGX', taxRate: 18, taxMode: 'inclusive', validityDays: 14 };
export const blankCustomer = (): QuotationCustomer => ({ name: '', billingAddress: '', deliveryAddress: '', contactPerson: '', telephone: '', email: '', customerType: 'B2B', tin: '' });
export const blankQuotationLine = (): QuotationLine => ({ id: crypto.randomUUID(), type: 'stock', description: '', group: '', specifications: '', quantity: 1, unit: '', unitPrice: 0 });
export function validCommercialDate(date: string) { return /^\d{4}-\d{2}-\d{2}$/.test(date) && Number.isFinite(Date.parse(date)) && new Date(`${date}T00:00:00Z`).toISOString().slice(0, 10) === date; }
export function addDays(date: string, days: number) { if (!validCommercialDate(date) || !Number.isInteger(days) || days < 0 || days > 3650) throw new Error('Use a valid date and 0–3650 days.'); const d = new Date(`${date}T00:00:00Z`); d.setUTCDate(d.getUTCDate() + days); return d.toISOString().slice(0, 10); }
export const quotationTotals = (q: Quotation) => {
 q.lines.forEach(l=>{if(l.led?.applies){if(!l.ledSnapshot)throw new Error('LED MAX requires valid weight, FX and an explicitly applied snapshot; percentage fallback is forbidden.');if(l.type==='stock'){if(l.led.conversion?.productId!==l.productId||l.led.conversion?.modelId!==l.modelId||l.led.conversion?.originalQuantity!==l.quantity||l.led.conversion?.originalUnit!==l.unit)throw new Error('LED weight source changed. Refresh the product/model conversion snapshot.');const net=l.quantity*l.unitPrice/(q.taxMode==='inclusive'?1+q.taxRate/100:1);const expected=calculateConfiguredLED(l.led,net,undefined,q.currency);if(JSON.stringify(expected)!==JSON.stringify(l.ledSnapshot))throw new Error('LED source/price changed. Refresh and apply the LED snapshot.');}}});
 return calculateCommercialTotals(q.lines,q.discount,q.taxRate,q.taxMode);
};
export function effectiveQuotationStatus(q: Quotation, date = today()): QuotationStatus { return ['Approved', 'Sent', 'Accepted'].includes(q.status) && q.validUntil < date ? 'Expired' : q.status; }
export function quotationEvent(user: User, type: string, description: string): QuotationEvent { return { id: crypto.randomUUID(), at: new Date().toISOString(), user: user.name, userId: user.id, type, description }; }
export function createQuotation(company: CompanySettings, all: Quotation[], user: User): Quotation {
  if (!QUOTATION_EDIT_ROLES.includes(user.role)) throw new Error('Your role cannot create quotations.');
  const id = crypto.randomUUID(); const date = today();
  return { id, rootId: id, number: `QT-${Math.max(0, ...all.map(q => Number(q.number.replace('QT-', '')) || 0)) + 1}`, revision: 1, documentType: 'Sales Quotation', date, validityDays: company.validityDays, validUntil: addDays(date, company.validityDays), currency: company.currency, taxRate: company.taxRate, taxMode: company.taxMode, discount: 0, customer: blankCustomer(), company: structuredClone(company), terms: { ...EMPTY_TERMS }, salesRepresentative: '', lines: [], status: 'Draft', createdBy: user.name, createdById: user.id, responses: [], events: [quotationEvent(user, 'Created', 'Commercial draft; no order, production or stock transaction.')] };
}
export function validateQuotation(q: Quotation, complete = true) {
  if (!q.number.trim() || !validCommercialDate(q.date) || q.validUntil !== addDays(q.date, q.validityDays) || !q.currency.trim() || !['Sales Quotation', 'Proforma Invoice'].includes(q.documentType)) throw new Error('Complete document identity, dates, currency and type.');
  if (q.deliveryDays !== undefined && (!Number.isInteger(q.deliveryDays) || q.deliveryDays < 0)) throw new Error('Delivery lead time must be a nonnegative whole number.');
  for (const n of [q.terms.advancePercent, q.terms.quantityTolerance]) if (n !== undefined && (!Number.isFinite(n) || n < 0 || n > 100)) throw new Error('Commercial percentages must be 0–100.');
  if (q.terms.creditDays !== undefined && (!Number.isInteger(q.terms.creditDays) || q.terms.creditDays < 0)) throw new Error('Credit days must be nonnegative.');
  if (new Set(q.lines.map(l => l.id)).size !== q.lines.length) throw new Error('Quotation line IDs must be distinct.');
  if (complete && ((!q.customer.customerId && !q.customer.prospectId) || !q.customer.name.trim() || !['B2B', 'B2C'].includes(q.customer.customerType) || !q.salesRepresentative.trim() || !q.lines.length)) throw new Error('Complete customer, sales representative and at least one line.');
  if (q.lines.some(l => !l.description.trim() || !l.unit.trim() || (l.type === 'stock' ? !l.productId : !l.modelId || !l.modelRevision))) throw new Error('Choose exact products/models, descriptions and units for each line.');
  quotationTotals(q);
}
export function matchesQuotationCost(e: CostEstimate, q: Quotation, line: QuotationLine) { return e.input.quotationId === q.rootId && e.input.itemId === line.id && e.input.customer === q.customer.name && e.input.quantity === line.quantity && e.input.unit === line.unit && e.input.modelId === line.modelId && e.input.modelRevision === line.modelRevision && e.input.specifications === line.specifications; }
export function quotedCostPrice(e: CostEstimate, q: Pick<Quotation, 'currency' | 'taxMode' | 'taxRate'>) {
  const publicPrice = customerEstimate(e);
  if (e.status !== 'Approved' || publicPrice.currency !== q.currency) throw new Error('Select approved costing in this document currency; no implicit exchange conversion.');
  const net = (publicPrice.subtotal + publicPrice.charges) / publicPrice.quantity;
  return q.taxMode === 'inclusive' ? net * (1 + q.taxRate / 100) : net;
}
export function validateQuotationSources(q: Quotation, estimates: CostEstimate[], versions: Model[]) {
  q.lines.filter(l => l.type === 'custom').forEach(line => {
    const e = estimates.find(e => e.id === line.estimateId);
    const approvedPrice = e ? quotedCostPrice(e, q) : undefined;
    const latest = Math.max(...versions.filter(m => m.id === line.modelId).map(m => m.revision ?? 1));
<<<<<<< HEAD:src/lib/quotations.ts
    if (!e || e.revision !== line.estimateRevision || !matchesQuotationCost(e, q, line) || latest !== line.modelRevision || (!line.manualPriceOverride && Math.abs((approvedPrice ?? 0) - line.unitPrice) > 1e-9)) throw new Error('Custom model/costing/quantity/price changed or is not approved. Revise/review this quotation and explicitly apply the approved price.');
=======
    if (!e || e.revision !== line.estimateRevision || !matchesQuotationCost(e, q, line) || latest !== line.modelRevision || Math.abs(quotedCostPrice(e, q) - line.unitPrice) > 1e-9 || JSON.stringify(e.totals.led)!==JSON.stringify(line.ledSnapshot)) throw new Error('Custom model/costing/quantity/price changed or is not approved. Revise/review this quotation and explicitly apply the approved price.');
>>>>>>> 34ecef126e16762b3c91dbf7bdf790e011046938:frontend/src/lib/quotations.ts
  });
}
export function submitQuotation(q: Quotation, estimates: CostEstimate[], models: Model[], user: User, date = today()): Quotation {
  if (!QUOTATION_EDIT_ROLES.includes(user.role) || q.status !== 'Draft' || q.validUntil < date) throw new Error('Submit only a current draft with an authorized sales role.');
  validateQuotation(q); validateQuotationSources(q, estimates, models);
  return { ...q, status: 'Pending Internal Approval', events: [...q.events, quotationEvent(user, 'Submitted', 'Internal price/tax/terms review requested.')] };
}
export function approveQuotation(q: Quotation, estimates: CostEstimate[], models: Model[], user: User, date = today()): Quotation {
  if (!QUOTATION_APPROVE_ROLES.includes(user.role) || q.status !== 'Pending Internal Approval' || q.validUntil < date) throw new Error('Only a Project Manager or Production Manager approves current submitted revisions.');
  validateQuotation(q); validateQuotationSources(q, estimates, models);
  return { ...q, status: 'Approved', approval: { id: crypto.randomUUID(), user: user.name, userId: user.id, at: new Date().toISOString(), totals: quotationTotals(q), roundingPolicy: COMMERCIAL_ROUNDING }, events: [...q.events, quotationEvent(user, 'Internally approved', 'Commercial snapshots frozen; customer has not accepted.')] };
}
export function sendQuotation(q: Quotation, estimates: CostEstimate[], models: Model[], user: User, date = today()): Quotation {
  if (!QUOTATION_EDIT_ROLES.includes(user.role) || effectiveQuotationStatus(q, date) !== 'Approved') throw new Error('Mark only current internally approved revisions as sent.');
  validateQuotationSources(q, estimates, models);
  return { ...q, status: 'Sent', events: [...q.events, quotationEvent(user, 'Marked sent', 'Recorded customer delivery; no automatic acceptance or email transmission.')] };
}
export function recordQuotationResponse(q: Quotation, response: Omit<QuotationResponse, 'id' | 'revision'>, user: User, date = today()): Quotation {
  const sentDate = q.events.find(e => e.type === 'Marked sent')?.at.slice(0, 10) ?? q.date;
  if (!QUOTATION_EDIT_ROLES.includes(user.role) || q.status !== 'Sent' || !['Accepted', 'Rejected', 'Revision Requested', 'Pending'].includes(response.response) || !validCommercialDate(response.date) || response.date > date || response.date < sentDate || !response.respondedBy.trim() || !response.remarks.trim()) throw new Error('Record a response to a sent revision with valid date, respondent and remarks.');
  if (response.response === 'Accepted' && response.date > q.validUntil) throw new Error('Acceptance after expiry requires a new approved revision.');
  const r = { ...response, id: crypto.randomUUID(), revision: q.revision };
  return { ...q, responses: [...q.responses, r], status: r.response === 'Accepted' ? 'Accepted' : r.response === 'Rejected' ? 'Rejected' : r.response === 'Revision Requested' ? 'Revision Requested' : 'Sent', events: [...q.events, quotationEvent(user, `Customer ${r.response}`, `${r.respondedBy}, ${r.date}; ${r.remarks}; reference ${r.reference || 'not supplied'}.`)] };
}
export function publicQuotation(q: Quotation) {
  return { number: q.number, revision: q.revision, documentType: q.documentType, date: q.date, validityDays: q.validityDays, validUntil: q.validUntil, deliveryDays: q.deliveryDays, currency: q.currency, taxRate: q.taxRate, taxMode: q.taxMode, status: effectiveQuotationStatus(q), salesRepresentative: q.salesRepresentative,
    company: { tradingName: q.company.tradingName, legalName: q.company.legalName, logo: q.company.logo, address: q.company.address, telephone: q.company.telephone, email: q.company.email, tin: q.company.tin, signatory: q.company.signatory, banks: structuredClone(q.company.banks) },
    customer: { name: q.customer.name, billingAddress: q.customer.billingAddress, deliveryAddress: q.customer.deliveryAddress, contactPerson: q.customer.contactPerson, telephone: q.customer.telephone, email: q.customer.email, customerType: q.customer.customerType, tin: q.customer.tin },
<<<<<<< HEAD:src/lib/quotations.ts
    lines: q.lines.map(l => ({ description: l.description, group: l.group, specifications: l.specifications, quantity: l.quantity, unit: l.unit, ...(l.unitId ? { unit_id: l.unitId } : {}), unitPrice: l.unitPrice })), terms: structuredClone(q.terms), totals: structuredClone(q.approval?.totals ?? quotationTotals(q)) };
=======
    lines: q.lines.map(l => ({ description: l.description, group: l.group, specifications: l.specifications, quantity: l.quantity, unit: l.unit, unitPrice: l.unitPrice, led: l.ledSnapshot ? {method:l.ledSnapshot.method,selectedAmount:l.ledSnapshot.selectedAmount,vatOnLED:l.ledSnapshot.vatOnLED} : undefined })), terms: structuredClone(q.terms), totals: structuredClone(q.approval?.totals ?? quotationTotals(q)) };
>>>>>>> 34ecef126e16762b3c91dbf7bdf790e011046938:frontend/src/lib/quotations.ts
}
export function reviseQuotation(q: Quotation, all: Quotation[], company: CompanySettings, user: User, duplicate = false): Quotation {
  if (!QUOTATION_EDIT_ROLES.includes(user.role) || (!duplicate && ['Converted to Sales Order', 'Superseded'].includes(q.status))) throw new Error('Revise the current unconverted quotation, or duplicate into a new offer.');
  const fresh = createQuotation(company, all, user);
  return { ...fresh, generationKey: duplicate ? undefined : q.generationKey, rootId: duplicate ? fresh.rootId : q.rootId, number: duplicate ? fresh.number : q.number, revision: duplicate ? 1 : Math.max(...all.filter(n => n.rootId === q.rootId).map(n => n.revision)) + 1, previousId: duplicate ? undefined : q.id, documentType: q.documentType, validityDays: q.validityDays, validUntil: addDays(fresh.date, q.validityDays), deliveryDays: q.deliveryDays, currency: q.currency, taxRate: q.taxRate, taxMode: q.taxMode, discount: q.discount, customer: structuredClone(q.customer), terms: structuredClone(q.terms), salesRepresentative: q.salesRepresentative, lines: structuredClone(q.lines).map(l => duplicate ? { ...l, id: crypto.randomUUID(), led:undefined,ledSnapshot:undefined, estimateId: undefined, estimateRevision: undefined, unitPrice: l.type === 'custom' ? 0 : l.unitPrice } : l), events: [quotationEvent(user, duplicate ? 'Duplicated' : 'Revision created', `From ${q.number} revision ${q.revision}; prior commercial content retained.`)] };
}
export function quotationConversionDraft(q: Quotation, customerId: string, requiredDate: string, orders: SalesOrder[], estimates: CostEstimate[], models: Model[], date = today()): SalesOrderDraft {
  if (orders.some(o => o.quotationId === q.rootId)) throw new Error('This quotation already has a Sales Order.');
  if (effectiveQuotationStatus(q, date) !== 'Accepted' || !q.approval || !q.responses.some(r => r.response === 'Accepted' && r.revision === q.revision)) throw new Error('Convert only the current, internally approved, accepted and unexpired revision.');
  validateQuotation(q); validateQuotationSources(q, estimates, models);
  if (!customerId) throw new Error('Explicitly select/link the customer master; conversion never creates a customer automatically.');
  if (q.lines.some(l => l.type === 'custom') && (!validCommercialDate(requiredDate) || requiredDate < date)) throw new Error('Confirm a manufacturing delivery date on or after the order date.');
  return { quotationId: q.rootId, quotationRevisionId: q.id, quotationNumber: q.number, quotationRevision: q.revision, prospectId: q.customer.prospectId, customerId, customerName: q.customer.name, date, marketingPersonName: q.salesRepresentative, customerType: q.customer.customerType, requisitionOrder: '', customerContact: structuredClone(q.customer), commercialTerms: structuredClone(q.terms), commercialPricing: { taxMode: q.taxMode, discount: q.discount, roundingPolicy: q.approval.roundingPolicy }, taxRate: q.taxRate, currency: q.currency, items: q.lines.map(l => ({ id: crypto.randomUUID(), quotationLineId: l.id, ledSnapshot:l.ledSnapshot?structuredClone(l.ledSnapshot):undefined, itemId: l.productId, modelId: l.modelId, modelRevision: l.modelRevision, estimateId: l.estimateId, quotationCostEstimateId: l.estimateId, quotationCostEstimateRevision: l.estimateRevision, fulfillmentSource: l.type === 'custom' ? 'manufacturing' : 'stock', itemName: l.description, specifications: l.specifications, quantity: l.quantity, unit: l.unit, unitPrice: l.unitPrice, totalPrice: l.quantity * l.unitPrice, requiredDate: l.type === 'custom' ? requiredDate : undefined })) };
}
