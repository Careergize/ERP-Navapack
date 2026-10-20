import type { CommercialRecord } from '@/lib/commercialApi';
import { CommercialSnapshot } from './CommercialSnapshot';

export function DraftPreview({ record, close }: { record: CommercialRecord; close: () => void }) {
  return <div role="dialog" aria-modal="true" aria-label="Development document preview" className="draft-preview fixed inset-0 z-50 overflow-auto bg-white p-6 sm:p-12">
    <style>{`@media print { body * { visibility: hidden; } .draft-preview, .draft-preview * { visibility: visible; } .draft-preview { position: absolute; inset: 0; overflow: visible; padding: 24mm 10mm; } .draft-preview .no-print { display: none; } .draft-preview .preview-mark { position: fixed; top: 0; left: 0; right: 0; background: white; padding: 6mm; font-size: 10px; } @page { margin: 15mm; } }`}</style>
    <p className="preview-mark border-2 border-amber-700 p-3 font-bold">DEVELOPMENT PREVIEW — NOT APPROVED FOR CUSTOMER ISSUE</p>
    <div className="no-print my-4 flex gap-4"><button onClick={() => window.print()}>Print / save draft PDF</button><button onClick={close}>Close preview</button></div>
    <h1 className="mt-6 text-2xl">Navapack {record.kind.replaceAll('_', ' ')} draft</h1>
    <p>Document {record.id} · revision {record.version} · {record.status}</p>
    <p className="break-all">Immutable revision: {record.revision} · SHA256: {record.sha256}</p>
    <p>VAT, LED and final payable are unknown and unavailable. This preview provides no approval, customer acceptance, stock commitment or financial posting.</p>
    <CommercialSnapshot snapshot={record.snapshot}/>
    <p className="mt-6">Persisted draft data only. No customer email or legally effective invoice is generated.</p>
  </div>;
}
