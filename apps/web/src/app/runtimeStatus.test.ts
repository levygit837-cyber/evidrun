import { describe, expect, it } from "vitest";
import type { Run } from "../types";
import { pendingRunCount, planeTone, runtimeAlert } from "./runtimeStatus";

function run(status: string): Run {
  return { status } as Run;
}

const ready = { status: "ready" } as const;
const failed = { status: "failed" } as const;
const stopped = { status: "stopped" } as const;
const starting = { status: "starting" } as const;

describe("plane tone", () => {
  it("separates ready from failed", () => {
    expect(planeTone("ready")).toBe("success");
    expect(planeTone("failed")).toBe("danger");
  });

  it("treats stopped as a warning, not an error", () => {
    // In a browser there is no supervised executor at all; flagging that red would cry wolf.
    expect(planeTone("stopped")).toBe("warning");
    expect(planeTone("starting")).toBe("warning");
  });
});

describe("pending run count", () => {
  it("counts Runs waiting on an executor", () => {
    expect(
      pendingRunCount([run("queued"), run("running"), run("completed"), run("failed")]),
    ).toBe(2);
  });

  it("ignores terminal Runs", () => {
    expect(pendingRunCount([run("completed"), run("failed"), run("budget_exhausted")])).toBe(0);
  });
});

describe("runtime alert", () => {
  it("stays silent when both planes are healthy", () => {
    expect(runtimeAlert(ready, ready, 3)).toBeNull();
  });

  it("never lets a stalled queue look healthy", () => {
    // The invariant the banner exists for.
    const alert = runtimeAlert(ready, failed, 3);
    expect(alert?.tone).toBe("danger");
    expect(alert?.title).toContain("3 Runs");
    expect(alert?.action).toBe("restart-executor");
  });

  it("counts a single waiting Run in the singular", () => {
    expect(runtimeAlert(ready, failed, 1)?.title).toBe("1 Run aguardando execução");
  });

  it("reports a dead executor with an empty queue without shouting", () => {
    const alert = runtimeAlert(ready, failed, 0);
    expect(alert?.tone).toBe("warning");
    expect(alert?.action).toBe("restart-executor");
  });

  it("puts the backend ahead of the executor", () => {
    // Without the API nothing is readable, and the queue count on screen cannot be trusted.
    const alert = runtimeAlert(failed, failed, 3);
    expect(alert?.title).toContain("Backend");
    expect(alert?.action).toBe("restart-backend");
  });

  it("stays quiet in a browser, where no executor is supervised", () => {
    expect(runtimeAlert(ready, stopped, 0)).toBeNull();
  });

  it("explains a queue waiting on an executor that is still coming up", () => {
    const alert = runtimeAlert(ready, starting, 2);
    expect(alert?.tone).toBe("warning");
    expect(alert?.action).toBeNull();
  });
});
