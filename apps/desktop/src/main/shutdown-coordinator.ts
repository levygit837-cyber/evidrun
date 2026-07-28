export interface ShutdownDependencies {
  stopExecutor(): Promise<void>;
  stopBackend(): Promise<void>;
  quit(): void;
  report(error: unknown): void;
}

/**
 * Every quit request is blocked while teardown runs. A failed process stop leaves the
 * app alive so a later quit request can retry without orphaning a sidecar.
 */
export class ShutdownCoordinator {
  private attempt: Promise<void> | null = null;
  private quitAuthorized = false;

  constructor(private readonly dependencies: ShutdownDependencies) {}

  handleBeforeQuit(event: { preventDefault(): void }): void {
    if (this.quitAuthorized) return;
    event.preventDefault();
    if (this.attempt) return;
    this.attempt = this.shutdown().finally(() => {
      this.attempt = null;
    });
  }

  private async shutdown(): Promise<void> {
    try {
      await this.dependencies.stopExecutor();
    } catch (error) {
      this.dependencies.report(error);
      return;
    }

    try {
      await this.dependencies.stopBackend();
    } catch (error) {
      this.dependencies.report(error);
      return;
    }

    this.quitAuthorized = true;
    this.dependencies.quit();
  }
}
