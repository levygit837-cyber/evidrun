import type { RunEvent } from "../../types";

/**
 * What a Run's terminal event says, read straight from the ledger.
 *
 * The ledger is the authority on why a Run ended, and none of this reaches the frontend through
 * a DTO — the terminal payload carries `goal_result` and `terminal_cause`, so both are derived
 * from the events the detail view already fetches rather than added to an API response.
 */

const TERMINAL_EVENT_TYPES = new Set([
  "run.completed",
  "run.failed",
  "run.cancelled",
  "run.budget_exhausted",
  "run.guardrail_stopped",
]);

export type GoalState = "achieved" | "partially_achieved" | "not_achieved" | "not_assessable";

export interface RunOutcome {
  /** `goal_state` result, when the terminal event declared one. */
  goalState: GoalState | null;
  terminalCause: string | null;
}

export interface RunMetrics {
  inputTokens: number | null;
  outputTokens: number | null;
  toolCalls: number | null;
}

export interface AttemptSummary {
  total: number;
  /** Counts per attempt status, in the order they should be read. */
  byStatus: Array<{ status: string; count: number }>;
}

function payload(event: RunEvent): Record<string, unknown> {
  return (event.payload ?? {}) as Record<string, unknown>;
}

export function terminalEvent(events: RunEvent[]): RunEvent | null {
  return events.find((event) => TERMINAL_EVENT_TYPES.has(event.type)) ?? null;
}

export function runOutcome(events: RunEvent[]): RunOutcome {
  const event = terminalEvent(events);
  if (!event) return { goalState: null, terminalCause: null };
  const body = payload(event);
  const goalResult = body.goal_result as Record<string, unknown> | undefined;
  const state = goalResult?.state;
  const cause = body.terminal_cause;
  return {
    goalState: typeof state === "string" ? (state as GoalState) : null,
    terminalCause: typeof cause === "string" && cause ? cause : null,
  };
}

/**
 * Whether the Run ended without a gradable result.
 *
 * `not_assessable` is the absence of a result — an indeterminate invocation, a response that
 * could not be recovered, a runtime inconsistency. It is not a negative result, and reading it
 * as one would count infrastructure failures as model failures.
 */
export function isAnomaly(outcome: RunOutcome): boolean {
  return outcome.goalState === "not_assessable";
}

export const goalStateLabels: Record<GoalState, string> = {
  achieved: "Objetivo alcançado",
  partially_achieved: "Objetivo parcialmente alcançado",
  not_achieved: "Objetivo não alcançado",
  not_assessable: "Anomalia (não avaliável)",
};

/**
 * Token and tool-call counts the Subject's response already recorded.
 *
 * These survive a failed Run because the ledger is append-only, so a Run that died still shows
 * what it consumed. `metadata` is a list of `{key, value}` pairs, not an object.
 */
export function runMetrics(events: RunEvent[]): RunMetrics {
  const responded = events.filter((event) => event.type === "subject.responded").at(-1);
  if (!responded) return { inputTokens: null, outputTokens: null, toolCalls: null };
  const entries = payload(responded).metadata;
  const values = new Map<string, unknown>();
  if (Array.isArray(entries)) {
    for (const entry of entries as Array<Record<string, unknown>>) {
      if (typeof entry?.key === "string") values.set(entry.key, entry.value);
    }
  }
  const numeric = (key: string): number | null => {
    const value = values.get(key);
    return typeof value === "number" ? value : null;
  };
  return {
    inputTokens: numeric("input_tokens"),
    outputTokens: numeric("output_tokens"),
    toolCalls: numeric("tool_calls"),
  };
}

export const attemptStatusLabels: Record<string, string> = {
  leased: "em execução",
  completed: "concluído",
  expired: "expirado",
  released: "liberado",
  rejected: "rejeitado",
};

/**
 * How many attempts a Run consumed, and how they ended.
 *
 * An attempt is an operational retry of the same Run — ADR 0014 has an expired lease create a
 * new attempt, never a new Run. Surfacing the count lets a researcher drop a Run from an
 * analysis when strict comparability matters, because a resumed Run inherits only the wall clock
 * budget that was left.
 */
export function attemptSummary(statuses: string[]): AttemptSummary {
  const counts = new Map<string, number>();
  for (const status of statuses) counts.set(status, (counts.get(status) ?? 0) + 1);
  return {
    total: statuses.length,
    byStatus: [...counts].map(([status, count]) => ({ status, count })),
  };
}

export function describeAttempts(summary: AttemptSummary): string {
  if (!summary.total) return "Nenhum";
  if (summary.total === 1 && summary.byStatus.length === 1) {
    return `1 (${attemptStatusLabels[summary.byStatus[0]!.status] ?? summary.byStatus[0]!.status})`;
  }
  const detail = summary.byStatus
    .map(({ status, count }) => `${count} ${attemptStatusLabels[status] ?? status}`)
    .join(", ");
  return `${summary.total} (${detail})`;
}
