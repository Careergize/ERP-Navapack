import assert from 'node:assert/strict';
import { createServer } from 'vite';
import { fileURLToPath } from 'node:url';

globalThis.localStorage = globalThis.sessionStorage = { getItem: () => null };
const server = await createServer({ configFile: false, resolve: { alias: { '@': fileURLToPath(new URL('../src', import.meta.url)) } }, optimizeDeps: { noDiscovery: true }, server: { middlewareMode: true, hmr: false }, appType: 'custom' });
try {
  const q = await server.ssrLoadModule('/src/lib/quotations.ts');
  const persistence = await server.ssrLoadModule('/src/lib/quotationApi.ts');
  const { api } = await server.ssrLoadModule('/src/lib/api.ts');
  const draft = q.createQuotation(q.COMPANY_DEFAULTS, [], { id: '1', name: 'Sales', role: 'admin' });
  draft.salesRepresentative = 'Sales rep';
  draft.lines = [{ ...q.blankQuotationLine(), productId: 'product-ref', description: 'Bag', unit: 'kg', unitId: 1, quantity: 2.5, unitPrice: 100 }];
  const record = { id: draft.id, version: 2, editor_data: { ...draft, taxRate: '18.00', discount: '0.00', status: 'Approved', lines: [{ ...draft.lines[0], quantity: '2.500000', unitPrice: '100.000000' }] }, created_by: '1', created_by_name: 'Sales', updated_at: '2026-10-16T10:00:00Z', review: null };
  let body;
  api.defaults.adapter = async config => {
    body = config.data && JSON.parse(config.data);
    return { config, status: 200, statusText: 'OK', headers: {}, data: config.method === 'post' ? record : { results: [record], next: null } };
  };
  draft.draftVersion = 1;
  await persistence.saveQuotationDraft(draft);
  assert.equal(body.expected_version, 1);
  assert.equal(body.editor_data.lines[0].productId, 'product-ref');
  const restored = (await persistence.loadQuotationDrafts())[0];
  assert.equal(restored.id, draft.id);
  assert.equal(restored.draftVersion, 2);
  assert.equal(restored.salesRepresentative, 'Sales rep');
  assert.equal(restored.lines[0].quantity, 2.5);
  assert.equal(restored.lines[0].unitPrice, 100);
  assert.equal(restored.status, 'Draft'); // client metadata cannot assert manager approval
  assert.equal(q.quotationTotals(restored).total, 250);
  record.review = { id: 'snapshot', submitted_at: '2026-10-16T10:00:00Z', approved: false, rejected_at: '2026-10-16T10:01:00Z', rejection_reason: 'Revise prices', reviewed_by: 'Manager', deliveries: [] };
  assert.equal(persistence.quotationFromDraft(record).status, 'Rejected');
  assert.equal(persistence.quotationFromDraft(record).events.at(-1).description, 'Revise prices');
  console.log('Passed: durable save payload/version, reload identity/source references, numeric reconstruction, totals and server-controlled review status.');
} finally { await server.close(); }
