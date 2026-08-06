import { afterEach, describe, expect, it, vi } from "vitest";
import { LiveLaboratoryAdapter, productionLaboratoryAdapter } from "./adapters";
import type { LabUiEvent } from "./contracts";

const session = {
  id: "session:1",
  workspace_id: "workspace:1",
  project_id: null,
  focus_kind: null,
  focus_id: null,
  form: "general" as const,
  title: "Laboratory",
  created_at: "2026-08-04T12:00:00Z",
};

function sse(events: LabUiEvent[], { done = true }: { done?: boolean } = {}) {
  const frames = [...events, ...(done ? [{ type: "done", source: "live" } as LabUiEvent] : [])];
  return new Response(frames.map((event) => `data: ${JSON.stringify(event)}\n\n`).join(""), {
    status: 200,
  });
}

/** Sessão já resolvida: cada teste de stream exercita o turno, não a seleção de escopo. */
function scopedAdapter(turns: (url: string) => Response | Promise<Response>) {
  const fetch = vi.fn(async (request: string | URL, init?: RequestInit) => {
    const url = String(request);
    if (url.includes("/lab/sessions?workspace_id=")) return Response.json([]);
    if (url.endsWith("/lab/sessions")) return Response.json(session);
    if (url.includes("/turns")) return turns(url);
    throw new Error(`Requisição inesperada: ${url}`);
  });
  vi.stubGlobal("fetch", fetch);
  return { adapter: new LiveLaboratoryAdapter(), fetch };
}

async function collect(iterable: AsyncIterable<LabUiEvent>) {
  const events: LabUiEvent[] = [];
  for await (const event of iterable) events.push(event);
  return events;
}

afterEach(() => vi.unstubAllGlobals());

describe("LiveLaboratoryAdapter", () => {
  it("declara o modo live em produção", () => {
    expect(productionLaboratoryAdapter.mode).toBe("live");
  });

  it("recusa enviar antes de a pessoa escolher o escopo", async () => {
    const { adapter } = scopedAdapter(() => {
      throw new Error("o turno não deveria ser alcançado sem escopo");
    });

    const events = await collect(adapter.send("oi", new AbortController().signal));

    // General chat oferece duas tools e Project treze. Escolher Workspace por heurística faria a
    // pessoa conversar num escopo que ela não declarou, então a ausência é recusa explícita.
    expect(events).toEqual([expect.objectContaining({ type: "error" })]);
  });

  it("repassa o corredor live em ordem e preserva os campos da tool", async () => {
    const { adapter } = scopedAdapter(() =>
      sse([
        {
          type: "tool",
          source: "live",
          id: "tool:1",
          name: "read_run",
          status: "running",
          argumentsSummary: '{"run_id":"run:1"}',
        },
        {
          type: "tool",
          source: "live",
          id: "tool:1",
          name: "read_run",
          status: "completed",
          argumentsSummary: '{"run_id":"run:1"}',
          resultSummary: '{"sample_size":2}',
        },
        { type: "message", source: "live", content: "Li a Run." },
      ]),
    );
    await adapter.selectScope({ workspaceId: "workspace:1" });

    const events = await collect(adapter.send("oi", new AbortController().signal));

    expect(events.map((event) => event.type)).toEqual(["tool", "tool", "message", "done"]);
    // O ADR 0018 exige que o humano veja o que o agente leu; resumo perdido apaga isso.
    expect(events[0]).toMatchObject({ status: "running", argumentsSummary: '{"run_id":"run:1"}' });
    expect(events[1]).toMatchObject({ status: "completed", resultSummary: '{"sample_size":2}' });
    // `source` vem do backend; reescrevê-lo no cliente mascararia divergência real.
    expect(events.every((event) => event.source === "live")).toBe(true);
  });

  it("preserva código e remediação de uma recusa no stream", async () => {
    const { adapter } = scopedAdapter(() =>
      sse([
        {
          type: "error",
          source: "live",
          message: "A referência solicitada não está disponível nesta sessão.",
          code: "scope.target_not_visible",
          remediation: "Liste os alvos deste Project antes de referenciar um id.",
        },
      ]),
    );
    await adapter.selectScope({ workspaceId: "workspace:1" });

    const events = await collect(adapter.send("oi", new AbortController().signal));

    // O errors-v1 proíbe a borda deduzir causa por texto: código e remediação têm de chegar.
    expect(events[0]).toMatchObject({
      type: "error",
      code: "scope.target_not_visible",
      remediation: "Liste os alvos deste Project antes de referenciar um id.",
    });
  });

  it("falha explicitamente quando o stream fecha sem done", async () => {
    const { adapter } = scopedAdapter(() =>
      sse([{ type: "message", source: "live", content: "Resposta truncada." }], { done: false }),
    );
    await adapter.selectScope({ workspaceId: "workspace:1" });

    const events = await collect(adapter.send("oi", new AbortController().signal));

    // Turno interrompido apresentado como completo é o invariante que o loop-v1 proíbe.
    expect(events.at(-1)).toMatchObject({ type: "error" });
    expect(events.some((event) => event.type === "done")).toBe(false);
  });

  it("encerra sem fabricar terminal quando o sinal já vem abortado", async () => {
    const controller = new AbortController();
    const { adapter, fetch } = scopedAdapter(() => {
      throw new Error("o turno não deveria abrir com sinal já abortado");
    });
    await adapter.selectScope({ workspaceId: "workspace:1" });
    controller.abort();

    const events = await collect(adapter.send("oi", controller.signal));

    // Nem `done` nem `error`: abortar é escolha do humano, e inventar terminal aqui apresentaria
    // um turno que ninguém pediu como concluído ou falho.
    expect(events).toEqual([]);
    expect(fetch.mock.calls.some(([request]) => String(request).includes("/turns"))).toBe(false);
  });

  it("propaga o abort ao fetch do turno", async () => {
    const controller = new AbortController();
    const { adapter, fetch } = scopedAdapter(() =>
      sse([{ type: "message", source: "live", content: "resposta" }]),
    );
    await adapter.selectScope({ workspaceId: "workspace:1" });

    await collect(adapter.send("oi", controller.signal));

    // Abortar o fetch é o que fecha a conexão e dispara o cancelamento no backend. Sem o sinal
    // chegando aqui, cancelar na UI não cancelaria nada no servidor.
    const turnCall = fetch.mock.calls.find(([request]) => String(request).includes("/turns"));
    expect(turnCall?.[1]).toMatchObject({ signal: controller.signal });
  });

  it("traduz erro HTTP tipado antes de abrir o stream", async () => {
    const { adapter } = scopedAdapter(() =>
      Response.json(
        {
          detail: {
            stage: "scope",
            code: "scope.target_not_visible",
            category: "not_found",
            message: "A referência solicitada não está disponível nesta sessão.",
            remediation: "Liste os alvos deste Workspace antes de referenciar um id.",
          },
        },
        { status: 404 },
      ),
    );
    await adapter.selectScope({ workspaceId: "workspace:1" });

    const events = await collect(adapter.send("oi", new AbortController().signal));

    expect(events[0]).toMatchObject({
      type: "error",
      code: "scope.target_not_visible",
      remediation: "Liste os alvos deste Workspace antes de referenciar um id.",
    });
  });
});
