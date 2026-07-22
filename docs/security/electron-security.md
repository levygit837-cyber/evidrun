---
id: security-electron
type: security
title: Baseline de segurança Electron
status: implemented
authority: normative
owner: desktop
created_at: 2026-07-22
updated_at: 2026-07-22
applies_to: apps/desktop
sources:
  - https://www.electronjs.org/docs/latest/tutorial/security
supersedes: []
superseded_by: null
implementation_refs:
  - apps/desktop/src/main/windows.ts
  - apps/desktop/src/main/index.ts
verification_refs:
  - apps/desktop/src/main/external-links.test.ts
---

# Segurança Electron

Renderer usa `nodeIntegration: false`, `contextIsolation: true`, `sandbox: true` e `webSecurity:
true`. Não carrega conteúdo remoto, não usa `webview` e não expõe IPC genérico.

Produção usa protocolo `evidrun://`; navegação e criação de janelas são bloqueadas. URLs externas
exigem HTTPS e allowlist. Permissões de dispositivo são negadas. A CSP não permite remote scripts ou
`unsafe-eval`.

O backend escuta em loopback e exige token efêmero enviado por stdin. Tokens não entram em args,
arquivos ou logs.

