import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ObservabilityAdapter } from "../../data/contracts";
import type { ProviderProfile, Run, RunDetail, RunEvent } from "../../types";
import { ObservabilityWorkspace } from "./ObservabilityPage";
import {
  filterRuns,
  getForensicTurnWindow,
  sortEvents,
  summarizeRuns,
} from "./observabilityModel";

const now = Date.parse("2026-07-24T16:00:00Z");

const runs: Run[] = [
  {
    id: "run:active-001",
    experiment_revision_id: "study:context-reliability@3",
    contract_mode: "study_v1",
    run_spec_id: "runspec:001",
    admission_id: "admission:001",
    variant_id: "candidate",
    status: "running",
    runner: "evidrun.runner/responses-read-agent-v1",
    output: null,
    context_hash: "sha256:context",
    created_at: "2026-07-24T15:30:00Z",
    completed_at: null,
    grade: null,
    context_snapshot: null,
  },
  {
    id: "run:completed-002",
    experiment_revision_id: "study:context-reliability@3",
    contract_mode: "study_v1",
    run_spec_id: "runspec:002",
    admission_id: "admission:002",
    variant_id: "baseline",
    status: "completed",
    runner: "evidrun.runner/scripted-v1",
    output: null,
    context_hash: "sha256:other",
    created_at: "2026-07-22T10:00:00Z",
    completed_at: "2026-07-22T10:00:02Z",
    grade: null,
    context_snapshot: null,
  },
  {
    id: "run:failed-003",
    experiment_revision_id: "study:incident@1",
    contract_mode: "legacy_v1",
    run_spec_id: null,
    admission_id: null,
    variant_id: "default",
    status: "failed",
    runner: "legacy-scripted",
    output: null,
    context_hash: null,
    created_at: "2026-07-24T14:00:00Z",
    completed_at: "2026-07-24T14:00:03Z",
    grade: null,
    context_snapshot: null,
  },
];

function event(sequence: number, type: string): RunEvent {
  return {
    event_id: `event:${sequence}`,
    schema_version: "1",
    run_id: "run:active-001",
    sequence,
    type,
    occurred_at_utc: `2026-07-24T15:30:0${sequence}Z`,
    actor_type: type.startsWith("tool.") ? "tool" : "runtime",
    actor_id: "actor:runtime",
    classification: "internal",
    payload:
      type === "tool.completed"
        ? { call_id: "call:orphan", result_ref: { artifact_id: "artifact:tool-result", digest: "sha256:result" } }
        : {},
    correlation_id: null,
    causation_id: null,
    prev_event_hash: sequence > 1 ? `sha256:${sequence - 1}` : null,
    event_hash: `sha256:${sequence}`,
  };
}

const traceEvents = [
  event(4, "subject.responded"),
  event(1, "run.queued"),
  event(3, "tool.completed"),
  event(2, "subject.invoked"),
];

const provider: ProviderProfile = {
  id: "cliproxyapi-local",
  display_name: "CLIProxyAPI local",
  api: "openai_responses",
  base_url: "http://127.0.0.1:8318/v1",
  model: "deepseek-v4-flash",
  reasoning_effort: "max",
  local_only: true,
  credential_service: "evidrun",
  default: true,
  credential_available: true,
  credential_source: "system_keychain",
};

const detail: RunDetail = {
  ...runs[0]!,
  record: null,
  events: traceEvents,
  execution: null,
  subject_envelope_digest: "sha256:subject-envelope",
};

function adapter(): ObservabilityAdapter {
  return {
    listRuns: vi.fn(async () => runs),
    getRun: vi.fn(async () => detail),
    getEvents: vi.fn(async () => traceEvents),
    getEvaluations: vi.fn(async () => []),
    getCheckpoints: vi.fn(async () => []),
    getProvider: vi.fn(async () => provider),
    exportRunBundle: vi.fn(async (runId: string) => ({
      path: `/tmp/${runId}.evidrun.zip`,
      run_id: runId,
      schema_version: "3" as const,
    })),
    stream: {
      subscribe(_runId, callbacks) {
        callbacks.onState("open");
        return () => callbacks.onState("closed");
      },
    },
  };
}

