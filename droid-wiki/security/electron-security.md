# Electron security

The Electron shell is the most exposed surface: it runs a Chromium renderer and spawns a local backend. The Main process is hardened so that a compromised renderer cannot escalate into desktop capability or reach the backend without the launch token. The normative baseline is `docs/security/electron-security.md`; the code is under `apps/desktop/src/main/`. For the wiring and directory layout see [apps: desktop](../apps/desktop.md).

## Window hardening

`createMainWindow` in `apps/desktop/src/main/windows.ts` builds the `BrowserWindow` with:

- `nodeIntegration: false`
- `contextIsolation: true`
- `sandbox: true`
- `webSecurity: true`
- `allowRunningInsecureContent: false`
- `experimentalFeatures: false`
- `devTools` enabled unless `EVIDRUN_DISABLE_DEVTOOLS` is set

The renderer therefore has no Node integration and runs sandboxed and context-isolated. It reaches the Main process only through the preload bridge.

## IPC: sender validation and a channel allowlist

`registerIpc` in `apps/desktop/src/main/index.ts` registers handlers only for the channels declared in `apps/desktop/src/shared/desktop-contract.ts` (app info, backend connection, backend restart, file/directory pickers, show-item-in-folder, open-external). There is no generic IPC. Every handler first calls `validateSender(senderUrl(event.senderFrame))`, which throws `Untrusted IPC sender` unless the frame URL passes `isTrustedRendererUrl`. Two handlers add argument checks:

- `showItemInFolder` requires an absolute string path under 4096 characters before calling `shell.showItemInFolder`.
- `openExternal` requires the URL to pass `isApprovedExternalUrl` before calling `shell.openExternal`.

The preload exposes exactly these as `window.evidrunDesktop` through `contextBridge`.

## Permission lockdown

`lockDownPermissions` in `apps/desktop/src/main/permissions.ts` denies everything on the default session: the permission check handler returns `false`, the permission request handler calls back `false`, and the device permission handler returns `false`. No camera, microphone, geolocation, or device access is granted.

## Navigation and window-open guards

In `index.ts`, the main window's `will-navigate` is prevented unless the target passes `isTrustedRendererUrl`, and `setWindowOpenHandler` denies all new windows, opening the URL in the system browser only if it passes the external-link allowlist. This blocks a compromised page from navigating away or spawning a window that escapes the sandbox.

## The external-link and renderer allowlists

`apps/desktop/src/main/external-links.ts` defines two functions:

- `isApprovedExternalUrl` accepts only `https:` URLs whose hostname is in a fixed `APPROVED_HOSTS` set (electronjs.org and www, openai.com / platform.openai.com / developers.openai.com, python.org and www). Anything else is rejected.
- `isTrustedRendererUrl` accepts `evidrun://app` and, in dev, the origin of `EVIDRUN_DEV_SERVER_URL`. This is the single definition of "trusted renderer" used by both IPC sender validation and the navigation guard.

## The evidrun:// privileged protocol and path-traversal guard

Before app-ready, `index.ts` registers `evidrun` as a privileged scheme (`standard`, `secure`, `supportFetchAPI`, `corsEnabled`). At startup, `registerAppProtocol` handles `evidrun://` by mapping the URL path to a file under `apps/web/dist` (defaulting `/` to `/index.html`), resolving the target, and returning 404 unless the resolved path stays within the `dist` root:

```ts
const target = path.resolve(webRoot, `.${requested}`);
if (!target.startsWith(`${webRoot}${path.sep}`) && target !== webRoot) {
  return new Response("Not found", { status: 404 });
}
return net.fetch(pathToFileURL(target).toString());
```

That prefix check is the path-traversal guard: a request like `evidrun://app/../../etc/passwd` resolves outside `dist` and is rejected. Production loads `evidrun://app/`; dev loads `EVIDRUN_DEV_SERVER_URL`.

## Backend spawn and the launch-token handshake

`BackendLifecycle` in `apps/desktop/src/main/backend-lifecycle.ts` spawns the Python backend and hands it a secret over stdin, never over argv, files, or logs:

1. Generate a 32-byte base64url launch token and a UUID instance id.
2. Spawn `evidrun serve --desktop-handshake` (dev: via `uv`; packaged: the bundled backend from `process.resourcesPath`), with `stdio` piped and `env` trimmed to `PATH` and `LANG`.
3. Write one JSON line to stdin: `{ token, data_dir, parent_instance_id }`.
4. Read the first stdout line and validate it with `parseReadiness` (`apps/desktop/src/main/desktop-handshake.ts`), which requires `protocol: "evidrun-desktop-v1"`, `schema_version: "1"`, a valid port, and the instance/pid/nonce fields.
5. Build `BackendConnection` as `{ baseUrl: http://127.0.0.1:<port>, token, instanceId }`, hand it to the renderer through IPC, and require the same token as a bearer on every HTTP request.

On the backend, `evidrun serve --desktop-handshake` (in `src/evidrun/entrypoints/cli/app.py`) reads that stdin line, binds an ephemeral loopback port, prints the readiness JSON, and creates the app with `launch_token` set. The app's `authorize` dependency then rejects any request without `Authorization: Bearer <token>`. `scripts/smoke_desktop_handshake.mjs` verifies the whole flow (401 without token, 200 with it).

A 15-second timeout kills the child if no valid readiness line arrives; `stop()` sends `SIGTERM` then `SIGKILL` after 4 seconds. The token exists only in memory in Main and in the backend process; it is never written to disk. The plain `evidrun serve` path (no handshake) sets no token and accepts any local loopback client, which the threat model flags as a known limitation.
