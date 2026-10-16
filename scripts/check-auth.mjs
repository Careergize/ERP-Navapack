import assert from 'node:assert/strict';
import axios, { AxiosError } from 'axios';
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
const originalAdapter = axios.defaults.adapter;
try {
  const storage = await server.ssrLoadModule('/src/lib/authSession.ts');
  const { api, currentUserRequest } = await server.ssrLoadModule('/src/lib/api.ts');
  const user = { id: 1, username: 'admin', role: 'admin' };
  const ok = (config, data) => ({ config, data, status: 200, statusText: 'OK', headers: {} });
  const unauthorized = config => { throw new AxiosError('Unauthorized', 'ERR_BAD_REQUEST', config, null, { config, data: {}, status: 401, statusText: 'Unauthorized', headers: {} }); };

  storage.saveTokens('access', 'refresh', false);
  assert.equal(sessionStorage.getItem('navapack_access'), 'access');
  assert.equal(localStorage.getItem('navapack_access'), null);
  api.defaults.adapter = async config => ok(config, user);
  assert.deepEqual(await currentUserRequest(), user); // profile restored using saved tokens

  let refreshes = 0;
  axios.defaults.adapter = async config => { refreshes++; return ok(config, { access: 'new-access', refresh: 'new-refresh' }); };
  api.defaults.adapter = async config => config.headers.Authorization === 'Bearer new-access' ? ok(config, user) : unauthorized(config);
  const profiles = await Promise.all([currentUserRequest(), currentUserRequest()]);
  assert.equal(profiles.length, 2);
  assert.equal(refreshes, 1); // parallel 401s share one rotating refresh request
  assert.equal(storage.readToken('navapack_refresh'), 'new-refresh');
  assert.equal(localStorage.getItem('navapack_access'), null);

  storage.saveTokens('expired', 'persistent-refresh', true);
  assert.equal(sessionStorage.getItem('navapack_access'), null);
  assert.deepEqual(await currentUserRequest(), user);
  assert.equal(localStorage.getItem('navapack_refresh'), 'new-refresh');

  let cleared = 0;
  window.addEventListener(storage.AUTH_CLEARED_EVENT, () => cleared++);
  storage.saveTokens('expired', 'invalid-refresh', true);
  axios.defaults.adapter = async config => unauthorized(config);
  await assert.rejects(currentUserRequest());
  assert.equal(storage.readToken('navapack_access'), null);
  assert.equal(storage.readToken('navapack_refresh'), null);
  assert.equal(cleared, 1);

  storage.saveTokens('expired', 'offline-refresh', false);
  axios.defaults.adapter = async config => { throw new AxiosError('Network unavailable', 'ERR_NETWORK', config); };
  await assert.rejects(currentUserRequest());
  assert.equal(storage.readToken('navapack_refresh'), 'offline-refresh'); // outage does not discard session

  sessionStorage.setItem('navapack_demo_user', '{"id":"demo-admin"}');
  localStorage.setItem('navapack_token', 'legacy');
  storage.clearSession();
  for (const key of ['navapack_access', 'navapack_refresh', 'navapack_demo_user', 'navapack_token', 'navapack_remember']) {
    assert.equal(sessionStorage.getItem(key), null); assert.equal(localStorage.getItem(key), null);
  }
  sessionStorage.setItem('navapack_demo_user', '{"id":"demo-admin"}');
  await assert.rejects(api.get('/job-cards/'));
  assert.notEqual(sessionStorage.getItem('navapack_demo_user'), null); // mock API fallback must not log demo user out
  storage.clearSession();
  console.log('Passed: saved profile restoration, tab/persistent storage, token rotation, shared concurrent refresh, invalid-session cleanup, outage preservation and logout cleanup.');
} finally {
  axios.defaults.adapter = originalAdapter;
  await server.close();
}
