import type { Role, User } from '../types';

export const QC_FREQUENCIES = ['per_receipt','per_batch','per_shift','daily','weekly','monthly','on_demand','per_activity'] as const;
export type QCCategory = 'raw' | 'production' | 'machine' | 'cleaning' | 'safety';
export type ResponseType = 'yes_no' | 'ok_not_ok' | 'tick_cross' | 'pass_fail' | 'numeric' | 'text';
export type QCStatus = 'Draft' | 'Submitted' | 'Passed' | 'Failed' | 'Reinspection Required' | 'Approved/Released' | 'Conditionally Accepted';
export interface QCItem { id: string; label: string; type: ResponseType; acceptable?: string; required: boolean; allowNA: boolean; remarksRequired?: boolean; measurementUnit?: string }
export interface QCTemplate { id: string; name: string; documentCode?: string; revision: number; effectiveDate: string; department: string; category: QCCategory; frequency: typeof QC_FREQUENCIES[number]; applicable: string; active: boolean; approvalRequired: boolean; items: QCItem[]; source: string }
export interface QCResponse { itemId: string; sample: number; value: string; remarks: string; target?: number; lowerTolerance?: number; upperTolerance?: number; unit?: string }
export interface QCSubject { kind: QCCategory; label: string; materialId?: string; receiptId?: string; supplierId?: string; supplierName?: string; jobCardId?: string; manufacturingItemId?: string; productId?: string; modelId?: string; modelName?: string; modelRevision?: number; stageId?: string; isFinishedOutput?: boolean; batchId?: string; batchNumber?: string; machineId?: string; machineType?: string; areaId?: string; quantity?: number; unit?: string }
export interface QCEvent { id: string; type: string; at: string; userId: string; user: string; description: string }
export interface QCApproval { id: string; decision: 'Passed' | 'Failed' | 'Reinspection Required' | 'Conditionally Accepted'; userId: string; user: string; at: string; remarks: string }
export interface QCInspection { scheduleKey?: string; id: string; number: string; template: QCTemplate; subject: QCSubject; date: string; time: string; department: string; inspectorId: string; inspector: string; assignedTo: string; sampleCount: number; responses: QCResponse[]; metadata: Record<string, string>; comments: string; status: QCStatus; result?: 'Pass' | 'Fail'; previousInspectionId?: string; approvals: QCApproval[]; events: QCEvent[] }
export interface QCRelease { id: string; requestId: string; inspectionId: string; subject: QCSubject; purpose: 'quality' | 'finished_stock'; acceptedQuantity?: number; rejectedQuantity?: number; unit?: string; userId: string; user: string; at: string }
export interface QCNonConformance { id: string; number: string; inspectionId: string; description: string; severity: 'Minor' | 'Major' | 'Critical'; quantityAffected?: number; unit?: string; department: string; assignedTo: string; immediateAction: string; correctiveAction: string; dueDate: string; verification: string; status: 'Open' | 'Assigned' | 'In Progress' | 'Awaiting Verification' | 'Closed'; events: QCEvent[] }
export interface QCState { inspections: QCInspection[]; releases: QCRelease[]; nonConformances: QCNonConformance[] }
export const QC_VIEW_ROLES: Role[] = ['qc_inspector', 'qc_supervisor', 'production_manager', 'store_keeper', 'admin'];
export const QC_REVIEW_ROLES: Role[] = ['qc_supervisor', 'admin'];
export const canRecordQC = (role?: Role) => !!role && ['qc_inspector', 'qc_supervisor', 'admin'].includes(role);
export const canViewQC = (role?: Role) => !!role && QC_VIEW_ROLES.includes(role);
export const isQCRole = (role?: Role) => role === 'qc_inspector' || role === 'qc_supervisor';
export const optionsFor = (type: ResponseType): string[] => ({ yes_no: ['Yes', 'No'], ok_not_ok: ['OK', 'Not OK'], tick_cross: ['Tick', 'Cross'], pass_fail: ['Pass', 'Fail'], numeric: [], text: [] })[type];
function ensure(value: unknown, message: string): asserts value { if (!value) throw new Error(message); }
const role = (user: User, roles: Role[]) => ensure(roles.includes(user.role), 'Your role cannot perform this QC action.');
const validDate = (date: string) => /^\d{4}-\d{2}-\d{2}$/.test(date) && Number.isFinite(Date.parse(date)) && new Date(`${date}T00:00:00Z`).toISOString().slice(0, 10) === date;
const finite = (n: unknown): n is number => typeof n === 'number' && Number.isFinite(n);
const event = (user: User, type: string, description: string): QCEvent => ({ id: crypto.randomUUID(), type, description, userId: user.id, user: user.name, at: new Date().toISOString() });
export function validateTemplate(t: QCTemplate) {
  ensure(!(t.id === 'ksec' && t.active && t.items.some(i => i.label === 'Client-confirmed checklist required before activation')), 'Configure client-confirmed KSEC checks before activation; its meaning is undefined.');
  ensure(t.id && t.name.trim() && t.department.trim() && validDate(t.effectiveDate), 'Complete template identity, department and effective date.');
  ensure(QC_FREQUENCIES.includes(t.frequency), 'Choose a supported frequency.');
  ensure(t.items.length && new Set(t.items.map(i => i.id)).size === t.items.length, 'Use distinct checklist items.');
  t.items.forEach(i => { ensure(i.label.trim() && (i.type === 'text' || i.type === 'numeric' || optionsFor(i.type).includes(i.acceptable ?? '')), 'Set an acceptable answer for each choice item.'); });
}
export function responsePass(item: QCItem, response: QCResponse): boolean {
  if (response.value === 'NA') return item.allowNA && !!response.remarks.trim();
  if (item.type === 'text') return !!response.value.trim();
  if (item.type !== 'numeric') return response.value === item.acceptable;
  const actual = Number(response.value);
  return !!response.value.trim() && finite(actual) && finite(response.target) && finite(response.lowerTolerance) && finite(response.upperTolerance) && response.lowerTolerance >= 0 && response.upperTolerance >= 0 && !!response.unit?.trim() && actual >= response.target - response.lowerTolerance && actual <= response.target + response.upperTolerance;
}
export function inspectionResult(i: QCInspection): 'Pass' | 'Fail' {
  ensure(Number.isInteger(i.sampleCount) && i.sampleCount >= 1 && i.sampleCount <= (i.template.category === 'production' ? 8 : 1), 'Use one to eight production samples; other records have one response set.');
  ensure(new Set(i.responses.map(r => `${r.itemId}:${r.sample}`)).size === i.responses.length && i.responses.every(r => i.template.items.some(t => t.id === r.itemId) && Number.isInteger(r.sample) && r.sample >= 1 && r.sample <= i.sampleCount), 'Responses must reference distinct items and valid sample numbers.');
  let failed = false, applicable = 0;
  for (let sample = 1; sample <= i.sampleCount; sample++) for (const item of i.template.items) {
    const r = i.responses.find(r => r.itemId === item.id && r.sample === sample);
    if (!r?.value.trim() && !item.required) continue;
    ensure(r && r.value.trim(), `Record ${item.label}, sample ${sample}.`);
    ensure(r.value !== 'NA' || (item.allowNA && r.remarks.trim()), 'Not Applicable needs permission and a reason.');
    if (r.value !== 'NA') applicable++;
    if (item.type === 'numeric' && r.value !== 'NA') ensure(finite(Number(r.value)) && finite(r.target) && finite(r.lowerTolerance) && finite(r.upperTolerance) && r.lowerTolerance >= 0 && r.upperTolerance >= 0 && !!r.unit?.trim(), 'Record actual measurement, specification target, nonnegative tolerances and unit.');
    if (!['numeric', 'text'].includes(item.type) && r.value !== 'NA') ensure(optionsFor(item.type).includes(r.value), 'Invalid checklist answer.');
    const pass = responsePass(item, r);
    ensure(!(item.remarksRequired || !pass) || !!r.remarks.trim(), 'Record remarks for required or non-compliant findings.');
    failed ||= !pass;
  }
  ensure(applicable > 0, 'An all-Not-Applicable inspection cannot pass.');
  return failed ? 'Fail' : 'Pass';
}
export function createInspection(template: QCTemplate, subject: QCSubject, user: User, date: string, department: string, sampleCount = 1): QCInspection {
  ensure(canRecordQC(user.role), 'Only QC staff/Admin can record inspections.'); validateTemplate(template);
  ensure(template.active && subject.kind === template.category && date >= template.effectiveDate && validDate(date) && department.trim(), 'Use an active applicable template, date and department.');
  ensure(subject.label.trim(), 'Select an inspection subject.');
  if (subject.kind === 'raw') ensure(subject.receiptId && subject.materialId && finite(subject.quantity) && subject.quantity > 0 && subject.unit, 'Link an exact Raw Material IN receipt.');
  if (subject.kind === 'production') ensure(subject.jobCardId && subject.manufacturingItemId && subject.stageId && subject.batchId && subject.batchNumber && finite(subject.quantity) && subject.quantity >= 0 && subject.unit, 'Link the exact Job Card item, stage and QC lot.');
  if (subject.kind === 'machine') ensure(subject.machineId && subject.machineType === template.applicable, 'Select a machine with the matching machine type.');
  if (subject.kind === 'cleaning') ensure(subject.areaId, 'Select a configured cleaning area.');
  ensure(Number.isInteger(sampleCount) && sampleCount >= 1 && sampleCount <= (subject.kind === 'production' ? 8 : 1), 'Invalid sample count.');
  const id = crypto.randomUUID();
  return { id, number: `QC-${id.slice(0, 8)}`, template: structuredClone(template), subject: structuredClone(subject), date, time: '', department, inspectorId: user.id, inspector: user.name, assignedTo: user.id, sampleCount, responses: [], metadata: {}, comments: '', status: 'Draft', approvals: [], events: [event(user, 'Created', 'Inspection created with an exact template revision snapshot.')] };
}
export function saveInspection(i: QCInspection, draft: Pick<QCInspection, 'time' | 'responses' | 'metadata' | 'comments'>, user: User): QCInspection {
  ensure(canRecordQC(user.role) && (user.id === i.assignedTo || user.role === 'admin') && i.status === 'Draft', 'Only assigned QC staff/Admin can edit a draft. Submitted records are immutable.');
  return { ...i, ...structuredClone(draft), events: [...i.events, event(user, 'Draft saved', 'Measurements and findings saved in frontend state.')] };
}
export function submitInspection(i: QCInspection, user: User): QCInspection {
  ensure(canRecordQC(user.role) && (i.assignedTo === user.id || user.role === 'admin') && i.status === 'Draft', 'Only assigned QC staff/Admin can submit a draft.');
  ensure(i.date <= new Date().toLocaleDateString('en-CA'), 'A scheduled future inspection cannot be submitted as completed.');
  ensure(/^([01]\d|2[0-3]):[0-5]\d$/.test(i.time), 'Record inspection time.');
  if (i.subject.kind === 'cleaning') ensure(['cleaningMethod', 'chemicals', 'cleanedBy'].every(k => i.metadata[k]?.trim()), 'Record cleaning method, chemicals/instruments and cleaned by.');
  if (i.subject.kind === 'raw') ensure(i.subject.batchNumber?.trim() && ['sampledQuantity', 'coa', 'tds', 'msds'].every(k => i.metadata[k]?.trim()) && Number.isFinite(Number(i.metadata.sampledQuantity)) && Number(i.metadata.sampledQuantity) > 0 && Number(i.metadata.sampledQuantity) <= i.subject.quantity!, 'Record supplier batch, document availability and valid sampled quantity in receipt units.');
  return { ...i, inspectorId: user.id, inspector: user.name, result: inspectionResult(i), status: 'Submitted', events: [...i.events, event(user, 'Submitted', 'Submitted; no stock or release authorization created.')] };
}
export function reviewInspection(i: QCInspection, decision: QCApproval['decision'], remarks: string, user: User): QCInspection {
  role(user, QC_REVIEW_ROLES); ensure(i.status === 'Submitted' && remarks.trim(), 'Review a submitted inspection with remarks.');
  ensure(user.id !== i.inspectorId, 'A different authorized reviewer must verify the inspection.');
  ensure(decision !== 'Conditionally Accepted' || i.subject.kind === 'raw', 'Conditional acceptance applies to raw receipts only and remains held.');
  const result = inspectionResult(i); ensure(decision !== 'Passed' || result === 'Pass', 'Failed checks cannot be approved. Record corrective action and reinspection.');
  const approval: QCApproval = { id: crypto.randomUUID(), decision, remarks, userId: user.id, user: user.name, at: new Date().toISOString() };
  return { ...i, result, status: decision, approvals: [...i.approvals, approval], events: [...i.events, event(user, decision, remarks)] };
}
export function subjectKey(s: QCSubject) { return s.kind === 'raw' ? `raw:${s.receiptId}` : s.kind === 'production' ? `production:${s.manufacturingItemId}:${s.batchId}:${s.stageId}` : s.kind === 'machine' ? `machine:${s.machineId}` : s.kind === 'cleaning' ? `cleaning:${s.areaId}` : `safety:${s.label}`; }
export function qualityReleased(state: QCState, i: QCInspection) { return state.releases.some(r => r.inspectionId === i.id && r.purpose === 'quality'); }
export function subjectHeld(state: QCState, subject: QCSubject): boolean {
  const records = state.inspections.filter(i => subjectKey(i.subject) === subjectKey(subject));
  // Every unresolved record keeps the subject held; unrelated items/batches are untouched.
  const resolved = (i: QCInspection, visited = new Set<string>()): boolean => { if (visited.has(i.id)) return false; visited.add(i.id); return qualityReleased(state, i) || records.some(n => n.previousInspectionId === i.id && resolved(n, new Set(visited))); };
  return records.some(i => !resolved(i)) || state.nonConformances.some(n => n.status !== 'Closed' && records.some(i => i.id === n.inspectionId));
}
export function releaseInspection(state: QCState, id: string, purpose: QCRelease['purpose'], requestId: string, user: User, accepted?: number, rejected?: number): QCState {
  role(user, purpose === 'quality' ? QC_REVIEW_ROLES : ['production_manager', 'admin']);
  const existing = state.releases.find(r => r.requestId === requestId);
  if (existing) { ensure(existing.inspectionId === id && existing.purpose === purpose && existing.acceptedQuantity === accepted && existing.rejectedQuantity === rejected, 'Idempotency key conflicts with another release.'); return state; }
  const i = state.inspections.find(i => i.id === id); ensure(i && requestId, 'Inspection and release request ID are required.');
  ensure(i.status === 'Passed' || i.status === 'Approved/Released', 'Only an independently reviewed passing inspection can be released.');
  ensure(!state.nonConformances.some(n => n.status !== 'Closed' && state.inspections.some(source => source.id === n.inspectionId && subjectKey(source.subject) === subjectKey(i.subject))), 'Verify and close related non-conformances first.');
  ensure(!state.releases.some(r => r.inspectionId === id && r.purpose === purpose), 'This action already has a release reference.');
  if (purpose === 'finished_stock') {
    ensure(!state.releases.some(r => r.purpose === 'finished_stock' && subjectKey(r.subject) === subjectKey(i.subject)), 'This exact physical QC lot already has final stock authorization.');
    ensure(i.subject.kind === 'production' && i.subject.isFinishedOutput === true && qualityReleased(state, i) && !subjectHeld(state, i.subject), 'Quality release is required before final stock authorization.');
    ensure(finite(accepted) && accepted >= 0 && finite(rejected) && rejected >= 0 && accepted + rejected > 0 && accepted + rejected <= i.subject.quantity!, 'Accepted/rejected quantities must fit inspected output in its explicit unit.');
  }
  const release: QCRelease = { id: crypto.randomUUID(), requestId, inspectionId: id, subject: structuredClone(i.subject), purpose, acceptedQuantity: accepted, rejectedQuantity: rejected, unit: i.subject.unit, userId: user.id, user: user.name, at: new Date().toISOString() };
  return { ...state, releases: [...state.releases, release], inspections: state.inspections.map(row => row.id === id ? { ...row, status: 'Approved/Released', events: [...row.events, event(user, purpose === 'quality' ? 'Quality released' : 'Stock authorization', `Release ${release.id}; no inventory posting.`)] } : row) };
}
export function reinspect(i: QCInspection, user: User): QCInspection {
  ensure(canRecordQC(user.role) && ['Failed', 'Reinspection Required', 'Conditionally Accepted'].includes(i.status), 'Create reinspection from a failed/reinspection record.');
  const next = createInspection(i.template, i.subject, user, new Date().toLocaleDateString('en-CA'), i.department, i.sampleCount);
  return { ...next, previousInspectionId: i.id, metadata: structuredClone(i.metadata) };
}
export function createNonConformance(i: QCInspection, description: string, severity: QCNonConformance['severity'], user: User): QCNonConformance {
  ensure(canRecordQC(user.role) && description.trim() && i.status !== 'Draft', 'Record a finding against a submitted inspection.');
  const id = crypto.randomUUID(); return { id, number: `NC-${id.slice(0, 8)}`, inspectionId: i.id, description, severity, department: i.department, assignedTo: '', immediateAction: '', correctiveAction: '', dueDate: '', verification: '', status: 'Open', events: [event(user, 'Reported', description)] };
}
export function updateNonConformance(n: QCNonConformance, change: Pick<QCNonConformance, 'assignedTo' | 'immediateAction' | 'correctiveAction' | 'dueDate' | 'verification' | 'status'>, user: User): QCNonConformance {
  role(user, QC_REVIEW_ROLES); ensure(n.status !== 'Closed', 'Closed findings are immutable.');
  const allowed: Record<QCNonConformance['status'], QCNonConformance['status'][]> = { Open: ['Assigned'], Assigned: ['In Progress'], 'In Progress': ['Awaiting Verification'], 'Awaiting Verification': ['Closed', 'In Progress'], Closed: [] };
  ensure(change.status === n.status || allowed[n.status].includes(change.status), 'Follow assignment, correction and verification before closure.');
  ensure(change.assignedTo.trim() && change.dueDate && Number.isFinite(Date.parse(change.dueDate)), 'Set assignment and due date.');
  if (['Awaiting Verification', 'Closed'].includes(change.status)) ensure(change.correctiveAction.trim(), 'Record corrective action.');
  if (change.status === 'Closed') ensure(change.verification.trim() && user.id !== change.assignedTo, 'Closure needs an independent verification outcome.');
  return { ...n, ...change, events: [...n.events, event(user, change.status, change.verification || change.correctiveAction || change.immediateAction || 'Assignment updated.')] };
}

export function inspectionStatusLabel(i: QCInspection) {
  if (i.subject.kind === 'cleaning') return ({ Draft: 'Scheduled Cleaning', Submitted: 'Completed / Pending Verification', Passed: 'Review Passed / Pending Verification Release', Failed: 'Recleaning Required', 'Reinspection Required': 'Recleaning Required', 'Approved/Released': 'Verified', 'Conditionally Accepted': 'On Hold' })[i.status];
  if (i.subject.kind === 'raw') return ({ Draft: 'Pending Inspection', Submitted: 'Inspection In Progress / Awaiting Review', Passed: 'Passed / Awaiting Acceptance Release', Failed: 'Rejected / On Hold', 'Reinspection Required': 'Reinspection Required', 'Approved/Released': 'Accepted / Released', 'Conditionally Accepted': 'Conditionally Accepted / On Hold' })[i.status];
  return i.status;
}
