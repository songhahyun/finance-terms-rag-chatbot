export type UserRole = "user" | "admin";

export interface AuthUser {
  username: string;
  roles: UserRole[];
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface SignupRequest extends LoginRequest {
  role: UserRole;
}

export interface TokenResponse {
  access_token: string;
  token_type: "bearer";
}

export interface ChatRequest {
  question: string;
  mode: string;
  k: number;
  language: "ko" | "en";
}

export interface SourceItem {
  chunk_id: string | null;
  source: string | null;
  text: string;
}

export interface ChatResponse {
  question: string;
  answer: string;
  retrieved_ids: Array<string | null>;
  sources: SourceItem[];
  keywords: string[];
  query_type: string | null;
  route_reason: string | null;
  router_target: string | null;
}

export interface MonitorSummaryItem {
  stage: string;
  count: number;
  success_rate: number;
  avg_elapsed_sec: number;
  avg_throughput: number;
  throughput_unit: string;
}

export interface MonitorSummaryResponse {
  total_queries: number;
  stage_count: number;
  stage_summary: MonitorSummaryItem[];
}

export interface MonitorRecentItem {
  timestamp: string;
  trace_id: string;
  query: string;
  stage: string;
  success: boolean;
  elapsed_sec: number;
  throughput: number;
  throughput_unit: string;
  work_units: number;
  error: string | null;
}

export interface MonitorRecentResponse {
  items: MonitorRecentItem[];
}
