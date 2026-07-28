import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { BackendState, ExecutorState, Run } from "../types";
import { RuntimeAlert } from "./RuntimeAlert";

const runs = vi.hoisted(() => vi.fn());
vi.mock("../api/client", () => ({ api: { runs } }));

const runtime = vi.hoisted(() => ({
  state: { status: "ready" } as BackendState,
  executor: { status: "ready" } as ExecutorState,
  restart: vi.fn(),
  restartExecutor: vi.fn(),
}));
vi.mock("./BackendRuntimeProvider", () => ({ useBackendRuntime: () => runtime }));

function renderAlert(backend: BackendState, executor: ExecutorState, queued: Run[]) {
  runtime.state = backend;
  runtime.executor = executor;
  runs.mockResolvedValue(queued);
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <RuntimeAlert />
    </QueryClientProvider>,
  );
}

const waiting = [{ status: "queued" } as Run];

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("runtime alert", () => {
  it("renders nothing when both planes are healthy", async () => {
    renderAlert({ status: "ready" }, { status: "ready" }, waiting);
    await waitFor(() => expect(runs).toHaveBeenCalled());
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("names the stalled queue and offers to restart the executor", async () => {
    renderAlert({ status: "ready" }, { status: "failed" }, waiting);
    // The banner renders before the queue query resolves, so wait for the count to land.
    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent("1 Run aguardando execução"),
    );
    expect(screen.getByRole("button", { name: "Reiniciar executor" })).toBeInTheDocument();
  });

  it("says evidence stays readable when only the executor is down", async () => {
    renderAlert({ status: "ready" }, { status: "failed" }, waiting);
    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(/evidência já gravada/i),
    );
  });

  it("offers the backend restart when the API is the one that died", async () => {
    renderAlert({ status: "failed", message: "Backend exited (1)" }, { status: "failed" }, waiting);
    expect(await screen.findByRole("alert")).toHaveTextContent("Backend exited (1)");
    expect(screen.getByRole("button", { name: "Reiniciar backend" })).toBeInTheDocument();
  });

  it("does not query the queue while the backend is unreachable", async () => {
    renderAlert({ status: "failed" }, { status: "failed" }, waiting);
    await screen.findByRole("alert");
    expect(runs).not.toHaveBeenCalled();
  });
});
