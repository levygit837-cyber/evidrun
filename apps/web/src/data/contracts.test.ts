import { afterEach, describe, expect, it, vi } from "vitest";
import { LiveLaboratoryAdapter, productionLaboratoryAdapter } from "./adapters";
import type { LabUiEvent } from "./contracts";

const session = { id: "session:1", workspace_id: "workspace:1", project_id: null, focus_kind: null, focus_id: null, form: "general" as const, title: "Laboratory", created_at: "2026-08-04T12:00:00Z" };

function response(events: LabUiEvent[]) {
  return new Response(events.map((event) => `data: ${JSON.stringify(event)}\n\n`).join(""), { status: 200 });
}

afterEach(() => vi.unstubAllGlobals());

describe("LiveLaboratoryAdapter", () => {
  it("exige escopo explícito, cria ou retoma a sessão e repassa SSE", async () => {
    const fetch = vi.fn(async (request: string | URL) => {
      const url = String(request);
      if (url.endsWith("/lab/sessions?workspace_id=workspace%3A1")) return Response.json([]);
      if (url.endsWith("/lab/sessions")) return Response.json(session);
      if (url.includes("/turns")) return response([{ type: "tool", source: "live", id: "tool:1", name: "read_run", status: "completed", argumentsSummary: "run:1", resultSummary: "sample_size: 2" }, { type: "done", source: "live" }]);
      throw new Error(`Requisição inesperada: ${url}`);
    });
    vi.stubGlobal("fetch", fetch);
    const adapter = new LiveLaboratoryAdapter();
    const before = [adapter.send("oi", new AbortController().signal)];
    for await (const event of before[0]) expect(event).toMatchObject({ type: "error" });
    await expect(adapter.selectScope({ workspaceId: "workspace:1" })).resolves.toEqual(session);
    const events: LabUiEvent[] = [];
    for await (const event of adapter.send("oi", new AbortController().signal)) events.push(event);
    expect(events.map((event) => event.type)).toEqual(["tool", "done"]);
    expect(productionLaboratoryAdapter.mode).toBe("live");
  });
});
