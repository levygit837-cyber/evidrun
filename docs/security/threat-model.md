---
id: security-threat-model-v1
type: security
title: Threat model inicial
status: accepted
authority: normative
owner: security
created_at: 2026-07-22
updated_at: 2026-07-22
applies_to: system
sources: []
supersedes: []
superseded_by: null
implementation_refs:
  - apps/desktop/src/main
  - src/evidrun/infrastructure/artifacts
verification_refs:
  - tests/security
---

# Threat model inicial

Ativos: raw sensível, prompts, respostas, artifacts, provider keys, event ledger e autoridade humana.

Fronteiras: renderer/Main, Main/sidecar, API/cliente, Lab/Subject Agent, runner/tool environment e
data store/export externo.

Ameaças prioritárias:

- XSS evoluir para capacidade desktop;
- processo local chamar API sem autorização;
- secret aparecer em log, trace ou bundle;
- Subject Agent alcançar hidden grader ou filesystem;
- alteração silenciosa de revision ou evento;
- path traversal em artifact ou protocolo Electron;
- bundle exportado escapar da retenção;
- agent aprovar a própria ação.

Controles atuais são documentados nos contratos de captura, event e desktop bridge. Sandbox de
código e sync exigirão revisões próprias deste threat model.

