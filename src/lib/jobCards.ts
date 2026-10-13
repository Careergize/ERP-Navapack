import type { JobCard, JobCardActivity, JobProductionStage, ProductionStageStatus, SalesOrder, User } from '../types';

export const JOB_STATUS_LABELS = {
  Draft: 'Draft', PendingApproval: 'Pending Approval', Approved: 'Approved', StoreIssuePending: 'Store Issue Pending',
  Issued: 'Material Issued', MaterialIssued: 'Material Issued', InProduction: 'In Production', OnHold: 'On Hold', ReadyForStock: 'Ready for Stock', Completed: 'Completed',
};
export const PRODUCTION_STATUS_LABELS: Record<ProductionStageStatus, string> = { Pending: 'Pending', Received: 'Received', InProgress: 'In Progress', Completed: 'Completed', OnHold: 'On Hold' };
export const localToday = () => new Date().toLocaleDateString('en-CA');
export const orderedStages = (card: JobCard) => [...(card.productionStages ?? [])].sort((a, b) => a.sequence - b.sequence);
export const productionStages = (card: JobCard) => orderedStages(card).filter(s => s.required && s.kind === 'production');
export const isDelayed = (card: JobCard, today = localToday()): boolean => card.manufacturingItems ? card.manufacturingItems.some(i => isDelayed(i, today)) : card.status !== 'Completed' && !!card.requiredDate && card.requiredDate < today;
export const fmtQuantity = (value: number | null | undefined, unit = '') => value == null ? 'Not recorded' : `${value.toLocaleString('en-IN', { maximumFractionDigits: 3 })}${unit ? ` ${unit}` : ''}`;
export function currentLocation(card: JobCard): { department: string; stage: string } {
  if (card.manufacturingItems) { const locations = card.manufacturingItems.map(currentLocation); return { department: [...new Set(locations.map(l => l.department))].join(', '), stage: [...new Set(locations.map(l => l.stage))].join(', ') }; }
  if (card.status === 'Draft' || card.status === 'PendingApproval') return { department: 'Production Manager', stage: 'PM Approval' };
  if (card.status === 'Approved' || card.status === 'StoreIssuePending') return { department: 'Store', stage: 'Store Issue' };
  if (card.status === 'ReadyForStock' || card.status === 'Completed') return { department: 'Stock Keeping', stage: card.status === 'Completed' ? 'Stock Confirmed' : orderedStages(card).find(s => s.required && s.kind === 'stock' && s.status !== 'Completed')?.name ?? 'Stock Keeping' };
  const stages = orderedStages(card).filter(s => s.required);
  const current = stages.find(s => ['InProgress', 'OnHold', 'Received'].includes(s.status)) ?? stages.find(s => s.status !== 'Completed');
  return { department: current?.department ?? card.department, stage: current?.name ?? 'Not recorded' };
}
export function productionTotals(card: JobCard) {
  const stages = productionStages(card);
  const last = stages.at(-1);
  const waste = new Map<string, number>();
  stages.forEach(stage => { if (stage.wasteQuantity != null) waste.set(stage.wasteUnit, (waste.get(stage.wasteUnit) ?? 0) + stage.wasteQuantity); });
  return { produced: last?.outputQuantity ?? null, unit: last?.outputUnit ?? card.unit ?? '', waste: [...waste].map(([unit, quantity]) => fmtQuantity(quantity, unit)).join(', ') || 'Not recorded' };
}
export function jobSummary(cards: JobCard[], today = localToday()) {
  return [
    ['Total Active', cards.filter(c => c.status !== 'Completed').length],
    ['Pending Approval', cards.filter(c => c.status === 'PendingApproval').length],
    ['Store Issue Pending', cards.filter(c => ['Approved', 'StoreIssuePending'].includes(c.status)).length],
    ['In Production', cards.filter(c => c.status === 'InProduction').length],
    ['Delayed', cards.filter(c => isDelayed(c, today)).length],
    ['Completed', cards.filter(c => c.status === 'Completed').length],
  ] as [string, number][];
}
export function normalizeJobCard(card: JobCard, orders: SalesOrder[] = []): JobCard {
  const order = orders.find(o => o.id === card.salesOrderId);
  const stages: JobProductionStage[] = card.productionStages ?? (card.stages ?? []).map(stage => ({
    id: `${card.id}-${stage.stage}`, legacyStage: stage.stage, name: stage.stage, department: stage.stage,
    sequence: stage.sequenceOrder, required: stage.required, kind: ['Stock', 'Ready to Sale'].includes(stage.stage) ? 'stock' : 'production',
    status: stage.status === 'Complete' ? 'Completed' : stage.status === 'InProgress' ? 'InProgress' : 'Pending',
    inputQuantity: null, outputQuantity: null, wasteQuantity: null, inputUnit: '', outputUnit: '', wasteUnit: '', operator: '', remarks: '',
  }));
  const normalized = { ...card, stages: card.stages ?? [], salesOrderNumber: card.salesOrderNumber ?? order?.orderNumber,
    customerName: card.customerName ?? order?.customerName, productionStages: stages, requiredMaterials: card.requiredMaterials ?? [], activityHistory: card.activityHistory ?? [] };
  return { ...normalized, department: currentLocation(normalized).department };
}
export interface JobFilters { query: string; status: string; department: string; stage: string; from: string; to: string }
export function filterJobCards(cards: JobCard[], filters: JobFilters, today = localToday()) {
  return cards.filter(card => {
    const items = card.manufacturingItems ?? [card];
    const text = [card.jobCardNumber, card.salesOrderNumber, card.customerName, ...items.flatMap(i => [i.modelName, i.product])].join(' ').toLowerCase();
    return filters.query.trim().toLowerCase().split(/\s+/).every(word => text.includes(word)) &&
      (filters.status === 'all' || (filters.status === 'Delayed' ? isDelayed(card, today) : filters.status === 'MaterialIssued' ? ['Issued', 'MaterialIssued'].includes(card.status) : card.status === filters.status)) &&
      (filters.department === 'all' || items.some(i => currentLocation(i).department === filters.department)) && (filters.stage === 'all' || items.some(i => currentLocation(i).stage === filters.stage)) &&
      (!filters.from || (!!card.createdDate && card.createdDate.slice(0, 10) >= filters.from)) &&
      (!filters.to || (!!card.createdDate && card.createdDate.slice(0, 10) <= filters.to));
  });
}
function assert(condition: unknown, message: string): asserts condition { if (!condition) throw new Error(message); }
const validQuantity = (value: number | null) => value !== null && Number.isFinite(value) && value >= 0;
const timestamp = (value: string | undefined) => value ? Date.parse(value) : NaN;
function requireRole(user: User, roles: string[]) { assert(roles.includes(user.role), 'Your role cannot perform this action.'); }
function event(card: JobCard, user: User, action: string, description: string, now: string, department = currentLocation(card).department): JobCardActivity[] {
  return [...(card.activityHistory ?? []), { id: crypto.randomUUID(), timestamp: now, action, user: user.name, department, description }];
}
export function approveJobCard(card: JobCard, user: User, now = new Date().toISOString()): JobCard {
  requireRole(user, ['production_manager', 'admin']);
  assert(['Draft', 'PendingApproval'].includes(card.status), 'This job card is already approved.');
  assert(!card.requirementsReviewRequired, 'Recalculate/review requirements and costing before routing approval.');
  assert(productionStages(card).length, 'At least one production stage is required.');
  return { ...card, status: 'StoreIssuePending', department: 'Store', routingApproved: { revision: card.routingRevision ?? 1, stages: structuredClone(orderedStages(card)), materials: structuredClone(card.requiredMaterials ?? []), approvedBy: user.name, approvedAt: now }, approval: { approvedBy: user.name, approvedAt: now },
    activityHistory: event(card, user, 'Approved', 'Production Manager approved the job card and forwarded it for Store Issue.', now) };
}
export function issueJobMaterials(card: JobCard, quantities: Record<string, number>, available: Record<string, number | null>, user: User, now = new Date().toISOString()): JobCard {
  requireRole(user, ['store_keeper', 'admin']);
  assert(['Approved', 'StoreIssuePending', 'MaterialIssued', 'Issued'].includes(card.status), 'Materials can only be issued after approval and before production.');
  const materials = card.requiredMaterials ?? [];
  assert(materials.length, 'Required materials are not configured.');
  let issuedAny = false;
  const requiredMaterials = materials.map(material => {
    const quantity = quantities[material.id] ?? 0;
    assert(validQuantity(quantity), 'Issue quantities must be finite and nonnegative.');
    assert(quantity <= Math.max(0, material.requiredQuantity - material.issuedQuantity) + 1e-6, `Issue exceeds the remaining requirement for ${material.name}.`);
    assert(quantity === 0 || available[material.id] == null || quantity <= available[material.id]! + 1e-6, `Issue exceeds recorded availability for ${material.name}.`);
    issuedAny ||= quantity > 0;
    return { ...material, issuedQuantity: Math.round((material.issuedQuantity + quantity) * 1e6) / 1e6 };
  });
  assert(issuedAny, 'Enter an issue quantity greater than zero.');
  const full = requiredMaterials.every(material => material.issuedQuantity >= material.requiredQuantity);
  const updated: JobCard = { ...card, requiredMaterials, status: 'MaterialIssued', activityHistory: event(card, user, 'Materials issued', `${full ? 'Full' : 'Partial'} material issue recorded in frontend state; inventory is unchanged.`, now, 'Store') };
  return { ...updated, department: currentLocation(updated).department };
}
export type StageUpdate = Pick<JobProductionStage, 'inputQuantity' | 'outputQuantity' | 'wasteQuantity' | 'inputUnit' | 'outputUnit' | 'wasteUnit' | 'status' | 'startedAt' | 'completedAt' | 'operator' | 'remarks' | 'wasteType' | 'wasteReason' | 'sentToRecycling'>;
export function updateJobStage(card: JobCard, id: string, update: StageUpdate, user: User, now = new Date().toISOString()): JobCard {
  requireRole(user, ['production_operator', 'production_manager', 'admin']);
  assert(['Issued', 'MaterialIssued', 'InProduction', 'OnHold'].includes(card.status), 'Approve and issue materials before updating production.');
  const all = orderedStages(card);
  assert(new Set(all.map(s => s.id)).size === all.length && new Set(all.map(s => s.sequence)).size === all.length && all.every(s => Number.isFinite(s.sequence) && s.sequence > 0), 'Stage IDs and sequence numbers must be unique and valid.');
  const stage = all.find(s => s.id === id);
  assert(stage && stage.required && stage.kind === 'production', 'Select a required production stage.');
  const approvedStage = card.estimateId ? card.routingApproved?.stages.find(s => s.id === id) : undefined;
  if (approvedStage) assert(update.inputUnit === approvedStage.inputUnit && update.outputUnit === approvedStage.outputUnit && update.wasteUnit === approvedStage.wasteUnit, 'Actual stage units must match the PM-approved routing.');
  assert(stage.status !== 'Completed', 'Completed stage records are locked.');
  const previous = all.filter(s => s.required && s.kind === 'production' && s.sequence < stage.sequence);
  assert(previous.every(s => s.status === 'Completed'), 'Complete the previous stages before updating this stage.');
  assert(Object.hasOwn(PRODUCTION_STATUS_LABELS, update.status), 'Invalid stage status.');
  for (const value of [update.inputQuantity, update.outputQuantity, update.wasteQuantity]) assert(value === null || validQuantity(value), 'Stage quantities must be finite and nonnegative.');
  assert(Number.isFinite(update.sentToRecycling ?? 0) && (update.sentToRecycling ?? 0) >= 0 && (update.sentToRecycling ?? 0) <= (update.wasteQuantity ?? 0), 'Recycling quantity cannot exceed stage waste.');
  if (stage.handover && stage.handover.unit === stage.inputUnit) assert(update.inputUnit === stage.inputUnit && update.inputQuantity === stage.handover.quantity, 'Received input and unit must match the previous stage output.');
  if (update.status !== 'Pending') {
    assert(validQuantity(update.inputQuantity) && update.inputUnit.trim(), 'Record input quantity and unit.');
    assert(update.operator.trim(), 'Record the responsible operator.');
  }
  if (['InProgress', 'Completed', 'OnHold'].includes(update.status)) assert(Number.isFinite(timestamp(update.startedAt)), 'Record a valid start date/time.');
  if (update.completedAt) assert(update.status === 'Completed', 'Completion time is only allowed for a completed stage.');
  if (update.startedAt) assert(Number.isFinite(timestamp(update.startedAt)) && timestamp(update.startedAt) <= timestamp(now), 'Start time cannot be invalid or in the future.');
  if (update.status === 'Completed') {
    assert(validQuantity(update.outputQuantity) && validQuantity(update.wasteQuantity) && update.outputUnit.trim() && update.wasteUnit.trim(), 'Record output, waste and their units.');
    assert(Number.isFinite(timestamp(update.completedAt)) && timestamp(update.completedAt) >= timestamp(update.startedAt) && timestamp(update.completedAt) <= timestamp(now), 'Completion time must follow the start and cannot be in the future.');
  }
  if (update.inputUnit && update.inputUnit === update.outputUnit && update.inputQuantity !== null && update.outputQuantity !== null) {
    assert(update.outputQuantity <= update.inputQuantity + 1e-6, 'Output cannot exceed input in the same unit.');
    if (update.wasteUnit === update.inputUnit && update.wasteQuantity !== null) assert(update.outputQuantity + update.wasteQuantity <= update.inputQuantity + 1e-6, 'Output plus waste exceeds input.');
  }
  let activityHistory = event(card, user, `${stage.name}: ${PRODUCTION_STATUS_LABELS[update.status]}`, `Input ${fmtQuantity(update.inputQuantity, update.inputUnit)}; output ${fmtQuantity(update.outputQuantity, update.outputUnit)}; waste ${fmtQuantity(update.wasteQuantity, update.wasteUnit)}.`, now);
  const productionStages = all.map(s => s.id === id ? { ...s, ...update } : { ...s });
  if (update.status === 'Completed') {
    const next = productionStages.find(s => s.required && s.kind === 'production' && s.sequence > stage.sequence);
    if (next) {
      assert(next.status === 'Pending' && next.inputQuantity === null && !next.handover, 'The next stage already has recorded input; handover would overwrite it.');
      next.handover = { quantity: update.outputQuantity!, unit: update.outputUnit, fromStageId: stage.id };
      if (next.inputUnit === update.outputUnit) { next.inputQuantity = update.outputQuantity; next.status = 'Received'; }
      activityHistory = [...activityHistory, { id: crypto.randomUUID(), timestamp: now, user: user.name, department: next.department, action: 'Stage handover', description: `${stage.name} sent ${fmtQuantity(update.outputQuantity, update.outputUnit)} to ${next.name}.${next.inputUnit !== update.outputUnit ? ' Different input unit: enter the received quantity explicitly; no conversion is assumed.' : ''}` }];
    }
  }
  const required = productionStages.filter(s => s.required && s.kind === 'production');
  const ready = required.length > 0 && required.every(s => s.status === 'Completed');
  const status = ready ? 'ReadyForStock' : required.some(s => s.status === 'OnHold') ? 'OnHold' : required.some(s => ['InProgress', 'Completed'].includes(s.status)) ? 'InProduction' : 'MaterialIssued';
  const updated = { ...card, productionStages, status, activityHistory } as JobCard;
  return { ...updated, department: currentLocation(updated).department, stages: card.stages.map(legacy => {
    const tracked = productionStages.find(s => s.legacyStage === legacy.stage);
    return tracked ? { ...legacy, required: tracked.required, status: tracked.status === 'Completed' ? 'Complete' : ['InProgress', 'OnHold'].includes(tracked.status) ? 'InProgress' : 'Pending' } : legacy;
  }) };
}
export interface StockReceiptOptions { id: string; batch: string; rejected: number; qcVerified: boolean }
export function transferJobToStock(card: JobCard, acceptedQuantity: number, batchDate: string, user: User, now = new Date().toISOString(), receipt?: StockReceiptOptions): JobCard {
  requireRole(user, ['store_keeper', 'admin']);
  if (receipt && card.stockTransfers?.some(r => r.id === receipt.id)) return card;
  assert(card.approval, 'Production Manager approval is required.');
  assert(card.status === 'ReadyForStock' && (!card.stockTransfer || !!receipt), 'Only ready jobs can be transferred once.');
  const totals = productionTotals(card);
  const previouslyAccepted = card.acceptedQuantity ?? 0, previouslyRejected = card.rejectedQuantity ?? 0;
  const rejected = receipt?.rejected ?? Math.max(0, (totals.produced ?? 0) - acceptedQuantity);
  if (receipt) assert(receipt.id && receipt.batch.trim() && receipt.qcVerified, 'Record a batch and confirm QC verification.');
  assert(validQuantity(rejected) && previouslyAccepted + previouslyRejected + acceptedQuantity + rejected <= (totals.produced ?? 0), 'Accepted and rejected batches exceed produced quantity.');
  const complete = Math.abs(previouslyAccepted + previouslyRejected + acceptedQuantity + rejected - (totals.produced ?? 0)) < 1e-6;
  assert(productionStages(card).every(s => s.status === 'Completed'), 'Complete all required production stages.');
  assert(validQuantity(acceptedQuantity) && (acceptedQuantity > 0 || (!!receipt && rejected > 0)) && totals.produced !== null && acceptedQuantity <= totals.produced && totals.unit, 'Confirm positive accepted or rejected quantity; accepted quantity cannot exceed final output.');
  assert(/^\d{4}-\d{2}-\d{2}$/.test(batchDate) && Number.isFinite(Date.parse(batchDate)) && batchDate <= new Date(now).toLocaleDateString('en-CA') && (!card.createdDate || batchDate >= card.createdDate.slice(0, 10)), 'Choose a valid batch date between creation and today.');
  return { ...card, status: complete ? 'Completed' : 'ReadyForStock', department: 'Stock Keeping', acceptedQuantity: previouslyAccepted + acceptedQuantity, rejectedQuantity: previouslyRejected + rejected,
    stockTransfers: [...(card.stockTransfers ?? []), { id: receipt?.id ?? `receipt-${card.id}`, batch: receipt?.batch ?? `LOT-${card.jobCardNumber}`, quantity: acceptedQuantity, rejectedQuantity: rejected, date: batchDate }],
    stages: card.stages.map(stage => card.productionStages?.some(s => s.required && s.kind === 'stock' && s.legacyStage === stage.stage) ? { ...stage, status: 'Complete' } : stage),
    stockTransfer: { quantity: acceptedQuantity, unit: totals.unit, batchDate, confirmedBy: user.name, confirmedAt: now, jobCardId: card.id, salesOrderId: card.salesOrderId, customerName: card.customerName ?? '', modelName: card.modelName, product: card.product ?? card.modelName },
    productionStages: orderedStages(card).map(s => s.required && s.kind === 'stock' ? { ...s, status: 'Completed', inputQuantity: acceptedQuantity, outputQuantity: acceptedQuantity, wasteQuantity: 0, inputUnit: totals.unit, outputUnit: totals.unit, wasteUnit: totals.unit, operator: user.name, startedAt: now, completedAt: now } : s),
    activityHistory: event(card, user, 'Finished quantity confirmed', `${fmtQuantity(acceptedQuantity, totals.unit)} confirmed for Stock Keeping. Verified transfer reference prepared; shared inventory posting is performed by JobCardsContext.`, now) };
}
export function editJobCard(card: JobCard, change: Pick<JobCard, 'modelName' | 'product' | 'specifications' | 'qty' | 'unit' | 'requiredDate' | 'productionRequirements'>, user: User, now = new Date().toISOString()): JobCard {
  requireRole(user, ['production_manager', 'admin']);
  assert(['Draft', 'PendingApproval'].includes(card.status), 'Job fields are locked after approval.');
  assert(change.modelName.trim() && change.product?.trim() && Number.isFinite(change.qty) && change.qty > 0 && change.unit?.trim(), 'Model, product, positive order quantity and unit are required.');
  assert(!!change.requiredDate && /^\d{4}-\d{2}-\d{2}$/.test(change.requiredDate) && Number.isFinite(Date.parse(change.requiredDate)) && (!card.createdDate || change.requiredDate >= card.createdDate.slice(0, 10)), 'Required date must be valid and on or after creation.');
  return { ...card, ...change, activityHistory: event(card, user, 'Job card edited', 'Production Manager updated job specifications and requirements.', now) };
}
export function toggleJobStage(card: JobCard, id: string, user: User, now = new Date().toISOString()): JobCard {
  requireRole(user, ['receptionist', 'production_manager', 'admin']);
  assert(!card.approval && ['Draft', 'PendingApproval'].includes(card.status), 'Approved routing is locked; request an authorized revision before changing stages.');
  const stage = card.productionStages?.find(s => s.id === id);
  assert(stage && stage.status === 'Pending', 'Only pending stages can be added or removed.');
  if (stage.required && stage.kind === 'production') assert(productionStages(card).length > 1, 'Keep at least one required production stage.');
  if (!stage.required && stage.kind === 'production') assert(!productionStages(card).some(s => s.sequence > stage.sequence && s.status !== 'Pending'), 'Cannot insert a stage before production that has already been received or started.');
  const updated: JobCard = { ...card, productionStages: card.productionStages!.map(s => s.id === id ? { ...s, required: !s.required } : s),
    stages: card.stages.map(s => s.stage === stage.legacyStage ? { ...s, required: !stage.required } : s),
    activityHistory: event(card, user, 'Stage requirement changed', `${stage.name} ${stage.required ? 'removed from' : 'added to'} required production.`, now) };
  if (['MaterialIssued', 'Issued', 'InProduction', 'OnHold', 'ReadyForStock'].includes(card.status)) {
    const required = productionStages(updated);
    if (required.length && required.every(s => s.status === 'Completed')) updated.status = 'ReadyForStock';
    else if (card.status === 'ReadyForStock') updated.status = 'InProduction';
  }
  return { ...updated, department: currentLocation(updated).department };
}
