---
id: operations-local-development
type: operations
title: Desenvolvimento local
status: implemented
authority: normative
owner: core
created_at: 2026-07-22
updated_at: 2026-07-24
applies_to: repository
sources: []
supersedes: []
superseded_by: null
implementation_refs:
  - pyproject.toml
  - package.json
  - code-budget.toml
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

## Orçamento estrutural

```bash
uv run python scripts/check_code_budget.py          # verifica; exit 1 em violação
uv run python scripts/check_code_budget.py --json    # saída de máquina
uv run python scripts/install_git_hooks.py           # instala pre-push local (opcional)
```

A política vive em `code-budget.toml` e o ADR 0017 explica os limites. O CI roda o mesmo comando no
job Python. Arquivos no ratchet `[baseline]` podem encolher, nunca crescer; quando uma métrica volta
para dentro do orçamento, remova a entrada. `--update-baseline` é operação humana deliberada e nunca
roda em CI.
