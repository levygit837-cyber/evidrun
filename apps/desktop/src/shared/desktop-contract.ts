/**
 * Stable codes for the bridge's observable refusals.
 *
 * Main throws across an IPC boundary, so the renderer only ever receives a serialized
 * message. Classifying by that text would make a reworded string an observable change, so
 * the code is the contract and the message stays free.
 */
export const bridgeErrorCodes = {
  untrustedSender: "bridge.untrusted_sender",
  senderWithoutFrame: "bridge.sender_without_frame",
  invalidBackendHandshake: "bridge.invalid_backend_handshake",
  invalidExecutorHandshake: "bridge.invalid_executor_handshake",
} as const;

export type BridgeErrorCode = (typeof bridgeErrorCodes)[keyof typeof bridgeErrorCodes];

/** A named bridge refusal. `code` is contract; `message` is text for a human. */
export class BridgeError extends Error {
  constructor(
    public readonly code: BridgeErrorCode,
    message: string,
  ) {
    // The code is prefixed onto the message because an Error crossing IPC arrives as a
    // string: without it the renderer would have nothing stable left to read.
    super(`${code}: ${message}`);
    this.name = "BridgeError";
  }
}

/** Read a bridge code out of anything that crossed the IPC boundary, or return null. */
export function bridgeErrorCodeOf(value: unknown): BridgeErrorCode | null {
  const text =
    value instanceof Error ? value.message : typeof value === "string" ? value : "";
  const known = Object.values(bridgeErrorCodes);
  return known.find((code) => text.includes(code)) ?? null;
}

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

