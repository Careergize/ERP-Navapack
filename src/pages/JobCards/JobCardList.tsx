import { workItems } from '@/lib/parentJobCards';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Search } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { ENTRY_INPUT } from '@/components/ui/SearchSelect';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { useJobCards } from '@/context/JobCardsContext';
import { JOB_STATUS_LABELS, currentLocation, filterJobCards, fmtQuantity, isDelayed, jobSummary, orderedStages, productionTotals, type JobFilters } from '@/lib/jobCards';
import { JOB_BUTTON, JobFields, JobProgress, JobStatus, jobDate } from './JobCardUI';

const emptyFilters: JobFilters = { query: '', status: 'all', department: 'all', stage: 'all', from: '', to: '' };
export function JobCardList() {
  const { cards, loading, usingDemo, load } = useJobCards();
  const [filters, setFilters] = useState(emptyFilters);
  useEffect(() => { void load(); }, [load]);
  const locations = cards.flatMap(workItems).map(currentLocation);
  const departments = [...new Set(locations.map(location => location.department))].sort();
  const stages = [...new Set(locations.map(location => location.stage))].sort();
  const filtered = filterJobCards(cards, filters);
  const update = (key: keyof JobFilters, value: string) => setFilters(current => ({ ...current, [key]: value }));
  return <div className="space-y-6">
    <header><h1 className="text-2xl font-semibold text-navy">Job Cards</h1><p className="mt-1 text-sm text-gray-500">Manufacturing approval, materials, department handovers and production tracking.</p></header>
    <section aria-label="Job card summary" className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">{jobSummary(cards).map(([label, count]) => <Card key={label}><p className="text-sm text-gray-500">{label}</p><p className={`mt-1 text-2xl font-semibold ${label === 'Delayed' && count ? 'text-amber-700' : 'text-navy'}`}>{count}</p></Card>)}</section>
    <p className="text-xs text-gray-500">{usingDemo ? 'Illustrative frontend Job Cards.' : 'Job Card data with frontend manufacturing tracking.'} Workflow changes survive navigation and reset on refresh. Store issue and stock transfer do not post inventory.</p>
    <Card><div className="flex flex-wrap items-end gap-3"><div className="relative min-w-0 w-full flex-1 sm:min-w-[200px]"><Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" /><input aria-label="Search job cards" type="search" placeholder="Job card, sales order, customer or product" value={filters.query} onChange={e => update('query', e.target.value)} className={`${ENTRY_INPUT} pl-9`} /></div>
      <label className="w-full text-xs text-gray-500 sm:w-auto">Status<select aria-label="Job status filter" value={filters.status} onChange={e => update('status', e.target.value)} className={`${ENTRY_INPUT} mt-1`}><option value="all">All statuses</option>{Object.entries(JOB_STATUS_LABELS).filter(([id]) => id !== 'Issued').map(([id, label]) => <option key={id} value={id}>{label}</option>)}<option value="Delayed">Delayed</option></select></label>
      <label className="w-full text-xs text-gray-500 sm:w-auto">Department<select aria-label="Department filter" value={filters.department} onChange={e => update('department', e.target.value)} className={`${ENTRY_INPUT} mt-1`}><option value="all">All departments</option>{departments.map(name => <option key={name}>{name}</option>)}</select></label>
      <label className="w-full text-xs text-gray-500 sm:w-auto">Current stage<select aria-label="Production stage filter" value={filters.stage} onChange={e => update('stage', e.target.value)} className={`${ENTRY_INPUT} mt-1`}><option value="all">All stages</option>{stages.map(name => <option key={name}>{name}</option>)}</select></label>
      <label className="w-full text-xs text-gray-500 sm:w-auto">Created from<input aria-label="Created from" type="date" max={filters.to || undefined} value={filters.from} onChange={e => update('from', e.target.value)} className={`${ENTRY_INPUT} mt-1`} /></label><label className="w-full text-xs text-gray-500 sm:w-auto">Created to<input aria-label="Created to" type="date" min={filters.from || undefined} value={filters.to} onChange={e => update('to', e.target.value)} className={`${ENTRY_INPUT} mt-1`} /></label><button className={JOB_BUTTON} onClick={() => setFilters(emptyFilters)}>Clear Filters</button>
    </div>{filters.from && filters.to && filters.from > filters.to && <p role="alert" className="mt-3 text-sm text-amber-700">Choose an end date on or after the start date.</p>}</Card>
    {loading && <p role="status" className="text-sm text-gray-500">Loading job cards…</p>}
    <p aria-live="polite" className="text-xs text-gray-500">Showing {filtered.length} of {cards.length} job cards</p>
    <div className="space-y-4">{filtered.map(card => {
      const location = currentLocation(card), totals = productionTotals(card);
      const latest = orderedStages(card).filter(s => s.required && s.kind === 'production' && s.outputQuantity !== null).at(-1);
      return <Link key={card.id} to={`/job-cards/${card.id}`} className="block rounded-card focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-navy" aria-label={`View ${card.jobCardNumber}`}><Card className={`space-y-4 transition-shadow hover:shadow-md ${isDelayed(card) ? 'ring-1 ring-amber-300' : ''}`}>
        <div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="font-semibold text-navy">{card.jobCardNumber}</h2><p className="mt-1 break-words text-sm text-gray-500">{card.salesOrderNumber ?? 'Sales order not recorded'} · {card.customerName ?? 'Customer not recorded'}</p></div><div className="flex flex-wrap gap-2"><JobStatus card={card} />{isDelayed(card) && <StatusBadge status="Delayed" />}</div></div>
        {card.manufacturingItems ? <div className="space-y-4">{card.manufacturingItems.map(item => <div key={item.id}><p className="text-sm font-medium text-navy">{item.product} · {item.modelName} · {fmtQuantity(item.qty, item.unit)} · {currentLocation(item).department} / {currentLocation(item).stage}</p><JobProgress card={item} compact /></div>)}<p className="text-xs text-gray-500">Due: {jobDate(card.requiredDate)} · {card.manufacturingItems.length} manufacturing items</p></div> : <JobFields fields={[["Model / Product", [card.modelName, card.product !== card.modelName ? card.product : ''].filter(Boolean).join(' · ')], ['Order Quantity', fmtQuantity(card.qty, card.unit)], ['Current Department', location.department], ['Current Production Stage', location.stage], ['Output / Produced Quantity', fmtQuantity(latest?.outputQuantity, latest?.outputUnit)], ['Waste Quantity', totals.waste], ['Required / Due Date', jobDate(card.requiredDate)]]} />}
        {!card.manufacturingItems && <JobProgress card={card} compact />}<p className="text-right text-sm font-medium text-navy">View Details →</p>
      </Card></Link>;
    })}{!loading && !filtered.length && <Card><p className="py-6 text-center text-sm text-gray-500">No job cards match your search and filters.</p></Card>}</div>
  </div>;
}
