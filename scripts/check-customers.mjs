import assert from 'node:assert/strict';
import { createServer } from 'vite';
import { fileURLToPath } from 'node:url';

class MemoryStorage {
  values = new Map();
  getItem(key) { return this.values.get(key) ?? null; }
  setItem(key, value) { this.values.set(key, String(value)); }
  removeItem(key) { this.values.delete(key); }
}
globalThis.localStorage = new MemoryStorage();
globalThis.sessionStorage = new MemoryStorage();
globalThis.window = new EventTarget();
const server = await createServer({ configFile: false, resolve: { alias: { '@': fileURLToPath(new URL('../src', import.meta.url)) } }, optimizeDeps: { noDiscovery: true }, server: { middlewareMode: true, hmr: false }, appType: 'custom' });
try {
  const { api } = await server.ssrLoadModule('/src/lib/api.ts');
  const customers = await server.ssrLoadModule('/src/lib/customersApi.ts');
  const buyer = { name: 'New buyer', contactPerson: 'Buyer contact', phone: '+916282744675', email: 'buyer@example.com', billingAddress: 'Billing', deliveryAddress: 'Delivery', tin: 'TIN', customerType: 'B2B' };
  await assert.rejects(customers.createCustomer(buyer, crypto.randomUUID()), /backend account/);
  sessionStorage.setItem('navapack_access', 'test-token');
  const record = { id: 7, code: 'CUS-7', ...customers.customerPayload(buyer), is_active: true };
  const responses = [];
  api.defaults.adapter = async config => {
    responses.push(config);
    const data = config.method === 'get'
      ? { results: [{ ...record, id: config.params.page === 1 ? 7 : 8 }], next: config.params.page === 1 ? 'next-page' : null }
      : { ...record, ...JSON.parse(config.data) };
    return { data, status: 200, statusText: 'OK', headers: {}, config };
  };
  const key = crypto.randomUUID();
  const saved = await customers.createCustomer(buyer, key);
  assert.equal(saved.id, 'db:7');
  assert.equal(saved.contactPerson, 'Buyer contact');
  assert.equal(saved.deliveryAddress, 'Delivery');
  assert.equal(JSON.parse(responses[0].data).creation_key, key);
  assert.equal(JSON.parse(responses[0].data).customer_type, 'B2B');
  const loaded = await customers.loadCustomers();
  assert.deepEqual(loaded.map(c => c.id), ['db:7', 'db:8']);
  const edited = await customers.updateCustomer({ ...saved, email: 'changed@example.com' });
  assert.equal(responses.at(-1).url, '/customers/7/');
  assert.equal(responses.at(-1).method, 'patch');
  assert.equal(edited.email, 'changed@example.com');
  await assert.rejects(customers.updateCustomer({ ...saved, id: 'mock-7' }), /saved backend customer/);
  console.log('Passed: customer creation payload and retry key, stable backend identity, all-page loading, master update and explicit demo-save rejection.');
} finally { await server.close(); }
