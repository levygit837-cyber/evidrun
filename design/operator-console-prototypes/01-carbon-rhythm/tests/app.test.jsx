import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, test, vi } from "vitest";
import { App } from "../src/App.jsx";
import { createInitialState, operatorReducer } from "../src/state/operatorState.js";

function renderAt(path = "/") {
  window.history.replaceState({}, "", path);
  return render(<App />);
}

afterEach(() => {
  vi.useRealTimers();
});

describe("Carbon Rhythm operator console", () => {
  test("navega pelas quatro rotas e respeita browser history", async () => {
    const user = userEvent.setup();
    renderAt();

    await user.click(screen.getAllByRole("link", { name: "Projects" })[0]);
    expect(
      await screen.findByRole("heading", { name: "Projects", level: 1 }),
    ).toBeInTheDocument();

    await user.click(screen.getAllByRole("link", { name: "Study" })[0]);
    expect(
      await screen.findByRole("heading", { name: "Diagnóstico de regressões após deploy", level: 1 }),
    ).toBeInTheDocument();

    act(() => window.history.back());
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "Projects", level: 1 })).toBeInTheDocument(),
    );

    await user.click(screen.getAllByRole("link", { name: "Runs" })[0]);
    expect(await screen.findByRole("heading", { name: "Runs", level: 1 })).toBeInTheDocument();
  });

  test("composer bloqueia vazio, preserva Shift+Enter e executa a sequência observável", async () => {
    const user = userEvent.setup();
    renderAt();

    const composer = screen.getByLabelText("Novo draft para o Lab Agent");
    const send = screen.getByRole("button", { name: "Enviar draft" });
    expect(send).toBeDisabled();

    await user.type(composer, "Linha um{Shift>}{Enter}{/Shift}linha dois");
    expect(composer).toHaveValue("Linha um\nlinha dois");
    expect(send).toBeEnabled();

    await user.clear(composer);
    await user.type(composer, "Quais sinais mudaram depois do deploy?{Enter}");
    expect(screen.getByText("Quais sinais mudaram depois do deploy?")).toBeInTheDocument();
    expect(screen.getAllByText("Preparando contexto autorizado").length).toBeGreaterThan(0);

    expect(await screen.findByText("Resposta capturada", {}, { timeout: 3_000 })).toBeInTheDocument();
    expect(screen.getByText("Draft do Lab Agent", { exact: true })).toBeInTheDocument();
    expect(composer).toHaveFocus();
  });

  test("disclosure observável apresenta tool call e tool result sem conteúdo privado", async () => {
    const user = userEvent.setup();
    renderAt();

    const disclosure = screen.getByText("Atividade observável").closest("summary");
    expect(disclosure).toBeVisible();
    expect(screen.getByText("Chamada de tool: read_text")).toBeVisible();
    expect(screen.getByText("Resultado da tool capturado")).toBeVisible();
    expect(screen.getByText(/Sem chain-of-thought/)).toBeVisible();

    await user.click(disclosure);
    expect(disclosure.closest("details")).not.toHaveAttribute("open");
    await user.click(disclosure);
    expect(disclosure.closest("details")).toHaveAttribute("open");
  });

  test("Chat usa snaps explícitos e preserva o thread entre rotas", async () => {
    const user = userEvent.setup();
    renderAt();

    const grip = screen.getByRole("button", { name: "Escolher posição e tamanho do Chat" });
    await user.click(grip);
    await user.click(screen.getByRole("menuitem", { name: /Meia altura/ }));
    expect(screen.getByRole("complementary", { name: "Chat do operador" })).toHaveClass(
      "adaptive-chat--half",
    );

    const note = screen.getByLabelText("Mensagem do Chat do operador");
    await user.type(note, "Nota persistente do operador");
    await user.click(screen.getByRole("button", { name: "Adicionar nota ao Chat" }));
    await user.click(screen.getAllByRole("link", { name: "Study" })[0]);
    expect(screen.getByText("Nota persistente do operador")).toBeVisible();
  });

  test("Chat mostra preview após long press e aceita snaps pelo teclado", () => {
    vi.useFakeTimers();
    renderAt();

    const grip = screen.getByRole("button", { name: "Escolher posição e tamanho do Chat" });
    fireEvent.pointerDown(grip, { pointerType: "mouse", button: 0, pointerId: 1 });
    act(() => vi.advanceTimersByTime(351));
    expect(document.querySelector(".snap-preview")).toBeInTheDocument();
    fireEvent.pointerUp(grip, { pointerType: "mouse", button: 0, pointerId: 1 });

    fireEvent.keyDown(grip, { key: "ArrowDown" });
    expect(screen.getByRole("menu", { name: "Posições do Chat" })).toBeInTheDocument();
    fireEvent.keyDown(grip, { key: "Enter" });
    expect(screen.getByRole("complementary", { name: "Chat do operador" })).toHaveClass(
      "adaptive-chat--half",
    );
  });

  test("Admission rejeitado bloqueia enqueue e nova revisão libera o fluxo", async () => {
    const user = userEvent.setup();
    renderAt("/study");

    expect(screen.getByRole("heading", { name: "Rejected" })).toBeInTheDocument();
    const blockedEnqueue = screen.getByRole("button", { name: /Enfileirar 2 RunSpecs/ });
    expect(blockedEnqueue).toBeDisabled();

    await user.click(screen.getByRole("button", { name: "Criar revisão corrigida" }));
    expect(screen.getByLabelText("Selecionar StudyRevision")).toHaveValue(
      "study-revision-stub-04",
    );
    const admittedEnqueue = screen.getByRole("button", { name: /Enfileirar 2 RunSpecs/ });
    expect(admittedEnqueue).toBeEnabled();

    await user.click(admittedEnqueue);
    expect(await screen.findByRole("heading", { name: "Runs", level: 1 })).toBeInTheDocument();
    expect(screen.getByText("Run stub enfileirada.", { exact: false })).toBeInTheDocument();
  });

  test("Run stub percorre queued, preparing, running, evaluating e terminal", async () => {
    const user = userEvent.setup();
    renderAt("/study");

    await user.click(screen.getByRole("button", { name: "Criar revisão corrigida" }));
    await user.click(screen.getByRole("button", { name: /Enfileirar 2 RunSpecs/ }));
    expect(await screen.findByRole("heading", { name: "Runs", level: 1 })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Iniciar Run stub" }));
    expect(screen.getByRole("heading", { name: "queued" })).toBeInTheDocument();

    expect(await screen.findByRole("heading", { name: "terminal" }, { timeout: 3_000 })).toBeInTheDocument();
    for (const eventName of [
      "run.queued",
      "subject.invoked",
      "subject.responded",
      "evaluation.recorded",
      "run.completed",
    ]) {
      expect(screen.getAllByText(eventName).length).toBeGreaterThan(0);
    }
    expect(screen.getByText("read_text, demonstração local")).toBeInTheDocument();
  });

  test("Projects seed sem Study ficam fail-closed no Lab, Study e Runs", async () => {
    const user = userEvent.setup();
    renderAt();

    for (const [projectName, projectId] of [
      ["Context Drift", "project-context-drift-stub"],
      ["Provider Gate", "project-provider-gate-stub"],
    ]) {
      const projectSwitcher = screen.getByLabelText("Trocar Project");
      await user.selectOptions(projectSwitcher, projectId);

      await waitFor(() =>
        expect(screen.getByRole("main")).toHaveTextContent(
          `Nenhuma Study vinculada a ${projectName}.`,
        ),
      );
      expect(screen.getByLabelText("Novo draft para o Lab Agent")).toBeDisabled();
      expect(screen.queryByText("tool.completed: read_text")).not.toBeInTheDocument();

      await user.click(screen.getAllByRole("link", { name: "Study" })[0]);
      expect(
        await screen.findByRole("heading", { name: "Nenhuma Study vinculada", level: 1 }),
      ).toBeInTheDocument();
      expect(screen.getByRole("main")).toHaveTextContent(projectName);
      expect(screen.queryByText("study-revision-stub-03")).not.toBeInTheDocument();

      await user.click(screen.getAllByRole("link", { name: "Runs" })[0]);
      expect(
        await screen.findByRole("heading", { name: "Nenhuma Run disponível", level: 2 }),
      ).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: /Run stub/ })).not.toBeInTheDocument();
      expect(screen.queryByText("run:stub-ri-0723-a")).not.toBeInTheDocument();

      await user.click(screen.getAllByRole("link", { name: "Lab" })[0]);
      await screen.findByRole("heading", { name: "Nenhuma Study vinculada", level: 1 });
    }
  });

  test("Chat mantém threads isolados quando o Project muda", async () => {
    const user = userEvent.setup();
    renderAt();

    await user.type(screen.getByLabelText("Mensagem do Chat do operador"), "Nota exclusiva RI");
    await user.click(screen.getByRole("button", { name: "Adicionar nota ao Chat" }));

    await user.selectOptions(screen.getByLabelText("Trocar Project"), "Context Drift");
    expect(screen.queryByText("Nota exclusiva RI")).not.toBeInTheDocument();
    expect(screen.getByText("Nenhuma nota neste Project.")).toBeInTheDocument();

    await user.type(screen.getByLabelText("Mensagem do Chat do operador"), "Nota exclusiva Context");
    await user.click(screen.getByRole("button", { name: "Adicionar nota ao Chat" }));
    expect(screen.getByText("Nota exclusiva Context")).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Trocar Project"), "Release Integrity");
    expect(screen.getByText("Nota exclusiva RI")).toBeInTheDocument();
    expect(screen.queryByText("Nota exclusiva Context")).not.toBeInTheDocument();
  });

  test("diálogo Criar Project mantém o foco dentro do modal", async () => {
    const user = userEvent.setup();
    renderAt("/projects");

    const trigger = screen.getByRole("button", { name: "Criar Project" });
    await user.click(trigger);
    const dialog = screen.getByRole("dialog", { name: "Criar Project" });
    const name = within(dialog).getByLabelText("Nome do Project");
    const intent = within(dialog).getByLabelText("Intenção");
    const cancel = within(dialog).getByRole("button", { name: "Cancelar" });
    const submit = within(dialog).getByRole("button", { name: "Criar Project" });
    const close = within(dialog).getByRole("button", { name: "Fechar diálogo" });

    await waitFor(() => expect(name).toHaveFocus());
    await user.tab();
    expect(intent).toHaveFocus();
    await user.tab();
    expect(cancel).toHaveFocus();
    await user.tab();
    expect(submit).toHaveFocus();
    await user.tab();
    expect(close).toHaveFocus();
    await user.tab();
    expect(name).toHaveFocus();
    await user.tab({ shift: true });
    expect(close).toHaveFocus();
  });

  test("novo Project nasce sem Study, Run, evidence ou Chat herdados", async () => {
    const user = userEvent.setup();
    renderAt("/projects");

    await user.click(screen.getByRole("button", { name: "Criar Project" }));
    await user.type(screen.getByLabelText("Nome do Project"), "Escopo Novo");
    await user.type(
      screen.getByLabelText("Intenção"),
      "Validar um escopo local sem herdar inventários anteriores.",
    );
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Criar Project" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());

    expect(screen.getByLabelText("Trocar Project")).toHaveDisplayValue("Escopo Novo");
    expect(screen.getByText("Nenhuma nota neste Project.")).toBeInTheDocument();

    await user.click(screen.getAllByRole("link", { name: "Lab" })[0]);
    expect(
      await screen.findByRole("heading", { name: "Nenhuma Study vinculada", level: 1 }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Novo draft para o Lab Agent")).toBeDisabled();

    await user.click(screen.getAllByRole("link", { name: "Study" })[0]);
    expect(screen.getByRole("heading", { name: "Nenhuma Study vinculada", level: 1 })).toBeInTheDocument();
    expect(screen.queryByText("study-revision-stub-03")).not.toBeInTheDocument();

    await user.click(screen.getAllByRole("link", { name: "Runs" })[0]);
    expect(
      await screen.findByRole("heading", { name: "Nenhuma Run disponível", level: 2 }),
    ).toBeInTheDocument();
    expect(screen.queryByText("run:stub-ri-0723-a")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Run stub/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Loading" })).not.toBeInTheDocument();
  });

  test("start e presets não contornam Admission rejeitado ou Study ausente", () => {
    const initial = createInitialState();
    const afterPreset = operatorReducer(initial, { type: "RUN_PRESET", preset: "completed" });
    const afterStart = operatorReducer(afterPreset, { type: "RUN_START" });

    expect(afterStart.runsByProjectId[initial.currentProjectId]).toEqual(
      initial.runsByProjectId[initial.currentProjectId],
    );

    const withoutStudy = operatorReducer(initial, {
      type: "PROJECT_SELECT",
      projectId: "project-context-drift-stub",
    });
    expect(operatorReducer(withoutStudy, { type: "RUN_PRESET", preset: "failed" })).toBe(
      withoutStudy,
    );
    expect(operatorReducer(withoutStudy, { type: "RUN_START" })).toBe(withoutStudy);
  });
});
