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
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RESOURCES = REPO_ROOT / "apps" / "desktop" / "resources" / "backend"
BUILD_ROOT = REPO_ROOT / ".pyinstaller-build"

# Console script entrypoint -> frozen executable name expected by the Electron main
# process. Keep these names in sync with `backend-lifecycle.ts` and `worker-lifecycle.ts`.
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
        "--onefile",
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
    ]
    for hidden in HIDDEN_IMPORTS:
        command += ["--hidden-import", hidden]
    command.append(str(script))
    subprocess.run(command, check=True, cwd=REPO_ROOT)
    built = work / "dist" / executable_name(name)
    if not built.is_file():
        raise SystemExit(f"PyInstaller did not produce {built}")
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
        destination = RESOURCES / executable_name(name)
        shutil.copy2(built, destination)
        destination.chmod(0o755)
        print(f"{destination.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
