import { CheckCircle2, Circle, PauseCircle } from 'lucide-react';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { JOB_STATUS_LABELS, PRODUCTION_STATUS_LABELS, currentLocation, orderedStages, productionStages } from '@/lib/jobCards';
import type { JobCard } from '@/types';

export const JOB_BUTTON = 'inline-flex items-center justify-center gap-2 rounded-card border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-navy hover:bg-gray-50 focus-visible:ring-2 focus-visible:ring-navy disabled:opacity-50';
export const JOB_PRIMARY = 'inline-flex items-center justify-center gap-2 rounded-card bg-navy px-4 py-2 text-sm font-medium text-white hover:opacity-90 focus-visible:ring-2 focus-visible:ring-navy disabled:opacity-50';
export const jobDate = (value?: string) => !value ? 'Not recorded' : Number.isNaN(Date.parse(value)) ? value : new Date(value).toLocaleString('en-IN', value.length === 10 ? { day: '2-digit', month: 'short', year: 'numeric' } : { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
export function JobStatus({ card }: { card: JobCard }) { return <StatusBadge status={JOB_STATUS_LABELS[card.status] ?? card.status} />; }
export function JobFields({ fields }: { fields: [string, string][] }) {
  return <dl className="grid gap-x-6 gap-y-4 sm:grid-cols-2 lg:grid-cols-3">{fields.map(([label, value]) => <div key={label} className="min-w-0"><dt className="text-xs text-gray-500">{label}</dt><dd className="mt-1 break-words text-sm font-medium text-navy">{value || 'Not recorded'}</dd></div>)}</dl>;
}
export function JobProgress({ card, compact = false }: { card: JobCard; compact?: boolean }) {
  const stages = productionStages(card);
  const completed = stages.filter(s => s.status === 'Completed').length;
  const location = currentLocation(card);
  const approved = !['Draft', 'PendingApproval'].includes(card.status);
  const issued = approved && !['Approved', 'StoreIssuePending'].includes(card.status);
  const steps = [
    { id: 'created', name: 'Created', status: 'Completed', current: false },
    { id: 'approval', name: 'PM Approval', status: approved ? 'Completed' : 'Pending', current: !approved },
    { id: 'issue', name: 'Store Issue', status: issued ? 'Completed' : 'Pending', current: approved && !issued },
    ...orderedStages(card).filter(s => s.required).map(s => ({ id: s.id, name: s.name, status: s.status, current: location.stage === s.name })),
  ];
  return <div className="space-y-3"><p className="text-xs font-medium text-gray-500">Production progress: {completed} / {stages.length} required production stages completed</p><ol aria-label="Job card workflow progress" className={`flex flex-wrap ${compact ? 'gap-2' : 'gap-3'}`}>{steps.map(step => {
    const done = step.status === 'Completed';
    const hold = step.status === 'OnHold';
    const Icon = done ? CheckCircle2 : hold ? PauseCircle : Circle;
    const label = PRODUCTION_STATUS_LABELS[step.status as keyof typeof PRODUCTION_STATUS_LABELS] ?? step.status;
    return <li key={step.id} aria-current={step.current ? 'step' : undefined} className={`flex max-w-full items-center gap-2 rounded-card border px-3 py-2 text-xs ${done ? 'border-green/20 bg-green/10 text-green' : hold ? 'border-amber-200 bg-amber-50 text-amber-700' : step.current || ['Received', 'InProgress'].includes(step.status) ? 'border-navy/30 bg-navy/10 text-navy' : 'border-gray-200 text-gray-500'}`}><Icon size={14} /><span className="min-w-0 break-words">{step.name}{!compact && <span className="mt-0.5 block text-[10px]">{step.current && step.status === 'Pending' ? 'Current · Pending' : label}</span>}</span><span className="sr-only">{compact ? label : ''}</span></li>;
  })}</ol></div>;
}
