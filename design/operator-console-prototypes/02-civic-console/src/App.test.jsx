import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { App } from "./App.jsx";

function firstNavLink(name) {
  return screen.getAllByRole("link", { name })[0];
}

describe("Civic Console", () => {
  it("navega pelas quatro rotas e responde ao histórico do browser", async () => {
    const user = userEvent.setup();
    render(<App />);

    expect(screen.getByRole("heading", { level: 1, name: "Retrieval Quality" })).toBeVisible();

    await user.click(firstNavLink("Projects"));
    expect(screen.getByRole("heading", { level: 1, name: "Escopo antes da execução" })).toBeVisible();
    expect(window.location.pathname).toBe("/projects");

    await user.click(firstNavLink("Study"));
    expect(
      screen.getByRole("heading", {
        level: 1,
        name: "Respostas com fontes insuficientes",
      }),
    ).toBeVisible();
    expect(window.location.pathname).toBe("/study");

    await user.click(firstNavLink("Runs"));
    expect(screen.getByRole("heading", { level: 1, name: "Execução determinística" })).toBeVisible();

    window.history.pushState({}, "", "/");
    fireEvent.popState(window);
    expect(await screen.findByRole("heading", { level: 1, name: "Retrieval Quality" })).toBeVisible();
  });

  it("falha fechado sem atribuir records de Retrieval Quality a outro Project", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(firstNavLink("Projects"));
    await user.click(
      screen.getByRole("button", {
        name: "Disclosure Boundary Verificar o limite de disclosure antes da execução.",
      }),
    );

    await user.click(firstNavLink("Lab"));
    expect(screen.getByRole("heading", { level: 1, name: "Disclosure Boundary" })).toBeVisible();
    expect(
      screen.getByRole("heading", {
        level: 2,
        name: "Lab indisponível para este Project",
      }),
    ).toBeVisible();
    expect(screen.queryByText("REV-STUB-002")).not.toBeInTheDocument();
    expect(screen.queryByText("direct-answer")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("textbox", { name: "Mensagem para o Lab Agent" }),
    ).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Abrir Chat" }));
    const disclosureChat = screen.getByLabelText("Chat");
    expect(disclosureChat).toHaveTextContent("0 mensagens · Disclosure Boundary");
    expect(disclosureChat).toHaveTextContent("Nenhuma conversa neste Project.");
    expect(screen.queryByText("Posso ajudar a preparar a próxima revisão.")).not.toBeInTheDocument();

    await user.click(firstNavLink("Study"));
    expect(
      screen.getByRole("heading", {
        level: 2,
        name: "Study indisponível para este Project",
      }),
    ).toBeVisible();
    expect(screen.queryByText("REV-STUB-002")).not.toBeInTheDocument();

    await user.click(firstNavLink("Runs"));
    expect(
      screen.getByRole("heading", {
        level: 2,
        name: "Runs indisponível para este Project",
      }),
    ).toBeVisible();
    expect(screen.queryByText("JOB-STUB-039")).not.toBeInTheDocument();
  });

  it("mantém envio vazio desabilitado, aceita Shift+Enter e envia com Enter", async () => {
    const user = userEvent.setup();
    render(<App />);
    const input = screen.getByRole("textbox", { name: "Mensagem para o Lab Agent" });
    const send = screen.getByRole("button", { name: "Enviar mensagem" });

    expect(send).toBeDisabled();
    await user.type(input, "Linha 1{Shift>}{Enter}{/Shift}Linha 2");
    expect(input).toHaveValue("Linha 1\nLinha 2");
    expect(send).toBeEnabled();
    expect(screen.getByText("read_text")).toBeVisible();

    await user.keyboard("{Enter}");
    expect(screen.getAllByText(/Linha 1/)).toHaveLength(2);
    expect(input).toHaveFocus();
    expect(screen.getByText("Atividade observável")).toBeVisible();
  });

  it("preserva thread e draft do composer ao navegar entre rotas", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.selectOptions(screen.getByRole("combobox", { name: "Preset do agente" }), "idle");
    const input = screen.getByRole("textbox", { name: "Mensagem para o Lab Agent" });
    await user.type(input, "Mensagem persistente");
    await user.keyboard("{Enter}");
    await user.type(input, "Draft ainda não enviado");
    await user.click(screen.getByRole("button", { name: "Abrir Chat" }));

    expect(screen.getAllByText("Mensagem persistente")).toHaveLength(2);
    await user.click(firstNavLink("Projects"));
    expect(screen.getByLabelText("Chat")).toHaveAttribute("data-chat-state", "compact");
    expect(screen.getByText("Mensagem persistente")).toBeVisible();

    await user.click(firstNavLink("Lab"));
    expect(
      screen.getByRole("textbox", { name: "Mensagem para o Lab Agent" }),
    ).toHaveValue("Draft ainda não enviado");
    expect(screen.getAllByText("Mensagem persistente")).toHaveLength(2);
  });

  it("mantém collapse, close e snaps do Chat como ações distintas", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: "Abrir Chat" }));
    let chat = screen.getByLabelText("Chat");
    expect(chat).toHaveAttribute("data-chat-state", "compact");

    await user.click(screen.getByRole("button", { name: "Expandir largura do Chat" }));
    chat = screen.getByLabelText("Chat");
    expect(chat).toHaveAttribute("data-chat-state", "full");
    await user.click(screen.getByRole("button", { name: "Reduzir largura do Chat" }));
    chat = screen.getByLabelText("Chat");
    expect(chat).toHaveAttribute("data-chat-state", "half");

    const grip = screen.getByRole("button", {
      name: "Segure para visualizar encaixes do Chat",
    });
    grip.focus();
    await user.keyboard("{ArrowLeft}");
    expect(screen.getByRole("option", { name: "Metade" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    await user.keyboard("{Enter}");
    chat = screen.getByLabelText("Chat");
    expect(chat).toHaveAttribute("data-chat-state", "half");

    await user.click(screen.getByRole("button", { name: "Alterar altura do Chat" }));
    chat = screen.getByLabelText("Chat");
    expect(chat).toHaveAttribute("data-chat-state", "tall");

    await user.click(screen.getByRole("button", { name: "Recolher Chat" }));
    await waitFor(() => expect(screen.getByLabelText("Chat recolhido")).toBeVisible());

    await user.click(screen.getByRole("button", { name: "Abrir Chat" }));
    await user.click(screen.getByRole("button", { name: "Mostrar encaixes do Chat" }));
    await user.click(screen.getByRole("option", { name: "Alto" }));
    expect(screen.getByLabelText("Chat")).toHaveAttribute("data-chat-state", "tall");

    await user.click(screen.getByRole("button", { name: "Fechar Chat" }));
    expect(screen.getByRole("button", { name: "Reabrir Chat" })).toBeVisible();
  });

  it("mostra a geometria de snap após hold e confirma a seleção ao soltar", () => {
    vi.useFakeTimers();
    try {
      render(<App />);
      fireEvent.click(screen.getByRole("button", { name: "Abrir Chat" }));
      const grip = screen.getByRole("button", {
        name: "Segure para visualizar encaixes do Chat",
      });

      fireEvent.pointerDown(grip, { pointerId: 1, pointerType: "touch" });
      act(() => vi.advanceTimersByTime(360));
      expect(screen.getByRole("listbox", { name: "Encaixes do Chat" })).toBeInTheDocument();
      expect(grip).toHaveAttribute("aria-expanded", "true");

      fireEvent.pointerUp(grip, { pointerId: 1, pointerType: "touch" });
      expect(grip).toHaveAttribute("aria-expanded", "false");
      expect(screen.getByLabelText("Chat")).toHaveAttribute("data-chat-state", "compact");
    } finally {
      vi.useRealTimers();
    }
  });

  it("falha fechado e habilita enqueue somente após corrigir e compilar a revisão", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(firstNavLink("Study"));

    let enqueue = screen.getAllByRole("button", { name: "Enfileirar" });
    expect(enqueue[0]).toBeDisabled();
    expect(enqueue[1]).toBeEnabled();

    await user.click(screen.getByRole("button", { name: "Nova revisão local" }));
    expect(screen.getByRole("checkbox", { name: /Cobertura de fontes autorizadas/ })).toBeChecked();

    await user.click(screen.getByRole("button", { name: "Compilar e validar" }));
    enqueue = screen.getAllByRole("button", { name: "Enfileirar" });
    expect(enqueue[0]).toBeEnabled();
    expect(screen.getByText("Os dois RunSpecs possuem AdmissionRecord admitted neste stub local.")).toBeVisible();
  });

  it("mantém todos os presets de Run bloqueados quando a Admission está rejected", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(firstNavLink("Runs"));

    expect(screen.getByRole("button", { name: "Start Stub Run" })).toBeDisabled();
    for (const preset of ["Loading", "Failed", "Completed"]) {
      expect(screen.getByRole("button", { name: preset })).toBeDisabled();
    }

    await user.click(screen.getByRole("button", { name: "Completed" }));
    expect(screen.queryByText("JOB-STUB-039")).not.toBeInTheDocument();
    expect(screen.queryByText("ATTEMPT-STUB-01")).not.toBeInTheDocument();
    expect(
      screen.getByText("Presets não criam uma Run sem AdmissionRecord admitted."),
    ).toBeVisible();
  });

  it("executa as fases determinísticas e mantém job e attempt separados", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(firstNavLink("Study"));
    await user.click(screen.getByRole("button", { name: "Nova revisão local" }));
    await user.click(screen.getByRole("button", { name: "Compilar e validar" }));
    await user.click(firstNavLink("Runs"));

    const start = screen.getByRole("button", { name: "Start Stub Run" });
    expect(start).toBeEnabled();
    await user.click(start);

    const lifecycle = screen.getByRole("heading", { name: "Lifecycle da Run" }).closest("section");
    expect(within(lifecycle).getByText("JOB-STUB-042")).toBeVisible();
    expect(within(lifecycle).getByText("ATTEMPT-STUB-01")).toBeVisible();

    await waitFor(
      () => {
        expect(within(lifecycle).getByText("Completed")).toBeVisible();
        expect(within(lifecycle).getByText("Tool event ilustrativo")).toBeVisible();
      },
      { timeout: 3500 },
    );
  });

  it("prende o foco no diálogo, fecha com Escape e retorna ao gatilho", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(firstNavLink("Projects"));
    const trigger = screen.getByRole("button", { name: "Novo Project" });
    await user.click(trigger);

    const nameInput = screen.getByLabelText("Nome do Project");
    const intentInput = screen.getByLabelText("Intent");
    await waitFor(() => expect(nameInput).toHaveFocus());

    await user.click(screen.getByRole("button", { name: "Criar Project" }));
    expect(nameInput).toHaveFocus();
    expect(nameInput).toHaveAttribute("aria-invalid", "true");

    await user.type(nameInput, "Focus Boundaries");
    await user.click(screen.getByRole("button", { name: "Criar Project" }));
    expect(intentInput).toHaveFocus();
    expect(intentInput).toHaveAttribute("aria-invalid", "true");

    const close = screen.getByRole("button", { name: "Fechar diálogo" });
    const create = screen.getByRole("button", { name: "Criar Project" });
    close.focus();
    await user.tab({ shift: true });
    expect(create).toHaveFocus();

    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });

  it("valida o diálogo de criação e mantém o novo Project apenas no estado React", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(firstNavLink("Projects"));
    await user.click(screen.getByRole("button", { name: "Novo Project" }));

    await user.click(screen.getByRole("button", { name: "Criar Project" }));
    expect(screen.getByRole("alert")).toHaveTextContent("pelo menos 3 caracteres");

    await user.type(screen.getByLabelText("Nome do Project"), "Citation Drift");
    await user.type(
      screen.getByLabelText("Intent"),
      "Verificar divergência de citações em um limite local.",
    );
    await user.click(screen.getByRole("button", { name: "Criar Project" }));

    expect(screen.getAllByText("Citation Drift").length).toBeGreaterThanOrEqual(2);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
