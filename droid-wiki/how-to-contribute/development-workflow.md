# Development workflow

This page describes the local branch-to-merge cycle and how CI mirrors it. The commands come from `README.md`, `docs/operations/local-development.md`, and `package.json`; CI is `.github/workflows/ci.yml`.

## Prerequisites

- Python 3.14 with `uv`
- Node.js 24 and pnpm 9.15.0

Both are pinned: `pyproject.toml` requires `>=3.14,<3.15`, `package.json` declares `packageManager` as `pnpm@9.15.0` and `engines.node` as `>=24 <25`. See [getting started](../overview/getting-started.md) for the first-run walkthrough.

## Set up

```bash
uv sync --extra dev   # runtime deps + dev tools (pytest, pyright, ruff, hypothesis)
pnpm install          # workspace deps for apps/web and apps/desktop
uv run evidrun init   # create the data dir (mode 0o700) and evidrun.db
```

## The cycle

1. **Branch.** Work on a feature branch off `main`. Never push directly to `main`.
2. **Code.** Follow the layering and contract rules in [patterns and conventions](patterns-and-conventions.md). If you touched a contract model, regenerate the schemas and TypeScript types before committing: `pnpm generate:contracts`.
3. **Verify locally.** Run the full suite below. It is the definition of done and it is exactly what CI runs.
4. **Docs.** If you added or changed a doc under `docs/`, run `uv run python scripts/validate_docs.py` so the frontmatter is valid and `docs/_generated/manifest.json` is regenerated. Commit the regenerated manifest.
5. **PR.** Open a pull request against `main`. CI runs on push and pull_request. Keep the title concise; put the details, what you tested, and any blocked capability in the description.
6. **Merge.** Merge once both CI jobs are green.

## The local verification suite

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

`pnpm test` chains `check:contracts` (regenerate schemas and contract types, diff against committed output) with `test:web` and `test:desktop`. `pnpm build` builds the web bundle and compiles the Electron main and preload. See [testing](testing.md) for what each suite validates and [tooling](tooling.md) for what each script does.

## How CI mirrors the local suite

`.github/workflows/ci.yml` runs on every push and pull request, split into two jobs.

| Job | Runs |
| --- | --- |
| `python` | `uv sync --extra dev`, `uv run ruff check .`, `uv run pyright`, `uv run pytest`, `uv run python scripts/validate_docs.py`, `uv run python scripts/generate_schemas.py --check`, then `git diff --exit-code -- docs/_generated` |
| `node` | `pnpm install --frozen-lockfile`, `node scripts/generate_contract_types.mjs --check`, `pnpm typecheck:web`, `pnpm typecheck:desktop`, `pnpm test:web`, `pnpm test:desktop`, `pnpm build` |

Two things to notice. First, CI splits contract generation across the two jobs: the `python` job checks the JSON Schemas with `generate_schemas.py --check`, and the `node` job checks the TypeScript with `generate_contract_types.mjs --check`. Locally, `pnpm check:contracts` runs both. Second, the `python` job runs the docs validator and then diffs `docs/_generated`, so a stale manifest fails the build even though the validator itself passed. Regenerate and commit the manifest whenever you change docs.

## Running the app locally

```bash
uv run evidrun serve   # FastAPI on 127.0.0.1:8765 (loopback only)
pnpm dev:web           # Vite dev server on 127.0.0.1:5173
pnpm desktop:dev       # build main/preload, start Vite, launch Electron
```

`evidrun serve` without `--desktop-handshake` binds loopback and accepts any local process (no token). The desktop path spawns the backend with a launch-token handshake. Set `EVIDRUN_DATA_DIR` to isolate data during manual testing. See [reference: configuration](../reference/configuration.md) for every environment variable, [apps: API](../apps/api.md) for the endpoints, and [apps: desktop](../apps/desktop.md) for the shell.
