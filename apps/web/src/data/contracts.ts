import type {
  BootstrapDemoResult,
  CheckpointRecordDto,
  DataMode,
  EvaluationRecordDto,
  ProviderProfile,
  Run,
  RunDetail,
  RunEvent,
} from "../types";

export type LabUiEvent =
  | { type: "status"; source: DataMode; label: string }
  | {
      type: "tool";
      source: DataMode;
      id: string;
      name: string;
      status: "running" | "completed" | "failed";
      durationMs?: number;
      argumentsSummary?: string;
      resultSummary?: string;
    }
  | { type: "message"; source: DataMode; content: string }
  | { type: "error"; source: DataMode; message: string }
  | { type: "done"; source: DataMode };

export interface LaboratoryAdapter {
  readonly mode: DataMode;
  send(input: string, signal: AbortSignal): AsyncIterable<LabUiEvent>;
}

export interface CreationAdapter {
  bootstrapCanonicalDemo(): Promise<BootstrapDemoResult>;
}

export type RunStreamState = "connecting" | "open" | "reconnecting" | "closed";

export interface RunEventStream {
  subscribe(
    runId: string,
    callbacks: {
      onEvent(event: RunEvent): void;
      onState(state: RunStreamState): void;
      onError(error: Error): void;
    },
  ): () => void;
}

export interface ObservabilityAdapter {
  listRuns(): Promise<Run[]>;
  getRun(runId: string): Promise<RunDetail>;
  getEvents(runId: string): Promise<RunEvent[]>;
  getEvaluations(runId: string): Promise<EvaluationRecordDto[]>;
  getCheckpoints(runId: string): Promise<CheckpointRecordDto[]>;
  getProvider(): Promise<ProviderProfile>;
  exportRunBundle(runId: string): Promise<{
    path: string;
    run_id: string;
    schema_version: "3" | "4";
  }>;
  /**
   * Run the same RunSpec again, as a new Run with `retry_of` declared.
   *
   * Not a resumption: the original Run stays terminal and untouched. Admission happens inside,
   * because it resolves inventory rather than asking a human for anything.
   */
  retryRun(runId: string, runSpecId: string): Promise<{ run_id: string }>;
  readonly stream: RunEventStream;
}
