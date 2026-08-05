import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import type { LabScopeSelection, LabSession, LaboratorySessionAdapter } from "../../data/contracts";
import { LaboratoryPage } from "./LaboratoryPage";

afterEach(cleanup);

function sessionFor(scope: LabScopeSelection): LabSession {
  return { id: `${scope.projectId ?? "general"}:${scope.focusId ?? ""}`, workspace_id: scope.workspaceId, project_id: scope.projectId ?? null, focus_kind: scope.focusKind ?? null, focus_id: scope.focusId ?? null, form: scope.focusId ? "focused" : scope.projectId ? "project" : "general", title: "Laboratory", created_at: "2026-08-05T00:00:00Z" };
}

function adapter(): LaboratorySessionAdapter {
  let active: LabSession | null = null;
  return {
    mode: "live",
    scopeOptions: async () => ({ workspaces: [{ id: "w:1", name: "Principal" }], projects: [{ id: "p:1", name: "Pesquisa" }, { id: "p:2", name: "Outro" }] }),
    selectScope: async (scope) => (active = sessionFor(scope)),
    activeSession: () => active,
    messages: async () => [],
    async *send(_input, signal) {
      yield { type: "status", source: "live", label: "Lendo evidência" };
      yield { type: "tool", source: "live", id: "tool:1", name: "read_run", status: "completed", argumentsSummary: "run:1", resultSummary: "sample_size: 2" };
      if (!signal.aborted) yield { type: "message", source: "live", content: "Resposta em rascunho." };
      if (!signal.aborted) yield { type: "done", source: "live" };
    },
  };
}

async function open(form: "general" | "project" | "focused") {
  fireEvent.change(await screen.findByLabelText("Workspace"), { target: { value: "w:1" } });
  fireEvent.change(screen.getByLabelText("Forma da sessão"), { target: { value: form } });
  if (form !== "general") fireEvent.change(screen.getByLabelText("Project"), { target: { value: "p:1" } });
  if (form === "focused") { fireEvent.change(screen.getByLabelText("Tipo do foco"), { target: { value: "study" } }); fireEvent.change(screen.getByLabelText("ID do foco"), { target: { value: "study:1" } }); }
  fireEvent.click(screen.getByRole("button", { name: "Criar ou retomar" }));
  await screen.findByLabelText("Mensagem para o Laboratory");
}

describe("LaboratoryPage", () => {
  it("abre as três formas sem copiar mensagens e marca a forma devolvida pela API", async () => {
    render(<LaboratoryPage adapter={adapter()} />);
    await open("general"); expect(screen.getAllByText("Chat geral").length).toBeGreaterThan(0);
    await open("project"); expect(screen.getAllByText("Project Room").length).toBeGreaterThan(0);
    await open("focused"); expect(screen.getAllByText("Chat focado").length).toBeGreaterThan(0);
    expect(screen.getByText(/não são copiadas/i)).toBeInTheDocument();
  });

  it("mostra o que a tool leu e a resposta do agente", async () => {
    render(<LaboratoryPage adapter={adapter()} />); await open("project");
    const input = screen.getByLabelText("Mensagem para o Laboratory");
    fireEvent.change(input, { target: { value: "Leia a Run" } }); fireEvent.click(screen.getByLabelText("Enviar mensagem"));
    await screen.findByText("Resposta em rascunho.");
    expect(screen.getByText("run:1")).toBeInTheDocument();
    expect(screen.getByText("sample_size: 2")).toBeInTheDocument();
  });

  it("não transforma terminal cancelado em conclusão", async () => {
    const cancelled = adapter(); cancelled.send = async function* () { yield { type: "status", source: "live", label: "cancelled" }; yield { type: "done", source: "live" }; };
    const { container } = render(<LaboratoryPage adapter={cancelled} />); await open("general");
    fireEvent.change(screen.getByLabelText("Mensagem para o Laboratory"), { target: { value: "Pare" } }); fireEvent.click(screen.getByLabelText("Enviar mensagem"));
    await waitFor(() => expect(container.querySelector(".laboratory")).toHaveAttribute("data-state", "cancelled"));
    expect(screen.getByText("Turno cancelado", { selector: "strong" })).toBeInTheDocument();
  });
});
