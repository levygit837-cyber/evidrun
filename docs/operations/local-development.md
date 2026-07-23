---
id: operations-local-development
type: operations
title: Desenvolvimento local
status: implemented
authority: normative
owner: core
created_at: 2026-07-22
updated_at: 2026-07-23
applies_to: repository
sources: []
supersedes: []
superseded_by: null
implementation_refs:
  - pyproject.toml
  - package.json
verification_refs:
  - .github/workflows/ci.yml
---

# Desenvolvimento local

```bash
uv sync --extra dev
pnpm install
uv run evidrun init
uv run evidrun demo
uv run evidrun serve
uv run evidrun-worker --data-dir ./.local-evidrun --once
pnpm dev:web
```

Electron usa `pnpm desktop:dev`, que compila Main/preload, inicia Vite e deixa o Main iniciar o
backend Python por handshake. `EVIDRUN_DATA_DIR` isola dados de testes manuais.

Antes de entregar, execute os comandos de verificação do `AGENTS.md`.
