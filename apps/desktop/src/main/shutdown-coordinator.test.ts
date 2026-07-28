import { describe, expect, it, vi } from "vitest";
import { ShutdownCoordinator } from "./shutdown-coordinator.js";

function quitEvent() {
  return { preventDefault: vi.fn() };
}

describe("desktop shutdown coordinator", () => {
  it("keeps the backend and app alive when the executor cannot stop, then permits retry", async () => {
    const stopExecutor = vi
      .fn<() => Promise<void>>()
      .mockRejectedValueOnce(new Error("executor still alive"))
      .mockResolvedValueOnce();
    const stopBackend = vi.fn<() => Promise<void>>().mockResolvedValue();
    const quit = vi.fn();
    const report = vi.fn();
    const coordinator = new ShutdownCoordinator({ stopExecutor, stopBackend, quit, report });

    const firstEvent = quitEvent();
    coordinator.handleBeforeQuit(firstEvent);
    await vi.waitFor(() => expect(report).toHaveBeenCalledWith(expect.any(Error)));

    expect(firstEvent.preventDefault).toHaveBeenCalledOnce();
    expect(stopBackend).not.toHaveBeenCalled();
    expect(quit).not.toHaveBeenCalled();

    const retryEvent = quitEvent();
    coordinator.handleBeforeQuit(retryEvent);
    await vi.waitFor(() => expect(quit).toHaveBeenCalledOnce());

    expect(retryEvent.preventDefault).toHaveBeenCalledOnce();
    expect(stopExecutor).toHaveBeenCalledTimes(2);
    expect(stopBackend).toHaveBeenCalledOnce();
  });

  it("keeps the app alive when the backend cannot stop, then permits retry", async () => {
    const stopExecutor = vi.fn<() => Promise<void>>().mockResolvedValue();
    const stopBackend = vi
      .fn<() => Promise<void>>()
      .mockRejectedValueOnce(new Error("backend still alive"))
      .mockResolvedValueOnce();
    const quit = vi.fn();
    const report = vi.fn();
    const coordinator = new ShutdownCoordinator({ stopExecutor, stopBackend, quit, report });

    coordinator.handleBeforeQuit(quitEvent());
    await vi.waitFor(() => expect(report).toHaveBeenCalledWith(expect.any(Error)));

    expect(quit).not.toHaveBeenCalled();

    const retryEvent = quitEvent();
    coordinator.handleBeforeQuit(retryEvent);
    await vi.waitFor(() => expect(quit).toHaveBeenCalledOnce());

    expect(retryEvent.preventDefault).toHaveBeenCalledOnce();
    expect(stopExecutor).toHaveBeenCalledTimes(2);
    expect(stopBackend).toHaveBeenCalledTimes(2);
  });

  it("authorizes the quit event emitted by its own successful teardown", async () => {
    const stopExecutor = vi.fn<() => Promise<void>>().mockResolvedValue();
    const stopBackend = vi.fn<() => Promise<void>>().mockResolvedValue();
    const quit = vi.fn();
    const coordinator = new ShutdownCoordinator({
      stopExecutor,
      stopBackend,
      quit,
      report: vi.fn(),
    });

    const requestedEvent = quitEvent();
    coordinator.handleBeforeQuit(requestedEvent);
    await vi.waitFor(() => expect(quit).toHaveBeenCalledOnce());

    const authorizedEvent = quitEvent();
    coordinator.handleBeforeQuit(authorizedEvent);

    expect(requestedEvent.preventDefault).toHaveBeenCalledOnce();
    expect(authorizedEvent.preventDefault).not.toHaveBeenCalled();
    expect(stopExecutor).toHaveBeenCalledOnce();
    expect(stopBackend).toHaveBeenCalledOnce();
  });
});
