---
id: planning-task-execution-trust-review-package
type: implementation-task
title: WS-40 Trust de execucao nao verificada e ReviewPackage
status: verified
authority: planning
volatility: snapshot
owner: governance
created_at: 2026-07-23
updated_at: 2026-07-31
observed_at: 2026-07-31
review_due: 2026-08-06
applies_to: control-plane-trust
sources:
  - docs/adr/0010-verifiable-human-authority.md
  - docs/adr/0015-human-subject-envelope-and-authenticator-lifecycle.md
  - docs/adr/0020-workspace-project-run-environment-boundaries.md
  - docs/adr/0022-explicit-execution-trust-without-per-run-authentication.md
  - docs/contracts/agent-inventory-workspace-v1.md
  - docs/contracts/execution-trust-v1.md
  - docs/planning/mvp-capability-map.md
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun/contracts/execution_trust.py
  - src/evidrun/contracts/review_package.py
  - src/evidrun/infrastructure/database/trust.py
  - src/evidrun/runs/preparation.py
  - src/evidrun/contracts/admission/checks/execution_trust.py
  - src/evidrun/infrastructure/database/catalog.py
  - src/evidrun/infrastructure/database/queue/enqueue.py
  - src/evidrun/evidence/export/run_v4.py
  - src/evidrun/evidence/verify/v4.py
  - src/evidrun/runs/review.py
  - src/evidrun/entrypoints/review_html.py
  - apps/web/src/features/observability/executionTrust.ts
verification_refs:
  - tests/unit/test_execution_trust.py
  - tests/integration/test_execution_trust_migration.py
  - tests/unit/test_unverified_admission.py
  - tests/acceptance/test_unverified_execution.py
  - tests/integration/test_execution_preparation_surfaces.py
  - tests/live/test_real_agent_benchmark.py
  - tests/acceptance/test_verified_execution_review.py
---

# WS-40 — Trust de execucao nao verificada e ReviewPackage

`workstream_state: delivered`

## Estado da entrega

- fundação de contratos, closure, digests, persistência, migration e estado legado: entregue;
- corredor draft -> preparação -> trust não verificado -> admissão -> fila -> Run: implementado e
  exercitado offline;
- Bundle v4 para ambos os kinds e verificação isolada contra tampering: implementados;
- smoke com provider real: disponível somente por opt-in;
- `ReviewPackage`, diff fechado, criação fail-closed do kind verificado, promoção por nova Run e
  projeções humanas: implementados e verificados offline;
- a integração da tela Create permanece no WS-51 e não faz parte deste workstream.

## Problema

Authority e opt-in, mas o compiler ainda resolve somente revisions aceitas. Na pratica, um usuario
nao consegue executar rapidamente um Study draft sem produzir uma aceitacao humana. Isso impede uma
execucao local explicitamente nao verificada, embora preserve corretamente a seguranca.

Esta task cria um caminho explicitamente nao verificado; ela nao torna a autenticacao humana
opcional para claims humanos e nao implementa, por si so, sandbox de OS/container.

## Pre-condicao normativa resolvida

O [ADR 0022](../../adr/0022-explicit-execution-trust-without-per-run-authentication.md) e o
[contrato Execution Trust v1](../../contracts/execution-trust-v1.md) fecharam identidade, digest,
restricoes, promocao e vocabulario. O codigo deve implementar exatamente:

```text
ExecutionTrustRecord.kind = unverified_revision_set | verified_revision_set
```

`unverified_revision_set` referencia a closure transitiva versionada, ordenada e ligada ao Project,
com os documentos e digests exatos usados para compilar, mas nao altera seu status para accepted. A
Run e o bundle carregam trust explicitamente. Promocao nunca reescreve a Run passada: cria decisions
humanas, novo trust record, nova admissao e nova Run.

## ReviewPackage

Um `ReviewPackage` lista explicitamente:

- Study e todas as refs transitivas;
- digests;
- diff desde o pacote anterior;
- Subject disclosure;
- capabilities/permissoes;
- classifications;
- network/external effects;
- EvaluationPlan e hidden inputs sem expor seu conteudo ao Subject;
- riscos e limitacoes.

O package apresenta o `ReviewTarget` canonico e seu `review_target_digest`. Ref nova, digest novo ou
RunSpec diferente muda o target; nao existe aprovacao aberta para referencias futuras. WS-40 gera e
verifica o target, mas nao implementa cerimonia de confirmacao.

