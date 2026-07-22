export interface BackendConnection {
  baseUrl: string;
  token: string;
  instanceId: string;
}

export interface BackendState {
  status: "starting" | "ready" | "failed" | "stopped";
  message?: string;
}

export interface DesktopApi {
  getAppInfo(): Promise<{ version: string; platform: string; packaged: boolean }>;
  getBackendConnection(): Promise<BackendConnection>;
  restartBackend(): Promise<BackendConnection>;
  selectFile(): Promise<string | null>;
  selectDirectory(): Promise<string | null>;
  showItemInFolder(path: string): Promise<boolean>;
  openApprovedExternalUrl(url: string): Promise<boolean>;
  onBackendStateChanged(callback: (state: BackendState) => void): () => void;
}

export const channels = {
  appInfo: "desktop:app-info",
  backendConnection: "desktop:backend-connection",
  backendRestart: "desktop:backend-restart",
  backendState: "desktop:backend-state",
  selectFile: "desktop:select-file",
  selectDirectory: "desktop:select-directory",
  showItemInFolder: "desktop:show-item-in-folder",
  openExternal: "desktop:open-external",
} as const;

