import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "../src/App.jsx";

function renderAt(path = "/") {
  window.history.replaceState({}, "", path);
  return render(<App />);
}

async function openChat(user) {
  const chatText = screen.getByText("Chat", { selector: "strong" });
  await user.click(chatText.closest("button"));
}

beforeEach(() => {
  window.history.replaceState({}, "", "/");
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

describe("Spatial Trace", () => {
  it("navega entre as quatro rotas e reage ao histórico do browser", async () => {
    const user = userEvent.setup();
    renderAt();

    expect(screen.getByRole("heading", { name: /Seu experimento continua/ })).toBeInTheDocument();
    await user.click(screen.getAllByRole("link", { name: "Projects" })[0]);
    expect(
      await screen.findByRole("heading", { name: "Escopos com limites visíveis." }),
    ).toBeInTheDocument();
    expect(window.location.pathname).toBe("/projects");

    await user.click(screen.getAllByRole("link", { name: "Study" })[0]);
    expect(
      await screen.findByRole("heading", { name: "Respostas com fontes insuficientes" }),
    ).toBeInTheDocument();

    window.history.pushState({}, "", "/runs");
    window.dispatchEvent(new PopStateEvent("popstate"));
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Execução como traço, não como tabela." })).toBeInTheDocument();
    });

    await user.click(screen.getAllByRole("link", { name: "Lab" })[0]);
    expect(window.location.pathname).toBe("/");
  });

  it("valida e cria um Project local sem tratar Project como Workspace", async () => {
    const user = userEvent.setup();
    renderAt("/projects");

    await user.click(screen.getByRole("button", { name: "Criar Project" }));
    const dialog = screen.getByRole("dialog", { name: "Criar Project" });
    await user.click(within(dialog).getByRole("button", { name: "Criar draft" }));
    expect(within(dialog).getByRole("alert")).toHaveTextContent("Informe um nome");

    await user.type(within(dialog).getByLabelText("Nome do Project"), "Citation Boundary");
    await user.type(
      within(dialog).getByLabelText("Objetivo local"),
      "Verificar fronteiras de citação em dados locais.",
    );
    await user.click(within(dialog).getByRole("button", { name: "Criar draft" }));

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(screen.getAllByText("Citation Boundary").length).toBeGreaterThan(0);
    expect(screen.getByText("Vínculo com Workspace indisponível")).toBeInTheDocument();

    const activeTraceStage = document.querySelector('[aria-current="step"] .trace__label');
    expect(activeTraceStage).toHaveTextContent("Intento");
    expect(
      screen.getByRole("link", { name: /StudyRevision/ }),
    ).not.toHaveAttribute("aria-current", "step");

    await user.click(screen.getAllByRole("link", { name: "Study" })[0]);
    expect(
      await screen.findByRole("heading", { name: "Nenhuma Admission representada para este Project." }),
    ).toBeInTheDocument();
    expect(screen.queryByText("stub-revision-07")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Adicionar à fila stub" })).not.toBeInTheDocument();

    await user.click(screen.getAllByRole("link", { name: "Runs" })[0]);
    expect(
      await screen.findByRole("heading", { name: "Nenhuma Run representada para este Project." }),
    ).toBeInTheDocument();
    expect(screen.queryByText("stub-run-evidence-first")).not.toBeInTheDocument();
  });

  it("mantém Study, Admission e Runs vinculados ao Project selecionado", async () => {
    const user = userEvent.setup();
    renderAt("/study");

    const switcher = screen.getByRole("button", { name: /Project selecionado: Retrieval Quality/ });
    await user.click(switcher);
    await user.click(screen.getByRole("option", { name: /Context Drift Review/ }));

    expect(
      screen.getByRole("heading", { name: "Nenhuma Admission representada para este Project." }),
    ).toBeInTheDocument();
    expect(screen.getAllByText("Context Drift Review").length).toBeGreaterThan(0);
    expect(screen.queryByText("stub-revision-07")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Adicionar à fila stub" })).not.toBeInTheDocument();

    await user.click(screen.getAllByRole("link", { name: "Runs" })[0]);
    expect(
      await screen.findByRole("heading", { name: "Nenhuma Run representada para este Project." }),
    ).toBeInTheDocument();
    expect(screen.queryByText("stub-run-evidence-first")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Iniciar Stub Run" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Project selecionado: Context Drift Review/ }));
    await user.click(screen.getByRole("option", { name: /Tool Permission Audit/ }));
    expect(
      screen.getByRole("heading", { name: "Nenhuma Run representada para este Project." }),
    ).toBeInTheDocument();
    expect(screen.getAllByText("Tool Permission Audit").length).toBeGreaterThan(0);
    expect(screen.queryByText("stub-run-evidence-first")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Project selecionado: Tool Permission Audit/ }));
    await user.click(screen.getByRole("option", { name: /Retrieval Quality/ }));
    expect(screen.getByText("stub-run-evidence-first")).toBeInTheDocument();
  });

  it("opera o Project switcher por setas, Enter, Space e Escape com foco restaurado", async () => {
    const user = userEvent.setup();
    renderAt();

    const switcher = screen.getByRole("button", { name: /Project selecionado: Retrieval Quality/ });
    switcher.focus();
    await user.keyboard("{ArrowDown}");

    const retrieval = screen.getByRole("option", { name: /Retrieval Quality/ });
    const context = screen.getByRole("option", { name: /Context Drift Review/ });
    expect(retrieval).toHaveFocus();

    await user.keyboard("{ArrowDown}{Enter}");
    await waitFor(() => {
      expect(screen.queryByRole("listbox", { name: "Selecionar Project" })).not.toBeInTheDocument();
    });
    expect(switcher).toHaveFocus();
    expect(switcher).toHaveTextContent("Context Drift Review");

    await user.keyboard("{ArrowDown}{ArrowUp}{Space}");
    expect(switcher).toHaveFocus();
    expect(switcher).toHaveTextContent("Retrieval Quality");

    await user.keyboard("{ArrowDown}");
    expect(screen.getByRole("option", { name: /Retrieval Quality/ })).toHaveFocus();
    await user.keyboard("{Escape}");
    await waitFor(() => {
      expect(screen.queryByRole("listbox", { name: "Selecionar Project" })).not.toBeInTheDocument();
    });
    expect(switcher).toHaveFocus();
    expect(context).not.toBeInTheDocument();
  });

  it("mantém o enqueue fechado para Admission rejeitada e cria correção append-only", async () => {
    const user = userEvent.setup();
    renderAt("/study");

    const enqueueButtons = screen.getAllByRole("button", { name: "Adicionar à fila stub" });
    expect(enqueueButtons).toHaveLength(2);
    expect(enqueueButtons[0]).toBeDisabled();
    expect(enqueueButtons[1]).toBeEnabled();
    expect(screen.getByText("3 interações")).toBeInTheDocument();
    expect(screen.getByText("1 interação", { selector: "dd" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Corrigir em novo draft" }));
    expect(
      screen.getByRole("heading", { name: "Correção preparada sem reescrever o record rejeitado." }),
    ).toBeInTheDocument();
    expect(enqueueButtons[0]).toBeDisabled();
  });

  it("executa a sequência queued, preparing, running, evaluating e terminal", async () => {
    vi.useFakeTimers();
    renderAt("/runs");

    fireEvent.click(screen.getByRole("button", { name: "Iniciar Stub Run" }));
    expect(screen.getByText("run.queued")).toBeInTheDocument();

    act(() => vi.advanceTimersByTime(380));
    expect(screen.getByText("Preparando", { selector: ".run-state" })).toBeInTheDocument();

    act(() => vi.advanceTimersByTime(400));
    expect(screen.getByText("subject.invoked")).toBeInTheDocument();
    expect(screen.getByText("tool.called")).toBeInTheDocument();
    expect(screen.getByText("tool.completed")).toBeInTheDocument();
    expect(screen.getByText("subject.responded")).toBeInTheDocument();

    act(() => vi.advanceTimersByTime(1000));
    expect(screen.getByText("run.completed")).toBeInTheDocument();
    expect(screen.getByText("Terminal", { selector: ".run-state" })).toBeInTheDocument();
  });

  it("renderiza User, Agent, atividade observável, Tool Call e Tool Result", async () => {
    vi.useFakeTimers();
    renderAt();
    fireEvent.click(screen.getByText("Chat", { selector: "strong" }).closest("button"));

    const composer = screen.getByLabelText("Mensagem para o Lab Agent");
    fireEvent.change(composer, { target: { value: "Prepare um draft local" } });
    fireEvent.click(screen.getByRole("button", { name: "Enviar mensagem" }));
    expect(screen.getByText("Você")).toBeInTheDocument();
    expect(screen.getByRole("status", { name: "Agente resolvendo o traço" })).toBeInTheDocument();

    act(() => vi.advanceTimersByTime(1000));
    expect(screen.getByText("Atividade observável")).toBeInTheDocument();
    expect(screen.getByText("Tool Call")).toBeInTheDocument();
    expect(screen.getByText("Tool Result")).toBeInTheDocument();
    expect(screen.getAllByText("Agent").length).toBeGreaterThan(0);
    expect(screen.getByText(/Draft local preparado/)).toBeInTheDocument();
  });

  it("mantém o foco no composer durante o envio determinístico", async () => {
    const user = userEvent.setup();
    renderAt();
    await openChat(user);

    const composer = screen.getByLabelText("Mensagem para o Lab Agent");
    await user.click(composer);
    await user.type(composer, "Prepare outro draft local");
    await user.click(screen.getByRole("button", { name: "Enviar mensagem" }));

    expect(composer).toHaveFocus();
    expect(composer).toHaveAttribute("readonly");
    expect(document.body).not.toHaveFocus();

    await waitFor(() => expect(composer).not.toHaveAttribute("readonly"), { timeout: 1600 });
    expect(composer).toHaveFocus();

    await user.type(composer, "falhar de forma controlada");
    await user.click(screen.getByRole("button", { name: "Enviar mensagem" }));
    expect(composer).toHaveFocus();
    expect(composer).toHaveAttribute("readonly");

    await waitFor(() => expect(composer).not.toHaveAttribute("readonly"), { timeout: 1600 });
    expect(composer).toHaveFocus();
    expect(screen.getByText(/sequência stub terminou em falha controlada/)).toBeInTheDocument();

    await user.tab();
    expect(
      screen.getByRole("button", { name: "Segure para escolher o encaixe do Chat" }),
    ).toHaveFocus();
  });

  it("oferece snaps explícitos para teclado e altera a geometria do Chat", async () => {
    const user = userEvent.setup();
    renderAt();
    await openChat(user);

    const tall = screen.getByRole("button", { name: "Alto" });
    await user.click(tall);
    expect(tall).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("complementary", { name: "Chat lateral do Lab Agent" })).toHaveClass(
      "chat-dock--tall",
    );

    const full = screen.getByRole("button", { name: "Thread completo" });
    await user.click(full);
    expect(full).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("complementary", { name: "Chat lateral do Lab Agent" })).toHaveClass(
      "chat-dock--full",
    );
  });

  it("revela previews após segurar o grip e aplica somente um snap controlado", () => {
    vi.useFakeTimers();
    const { container } = renderAt();
    fireEvent.click(screen.getByText("Chat", { selector: "strong" }).closest("button"));
    const grip = screen.getByRole("button", { name: "Segure para escolher o encaixe do Chat" });

    fireEvent.pointerDown(grip, { pointerId: 7, clientX: 360, clientY: 540 });
    act(() => vi.advanceTimersByTime(360));
    expect(container.querySelector(".snap-previews")).toBeInTheDocument();

    fireEvent.pointerMove(grip, { pointerId: 7, clientX: 100, clientY: 100 });
    fireEvent.pointerUp(grip, { pointerId: 7, clientX: 100, clientY: 100 });
    expect(container.querySelector(".snap-previews")).not.toBeInTheDocument();
    expect(screen.getByRole("complementary", { name: "Chat lateral do Lab Agent" })).toHaveClass(
      "chat-dock--full",
    );
  });
});
