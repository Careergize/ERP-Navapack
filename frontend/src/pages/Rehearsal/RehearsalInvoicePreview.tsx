import type { RehearsalJob } from '@/lib/rehearsalApi';
import { CommercialSnapshot } from '../Commercial/CommercialSnapshot';
import type { CommercialRecord } from '@/lib/commercialApi';
export function RehearsalInvoicePreview({job, close}: {job: RehearsalJob; close: () => void}) {
  return <div role="dialog" aria-modal="true" aria-label="Synthetic invoice preview" className="rehearsal-preview fixed inset-0 z-50 overflow-auto bg-white p-6 sm:p-12">
    <style>{`@media print { body * { visibility: hidden; } .rehearsal-preview, .rehearsal-preview * { visibility: visible; } .rehearsal-preview { position: absolute; inset: 0; overflow: visible; padding: 24mm 10mm; } .rehearsal-preview .no-print { display: none; } .rehearsal-preview .preview-mark { position: fixed; top: 0; left: 0; right: 0; background: white; padding: 6mm; font-size: 10px; } @page { margin: 15mm; } }`}</style>
    <p className="preview-mark border-2 border-amber-700 p-3 font-bold">DEVELOPMENT PREVIEW — NOT APPROVED FOR CUSTOMER ISSUE</p>
    <div className="no-print my-4 flex gap-4"><button onClick={() => window.print()}>Print / save draft PDF</button><button onClick={close}>Close preview</button></div>
    <h1 className="mt-6 text-2xl">Synthetic invoice example</h1>
    <p>Simulation job {job.id} · revision {job.version} · status {job.status}</p><p>Immutable sales order revision: {job.sales_order_revision}</p>
    <p>No legal invoice number. No financial posting, customer acceptance or customer communication. VAT, LED and final payable are unavailable pending verified policies.</p>
    <CommercialSnapshot snapshot={job.snapshot.source as unknown as CommercialRecord['snapshot']}/>
    <p className="mt-6 font-semibold">SIMULATION ONLY — NO OPERATIONAL AUTHORITY</p>
  </div>;
}
