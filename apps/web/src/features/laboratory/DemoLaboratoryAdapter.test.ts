import { describe, expect, it } from "vitest";
import type { LabUiEvent } from "../../data/contracts";
import { DemoLaboratoryAdapter } from "./DemoLaboratoryAdapter";

async function collect(adapter: DemoLaboratoryAdapter, input: string) {
  const events: LabUiEvent[] = [];
  for await (const event of adapter.send(input, new AbortController().signal)) events.push(event);
  return events;
}

describe("DemoLaboratoryAdapter", () => {
  it("keeps every normal event explicitly sourced from Demo", async () => {
    const events = await collect(new DemoLaboratoryAdapter({ delayMs: 0 }), "Resuma o contexto.");

    expect(events.map((event) => event.type)).toEqual(["status", "status", "message", "done"]);
    expect(events.every((event) => event.source === "demo")).toBe(true);
    expect(events.find((event) => event.type === "message")).toEqual(
      expect.objectContaining({ content: expect.stringContaining("não contém resultados de uma Run real") }),
    );
  });

  it("emits the deterministic tool chronology with running and completed states", async () => {
    const events = await collect(
      new DemoLaboratoryAdapter({ delayMs: 0 }),
      "Use ferramentas para inspecionar o Run Demo.",
    );
    const tools = events.filter((event) => event.type === "tool");

    expect(tools.map((tool) => [tool.name, tool.status])).toEqual([
      ["search_repository", "running"],
      ["search_repository", "completed"],
      ["compile_subject", "running"],
      ["compile_subject", "completed"],
      ["inspect_run", "running"],
      ["inspect_run", "completed"],
    ]);
    expect(tools.every((tool) => tool.source === "demo")).toBe(true);
  });

  it("fails once and succeeds deterministically on retry", async () => {
    const adapter = new DemoLaboratoryAdapter({ delayMs: 0 });
    const input = "Simule uma falha e permita uma nova tentativa.";

    const firstAttempt = await collect(adapter, input);
    const retry = await collect(adapter, input);

    expect(firstAttempt.at(-1)).toEqual(
      expect.objectContaining({ type: "error", source: "demo" }),
    );
    expect(retry.at(-1)).toEqual({ type: "done", source: "demo" });
    expect(retry).toContainEqual(
      expect.objectContaining({ type: "message", content: expect.stringContaining("nova tentativa") }),
    );
  });

  it("aborts a pending sequence without fabricating a terminal event", async () => {
    const adapter = new DemoLaboratoryAdapter({ delayMs: 100 });
    const controller = new AbortController();
    const iterator = adapter.send("Cancele esta demonstração.", controller.signal)[
      Symbol.asyncIterator
    ]();

    expect(await iterator.next()).toEqual({
      done: false,
      value: { type: "status", source: "demo", label: "Organizando contexto Demo" },
    });
    const pending = iterator.next();
    controller.abort();

    await expect(pending).rejects.toMatchObject({ name: "AbortError" });
  });
});

