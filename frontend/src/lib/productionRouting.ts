import type { JobCard, JobProductionStage, JobCardMaterial, User } from '../types';
import { orderedStages } from './jobCards';
export function validateRouting(stages: JobProductionStage[]) {
  if (!stages.some(s => s.required && s.kind === 'production') || new Set(stages.map(s => s.id)).size !== stages.length || new Set(stages.map(s => s.sequence)).size !== stages.length) throw new Error('Keep mandatory production stages with unique IDs and sequences.');
  if (stages.some(s => !s.name.trim() || !s.department.trim() || !s.inputUnit.trim() || !s.outputUnit.trim() || !s.wasteUnit.trim() || !Number.isInteger(s.sequence) || s.sequence < 1 || [s.expectedInput, s.expectedOutput, s.plannedWastePercent].some(n => n !== undefined && (!Number.isFinite(n) || n < 0)) || (s.plannedWastePercent ?? 0) > 100)) throw new Error('Complete stage names, departments, units and valid planned quantities/waste.');
}
export function changeRouting(card: JobCard, stages: JobProductionStage[], materials: JobCardMaterial[], user: User): JobCard {
  if (!['admin', 'production_manager'].includes(user.role)) throw new Error('Only Production Manager/Admin can edit routing.');
  if (card.approval || !['Draft', 'PendingApproval'].includes(card.status) || orderedStages(card).some(s => s.status !== 'Pending')) throw new Error('Approved or started routing is locked. Use authorized revision/reapproval before production.');
  validateRouting(stages);
  if (!materials.length || materials.some(m => !m.materialId || !m.unit.trim() || !Number.isFinite(m.requiredQuantity) || m.requiredQuantity <= 0 || m.issuedQuantity !== 0) || new Set(materials.map(m => m.materialId)).size !== materials.length) throw new Error('Complete distinct unissued material requirements.');
  const nextStages = stages.map((s, i) => ({ ...s, sequence: i + 1, status: 'Pending' as const, inputQuantity: null, outputQuantity: null, wasteQuantity: null, operator: '', remarks: '', startedAt: undefined, completedAt: undefined, handover: undefined }));
  return { ...card, status: 'Draft', routingRevision: (card.routingRevision ?? 1) + 1, productionStages: nextStages, requiredMaterials: structuredClone(materials), requirementsReviewRequired: true, activityHistory: [...(card.activityHistory ?? []), { id: crypto.randomUUID(), timestamp: new Date().toISOString(), action: 'Routing revised', user: user.name, department: 'Production Manager', description: 'Proposed route/materials changed; linked costing requires recalculation/review.' }] };
}
export function reopenRouting(card: JobCard, user: User): JobCard {
  if (!['admin', 'production_manager'].includes(user.role)) throw new Error('Your role cannot request routing revision.');
  if (!card.approval || card.stockTransfers?.length || (card.requiredMaterials ?? []).some(m => m.issuedQuantity > 0) || orderedStages(card).some(s => s.status !== 'Pending')) throw new Error('Reapproval is available only before material issue or production. Recorded history cannot be discarded.');
  return { ...card, approval: undefined, status: 'Draft', routingApprovalHistory: [...(card.routingApprovalHistory ?? []), ...(card.routingApproved ? [structuredClone(card.routingApproved)] : [])], routingApproved: undefined, requirementsReviewRequired: true, activityHistory: [...(card.activityHistory ?? []), { id: crypto.randomUUID(), timestamp: new Date().toISOString(), action: 'Routing revision requested', user: user.name, department: 'Production Manager', description: 'Previous approval retained in activity history; a new routing approval is required.' }] };
}
