import axios from "axios";

// Point this at your DRF backend. Injected via .env as VITE_API_BASE_URL
// so the same build can target dev/staging/prod without a code change.
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? (import.meta.env.DEV ? "http://localhost:8000/api" : "/api");

export const api = axios.create({
  baseURL: apiBaseUrl,
});

export interface LoginRequest {
  username: string;
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
    department?: string;
  };
}

export async function loginRequest(credentials: LoginRequest): Promise<LoginResponse> {
  const { data } = await api.post<LoginResponse>("/auth/login/", credentials);
  return data;
}

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("navapack_access") ?? localStorage.getItem("navapack_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && !window.location.pathname.endsWith("/login")) {
      localStorage.removeItem("navapack_token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);
