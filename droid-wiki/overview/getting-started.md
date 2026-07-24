# Getting started

This page covers prerequisites, install, and the commands to build, test, and run Evidrun locally. The reference benchmark runs fully offline, so you can exercise the whole pipeline without any external API.

## Prerequisites

- **Python 3.14** (the project pins `>=3.14,<3.15` in `pyproject.toml`)
- **uv** for Python dependency and environment management
- **Node.js 24** (`.node-version` pins 24; `package.json` requires `>=24 <25`)
- **pnpm 9.15.0** (declared as the `packageManager`)

The Python package is `evidrun`, built with hatchling and sourced from `src/evidrun`. The workspace is a pnpm monorepo whose packages live under `apps/*`.

## Install

```bash
uv sync --extra dev
pnpm install
```

`uv sync --extra dev` installs the runtime dependencies (alembic, cryptography, fastapi, httpx, keyring, platformdirs, pydantic, pyyaml, rich, sqlalchemy, typer, uvicorn) plus the dev tools (hypothesis, pyright, pytest, pytest-asyncio, ruff).

## First run

```bash
uv run evidrun init          # create the data dir and SQLite database
uv run evidrun doctor        # verify environment, benchmark, and default provider
uv run evidrun demo          # run the offline CRL-CTX-002 benchmark end to end
uv run evidrun provider status
uv run evidrun provider doctor
```

`evidrun init` creates the data directory (default from `platformdirs`, overridable with `EVIDRUN_DATA_DIR` or `--data-dir`) with mode `0o700` and initializes `evidrun.db`. `evidrun demo` bootstraps the `CRL-CTX-002` experiment, compiles it into RunSpecs, admits them, runs the deterministic subject, grades the output, and produces a paired comparison, all offline. See the [CLI reference](../apps/cli/index.md) for the full command tree.

## Backend and browser

```bash
uv run evidrun serve         # FastAPI on 127.0.0.1:8765
pnpm dev:web                 # Vite dev server on 127.0.0.1:5173
```

The API binds to loopback only. The React app talks to it over HTTP using the same client in the browser and in the desktop app.

## Desktop (Electron)

```bash
pnpm desktop:dev
```

`desktop:dev` compiles the Electron Main and preload, starts Vite, and lets Main launch the Python backend through a stdin handshake that hands over a launch token and data directory. Set `EVIDRUN_DATA_DIR` to isolate data during manual testing. See [desktop app](../apps/desktop.md) for the lifecycle and security model.

## Mandatory verification suite

Before delivering any change, run the full suite from `AGENTS.md`. CI enforces the same checks in `.github/workflows/ci.yml`.

```bash
uv run pytest
uv run ruff check .
uv run pyright
pnpm typecheck:web
pnpm typecheck:desktop
pnpm test
pnpm build
uv run python scripts/validate_docs.py
```

`pnpm test` chains `check:contracts` (regenerating schemas and contract types and diffing them) with the web and desktop Vitest suites. The `CRL-CTX-002` benchmark must stay offline and deterministic. See [testing](../how-to-contribute/testing.md) and [tooling](../how-to-contribute/tooling.md) for what each command validates.

## Provider configuration

The default provider is `cliproxyapi-local` with model `deepseek-v4-flash` and `reasoning=max`, pointed at a local CLIProxyAPI at `127.0.0.1:8318/v1`. API keys live in the system Keychain (or an ephemeral environment variable), never in code. Use `evidrun provider set-key` to store a credential and `evidrun provider smoke` to make a minimal live call. The benchmark does not need the provider to be available. See [provider runtime](../systems/providers.md).
