import type { JobCard, Role } from '../types';
import type { RawMaterialMovement } from './rawMaterialData';
import type { FinishedGoodsMovement } from './finishedGoodsData';
import { qualityReleased, subjectHeld, type QCState, type QCRelease } from './quality';

export function rawQualityStatus(state: QCState, receiptId: string) {
  const records = state.inspections.filter(i => i.subject.kind === 'raw' && i.subject.receiptId === receiptId);
  if (!records.length) return 'Pending QC';
  if (records.at(-1)?.status === 'Conditionally Accepted') return 'Conditionally Accepted / On Hold';
  if (subjectHeld(state, records[0].subject)) return records.some(i => i.status === 'Failed') ? 'Rejected / On Hold' : 'Pending QC / On Hold';
  return records.some(i => qualityReleased(state, i)) ? 'Accepted / Released' : 'Pending QC';
}
export function rawHeldQuantity(state: QCState, movements: RawMaterialMovement[], materialId: string) {
  return movements.filter(m => m.materialId === materialId && m.movementType === 'IN' && rawQualityStatus(state, m.id) !== 'Accepted / Released').reduce((sum, m) => sum + m.quantity, 0);
}
export function assertProductionQC(state: QCState, card: JobCard, beforeSequence = Infinity) {
  const records = state.inspections.filter(i => i.subject.manufacturingItemId === card.id);
  if (records.some(i => subjectHeld(state, i.subject))) throw new Error('This manufacturing item has an unresolved QC hold. Unrelated items remain available.');
  const stages = card.routingApproved?.stages ?? card.productionStages ?? [];
  for (const stage of stages.filter(s => s.required && s.kind === 'production' && s.sequence < beforeSequence)) {
    for (const templateId of stage.qcTemplateIds ?? []) {
      const actual = card.productionStages?.find(s => s.id === stage.id);
      const batches = new Map<string, number>();
      records.filter(i => i.template.id === templateId && i.subject.stageId === stage.id && i.subject.unit === actual?.outputUnit && qualityReleased(state, i) && !subjectHeld(state, i.subject)).forEach(i => batches.set(i.subject.batchId!, i.subject.quantity ?? 0));
      if (!actual || actual.status !== 'Completed' || !batches.size || [...batches.values()].reduce((a, b) => a + b, 0) < (actual.outputQuantity ?? Infinity)) throw new Error(`Mandatory QC for ${stage.name} must cover its recorded output before advancement/release.`);
    }
  }
}
export function finishedAuthorization(state: QCState, card: JobCard, batch: string, accepted: number, rejected: number): QCRelease {
  assertProductionQC(state, card);
  const last = [...(card.productionStages ?? [])].filter(s => s.required && s.kind === 'production').sort((a, b) => a.sequence - b.sequence).at(-1);
  const release = state.releases.find(r => r.purpose === 'finished_stock' && r.subject.manufacturingItemId === card.id && r.subject.stageId === last?.id && r.subject.batchNumber === batch);
  if (!release || subjectHeld(state, release.subject) || release.unit !== last?.outputUnit) throw new Error('This exact finished batch needs QC release and separate Production Manager/Admin stock authorization.');
  const posted = (card.stockTransfers ?? []).filter(r => r.batch === batch);
  if (posted.reduce((sum, r) => sum + r.quantity, 0) + accepted > (release.acceptedQuantity ?? 0) || posted.reduce((sum, r) => sum + r.rejectedQuantity, 0) + rejected > (release.rejectedQuantity ?? 0)) throw new Error('Stock receipt exceeds the authorized accepted/rejected quantities for this batch.');
  return release;
}

export function assertMachineQC(state: QCState, machineId?: string) {
  if (!machineId) return;
  const records = state.inspections.filter(i => i.subject.kind === 'machine' && i.subject.machineId === machineId);
  const latest = records.at(-1);
  if (!latest || subjectHeld(state, latest.subject) || !records.some(i => qualityReleased(state, i))) throw new Error('Assigned machine requires a verified QC record and resolution of equipment warnings.');
}

export function assertFinishedReceiptQC(state: QCState, movement: FinishedGoodsMovement, movements: FinishedGoodsMovement[]) {
  const authorization = state.releases.find(r => r.id === movement.stockApprovalId && r.purpose === 'finished_stock');
  const qualityRelease = state.releases.find(r => r.id === movement.qualityReleaseId && r.purpose === 'quality');
  if (!authorization || !qualityRelease || qualityRelease.inspectionId !== authorization.inspectionId || authorization.subject.manufacturingItemId !== movement.manufacturingItemId || authorization.subject.jobCardId !== movement.jobCardId || authorization.subject.batchNumber !== movement.batch || authorization.unit !== movement.unit || subjectHeld(state, authorization.subject) || (authorization.subject.productId && authorization.subject.productId !== movement.productId)) throw new Error('Production receipt requires exact QC and final stock authorization references.');
  if (movement.date < new Date(authorization.at).toLocaleDateString('en-CA')) throw new Error('Stock receipt cannot precede final managerial authorization.');
  const received = movements.filter(m => m.stockApprovalId === authorization.id && m.type === 'IN').reduce((sum, m) => sum + m.quantity, 0);
  if (received + movement.quantity > (authorization.acceptedQuantity ?? 0)) throw new Error('Receipt exceeds this batch stock authorization.');
}

export function assertManualFinishedINQC(state: QCState, userRole: Role | undefined, productId: string) {
  if (userRole !== 'admin') throw new Error('Production Stock IN must use a QC-authorized Job Card receipt. Admin alone can record a separate legacy reference import.');
  if (state.inspections.some(i => i.subject.productId === productId && subjectHeld(state, i.subject))) throw new Error('Manual unbatched Stock IN cannot bypass this product QC hold. Use an exact authorized batch receipt.');
}