## Restricoes da execucao nao verificada

- execucao no produto local, sem afirmar isolamento maior que o runtime comprova;
- `public`/`internal`; nunca `sensitive` ou `restricted` neste marco;
- external effects `denied`;
- network no maximo `provider_only` para adapter explicitamente admitido;
- nenhuma human review/adjudication;
- nenhum claim `human_verified`;
- bundle e UI marcados `unverified_revision_set`, nunca apenas `sandbox`;
- nenhuma promocao automatica;
- nenhuma alteracao da Run original;
- capabilities somente do catalogo seguro do Runtime Kernel.

## Run Environment

Trust, isolamento e configuracao sao eixos distintos. O package nao cria Workspace/Project e nao
recebe o Workspace do Control Plane como mount. Depois de RunSpec e admissao, o Run Environment
efetivo e a intersecao entre policy ceiling futura, `WorkspaceTemplateRevision` solicitado e
capabilities reais do runtime.

Enquanto o runtime ativo for `in_process`, a UI diz `in_process` e nao afirma sandbox forte. Um
adapter futuro so pode anunciar isolamento quando aplicar e provar o preset efemero, mounts
read-only, zero write zones/secrets, network `denied` ou `provider_only`, efeitos negados, snapshot
desabilitado e cleanup `discard`. Opcao nao suportada rejeita admissao; nao vira toggle otimista.

## Harness

```text
TASK_ID=WS-40
MAX_REPAIR_LOOPS=10
FULL_GATE_INTERVAL=3
ADR_REQUIRED_BEFORE_CODE=docs/adr/0022-explicit-execution-trust-without-per-run-authentication.md
ALLOW_FAKE_HUMAN=0
ALLOW_UNVERIFIED_PROMOTION_IN_PLACE=0
ALLOW_EXTERNAL_EFFECTS=0
```

Loop:

```text
REDISCOVER current contracts and migrations
-> IMPLEMENT the accepted ADR and contract
-> IMPLEMENT trust/package contracts
-> IMPLEMENT compiler/admission path
-> IMPLEMENT API/CLI
-> ATTACK claim confusion and digest drift
-> REPAIR
-> VERIFY verified kind only from existing accepted human decisions
-> FULL GATES
```

### Condicionais

- Se o codigo exigir mudar a fonte de verdade fechada pelo ADR 0022, pare e proponha ADR sucessor.
- Se qualquer resposta/API tratar nao verificado como accepted/verified, P0.
- Se `in_process` for apresentado como sandbox seguro, P0 de claim; corrija a linguagem e mantenha a
  capability rejeitada.
- Se um agent endpoint puder criar o kind verificado, P0.
- Se a promocao puder alterar a Run original, rejeite o design.
- Se um diff de package omitir capability, hidden input ou disclosure, nao publique o package.
- Se platform passkey/recovery surgir como requisito, abra follow-up; o autenticador local opt-in
  continua suficiente para o MVP local.

## Subagentes

- security reviewer read-only para confused authority e replay;
- product reviewer read-only para reduzir friccao cotidiana;
- contract reviewer read-only para digest/package/transitive refs.

## Testes obrigatorios

- draft nao verificado compila sem Decision humana e preserva todos os digests;
- bundle/UI nunca afirmam human verified;
- sensitive/restricted/external effect rejeitados;
- package muda quando qualquer ref, permission, input ou disclosure muda;
- package muda quando o mesmo conjunto de refs e ligado a outro Project ou RunSpec;
- closure e digest independem da ordem de insercao e nao resolvem `latest`;
- package nao aceita ref futura;
- `ReviewTarget` cobre revision set e todos os RunSpecs em ordem canonica;
- agente nao cria kind verificado;
- decisions humanas aceitas preexistentes permitem novo trust record, nova admissao e nova Run;
- API/CLI equivalentes;
- migrations empty/legacy/current.

## Criterio de saida

Um usuario executa um Study draft como nao verificado sem autenticacao e recebe claims honestos.
Quando ja existirem decisions humanas verificadas sobre o conjunto exato, o sistema pode criar o
kind verificado e qualquer execucao nasce como nova Run. Trust aparece como texto no bundle e nas
projecoes de UI, separado do isolamento efetivo. Cerimonia local sobre o `ReviewPackage`, enrollment,
recovery, rotacao e revogacao pertencem a um workstream futuro da opcao A.
