import { describe, expect, it } from "vitest";
import type { RunEvent } from "../../types";
import {
  attemptSummary,
  describeAttempts,
  isAnomaly,
  runMetrics,
  runOutcome,
} from "./runOutcome";

function event(type: string, payload: Record<string, unknown> = {}): RunEvent {
  return { type, payload } as RunEvent;
}

const responded = event("subject.responded", {
  metadata: [
    { key: "input_tokens", value: 1240 },
    { key: "output_tokens", value: 380 },
    { key: "tool_calls", value: 3 },
  ],
});

describe("run outcome", () => {
  it("reads the goal state and cause from the terminal event", () => {
    const outcome = runOutcome([
      event("run.running"),
      event("run.failed", {
        goal_result: { goal_mode: "goal_state", state: "not_assessable" },
        terminal_cause: "Subject response cannot be deterministically recovered",
      }),
    ]);
    expect(outcome.goalState).toBe("not_assessable");
    expect(outcome.terminalCause).toContain("deterministically");
  });

  it("reports nothing for a Run still running", () => {
    expect(runOutcome([event("run.running")])).toEqual({ goalState: null, terminalCause: null });
  });

  it("separates absence of a result from a negative one", () => {
    // Counting an indeterminate invocation as a wrong answer would blame the Subject for
    // infrastructure failure.
    const anomaly = runOutcome([
      event("run.failed", { goal_result: { state: "not_assessable" }, terminal_cause: "x" }),
    ]);
    const wrong = runOutcome([
      event("run.completed", { goal_result: { state: "not_achieved" }, terminal_cause: "x" }),
    ]);
    expect(isAnomaly(anomaly)).toBe(true);
    expect(isAnomaly(wrong)).toBe(false);
  });

  it("survives a terminal payload without a goal result", () => {
    expect(runOutcome([event("run.cancelled", {})]).goalState).toBeNull();
  });
});

describe("run metrics", () => {
  it("reads tokens and tool calls off the response metadata", () => {
    expect(runMetrics([responded])).toEqual({
      inputTokens: 1240,
      outputTokens: 380,
      toolCalls: 3,
    });
  });

  it("still reports what a failed Run consumed", () => {
    // The ledger is append-only, so a Run that died mid-flight kept its counters.
    const metrics = runMetrics([
      responded,
      event("run.failed", { goal_result: { state: "not_assessable" }, terminal_cause: "x" }),
    ]);
    expect(metrics.inputTokens).toBe(1240);
  });

  it("reports nothing when the Subject never answered", () => {
    expect(runMetrics([event("run.running")])).toEqual({
      inputTokens: null,
      outputTokens: null,
      toolCalls: null,
    });
  });

  it("ignores metadata that is not a numeric pair list", () => {
    expect(runMetrics([event("subject.responded", { metadata: "nope" })]).toolCalls).toBeNull();
  });
});

describe("attempt summary", () => {
  it("describes a single clean attempt", () => {
    expect(describeAttempts(attemptSummary(["completed"]))).toBe("1 (concluído)");
  });

  it("makes a resumption readable as a resumption", () => {
    // An expired lease creates another attempt on the same Run, never a new Run. Showing the
    // count is what lets a researcher drop the Run from a strict comparison.
    expect(describeAttempts(attemptSummary(["expired", "completed"]))).toBe(
      "2 (1 expirado, 1 concluído)",
    );
  });

  it("counts repeated statuses together", () => {
    expect(describeAttempts(attemptSummary(["expired", "expired", "completed"]))).toBe(
      "3 (2 expirado, 1 concluído)",
    );
  });

  it("says so when there is no attempt at all", () => {
    expect(describeAttempts(attemptSummary([]))).toBe("Nenhum");
  });
});
