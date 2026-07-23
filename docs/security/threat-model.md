---
id: security-threat-model-v1
type: security
title: Threat model inicial
status: accepted
authority: normative
owner: security
created_at: 2026-07-22
updated_at: 2026-07-23
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

Controles existentes são documentados nos contratos de captura, event e desktop bridge, mas não
fecham todas as ameaças acima. Em particular:

- o launch token protege o sidecar iniciado pelo desktop; `evidrun serve` sem handshake aceita
  qualquer processo local em loopback;
- `actor_type=human` é validado no contract, mas a API ainda não autentica uma role humana separada;
- capture policy e rejeição de restricted estão completas no `ArtifactStore`, não em snapshots e
  eventos da Run;
- campos textuais livres ainda não passam por secret scanning.

Sandbox de código, sync, autoridade do futuro Lab Agent e expansão do pipeline para conteúdo
sensível exigirão revisões próprias deste threat model.
