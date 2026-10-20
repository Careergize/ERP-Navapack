import axios from "axios";
import { clearSession, readToken, replaceTokens } from './authSession';

// Point this at your DRF backend. Injected via .env as VITE_API_BASE_URL
// so the same build can target dev/staging/prod without a code change.
const configuredBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? (import.meta.env.DEV ? "http://localhost:8000/api/v1" : "/api/v1")).replace(/\/+$/, '');
// Preserve existing environment files while upgrading the legacy Django prefix.
const apiBaseUrl = configuredBaseUrl.endsWith('/api') ? `${configuredBaseUrl}/v1` : configuredBaseUrl;

export const api = axios.create({
  baseURL: apiBaseUrl,
});

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access: string;
  refresh: string;
  user?: {
    id: string | number;
    name?: string;
    username?: string;
    email?: string;
    role?: string;
    roles?: string[];
    permissions?: string[];
    is_master_admin?: boolean;
    department?: string;
  };
}

export async function logoutRequest() {
  const refresh = readToken('navapack_refresh');
  if (refresh) await api.post('/auth/logout/', { refresh }, { timeout: 15000 });
}

export async function loginRequest(credentials: LoginRequest): Promise<LoginResponse> {
  const { data } = await api.post<LoginResponse>("/auth/login/", credentials);
  return data;
}

api.interceptors.request.use((config) => {
  const token = readToken('navapack_access');
  if (token && !config.url?.startsWith('/auth/login/')) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let refreshPromise: Promise<string> | null = null;
export function refreshAccessToken(): Promise<string> {
  if (refreshPromise) return refreshPromise;
  const refresh = readToken('navapack_refresh');
  if (!refresh) { clearSession(); return Promise.reject(new Error('Session expired. Please sign in again.')); }
  refreshPromise = axios.post<{ access: string; refresh?: string }>(`${apiBaseUrl}/auth/refresh/`, { refresh }, { timeout: 15000 })
    .then(({ data }) => {
      if (readToken('navapack_refresh') !== refresh) throw new Error('Session changed during refresh.');
      replaceTokens(data.access, data.refresh ?? refresh);
      return data.access;
    })
    .catch(error => {
      if (axios.isAxiosError(error) && [400, 401, 403].includes(error.response?.status ?? 0) && readToken('navapack_refresh') === refresh) clearSession();
      throw error;
    })
    .finally(() => { refreshPromise = null; });
  return refreshPromise;
}

export async function currentUserRequest() {
  // Existing sessions may have a refresh token but no access token.
  if (!readToken('navapack_access') && readToken('navapack_refresh')) await refreshAccessToken();
  const { data } = await api.get<NonNullable<LoginResponse['user']>>('/auth/me/', { timeout: 15000 });
  return data;
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const config = error.config as (import('axios').InternalAxiosRequestConfig & { _authRetry?: boolean }) | undefined;
    if (error.response?.status === 401 && config && (readToken('navapack_access') || readToken('navapack_refresh')) && (!config.url?.startsWith('/auth/') || config.url === '/auth/me/')) {
      if (config._authRetry) { clearSession(); throw error; }
      config._authRetry = true;
      const current = readToken('navapack_access');
      // Another in-flight request may already have renewed this stale token.
      const token = current && config.headers.Authorization !== `Bearer ${current}` ? current : await refreshAccessToken();
      config.headers.Authorization = `Bearer ${token}`;
      return api.request(config);
    }
    return Promise.reject(error);
  }
);
