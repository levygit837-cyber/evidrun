import type { BackendConnection, BackendState, ExecutorState } from "./types";

declare global {
  interface Window {
    evidrunDesktop?: {
      getAppInfo(): Promise<{ version: string; platform: string; packaged: boolean }>;
      getBackendConnection(): Promise<BackendConnection>;
      restartBackend(): Promise<BackendConnection>;
      getExecutorState(): Promise<ExecutorState>;
      restartExecutor(): Promise<ExecutorState>;
      selectFile(): Promise<string | null>;
      selectDirectory(): Promise<string | null>;
      showItemInFolder(path: string): Promise<boolean>;
      openApprovedExternalUrl(url: string): Promise<boolean>;
      onBackendStateChanged(callback: (state: BackendState) => void): () => void;
      onExecutorStateChanged(callback: (state: ExecutorState) => void): () => void;
    };
  }
}

export {};
