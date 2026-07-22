---
id: architecture-desktop-runtime
type: architecture
title: Runtime Electron e sidecar Python
status: implemented
authority: normative
owner: desktop
created_at: 2026-07-22
updated_at: 2026-07-22
applies_to: apps/desktop
sources:
  - https://www.electronjs.org/docs/latest/tutorial/process-model
supersedes: []
superseded_by: null
implementation_refs:
  - apps/desktop/src/main
  - apps/desktop/src/preload
verification_refs:
  - apps/desktop/src/main/backend-lifecycle.test.ts
---

# Runtime desktop

O processo principal inicia o backend por `child_process.spawn`, envia um token efêmero por stdin e
recebe uma readiness message por stdout. O backend escolhe uma porta loopback efêmera e exige Bearer
token em toda chamada. Token, porta e instance ID ficam apenas em memória.

O renderer não possui Node. O preload expõe métodos individuais por `contextBridge`. Domínio usa
REST/SSE, não IPC duplicado. Produção usa o protocolo seguro `evidrun://app`.

Crash do backend é um estado observável. O aplicativo pode reiniciá-lo sem reescrever evidência.
Release exige que o executável PyInstaller seja incluído e assinado junto do Electron.

