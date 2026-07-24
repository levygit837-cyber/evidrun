import path from "node:path";
import { BrowserWindow } from "electron";

export function createMainWindow(preloadPath: string): BrowserWindow {
  const window = new BrowserWindow({
    width: 1440,
    height: 940,
    minWidth: 880,
    minHeight: 650,
    backgroundColor: "#fcfcfd",
    titleBarStyle: process.platform === "darwin" ? "hiddenInset" : "default",
    show: false,
    webPreferences: {
      preload: path.resolve(preloadPath),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
      webSecurity: true,
      allowRunningInsecureContent: false,
      experimentalFeatures: false,
      devTools: !process.env.EVIDRUN_DISABLE_DEVTOOLS,
    },
  });
  window.once("ready-to-show", () => window.show());
  window.webContents.once("did-finish-load", () => {
    if (!window.isVisible()) window.show();
  });
  window.webContents.on("did-fail-load", (_event, errorCode, errorDescription, validatedUrl) => {
    console.error(
      `[evidrun-renderer] Failed to load ${validatedUrl}: ${errorCode} ${errorDescription}`,
    );
  });
  return window;
}
