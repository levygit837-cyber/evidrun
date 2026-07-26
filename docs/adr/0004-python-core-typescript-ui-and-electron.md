---
id: adr-0004
type: adr
title: Python core, TypeScript UI e Electron
status: accepted
authority: normative
volatility: timeless
owner: desktop
created_at: 2026-07-22
updated_at: 2026-07-22
applies_to: stack
sources:
  - https://www.electronjs.org/docs/latest/tutorial/process-model
supersedes: []
superseded_by: null
implementation_refs:
  - pyproject.toml
  - package.json
  - apps/desktop
verification_refs:
  - apps/desktop/src/main/external-links.test.ts
---

# Decisão

Python concentra domínio, evals e backend. React/TypeScript implementa UI. Electron fornece Chromium,
DevTools, desktop APIs e packaging. O backend roda como sidecar em loopback.

# Alternativas

TypeScript end-to-end reduziria linguagens, mas enfraqueceria a base analítica. Tauri reduziria o
binário, mas não foi escolhido devido à preferência pelo ecossistema Electron/Node.

# Consequências

Aceitamos maior consumo e obrigação de atualizar Electron. Renderer permanece sandboxed e sem Node.

