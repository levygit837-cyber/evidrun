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
  fireEvent.click(screen.getByRole("button", { name: /generate execution plans/i }));
  fireEvent.click(screen.getByRole("button", { name: /check readiness/i }));
}

describe("CreatePage", () => {
  it("navega por etapas alcançadas e só torna o downstream stale após alteração efetiva", () => {
    const adapter: CreationAdapter = {
      bootstrapCanonicalDemo: vi.fn().mockResolvedValue(bootstrapResult),
    };
    renderCreate(adapter);

    expect(screen.getByRole("heading", { name: "Study Design" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Execution Plans" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Readiness Check" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Runs" })).toBeInTheDocument();

    const name = screen.getByRole("textbox", { name: /study name/i });
    fireEvent.change(name, { target: { value: "Study preservado" } });
    expect(screen.getByRole("button", { name: /execution plans locked/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /readiness check locked/i })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: /generate execution plans/i }));

    expect(screen.getByRole("button", { name: "Execution Plans" })).toHaveAttribute("aria-current", "step");
    expect(screen.getByText(/local execution plans/i)).toBeInTheDocument();
    expect(screen.getByText(/não são enviados nem usados pelo bootstrap crl-ctx-002/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Study Design" }));
    expect(screen.getByRole("button", { name: "Study Design" })).toHaveAttribute("aria-current", "step");
    expect(screen.getByRole("textbox", { name: /study name/i })).toHaveValue("Study preservado");
    fireEvent.click(screen.getByRole("button", { name: "Execution Plans" }));

    fireEvent.click(screen.getByRole("button", { name: /edit study design/i }));

    expect(screen.getByRole("textbox", { name: /study name/i })).toHaveValue("Study preservado");
    expect(screen.queryByText("Downstream steps are outdated")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Execution Plans" })).toBeEnabled();

    fireEvent.change(screen.getByRole("textbox", { name: /study name/i }), {
      target: { value: "Study realmente alterado" },
    });
    expect(screen.getByText("Downstream steps are outdated")).toBeInTheDocument();
    expect(screen.getAllByText("outdated").length).toBeGreaterThanOrEqual(3);
    expect(screen.getByRole("button", { name: /execution plans outdated/i })).toBeDisabled();
  });

  it("adiciona, remove e preserva Scenarios, Variants e Evaluation modules no estado local", () => {
    renderCreate({ bootstrapCanonicalDemo: vi.fn().mockResolvedValue(bootstrapResult) });

    fireEvent.click(screen.getByRole("button", { name: /add scenario/i }));
    fireEvent.change(screen.getByRole("textbox", { name: "Scenarios 2" }), {
      target: { value: "Scenario preservado" },
    });

    fireEvent.click(screen.getByText("Variants"));
    fireEvent.click(screen.getByRole("button", { name: /add variant/i }));
    fireEvent.change(screen.getByRole("textbox", { name: "Variants 3" }), {
      target: { value: "Variant preservada" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Remove Variants 1" }));

    fireEvent.click(screen.getByText("Evaluation criteria"));
    fireEvent.click(screen.getByRole("button", { name: /add evaluation criterion/i }));
    fireEvent.change(screen.getByRole("textbox", { name: "Evaluation criteria 2" }), {
      target: { value: "Evaluation preservada" },
    });

    fireEvent.click(screen.getByRole("button", { name: /generate execution plans/i }));
    fireEvent.click(screen.getByRole("button", { name: "Study Design" }));

    expect(screen.getByDisplayValue("Scenario preservado")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Variant preservada")).toBeInTheDocument();
    expect(screen.queryByDisplayValue("Full context")).not.toBeInTheDocument();
    expect(screen.getByDisplayValue("Evaluation preservada")).toBeInTheDocument();
  });

  it("expõe rejection para disclosure pre_run e distingue todos os estados de Admission", () => {
    const adapter: CreationAdapter = {
      bootstrapCanonicalDemo: vi.fn().mockResolvedValue(bootstrapResult),
    };
    renderCreate(adapter);

    fireEvent.change(screen.getByRole("combobox", { name: /evaluation disclosure/i }), {
      target: { value: "pre_run" },
    });
    advanceToAdmission();

    expect(screen.getByText("Run Blocked")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /fix study design/i })).toBeInTheDocument();

    fireEvent.click(screen.getByText(/readiness check states/i));
    const key = screen.getByText(/readiness check states/i).closest("details");
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

    expect(screen.getByText(/o rascunho não será enviado/i)).toBeInTheDocument();
    expect(screen.getByText(/fixture não humana/i)).toBeInTheDocument();
    const execute = screen.getByRole("button", { name: /executar crl-ctx-002/i });
    fireEvent.click(execute);
    fireEvent.click(execute);

    await waitFor(() => expect(bootstrapCanonicalDemo).toHaveBeenCalledTimes(1));
    expect(screen.getAllByText("Executando CRL-CTX-002 no backend").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByRole("button", { name: /executando crl-ctx-002 no backend/i })).toBeDisabled();
    expect(document.querySelector(".create-flow .ui-spinner")).toBeNull();
    await waitFor(() => expect(document.querySelector(".create-flow .ui-spinner")).not.toBeNull(), {
      timeout: 800,
    });

    resolveBootstrap(bootstrapResult);
    expect(await screen.findByText("run-baseline-real")).toBeInTheDocument();
  });

  it("executa o bootstrap mockado, invalida queries e cria links reais para baseline e candidate", async () => {
    const bootstrapCanonicalDemo = vi.fn().mockResolvedValue(bootstrapResult);
    const { invalidate } = renderCreate({ bootstrapCanonicalDemo });
    advanceToAdmission();

    fireEvent.click(screen.getByRole("button", { name: /executar crl-ctx-002/i }));

    const baseline = await screen.findByText("run-baseline-real");
    const candidate = screen.getByText("run-candidate-real");
    expect(bootstrapCanonicalDemo).toHaveBeenCalledTimes(1);
    expect(bootstrapCanonicalDemo).toHaveBeenCalledWith();
    expect(invalidate).toHaveBeenCalled();
    expect(baseline.closest("a")).toHaveAttribute("href", "#/observability?run=run-baseline-real");
    expect(candidate.closest("a")).toHaveAttribute("href", "#/observability?run=run-candidate-real");
    expect(screen.getByText(/comparison-real-1/)).toBeInTheDocument();
    expect(screen.getByText(/crl-ctx-002 concluída no backend/i)).toBeInTheDocument();
    expect(screen.getByText(/o rascunho local não foi enviado/i)).toBeInTheDocument();
  });

  it("termina authority, autoria e Artifact ausentes como Integração pendente", async () => {
    renderCreate({ bootstrapCanonicalDemo: vi.fn().mockResolvedValue(bootstrapResult) });
    advanceToAdmission();

    expect(screen.getByText("Study authorship")).toBeInTheDocument();
    expect(screen.getByText("Human authority")).toBeInTheDocument();
    expect(screen.getByText("Artifact access")).toBeInTheDocument();
    expect(screen.getAllByText("Integração pendente")).toHaveLength(3);

    fireEvent.click(screen.getByRole("button", { name: /executar crl-ctx-002/i }));
    await waitFor(() => expect(screen.getByText("run-candidate-real")).toBeInTheDocument());
    expect(screen.getByText("Integração pendente")).toBeInTheDocument();
    expect(screen.getByText(/autoria humana, autoridade verificável e materialização do artefato/i)).toBeInTheDocument();
  });
});
