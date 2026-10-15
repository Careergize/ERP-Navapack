import type { JobCard, JobCardMaterial, JobProductionStage, SalesOrder } from '../types';
import { RAW_MATERIALS } from './rawMaterialData';
import { normalizeJobCard } from './jobCards';

// Illustrative job-specific requirements, not calculated model/BOM consumption.
export function withJobCardDemo(card: JobCard, orders: SalesOrder[]): JobCard {
  const order = orders.find(o => o.id === card.salesOrderId)!;
  const completed = card.status === 'Completed';
  const producing = card.status === 'InProduction';
  const approved = producing || completed || card.status === 'Approved';
  const createdDate = `${order.date}T09:00:00+05:30`;
  const resin = RAW_MATERIALS.find(m => m.family === (card.id === 'jc-3' ? 'LDPE' : 'HDPE'))!;
  const ink = RAW_MATERIALS.find(m => m.category === 'ink')!;
  const requiredMaterials: JobCardMaterial[] = (card.id === 'jc-2' ? [ink] : [resin, ink]).map((material, i) => ({
    id: `${card.id}-material-${i}`, materialId: material.id, name: material.name, unit: material.unit,
    requiredQuantity: material.category === 'ink' ? 15 : 500, issuedQuantity: producing || completed ? material.category === 'ink' ? 15 : 500 : 0,
  }));
  const productionStages: JobProductionStage[] = card.stages.map(stage => {
    const kind = ['Stock', 'Ready to Sale'].includes(stage.stage) ? 'stock' : 'production';
    const status = stage.status === 'Complete' ? 'Completed' : stage.status === 'InProgress' ? 'InProgress' : 'Pending';
    const done = status === 'Completed';
    const first = stage.sequenceOrder === 1;
    const kgInput = card.id !== 'jc-2' && stage.stage !== 'Stock' && stage.stage !== 'Ready to Sale';
    const inputUnit = kgInput ? 'kg' : 'pcs';
    const outputUnit = stage.stage === 'Packaging' || kind === 'stock' || card.id === 'jc-2' ? 'pcs' : 'kg';
    const inputQuantity = done || status === 'InProgress' ? kind === 'stock' ? card.qty : first ? 500 : 480 : null;
    const outputQuantity = done ? outputUnit === 'pcs' ? card.qty : 480 : null;
    return { id: `${card.id}-${stage.stage}`, legacyStage: stage.stage, name: stage.stage, department: kind === 'stock' ? 'Stock Keeping' : stage.stage,
      sequence: stage.sequenceOrder, required: stage.required, kind, status, inputQuantity, outputQuantity,
      wasteQuantity: done ? first && kgInput ? 20 : 0 : null, inputUnit, outputUnit, wasteUnit: inputUnit,
      startedAt: done || status === 'InProgress' ? `${order.date}T10:00:00+05:30` : undefined,
      completedAt: done ? `${order.date}T14:00:00+05:30` : undefined,
      operator: done || status === 'InProgress' ? 'Demo production operator' : '', remarks: 'Illustrative frontend stage record.',
      wasteType: first ? 'Process trim' : 'Process waste', wasteReason: first ? 'Trimming during production' : '', sentToRecycling: 0,
    };
  });
  return normalizeJobCard({ ...card, status: card.status === 'Approved' ? 'StoreIssuePending' : card.status,
    salesOrderNumber: order.orderNumber, customerName: order.customerName, product: card.modelName, unit: 'pcs', createdDate,
    requiredDate: card.id === 'jc-2' ? '2026-10-15' : card.id === 'jc-3' ? '2026-10-16' : '2026-09-30',
    specifications: `${card.modelName}; customer configuration to be confirmed.`, productionRequirements: 'Follow selected model stages. Material quantities are illustrative frontend requirements, not automatic model calculations.',
    approval: approved ? { approvedBy: 'Kwame (Production Manager)', approvedAt: `${order.date}T09:30:00+05:30` } : undefined,
    requiredMaterials, productionStages, acceptedQuantity: completed ? card.qty : undefined,
    stockTransfer: completed ? { quantity: card.qty, unit: 'pcs', batchDate: order.date, confirmedBy: 'Zola (Store Keeper)', confirmedAt: `${order.date}T15:00:00+05:30`, jobCardId: card.id, salesOrderId: card.salesOrderId, customerName: order.customerName, modelName: card.modelName, product: card.modelName } : undefined,
    activityHistory: [
      { id: `${card.id}-created`, timestamp: createdDate, action: 'Created', user: 'Amara (Receptionist)', department: 'Reception', description: `${card.jobCardNumber} created from ${order.orderNumber}.` },
      { id: `${card.id}-forwarded`, timestamp: `${order.date}T09:05:00+05:30`, action: 'Forwarded for approval', user: 'Amara (Receptionist)', department: 'Production Manager', description: 'Job card forwarded to Production Manager.' },
      ...(approved ? [{ id: `${card.id}-approved`, timestamp: `${order.date}T09:30:00+05:30`, action: 'Approved', user: 'Kwame (Production Manager)', department: 'Production Manager', description: 'Approved and forwarded for Store Issue.' }] : []),
      ...(producing || completed ? [{ id: `${card.id}-issued`, timestamp: `${order.date}T09:45:00+05:30`, action: 'Materials issued', user: 'Zola (Store Keeper)', department: 'Store', description: 'Illustrative full material issue; no inventory transaction.' }] : []),
      ...productionStages.filter(s => s.required && s.startedAt).map(s => ({ id: `${s.id}-activity`, timestamp: s.completedAt ?? s.startedAt!, action: s.status === 'Completed' ? 'Stage completed' : 'Stage started', user: s.operator, department: s.department, description: `${s.name}: ${s.outputQuantity == null ? 'In progress' : `output ${s.outputQuantity} ${s.outputUnit}, waste ${s.wasteQuantity} ${s.wasteUnit}`}.` })),
      ...(completed ? [{ id: `${card.id}-stock`, timestamp: `${order.date}T15:00:00+05:30`, action: 'Completed', user: 'Zola (Store Keeper)', department: 'Stock Keeping', description: 'Finished quantity confirmed; illustrative frontend transfer only.' }] : []),
    ],
  }, orders);
}
