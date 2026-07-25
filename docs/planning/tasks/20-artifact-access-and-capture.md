---
id: planning-task-artifact-access-capture
type: implementation-task
title: WS-20 Artifact access, materializacao e capture
status: proposed
authority: planning
owner: evidence
created_at: 2026-07-23
updated_at: 2026-07-23
observed_at: 2026-07-23
review_due: 2026-08-06
applies_to: artifact-runtime
sources:
  - docs/adr/0011-progress-artifacts-and-bundle-boundaries.md
  - docs/architecture/data-and-evidence.md
  - docs/contracts/capture-and-retention.md
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
---

# WS-20 — Artifact access e capture

`workstream_state: queued`

## Resultado pratico

Transformar `ArtifactRef` de identidade passiva em uma cadeia auditavel de autorizacao e uso, sem
reintroduzir locator. Uma Run deve conseguir materializar um input permitido, provar quem recebeu o
conteudo e aplicar capture/classification a snapshot, tool arguments/results e Subject output.

Esta task comeca somente depois das costuras do dominio (WS-11/12) estarem em `main`. O Runtime
Kernel de que ela depende ja esta integrado.

## Escopo

- `ArtifactAccessGrant` imutavel e ligado a project, audience, purpose, actions, Run/spec e digest;
- `ArtifactMaterializationRecord` para cada conteudo realmente entregue/montado;
- `ArtifactReadRecord` ou evento equivalente somente quando necessario para provar acesso, sem virar
  telemetria de todo arquivo;
- project/run scoping no ArtifactStore;
- TTL, revogacao e tombstone sem apagar ledger historico;
- capture modes aplicados no pipeline real;
- raw sensivel somente cifrado e referenciado;
- bundle manifest distinguindo identidade, autorizacao, materializacao e inclusao;
- API/CLI minima para importar, listar metadata, conceder/revogar e inspecionar materializacao.

## Nao objetivos

- suporte a `restricted`;
- export portatil de blobs;
- filesystem irrestrito;
- inventario de todos os arquivos lidos/editados;
- restore de workspace;
- Canvas.

## Invariantes

- `ArtifactRef` continua sem path, URL ou locator.
- Ref nao concede acesso.
- Grant para outra Run/project/audience falha fechado.
- Permissao efetiva nunca excede a solicitada no RunSpec/Admission.
- Materializacao verifica digest antes da entrega.
- `sensitive` nunca aparece inline em event, log, API ou bundle.
- `restricted` continua rejeitado ate existir ADR/adapter proprio.
- Progress Artifact e manifest continuam intencionais; nao viram file-access log.
- Purge remove bytes quando permitido, mas preserva tombstone e fatos auditaveis.

## Harness

```text
TASK_ID=WS-20
BASE_REQUIRES=WS-11:done_on_main,WS-12:done_on_main
MAX_REPAIR_LOOPS=10
FULL_GATE_INTERVAL=3
ALLOW_RESTRICTED=0
ALLOW_LOCATOR=0
ALLOW_PORTABLE_BUNDLE=0
```

Loop:

```text
AUDIT all artifact consumers
-> MODEL grant/materialization boundaries
-> ADR successor only if semantics changed
-> IMPLEMENT domain records
-> IMPLEMENT repository/store enforcement
-> INTEGRATE one Subject input vertically
-> ATTACK cross-run/project/classification
-> REPAIR
-> INTEGRATE capture/bundle
-> FULL GATES
```

### Condicionais

- Se um consumer precisar de locator, redesenhe a materializacao; nao relaxe `ArtifactRef`.
- Se um grant depender de autoridade humana, use attestation existente; nao aceite booleano
  `approved=true`.
- Se bytes sensiveis aparecerem em um assertion de teste, trate como P0 e faça busca no workspace.
- Se a mesma regra estiver duplicada em API/worker/bundle, extraia um service do dominio antes de
  continuar.
- Se WS-40 estiver em paralelo, combine somente o contrato de trust/grant; repositories e migrations
  permanecem separados ate o rebase.

## Subagentes

- threat reviewer read-only para confused deputy, cross-project e leakage;
- data lifecycle reviewer read-only para TTL/purge/tombstone/backup;
- bundle reviewer read-only para manifest e claims de completude.

## Testes obrigatorios

- grant expirado, revogado, audience incorreta e Run incorreta;
- project A tentando ler bytes de project B;
- digest/media type/classification divergentes;
- materializacao duplicada idempotente;
- path traversal impossivel estruturalmente;
- sensitive cifrado, wrong key e Keychain indisponivel;
- capture `metadata`, `redacted`, `raw_encrypted` e `disabled` ponta a ponta;
- purge + tombstone + bundle references-only;
- logs/exceptions sem conteudo;
- restart/worker retry sem duplicar materialization records;
- Bundle tampered com grant/ref/materialization divergente.

Executar tambem todos os gates do `AGENTS.md`.

## Criterio de saida

Uma Run com input `internal` e uma Run com output `sensitive` opt-in atravessam worker, evaluation e
bundle sem locator, sem acesso cruzado e sem bytes sensiveis no ledger. `restricted` permanece
explicitamente rejeitado.
