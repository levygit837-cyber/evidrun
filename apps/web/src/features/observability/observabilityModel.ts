import type {
  CheckpointRecordDto,
  EvaluationRecordDto,
  Run,
  RunDetail,
  RunEvent,
} from "../../types";
import { runStatusLabels } from "../../productLanguage";

export const ACTIVE_RUN_STATUSES = new Set(["queued", "preparing", "running", "evaluating"]);
export const ATTENTION_RUN_STATUSES = new Set([
  "failed",
  "budget_exhausted",
  "cancelled",
  "guardrail_stopped",
]);
export const TERMINAL_RUN_STATUSES = new Set([
  "completed",
  "failed",
  "budget_exhausted",
  "cancelled",
  "guardrail_stopped",
]);

export type RunStatusFilter =
  | "all"
  | "active"
  | "completed"
  | "attention"
  | "queued"
  | "preparing"
  | "running"
  | "evaluating"
  | "failed"
  | "budget_exhausted";

export type RunPeriodFilter = "all" | "24h" | "7d" | "30d";

export interface ObservabilitySearchState {
  q?: string;
  status?: string;
  period?: string;
  run?: string;
}

export function normalizeStatusFilter(value: string | undefined): RunStatusFilter {
  const accepted: RunStatusFilter[] = [
    "all",
    "active",
    "completed",
    "attention",
    "queued",
    "preparing",
    "running",
    "evaluating",
    "failed",
    "budget_exhausted",
  ];
  return accepted.includes(value as RunStatusFilter) ? (value as RunStatusFilter) : "all";
}

export function normalizePeriodFilter(value: string | undefined): RunPeriodFilter {
  return value === "24h" || value === "7d" || value === "30d" ? value : "all";
}

function statusMatches(runStatus: string, filter: RunStatusFilter): boolean {
  if (filter === "all") return true;
  if (filter === "active") return ACTIVE_RUN_STATUSES.has(runStatus);
  if (filter === "attention") return ATTENTION_RUN_STATUSES.has(runStatus);
  return runStatus === filter;
}

export function filterRuns(
  runs: Run[],
  search: ObservabilitySearchState,
  now = Date.now(),
): Run[] {
  const query = search.q?.trim().toLocaleLowerCase("pt-BR") ?? "";
  const status = normalizeStatusFilter(search.status);
  const period = normalizePeriodFilter(search.period);
  const periodMs = period === "24h" ? 86_400_000 : period === "7d" ? 604_800_000 : 2_592_000_000;

  return runs.filter((run) => {
    if (!statusMatches(run.status, status)) return false;
    if (period !== "all") {
      const createdAt = Date.parse(run.created_at);
      if (!Number.isFinite(createdAt) || now - createdAt > periodMs) return false;
    }
    if (!query) return true;
    return [
      run.id,
      run.experiment_revision_id,
      run.variant_id,
      run.status,
      run.runner,
      run.run_spec_id,
      run.admission_id,
      run.context_hash,
    ]
      .filter((value): value is string => Boolean(value))
      .some((value) => value.toLocaleLowerCase("pt-BR").includes(query));
  });
}

export function summarizeRuns(runs: Run[]) {
  return {
    all: runs.length,
    active: runs.filter((run) => ACTIVE_RUN_STATUSES.has(run.status)).length,
    completed: runs.filter((run) => run.status === "completed").length,
    attention: runs.filter((run) => ATTENTION_RUN_STATUSES.has(run.status)).length,
  };
}

export function sortEvents(events: RunEvent[]): RunEvent[] {
  return [...events].sort(
    (left, right) => left.sequence - right.sequence || left.event_id.localeCompare(right.event_id),
  );
}

export function mergeEvents(current: RunEvent[], incoming: RunEvent[]): RunEvent[] {
  const byIdentity = new Map<string, RunEvent>();
  for (const event of [...current, ...incoming]) {
    byIdentity.set(`${event.sequence}:${event.event_id}`, event);
  }
  return sortEvents([...byIdentity.values()]);
}

export function getForensicTurnWindow(
  events: RunEvent[],
  selectedEventId: string,
): RunEvent[] | null {
  const ordered = sortEvents(events);
  const selectedIndex = ordered.findIndex((event) => event.event_id === selectedEventId);
  if (selectedIndex < 0) return null;

  let start = -1;
  for (let index = selectedIndex; index >= 0; index -= 1) {
    if (ordered[index]?.type === "subject.invoked") {
      start = index;
      break;
    }
    if (index !== selectedIndex && ordered[index]?.type === "subject.responded") break;
  }
  if (start < 0) return null;

  let end = -1;
  for (let index = start + 1; index < ordered.length; index += 1) {
    if (ordered[index]?.type === "subject.responded") {
      end = index;
      break;
    }
    if (ordered[index]?.type === "subject.invoked") return null;
  }
  if (end < selectedIndex || end < 0) return null;
  return ordered.slice(start, end + 1);
}

export type EvidenceOrigin = "event" | "evaluation" | "checkpoint";

export interface EvidenceProjection {
  ref: string;
  digest?: string;
  mediaType?: string;
  origin: EvidenceOrigin;
  role: string;
  sourceId: string;
  sequence?: number;
  timestamp?: string;
  classification?: string;
  gateStatus?: string;
}

interface WalkedReference {
  ref: string;
  role: string;
  digest?: string;
  mediaType?: string;
  classification?: string;
}

