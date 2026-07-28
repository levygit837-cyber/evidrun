import { spawn, type ChildProcessWithoutNullStreams } from "node:child_process";
import { EventEmitter } from "node:events";
import path from "node:path";
import readline from "node:readline";
import { app } from "electron";
import type { ExecutorState } from "../shared/desktop-contract.js";
import { parseExecutorReadiness } from "./executor-handshake.js";
import { sidecarPath } from "./sidecar-path.js";

/**
 * Supervises the durable Run executor as a process of its own.
 *
 * A sibling of `BackendLifecycle`, not a copy: the executor announces a worker id rather
 * than a port and token, and it has no connection object to hand out — nothing in the
 * renderer talks to it directly. Its state exists so a stalled queue is visible instead
 * of silent.
 *
 * The data dir goes over stdin, never argv, because a database path in argv is readable
 * by every other process on the machine. Killing this process is safe by construction:
 * ADR 0014 has an expired lease produce a new attempt on the same Run, never a new Run.
 */
export class ExecutorLifecycle extends EventEmitter {
  private child: ChildProcessWithoutNullStreams | null = null;
  private startPromise: Promise<ExecutorState> | null = null;
  private stopping = false;
  private current: ExecutorState = { status: "stopped" };

  get state(): ExecutorState {
    return this.current;
  }

  async start(dataDir: string): Promise<ExecutorState> {
    if (this.child) return this.current;
    if (this.startPromise) return this.startPromise;
    this.startPromise = this.spawnExecutor(dataDir);
    try {
      return await this.startPromise;
    } finally {
      this.startPromise = null;
    }
  }

  async restart(dataDir: string): Promise<ExecutorState> {
    await this.stop();
    return this.start(dataDir);
  }

  /**
   * Ask the executor to finish, and wait for it.
   *
   * SIGTERM lets `run_forever` leave its poll and release the lease it holds; without
   * waiting, a Run in flight would sit until its lease expired. SIGKILL is the fallback,
   * not the opening move.
   */
  async stop(): Promise<void> {
    this.stopping = true;
    const child = this.child;
    this.child = null;
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
      }, 8_000);
      child.once("exit", () => {
        clearTimeout(timeout);
        resolve();
      });
    });
    this.emitState({ status: "stopped" });
    this.stopping = false;
  }

  private spawnExecutor(dataDir: string): Promise<ExecutorState> {
    const root = path.resolve(import.meta.dirname, "../../../..");
    const executable = app.isPackaged ? sidecarPath("evidrun-worker", process.resourcesPath) : "uv";
    const args = app.isPackaged
      ? ["--desktop-handshake"]
      : ["run", "evidrun-worker", "--desktop-handshake"];

    this.emitState({ status: "starting", message: "Inicializando executor de Runs" });
    const child = spawn(executable, args, {
      cwd: app.isPackaged ? process.resourcesPath : root,
      stdio: ["pipe", "pipe", "pipe"],
      env: {
        PATH: process.env.PATH,
        LANG: process.env.LANG ?? "en_US.UTF-8",
      },
    });
    this.child = child;
    child.stdin.write(`${JSON.stringify({ data_dir: dataDir })}\n`);

    return new Promise<ExecutorState>((resolve, reject) => {
      const timeout = setTimeout(() => {
        child.kill("SIGTERM");
        const message = "Executor de Runs não respondeu ao handshake";
        this.emitState({ status: "failed", message });
        reject(new Error(message));
      }, 30_000);
      const lines = readline.createInterface({ input: child.stdout });
      let ready = false;

      lines.once("line", (line) => {
        try {
          parseExecutorReadiness(line);
          ready = true;
          clearTimeout(timeout);
          const state: ExecutorState = { status: "ready" };
          this.emitState(state);
          resolve(state);
        } catch (error) {
          clearTimeout(timeout);
          child.kill("SIGTERM");
          this.emitState({ status: "failed", message: "Handshake do executor inválido" });
          reject(error);
        }
      });

      child.stderr.on("data", (chunk: Buffer) => {
        const line = chunk.toString("utf8").trim();
        if (line) console.error(`[evidrun-worker] ${line}`);
      });
      child.once("error", (error) => {
        clearTimeout(timeout);
        this.child = null;
        this.emitState({ status: "failed", message: error.message });
        reject(error);
      });
      child.once("exit", (code, signal) => {
        clearTimeout(timeout);
        this.child = null;
        const message = `Executor encerrou (${code ?? signal ?? "desconhecido"})`;
        this.emitState({ status: ready && this.stopping ? "stopped" : "failed", message });
        if (!ready) reject(new Error(message));
      });
    });
  }

  private emitState(state: ExecutorState): void {
    this.current = state;
    this.emit("state", state);
  }
}
