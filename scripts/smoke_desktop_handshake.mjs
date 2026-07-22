import { spawn } from "node:child_process";
import { randomBytes, randomUUID } from "node:crypto";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import readline from "node:readline";

const dataDir = await mkdtemp(path.join(tmpdir(), "evidrun-handshake-"));
const token = randomBytes(32).toString("base64url");
const child = spawn("uv", ["run", "evidrun", "serve", "--desktop-handshake"], {
  cwd: process.cwd(),
  stdio: ["pipe", "pipe", "pipe"],
  env: { ...process.env, UV_CACHE_DIR: "/private/tmp/evidrun-uv-cache" },
});

let stderr = "";
child.stderr.on("data", (chunk) => {
  stderr += chunk.toString("utf8");
});

function waitForReadiness() {
  return new Promise((resolve, reject) => {
    const lines = readline.createInterface({ input: child.stdout });
    const timeout = setTimeout(() => {
      child.kill("SIGKILL");
      reject(new Error(`Desktop handshake timed out.\n${stderr}`));
    }, 15_000);

    const finish = (callback, value) => {
      clearTimeout(timeout);
      lines.close();
      callback(value);
    };

    lines.once("line", (line) => finish(resolve, line));
    child.once("error", (error) => finish(reject, error));
    child.once("exit", (code, signal) =>
      finish(
        reject,
        new Error(`Backend exited before readiness (${code ?? signal ?? "unknown"}).\n${stderr}`),
      ),
    );
  });
}

try {
  child.stdin.write(
    `${JSON.stringify({
      token,
      data_dir: dataDir,
      parent_instance_id: randomUUID(),
    })}\n`,
  );
  const readiness = JSON.parse(await waitForReadiness());
  if (readiness.protocol !== "evidrun-desktop-v1") throw new Error("Invalid protocol");

  const unauthenticated = await fetch(`http://127.0.0.1:${readiness.port}/api/v1/health`);
  if (unauthenticated.status !== 401) throw new Error("Backend accepted an unauthenticated request");

  const authenticated = await fetch(`http://127.0.0.1:${readiness.port}/api/v1/health`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!authenticated.ok) throw new Error(`Health failed: ${authenticated.status}`);
  const body = await authenticated.json();
  console.log(JSON.stringify({ handshake: "ok", health: body.status, port: readiness.port }));
} finally {
  child.kill("SIGTERM");
  await rm(dataDir, { recursive: true, force: true });
}
