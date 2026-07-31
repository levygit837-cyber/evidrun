import { EventEmitter } from "node:events";
import { beforeEach, describe, expect, it, vi } from "vitest";

class FakeBackend extends EventEmitter {
  stdin = { write: vi.fn() };
  stdout = new EventEmitter();
  stderr = new EventEmitter();
  killed = false;

  kill(): boolean {
    this.killed = true;
    return true;
  }

  ready(): void {
    this.stdout.emit("line-source");
  }
}

let child: FakeBackend;

vi.mock("node:child_process", () => ({
  spawn: () => child,
}));
vi.mock("electron", () => ({
  app: {
    getPath: () => "/Users/someone/Library/evidrun",
    isPackaged: false,
  },
}));

const READY_LINE = JSON.stringify({
  protocol: "evidrun-desktop-v1",
  port: 43121,
  backend_instance_id: "backend-1",
  schema_version: "1",
  pid: 123,
  health_nonce: "nonce",
});

function createInterface({ input }: { input: EventEmitter }) {
  const lines = new EventEmitter();
  input.on("line-source", () => lines.emit("line", READY_LINE));
  return lines;
}

vi.mock("node:readline", () => ({ default: { createInterface }, createInterface }));

const { BackendLifecycle } = await import("./backend-lifecycle.js");

describe("backend lifecycle secure logging", () => {
  beforeEach(() => {
    child = new FakeBackend();
    vi.restoreAllMocks();
  });

  it("does not forward backend stderr into desktop logs", async () => {
    const report = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const secret = "fixture-secret-must-never-be-logged";
    const lifecycle = new BackendLifecycle();
    const starting = lifecycle.start();

    child.stderr.emit(
      "data",
      Buffer.from(`Cookie: session=${secret} at /Users/someone/Library/evidrun`),
    );
    child.ready();
    await starting;

    const serialized = String(report.mock.calls[0]?.[0]);
    expect(serialized).toContain('"event_code":"desktop.sidecar.stderr"');
    expect(serialized).toMatch(/"correlation_id":"[0-9a-f-]+"/);
    expect(serialized).toContain('"process":"backend"');
    expect(serialized).not.toContain(secret);
    expect(serialized).not.toContain("someone");
  });

  it("rejects process failures without propagating the original exception text", async () => {
    const report = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const secret = `sk-proj-${"A".repeat(32)}`;
    const lifecycle = new BackendLifecycle();
    const starting = lifecycle.start();

    child.emit("error", new Error(`spawn failed with ${secret}`));

    await expect(starting).rejects.toThrow("Falha ao iniciar backend local");
    await expect(starting).rejects.not.toThrow(secret);
    const serialized = report.mock.calls.map(([line]) => String(line)).join("\n");
    expect(serialized).toContain('"event_code":"desktop.sidecar.failed"');
    expect(serialized).not.toContain(secret);
  });
});
