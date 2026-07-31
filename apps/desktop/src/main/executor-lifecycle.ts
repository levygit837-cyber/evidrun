import { spawn, type ChildProcessWithoutNullStreams } from "node:child_process";
import { randomUUID } from "node:crypto";
import { EventEmitter } from "node:events";
import path from "node:path";
import readline from "node:readline";
import { app } from "electron";
import type { ExecutorState } from "../shared/desktop-contract.js";
import { parseExecutorReadiness } from "./executor-handshake.js";
import { emitSecureLog } from "./secure-logging.js";
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
/** Whether the OS process is still running, regardless of signals already sent. */
function isRunning(child: ChildProcessWithoutNullStreams): boolean {
  // `child.killed` only reports that a signal was delivered, so a process that ignores or
  // is slow to handle SIGTERM still reads as `killed`. Exit is the pair going non-null.
  return child.exitCode === null && child.signalCode === null;
}

function safeStopFailureMessage(error: unknown): string {
  const known = new Set([
    "Não foi possível encerrar o executor com SIGKILL",
    "Executor não confirmou saída após SIGKILL",
  ]);
  return error instanceof Error && known.has(error.message)
    ? error.message
    : "Falha ao encerrar executor de Runs";
}

export class ExecutorLifecycle extends EventEmitter {
  private child: ChildProcessWithoutNullStreams | null = null;
  private startPromise: Promise<ExecutorState> | null = null;
  private stopPromise: Promise<void> | null = null;
  private stopping = false;
  private instanceId: string | null = null;
  private current: ExecutorState = { status: "stopped" };

  get state(): ExecutorState {
    return this.current;
  }

  async start(dataDir: string): Promise<ExecutorState> {
    // A shutdown in flight still owns the current child. Wait for it so start cannot
    // spawn a second executor alongside one that has not exited.
    if (this.stopPromise) await this.stopPromise;
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
    try {
      if (!child || !isRunning(child)) {
        this.child = null;
        this.instanceId = null;
        this.emitState({ status: "stopped" });
        return;
      }
      await new Promise<void>((resolve, reject) => {
        let timeout: NodeJS.Timeout;
        const onExit = () => {
          clearTimeout(timeout);
          child.off("error", onError);
          resolve();
        };
        const onError = (error: Error) => {
          clearTimeout(timeout);
          child.off("exit", onExit);
          child.off("error", onError);
          reject(error);
        };
        timeout = setTimeout(() => {
          if (!isRunning(child)) return;
          if (!child.kill("SIGKILL")) {
            onError(new Error("Não foi possível encerrar o executor com SIGKILL"));
            return;
          }
          timeout = setTimeout(() => {
            onError(new Error("Executor não confirmou saída após SIGKILL"));
          }, 8_000);
        }, 8_000);
        child.once("exit", onExit);
        child.once("error", onError);
        child.kill("SIGTERM");
      });
      this.emitState({ status: "stopped" });
    } catch (error) {
      if (child && isRunning(child)) this.child = child;
      const message = safeStopFailureMessage(error);
      emitSecureLog("desktop.sidecar.stop_failed", {
        correlationId: this.instanceId ?? undefined,
        errorCode: "desktop.worker_stop_failed",
        error,
        fields: { process: "worker" },
      });
      this.emitState({ status: "failed", message });
      throw new Error(message);
    } finally {
      this.stopping = false;
    }
  }

  private spawnExecutor(dataDir: string): Promise<ExecutorState> {
    const instanceId = randomUUID();
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
    this.instanceId = instanceId;
    child.stdin.write(`${JSON.stringify({ data_dir: dataDir })}\n`);

    return new Promise<ExecutorState>((resolve, reject) => {
      let ready = false;
      // Set once the timeout fires, so the exit it causes is not reported as the reason
      // the executor failed. The user needs to read "never answered", not "exited".
      let timedOut = false;
      // Readiness that never arrives must leave the object usable: reap the process
      // instead of parking a half-dead child that neither `start` nor `stop` can act on.
      const rejectAfterStop = (error: unknown, fallbackMessage: string) => {
        void this.stop().then(
          () => {
            this.emitState({ status: "failed", message: fallbackMessage });
            reject(error);
          },
          (stopError: unknown) => reject(stopError),
        );
      };
      const timeout = setTimeout(() => {
        timedOut = true;
        const message = "Executor de Runs não respondeu ao handshake";
        rejectAfterStop(new Error(message), message);
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
          emitSecureLog("desktop.sidecar.handshake_invalid", {
            correlationId: instanceId,
            errorCode: "desktop.worker_handshake_invalid",
            error,
            fields: { process: "worker" },
          });
          rejectAfterStop(
            new Error("Handshake do executor inválido"),
            "Handshake do executor inválido",
          );
        }
      });

      child.stderr.on("data", (chunk: Buffer) => {
        if (chunk.length === 0) return;
        emitSecureLog("desktop.sidecar.stderr", {
          correlationId: instanceId,
          errorCode: "desktop.worker_stderr",
          fields: { process: "worker" },
        });
      });
      child.once("error", (error) => {
        clearTimeout(timeout);
        this.child = null;
        this.instanceId = null;
        emitSecureLog("desktop.sidecar.failed", {
          correlationId: instanceId,
          errorCode: "desktop.worker_process_error",
          error,
          fields: { process: "worker" },
        });
        this.emitState({ status: "failed", message: "Falha ao iniciar executor de Runs" });
        reject(new Error("Falha ao iniciar executor de Runs"));
      });
      child.once("exit", (code, signal) => {
        clearTimeout(timeout);
        this.child = null;
        this.instanceId = null;
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
