import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";
import { App } from "./App.jsx";

function renderAt(route = "lab") {
  window.history.replaceState(null, "", `${window.location.pathname}#/${route}`);
  return render(<App />);
}

async function openChat(user) {
  await user.click(screen.getByRole("button", { name: "Abrir Chat" }));
  return screen.getByRole("textbox", { name: "Mensagem para o Lab Agent" });
}

describe("Command Deck", () => {
  beforeEach(() => {
    window.history.replaceState(null, "", `${window.location.pathname}#/lab`);
  });

  test("navigates through stable hash routes", async () => {
    const user = userEvent.setup();
    renderAt();

    const desktopNavigation = screen.getByRole("navigation", { name: "Navegação principal" });
    await user.click(within(desktopNavigation).getByRole("link", { name: "Projects" }));

    expect(await screen.findByRole("heading", { level: 1, name: "Projects" })).toBeInTheDocument();
    expect(window.location.hash).toBe("#/projects");

    await user.click(within(desktopNavigation).getByRole("link", { name: "Study" }));
    expect(await screen.findByRole("heading", { level: 1, name: "Study" })).toBeInTheDocument();
  });

  test("keeps send disabled for an empty composer and preserves Shift+Enter", async () => {
    const user = userEvent.setup();
    renderAt();
    const composer = await openChat(user);
    const sendButton = screen.getByRole("button", { name: "Enviar mensagem" });

    expect(sendButton).toBeDisabled();
    await user.type(composer, "linha um{Shift>}{Enter}{/Shift}linha dois");
    expect(composer).toHaveValue("linha um\nlinha dois");
    expect(sendButton).toBeEnabled();
  });

  test("executes the deterministic send flow with observable activity and tool result", async () => {
    const user = userEvent.setup();
    renderAt();
    const composer = await openChat(user);

    await user.type(composer, "Diagnostique o trecho autorizado");
    await user.click(screen.getByRole("button", { name: "Enviar mensagem" }));

    expect(screen.getByRole("status", { name: "Execução do stub em andamento" })).toBeInTheDocument();
    expect(composer).toHaveFocus();
    expect(screen.getByText("Diagnostique o trecho autorizado")).toBeInTheDocument();

    expect(
      await screen.findByText(/O stub encontrou um sinal de latência/, {}, { timeout: 2600 }),
    ).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Tool Call read_text" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Tool Result local" })).toHaveTextContent("Stub local");
    expect(screen.getByText(/23:16:42 endpoint/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Atividade observável/ }));
    expect(screen.getByText("Resposta capturada")).toBeInTheDocument();
  });

  test("fails Admission closed and disables enqueue", async () => {
    const user = userEvent.setup();
    renderAt("study");

    await user.click(screen.getByRole("button", { name: "Rejeitada" }));
    expect(screen.getByRole("button", { name: "Enqueue Stub" })).toBeDisabled();
    expect(screen.getByText("Enqueue bloqueado")).toBeInTheDocument();
    expect(screen.getByText(/Corrija o draft e compile novos RunSpecs/)).toBeInTheDocument();
    expect(screen.getAllByText("Rejected")).toHaveLength(2);
  });

  test("traps reverse focus in the Project dialog and restores the trigger on Escape", async () => {
    const user = userEvent.setup();
    renderAt("projects");
    const trigger = screen.getByRole("button", { name: "Novo Project" });

    await user.click(trigger);
    const dialog = screen.getByRole("dialog", { name: "Criar Project local" });
    const close = within(dialog).getByRole("button", { name: "Fechar diálogo" });
    const create = within(dialog).getByRole("button", { name: "Criar Project" });

    close.focus();
    fireEvent.keyDown(window, { key: "Tab", shiftKey: true });
    expect(create).toHaveFocus();

    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByRole("dialog", { name: "Criar Project local" })).not.toBeInTheDocument();
    await waitFor(() => expect(trigger).toHaveFocus());
  });

  test("offers keyboard snap alternatives and a hold preview", async () => {
    const user = userEvent.setup();
    renderAt();
    await openChat(user);
    const grip = screen.getByTestId("chat-grip");

    fireEvent.keyDown(grip, { key: "End" });
    expect(screen.getByLabelText("Chat adaptativo do Lab Agent")).toHaveAttribute("data-layout", "full");

    vi.useFakeTimers();
    fireEvent.pointerDown(grip, { pointerId: 1, clientY: 700 });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(351);
    });
    expect(screen.getByTestId("snap-preview")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Meia altura" })).toBeInTheDocument();
  });

  test("preserves Chat draft while navigating within the session", async () => {
    const user = userEvent.setup();
    renderAt();
    const composer = await openChat(user);
    await user.type(composer, "rascunho persistente");

    const desktopNavigation = screen.getByRole("navigation", { name: "Navegação principal" });
    await user.click(within(desktopNavigation).getByRole("link", { name: "Runs" }));

    expect(await screen.findByRole("heading", { level: 1, name: "Runs" })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Mensagem para o Lab Agent" })).toHaveValue("rascunho persistente");
  });

  test("progresses a stub Run to terminal completed", async () => {
    vi.useFakeTimers();
    renderAt("runs");

    fireEvent.click(screen.getByRole("button", { name: "Start Stub Run" }));
    expect(screen.getAllByText("Queued").length).toBeGreaterThan(0);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(2400);
    });

    expect(screen.getByText("Terminal completed")).toBeInTheDocument();
    expect(screen.getByText("Evidence")).toBeInTheDocument();
    expect(screen.getByText("Não replayable")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run encerrada" })).toBeDisabled();
  });

  test("represents a failed terminal Run without inventing evaluation", async () => {
    const user = userEvent.setup();
    renderAt("runs");

    await user.click(screen.getByRole("button", { name: "Failed" }));
    const progression = screen.getByRole("list", { name: "Progressão de eventos da Run" });
    const running = within(progression).getByText("Running").closest("li");
    const evaluating = within(progression).getByText("Evaluating").closest("li");
    const terminal = within(progression).getByText("Terminal").closest("li");

    expect(screen.getByText("Terminal failed")).toBeInTheDocument();
    expect(running).toHaveAttribute("data-current", "false");
    expect(evaluating).toHaveAttribute("data-reached", "false");
    expect(within(evaluating).getByText("reserved until phase")).toBeInTheDocument();
    expect(terminal).toHaveAttribute("data-reached", "true");
    expect(terminal).toHaveAttribute("data-current", "true");
    expect(within(terminal).getByText("event-run-failed-001")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run encerrada" })).toBeDisabled();
    expect(screen.queryByText("Evidence")).not.toBeInTheDocument();
  });

  test("commits terminal state atomically and keeps Start disabled in flight", async () => {
    vi.useFakeTimers();
    renderAt("runs");

    fireEvent.click(screen.getByRole("button", { name: "Start Stub Run" }));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1600);
    });

    const progression = screen.getByRole("list", { name: "Progressão de eventos da Run" });
    const terminal = within(progression).getByText("Terminal").closest("li");
    expect(terminal).toHaveAttribute("data-reached", "false");
    expect(screen.getByRole("button", { name: "Stub Run em andamento" })).toBeDisabled();
    expect(screen.getByText("O estado terminal ainda não foi registrado.")).toBeInTheDocument();
    expect(screen.queryByText("Terminal completed")).not.toBeInTheDocument();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(80);
    });

    expect(screen.getByText("Terminal completed")).toBeInTheDocument();
    expect(terminal).toHaveAttribute("data-reached", "true");
    expect(screen.getByRole("button", { name: "Run encerrada" })).toBeDisabled();
  });
});
