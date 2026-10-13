import { useQuality } from '@/context/QualityContext';
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react';
import { X } from 'lucide-react';
import { ENTRY_INPUT } from '@/components/ui/SearchSelect';
import { productionTotals, fmtQuantity, localToday, PRODUCTION_STATUS_LABELS, type StageUpdate, type StockReceiptOptions } from '@/lib/jobCards';
import type { JobCard, JobProductionStage } from '@/types';
import { JOB_BUTTON, JOB_PRIMARY } from './JobCardUI';

function JobModal({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  const dialog = useRef<HTMLDivElement>(null);
  const close = useRef(onClose); close.current = onClose;
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    dialog.current?.querySelector<HTMLElement>('button')?.focus();
    const keydown = (event: KeyboardEvent) => {
      if (event.defaultPrevented) return;
      if (event.key === 'Escape') { event.preventDefault(); close.current(); }
      if (event.key === 'Tab') {
        const elements = Array.from(dialog.current?.querySelectorAll<HTMLElement>('button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled)') ?? []);
        const first = elements[0], last = elements.at(-1);
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
      }
    };
    document.addEventListener('keydown', keydown);
    return () => { document.body.style.overflow = overflow; document.removeEventListener('keydown', keydown); previous?.focus(); };
  }, []);
  return <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/35 p-4" onMouseDown={e => { if (e.target === e.currentTarget) onClose(); }}><div ref={dialog} role="dialog" aria-modal="true" aria-labelledby="job-modal-title" className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-card bg-white shadow-xl"><div className="flex items-center justify-between border-b border-gray-200 p-5"><h2 id="job-modal-title" className="text-lg font-semibold text-navy">{title}</h2><button aria-label="Close" type="button" onClick={onClose}><X size={20} /></button></div><div className="p-5">{children}</div></div></div>;
}
const localTime = (value?: string) => {
  const date = value ? new Date(value) : new Date();
  if (Number.isNaN(date.getTime())) return '';
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
};
const isoTime = (value: string) => value ? new Date(value).toISOString() : undefined;
const errorText = (error: unknown) => error instanceof Error ? error.message : 'Unable to save job card';
const quantity = (value: string) => value === '' ? null : Number(value);

export function JobEditForm({ card, onSave, onClose }: { card: JobCard; onSave: (change: Pick<JobCard, 'modelName' | 'product' | 'specifications' | 'qty' | 'unit' | 'requiredDate' | 'productionRequirements'>) => void; onClose: () => void }) {
  const [draft, setDraft] = useState({ modelName: card.modelName, product: card.product ?? '', specifications: card.specifications ?? '', qty: String(card.qty), unit: card.unit ?? '', requiredDate: card.requiredDate ?? '', productionRequirements: card.productionRequirements ?? '' });
  const [error, setError] = useState('');
  const submit = (e: FormEvent) => { e.preventDefault(); try { onSave({ ...draft, qty: Number(draft.qty) }); onClose(); } catch (error) { setError(errorText(error)); } };
  return <JobModal title={`Edit ${card.jobCardNumber}`} onClose={onClose}><form onSubmit={submit} className="space-y-4"><div className="grid gap-4 sm:grid-cols-2">{([['modelName', 'Model'], ['product', 'Product'], ['qty', 'Order Quantity'], ['unit', 'Unit'], ['requiredDate', 'Required Date']] as const).map(([key, label]) => <label key={key} className="text-sm text-gray-600">{label}<input required type={key === 'qty' ? 'number' : key === 'requiredDate' ? 'date' : 'text'} min={key === 'qty' ? '0.000001' : key === 'requiredDate' ? card.createdDate?.slice(0, 10) : undefined} step={key === 'qty' ? 'any' : undefined} value={draft[key]} onChange={e => setDraft({ ...draft, [key]: e.target.value })} className={`${ENTRY_INPUT} mt-1`} /></label>)}</div>{([['specifications', 'Specifications'], ['productionRequirements', 'Production Requirements']] as const).map(([key, label]) => <label key={key} className="block text-sm text-gray-600">{label}<textarea value={draft[key]} onChange={e => setDraft({ ...draft, [key]: e.target.value })} className={`${ENTRY_INPUT} mt-1`} /></label>)}<p className="text-xs text-gray-500">Editing quantity or requirements does not calculate a material BOM automatically.</p>{error && <p role="alert" className="text-sm text-red-600">{error}</p>}<div className="flex justify-end gap-2"><button type="button" className={JOB_BUTTON} onClick={onClose}>Cancel</button><button className={JOB_PRIMARY}>Save Job Card</button></div></form></JobModal>;
}

