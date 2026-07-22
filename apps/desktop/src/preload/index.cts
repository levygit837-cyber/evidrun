import { contextBridge, ipcRenderer } from "electron";
import type { BackendState, DesktopApi } from "../shared/desktop-contract.js";

const channels = {
  appInfo: "desktop:app-info",
  backendConnection: "desktop:backend-connection",
  backendRestart: "desktop:backend-restart",
  backendState: "desktop:backend-state",
  selectFile: "desktop:select-file",
  selectDirectory: "desktop:select-directory",
  showItemInFolder: "desktop:show-item-in-folder",
  openExternal: "desktop:open-external",
} as const;

const desktopApi: DesktopApi = {
  getAppInfo: () => ipcRenderer.invoke(channels.appInfo),
  getBackendConnection: () => ipcRenderer.invoke(channels.backendConnection),
  restartBackend: () => ipcRenderer.invoke(channels.backendRestart),
  selectFile: () => ipcRenderer.invoke(channels.selectFile),
  selectDirectory: () => ipcRenderer.invoke(channels.selectDirectory),
  showItemInFolder: (path: string) => ipcRenderer.invoke(channels.showItemInFolder, path),
  openApprovedExternalUrl: (url: string) => ipcRenderer.invoke(channels.openExternal, url),
  onBackendStateChanged: (callback: (state: BackendState) => void) => {
    const listener = (_event: Electron.IpcRendererEvent, state: BackendState) => callback(state);
    ipcRenderer.on(channels.backendState, listener);
    return () => ipcRenderer.removeListener(channels.backendState, listener);
  },
};

contextBridge.exposeInMainWorld("evidrunDesktop", desktopApi);

