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
  email: string;
  role: UserRole;
}

export interface TokenResponse {
  access_token: string;
  token_type: "bearer";
}

export interface ChatRequest {
  question: string;
  mode: "dense" | "bm25" | "hybrid";
  k: number;
  language: "ko" | "en";
}

export type ChatIntent = "needs_rag" | "needs_web" | "clarify" | "simple";

export interface SourceItem {
  chunk_id: string | null;
  source: string | null;
  text: string;
  term?: string | null;
  explanation?: string | null;
  related_terms?: string[];
}

export interface ClassifierInfo {
  method: string;
  confidence: number;
}

export interface ChatResponse {
  question: string;
  answer: string;
  retrieved_ids: Array<string | null>;
  sources: SourceItem[];
  intent: ChatIntent;
  routing_reason: string;
  matched_terms: string[];
  classifier: ClassifierInfo;
}

export interface MonitorSummaryItem {
  stage: string;
  count: number;
  success_count: number;
  success_rate: number;
  avg_elapsed_sec: number;
  avg_throughput: number;
  throughput_unit: string;
}

export interface DashboardStageSummary {
  stage_type?: "call_based" | "generation" | "unknown" | string;
  total_rows: number;
  success_count: number;
  fail_count: number;
  avg_elapsed_sec: number;
  success_rate: number;
  throughput: Record<string, number>;
  elapsed_sec?: number;
  attempted_rps?: number | null;
  successful_rps?: number | null;
  result_count?: number | null;
  status?: string | null;
  output_tps?: number | null;
  chars_per_sec?: number | null;
  rpm?: number | null;
  output_tpm?: number | null;
  total_tpm?: number | null;
  input_tokens?: number | null;
  output_tokens?: number | null;
  total_tokens?: number | null;
  token_count_source?: string | null;
}

export interface MonitorSummaryResponse {
  trace_count: number;
  stage_summary: Record<string, MonitorSummaryItem>;
  dashboard_stage_summary: Record<string, DashboardStageSummary>;
  total_rows: number;
  error_rows: number;
  warning_rows: number;
  last_refresh: string;
}

export interface MonitorRecentItem {
  trace_id: string;
  query: string;
  created_at: string;
  metadata: Record<string, unknown>;
  stages: MonitorSummaryItem[];
}

export interface MonitorRecentRow {
  timestamp: string;
  trace_id: string;
  stage: string;
  user_query: string;
  generated_answer: string;
  status: "success" | "fail" | string;
  error_message: string;
  elapsed_sec: number;
  throughput: number;
  attempted_calls_per_sec?: number | null;
  successful_calls_per_sec?: number | null;
  output_tokens_per_sec?: number | null;
  chars_per_sec?: number | null;
  total_tokens?: number | null;
  generation_elapsed_sec?: number | null;
}

export interface MonitorRecentPagingPage {
  page: number;
  label: string;
  start_row: number;
  end_row: number;
}

export interface MonitorRecentPaging {
  limit: number;
  page: number;
  total_rows: number;
  total_pages: number;
  start_row: number;
  end_row: number;
  errors_only: boolean;
  pages: MonitorRecentPagingPage[];
}

export interface MonitorRecentResponse {
  items: MonitorRecentItem[];
  rows: MonitorRecentRow[];
  paging: MonitorRecentPaging;
}

export interface KnowledgeDocument {
  id: string;
  term: string;
  explanation: string;
  relatedTerms: string[];
}

export interface KnowledgeDocumentsResponse {
  items: KnowledgeDocument[];
}
