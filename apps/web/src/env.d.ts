import type { BackendConnection, BackendState } from "./types";

declare global {
  interface Window {
    evidrunDesktop?: {
      getAppInfo(): Promise<{ version: string; platform: string; packaged: boolean }>;
      getBackendConnection(): Promise<BackendConnection>;
      restartBackend(): Promise<BackendConnection>;
      selectFile(): Promise<string | null>;
      selectDirectory(): Promise<string | null>;
      showItemInFolder(path: string): Promise<boolean>;
      openApprovedExternalUrl(url: string): Promise<boolean>;
      onBackendStateChanged(callback: (state: BackendState) => void): () => void;
    };
  }
}

export {};
