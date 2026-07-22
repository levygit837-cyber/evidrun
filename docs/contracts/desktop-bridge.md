---
id: contract-desktop-bridge-v1
type: contract
title: Desktop Bridge v1
status: implemented
authority: normative
owner: desktop
created_at: 2026-07-22
updated_at: 2026-07-22
applies_to: electron/preload@1
sources: []
supersedes: []
superseded_by: null
implementation_refs:
  - apps/desktop/src/shared/desktop-contract.ts
verification_refs:
  - apps/desktop/src/main/external-links.test.ts
---

# Desktop Bridge v1

O preload expõe apenas informações do app, conexão do backend, restart, seleção de arquivo/diretório,
reveal-in-folder, abertura de HTTPS aprovada e evento de estado do backend.

Não existe `execute`, shell, filesystem genérico ou exposição direta de `ipcRenderer`. Inputs e
sender são validados no Main. Regras do domínio permanecem na API Python.

