import type {
  ChatRequest,
  ChatResponse,
  LoginRequest,
  MonitorRecentResponse,
  MonitorSummaryResponse,
  SignupRequest,
  TokenResponse,
} from "@/types/api";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

class ApiError extends Error {
  status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init.headers ?? {}),
    },
  });

  if (!response.ok) {
    let message = `HTTP ${response.status}`;
    try {
      const data = (await response.json()) as { detail?: string };
      if (data?.detail) {
        message = data.detail;
      }
    } catch {
      // no-op
    }
    throw new ApiError(message, response.status);
  }

  return (await response.json()) as T;
}

export async function login(payload: LoginRequest): Promise<TokenResponse> {
  return request<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function signup(payload: SignupRequest): Promise<TokenResponse> {
  return request<TokenResponse>("/auth/signup", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function postChat(payload: ChatRequest, token: string): Promise<ChatResponse> {
  return request<ChatResponse>("/chat", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  });
}

export async function fetchMonitorSummary(token: string): Promise<MonitorSummaryResponse> {
  return request<MonitorSummaryResponse>("/monitor/summary", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function fetchMonitorRecent(token: string, limit = 20): Promise<MonitorRecentResponse> {
  return request<MonitorRecentResponse>(`/monitor/recent?limit=${limit}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export { ApiError, API_BASE_URL };