export function MaterialIssueForm({ card, available, onSave, onClose }: { card: JobCard; available: Record<string, number | null>; onSave: (quantities: Record<string, number>) => void; onClose: () => void }) {
  const materials = card.requiredMaterials ?? [];
  const [values, setValues] = useState<Record<string, string>>({});
  const [error, setError] = useState('');
  const submit = (e: FormEvent) => { e.preventDefault(); try { onSave(Object.fromEntries(materials.map(m => [m.id, Number(values[m.id] || 0)]))); onClose(); } catch (error) { setError(errorText(error)); } };
  return <JobModal title={`Issue Materials — ${card.jobCardNumber}`} onClose={onClose}><form onSubmit={submit} className="space-y-4"><p className="text-xs text-gray-500">Frontend issue only. Raw Material stock is unchanged. Unrecorded availability requires Store confirmation before real posting.</p><button type="button" className={JOB_BUTTON} onClick={() => setValues(Object.fromEntries(materials.map(m => [m.id, String(Math.max(0, m.requiredQuantity - m.issuedQuantity))])))}>Full Issue — Fill Remaining</button>{materials.map(m => <div key={m.id} className="space-y-3 rounded-card border border-gray-200 p-4"><h3 className="text-sm font-medium text-navy">{m.name}</h3><dl className="grid grid-cols-2 gap-2 text-xs text-gray-500"><div><dt>Required</dt><dd>{fmtQuantity(m.requiredQuantity, m.unit)}</dd></div><div><dt>Already Issued</dt><dd>{fmtQuantity(m.issuedQuantity, m.unit)}</dd></div><div><dt>Remaining</dt><dd>{fmtQuantity(Math.max(0, m.requiredQuantity - m.issuedQuantity), m.unit)}</dd></div><div><dt>Available</dt><dd>{fmtQuantity(available[m.id], m.unit)}</dd></div></dl><label className="block text-sm text-gray-600">Issue Quantity — {m.name}<input aria-label={`Issue quantity ${m.name}`} type="number" min="0" max={Math.max(0, m.requiredQuantity - m.issuedQuantity)} step="any" value={values[m.id] ?? ''} onChange={e => setValues({ ...values, [m.id]: e.target.value })} className={`${ENTRY_INPUT} mt-1`} /></label><p className="text-xs text-gray-500">Unit: {m.unit}. Enter less than the remaining requirement for a partial issue.</p></div>)}{error && <p role="alert" className="text-sm text-red-600">{error}</p>}<div className="flex justify-end gap-2"><button type="button" className={JOB_BUTTON} onClick={onClose}>Cancel</button><button className={JOB_PRIMARY}>Record Material Issue</button></div></form></JobModal>;
}

