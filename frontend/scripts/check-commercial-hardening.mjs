import assert from 'node:assert/strict';
import { createServer } from 'vite';
import { fileURLToPath } from 'node:url';
class Storage { values = new Map(); getItem(k) { return this.values.get(k) ?? null; } setItem(k,v) { this.values.set(k,String(v)); } removeItem(k) { this.values.delete(k); } }
globalThis.localStorage = new Storage(); globalThis.sessionStorage = new Storage(); globalThis.window = new EventTarget();
const server = await createServer({ configFile: false, resolve: { alias: { '@': fileURLToPath(new URL('../src', import.meta.url)) } }, optimizeDeps: { noDiscovery: true }, server: { middlewareMode: true, hmr: false }, appType: 'custom' });
try {
  const { api, loginRequest } = await server.ssrLoadModule('/src/lib/api.ts');
  const { saveTokens } = await server.ssrLoadModule('/src/lib/authSession.ts');
  const commercial = await server.ssrLoadModule('/src/lib/commercialApi.ts');
  const gov = await server.ssrLoadModule('/src/lib/commercialGovernanceApi.ts');
  const editor = await server.ssrLoadModule('/src/lib/commercialEditor.ts');
  const sample = { currency: 'UGX', money_places: 2, rounding: 'HALF_UP', discount: '0', terms: 'Retained', marketing_person: 'employee', classification: 'B2B', lines: [{ variant: 'v', unit: 'u', quantity: '0.000001', unit_price: '1.123456', specifications: 'Spec', customisation: 'Artwork', model_revision: 'model-r1', stock_identity: 'stock', requested_delivery: '2026-11-02', costing: { materials: [{ material: 'm', unit: 'u', price_unit: 'u', currency: 'UGX', quantity: '0.000001', price: '1.123456', master_snapshot: { name: 'Old name' } }, { material: 'm2', unit: 'u2', price_unit: 'u2', currency: 'UGX', quantity: '2', price: '3' }], processes: [{ description: 'A', currency: 'UGX', amount: '1' }, { description: 'B', currency: 'UGX', amount: '2' }], waste_percent: '2', rejection_percent: '1', markup_percent: '25', assumption_evidence: 'Synthetic' }, variant_snapshot: { name: 'Old variant' } }], party_snapshot: null };
  const projected = editor.editableCommercialInput(sample);
  assert.equal(projected.lines[0].costing.materials.length, 2); assert.equal(projected.lines[0].costing.processes.length, 2);
  assert.equal(projected.lines[0].stock_identity, 'stock'); assert.equal(projected.marketing_person, 'employee');
  assert.equal(projected.lines[0].model_revision, 'model-r1'); assert.equal(projected.lines[0].quantity, '0.000001');
  assert.ok(!('master_snapshot' in projected.lines[0].costing.materials[0]));
  assert.throws(() => editor.editableCommercialInput({ ...sample, future_required_rule: 'must not vanish' }));
  assert.equal(editor.compareCommercial(projected, structuredClone(projected)).length, 0);
  if (process.env.PHASE4B_LIVE_URL) {
    assert.match(process.env.PHASE4B_LIVE_URL, /^http:\/\/localhost:\d+\/api\/v1$/); api.defaults.baseURL = process.env.PHASE4B_LIVE_URL;
    async function login(email) { const r = await loginRequest({ email, password: 'password' }); saveTokens(r.access, r.refresh, false); }
    await login('commercial@example.com');
    const data = JSON.parse(process.env.PHASE4B_SYNTHETIC_INPUT);
    const employee = (await commercial.allCommercialReferences('/commercial/references/marketing-people/'))[0]; data.marketing_person = employee.id;
    data.lines[0].model_revision = process.env.PHASE4B_MODEL_REVISION; data.lines[0].requested_delivery = '2026-11-02';
    data.lines[0].costing.materials.push({ ...data.lines[0].costing.materials[0], quantity: '2' });
    data.lines[0].costing.processes.push({ description: 'Second process', currency: 'UGX', amount: '2.123456' });
    const cost = await commercial.saveCommercial('COSTING', data, 'Synthetic multicomponent costing', crypto.randomUUID());
    const edited = editor.editableCommercialInput(cost.snapshot.input); assert.deepEqual(edited, data);
    edited.terms = 'Changed terms'; const revised = await commercial.saveCommercial('COSTING', edited, 'Synthetic advanced edit', crypto.randomUUID(), cost);
    await assert.rejects(commercial.saveCommercial('COSTING', edited, 'Stale', crypto.randomUUID(), cost), e => e.response.status === 412);
    assert.equal((await commercial.commercialHistory(cost.id)).results[0].snapshot.input.terms, data.terms);
    const q = editor.editableCommercialInput(revised.snapshot.input); delete q.lines[0].costing; q.lines[0].costing_revision = cost.revision;
    q.lines.push({ ...q.lines[0], variant: process.env.PHASE4B_SECOND_VARIANT, costing_revision: undefined, quantity: '4' });
    const quote = await commercial.saveCommercial('QUOTATION', q, 'Synthetic two-product quote', crypto.randomUUID());
    const order = await commercial.saveCommercial('SALES_ORDER', q, 'Synthetic two-product order', crypto.randomUUID());
    assert.equal(order.snapshot.input.lines.length, 2); assert.equal(order.snapshot.estimate.payable_total, null);
    const ref = (await commercial.allCommercialReferences('/commercial/references/costing-revisions/')).find(v => v.id === cost.revision); assert.ok(ref);
    const policyBody = { policy_type: 'VAT_LED', title: 'Unverified rule', draft_payload: { vat: '18', approved: true }, evidence: [{ reference: 'synthetic:source', description: 'Conflicting client evidence, not approved' }], proposed_effective_date: '2026-11-01' };
    const pkey = crypto.randomUUID(); const policy = await gov.saveProposal('POLICY', policyBody, 'Synthetic proposal', pkey);
    assert.equal((await gov.saveProposal('POLICY', policyBody, 'Synthetic proposal', pkey)).id, policy.id);
    assert.equal(policy.active, false); assert.equal(policy.authority, false);
    const answer = await gov.saveProposal('DECISION', { decision_id: 'P4-01', answer: 'Unverified answer', evidence: policyBody.evidence, linked_policy_revision: policy.revision }, 'Synthetic answer', crypto.randomUUID());
    assert.equal(answer.status, 'PENDING_VERIFICATION');
    const registry = await gov.decisionRegistry(); assert.equal(registry.results[0].baseline_status, 'OPEN'); assert.equal(registry.results[0].conflicting_evidence.length, 3);
    const p2 = await gov.saveProposal('POLICY', { ...policyBody, title: 'Revised proposal' }, 'New evidence', crypto.randomUUID(), policy);
    assert.equal((await gov.proposalHistory(p2)).length, 2);
    assert.equal(answer.content.linked_policy_snapshot.content.title, 'Unverified rule');
    await assert.rejects(api.post(`/commercial/documents/${quote.id}/transition/`, { transition: 'approve', reason: 'Synthetic forbidden approval' }, { headers: { 'If-Match': '"1"', 'Idempotency-Key': crypto.randomUUID() } }), e => e.response.status === 409);
    await assert.rejects(commercial.saveCommercial('QUOTATION', { ...q, vat_rate: '18' }, 'Forbidden tax', crypto.randomUUID()), e => e.response.status === 400);
    const variant = (await api.get(`/finished-goods/${data.lines[0].variant}/`)).data;
    await api.patch(`/finished-goods/${variant.id}/`, { name: 'Changed current master' }, { headers: { 'If-Match': `"${variant.version}"`, 'Idempotency-Key': crypto.randomUUID() } });
    const historical = await commercial.saveCommercial('QUOTATION', q, 'Historical costing after master change', crypto.randomUUID());
    assert.deepEqual(historical.snapshot.input.lines[0].costing_snapshot.source, cost.snapshot);
    await login('other-commercial@example.com');
    assert.equal((await commercial.commercialPage()).count, 0); assert.equal((await gov.proposalRecords('POLICY')).length, 0);
    await assert.rejects(api.get(`/commercial/documents/${quote.id}/`), e => e.response.status === 404);
    console.log('LIVE PHASE4B PASS: multi-component costing, lossless advanced edit, two-product quote/order, references, policies/answers/history, retries, stale/foreign/approval/tax denial, historical linkage.');
  } else {
    const requests = []; api.defaults.adapter = async config => { requests.push(config); return { config, data: { id: 'record', version: 2 }, status: 200, statusText: 'OK', headers: {} }; };
    await gov.saveProposal('POLICY', { title: 'Proposal' }, 'Evidence', 'same-key', { id: 'record', version: 1 });
    assert.equal(requests.at(-1).headers['If-Match'], '"1"'); assert.equal(requests.at(-1).headers['Idempotency-Key'], 'same-key');
    await gov.decisionRegistry(); assert.equal(requests.at(-1).url, '/commercial/decision-registry/');
    api.defaults.adapter = async () => { throw new Error('denied'); }; await assert.rejects(gov.saveProposal('POLICY', {}, 'Synthetic', 'denied'));
    console.log('PASS: advanced editor roundtrip, components/precision/references, unknown-field refusal, comparisons and proposal request contracts.');
  }
} catch (e) { console.error('Phase4B check failed:', e.response?.status ?? '', e.response?.data?.error ?? e.message); process.exitCode = 1; }
finally { await server.close(); }
