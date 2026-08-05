import { afterEach, describe, expect, it, vi } from "vitest";
import { LiveLaboratoryAdapter, productionLaboratoryAdapter } from "./adapters";
import type { LabUiEvent } from "./contracts";

function sseResponse(events: LabUiEvent[]): Response {
  const body = events
    .map((event) => `event: ${event.type}\ndata: ${JSON.stringify(event)}\n\n`)
    .join("");
  return new Response(body, { status: 200, headers: { "Content-Type": "text/event-stream" } });
}

async function collect(input = "olá", signal = new AbortController().signal) {
  const events: LabUiEvent[] = [];
  for await (const event of new LiveLaboratoryAdapter().send(input, signal)) events.push(event);
  return events;
}

function stubSessionAndTurn(turn: Response | (() => Promise<Response>)) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (request: string | URL | Request, init?: RequestInit) => {
      const url = String(request);
      if (url.endsWith("/api/v1/dashboard")) {
        return Response.json({ workspaces: [{ id: "workspace:1", name: "Principal" }] });
      }
      if (url.endsWith("/api/v1/lab/sessions")) {
        return Response.json({
          id: "session:1",
          workspace_id: "workspace:1",
          project_id: null,
          focus_kind: null,
          focus_id: null,
          form: "general",
          title: "Laboratory",
          created_at: "2026-08-04T12:00:00Z",
        });
      }
      if (url.endsWith("/api/v1/lab/sessions/session%3A1/turns")) {
        expect(init?.signal).toBeInstanceOf(AbortSignal);
        return typeof turn === "function" ? turn() : turn;
      }
      throw new Error(`Requisição inesperada: ${url}`);
    }),
  );
}

afterEach(() => vi.unstubAllGlobals());

describe("frontend data seams", () => {
  it("repassa o corredor live em ordem e preserva os campos", async () => {
    const streamed: LabUiEvent[] = [
      {
        type: "tool",
        source: "live",
        id: "call:1",
        name: "read_run",
        status: "running",
        argumentsSummary: "run:1",
      },
      {
        type: "tool",
        source: "live",
        id: "call:1",
        name: "read_run",
        status: "completed",
        resultSummary: "Run carregada",
      },
      { type: "message", source: "live", content: "A análise está pronta." },
      { type: "done", source: "live" },
    ];
    stubSessionAndTurn(sseResponse(streamed));

    const events = await collect();
    expect(productionLaboratoryAdapter.mode).toBe("live");
    expect(events).toEqual(streamed);
    expect(events.every((event) => event.source !== "integration_pending")).toBe(true);
  });

  it("preserva código e remediação de uma recusa no stream", async () => {
    stubSessionAndTurn(
      sseResponse([
        {
          type: "error",
          source: "live",
          message: "Ação requer decisão humana.",
          code: "authority.human_decision_required",
          remediation: "Solicite confirmação explícita.",
        },
        { type: "done", source: "live" },
      ]),
    );

    expect(await collect()).toEqual([
      expect.objectContaining({
        type: "error",
        code: "authority.human_decision_required",
        remediation: "Solicite confirmação explícita.",
      }),
      { type: "done", source: "live" },
    ]);
  });

  it("falha explicitamente quando o stream fecha sem done", async () => {
    stubSessionAndTurn(
      sseResponse([{ type: "message", source: "live", content: "Resposta parcial" }]),
    );

    const events = await collect();
    expect(events.map((event) => event.type)).toEqual(["message", "error"]);
    expect(events).not.toContainEqual({ type: "done", source: "live" });
  });

  it("propaga o abort ao fetch e encerra sem fabricar terminal", async () => {
    const controller = new AbortController();
    let receivedSignal: AbortSignal | null = null;
    stubSessionAndTurn(
      () =>
        new Promise<Response>((_resolve, reject) => {
          const fetchMock = vi.mocked(fetch);
          receivedSignal = fetchMock.mock.calls.at(-1)?.[1]?.signal ?? null;
          receivedSignal?.addEventListener(
            "abort",
            () => reject(new DOMException("Abortado", "AbortError")),
            { once: true },
          );
        }),
    );

    const pending = collect("cancele", controller.signal);
    await vi.waitFor(() => expect(receivedSignal).toBe(controller.signal));
    controller.abort();

    await expect(pending).resolves.toEqual([]);
  });

  it("traduz erro HTTP tipado antes de abrir o stream", async () => {
    stubSessionAndTurn(
      new Response(
        JSON.stringify({
          detail: {
            stage: "scope",
            code: "scope.target_not_visible",
            message: "O alvo não está visível neste escopo.",
            remediation: "Selecione um alvo visível.",
            category: "not_found",
          },
        }),
        { status: 404 },
      ),
    );

    expect(await collect()).toEqual([
      {
        type: "error",
        source: "live",
        message: "O alvo não está visível neste escopo.",
        code: "scope.target_not_visible",
        remediation: "Selecione um alvo visível.",
      },
    ]);
  });
});
