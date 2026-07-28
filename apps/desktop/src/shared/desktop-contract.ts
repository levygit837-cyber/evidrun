export interface BackendConnection {
  baseUrl: string;
  token: string;
  instanceId: string;
}

export interface BackendState {
  status: "starting" | "ready" | "failed" | "stopped";
  message?: string;
}

/**
 * The Run executor's process state, tracked separately from the backend's.
 *
 * ADR 0002 and ADR 0014 keep the Control Plane and the Execution Plane apart, so a dead
 * executor and a dead API are different failures with different consequences: the first
 * stalls the queue while evidence stays readable, the second takes reading away. One
 * status field could not say which happened.
 */
export interface ExecutorState {
  status: "starting" | "ready" | "failed" | "stopped";
  message?: string;
}

export interface DesktopApi {
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
}

export const channels = {
  appInfo: "desktop:app-info",
  backendConnection: "desktop:backend-connection",
  backendRestart: "desktop:backend-restart",
  backendState: "desktop:backend-state",
  executorState: "desktop:executor-state",
  executorStateChanged: "desktop:executor-state-changed",
  executorRestart: "desktop:executor-restart",
  selectFile: "desktop:select-file",
  selectDirectory: "desktop:select-directory",
  showItemInFolder: "desktop:show-item-in-folder",
  openExternal: "desktop:open-external",
} as const;

