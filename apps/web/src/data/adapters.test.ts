import { describe, expect, it, vi } from "vitest";

const admitRunSpec = vi.hoisted(() => vi.fn());
const retryRun = vi.hoisted(() => vi.fn());
vi.mock("../api/client", () => ({
  api: { admitRunSpec, retryRun },
  runEventStream: { subscribe: () => () => {} },
}));

const { observabilityAdapter } = await import("./adapters");

describe("retry idempotency", () => {
  it("keys a retry by its source Run, never by the clock", async () => {
    // The queue dedupes on the idempotency key alone, and `disabled` on the button only takes
    // effect after a re-render — so a wall-clock key let a double click enqueue two Runs.
    // Time is advanced between the calls, because two clicks in the same millisecond would
    // collide by accident and hide exactly that bug.
    admitRunSpec.mockResolvedValue({ id: "admission:1", decision: "admitted" });
    retryRun.mockResolvedValue({ run_id: "run:retry-001" });
    retryRun.mockClear();

    vi.useFakeTimers();
    try {
      vi.setSystemTime(new Date("2026-07-28T10:00:00Z"));
      await observabilityAdapter.retryRun("run:source", "runspec:1");
      vi.setSystemTime(new Date("2026-07-28T10:00:05Z"));
      await observabilityAdapter.retryRun("run:source", "runspec:1");
    } finally {
      vi.useRealTimers();
    }

    const keys = new Set(retryRun.mock.calls.map((call) => call[2] as string));
    expect(keys.size).toBe(1);
    expect([...keys][0]).toContain("run:source");
  });

  it("keys retries of different Runs apart", async () => {
    admitRunSpec.mockResolvedValue({ id: "admission:1", decision: "admitted" });
    retryRun.mockResolvedValue({ run_id: "run:retry-002" });
    retryRun.mockClear();

    await observabilityAdapter.retryRun("run:a", "runspec:1");
    await observabilityAdapter.retryRun("run:b", "runspec:1");

    const keys = new Set(retryRun.mock.calls.map((call) => call[2] as string));
    expect(keys.size).toBe(2);
  });

  it("admits before retrying, because a retry needs a fresh admission", async () => {
    const order: string[] = [];
    admitRunSpec.mockImplementation(async () => {
      order.push("admit");
      return { id: "admission:1", decision: "admitted" };
    });
    retryRun.mockImplementation(async () => {
      order.push("retry");
      return { run_id: "run:retry-003" };
    });

    await observabilityAdapter.retryRun("run:source", "runspec:1");
    expect(order).toEqual(["admit", "retry"]);
  });

  it("does not retry when admission fails", async () => {
    admitRunSpec.mockRejectedValue(new Error("A admissão recusou este RunSpec: rejected."));
    retryRun.mockClear();

    await expect(observabilityAdapter.retryRun("run:source", "runspec:1")).rejects.toThrow(
      /recusou/,
    );
    expect(retryRun).not.toHaveBeenCalled();
  });
});