export function StageUpdateForm({ stage, operator, onSave, onClose, lockUnits = false }: { lockUnits?: boolean; stage: JobProductionStage; operator: string; onSave: (update: StageUpdate) => void; onClose: () => void }) {
  const [draft, setDraft] = useState({ inputQuantity: stage.inputQuantity == null ? '' : String(stage.inputQuantity), outputQuantity: stage.outputQuantity == null ? '' : String(stage.outputQuantity), wasteQuantity: stage.wasteQuantity == null ? '' : String(stage.wasteQuantity), inputUnit: stage.inputUnit, outputUnit: stage.outputUnit, wasteUnit: stage.wasteUnit, operator: stage.operator || operator, startedAt: localTime(stage.startedAt), completedAt: localTime(stage.completedAt), status: stage.status, remarks: stage.remarks, wasteType: stage.wasteType ?? '', wasteReason: stage.wasteReason ?? '', sentToRecycling: String(stage.sentToRecycling ?? 0) });
  const [error, setError] = useState('');
  const received = !!stage.handover && stage.handover.unit === stage.inputUnit;
  const submit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const complete = (e.nativeEvent as SubmitEvent).submitter?.getAttribute('value') === 'complete';
    try {
      const status = complete ? 'Completed' : draft.status;
      onSave({ ...draft, status, inputQuantity: quantity(draft.inputQuantity), outputQuantity: quantity(draft.outputQuantity), wasteQuantity: quantity(draft.wasteQuantity), sentToRecycling: Number(draft.sentToRecycling), startedAt: status === 'Pending' || status === 'Received' ? stage.startedAt : isoTime(draft.startedAt), completedAt: status === 'Completed' ? isoTime(draft.completedAt) : undefined });
      onClose();
    } catch (error) { setError(errorText(error)); }
  };
  return <JobModal title={`Update Stage — ${stage.name}`} onClose={onClose}><form onSubmit={submit} className="space-y-4">{stage.handover && <p className="rounded-card bg-navy/5 p-3 text-sm text-navy">Previous stage output: {fmtQuantity(stage.handover.quantity, stage.handover.unit)}. {received ? 'Received input is prefilled and locked.' : 'This stage uses a different input unit; record received input explicitly.'}</p>}<div className="grid gap-4 sm:grid-cols-2">{([['inputQuantity', 'Input Quantity'], ['outputQuantity', 'Output Quantity'], ['wasteQuantity', 'Waste Quantity']] as const).map(([key, label]) => <label key={key} className="text-sm text-gray-600">{label}<input readOnly={key === 'inputQuantity' && received} type="number" min="0" step="any" value={draft[key]} onChange={e => setDraft({ ...draft, [key]: e.target.value })} className={`${ENTRY_INPUT} mt-1`} /></label>)}{([['inputUnit', 'Input Unit'], ['outputUnit', 'Output Unit'], ['wasteUnit', 'Waste Unit'], ['operator', 'Operator / Responsible Person'], ['wasteType', 'Waste Type / Category'], ['wasteReason', 'Waste Reason']] as const).map(([key, label]) => <label key={key} className="text-sm text-gray-600">{label}<input readOnly={lockUnits && ['inputUnit', 'outputUnit', 'wasteUnit'].includes(key) || key === 'inputUnit' && received} value={draft[key]} onChange={e => setDraft({ ...draft, [key]: e.target.value })} className={`${ENTRY_INPUT} mt-1`} /></label>)}<label className="text-sm text-gray-600">Quantity Sent to Recycling<input type="number" min="0" step="any" value={draft.sentToRecycling} onChange={e => setDraft({ ...draft, sentToRecycling: e.target.value })} className={`${ENTRY_INPUT} mt-1`} /></label><label className="text-sm text-gray-600">Status<select aria-label="Stage status" value={draft.status} onChange={e => setDraft({ ...draft, status: e.target.value as JobProductionStage['status'] })} className={`${ENTRY_INPUT} mt-1`}>{Object.entries(PRODUCTION_STATUS_LABELS).map(([id, label]) => <option key={id} value={id}>{label}</option>)}</select></label><label className="text-sm text-gray-600">Start Date/Time<input type="datetime-local" value={draft.startedAt} onChange={e => setDraft({ ...draft, startedAt: e.target.value })} className={`${ENTRY_INPUT} mt-1`} /></label><label className="text-sm text-gray-600">Completion Date/Time<input type="datetime-local" value={draft.completedAt} onChange={e => setDraft({ ...draft, completedAt: e.target.value })} className={`${ENTRY_INPUT} mt-1`} /></label></div>
    <button type="button" className={JOB_BUTTON} disabled={!draft.inputUnit || draft.inputUnit !== draft.outputUnit || draft.inputUnit !== draft.wasteUnit || draft.inputQuantity === '' || draft.outputQuantity === '' || Number(draft.outputQuantity) > Number(draft.inputQuantity)} onClick={() => setDraft({ ...draft, wasteQuantity: String(Math.round((Number(draft.inputQuantity) - Number(draft.outputQuantity)) * 1e6) / 1e6) })}>Calculate Waste (same units)</button><label className="block text-sm text-gray-600">Remarks<textarea value={draft.remarks} onChange={e => setDraft({ ...draft, remarks: e.target.value })} className={`${ENTRY_INPUT} mt-1`} /></label><p className="text-xs text-gray-500">Recycling quantities are Job Card tracking only; no Recycling movement is posted. Completed records are locked.</p>{error && <p role="alert" className="text-sm text-red-600">{error}</p>}<div className="flex flex-wrap justify-end gap-2"><button type="button" className={JOB_BUTTON} onClick={onClose}>Cancel</button><button className={JOB_BUTTON} value="save">Save Stage</button><button className={JOB_PRIMARY} value="complete">Complete &amp; Send to Next Stage</button></div></form></JobModal>;
}

