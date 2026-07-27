Electron Forge copies this directory verbatim into the packaged app, so both sidecar
executables must exist here before packaging.

  evidrun-backend   Control Plane; the app spawns `evidrun-backend serve --desktop-handshake`
  evidrun-worker    Execution Plane; the durable Run executor

On Windows both carry the `.exe` suffix. Build them for the host platform and
architecture with:

  uv run --extra package python scripts/build_desktop_binaries.py

The executables are generated artifacts and are not tracked by git. Signing and
notarization stay gated behind EVIDRUN_CODESIGN / EVIDRUN_NOTARIZE; a packaged
release for macOS must sign both nested binaries.
