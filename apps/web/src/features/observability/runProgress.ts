import type { ExecutorState, Run } from "../../types";
import type { RunStreamState } from "../../data/contracts";
import { ACTIVE_RUN_STATUSES } from "./observabilityModel";

/**
 * Why a Run that is not finishing is not finishing.
 *
 * Two very different situations used to produce the same error line: a stream that dropped and
 * is reconnecting on its own, and an executor that died so nothing will progress at all. The
 * first resolves itself and deserves a quiet note; the second needs the user to act.
 */
export type RunProgressIssue =
  | { kind: "stream-reconnecting"; message: string }
  | { kind: "stream-failed"; message: string }
  | { kind: "executor-down"; message: string };

export function runProgressIssue({
  run,
  streamState,
  streamError,
  executor,
}: {
  run: Run;
  streamState: RunStreamState;
  streamError: string | null;
  /** Absent outside the desktop shell, where no executor is supervised. */
  executor?: ExecutorState;
}): RunProgressIssue | null {
  const waiting = ACTIVE_RUN_STATUSES.has(run.status);
  // A dead executor outranks a stream problem: reconnecting to a Run that nothing is executing
  // would report the symptom and hide the cause.
  if (executor && waiting && executor.status !== "ready") {
    return {
      kind: "executor-down",
      message:
        executor.status === "failed"
          ? "O executor de Runs parou. Esta Run não avança até que ele volte."
          : "O executor de Runs ainda não está pronto. Esta Run não avança até que ele esteja.",
    };
  }
  if (streamState === "reconnecting") {
    return {
      kind: "stream-reconnecting",
      message: "Reconectando ao stream desta Run. Os eventos já recebidos continuam válidos.",
    };
  }
  if (streamError) {
    return { kind: "stream-failed", message: streamError };
  }
  return null;
}

/** Only a stalled executor is worth an assertive announcement; a stream recovers on its own. */
export function issueTone(issue: RunProgressIssue): "info" | "danger" {
  return issue.kind === "executor-down" ? "danger" : "info";
}
