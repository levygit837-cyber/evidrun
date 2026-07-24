import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import type { LaboratoryAdapter } from "../../data/contracts";
import { DemoLaboratoryAdapter } from "./DemoLaboratoryAdapter";
import { LaboratoryPage } from "./LaboratoryPage";

afterEach(cleanup);

function renderLaboratory(
  adapter: LaboratoryAdapter = new DemoLaboratoryAdapter({ delayMs: 0 }),
) {
  const result = render(<LaboratoryPage adapter={adapter} />);
  const root = result.container.querySelector<HTMLElement>(".laboratory");
  if (!root) throw new Error("Laboratory root not found");
  return { ...result, root };
}

describe("LaboratoryPage", () => {
  it("starts centered, becomes ready, and preserves the exact first message on Enter", async () => {
    const { root } = renderLaboratory();
    const textarea = screen.getByLabelText(
      "Mensagem para a demonstração do Laboratory",
    );
    const exactMessage = "  Primeira linha\nsegunda linha com espaços  ";

    expect(root).toHaveAttribute("data-state", "empty");
    fireEvent.change(textarea, { target: { value: exactMessage } });
    expect(root).toHaveAttribute("data-state", "ready");
    fireEvent.keyDown(textarea, { key: "Enter", shiftKey: false });

    await waitFor(() =>
      expect(root).toHaveAttribute("data-state", "completed"),
    );
    expect(resultMessage(root, ".laboratory-user-message p")).toBe(
      exactMessage,
    );
    expect(screen.getByText("Atividade auditável")).toBeInTheDocument();
    expect(
      screen.getByText(/não contém resultados de uma Run real/i),
    ).toBeInTheDocument();
    expect(root).toHaveAttribute("data-conversation", "started");
    expect(root.querySelector(".laboratory-fresh-state")).toHaveAttribute(
      "aria-hidden",
      "true",
    );
  });

  it("keeps Shift+Enter available for a newline instead of submitting", () => {
    const { root } = renderLaboratory();
    const textarea = screen.getByLabelText(
      "Mensagem para a demonstração do Laboratory",
    );

    fireEvent.change(textarea, { target: { value: "linha um" } });
    fireEvent.keyDown(textarea, { key: "Enter", shiftKey: true });

    expect(root).toHaveAttribute("data-state", "ready");
    expect(screen.queryByText("Você")).not.toBeInTheDocument();
  });

  it("caps textarea auto-growth at 160 pixels", () => {
    renderLaboratory();
    const textarea = screen.getByLabelText<HTMLTextAreaElement>(
      "Mensagem para a demonstração do Laboratory",
    );
    Object.defineProperty(textarea, "scrollHeight", {
      configurable: true,
      value: 260,
    });

    fireEvent.input(textarea);

    expect(textarea.style.height).toBe("160px");
  });

  it("turns send into cancel and reaches the cancelled state", async () => {
    const { root } = renderLaboratory(
      new DemoLaboratoryAdapter({ delayMs: 100 }),
    );
    const textarea = screen.getByLabelText(
      "Mensagem para a demonstração do Laboratory",
    );

    fireEvent.change(textarea, {
      target: { value: "Demonstração longa para cancelar" },
    });
    fireEvent.click(screen.getByLabelText("Enviar mensagem"));
    const cancelButton = await screen.findByLabelText("Cancelar demonstração");
    fireEvent.click(cancelButton);

    await waitFor(() =>
      expect(root).toHaveAttribute("data-state", "cancelled"),
    );
    expect(
      screen.getByText("Demonstração cancelada", { selector: "strong" }),
    ).toBeInTheDocument();
  });

  it("shows expandable Lucide tool calls in chronological order", async () => {
    const { root } = renderLaboratory();
    const textarea = screen.getByLabelText(
      "Mensagem para a demonstração do Laboratory",
    );
    fireEvent.change(textarea, {
      target: { value: "Use ferramentas para inspecionar o Run Demo." },
    });
    fireEvent.click(screen.getByLabelText("Enviar mensagem"));

    await waitFor(() =>
      expect(root).toHaveAttribute("data-state", "completed"),
    );
    const toolNames = Array.from(
      root.querySelectorAll(".laboratory-tool-name"),
    ).map((element) => element.textContent);
    expect(toolNames).toEqual([
      "search_repository",
      "compile_subject",
      "inspect_run",
    ]);

    fireEvent.click(screen.getByText("search_repository"));
    expect(
      screen.getByText("3 referências demonstrativas encontradas."),
    ).toBeVisible();
    expect(
      root.querySelectorAll(".laboratory-tool svg").length,
    ).toBeGreaterThan(0);
  });

  it("exposes failed and retry states without implying backend execution", async () => {
    const { root } = renderLaboratory();
    const textarea = screen.getByLabelText(
      "Mensagem para a demonstração do Laboratory",
    );
    fireEvent.change(textarea, {
      target: { value: "Simule uma falha e permita uma nova tentativa." },
    });
    fireEvent.click(screen.getByLabelText("Enviar mensagem"));

    await waitFor(() => expect(root).toHaveAttribute("data-state", "failed"));
    expect(
      screen.getByText(/Nenhum backend foi acionado/i),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /tentar novamente/i }));

    await waitFor(() =>
      expect(root).toHaveAttribute("data-state", "completed"),
    );
    expect(
      screen.getByText(/recuperado na nova tentativa/i),
    ).toBeInTheDocument();
  });

  it("locks submission synchronously against double submit", async () => {
    let sendCalls = 0;
    let release: (() => void) | undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    const adapter: LaboratoryAdapter = {
      mode: "demo",
      async *send() {
        sendCalls += 1;
        await gate;
        yield { type: "done", source: "demo" };
      },
    };
    const { root } = renderLaboratory(adapter);
    const textarea = screen.getByLabelText(
      "Mensagem para a demonstração do Laboratory",
    );
    const sendButton = screen.getByLabelText("Enviar mensagem");
    fireEvent.change(textarea, { target: { value: "Enviar uma única vez" } });

    act(() => {
      sendButton.click();
      sendButton.click();
    });

    await waitFor(() => expect(sendCalls).toBe(1));
    release?.();
    await waitFor(() =>
      expect(root).toHaveAttribute("data-state", "completed"),
    );
  });

  it("labels visual-only settings and supports roving menu focus", async () => {
    renderLaboratory();
    expect(
      screen.getByText("Configuração visual Demo · não aplicada"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Demo local determinística · nenhum provider consultado",
      ),
    ).toBeInTheDocument();
    const trigger = screen.getByLabelText(
      "Selecionar modo de aprovação visual Demo, não aplicado",
    );

    fireEvent.keyDown(trigger, { key: "ArrowDown" });
    const ask = await screen.findByRole("menuitemradio", {
      name: "Ask before actions",
    });
    const readOnly = screen.getByRole("menuitemradio", { name: "Read-only" });
    const admitted = screen.getByRole("menuitemradio", {
      name: "Allow admitted tools",
    });
    await waitFor(() => expect(ask).toHaveFocus());

    fireEvent.keyDown(ask, { key: "ArrowDown" });
    await waitFor(() => expect(readOnly).toHaveFocus());
    fireEvent.keyDown(readOnly, { key: "End" });
    await waitFor(() => expect(admitted).toHaveFocus());
    fireEvent.keyDown(admitted, { key: "Home" });
    await waitFor(() => expect(ask).toHaveFocus());
    fireEvent.keyDown(ask, { key: "Escape" });
    await waitFor(() => expect(trigger).toHaveFocus());
    expect(trigger).toHaveAttribute("aria-expanded", "false");

    fireEvent.keyDown(trigger, { key: "ArrowDown" });
    await waitFor(() =>
      expect(
        screen.getByRole("menuitemradio", { name: "Ask before actions" }),
      ).toHaveFocus(),
    );
    fireEvent.click(screen.getByRole("menuitemradio", { name: "Read-only" }));
    await waitFor(() => expect(trigger).toHaveFocus());
    expect(trigger).toHaveTextContent("Read-only");
  });

  it("fails closed into unavailable when the injected adapter has no capability", () => {
    const unavailableAdapter: LaboratoryAdapter = {
      mode: "integration_pending",
      async *send() {
        throw new Error("send must not be reached");
      },
    };
    const { root } = renderLaboratory(unavailableAdapter);

    expect(root).toHaveAttribute("data-state", "unavailable");
    expect(
      screen.getByRole("heading", { name: "Laboratory indisponível" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Nenhuma mensagem foi enviada."),
    ).toBeInTheDocument();
    expect(
      screen.queryByLabelText("Mensagem para a demonstração do Laboratory"),
    ).not.toBeInTheDocument();
    expect(
      root.querySelector(".laboratory-composer-position"),
    ).not.toBeInTheDocument();
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    expect(
      screen.queryByLabelText(
        "Selecionar modo de aprovação visual Demo, não aplicado",
      ),
    ).not.toBeInTheDocument();
  });
});

function resultMessage(root: HTMLElement, selector: string) {
  const element = root.querySelector(selector);
  if (!element) throw new Error(`Expected ${selector}`);
  return element.textContent;
}
