import type {
  BackendConnection,
  BootstrapDemoResult,
  CheckpointRecordDto,
  DashboardData,
  EvaluationRecordDto,
  ProviderProfile,
  Run,
  RunDetail,
  RunEvent,
} from "../types";
import type { RunEventStream, RunStreamState } from "../data/contracts";
import type { TriageError } from "../generated/contracts";

let cachedConnection: BackendConnection | null = null;
let pendingConnection: Promise<BackendConnection> | null = null;

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly detail: string,
  ) {
    super(`API ${status}: ${detail}`);
  }
}

/**
 * A refusal that keeps its code reachable after the client turns it into an `Error`.
 *
 * Rendering the reason into a sentence and discarding the code forced the console to guess
 * the cause back out of message text. The code travels with the message instead.
 */
export class RefusalError extends Error {
  constructor(
    message: string,
    public readonly triage: TriageError | null,
    public readonly status: number,
  ) {
    super(message);
  }
}

/** Read a `TriageError` out of a response body, or return null when there is none. */
export function triageErrorOf(detail: string): TriageError | null {
  try {
    const body: unknown = JSON.parse(detail);
    if (!body || typeof body !== "object") return null;
    const candidate = "detail" in body ? (body as { detail: unknown }).detail : body;
    const nested =
      candidate && typeof candidate === "object" && "error" in candidate
        ? (candidate as { error: unknown }).error
        : candidate;
    if (!nested || typeof nested !== "object") return null;
    const typed = nested as Partial<TriageError>;
    return typeof typed.code === "string" && typeof typed.phase === "string"
      ? (nested as TriageError)
      : null;
  } catch {
    return null;
  }
}

/**
 * Turn a refused admission into a sentence, falling back to the status when it cannot be read.
 *
 * The rejection body carries a typed error with a message and the requirements that were missing;
 * showing the serialized JSON instead would put contract internals on screen.
 */
export function admissionRefusal(error: ApiError): string {
  try {
    const body = JSON.parse(error.detail) as {
      decision?: string;
      missing_requirements?: string[];
      error?: { message?: string };
    };
    const reason = body.error?.message ?? body.decision ?? `HTTP ${error.status}`;
    const missing = body.missing_requirements?.length
      ? ` Requisitos ausentes: ${body.missing_requirements.join(", ")}.`
      : "";
    return `A admissão recusou este RunSpec: ${reason}.${missing}`;
  } catch {
    return `A admissão recusou este RunSpec (HTTP ${error.status}).`;
  }
}

export function invalidateBackendConnection(): void {
  cachedConnection = null;
  pendingConnection = null;
}

async function connection(): Promise<BackendConnection> {
  if (cachedConnection) return cachedConnection;
  if (pendingConnection) return pendingConnection;
  pendingConnection = window.evidrunDesktop
    ? window.evidrunDesktop.getBackendConnection()
    : Promise.resolve({ baseUrl: "", token: "", instanceId: "browser" });
  try {
    cachedConnection = await pendingConnection;
    return cachedConnection;
  } finally {
    pendingConnection = null;
  }
}

