import type {
  CheckpointRecord,
  EvaluationRecord,
  RunExecutionAttempt,
  RunExecutionJob,
  RunRecord,
} from "./generated/contracts";

export type DataMode = "live" | "demo" | "integration_pending" | "unavailable";

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
  contract_mode: "study_v1" | "legacy_v1";
  run_spec_id: string | null;
  admission_id: string | null;
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

export interface RunEvent {
  event_id: string;
  schema_version: "1";
  run_id: string;
  sequence: number;
  type: string;
  occurred_at_utc: string;
  actor_type: string;
  actor_id: string;
  classification: string;
  payload: Record<string, unknown>;
  correlation_id: string | null;
  causation_id: string | null;
  prev_event_hash: string | null;
  event_hash: string;
}

export type EvaluationRecordDto = EvaluationRecord & { digest: string };
export type CheckpointRecordDto = CheckpointRecord & { checkpoint_hash: string };

export interface RunDetail extends Run {
  record: RunRecord | null;
  events: RunEvent[];
  execution: {
    job: RunExecutionJob & { digest: string };
    attempts: Array<RunExecutionAttempt & { digest: string }>;
  } | null;
  subject_envelope_digest: string | null;
}

export interface BootstrapDemoResult {
  experiment_revision_id: string;
  study_revision: Record<string, unknown>;
  comparison_id: string;
  baseline_run_id: string;
  candidate_run_id: string;
  validity: string;
  context_diff: Record<string, unknown>;
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

export interface ProviderProfile {
  id: string;
  display_name: string;
  api: "openai_responses";
  base_url: string;
  model: string;
  reasoning_effort: "none" | "low" | "medium" | "high" | "max";
  local_only: boolean;
  credential_service: string;
  default: boolean;
  credential_available: boolean;
  credential_source: "environment" | "system_keychain" | null;
}
