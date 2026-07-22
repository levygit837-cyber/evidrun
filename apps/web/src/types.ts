export interface Grade {
  id: string;
  score: number;
  passed: boolean;
  rationale: string;
  evidence: string[];
}

export interface ContextSnapshot {
  id: string;
  policy_id: string;
  strategy: "head" | "tail" | "full";
  max_chars: number;
  source_chars: number;
  selected_chars: number;
  selected_content: string;
  omitted: Array<{ start: number; end: number }>;
  content_hash: string;
}

export interface Run {
  id: string;
  experiment_revision_id: string;
  variant_id: string;
  status: string;
  runner: string;
  output: string | null;
  context_hash: string | null;
  created_at: string;
  completed_at: string | null;
  grade: Grade | null;
  context_snapshot: ContextSnapshot | null;
}

export interface Comparison {
  id: string;
  experiment_revision_id: string;
  baseline_run_id: string;
  candidate_run_id: string;
  primary_variable: string;
  validity: string;
  baseline_score: number;
  candidate_score: number;
  delta: number;
  report_markdown: string;
  created_at: string;
}

export interface Experiment {
  id: string;
  experiment_id: string;
  title: string;
  status: string;
  manifest_hash: string;
  manifest: {
    hypothesis: string;
    primary_variable: string;
    evidence_mode: string;
  };
}

export interface ChatSession {
  id: string;
  title: string;
  scope_type: string | null;
  scope_id: string | null;
}

export interface DashboardData {
  workspaces: Array<{ id: string; name: string }>;
  projects: Array<{ id: string; name: string }>;
  experiments: Experiment[];
  runs: Run[];
  comparisons: Comparison[];
  chats: ChatSession[];
  summary: {
    experiments: number;
    runs: number;
    comparisons: number;
    events: number;
  };
}

export interface BackendConnection {
  baseUrl: string;
  token: string;
  instanceId: string;
}

export interface BackendState {
  status: "starting" | "ready" | "failed" | "stopped";
  message?: string;
}