async function authenticatedHeaders(init?: RequestInit): Promise<Headers> {
  const backend = await connection();
  const headers = new Headers(init?.headers);
  if (init?.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  if (backend.token) headers.set("Authorization", `Bearer ${backend.token}`);
  return headers;
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const backend = await connection();
  const headers = await authenticatedHeaders(init);
  const response = await fetch(`${backend.baseUrl}${path}`, { ...init, headers });
  if (!response.ok) {
    const detail = await response.text();
    throw new ApiError(response.status, detail);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  dashboard: () => apiFetch<DashboardData>("/api/v1/dashboard"),
  defaultProvider: () => apiFetch<ProviderProfile>("/api/v1/providers/default"),
  bootstrapDemo: () =>
    apiFetch<BootstrapDemoResult>("/api/v1/demo/bootstrap", { method: "POST" }),
  runs: () => apiFetch<Run[]>("/api/v1/runs"),
  /**
   * Resolve inventory and capabilities for a RunSpec.
   *
   * A rejection answers 4xx with the decision in the body, so `apiFetch` throws before the caller
   * can inspect `decision`. The reason is unwrapped into a sentence for the user, and the named
   * refusal travels alongside it so the console classifies by code instead of by message text.
   */
  admitRunSpec: async (runSpecId: string) => {
    try {
      return await apiFetch<{ id: string; decision: string }>(
        `/api/v1/run-specs/${encodeURIComponent(runSpecId)}/admit`,
        { method: "POST" },
      );
    } catch (error) {
      if (!(error instanceof ApiError)) throw error;
      throw new RefusalError(admissionRefusal(error), triageErrorOf(error.detail), error.status);
    }
  },
  /**
   * Enqueue a fresh Run derived from one that already finished.
   *
   * A retry needs an AdmissionRecord created after the source Run went terminal, so callers admit
   * first. That admission is inventory resolution, not human approval — the RunSpec is unchanged
   * and no revision is accepted — which is why it can hide behind one user action. The result is a
   * new Run carrying `retry_of`, never a continuation of the original.
   */
  retryRun: (runId: string, admissionId: string, idempotencyKey: string) =>
    apiFetch<{ run_id: string; retry_of: string | null; status: string }>(
      `/api/v1/runs/${encodeURIComponent(runId)}/retries`,
      {
        method: "POST",
        headers: { "Idempotency-Key": idempotencyKey },
        body: JSON.stringify({ admission_id: admissionId }),
      },
    ),
  runDetail: (runId: string) => apiFetch<RunDetail>(`/api/v1/runs/${encodeURIComponent(runId)}`),
  runEvents: (runId: string) =>
    apiFetch<RunEvent[]>(`/api/v1/runs/${encodeURIComponent(runId)}/events`),
  runEvaluations: (runId: string) =>
    apiFetch<EvaluationRecordDto[]>(`/api/v1/runs/${encodeURIComponent(runId)}/evaluations`),
  runCheckpoints: (runId: string) =>
    apiFetch<CheckpointRecordDto[]>(`/api/v1/runs/${encodeURIComponent(runId)}/checkpoints`),
  exportRunBundle: (runId: string) =>
    apiFetch<{ path: string; run_id: string; schema_version: "3" }>(
      `/api/v1/runs/${encodeURIComponent(runId)}/evidence-bundles`,
      { method: "POST" },
    ),
  exportComparisonBundle: (comparisonId: string) =>
    apiFetch<{ path: string }>(`/api/v1/evidence-bundles/${encodeURIComponent(comparisonId)}`, {
      method: "POST",
    }),
};

const terminalEvents = new Set([
  "run.completed",
  "run.failed",
  "run.cancelled",
  "run.budget_exhausted",
  "run.guardrail_stopped",
]);

function parseEventBlock(block: string): RunEvent | null {
  const data = block
    .split("\n")
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).trimStart())
    .join("\n");
  if (!data) return null;
  return JSON.parse(data) as RunEvent;
}

async function consumeEventStream(
  runId: string,
  signal: AbortSignal,
  onEvent: (event: RunEvent) => void,
  onState: (state: RunStreamState) => void,
): Promise<void> {
  const backend = await connection();
  const response = await fetch(
    `${backend.baseUrl}/api/v1/runs/${encodeURIComponent(runId)}/stream`,
    {
      headers: backend.token ? { Authorization: `Bearer ${backend.token}` } : undefined,
      signal,
    },
  );
  if (!response.ok || !response.body) {
    throw new ApiError(response.status, await response.text());
  }
  onState("open");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (!signal.aborted) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value, { stream: !done }).replaceAll("\r\n", "\n");
    let boundary = buffer.indexOf("\n\n");
    while (boundary >= 0) {
      const block = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      const event = parseEventBlock(block);
      if (event) onEvent(event);
      boundary = buffer.indexOf("\n\n");
    }
    if (done) return;
  }
}

export const runEventStream: RunEventStream = {
  subscribe(runId, callbacks) {
    const controller = new AbortController();
    const seen = new Set<string>();
    let reconnectAttempt = 0;
    let terminal = false;

    const deliver = (event: RunEvent) => {
      const key = `${event.sequence}:${event.event_id}`;
      if (seen.has(key)) return;
      seen.add(key);
      callbacks.onEvent(event);
      if (terminalEvents.has(event.type)) terminal = true;
    };

    const run = async () => {
      callbacks.onState("connecting");
      while (!controller.signal.aborted && !terminal) {
        try {
          await consumeEventStream(runId, controller.signal, deliver, callbacks.onState);
          if (terminal || controller.signal.aborted) break;
        } catch (error) {
          if (controller.signal.aborted) break;
          callbacks.onError(error instanceof Error ? error : new Error("Falha no stream da Run"));
        }
        callbacks.onState("reconnecting");
        const delay = Math.min(500 * 2 ** reconnectAttempt, 5_000);
        reconnectAttempt += 1;
        await new Promise<void>((resolve) => {
          const timeout = window.setTimeout(resolve, delay);
          controller.signal.addEventListener(
            "abort",
            () => {
              window.clearTimeout(timeout);
              resolve();
            },
            { once: true },
          );
        });
      }
      callbacks.onState("closed");
    };
    void run();
    return () => controller.abort();
  },
};
