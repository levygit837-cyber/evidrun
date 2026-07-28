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
/** Replace the data dir with a placeholder so diagnostics stay useful without the path. */
export function redactDataDir(line: string, dataDir: string): string {
  return dataDir ? line.split(dataDir).join("<data-dir>") : line;
}

/** Whether the OS process is still running, regardless of signals already sent. */
function isRunning(child: ChildProcessWithoutNullStreams): boolean {
  // `child.killed` only reports that a signal was delivered, so a process that ignores or
  // is slow to handle SIGTERM still reads as `killed`. Exit is the pair going non-null.
  return child.exitCode === null && child.signalCode === null;
}

export class ExecutorLifecycle extends EventEmitter {
  private child: ChildProcessWithoutNullStreams | null = null;
  private startPromise: Promise<ExecutorState> | null = null;
  private stopPromise: Promise<void> | null = null;
  private stopping = false;
  private current: ExecutorState = { status: "stopped" };

  get state(): ExecutorState {
    return this.current;
  }

  async start(dataDir: string): Promise<ExecutorState> {
    // A shutdown in flight has already cleared `child`, so starting now would spawn a
    // second executor alongside one still dying. Wait it out first.
    if (this.stopPromise) await this.stopPromise;
    if (this.child && isRunning(this.child) && this.current.status !== "failed") {
      return this.current;
    }
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
   * Ask the executor to finish, and wait for it to actually be gone.
   *
   * SIGTERM lets `run_forever` leave its poll and release the lease it holds; without
   * waiting, a Run in flight would sit until its lease expired. SIGKILL is the fallback
   * for a process that will not leave, so it has to be driven by real exit rather than by
   * whether a signal was delivered.
   */
  async stop(): Promise<void> {
    if (this.stopPromise) return this.stopPromise;
    this.stopPromise = this.terminate();
    try {
      await this.stopPromise;
    } finally {
      this.stopPromise = null;
    }
  }

  private async terminate(): Promise<void> {
    this.stopping = true;
    const child = this.child;
    this.child = null;
    try {
      if (!child || !isRunning(child)) {
        this.emitState({ status: "stopped" });
        return;
      }
      child.kill("SIGTERM");
      await new Promise<void>((resolve) => {
        const timeout = setTimeout(() => {
          if (isRunning(child)) child.kill("SIGKILL");
        }, 8_000);
        child.once("exit", () => {
          clearTimeout(timeout);
          resolve();
        });
      });
      this.emitState({ status: "stopped" });
    } finally {
      this.stopping = false;
    }
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
      let ready = false;
      // Set once the timeout fires, so the exit it causes is not reported as the reason
      // the executor failed. The user needs to read "never answered", not "exited".
      let timedOut = false;
      // Readiness that never arrives must leave the object usable: reap the process
      // instead of parking a half-dead child that neither `start` nor `stop` can act on.
      const timeout = setTimeout(() => {
        timedOut = true;
        const message = "Executor de Runs não respondeu ao handshake";
        void this.stop().finally(() => {
          this.emitState({ status: "failed", message });
          reject(new Error(message));
        });
      }, 30_000);
      const lines = readline.createInterface({ input: child.stdout });

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
          void this.stop().finally(() => {
            this.emitState({ status: "failed", message: "Handshake do executor inválido" });
            reject(error);
          });
        }
      });

      child.stderr.on("data", (chunk: Buffer) => {
        // A traceback from the worker quotes the paths it failed on, and the data dir is
        // one of them. Keeping it out of argv would be pointless if the log printed it.
        const line = redactDataDir(chunk.toString("utf8").trim(), dataDir);
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
        if (timedOut) return;
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