function renderWorkspace(
  search: { q?: string; status?: string; period?: string; run?: string } = {},
  onSearchChange = vi.fn(),
  customAdapter = adapter(),
) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const result = render(
    <QueryClientProvider client={queryClient}>
      <ObservabilityWorkspace
        adapter={customAdapter}
        onSearchChange={onSearchChange}
        search={search}
      />
    </QueryClientProvider>,
  );
  return { ...result, onSearchChange, queryClient };
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("Observability filters and search params", () => {
  it("filters q, status and period without changing the Run records", () => {
    expect(filterRuns(runs, { q: "candidate" }, now).map((run) => run.id)).toEqual([
      "run:active-001",
    ]);
    expect(filterRuns(runs, { status: "attention" }, now).map((run) => run.id)).toEqual([
      "run:failed-003",
    ]);
    expect(filterRuns(runs, { period: "24h" }, now).map((run) => run.id)).toEqual([
      "run:active-001",
      "run:failed-003",
    ]);
    expect(summarizeRuns(runs)).toEqual({ all: 3, active: 1, completed: 1, attention: 1 });
  });

  it("publishes command and selection changes as TanStack-compatible search state", async () => {
    const onSearchChange = vi.fn();
    renderWorkspace({}, onSearchChange);
    await screen.findByText("run:active-001");

    fireEvent.change(screen.getByRole("searchbox", { name: "Buscar Runs" }), {
      target: { value: "incident" },
    });
    expect(onSearchChange).toHaveBeenLastCalledWith({ q: "incident" });

    fireEvent.click(screen.getByRole("button", { name: "Mais filtros" }));
    fireEvent.change(screen.getByRole("combobox", { name: "Status exato" }), {
      target: { value: "running" },
    });
    expect(onSearchChange).toHaveBeenLastCalledWith({ status: "running" });

    fireEvent.change(screen.getByRole("combobox", { name: "Período" }), {
      target: { value: "7d" },
    });
    expect(onSearchChange).toHaveBeenLastCalledWith({ period: "7d" });

    fireEvent.click(screen.getByRole("button", { name: /run:active-001/i }));
    expect(onSearchChange).toHaveBeenLastCalledWith({ run: "run:active-001" });
  });
});

describe("Observability layout and trace", () => {
  it("keeps full list without selection and exposes master-detail state with selection", async () => {
    const list = renderWorkspace();
    await screen.findByText("run:active-001");
    expect(list.container.querySelector("[data-layout='list']")).toBeInTheDocument();
    list.unmount();

    const selected = renderWorkspace({ run: "run:active-001" });
    await screen.findByText("sha256:subject-envelope");
    expect(selected.container.querySelector("[data-layout='master-detail']")).toBeInTheDocument();
    expect(selected.container.querySelector(".obs-split-divider")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Voltar às Runs" })).toBeInTheDocument();
  });

  it("orders real events by sequence and exposes one complete forensic turn", async () => {
    renderWorkspace({ run: "run:active-001" });
    const trace = await screen.findByRole("list", { name: "Eventos ordenados por sequence" });
    const rows = within(trace).getAllByRole("button");
    expect(rows.map((row) => row.textContent)).toEqual([
      expect.stringContaining("run.queued"),
      expect.stringContaining("subject.invoked"),
      expect.stringContaining("tool.completed"),
      expect.stringContaining("subject.responded"),
    ]);
    fireEvent.click(within(trace).getByRole("button", { name: /tool.completed/i }));
    expect(screen.getByText(/Evento factual incompleto/)).toBeInTheDocument();
    expect(screen.getByText("Janela forense read-only")).toBeInTheDocument();
    expect(screen.getByText("1 turno disponível")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Copiar 1 turno" })).toBeInTheDocument();

    expect(sortEvents(traceEvents).map((item) => item.sequence)).toEqual([1, 2, 3, 4]);
    expect(getForensicTurnWindow(traceEvents, "event:3")?.map((item) => item.sequence)).toEqual([
      2, 3, 4,
    ]);
    expect(getForensicTurnWindow(traceEvents, "event:4")?.map((item) => item.sequence)).toEqual([
      2, 3, 4,
    ]);
  });

  it("does not expose a replay action or claim", async () => {
    renderWorkspace({ run: "run:active-001" });
    await screen.findByText("sha256:subject-envelope");
    fireEvent.click(screen.getByRole("tab", { name: "Evidence" }));
    await waitFor(() => expect(screen.getByText(/references_only/)).toBeInTheDocument());
    expect(screen.getByText("Run events")).toBeInTheDocument();
    expect(screen.getByText("Referência preservada; conteúdo indisponível")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /replay|reproduzir/i })).not.toBeInTheDocument();
    expect(screen.queryByText(/replay disponível|reprodução disponível/i)).not.toBeInTheDocument();
  });

  it("wires complete tab ARIA and arrow-key roving focus", async () => {
    renderWorkspace({ run: "run:active-001" });
    const traceTab = await screen.findByRole("tab", { name: "Trace" });
    const evaluationTab = screen.getByRole("tab", { name: "Evaluation" });
    expect(traceTab).toHaveAttribute("aria-controls", "obs-panel-trace");
    expect(evaluationTab).toHaveAttribute("tabindex", "-1");
    fireEvent.keyDown(traceTab, { key: "ArrowRight" });
    await waitFor(() => expect(evaluationTab).toHaveAttribute("aria-selected", "true"));
    expect(screen.getByRole("tabpanel", { name: "Evaluation" })).toHaveAttribute("id", "obs-panel-evaluation");
  });

  it("shows endpoint errors separately and retries the list query", async () => {
    const failing = adapter();
    const listRuns = vi.fn().mockRejectedValueOnce(new Error("HTTP 500")).mockResolvedValueOnce(runs);
    failing.listRuns = listRuns;
    renderWorkspace({}, vi.fn(), failing);
    expect(await screen.findByText("Falha no endpoint de Runs")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
    await screen.findByText("run:active-001");
    expect(listRuns).toHaveBeenCalledTimes(2);
  });
});
