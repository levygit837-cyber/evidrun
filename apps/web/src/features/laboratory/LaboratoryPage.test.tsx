import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import type { LaboratoryAdapter } from "../../data/contracts";
import { DemoLaboratoryAdapter } from "./DemoLaboratoryAdapter";
import { LaboratoryPage } from "./LaboratoryPage";

afterEach(cleanup);

function renderLaboratory(adapter: LaboratoryAdapter = new DemoLaboratoryAdapter({ delayMs: 0 })) {
  const result = render(<LaboratoryPage adapter={adapter} />);
  const root = result.container.querySelector<HTMLElement>(".laboratory");
  if (!root) throw new Error("Laboratory root not found");
  return { ...result, root };
}

describe("LaboratoryPage", () => {
  it("starts centered, becomes ready, and preserves the exact first message on Enter", async () => {
    const { root } = renderLaboratory();
    const textarea = screen.getByLabelText("Mensagem para a demonstração do Laboratory");
    const exactMessage = "  Primeira linha\nsegunda linha com espaços  ";

    expect(root).toHaveAttribute("data-state", "empty");
    fireEvent.change(textarea, { target: { value: exactMessage } });
    expect(root).toHaveAttribute("data-state", "ready");
    fireEvent.keyDown(textarea, { key: "Enter", shiftKey: false });

    await waitFor(() => expect(root).toHaveAttribute("data-state", "completed"));
    expect(resultMessage(root, ".laboratory-user-message p")).toBe(exactMessage);
    expect(screen.getByText("Atividade auditável")).toBeInTheDocument();
    expect(screen.getByText(/não contém resultados de uma Run real/i)).toBeInTheDocument();
  });

  it("keeps Shift+Enter available for a newline instead of submitting", () => {
    const { root } = renderLaboratory();
    const textarea = screen.getByLabelText("Mensagem para a demonstração do Laboratory");

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
    Object.defineProperty(textarea, "scrollHeight", { configurable: true, value: 260 });

    fireEvent.input(textarea);

    expect(textarea.style.height).toBe("160px");
  });

  it("turns send into cancel and reaches the cancelled state", async () => {
    const { root } = renderLaboratory(new DemoLaboratoryAdapter({ delayMs: 100 }));
    const textarea = screen.getByLabelText("Mensagem para a demonstração do Laboratory");

    fireEvent.change(textarea, { target: { value: "Demonstração longa para cancelar" } });
    fireEvent.click(screen.getByLabelText("Enviar mensagem"));
    const cancelButton = await screen.findByLabelText("Cancelar demonstração");
    fireEvent.click(cancelButton);

    await waitFor(() => expect(root).toHaveAttribute("data-state", "cancelled"));
    expect(screen.getByText("Demonstração cancelada", { selector: "strong" })).toBeInTheDocument();
  });

  it("shows expandable Lucide tool calls in chronological order", async () => {
    const { root } = renderLaboratory();
    const textarea = screen.getByLabelText("Mensagem para a demonstração do Laboratory");
    fireEvent.change(textarea, {
      target: { value: "Use ferramentas para inspecionar o Run Demo." },
    });
    fireEvent.click(screen.getByLabelText("Enviar mensagem"));

    await waitFor(() => expect(root).toHaveAttribute("data-state", "completed"));
    const toolNames = Array.from(root.querySelectorAll(".laboratory-tool-name")).map(
      (element) => element.textContent,
    );
    expect(toolNames).toEqual(["search_repository", "compile_subject", "inspect_run"]);

    fireEvent.click(screen.getByText("search_repository"));
    expect(screen.getByText("3 referências demonstrativas encontradas.")).toBeVisible();
    expect(root.querySelectorAll(".laboratory-tool svg").length).toBeGreaterThan(0);
  });

  it("exposes failed and retry states without implying backend execution", async () => {
    const { root } = renderLaboratory();
    const textarea = screen.getByLabelText("Mensagem para a demonstração do Laboratory");
    fireEvent.change(textarea, {
      target: { value: "Simule uma falha e permita uma nova tentativa." },
    });
    fireEvent.click(screen.getByLabelText("Enviar mensagem"));

    await waitFor(() => expect(root).toHaveAttribute("data-state", "failed"));
    expect(screen.getByText(/Nenhum backend foi acionado/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /tentar novamente/i }));

    await waitFor(() => expect(root).toHaveAttribute("data-state", "completed"));
    expect(screen.getByText(/recuperado na nova tentativa/i)).toBeInTheDocument();
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
    expect(screen.getByRole("heading", { name: "Laboratory indisponível" })).toBeInTheDocument();
    expect(screen.getByText("Nenhuma mensagem foi enviada.")).toBeInTheDocument();
    expect(screen.getByLabelText("Mensagem para a demonstração do Laboratory")).toBeDisabled();
  });
});

function resultMessage(root: HTMLElement, selector: string) {
  const element = root.querySelector(selector);
  if (!element) throw new Error(`Expected ${selector}`);
  return element.textContent;
}
