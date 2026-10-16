import { useEffect, useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuality } from '@/context/QualityContext';
import { useInventory } from '@/context/InventoryContext';
import { useJobCards } from '@/context/JobCardsContext';
import { useModels } from '@/context/ModelsContext';
import { useAuth } from '@/context/AuthContext';
import { workItems } from '@/lib/parentJobCards';
import { canRecordQC, type QCCategory, type QCSubject } from '@/lib/quality';
import { today } from '@/lib/salesOrders';
import { ENTRY_INPUT } from '@/components/ui/SearchSelect';
import { QC_BUTTON } from './InspectionForm';

export function NewInspection({ category }: { category: QCCategory }) {
  const quality = useQuality(); const { rawMovements } = useInventory(); const { cards, load, registerBatch } = useJobCards(); const { machines } = useModels(); const { user } = useAuth(); const navigate = useNavigate();
  const templates = quality.templates.filter(t => t.category === category && t.active && !quality.templates.some(n => n.id === t.id && n.revision > t.revision));
  const [templateId, setTemplateId] = useState(templates[0]?.id ?? ''), [source, setSource] = useState(''), [stageId, setStageId] = useState(''), [error, setError] = useState('');
  useEffect(() => { void load(); }, [load]);
  const items = cards.flatMap(workItems); const selectedItem = items.find(i => i.id === source); const selectedStage = selectedItem?.productionStages?.find(s => s.id === stageId);
  const submit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault(); const f = new FormData(e.currentTarget);
    try {
      const template = templates.find(t => t.id === templateId); if (!template) throw new Error('Select an active template.');
      let subject: QCSubject = { kind: category, label: String(f.get('area') ?? '') };
      if (category === 'raw') { const r = rawMovements.find(m => m.id === source && m.movementType === 'IN'); if (!r) throw new Error('Select an exact inward receipt.'); subject = { kind: category, label: r.materialName, receiptId: r.id, materialId: r.materialId, batchNumber: String(f.get('batch')), quantity: r.quantity, unit: r.unit }; }
      if (category === 'production') {
        if (!selectedItem || !selectedStage || selectedStage.status !== 'Completed') throw new Error('Select a completed production checkpoint.');
        const batch = registerBatch(selectedItem.id, stageId, String(f.get('batch')), Number(f.get('lotQuantity')));
        subject = { kind: category, label: selectedItem.product ?? selectedItem.modelName, jobCardId: selectedItem.parentJobCardId ?? selectedItem.id, manufacturingItemId: selectedItem.id, productId: selectedItem.finishedProductId, modelId: selectedItem.modelId, modelName: selectedItem.modelName, modelRevision: selectedItem.modelRevision, stageId, isFinishedOutput: selectedItem.productionStages?.filter(s => s.required && s.kind === 'production').sort((a, b) => a.sequence - b.sequence).at(-1)?.id === stageId && selectedItem.productionStages?.filter(s => s.required && s.kind === 'production').every(s => s.status === 'Completed'), batchId: batch.id, batchNumber: batch.number, quantity: batch.quantity, unit: batch.unit };
      }
      if (category === 'machine') { const machine = machines.find(m => m.id === source && m.active); if (!machine) throw new Error('Admin must configure an exact machine in the shared master.'); subject = { kind: category, label: machine.name, machineId: machine.id, machineType: machine.type }; }
      if (category === 'cleaning') { const area = quality.areas.find(a => a.id === source); if (!area) throw new Error('Select a cleaning area.'); subject = { kind: category, label: area.name, areaId: area.id }; }
      const i = quality.create(template, subject, String(f.get('date')), String(f.get('department')), Number(f.get('samples') ?? 1)); navigate(`/qc/inspections/${i.id}`);
    } catch(e) { setError(e instanceof Error ? e.message : 'Unable to create inspection.'); }
  };
  if (!canRecordQC(user?.role)) return null;
  return <details className="rounded-card border bg-white p-4"><summary className="cursor-pointer font-medium text-navy">Schedule / Create inspection</summary><form onSubmit={submit} className="mt-4 space-y-3"><div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3"><label>Template<select className={ENTRY_INPUT} value={templateId} onChange={e => setTemplateId(e.target.value)}>{templates.map(t => <option key={`${t.id}-${t.revision}`} value={t.id}>{t.name} · Revision {t.revision}</option>)}</select></label><label>Inspection date<input required name="date" type="date" defaultValue={today()} className={ENTRY_INPUT} /></label><label>Department / area<input required name="department" defaultValue={templates.find(t => t.id === templateId)?.department} className={ENTRY_INPUT} /></label>
    {category !== 'safety' ? <label>Exact source<select required value={source} onChange={e => { setSource(e.target.value); setStageId(''); }} className={ENTRY_INPUT}><option value="">Select source</option>{category === 'raw' && rawMovements.filter(m => m.movementType === 'IN').map(m => <option key={m.id} value={m.id}>{m.date} · {m.materialName} · {m.reference} · {m.quantity} {m.unit} · {m.id}</option>)}{category === 'production' && items.map(i => <option key={i.id} value={i.id}>{i.jobCardNumber} · {i.product ?? i.modelName} · Item {i.id}</option>)}{category === 'machine' && machines.filter(m => m.active).map(m => <option key={m.id} value={m.id}>{m.name} · {m.type}</option>)}{category === 'cleaning' && quality.areas.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}</select></label> : <label>Inspected area<input required name="area" className={ENTRY_INPUT} /></label>}
    {['raw', 'production'].includes(category) && <label>Actual supplier / production batch number<input required name="batch" className={ENTRY_INPUT} /></label>}
    {category === 'raw' && <p className="text-xs text-gray-500">Receipt is physically received, not QC accepted. Supplier identity is unrecorded in existing inward data; no name matching is used.</p>}
    {category === 'production' && <><label>Completed production stage<select required value={stageId} onChange={e => setStageId(e.target.value)} className={ENTRY_INPUT}><option value="">Select checkpoint</option>{selectedItem?.productionStages?.filter(s => s.kind === 'production' && s.required && s.status === 'Completed').map(s => <option key={s.id} value={s.id}>{s.name} · Output {s.outputQuantity} {s.outputUnit}</option>)}</select></label><label>Quantity represented by this QC lot ({selectedStage?.outputUnit ?? 'select stage'})<input required name="lotQuantity" type="number" min="0.000001" max={selectedStage?.outputQuantity ?? undefined} step="any" className={ENTRY_INPUT} /></label><label>Number of samples<input name="samples" type="number" min="1" max="8" defaultValue="1" className={ENTRY_INPUT} /></label></>}
    </div>{error && <p role="alert" className="text-red-700">{error}</p>}<button className={QC_BUTTON}>Create Draft</button></form></details>;
}