function walkReferences(
  value: unknown,
  path: string,
  emit: (reference: WalkedReference) => void,
): void {
  if (typeof value === "string") {
    if (/^(run|event|artifact):/.test(value)) emit({ ref: value, role: path || "reference" });
    return;
  }
  if (Array.isArray(value)) {
    value.forEach((item, index) => walkReferences(item, `${path}[${index}]`, emit));
    return;
  }
  if (value && typeof value === "object") {
    const record = value as Record<string, unknown>;
    if (typeof record.artifact_id === "string") {
      emit({
        ref: record.artifact_id,
        role: path || "artifact_ref",
        digest: typeof record.digest === "string" ? record.digest : undefined,
        mediaType: typeof record.media_type === "string" ? record.media_type : undefined,
        classification: typeof record.classification === "string" ? record.classification : undefined,
      });
      return;
    }
    Object.entries(value).forEach(([key, item]) =>
      walkReferences(item, path ? `${path}.${key}` : key, emit),
    );
  }
}

export function projectEvidenceReferences(
  events: RunEvent[],
  evaluations: EvaluationRecordDto[],
  checkpoints: unknown[],
): EvidenceProjection[] {
  const projected: EvidenceProjection[] = [];
  for (const event of events) {
    walkReferences(event.payload, "payload", (reference) => projected.push({
      ref: reference.ref,
      digest: reference.digest,
      mediaType: reference.mediaType,
      origin: "event",
      role: reference.role,
      sourceId: event.event_id,
      sequence: event.sequence,
      timestamp: event.occurred_at_utc,
      classification: reference.classification ?? event.classification,
    }));
  }
  for (const evaluation of evaluations) {
    evaluation.dimension_values.forEach((dimension) => {
      dimension.evidence_refs.forEach(({ ref }) => projected.push({
        ref,
        origin: "evaluation",
        role: `dimension:${dimension.dimension_id}`,
        sourceId: evaluation.record_id,
        timestamp: evaluation.created_at_utc,
        gateStatus: evaluation.gate_status,
      }));
    });
  }
  checkpoints.forEach((checkpoint, index) => {
    const record = checkpoint as Record<string, unknown>;
    walkReferences(record, "checkpoint", (reference) => projected.push({
      ref: reference.ref,
      digest: reference.digest,
      mediaType: reference.mediaType,
      origin: "checkpoint",
      role: reference.role,
      sourceId: typeof record.checkpoint_id === "string" ? record.checkpoint_id : `checkpoint:${index + 1}`,
      sequence: typeof record.up_to_event_sequence === "number" ? record.up_to_event_sequence : undefined,
      timestamp: typeof record.created_at_utc === "string" ? record.created_at_utc : undefined,
      classification: reference.classification,
    }));
  });
  return projected.sort((left, right) =>
    left.origin.localeCompare(right.origin) || left.sourceId.localeCompare(right.sourceId) || left.ref.localeCompare(right.ref),
  );
}

export function correlateToolEvents(events: RunEvent[]): Map<string, "complete" | "orphan-terminal"> {
  const called = new Set<string>();
  const terminals: Array<{ eventId: string; callId: string }> = [];
  for (const event of events) {
    const callId = typeof event.payload.call_id === "string" ? event.payload.call_id : null;
    if (!callId) continue;
    if (event.type === "tool.called") called.add(callId);
    if (["tool.completed", "tool.denied", "tool.failed"].includes(event.type)) {
      terminals.push({ eventId: event.event_id, callId });
    }
  }
  const status = new Map<string, "complete" | "orphan-terminal">();
  for (const event of events) {
    const callId = typeof event.payload.call_id === "string" ? event.payload.call_id : null;
    if (event.type === "tool.called" && callId && terminals.some((item) => item.callId === callId)) {
      status.set(event.event_id, "complete");
    }
  }
  terminals.forEach((terminal) => status.set(
    terminal.eventId,
    called.has(terminal.callId) ? "complete" : "orphan-terminal",
  ));
  return status;
}

export function cleanSearchState(search: ObservabilitySearchState): ObservabilitySearchState {
  return Object.fromEntries(
    Object.entries(search).filter(([, value]) => typeof value === "string" && value.length > 0),
  );
}

export interface DetailData {
  run: RunDetail;
  events: RunEvent[];
  evaluations: EvaluationRecordDto[];
  checkpoints: CheckpointRecordDto[];
}

export const statusLabels = runStatusLabels;

export function statusTone(status: string): string {
  if (status === "completed") return "success";
  if (ATTENTION_RUN_STATUSES.has(status)) return "danger";
  if (status === "running" || status === "evaluating") return "info";
  return "neutral";
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "Não registrado";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(date);
}

export function formatDuration(run: Run): string {
  if (!run.completed_at) return ACTIVE_RUN_STATUSES.has(run.status) ? "Em curso" : "Não registrado";
  const duration = Date.parse(run.completed_at) - Date.parse(run.created_at);
  if (!Number.isFinite(duration) || duration < 0) return "Não registrado";
  if (duration < 1_000) return `${duration} ms`;
  return `${(duration / 1_000).toFixed(1)} s`;
}

export function shortId(value: string | null | undefined): string {
  if (!value) return "Não registrado";
  return value.length > 28 ? `${value.slice(0, 16)}…${value.slice(-8)}` : value;
}

export type ListFailureKind = "disconnected" | "endpoint";

/**
 * Copy for a failed Run list query. A fetch-level `TypeError` means the backend was never
 * reached; any other rejection came from a backend that answered.
 */
export const listFailureCopy: Record<
  ListFailureKind,
  { connection: string; title: string; detail: string }
> = {
  disconnected: {
    connection: "Backend desconectado",
    title: "Backend desconectado",
    detail: "Não foi possível alcançar o backend local.",
  },
  endpoint: {
    connection: "Falha no endpoint",
    title: "Falha no endpoint de Runs",
    detail: "O backend respondeu, mas a lista de Runs falhou.",
  },
};
