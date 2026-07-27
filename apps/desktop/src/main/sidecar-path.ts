import path from "node:path";

/**
 * Where the frozen Python sidecars live inside the packaged app.
 *
 * PyInstaller builds these as `--onedir`, so each sidecar is a directory holding its
 * executable plus shared libraries. A onefile build would re-extract tens of MB on
 * every launch and blow past the readiness timeout.
 */
export function sidecarPath(name: string, resourcesRoot: string): string {
  const executable = process.platform === "win32" ? `${name}.exe` : name;
  return path.join(resourcesRoot, "backend", name, executable);
}
