import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import {
  app,
  BrowserWindow,
  dialog,
  ipcMain,
  Menu,
  net,
  protocol,
  session,
  shell,
} from "electron";
import { BackendLifecycle } from "./backend-lifecycle.js";
import { isApprovedExternalUrl, isTrustedRendererUrl } from "./external-links.js";
import { lockDownPermissions } from "./permissions.js";
import { createMainWindow } from "./windows.js";
import { channels } from "../shared/desktop-contract.js";

const currentDir = path.dirname(fileURLToPath(import.meta.url));
const devServerUrl = process.env.EVIDRUN_DEV_SERVER_URL;
const backend = new BackendLifecycle();
let mainWindow: BrowserWindow | null = null;

protocol.registerSchemesAsPrivileged([
  {
    scheme: "evidrun",
    privileges: {
      standard: true,
      secure: true,
      supportFetchAPI: true,
      corsEnabled: true,
    },
  },
]);

function validateSender(frameUrl: string): void {
  if (!isTrustedRendererUrl(frameUrl, devServerUrl)) throw new Error("Untrusted IPC sender");
}

function senderUrl(frame: Electron.WebFrameMain | null): string {
  if (!frame) throw new Error("IPC sender has no frame");
  return frame.url;
}

function registerIpc(): void {
  ipcMain.handle(channels.appInfo, (event) => {
    validateSender(senderUrl(event.senderFrame));
    return { version: app.getVersion(), platform: process.platform, packaged: app.isPackaged };
  });
  ipcMain.handle(channels.backendConnection, async (event) => {
    validateSender(senderUrl(event.senderFrame));
    return backend.start();
  });
  ipcMain.handle(channels.backendRestart, async (event) => {
    validateSender(senderUrl(event.senderFrame));
    return backend.restart();
  });
  ipcMain.handle(channels.selectFile, async (event) => {
    validateSender(senderUrl(event.senderFrame));
    const result = await dialog.showOpenDialog({ properties: ["openFile"] });
    return result.canceled ? null : result.filePaths[0] ?? null;
  });
  ipcMain.handle(channels.selectDirectory, async (event) => {
    validateSender(senderUrl(event.senderFrame));
    const result = await dialog.showOpenDialog({ properties: ["openDirectory", "createDirectory"] });
    return result.canceled ? null : result.filePaths[0] ?? null;
  });
  ipcMain.handle(channels.showItemInFolder, (event, target: unknown) => {
    validateSender(senderUrl(event.senderFrame));
    if (typeof target !== "string" || target.length > 4096 || !path.isAbsolute(target)) return false;
    shell.showItemInFolder(path.normalize(target));
    return true;
  });
  ipcMain.handle(channels.openExternal, async (event, target: unknown) => {
    validateSender(senderUrl(event.senderFrame));
    if (typeof target !== "string" || !isApprovedExternalUrl(target)) return false;
    await shell.openExternal(target);
    return true;
  });
}

async function registerAppProtocol(): Promise<void> {
  const webRoot = path.resolve(app.getAppPath(), "apps/web/dist");
  protocol.handle("evidrun", async (request) => {
    const url = new URL(request.url);
    const requested = decodeURIComponent(url.pathname === "/" ? "/index.html" : url.pathname);
    const target = path.resolve(webRoot, `.${requested}`);
    if (!target.startsWith(`${webRoot}${path.sep}`) && target !== webRoot) {
      return new Response("Not found", { status: 404 });
    }
    return net.fetch(pathToFileURL(target).toString());
  });
}

async function createApplicationWindow(): Promise<void> {
  const preloadPath = path.resolve(currentDir, "../preload/index.cjs");
  mainWindow = createMainWindow(preloadPath);
  backend.on("state", (state) => mainWindow?.webContents.send(channels.backendState, state));
  mainWindow.webContents.on("will-navigate", (event, target) => {
    if (!isTrustedRendererUrl(target, devServerUrl)) event.preventDefault();
  });
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (isApprovedExternalUrl(url)) void shell.openExternal(url);
    return { action: "deny" };
  });
  await backend.start();
  if (devServerUrl) await mainWindow.loadURL(devServerUrl);
  else await mainWindow.loadURL("evidrun://app/");
}

app.whenReady().then(async () => {
  lockDownPermissions(session.defaultSession);
  await registerAppProtocol();
  registerIpc();
  Menu.setApplicationMenu(
    Menu.buildFromTemplate([
      { role: "appMenu" },
      { role: "fileMenu" },
      { role: "editMenu" },
      { role: "viewMenu" },
      { role: "windowMenu" },
      { role: "help" },
    ]),
  );
  await createApplicationWindow();
  app.on("activate", async () => {
    if (BrowserWindow.getAllWindows().length === 0) await createApplicationWindow();
  });
});

app.on("before-quit", () => {
  void backend.stop();
});
app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
