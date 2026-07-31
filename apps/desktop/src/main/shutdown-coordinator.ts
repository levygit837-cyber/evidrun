export interface ShutdownDependencies {
  stopExecutor(): Promise<void>;
  stopBackend(): Promise<void>;
  quit(): void;
  report(error: unknown): void;
}
export interface SecondInstanceWindow {
  isDestroyed(): boolean;
  isMinimized(): boolean;
  restore(): void;
  focus(): void;
}

/**
 * Every quit request is blocked while teardown runs. A failed process stop leaves the
 * app alive so a later launch request can retry without orphaning a sidecar.
 */
export class ShutdownCoordinator {
  private attempt: Promise<void> | null = null;
  private quitAuthorized = false;
  private retryRequested = false;
  private retryable = false;

  constructor(private readonly dependencies: ShutdownDependencies) {}

  handleBeforeQuit(event: { preventDefault(): void }): void {
    if (this.quitAuthorized) return;
    event.preventDefault();
    if (this.attempt) return;
    this.startShutdown();
  }

  handleSecondInstance(window: SecondInstanceWindow | null): void {
    if (!window || window.isDestroyed()) {
      this.retryShutdown();
      return;
    }
    if (window.isMinimized()) window.restore();
    window.focus();
  }

  /** Retry only a shutdown already in flight or one that failed. */
  private retryShutdown(): boolean {
    if (this.quitAuthorized) return false;
    if (this.attempt) {
      this.retryRequested = true;
      return true;
    }
    if (!this.retryable) return false;
    this.startShutdown();
    return true;
  }

  private startShutdown(): void {
    this.retryable = false;
    this.attempt = this.shutdown().finally(() => {
      this.attempt = null;
      if (this.retryRequested && !this.quitAuthorized) {
        this.retryRequested = false;
        this.startShutdown();
      }
    });
  }

  private async shutdown(): Promise<void> {
    try {
      await this.dependencies.stopExecutor();
    } catch (error) {
      this.retryable = true;
      this.dependencies.report(error);
      return;
    }

    try {
      await this.dependencies.stopBackend();
    } catch (error) {
      this.retryable = true;
      this.dependencies.report(error);
      return;
    }

    this.quitAuthorized = true;
    this.dependencies.quit();
  }
}
