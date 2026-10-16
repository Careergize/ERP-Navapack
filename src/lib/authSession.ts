export const MOCK_LOGIN_ENABLED = import.meta.env.VITE_ENABLE_MOCK_LOGIN === 'true';
export const AUTH_CLEARED_EVENT = 'navapack-auth-cleared';
const AUTH_KEYS = ['navapack_access', 'navapack_refresh', 'navapack_token', 'navapack_demo_user'];

export function readToken(key: 'navapack_access' | 'navapack_refresh') {
  return sessionStorage.getItem(key) ?? localStorage.getItem(key);
}

export function clearSession() {
  for (const storage of [localStorage, sessionStorage]) {
    for (const key of AUTH_KEYS) storage.removeItem(key);
    storage.removeItem('navapack_remember');
  }
  window.dispatchEvent(new Event(AUTH_CLEARED_EVENT));
}

export function saveTokens(access: string, refresh: string, remember: boolean) {
  for (const storage of [localStorage, sessionStorage]) {
    for (const key of AUTH_KEYS) storage.removeItem(key);
  }
  const storage = remember ? localStorage : sessionStorage;
  storage.setItem('navapack_access', access);
  storage.setItem('navapack_refresh', refresh);
  if (remember) localStorage.setItem('navapack_remember', 'true');
  else localStorage.removeItem('navapack_remember');
}

export function replaceTokens(access: string, refresh: string) {
  const persistent = localStorage.getItem('navapack_refresh') !== null && sessionStorage.getItem('navapack_refresh') === null;
  saveTokens(access, refresh, persistent);
}
