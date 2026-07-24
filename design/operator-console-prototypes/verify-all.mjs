import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.dirname(fileURLToPath(import.meta.url));
const workspaces = [
  "01-carbon-rhythm",
  "02-civic-console",
  "03-command-deck",
  "04-spatial-trace",
  "05-evidence-ledger-open-canvas",
];
const commands = [
  ["npm", ["test"]],
  ["npm", ["run", "build"]],
  ["npm", ["run", "test:sites"]],
];

const results = [];

for (const workspace of workspaces) {
  const cwd = path.join(root, workspace);
  for (const [command, args] of commands) {
    const label = `${command} ${args.join(" ")}`;
    const result = spawnSync(command, args, {
      cwd,
      encoding: "utf8",
      env: process.env,
      stdio: "pipe",
    });

    results.push({
      workspace,
      command: label,
      status: result.status,
      stdout: result.stdout,
      stderr: result.stderr,
    });

    process.stdout.write(`\n[${workspace}] ${label}\n`);
    process.stdout.write(result.stdout ?? "");
    process.stderr.write(result.stderr ?? "");

    if (result.status !== 0) {
      process.exitCode = 1;
    }
  }
}

const failures = results.filter((result) => result.status !== 0);
process.stdout.write(
  `\nVerified ${results.length} command runs across ${workspaces.length} workspaces. ` +
    `${failures.length} failure(s).\n`,
);
