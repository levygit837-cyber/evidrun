import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ObservabilityAdapter } from "../../data/contracts";
import type { ExecutorState, RunDetail, RunEvent } from "../../types";
import { RunDetailPanel } from "./RunDetailPanel";
import type { DetailData } from "./observabilityModel";

function event(type: string, payload: Record<string, unknown> = {}): RunEvent {
  return { type, payload, event_id: type, sequence: 1 } as unknown as RunEvent;
}

const anomalyEvents = [
  event("subject.responded", {
    metadata: [
      { key: "input_tokens", value: 1240 },
      { key: "output_tokens", value: 380 },
      { key: "tool_calls", value: 3 },
    ],
  }),
  event("run.failed", {
    goal_result: { goal_mode: "goal_state", state: "not_assessable" },
    terminal_cause: "Subject response cannot be deterministically recovered",
  }),
];

function detail(overrides: Partial<RunDetail> = {}, events = anomalyEvents): DetailData {
  return {
    run: {
      id: "run:anomaly-001",
      contract_mode: "study_v1",
      run_spec_id: "runspec:001",
      admission_id: "admission:001",
      experiment_revision_id: "study@1",
      variant_id: "candidate",
      status: "failed",
      runner: "evidrun.runner/responses-read-agent-v1",
      output: null,
      context_hash: null,
      execution_trust: {
        status: "recorded",
        trust_id: "trust:anomaly-001",
        digest: "a".repeat(64),
        kind: "unverified_revision_set",
      },
      isolation: "in_process",
      created_at: "2026-07-28T10:00:00Z",
      completed_at: "2026-07-28T10:01:00Z",
      grade: null,
      context_snapshot: null,
      record: null,
      events,
      execution: null,
      subject_envelope_digest: null,
      ...overrides,
    } as RunDetail,
    events,
    evaluations: [],
    checkpoints: [],
  };
}

function adapter(retryRun = vi.fn(async () => ({ run_id: "run:retry-001" }))): ObservabilityAdapter {
  return {
    listRuns: vi.fn(async () => []),
    getRun: vi.fn(),
    getEvents: vi.fn(async () => []),
    getEvaluations: vi.fn(async () => []),
    getCheckpoints: vi.fn(async () => []),
    getProvider: vi.fn(),
    exportRunBundle: vi.fn(),
    retryRun,
    stream: { subscribe: () => () => {} },
  } as unknown as ObservabilityAdapter;
}

function renderPanel({
  data = detail(),
  executor,
  streamState = "open" as const,
  streamError = null as string | null,
  onRetried = vi.fn(),
  panelAdapter = adapter(),
}: {
  data?: DetailData;
  executor?: ExecutorState;
  streamState?: "connecting" | "open" | "reconnecting" | "closed";
  streamError?: string | null;
  onRetried?: (runId: string) => void;
  panelAdapter?: ObservabilityAdapter;
} = {}) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <RunDetailPanel
        adapter={panelAdapter}
        data={data}
        executor={executor}
        onBack={vi.fn()}
        onRetried={onRetried}
        streamError={streamError}
        streamState={streamState}
      />
    </QueryClientProvider>,
  );
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("anomaly presentation", () => {
  it("shows trust and isolation as independent text", () => {
    renderPanel();
    expect(screen.getByText("Trust: Não verificada")).toBeInTheDocument();
    expect(screen.getByText("Isolamento: in_process")).toBeInTheDocument();
    expect(screen.getByText(/Não verificada — Sem confirmação humana/)).toBeInTheDocument();
    expect(screen.getByText("in_process")).toBeInTheDocument();
  });

  it("names the anomaly and its cause", () => {
    renderPanel();
    expect(screen.getByText("Anomalia (não avaliável)")).toBeInTheDocument();
    expect(screen.getByText(/deterministically recovered/)).toBeInTheDocument();
  });

  it("says the absence of a result is not a negative result", () => {
    renderPanel();
    expect(screen.getByText(/Ausência de resultado, não resultado negativo/)).toBeInTheDocument();
  });

  it("keeps the partial metrics a failed Run already recorded", () => {
    renderPanel();
    expect(screen.getByText("1240 entrada / 380 saída")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("does not present a completed Run as an anomaly", () => {
    const events = [
      event("run.completed", { goal_result: { state: "achieved" }, terminal_cause: "ok" }),
    ];
    renderPanel({ data: detail({ status: "completed" }, events) });
    expect(screen.queryByText(/Ausência de resultado/)).not.toBeInTheDocument();
    expect(screen.getByText("Objetivo alcançado")).toBeInTheDocument();
  });

  it("distinguishes a failed objective from an unassessable one", () => {
    // Counting an indeterminate invocation as a wrong answer would blame the Subject for infra.
    const events = [
      event("run.completed", { goal_result: { state: "not_achieved" }, terminal_cause: "x" }),
    ];
    renderPanel({ data: detail({ status: "completed" }, events) });
    expect(screen.getByText("Objetivo não alcançado")).toBeInTheDocument();
    expect(screen.queryByText(/Ausência de resultado/)).not.toBeInTheDocument();
  });
});

describe("retry", () => {
  it("makes clear a retry is a new Run rather than a resumption", () => {
    renderPanel();
    expect(screen.getByText(/usa o mesmo Execution Plan do zero/)).toBeInTheDocument();
    expect(screen.getByText(/Esta Run permanece como está/)).toBeInTheDocument();
  });

  it("follows the Run a retry created", async () => {
    const onRetried = vi.fn();
    renderPanel({ onRetried });
    screen.getByRole("button", { name: "Rerun" }).click();
    await waitFor(() => expect(onRetried).toHaveBeenCalledWith("run:retry-001"));
  });

  it("reports a refused admission instead of failing silently", async () => {
    const retryRun = vi.fn(async () => {
      throw new Error("A admissão recusou este RunSpec: rejected");
    });
    renderPanel({ panelAdapter: adapter(retryRun as never) });
    screen.getByRole("button", { name: "Rerun" }).click();
    expect(await screen.findByText(/A admissão recusou/)).toBeInTheDocument();
  });

  it("offers no retry without a canonical RunSpec", () => {
    renderPanel({ data: detail({ run_spec_id: null }) });
    expect(screen.queryByRole("button", { name: "Rerun" })).not.toBeInTheDocument();
    expect(screen.getByText(/Sem Execution Plan canônico/)).toBeInTheDocument();
  });
});

describe("progress note", () => {
  it("blames the executor, not the stream, when nothing can progress", () => {
    renderPanel({
      data: detail({ status: "queued" }),
      executor: { status: "failed" },
      streamState: "reconnecting",
      streamError: "Stream interrompido",
    });
    expect(screen.getByRole("alert")).toHaveTextContent(/executor de Runs parou/);
  });

  it("keeps a reconnecting stream quiet", () => {
    renderPanel({
      data: detail({ status: "queued" }),
      executor: { status: "ready" },
      streamState: "reconnecting",
    });
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.getByText(/Reconectando ao stream/)).toBeInTheDocument();
  });
});
