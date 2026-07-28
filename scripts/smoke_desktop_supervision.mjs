/**
 * The gate against blocker B2: a Run enqueued with no terminal involved must reach a
 * terminal state, drained by a supervised executor.
 *
 * This exercises the two processes the desktop shell spawns, over the same data dir and
 * over the same stdin handshakes, without Electron. Removing the executor from the picture
 * has to make this fail — a gate that passes with the bug present is not a gate.
 *
 * Offline and deterministic by construction: the canonical benchmark needs no provider.
 */

import { spawn } from "node:child_process";
import { randomBytes, randomUUID } from "node:crypto";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import readline from "node:readline";

const SKIP_EXECUTOR = process.env.EVIDRUN_SMOKE_SKIP_EXECUTOR === "1";
const dataDir = await mkdtemp(path.join(tmpdir(), "evidrun-supervision-"));
const token = randomBytes(32).toString("base64url");
const env = { ...process.env };
const children = [];

function launch(args) {
  const child = spawn("uv", ["run", ...args], { cwd: process.cwd(), stdio: ["pipe", "pipe", "pipe"], env });
  children.push(child);
  child.stderr.on("data", (chunk) => {
    const line = chunk.toString("utf8").trim();
    if (line) console.error(`[${args[1] ?? args[0]}] ${line}`);
  });
  return child;
}

function readiness(child, label, timeoutMs) {
  return new Promise((resolve, reject) => {
    const lines = readline.createInterface({ input: child.stdout });
    const timer = setTimeout(() => reject(new Error(`${label} readiness timed out`)), timeoutMs);
    const finish = (callback, value) => {
      clearTimeout(timer);
      lines.close();
      callback(value);
    };
    lines.once("line", (line) => finish(resolve, JSON.parse(line)));
    child.once("exit", (code, signal) =>
      finish(reject, new Error(`${label} exited before readiness (${code ?? signal})`)),
    );
  });
}

async function api(baseUrl, route, init) {
  const response = await fetch(`${baseUrl}${route}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${token}`,
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
  });
  if (!response.ok) throw new Error(`${route} failed: ${response.status} ${await response.text()}`);
  return response.status === 204 ? null : response.json();
}

/** Poll the public Run route until it leaves the non-terminal states. */
async function waitForTerminal(baseUrl, runId, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  const pending = new Set(["queued", "preparing", "running", "evaluating"]);
  while (Date.now() < deadline) {
    const run = await api(baseUrl, `/api/v1/runs/${runId}`);
    if (!pending.has(run.status)) return run.status;
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  return null;
}

try {
  const backend = launch(["evidrun", "serve", "--desktop-handshake"]);
  backend.stdin.write(
    `${JSON.stringify({ token, data_dir: dataDir, parent_instance_id: randomUUID() })}\n`,
  );
  const banner = await readiness(backend, "backend", 60_000);
  if (banner.protocol !== "evidrun-desktop-v1") throw new Error("Invalid backend protocol");
  const baseUrl = `http://127.0.0.1:${banner.port}`;

  // The supervised executor takes its data dir over stdin, never argv.
  if (!SKIP_EXECUTOR) {
    const executor = launch(["evidrun-worker", "--desktop-handshake"]);
    executor.stdin.write(`${JSON.stringify({ data_dir: dataDir })}\n`);
    const executorBanner = await readiness(executor, "executor", 60_000);
    if (executorBanner.protocol !== "evidrun-worker-v1") throw new Error("Invalid executor protocol");
    if (!executorBanner.worker_id) throw new Error("Executor announced no worker id");
    if (JSON.stringify(executorBanner).includes(dataDir)) {
      throw new Error("Executor readiness leaked the data dir");
    }
  }

  // Bootstrap drains its own Runs inline, so reuse its RunSpec to enqueue a fresh Run that
  // nothing has claimed. That is the state blocker B2 left stuck forever.
  const demo = await api(baseUrl, "/api/v1/demo/bootstrap", { method: "POST" });
  if (!demo.baseline_run_id) throw new Error(`Bootstrap returned no Run: ${JSON.stringify(demo)}`);
  const seeded = await api(baseUrl, `/api/v1/runs/${demo.baseline_run_id}`);
  const runSpecId = seeded.run_spec_id;
  if (!runSpecId) throw new Error(`Run carries no RunSpec: ${JSON.stringify(seeded)}`);

  const admission = await api(baseUrl, `/api/v1/run-specs/${runSpecId}/admit`, { method: "POST" });
  if (admission.decision !== "admitted") throw new Error(`Admission was ${admission.decision}`);

  const enqueued = await api(baseUrl, `/api/v1/run-specs/${runSpecId}/runs`, {
    method: "POST",
    headers: { "Idempotency-Key": `smoke-${randomUUID()}` },
    body: JSON.stringify({ admission_id: admission.id }),
  });
  if (enqueued.status !== "queued") throw new Error(`Expected a queued job, got ${enqueued.status}`);

  const status = await waitForTerminal(baseUrl, enqueued.run_id, 90_000);
  if (status === null) {
    throw new Error(
      SKIP_EXECUTOR
        ? "Run stayed non-terminal, as expected without a supervised executor"
        : "Run never reached a terminal state: the executor is not draining the queue",
    );
  }
  console.log(JSON.stringify({ supervision: "ok", run: enqueued.run_id, status }));
} finally {
  for (const child of children) child.kill("SIGTERM");
  await rm(dataDir, { recursive: true, force: true });
}
