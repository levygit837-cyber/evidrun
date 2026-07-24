import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { type ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { CreationAdapter } from "../../data/contracts";
import type { BootstrapDemoResult } from "../../types";
import { CreatePage } from "./CreatePage";

afterEach(cleanup);

const bootstrapResult: BootstrapDemoResult = {
  experiment_revision_id: "revision-real-1",
  study_revision: { id: "study-real-1" },
  comparison_id: "comparison-real-1",
  baseline_run_id: "run-baseline-real",
  candidate_run_id: "run-candidate-real",
  validity: "valid",
  context_diff: {},
};

function renderCreate(adapter: CreationAdapter) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const invalidate = vi.spyOn(queryClient, "invalidateQueries");

  function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  }

  render(<CreatePage adapter={adapter} />, { wrapper: Wrapper });
  return { invalidate };
}

function advanceToAdmission() {
  fireEvent.click(screen.getByRole("button", { name: /compilar runspecs/i }));
  fireEvent.click(screen.getByRole("button", { name: /revisar admission/i }));
}

describe("CreatePage", () => {
  it("navega pelas etapas, preserva o draft e torna o downstream stale ao editar Study", () => {
    const adapter: CreationAdapter = {
      bootstrapCanonicalDemo: vi.fn().mockResolvedValue(bootstrapResult),
    };
    renderCreate(adapter);

    const name = screen.getByRole("textbox", { name: /nome do study/i });
    fireEvent.change(name, { target: { value: "Study preservado" } });
    fireEvent.click(screen.getByRole("button", { name: /compilar runspecs/i }));

    expect(screen.getByText(/2 snapshots imutáveis/i)).toBeInTheDocument();
    expect(screen.getByText(/snapshots locais, ainda sem record canônico/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /editar study/i }));

    expect(screen.getByRole("textbox", { name: /nome do study/i })).toHaveValue("Study preservado");
    expect(screen.getByText("Downstream stale")).toBeInTheDocument();
    expect(screen.getAllByText("stale").length).toBeGreaterThanOrEqual(3);
  });

  it("expõe rejection para disclosure pre_run e distingue todos os estados de Admission", () => {
    const adapter: CreationAdapter = {
      bootstrapCanonicalDemo: vi.fn().mockResolvedValue(bootstrapResult),
    };
    renderCreate(adapter);

    fireEvent.change(screen.getByRole("combobox", { name: /disclosure da avaliação/i }), {
      target: { value: "pre_run" },
    });
    advanceToAdmission();

    expect(screen.getByText("Admission rejected")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /corrigir study/i })).toBeInTheDocument();

    fireEvent.click(screen.getByText(/estados de admission distinguidos/i));
    const key = screen.getByText(/estados de admission distinguidos/i).closest("details");
    expect(key).not.toBeNull();
    for (const state of ["admitted", "rejected", "failed", "unavailable", "stale"]) {
      expect(within(key as HTMLElement).getByText(state)).toBeInTheDocument();
    }
  });

  it("mostra um único estado factual pendente e bloqueia submit duplicado", async () => {
    let resolveBootstrap!: (result: BootstrapDemoResult) => void;
    const pending = new Promise<BootstrapDemoResult>((resolve) => {
      resolveBootstrap = resolve;
    });
    const bootstrapCanonicalDemo = vi.fn(() => pending);
    renderCreate({ bootstrapCanonicalDemo });
    advanceToAdmission();

    const execute = screen.getByRole("button", { name: /executar fixture canônica/i });
    fireEvent.click(execute);
    fireEvent.click(execute);

    await waitFor(() => expect(bootstrapCanonicalDemo).toHaveBeenCalledTimes(1));
    expect(screen.getAllByText("Executando fixture no backend").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByRole("button", { name: /executando fixture no backend/i })).toBeDisabled();

    resolveBootstrap(bootstrapResult);
    expect(await screen.findByText("run-baseline-real")).toBeInTheDocument();
  });

  it("executa o bootstrap mockado, invalida queries e cria links reais para baseline e candidate", async () => {
    const bootstrapCanonicalDemo = vi.fn().mockResolvedValue(bootstrapResult);
    const { invalidate } = renderCreate({ bootstrapCanonicalDemo });
    advanceToAdmission();

    fireEvent.click(screen.getByRole("button", { name: /executar fixture canônica/i }));

    const baseline = await screen.findByText("run-baseline-real");
    const candidate = screen.getByText("run-candidate-real");
    expect(bootstrapCanonicalDemo).toHaveBeenCalledTimes(1);
    expect(invalidate).toHaveBeenCalled();
    expect(baseline.closest("a")).toHaveAttribute("href", "#/observability?run=run-baseline-real");
    expect(candidate.closest("a")).toHaveAttribute("href", "#/observability?run=run-candidate-real");
    expect(screen.getByText(/comparison-real-1/)).toBeInTheDocument();
  });

  it("termina authority, autoria e Artifact ausentes como Integração pendente", async () => {
    renderCreate({ bootstrapCanonicalDemo: vi.fn().mockResolvedValue(bootstrapResult) });
    advanceToAdmission();

    expect(screen.getByText("Autoria do Study")).toBeInTheDocument();
    expect(screen.getByText("Authority humana")).toBeInTheDocument();
    expect(screen.getByText("Acesso a Artifact")).toBeInTheDocument();
    expect(screen.getAllByText("Integração pendente")).toHaveLength(3);

    fireEvent.click(screen.getByRole("button", { name: /executar fixture canônica/i }));
    await waitFor(() => expect(screen.getByText("run-candidate-real")).toBeInTheDocument());
    expect(screen.getByText("Integração pendente")).toBeInTheDocument();
    expect(screen.getByText(/autoria humana, authority verificável e materialização de artifact/i)).toBeInTheDocument();
  });
});
