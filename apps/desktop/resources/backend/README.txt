Electron Forge copies this directory verbatim into the packaged app, so both sidecars
must exist here before packaging:

  evidrun-backend/  Control Plane; the app spawns `evidrun-backend serve --desktop-handshake`
  evidrun-worker/   Execution Plane; the durable Run executor

Each is a PyInstaller `--onedir` build: a directory holding the executable (with the
`.exe` suffix on Windows) next to its shared libraries. A onefile build would re-extract
the archive on every launch and miss the readiness timeout.

Build them for the host platform and architecture with:

  pnpm build:sidecars

PyInstaller does not cross-compile, so build on the platform and architecture you ship.

These directories are generated artifacts and are not tracked by git. Signing and
notarization stay gated behind EVIDRUN_CODESIGN / EVIDRUN_NOTARIZE; a macOS release must
sign both nested binaries. Until they are signed, the first launch of a freshly built
binary pays a one-time Gatekeeper evaluation of roughly a minute.
