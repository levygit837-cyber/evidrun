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
  fireEvent.click(screen.getByRole("button", { name: /compilar preview demo/i }));
  fireEvent.click(screen.getByRole("button", { name: /revisar admission/i }));
}

describe("CreatePage", () => {
  it("navega por etapas alcançadas, bloqueia futuras e torna o downstream stale ao editar Study", () => {
    const adapter: CreationAdapter = {
      bootstrapCanonicalDemo: vi.fn().mockResolvedValue(bootstrapResult),
    };
    renderCreate(adapter);

    expect(
      screen.getAllByText("Demo / integration_pending · não alimenta bootstrap"),
    ).toHaveLength(4);

    const name = screen.getByRole("textbox", { name: /nome do study/i });
    fireEvent.change(name, { target: { value: "Study preservado" } });
    expect(screen.getByRole("button", { name: /runspecs bloqueado/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /admission bloqueado/i })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: /compilar preview demo/i }));

    expect(screen.getByRole("button", { name: "RunSpecs" })).toHaveAttribute("aria-current", "step");
    expect(screen.getByText(/preview demo · integration_pending/i)).toBeInTheDocument();
    expect(screen.getByText(/não são enviados nem usados pelo bootstrap crl-ctx-002/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Study" }));
    expect(screen.getByRole("button", { name: "Study" })).toHaveAttribute("aria-current", "step");
    expect(screen.getByRole("textbox", { name: /nome do study/i })).toHaveValue("Study preservado");
    fireEvent.click(screen.getByRole("button", { name: "RunSpecs" }));

    fireEvent.click(screen.getByRole("button", { name: /editar study/i }));

    expect(screen.getByRole("textbox", { name: /nome do study/i })).toHaveValue("Study preservado");
    expect(screen.getByText("Downstream stale")).toBeInTheDocument();
    expect(screen.getAllByText("stale").length).toBeGreaterThanOrEqual(3);
    expect(screen.getByRole("button", { name: /runspecs stale/i })).toBeDisabled();
  });

  it("adiciona, remove e preserva Scenarios, Variants e Evaluation modules no estado local", () => {
    renderCreate({ bootstrapCanonicalDemo: vi.fn().mockResolvedValue(bootstrapResult) });

    fireEvent.click(screen.getByRole("button", { name: /adicionar scenario/i }));
    fireEvent.change(screen.getByRole("textbox", { name: "Scenarios 2" }), {
      target: { value: "Scenario preservado" },
    });

    fireEvent.click(screen.getByText("Variants"));
    fireEvent.click(screen.getByRole("button", { name: /adicionar variant/i }));
    fireEvent.change(screen.getByRole("textbox", { name: "Variants 3" }), {
      target: { value: "Variant preservada" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Remover Variants 1" }));

    fireEvent.click(screen.getByText("Evaluation modules"));
    fireEvent.click(screen.getByRole("button", { name: /adicionar evaluation module/i }));
    fireEvent.change(screen.getByRole("textbox", { name: "Evaluation modules 2" }), {
      target: { value: "Evaluation preservada" },
    });

    fireEvent.click(screen.getByRole("button", { name: /compilar preview demo/i }));
    fireEvent.click(screen.getByRole("button", { name: "Study" }));

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

    expect(screen.getByText(/o draft não será enviado/i)).toBeInTheDocument();
    expect(screen.getByText(/repository_fixture não humana/i)).toBeInTheDocument();
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
    expect(screen.getByText(/o draft local não foi enviado/i)).toBeInTheDocument();
  });

  it("termina authority, autoria e Artifact ausentes como Integração pendente", async () => {
    renderCreate({ bootstrapCanonicalDemo: vi.fn().mockResolvedValue(bootstrapResult) });
    advanceToAdmission();

    expect(screen.getByText("Autoria do Study")).toBeInTheDocument();
    expect(screen.getByText("Authority humana")).toBeInTheDocument();
    expect(screen.getByText("Acesso a Artifact")).toBeInTheDocument();
    expect(screen.getAllByText("Integração pendente")).toHaveLength(3);

    fireEvent.click(screen.getByRole("button", { name: /executar crl-ctx-002/i }));
    await waitFor(() => expect(screen.getByText("run-candidate-real")).toBeInTheDocument());
    expect(screen.getByText("Integração pendente")).toBeInTheDocument();
    expect(screen.getByText(/autoria humana, authority verificável e materialização de artifact/i)).toBeInTheDocument();
  });
});
