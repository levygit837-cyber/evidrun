import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import type {
  LabScopeSelection,
  LabSession,
  LaboratoryAdapter,
  LaboratorySessionAdapter,
} from "../../data/contracts";
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

  it.each([
    ["budget_exhausted", "exhausted"],
    ["repeated_refusal", "exhausted"],
    ["provider_failed", "failed"],
    ["proposed", "proposed"],
    ["answered", "completed"],
  ])("mapeia o terminal %s para a fase %s", async (terminal, expected) => {
    const named = adapter();
    named.send = async function* () {
      yield { type: "status", source: "live", label: terminal };
      yield { type: "done", source: "live" };
    };
    const { container } = render(<LaboratoryPage adapter={named} />);
    await open("general");
    fireEvent.change(screen.getByLabelText("Mensagem para o Laboratory"), {
      target: { value: "Vai" },
    });
    fireEvent.click(screen.getByLabelText("Enviar mensagem"));

    // `budget_exhausted` e `repeated_refusal` não contêm "cancel" nem "fail": a heurística de
    // substring anterior os apresentava como conclusão, violando o invariante de turno parcial.
    await waitFor(() =>
      expect(container.querySelector(".laboratory")).toHaveAttribute("data-state", expected),
    );
  });

  it("falha explícito quando o backend emite um terminal desconhecido", async () => {
    const unknown = adapter();
    unknown.send = async function* () {
      yield { type: "status", source: "live", label: "terminal_que_nao_existe" };
      yield { type: "done", source: "live" };
    };
    const { container } = render(<LaboratoryPage adapter={unknown} />);
    await open("general");
    fireEvent.change(screen.getByLabelText("Mensagem para o Laboratory"), {
      target: { value: "Vai" },
    });
    fireEvent.click(screen.getByLabelText("Enviar mensagem"));

    // Terminal novo no backend não pode virar conclusão silenciosa; falhar alto é o caminho honesto.
    await waitFor(() =>
      expect(container.querySelector(".laboratory")).toHaveAttribute("data-state", "failed"),
    );
    expect(screen.getByText(/terminal que esta interface não conhece/)).toBeInTheDocument();
  });

  it("oculta número agregado que chega sem sample_size", async () => {
    const aggregate = adapter();
    aggregate.send = async function* () {
      yield {
        type: "tool",
        source: "live",
        id: "tool:agg",
        name: "aggregate_metrics",
        status: "completed",
        argumentsSummary: '{"metric":"grade_score"}',
        resultSummary: '{"groups":[{"group":"succeeded","value":0.8}]}',
      };
      yield { type: "status", source: "live", label: "answered" };
      yield { type: "done", source: "live" };
    };
    render(<LaboratoryPage adapter={aggregate} />);
    await open("project");
    fireEvent.change(screen.getByLabelText("Mensagem para o Laboratory"), {
      target: { value: "Agregue" },
    });
    fireEvent.click(screen.getByLabelText("Enviar mensagem"));

    // Valor sem amostra não é resultado. A decisão vem do nome da tool, não de palavra no texto:
    // um resumo JSON como este não contém "média" nem "agregado".
    expect(await screen.findByText(/amostra \(sample_size\) não foi informada/)).toBeInTheDocument();
    expect(screen.queryByText(/0\.8/)).not.toBeInTheDocument();
  });

  it("recusa enviar antes de a pessoa escolher o escopo", async () => {
    render(<LaboratoryPage adapter={adapter()} />);

    await screen.findByLabelText("Workspace");

    // General oferece duas tools e Project treze. Sem escopo declarado, um composer habilitado
    // convidaria a pessoa a conversar num escopo que ela não escolheu.
    expect(screen.queryByLabelText("Mensagem para o Laboratory")).not.toBeInTheDocument();
  });

  it("mantém Shift+Enter como quebra de linha em vez de enviar", async () => {
    const sent: string[] = [];
    const tracked = adapter();
    const original = tracked.send.bind(tracked);
    tracked.send = (input, signal) => {
      sent.push(input);
      return original(input, signal);
    };
    render(<LaboratoryPage adapter={tracked} />);
    await open("general");
    const input = screen.getByLabelText("Mensagem para o Laboratory");

    fireEvent.change(input, { target: { value: "primeira linha" } });
    fireEvent.keyDown(input, { key: "Enter", shiftKey: true });

    expect(sent).toEqual([]);

    fireEvent.keyDown(input, { key: "Enter" });
    await waitFor(() => expect(sent).toEqual(["primeira linha"]));
  });

  it("trava o envio contra duplo clique de forma sincrona", async () => {
    let calls = 0;
    const tracked = adapter();
    tracked.send = async function* (_input, signal) {
      calls += 1;
      if (!signal.aborted) yield { type: "message", source: "live", content: "uma vez" };
      if (!signal.aborted) yield { type: "done", source: "live" };
    };
    render(<LaboratoryPage adapter={tracked} />);
    await open("general");
    fireEvent.change(screen.getByLabelText("Mensagem para o Laboratory"), {
      target: { value: "Envie" },
    });
    const button = screen.getByLabelText("Enviar mensagem");

    // Dois cliques na mesma task: a trava é sincrona de propósito, antes do primeiro await.
    fireEvent.click(button);
    fireEvent.click(button);

    await screen.findByText("uma vez");
    expect(calls).toBe(1);
  });

  it("vira cancelar durante o turno e alcança o estado cancelado", async () => {
    const slow = adapter();
    slow.send = async function* (_input, signal) {
      yield { type: "status", source: "live", label: "Lendo evidência" };
      // Só avança quando o humano aborta: um timer fixo terminaria o turno antes do clique e o
      // botão voltaria a "Enviar mensagem" sem provar nada.
      // `Promise.withResolvers` exigiria lib ES2024, e o web compila em ES2023. O executor aqui
      // segue a convenção que `DemoLaboratoryAdapter.wait` já usa neste pacote.
      await new Promise<void>((resolve) => signal.addEventListener("abort", () => resolve()));
      if (signal.aborted) return;
      yield { type: "done", source: "live" };
    };
    const { container } = render(<LaboratoryPage adapter={slow} />);
    await open("general");
    fireEvent.change(screen.getByLabelText("Mensagem para o Laboratory"), {
      target: { value: "Comece" },
    });
    fireEvent.click(screen.getByLabelText("Enviar mensagem"));

    const cancel = await screen.findByLabelText("Cancelar turno");
    fireEvent.click(cancel);

    // `stopping` antes de `cancelled`: o abort precisa alcançar o gerador e ele encerrar. Aceitar
    // só o estado final esconderia a fase em que o botão ainda está desabilitado.
    await waitFor(() =>
      expect(container.querySelector(".laboratory")).toHaveAttribute("data-state", "cancelled"),
      { timeout: 3000 },
    );
  });

  it("expõe recusa com sua remediação sem apresentar o turno como concluído", async () => {
    const refused = adapter();
    refused.send = async function* () {
      yield {
        type: "error",
        source: "live",
        message: "A referência solicitada não está disponível nesta sessão.",
        code: "scope.target_not_visible",
        remediation: "Liste os alvos deste Project antes de referenciar um id.",
      };
    };
    const { container } = render(<LaboratoryPage adapter={refused} />);
    await open("project");
    fireEvent.change(screen.getByLabelText("Mensagem para o Laboratory"), {
      target: { value: "Leia run:404" },
    });
    fireEvent.click(screen.getByLabelText("Enviar mensagem"));

    // A remediação nomeia a próxima ação válida; exibir só a mensagem deixaria a pessoa sem saída.
    await screen.findByText(/Liste os alvos deste Project/);
    expect(container.querySelector(".laboratory")).not.toHaveAttribute("data-state", "completed");
  });

  it("falha fechado em indisponível quando o adapter não tem capacidade", async () => {
    const unavailable: LaboratoryAdapter = {
      mode: "integration_pending",
      async *send() {
        throw new Error("send não deve ser alcançado sem capacidade");
      },
    };

    render(<LaboratoryPage adapter={unavailable} />);

    expect(
      await screen.findByRole("heading", { name: "Laboratory indisponível" }),
    ).toBeInTheDocument();
    expect(screen.queryByLabelText("Mensagem para o Laboratory")).not.toBeInTheDocument();
  });
});