export function StockTransferForm({ card, onSave, onClose }: { card: JobCard; onSave: (quantity: number, batchDate: string, receipt: StockReceiptOptions) => void; onClose: () => void }) {
  const quality = useQuality();
  const authorizedBatches = quality.releases.filter(r => r.purpose === 'finished_stock' && r.subject.manufacturingItemId === card.id);
  const totals = productionTotals(card);
  const remaining = (totals.produced ?? 0) - (card.acceptedQuantity ?? 0) - (card.rejectedQuantity ?? 0);
  const [receiptId] = useState(() => crypto.randomUUID());
  const [batch, setBatch] = useState(authorizedBatches[0]?.subject.batchNumber ?? '');
  const [rejected, setRejected] = useState('0');
  const [verified, setVerified] = useState(false);
  const [accepted, setAccepted] = useState(String(remaining));
  const [batchDate, setBatchDate] = useState(localToday());
  const [error, setError] = useState('');
  const submit = (e: FormEvent) => { e.preventDefault(); try { onSave(Number(accepted), batchDate, { id: receiptId, batch, rejected: Number(rejected), qcVerified: verified }); onClose(); } catch (error) { setError(errorText(error)); } };
  return <JobModal title={`Transfer to Finished Goods — ${card.jobCardNumber}`} onClose={onClose}><form onSubmit={submit} className="space-y-4"><p className="text-sm text-gray-600">Job: {card.jobCardNumber} · Sales Order: {card.salesOrderNumber} · Customer: {card.customerName} · Product: {card.product} · Model: {card.modelName} · Remaining unaccounted: {remaining} {totals.unit}. Final produced quantity: {fmtQuantity(totals.produced, totals.unit)}</p><label>Authorized QC Batch / Lot<select required value={batch} onChange={e => setBatch(e.target.value)} className={ENTRY_INPUT}><option value="">Select authorized batch</option>{authorizedBatches.map(r => <option key={r.id} value={r.subject.batchNumber}>{r.subject.batchNumber} · Approved {r.acceptedQuantity} / Rejected {r.rejectedQuantity} {r.unit}</option>)}</select></label><label>Rejected Quantity<input required type="number" min="0" max={remaining} step="any" value={rejected} onChange={e => setRejected(e.target.value)} className={ENTRY_INPUT} /></label><label className="block"><input required type="checkbox" checked={verified} onChange={e => setVerified(e.target.checked)} /> QC verified accepted quantity</label><label className="block text-sm text-gray-600">Accepted Finished Quantity<input required type="number" min="0" max={remaining} step="any" value={accepted} onChange={e => setAccepted(e.target.value)} className={`${ENTRY_INPUT} mt-1`} /></label><label className="block text-sm text-gray-600">Production / Batch Date<input required type="date" min={card.createdDate?.slice(0, 10)} max={localToday()} value={batchDate} onChange={e => setBatchDate(e.target.value)} className={`${ENTRY_INPUT} mt-1`} /></label><p className="text-xs text-gray-500">Confirm that QC accepted this quantity. Rejected this batch: {rejected} {totals.unit}. Remaining quantity can be received in another batch. Posts Finished Goods Stock IN in shared frontend state; no dispatch occurs. Location is not configured.</p>{error && <p role="alert" className="text-sm text-red-600">{error}</p>}<div className="flex justify-end gap-2"><button type="button" className={JOB_BUTTON} onClick={onClose}>Cancel</button><button className={JOB_PRIMARY}>Confirm Transfer</button></div></form></JobModal>;
}
