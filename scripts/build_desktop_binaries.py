"""Freeze the two desktop sidecar executables with PyInstaller.

The desktop app supervises two processes over the same data dir: the Control Plane
(`evidrun-backend serve --desktop-handshake`) and the Execution Plane executor
(`evidrun-worker`). Electron Forge copies `resources/backend` verbatim, so both
have to exist there before packaging, built for the host platform and architecture.

Two executables rather than one because ADR 0002 separates the planes and ADR 0014
makes the executor a distinct durable process: a crash in Run execution must not
take the evidence API down with it.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RESOURCES = REPO_ROOT / "apps" / "desktop" / "resources" / "backend"
BUILD_ROOT = REPO_ROOT / ".pyinstaller-build"

# Console script entrypoint -> frozen executable name the Electron main process looks
# up through `sidecarPath`. Keep these names in sync with `apps/desktop/src/main/sidecar-path.ts`.
TARGETS = {
    "evidrun-backend": "evidrun.entrypoints.cli.app:main",
    "evidrun-worker": "evidrun.entrypoints.worker.app:main",
}

# Typer/FastAPI resolve these lazily, so PyInstaller's static analysis misses them.
HIDDEN_IMPORTS = (
    "evidrun.entrypoints.api.app",
    "evidrun.entrypoints.cli.app",
    "evidrun.entrypoints.worker.app",
    "uvicorn.lifespan.on",
    "uvicorn.loops.auto",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets.auto",
)


def executable_name(name: str) -> str:
    return f"{name}.exe" if sys.platform == "win32" else name


def bundled_data() -> tuple[Path, str]:
    """Read-only material to ship inside the bundle, as (source, bundle-relative name).

    The canonical benchmark package has to stay reachable offline in the installed app.
    `evidrun.shared.resources.benchmarks_root` looks for it under this exact name, so the
    frozen layout matches a checkout and no caller branches on frozen-ness.
    """

    return REPO_ROOT / "benchmarks", "benchmarks"


def write_entrypoint(name: str, target: str, directory: Path) -> Path:
    """Emit a launcher module, because PyInstaller freezes files, not entrypoints."""

    module, function = target.split(":")
    script = directory / f"{name.replace('-', '_')}_main.py"
    script.write_text(
        f"from {module} import {function}\n\nif __name__ == '__main__':\n    {function}()\n",
        encoding="utf-8",
    )
    return script


def freeze(name: str, target: str) -> Path:
    work = BUILD_ROOT / name
    work.mkdir(parents=True, exist_ok=True)
    script = write_entrypoint(name, target, work)
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        # `--onedir`, not `--onefile`: onefile re-extracts the whole archive into a
        # fresh temp dir on every launch, so it pays that cost forever. onedir extracts
        # once at build time and reaches readiness in ~2.6s, well inside the 15s
        # handshake timeout in `backend-lifecycle.ts`.
        #
        # Note the FIRST launch of any newly written ad-hoc-signed binary still takes
        # ~46s while macOS `syspolicyd` evaluates it, once per inode. That is Gatekeeper,
        # not PyInstaller, and proper signing is what removes it — see EVIDRUN_CODESIGN
        # in forge.config.cjs.
        "--onedir",
        "--noconfirm",
        "--clean",
        "--name",
        name,
        "--distpath",
        str(work / "dist"),
        "--workpath",
        str(work / "build"),
        "--specpath",
        str(work),
        "--paths",
        str(REPO_ROOT / "src"),
        "--add-data",
        os.pathsep.join(str(part) for part in bundled_data()),
    ]
    for hidden in HIDDEN_IMPORTS:
        command += ["--hidden-import", hidden]
    command.append(str(script))
    subprocess.run(command, check=True, cwd=REPO_ROOT)
    built = work / "dist" / name
    if not (built / executable_name(name)).is_file():
        raise SystemExit(f"PyInstaller did not produce {built / executable_name(name)}")
    return built


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--only",
        choices=sorted(TARGETS),
        help="freeze a single executable instead of both",
    )
    args = parser.parse_args()
    names = [args.only] if args.only else sorted(TARGETS)

    RESOURCES.mkdir(parents=True, exist_ok=True)
    for name in names:
        built = freeze(name, TARGETS[name])
        destination = RESOURCES / name
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(built, destination)
        (destination / executable_name(name)).chmod(0o755)
        print(f"{(destination / executable_name(name)).relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
