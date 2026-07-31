import { EventEmitter } from "node:events";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const spawned: FakeChild[] = [];

/**
 * A child process that only dies when told to, so shutdown can be tested honestly.
 *
 * The distinction that matters: `killed` means "a signal was delivered", while `exitCode`
 * and `signalCode` staying null means "still running". A worker mid-Run behaves exactly
 * like this — it takes SIGTERM and needs a moment to release its lease.
 */
class FakeChild extends EventEmitter {
  stdin = { write: vi.fn() };
  stdout = new EventEmitter();
  stderr = new EventEmitter();
  killed = false;
  exitCode: number | null = null;
  signalCode: string | null = null;
  signals: string[] = [];
  refuseSigkill = false;

  kill(signal: string): boolean {
    this.signals.push(signal);
    this.killed = true;
    return signal !== "SIGKILL" || !this.refuseSigkill;
  }

  exit(code: number | null, signal: string | null = null): void {
    this.exitCode = code;
    this.signalCode = signal;
    this.emit("exit", code, signal);
  }

  ready(): void {
    this.stdout.emit("line-source", "");
  }
}

vi.mock("node:child_process", () => ({
  spawn: () => {
    const child = new FakeChild();
    spawned.push(child);
    return child;
  },
}));
vi.mock("electron", () => ({ app: { isPackaged: false } }));
function createInterface({ input }: { input: EventEmitter }) {
  const emitter = new EventEmitter();
  input.on("line-source", () => emitter.emit("line", READY_LINE));
  input.on("bad-line", () => emitter.emit("line", "not json"));
  return emitter;
}

vi.mock("node:readline", () => ({ default: { createInterface }, createInterface }));

const READY_LINE = JSON.stringify({
  protocol: "evidrun-worker-v1",
  schema_version: "1",
  pid: 4321,
  worker_id: "host:4321:worker_01",
});

const { ExecutorLifecycle, redactDataDir } = await import("./executor-lifecycle.js");

