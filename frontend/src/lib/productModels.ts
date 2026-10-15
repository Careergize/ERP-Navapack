import type { Model } from '../types';
import { RAW_MATERIALS } from './rawMaterialData';
export function reviseProductModel(model: Model, versions: Model[]): Model {
  if (!model.id || !model.name.trim() || !model.defaultUnit?.trim()) throw new Error('Model ID, name and default quantity unit are required.');
  if ((model.recipe ?? []).some(m => !RAW_MATERIALS.some(raw => raw.id === m.materialId && raw.unit === m.unit))) throw new Error('Recipe must reference selected raw material IDs and units.');
  for (const n of [model.wastePercent, model.overheads, model.batchQuantity, model.costingConfig?.markupPercent, model.costingConfig?.taxPercent]) if (n !== undefined && (!Number.isFinite(n) || n < 0)) throw new Error('Model defaults must be finite and nonnegative.');
  if ((model.wastePercent ?? 0) > 100 || (model.costingConfig?.taxPercent ?? 0) > 100) throw new Error('Model waste/tax percentages cannot exceed 100.');
  const revision = Math.max(0, ...versions.filter(m => m.id === model.id).map(m => m.revision ?? 1)) + 1;
  return structuredClone({ ...model, revision });
}
