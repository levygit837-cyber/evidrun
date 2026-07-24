import type { EvaluationRecordDto, Run, RunEvent } from "../../types";

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

function collectReferenceStrings(value: unknown, output: Set<string>): void {
  if (typeof value === "string") {
    if (/^(run|event|artifact):/.test(value)) output.add(value);
    return;
  }
  if (Array.isArray(value)) {
    for (const item of value) collectReferenceStrings(item, output);
    return;
  }
  if (value && typeof value === "object") {
    for (const item of Object.values(value)) collectReferenceStrings(item, output);
  }
}

export function collectEvidenceReferences(
  events: RunEvent[],
  evaluations: EvaluationRecordDto[],
  checkpoints: unknown[],
): string[] {
  const refs = new Set<string>();
  for (const event of events) collectReferenceStrings(event.payload, refs);
  for (const evaluation of evaluations) collectReferenceStrings(evaluation.dimension_values, refs);
  for (const checkpoint of checkpoints) collectReferenceStrings(checkpoint, refs);
  return [...refs].sort((left, right) => left.localeCompare(right));
}

export function cleanSearchState(search: ObservabilitySearchState): ObservabilitySearchState {
  return Object.fromEntries(
    Object.entries(search).filter(([, value]) => typeof value === "string" && value.length > 0),
  );
}