describe("executor lifecycle", () => {
  let lifecycle: InstanceType<typeof ExecutorLifecycle>;

  beforeEach(() => {
    spawned.length = 0;
    lifecycle = new ExecutorLifecycle();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  async function startReady(): Promise<FakeChild> {
    const starting = lifecycle.start("/data");
    const child = spawned[0]!;
    child.ready();
    await starting;
    return child;
  }

  it("reports ready once the executor announces itself", async () => {
    await startReady();
    expect(lifecycle.state).toEqual({ status: "ready" });
  });

  it("passes the data dir over stdin and never in argv", async () => {
    const child = await startReady();
    expect(child.stdin.write).toHaveBeenCalledWith(`${JSON.stringify({ data_dir: "/data" })}\n`);
  });

  it("waits for real exit before reporting stopped", async () => {
    const child = await startReady();
    const stopping = lifecycle.stop();
    // Signal delivered, process still alive: `killed` is already true here, which is why
    // it cannot be the test for whether the executor is gone.
    expect(child.killed).toBe(true);
    expect(lifecycle.state).toEqual({ status: "ready" });
    child.exit(0);
    await stopping;
    expect(lifecycle.state.status).toBe("stopped");
  });

  it("waits for exit after escalating to SIGKILL", async () => {
    vi.useFakeTimers();
    const starting = lifecycle.start("/data");
    const child = spawned[0]!;
    child.ready();
    await starting;
    let stopped = false;
    const stopping = lifecycle.stop().then(() => {
      stopped = true;
    });
    await vi.advanceTimersByTimeAsync(8_000);
    expect(child.signals).toEqual(["SIGTERM", "SIGKILL"]);
    expect(stopped).toBe(false);
    expect(lifecycle.state).toEqual({ status: "ready" });
    child.exit(null, "SIGKILL");
    await stopping;
    expect(lifecycle.state.status).toBe("stopped");
  });

  it("rejects restart when SIGKILL cannot be delivered", async () => {
    vi.useFakeTimers();
    const child = await startReady();
    child.refuseSigkill = true;
    const restarting = lifecycle.restart("/data");
    const rejection = expect(restarting).rejects.toThrow("SIGKILL");
    await vi.advanceTimersByTimeAsync(8_000);
    await rejection;
    expect(spawned).toHaveLength(1);
    expect(lifecycle.state.status).toBe("failed");
    expect(await lifecycle.start("/data")).toEqual(lifecycle.state);
    expect(spawned).toHaveLength(1);
  });

  it("rejects shutdown when SIGKILL is delivered but exit never arrives", async () => {
    vi.useFakeTimers();
    const child = await startReady();
    const stopping = lifecycle.stop();
    const rejection = expect(stopping).rejects.toThrow("SIGKILL");
    await vi.advanceTimersByTimeAsync(16_000);
    await rejection;
    expect(child.signals).toEqual(["SIGTERM", "SIGKILL"]);
    expect(lifecycle.state.status).toBe("failed");
    expect(await lifecycle.start("/data")).toEqual(lifecycle.state);
    expect(spawned).toHaveLength(1);
  });

  it("treats a crash as failed and a requested stop as stopped", async () => {
    const child = await startReady();
    child.exit(1);
    expect(lifecycle.state.status).toBe("failed");
    expect(lifecycle.state.message).toContain("1");
  });

  it("never runs two executors when start races a shutdown", async () => {
    const child = await startReady();
    const stopping = lifecycle.stop();
    const starting = lifecycle.start("/data");
    child.exit(0);
    await stopping;
    spawned[1]?.ready();
    await starting;
    expect(spawned).toHaveLength(2);
    expect(spawned[0]!.exitCode).toBe(0);
  });

  it("keeps the data dir out of the log when the worker tracebacks", () => {
    const traceback = "FileNotFoundError: '/Users/someone/Library/evidrun/evidrun.db'";
    expect(redactDataDir(traceback, "/Users/someone/Library/evidrun")).not.toContain("someone");
    expect(redactDataDir(traceback, "/Users/someone/Library/evidrun")).toContain("<data-dir>");
  });

  it("does not accumulate processes across repeated restarts", async () => {
    await startReady();
    for (let i = 0; i < 3; i++) {
      const restarting = lifecycle.restart("/data");
      spawned[i]!.exit(0);
      await new Promise((resolve) => setImmediate(resolve));
      spawned[i + 1]?.ready();
      await restarting;
    }
    expect(spawned.filter((child) => child.exitCode === null)).toHaveLength(1);
  });

  it("reaps the process when readiness never arrives", async () => {
    vi.useFakeTimers();
    const starting = lifecycle.start("/data");
    const child = spawned[0]!;
    const settled = starting.catch((error: Error) => error.message);
    await vi.advanceTimersByTimeAsync(30_000);
    child.exit(null, "SIGTERM");
    await vi.advanceTimersByTimeAsync(8_000);
    await expect(settled).resolves.toContain("handshake");
    expect(child.signals).toContain("SIGTERM");
    expect(lifecycle.state.status).toBe("failed");
  });

  it("preserves a shutdown failure after the readiness timeout", async () => {
    vi.useFakeTimers();
    const starting = lifecycle.start("/data").catch((error: Error) => error.message);
    const child = spawned[0]!;
    child.refuseSigkill = true;
    await vi.advanceTimersByTimeAsync(38_000);
    await expect(starting).resolves.toContain("SIGKILL");
    expect(lifecycle.state.message).toContain("SIGKILL");
  });

  it("preserves a shutdown failure after an invalid handshake", async () => {
    vi.useFakeTimers();
    const starting = lifecycle.start("/data").catch((error: Error) => error.message);
    const child = spawned[0]!;
    child.refuseSigkill = true;
    child.stdout.emit("bad-line");
    await vi.advanceTimersByTimeAsync(8_000);
    await expect(starting).resolves.toContain("SIGKILL");
    expect(lifecycle.state.message).toContain("SIGKILL");
  });

  it("starts a fresh executor after a failure instead of returning the failure", async () => {
    const child = await startReady();
    child.exit(1);
    expect(lifecycle.state.status).toBe("failed");
    const starting = lifecycle.start("/data");
    spawned[1]?.ready();
    await starting;
    expect(lifecycle.state).toEqual({ status: "ready" });
  });
});
