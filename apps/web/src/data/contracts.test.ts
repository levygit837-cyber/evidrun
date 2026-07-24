import { describe, expect, it } from "vitest";
import { productionLaboratoryAdapter } from "./adapters";

describe("frontend data seams", () => {
  it("keeps the production Laboratory capability honest while the backend is absent", async () => {
    const events = [];
    for await (const event of productionLaboratoryAdapter.send("olá", new AbortController().signal)) {
      events.push(event);
    }

    expect(productionLaboratoryAdapter.mode).toBe("integration_pending");
    expect(events).toEqual([
      expect.objectContaining({ type: "error", source: "integration_pending" }),
    ]);
  });
});
