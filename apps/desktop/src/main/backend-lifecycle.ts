import { spawn, type ChildProcessWithoutNullStreams } from "node:child_process";
import { EventEmitter } from "node:events";
import { randomBytes, randomUUID } from "node:crypto";
import path from "node:path";
import readline from "node:readline";
import { app } from "electron";
import type { BackendConnection, BackendState } from "../shared/desktop-contract.js";
import { parseReadiness } from "./desktop-handshake.js";
import { emitSecureLog } from "./secure-logging.js";
import { sidecarPath } from "./sidecar-path.js";

export class BackendLifecycle extends EventEmitter {
  private child: ChildProcessWithoutNullStreams | null = null;
  private connection: BackendConnection | null = null;
  private startPromise: Promise<BackendConnection> | null = null;
  private stopping = false;

  get state(): BackendState {
    if (this.connection) return { status: "ready" };
    if (this.child) return { status: "starting" };
    return { status: "stopped" };
  }

  async start(): Promise<BackendConnection> {
    if (this.connection) return this.connection;
    if (this.startPromise) return this.startPromise;
    this.startPromise = this.spawnBackend();
    try {
      return await this.startPromise;
    } finally {
      this.startPromise = null;
    }
  }

  async restart(): Promise<BackendConnection> {
    await this.stop();
    return this.start();
  }

  async stop(): Promise<void> {
    this.stopping = true;
    const child = this.child;
    this.child = null;
    this.connection = null;
    if (!child || child.killed) {
      this.emitState({ status: "stopped" });
      this.stopping = false;
      return;
    }
    child.kill("SIGTERM");
    await new Promise<void>((resolve) => {
      const timeout = setTimeout(() => {
        if (!child.killed) child.kill("SIGKILL");
        resolve();
      }, 4_000);
      child.once("exit", () => {
        clearTimeout(timeout);
        resolve();
      });
    });
    this.emitState({ status: "stopped" });
    this.stopping = false;
  }

  private spawnBackend(): Promise<BackendConnection> {
    const token = randomBytes(32).toString("base64url");
    const instanceId = randomUUID();
    const root = path.resolve(import.meta.dirname, "../../../..");
    const executable = app.isPackaged
      ? sidecarPath("evidrun-backend", process.resourcesPath)
      : "uv";
    const args = app.isPackaged
      ? ["serve", "--desktop-handshake"]
      : ["run", "evidrun", "serve", "--desktop-handshake"];

    this.emitState({ status: "starting", message: "Inicializando backend local" });
    const child = spawn(executable, args, {
      cwd: app.isPackaged ? process.resourcesPath : root,
      stdio: ["pipe", "pipe", "pipe"],
      env: {
        PATH: process.env.PATH,
        LANG: process.env.LANG ?? "en_US.UTF-8",
      },
    });
    this.child = child;
    child.stdin.write(
      `${JSON.stringify({
        token,
        data_dir: app.getPath("userData"),
        parent_instance_id: instanceId,
      })}\n`,
    );

    return new Promise<BackendConnection>((resolve, reject) => {
      const timeout = setTimeout(() => {
        child.kill("SIGTERM");
        reject(new Error("Backend handshake timed out"));
      }, 15_000);
      const lines = readline.createInterface({ input: child.stdout });
      let ready = false;

      lines.once("line", (line) => {
        try {
          const message = parseReadiness(line);
          ready = true;
          clearTimeout(timeout);
          this.connection = {
            baseUrl: `http://127.0.0.1:${message.port}`,
            token,
            instanceId: message.backend_instance_id,
          };
          this.emitState({ status: "ready" });
          resolve(this.connection);
        } catch (error) {
          clearTimeout(timeout);
          child.kill("SIGTERM");
          emitSecureLog("desktop.sidecar.handshake_invalid", {
            correlationId: instanceId,
            errorCode: "desktop.backend_handshake_invalid",
            error,
            fields: { process: "backend" },
          });
          reject(new Error("Handshake do backend inválido"));
        }
      });

      child.stderr.on("data", (chunk: Buffer) => {
        if (chunk.length === 0) return;
        emitSecureLog("desktop.sidecar.stderr", {
          correlationId: instanceId,
          errorCode: "desktop.backend_stderr",
          fields: { process: "backend" },
        });
      });
      child.once("error", (error) => {
        clearTimeout(timeout);
        this.connection = null;
        emitSecureLog("desktop.sidecar.failed", {
          correlationId: instanceId,
          errorCode: "desktop.backend_process_error",
          error,
          fields: { process: "backend" },
        });
        this.emitState({ status: "failed", message: "Falha ao iniciar backend local" });
        reject(new Error("Falha ao iniciar backend local"));
      });
      child.once("exit", (code, signal) => {
        clearTimeout(timeout);
        this.child = null;
        this.connection = null;
        const message = `Backend exited (${code ?? signal ?? "unknown"})`;
        this.emitState({ status: ready && this.stopping ? "stopped" : "failed", message });
        if (!ready) reject(new Error(message));
      });
    });
  }

  private emitState(state: BackendState): void {
    this.emit("state", state);
  }
}
