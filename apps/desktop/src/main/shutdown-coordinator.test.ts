import { describe, expect, it, vi } from "vitest";
import { ShutdownCoordinator } from "./shutdown-coordinator.js";

function quitEvent() {
  return { preventDefault: vi.fn() };
}
function destroyedWindow() {
  return {
    isDestroyed: () => true,
    isMinimized: vi.fn(() => false),
    restore: vi.fn(),
    focus: vi.fn(),
  };
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

    coordinator.handleSecondInstance(destroyedWindow());
    await vi.waitFor(() => expect(quit).toHaveBeenCalledOnce());

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

    coordinator.handleSecondInstance(destroyedWindow());
    await vi.waitFor(() => expect(quit).toHaveBeenCalledOnce());

    expect(stopExecutor).toHaveBeenCalledTimes(2);
    expect(stopBackend).toHaveBeenCalledTimes(2);
  });

  it("queues a retry when a second launch arrives during teardown", async () => {
    let rejectStop: (error: Error) => void = () => undefined;
    const stopExecutor = vi
      .fn<() => Promise<void>>()
      .mockImplementationOnce(
        () =>
          new Promise<void>((_resolve, reject) => {
            rejectStop = reject;
          }),
      )
      .mockResolvedValueOnce();
    const stopBackend = vi.fn<() => Promise<void>>().mockResolvedValue();
    const quit = vi.fn();
    const coordinator = new ShutdownCoordinator({
      stopExecutor,
      stopBackend,
      quit,
      report: vi.fn(),
    });

    coordinator.handleBeforeQuit(quitEvent());
    coordinator.handleSecondInstance(destroyedWindow());
    rejectStop(new Error("executor still alive"));
    await vi.waitFor(() => expect(quit).toHaveBeenCalledOnce());

    expect(stopExecutor).toHaveBeenCalledTimes(2);
    expect(stopBackend).toHaveBeenCalledOnce();
  });

  it("does not turn an early second launch into a shutdown request", () => {
    const stopExecutor = vi.fn<() => Promise<void>>().mockResolvedValue();
    const coordinator = new ShutdownCoordinator({
      stopExecutor,
      stopBackend: vi.fn<() => Promise<void>>().mockResolvedValue(),
      quit: vi.fn(),
      report: vi.fn(),
    });

    coordinator.handleSecondInstance(destroyedWindow());
    expect(stopExecutor).not.toHaveBeenCalled();
  });

  it("restores and focuses a live window instead of touching shutdown", () => {
    const stopExecutor = vi.fn<() => Promise<void>>().mockResolvedValue();
    const window = {
      isDestroyed: () => false,
      isMinimized: () => true,
      restore: vi.fn(),
      focus: vi.fn(),
    };
    const coordinator = new ShutdownCoordinator({
      stopExecutor,
      stopBackend: vi.fn<() => Promise<void>>().mockResolvedValue(),
      quit: vi.fn(),
      report: vi.fn(),
    });

    coordinator.handleSecondInstance(window);

    expect(window.restore).toHaveBeenCalledOnce();
    expect(window.focus).toHaveBeenCalledOnce();
    expect(stopExecutor).not.toHaveBeenCalled();
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
