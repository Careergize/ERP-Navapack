import assert from 'node:assert/strict';
import { createServer } from 'vite';
import { fileURLToPath } from 'node:url';
class Storage { values = new Map(); getItem(k) { return this.values.get(k) ?? null; } setItem(k,v) { this.values.set(k,String(v)); } removeItem(k) { this.values.delete(k); } }
globalThis.localStorage = new Storage(); globalThis.sessionStorage = new Storage(); globalThis.window = new EventTarget();
const server = await createServer({ configFile: false, resolve: { alias: { '@': fileURLToPath(new URL('../src', import.meta.url)) } }, optimizeDeps: { noDiscovery: true }, server: { middlewareMode: true, hmr: false }, appType: 'custom' });
try {
  const { api, loginRequest } = await server.ssrLoadModule('/src/lib/api.ts');
  const { saveTokens } = await server.ssrLoadModule('/src/lib/authSession.ts');
  const { saveCommercial, commercialPage, commercialHistory, transitionCommercial } = await server.ssrLoadModule('/src/lib/commercialApi.ts');
  if (process.env.PHASE4A_LIVE_URL) {
    assert.match(process.env.PHASE4A_LIVE_URL, /^http:\/\/localhost:\d+\/api\/v1$/);
    api.defaults.baseURL = process.env.PHASE4A_LIVE_URL;
    const login = await loginRequest({ email: 'commercial@example.com', password: 'password' });
    saveTokens(login.access, login.refresh, false);
    const data = JSON.parse(process.env.PHASE4A_SYNTHETIC_INPUT);
    const key = crypto.randomUUID();
    const cost = await saveCommercial('COSTING', data, 'Synthetic transport costing', key);
    assert.equal(cost.snapshot.estimate.net_estimate, '3.02');
    assert.equal((await saveCommercial('COSTING', data, 'Synthetic transport costing', key)).id, cost.id);
    const commercial = structuredClone(data); delete commercial.lines[0].costing;
    commercial.lines[0].costing_revision = cost.revision;
    const quote = await saveCommercial('QUOTATION', commercial, 'Synthetic transport quote', crypto.randomUUID());
    const updated = await saveCommercial('QUOTATION', { ...commercial, terms: 'Revised terms' }, 'Synthetic edit', crypto.randomUUID(), quote);
    await assert.rejects(saveCommercial('QUOTATION', commercial, 'Stale edit', crypto.randomUUID(), quote), e => e.response.status === 412);
    const review = await transitionCommercial(updated, 'submit', 'Synthetic review', crypto.randomUUID());
    assert.equal(review.status, 'REVIEW');
    const reopened = await transitionCommercial(review, 'reopen', 'Synthetic correction', crypto.randomUUID());
    assert.equal(reopened.status, 'DRAFT');
    assert.equal((await commercialHistory(quote.id)).count, 4);
    commercial.lines.push({ ...commercial.lines[0], quantity: '7', costing_revision: undefined });
    const order = await saveCommercial('SALES_ORDER', commercial, 'Synthetic multi-line order', crypto.randomUUID());
    assert.equal(order.snapshot.input.lines.length, 2); assert.equal(order.snapshot.estimate.payable_total, null);
    assert.equal((await commercialPage()).count, 3);
    console.log('LIVE PASS: actual React API adapter, JWT login, costing/quote/order persistence, exact snapshots, retry, stale edit, review/reopen and history.');
  } else {
    const requests = [];
    api.defaults.adapter = async config => { requests.push(config); return { config, data: { id: 'synthetic', version: 2 }, status: 200, statusText: 'OK', headers: {} }; };
    const data = { lines: [{ quantity: '0.123456', unit_price: '999.123456' }] };
    await saveCommercial('QUOTATION', data, 'Synthetic intent', 'same-key');
    assert.equal(requests.at(-1).url, '/commercial/documents/');
    assert.equal(JSON.parse(requests.at(-1).data).data.lines[0].quantity, '0.123456');
    const record = { id: 'synthetic', version: 7 };
    await saveCommercial('QUOTATION', data, 'Synthetic intent', 'same-edit-key', record);
    assert.equal(requests.at(-1).headers['If-Match'], '"7"');
    assert.equal(requests.at(-1).headers['Idempotency-Key'], 'same-edit-key');
    await transitionCommercial(record, 'submit', 'Review', 'review-key');
    assert.equal(requests.at(-1).url, '/commercial/documents/synthetic/transition/');
    await commercialHistory('synthetic', 2); assert.equal(requests.at(-1).params.page, 2);
    api.defaults.adapter = async () => { throw new Error('denied'); };
    await assert.rejects(saveCommercial('SALES_ORDER', data, 'Synthetic', 'denied'));
    console.log('PASS: commercial decimal strings, version/retry headers, namespaced routes, history pagination and error propagation.');
  }
} catch (error) {
  console.error('Commercial check failed:', error.response?.status ?? '', error.response?.data?.error ?? error.message);
  process.exitCode = 1;
} finally { await server.close(); }
