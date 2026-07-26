---
id: security-threat-model-v1
type: security
title: Threat model inicial
status: accepted
authority: normative
volatility: timeless
owner: security
created_at: 2026-07-22
updated_at: 2026-07-23
applies_to: system
sources: []
supersedes: []
superseded_by: null
implementation_refs:
  - apps/desktop/src/main
  - src/evidrun/contracts/authority.py
  - src/evidrun/infrastructure/artifacts
  - src/evidrun/infrastructure/database/repository.py
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
- authority humana exige `HumanAttestationRecord` e verifier confiável; como nenhum adapter WebAuthn
  está instalado, API, CLI e repository default falham fechado em vez de aceitar uma role alegada;
- `repository_fixture` é não humano e só é permitido pelo método dedicado que confere o pacote
  canônico completo `CRL-CTX-002`; ampliar esse caminho seria uma quebra da fronteira definida no
  [ADR 0010](../adr/0010-verifiable-human-authority.md);
- o runtime rejeita inputs sensitive/restricted e valida shape/modo da resposta do Subject; Context
  Snapshots, demais eventos e strings livres ainda não possuem enforcement de conteúdo equivalente;
- `ArtifactRef` ainda não possui grant/materialization enforcement, e bundle auditável não implica
  blobs portáteis ou replay, conforme o
  [ADR 0011](../adr/0011-progress-artifacts-and-bundle-boundaries.md);
- campos textuais livres ainda não passam por secret scanning.

Sandbox de código, sync, autoridade do futuro Lab Agent e expansão do pipeline para conteúdo
sensível exigirão revisões próprias deste threat model.
