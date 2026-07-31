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
import { ExecutorLifecycle } from "./executor-lifecycle.js";
import { isApprovedExternalUrl, isTrustedRendererUrl } from "./external-links.js";
import { lockDownPermissions } from "./permissions.js";
import { ShutdownCoordinator } from "./shutdown-coordinator.js";
import { createMainWindow } from "./windows.js";
import { channels } from "../shared/desktop-contract.js";

const currentDir = path.dirname(fileURLToPath(import.meta.url));
const devServerUrl = process.env.EVIDRUN_DEV_SERVER_URL;
const backend = new BackendLifecycle();
const executor = new ExecutorLifecycle();
const shutdown = new ShutdownCoordinator({
  stopExecutor: () => executor.stop(),
  stopBackend: () => backend.stop(),
  quit: () => app.quit(),
  report: (error) => console.error("[evidrun]", error instanceof Error ? error.message : error),
});
let mainWindow: BrowserWindow | null = null;

/** The data boundary both planes share; the handshake already resolves it this way. */
function dataDir(): string {
  return app.getPath("userData");
}

/**
 * Send a state update to the renderer, if there is still one listening.
 *
 * A destroyed `BrowserWindow` throws from the `webContents` getter itself, so optional
 * chaining is not enough. This runs on the shutdown path, where a throw would abort the
 * teardown sequence and leave the app running with no window.
 */
function publish(channel: string, state: unknown): void {
  if (!mainWindow || mainWindow.isDestroyed()) return;
  mainWindow.webContents.send(channel, state);
}

/**
 * Bring the executor up, tolerating failure.
 *
 * A failed executor is a stalled queue, not a dead app: evidence stays readable and the
 * failure is published as state. Rejecting here would take the window down with it.
 */
async function startExecutor(): Promise<void> {
  try {
    await executor.start(dataDir());
  } catch (error) {
    console.error("[evidrun-worker]", error instanceof Error ? error.message : error);
  }
}

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
  ipcMain.handle(channels.executorState, (event) => {
    validateSender(senderUrl(event.senderFrame));
    return executor.state;
  });
  ipcMain.handle(channels.executorRestart, async (event) => {
    validateSender(senderUrl(event.senderFrame));
    return executor.restart(dataDir());
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
  backend.removeAllListeners("state");
  executor.removeAllListeners("state");
  backend.on("state", (state) => publish(channels.backendState, state));
  executor.on("state", (state) => publish(channels.executorStateChanged, state));
  mainWindow.webContents.on("will-navigate", (event, target) => {
    if (!isTrustedRendererUrl(target, devServerUrl)) event.preventDefault();
  });
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (isApprovedExternalUrl(url)) void shell.openExternal(url);
    return { action: "deny" };
  });
  await backend.start();
  // After the backend, so the queue the executor drains is already reachable, and not
  // awaited: a slow or failing executor must not delay the window.
  void startExecutor();
  if (devServerUrl) await mainWindow.loadURL(devServerUrl);
  else await mainWindow.loadURL("evidrun://app/");
}

/**
 * One app instance per machine, because instances share `userData`.
 *
 * Two instances would supervise two executors over the same database. Lease fencing means
 * that is safe — no Run executes twice — but it is still two processes competing where the
 * brief asks for exactly one, and the second app's executor state would describe a queue
 * the first one is draining.
 */
if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on("second-instance", () => shutdown.handleSecondInstance(mainWindow));
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

/**
 * Stop the executor before the backend.
 *
 * Order matters: the executor needs a reachable database to release the lease it holds.
 * If its process cannot be confirmed dead, shutdown fails closed: the backend and app
 * remain alive so a later quit request can retry without orphaning the executor.
 */
app.on("before-quit", (event) => shutdown.handleBeforeQuit(event));
app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
