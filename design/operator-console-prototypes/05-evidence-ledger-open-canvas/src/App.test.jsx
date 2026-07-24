import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { App } from "./App.jsx";

function renderApp(path = "/") {
  window.history.replaceState({}, "", path);
  return render(<App />);
}

beforeEach(() => {
  vi.useRealTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("EvidRun operator console prototype", () => {
  test("navigates across all four routes and responds to history state", async () => {
    const user = userEvent.setup();
    renderApp();

    expect(screen.getByRole("heading", { name: "O que você quer investigar?" })).toBeInTheDocument();
    await user.click(within(screen.getByLabelText("Navegação principal")).getByRole("button", { name: "Projetos" }));
    expect(screen.getByRole("heading", { name: "Escopos e proveniência" })).toBeInTheDocument();

    act(() => {
      window.history.pushState({}, "", "/study");
      window.dispatchEvent(new PopStateEvent("popstate", { state: {} }));
    });
    expect(await screen.findByRole("heading", { name: "Preservação da causa-raiz em logs longos" })).toBeInTheDocument();

    await user.click(within(screen.getByLabelText("Navegação principal")).getByRole("button", { name: "Runs & Evidence" }));
    expect(screen.getByRole("heading", { name: "Run completed" })).toBeInTheDocument();
  });

  test("switches between first-use and returning Lab states", async () => {
    const user = userEvent.setup();
    renderApp();

    expect(screen.getByText("Converse, localize referências ou transforme uma intenção em draft de Study.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Retorno" }));

    expect(screen.getByRole("heading", { name: "Evidência em contexto" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Atividade observável" })).toBeInTheDocument();
    expect(screen.getByText("Tool Call")).toBeInTheDocument();
    expect(screen.getByText("Tool Result")).toBeInTheDocument();
    expect(screen.getByText("Lab Agent · Draft only", { selector: "strong" })).toBeInTheDocument();
  });

  test("composer disables empty send, preserves Shift+Enter, sends on Enter and reaches success", async () => {
    vi.useFakeTimers();
    renderApp();

    const input = screen.getByPlaceholderText("Descreva uma hipótese, uma Run ou a evidência que procura");
    const send = screen.getByRole("button", { name: "Enviar" });
    expect(send).toBeDisabled();

    fireEvent.change(input, { target: { value: "Compare os records\nsem aceitar por mim" } });
    fireEvent.keyDown(input, { key: "Enter", shiftKey: true });
    expect(input).toHaveValue("Compare os records\nsem aceitar por mim");
    fireEvent.keyDown(input, { key: "Enter", shiftKey: false });

    expect(screen.getByLabelText("Lab Agent processando")).toBeInTheDocument();
    expect(screen.getByText("Compare os records sem aceitar por mim", { exact: false })).toBeInTheDocument();

    for (let index = 0; index < 3; index += 1) act(() => vi.advanceTimersByTime(700));
    expect(screen.getByText("Tool Call")).toBeInTheDocument();
    expect(input).toHaveFocus();
  });

  test("Chat persists across routes and supports keyboard snaps, collapse and close", async () => {
    const user = userEvent.setup();
    renderApp();

    await user.click(screen.getByRole("button", { name: "Chat" }));
    const grip = screen.getByRole("slider", { name: "Ajustar encaixe do Chat" });
    expect(grip).toHaveAttribute("aria-valuetext", "compacto");
    await user.type(grip, "{ArrowUp}");
    expect(grip).toHaveAttribute("aria-valuetext", "meia altura");
    await user.type(grip, "{ArrowRight}");
    expect(grip).toHaveAttribute("aria-valuetext", "thread amplo");

    await user.click(within(screen.getByLabelText("Navegação principal")).getByRole("button", { name: "Projetos" }));
    expect(screen.getByText("Project / Context Reliability Lab")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Colapsar thread" }));
    expect(screen.queryByLabelText("Mensagem para o Lab Agent")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Chat contextual")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Fechar Chat" }));
    expect(screen.getByRole("button", { name: "Chat" })).toBeInTheDocument();
  });

  test("validates project creation before adding local state", async () => {
    const user = userEvent.setup();
    renderApp("/projects");

    await user.click(screen.getByRole("button", { name: "Chat" }));
    const crlChatInput = screen.getByLabelText("Mensagem para o Lab Agent");
    await user.type(crlChatInput, "Mensagem exclusiva da fixture CRL{Enter}");
    expect(screen.getByText("Mensagem exclusiva da fixture CRL")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Fechar Chat" }));

    await user.click(screen.getByRole("button", { name: "Criar Project" }));
    const dialog = screen.getByRole("dialog", { name: "Criar Project local" });
    await user.click(within(dialog).getByRole("button", { name: "Criar Project" }));
    expect(within(dialog).getByText("Use pelo menos 3 caracteres.")).toBeInTheDocument();
    expect(within(dialog).getByText("Descreva o escopo em pelo menos 12 caracteres.")).toBeInTheDocument();

    await user.type(within(dialog).getByLabelText("Nome do Project"), "Long Context Audit");
    await user.type(within(dialog).getByLabelText("Descrição"), "Escopo local para uma avaliação controlada.");
    await user.click(within(dialog).getByRole("button", { name: "Criar Project" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Long Context Audit" })).toBeInTheDocument();
  });

  test("keeps non-CRL Projects isolated from the CRL Study, Runs and Chat fixture", async () => {
    const user = userEvent.setup();
    renderApp("/projects");

    await user.click(screen.getByRole("button", { name: "Criar Project" }));
    const dialog = screen.getByRole("dialog", { name: "Criar Project local" });
    await user.type(within(dialog).getByLabelText("Nome do Project"), "Boundary QA Project");
    await user.type(within(dialog).getByLabelText("Descrição"), "Escopo sem records canônicos vinculados.");
    await user.click(within(dialog).getByRole("button", { name: "Criar Project" }));

    await user.click(within(screen.getByLabelText("Navegação principal")).getByRole("button", { name: "Study & Admission" }));
    expect(screen.getByRole("heading", { name: "Nenhuma Study vinculada" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Preservação da causa-raiz em logs longos" })).not.toBeInTheDocument();
    expect(screen.getByText(/CRL-CTX-002 permanece uma fixture separada/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Chat" }));
    expect(screen.getByText("Project / Boundary QA Project · sem Study")).toBeInTheDocument();
    expect(screen.getByText(/não possui Study, Run ou evidência registrada/i)).toBeInTheDocument();
    expect(screen.queryByText("Mensagem exclusiva da fixture CRL")).not.toBeInTheDocument();

    await user.click(within(screen.getByLabelText("Navegação principal")).getByRole("button", { name: "Runs & Evidence" }));
    expect(screen.getByRole("heading", { name: "Nenhuma Run vinculada" })).toBeInTheDocument();
    expect(screen.queryByText("run_019f9100...ae5e5")).not.toBeInTheDocument();
    expect(screen.getByText("Project / Boundary QA Project · sem Run")).toBeInTheDocument();
  });

  test("traps dialog focus, focuses invalid fields and restores the trigger on Escape", async () => {
    const user = userEvent.setup();
    renderApp("/projects");

    const trigger = screen.getByRole("button", { name: "Criar Project" });
    await user.click(trigger);
    const dialog = screen.getByRole("dialog", { name: "Criar Project local" });
    const close = within(dialog).getByRole("button", { name: "Fechar diálogo" });
    const submit = within(dialog).getByRole("button", { name: "Criar Project" });
    const nameInput = within(dialog).getByLabelText("Nome do Project");
    const descriptionInput = within(dialog).getByLabelText("Descrição");

    await user.click(submit);
    await waitFor(() => expect(nameInput).toHaveFocus());

    await user.type(nameInput, "Boundary QA Project");
    await user.click(submit);
    await waitFor(() => expect(descriptionInput).toHaveFocus());

    close.focus();
    fireEvent.keyDown(document, { key: "Tab", shiftKey: true });
    expect(submit).toHaveFocus();
    fireEvent.keyDown(document, { key: "Tab" });
    expect(close).toHaveFocus();

    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("dialog", { name: "Criar Project local" })).not.toBeInTheDocument();
    await waitFor(() => expect(trigger).toHaveFocus());
  });

  test("gates enqueue on exact Admission decision and blocks local revisions", async () => {
    const user = userEvent.setup();
    renderApp("/study");

    const panel = screen.getByRole("heading", { name: "Admission" }).closest("aside");
    const enqueue = within(panel).getByRole("button", { name: "Enfileirar RunSpec" });
    expect(within(panel).getByText("unsupported_execution_contract")).toBeInTheDocument();
    expect(enqueue).toBeDisabled();

    await user.click(within(panel).getByRole("button", { name: "tail-preservation" }));
    expect(within(panel).getByText("Compatível com o runner ativo")).toBeInTheDocument();
    expect(enqueue).toBeEnabled();

    await user.click(within(panel).getByRole("button", { name: "Criar nova revisão" }));
    expect(within(panel).getByText("Compile uma revisão aceita primeiro")).toBeInTheDocument();
    expect(enqueue).toBeDisabled();
  });

  test("shows completed CRL ledger without tools and keeps illustrative tools separate", async () => {
    const user = userEvent.setup();
    renderApp("/runs");

    expect(screen.getByText("9 de 9 eventos da história canônica.")).toBeInTheDocument();
    expect(screen.getByText("run.completed")).toBeInTheDocument();
    expect(screen.queryByText("tool.called · read_text")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Live ilustrativa" }));
    expect(screen.getByText("tool.called · read_text")).toBeInTheDocument();
    expect(screen.getByText(/manifest CRL-CTX-002 não possui tools/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Failed" }));
    expect(screen.getByRole("heading", { name: "Attempt encerrado antes da fase terminal" })).toBeInTheDocument();
    expect(screen.queryByText("run.completed")).not.toBeInTheDocument();
  });

  test("progresses a stub Run through the reducer phase sequence", async () => {
    vi.useFakeTimers();
    renderApp("/runs");

    fireEvent.click(screen.getByRole("button", { name: "Start Stub Run" }));
    expect(screen.getAllByText("demo:run-stub-admitted")).toHaveLength(2);
    expect(screen.getByText("1 de 9 eventos ilustrativos.")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Comparação capturada" })).not.toBeInTheDocument();
    expect(screen.getAllByText("queued", { selector: ".status-badge" }).length).toBeGreaterThanOrEqual(1);
    for (let index = 0; index < 4; index += 1) act(() => vi.advanceTimersByTime(800));
    expect(screen.getByText("9 de 9 eventos ilustrativos.")).toBeInTheDocument();
    expect(screen.getByText("event:demo-stub-09")).toBeInTheDocument();
    expect(screen.getAllByText("demo:run-stub-admitted")).toHaveLength(2);
    expect(screen.getByText("run.completed")).toBeInTheDocument();
    expect(screen.queryByText("run_019f9100...ae5e5")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Completed" }));
    expect(screen.getByText("9 de 9 eventos da história canônica.")).toBeInTheDocument();
    expect(screen.getAllByText("run_019f9100...ae5e5")).toHaveLength(2);
  });
});
