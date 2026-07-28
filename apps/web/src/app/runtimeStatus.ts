import type { BackendState, ExecutorState, Run } from "../types";

/** Run statuses that are waiting on the executor rather than on a decision. */
const PENDING_RUN_STATUSES = new Set(["queued", "preparing", "running", "evaluating"]);

export type RuntimeTone = "neutral" | "info" | "success" | "warning" | "danger";

/**
 * Colour for one plane's status.
 *
 * `stopped` is a warning rather than a danger: outside the desktop shell there is no
 * supervised executor at all, and reporting that as an error would cry wolf in the browser.
 */
export function planeTone(status: BackendState["status"] | ExecutorState["status"]): RuntimeTone {
  if (status === "ready") return "success";
  if (status === "failed") return "danger";
  return "warning";
}

/**
 * How many Runs are waiting for an executor to pick them up.
 *
 * Derived from the Run list the workspace already fetches — the queue is never read through
 * the desktop bridge, because Electron Main must not open the database.
 */
export function pendingRunCount(runs: Run[]): number {
  return runs.filter((run) => PENDING_RUN_STATUSES.has(run.status)).length;
}

export interface RuntimeAlert {
  tone: "warning" | "danger";
  title: string;
  detail: string;
  action: "restart-executor" | "restart-backend" | null;
}

/**
 * The banner to show, or `null` when nothing needs saying.
 *
 * The invariant this exists for: an executor that died with Runs still queued must never look
 * like a healthy app. A stalled executor with an empty queue is worth a quiet status line, not
 * an interruption — so the banner stays silent until work is actually stuck.
 *
 * A dead backend outranks a dead executor, because without the API nothing is readable and the
 * queue count on screen cannot be trusted either.
 */
export function runtimeAlert(
  backend: BackendState,
  executor: ExecutorState,
  pendingRuns: number,
): RuntimeAlert | null {
  if (backend.status === "failed") {
    return {
      tone: "danger",
      title: "Backend local indisponível",
      detail:
        backend.message ??
        "A API local parou. Evidência e Runs ficam ilegíveis até que ela volte.",
      action: "restart-backend",
    };
  }
  if (executor.status === "failed" && pendingRuns > 0) {
    return {
      tone: "danger",
      title: describeStalledQueue(pendingRuns),
      detail:
        "O executor de Runs parou. Nenhuma Run avança até que ele volte; a evidência já gravada continua legível.",
      action: "restart-executor",
    };
  }
  if (executor.status === "failed") {
    return {
      tone: "warning",
      title: "Executor de Runs parado",
      detail:
        executor.message ??
        "Nenhuma Run está aguardando, mas nada será executado até que o executor volte.",
      action: "restart-executor",
    };
  }
  if (executor.status !== "ready" && pendingRuns > 0) {
    return {
      tone: "warning",
      title: describeStalledQueue(pendingRuns),
      detail: "O executor de Runs ainda não está pronto.",
      action: null,
    };
  }
  return null;
}

function describeStalledQueue(pendingRuns: number): string {
  return pendingRuns === 1 ? "1 Run aguardando execução" : `${pendingRuns} Runs aguardando execução`;
}
