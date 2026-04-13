export type ProjectStatus = "created" | "evaluating" | "completed" | "failed" | "archived";

export type RunStatus = "pending" | "running" | "completed" | "failed" | "cancelled";

export type RunStage =
  | "pending"
  | "planning"
  | "collecting_signals"
  | "normalizing_evidence"
  | "enriching_evidence"
  | "clustering_evidence"
  | "scoring"
  | "gate_review"
  | "rendering"
  | "completed"
  | "failed";

export type GateAction = "go" | "conditional_go" | "hold" | "stop";

export type ReportType = "evaluation" | "prd";

export interface OpportunityProject {
  id: string;
  topic_id: string;
  title: string;
  input_topic: string;
  target_market?: string | null;
  target_user_hint?: string | null;
  constraints: Record<string, unknown>;
  status: ProjectStatus;
  latest_evaluation_run_id?: string | null;
  latest_report_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface EvaluationRun {
  id: string;
  project_id: string;
  topic_id: string;
  status: RunStatus;
  stage: RunStage;
  progress: number;
  message: string;
  plan: Record<string, unknown>;
  budget: Record<string, unknown>;
  error?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
}

export interface EvidenceItem {
  id: string;
  evaluation_run_id: string;
  project_id: string;
  raw_signal_id?: string | null;
  cluster_id?: string | null;
  dimension: string;
  title: string;
  content: string;
  summary: string;
  url?: string | null;
  source_platform: string;
  source_type: string;
  content_type: string;
  author?: string | null;
  published_at?: string | null;
  fetched_at: string;
  engagement_metrics: Record<string, number>;
  hotness_score: number;
  sentiment_label: string;
  sentiment_score: number;
  stance_label: string;
  credibility_score: number;
  freshness_score: number;
  relevance_score: number;
  dedupe_hash: string;
  status: string;
  tags: string[];
}

export interface ScoreLedger {
  id: string;
  evaluation_run_id: string;
  dimension: string;
  score: number;
  confidence: number;
  weight: number;
  rationale: string;
  positive_evidence_ids: string[];
  negative_evidence_ids: string[];
  missing_evidence: string[];
  assumptions: string[];
  created_at: string;
}

export interface GateDecision {
  id: string;
  evaluation_run_id: string;
  project_id: string;
  action: GateAction;
  total_score: number;
  confidence: number;
  reason: string;
  next_steps: string[];
  created_at: string;
}

export interface EvaluationReport {
  id: string;
  evaluation_run_id: string;
  project_id: string;
  report_type: ReportType;
  title: string;
  markdown_path: string;
  structured_data: Record<string, unknown>;
  evidence_refs: string[];
  status: string;
  created_at: string;
}

export interface EvaluationView {
  project: OpportunityProject;
  run: EvaluationRun;
  plan: Record<string, unknown>;
  evidence_summary: {
    raw_signal_count: number;
    valid_evidence_count: number;
    cluster_count: number;
    source_diversity: number;
    avg_credibility: number;
    avg_hotness: number;
  };
  score_summary: {
    total_score?: number | null;
    overall_confidence?: number | null;
    dimensions: ScoreLedger[];
  };
  gate_decision?: GateDecision | null;
  reports: EvaluationReport[];
  llm_log_count: number;
}

export interface LlmCallLog {
  id: string;
  evaluation_run_id: string;
  provider: string;
  model: string;
  purpose: string;
  dimension?: string | null;
  query?: string | null;
  status: string;
  event_count: number;
  reasoning_text: string;
  output_text: string;
  error?: string | null;
  created_at: string;
  updated_at: string;
  raw_event_count?: number;
}

export interface EvaluationEvent {
  id: string;
  evaluation_run_id: string;
  event_type: string;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface ConfigStatus {
  llm_provider: string;
  search_provider: string;
  search: {
    provider: string;
    max_workers: number;
    per_dimension_workers: number;
    evidence_per_dimension: number;
  };
  ark: {
    configured: boolean;
    base_url: string;
    model: string;
    timeout_seconds: number;
    stream: boolean;
    enable_tool_choice: boolean;
    web_search: {
      limit: number;
      max_keyword: number;
      user_location: Record<string, unknown>;
    };
  };
}

export interface ApiListProjectsResponse {
  projects: OpportunityProject[];
}

export interface ApiProjectResponse {
  project: OpportunityProject;
}

export interface ApiRunResponse {
  run: EvaluationRun;
}

export interface ApiEvidenceResponse {
  evidence: EvidenceItem[];
}

export interface ApiScoresResponse {
  scores: ScoreLedger[];
}

export interface ApiLogsResponse {
  logs: LlmCallLog[];
}

export interface ApiReportResponse {
  report: EvaluationReport;
}
