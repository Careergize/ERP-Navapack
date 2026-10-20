import assert from 'node:assert/strict';
import { createServer } from 'vite';
import { fileURLToPath } from 'node:url';
class Storage { values = new Map(); getItem(k) { return this.values.get(k) ?? null; } setItem(k,v) { this.values.set(k,String(v)); } removeItem(k) { this.values.delete(k); } }
globalThis.localStorage = new Storage(); globalThis.sessionStorage = new Storage(); globalThis.window = new EventTarget();
const server = await createServer({ configFile: false, resolve: { alias: { '@': fileURLToPath(new URL('../src', import.meta.url)) } }, optimizeDeps: { noDiscovery: true }, server: { middlewareMode: true, hmr: false }, appType: 'custom' });
try {
  const { api, loginRequest } = await server.ssrLoadModule('/src/lib/api.ts');
  const { saveTokens } = await server.ssrLoadModule('/src/lib/authSession.ts');
  const { saveCommercial, deriveCommercial } = await server.ssrLoadModule('/src/lib/commercialApi.ts');
  const { createRehearsal, commandRehearsal, rehearsalJob, rehearsalHistory, rehearsalDashboard } = await server.ssrLoadModule('/src/lib/rehearsalApi.ts');
  if (process.env.ERP_LIVE_URL) {
    assert.match(process.env.ERP_LIVE_URL, /^http:\/\/localhost:\d+\/api\/v1$/);
    api.defaults.baseURL = process.env.ERP_LIVE_URL;
    const login = await loginRequest({ email: 'commercial@example.com', password: 'password' });
    saveTokens(login.access, login.refresh, false);
    const fixture = JSON.parse(process.env.ERP_SYNTHETIC_INPUT);
    const cost = await saveCommercial('COSTING', fixture.data, 'Synthetic transport costing', crypto.randomUUID());
    const quote = await deriveCommercial(cost, 'Synthetic transport quotation', crypto.randomUUID());
    const order = await deriveCommercial(quote, 'Synthetic transport demand', crypto.randomUUID());
    assert.equal(order.snapshot.synthetic_source.revision, quote.revision);
    const body = { sales_order_revision: order.revision, warehouse: fixture.warehouse,
      routes: fixture.data.lines.map((_, line) => ({line, stages: ['PACKING']})), reason: 'Synthetic transport job' };
    const key = crypto.randomUUID();
    let job = await createRehearsal(body, key);
    assert.equal((await createRehearsal(body, key)).id, job.id);
    const old = job;
    job = await commandRehearsal(job, 'review', {}, 'Synthetic review', crypto.randomUUID());
    await assert.rejects(commandRehearsal(old, 'review', {}, 'Stale synthetic review', crypto.randomUUID()), e => e.response.status === 412);
    await assert.rejects(commandRehearsal(job, 'issue', {quantity:'10', available_quantity:'9'}, 'Insufficient simulation', crypto.randomUUID()), e => e.response.status === 409);
    job = await commandRehearsal(job, 'issue', {quantity:'10', available_quantity:'10'}, 'Synthetic issue', crypto.randomUUID());
    for (let line = 0; line < fixture.data.lines.length; line++) {
      job = await commandRehearsal(job, 'start', {line, stage:'PACKING', machine:'synthetic:machine', operator:'synthetic:operator', input_quantity:'3'}, 'Synthetic start', crypto.randomUUID());
      job = await commandRehearsal(job, 'complete', {line, stage:'PACKING', output_quantity:'3', waste:'0', rejection:'0'}, 'Synthetic complete', crypto.randomUUID());
    }
    for (const [action, data] of [['qc', {outcome:'PASS'}], ['finish', {}], ['dispatch', {}]])
      job = await commandRehearsal(job, action, data, 'Synthetic '+action, crypto.randomUUID());
    assert.equal(job.status, 'DISPATCHED'); assert.equal(job.operational_posting, false);
    assert.equal(job.invoice_preview.payable_total, null);
    assert.match(job.invoice_preview.watermark, /NOT APPROVED FOR CUSTOMER ISSUE/);
    assert.equal((await rehearsalJob(job.id)).version, job.version);
    assert.equal((await rehearsalHistory(job.id)).count, job.version);
    assert.equal((await rehearsalDashboard()).statuses.DISPATCHED, 1);
    const renewed = await loginRequest({ email: 'commercial@example.com', password: 'password' });
    saveTokens(renewed.access, renewed.refresh, false);
    const restored = await rehearsalJob(job.id);
    assert.equal(restored.version, job.version);
    assert.equal(restored.status, 'DISPATCHED');
    assert.equal(restored.snapshot.source_sha256, job.snapshot.source_sha256);
    console.log('LIVE ERP PASS: actual React adapters, JWT, draft costing/quotation/order lineage, two-product synthetic production/QC/dispatch, stale edits, retries and immutable history.');
  } else {
    const requests = [];
    api.defaults.adapter = async config => { requests.push(config); return { config, data:{id:'synthetic', version:2}, status:200, statusText:'OK', headers:{} }; };
    await createRehearsal({sales_order_revision:'revision', warehouse:'warehouse', routes:[{line:0, stages:['PACKING']}], reason:'Synthetic'}, 'create-key');
    assert.equal(requests.at(-1).url, '/rehearsal/jobs/');
    assert.equal(requests.at(-1).headers['Idempotency-Key'], 'create-key');
    await commandRehearsal({id:'job', version:7}, 'issue', {quantity:'0.123456', available_quantity:'1'}, 'Synthetic', 'issue-key');
    assert.equal(requests.at(-1).headers['If-Match'], '"7"');
    assert.equal(JSON.parse(requests.at(-1).data).data.quantity, '0.123456');
    await rehearsalHistory('job', 2); assert.equal(requests.at(-1).params.page, 2);
    await deriveCommercial({id:'cost', revision:'sealed'}, 'Synthetic', 'derive-key');
    assert.equal(JSON.parse(requests.at(-1).data).source_revision, 'sealed');
    api.defaults.adapter = async () => { throw new Error('denied'); };
    await assert.rejects(commandRehearsal({id:'job', version:7}, 'review', {}, 'Synthetic', 'denied'));
    console.log('PASS: rehearsal retry/version headers, exact quantity strings, pagination, immutable draft derivation and denied-command propagation.');
  }
} catch(error) { console.error('Rehearsal check failed:', error.response?.status ?? '', error.response?.data ?? error); process.exitCode = 1; }
finally { await server.close(); }
