---
id: planning-task-runtime-kernel-integration
type: implementation-task
title: WS-00 Integrar Runtime Kernel, Subject real e authority
status: accepted
authority: planning
owner: runtime
created_at: 2026-07-23
updated_at: 2026-07-24
observed_at: 2026-07-24
review_due: 2026-07-25
applies_to: task/implementar-runtime-kernel-genrico
sources:
  - docs/planning/mvp-capability-map.md
  - docs/architecture/system.md
  - docs/adr/0015-human-subject-envelope-and-authenticator-lifecycle.md
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun/runs/coordinator.py
  - src/evidrun/runs/worker.py
  - src/evidrun/runs/adapters.py
verification_refs:
  - tests/integration/test_runtime_kernel.py
  - tests/integration/test_runtime_queue.py
  - tests/integration/test_live_agent_runtime.py
---

# WS-00 — Runtime Kernel integration

`workstream_state: done_on_main`

## Registro de conclusao

- merge: PR #4;
- commit em `main`: `ffc513137d343e015cede7f15f14ed5e749db2b4`;
- ADRs finais: 0014 para Runtime Kernel, 0015 para authority e 0016 para Subject real/read tool;
- migration chain, composition root, contracts gerados e testes de authority foram reconciliados;
- Bundle v3 permanece `references_only`, `portable=false` e `replayable=false`.

O restante deste brief e preservado como registro do plano executado. Nao e um dispatch ativo e nao
autoriza ampliar o Kernel para grants, Progress Artifacts, bounded exploration, graph ou replay.

## Contexto abstrato

O Runtime Kernel transforma uma Run admitida em uma execucao duravel. A source branch ampliou o
escopo original: alem de queue/lease/worker, incluiu Subject com modelo real, read tool fechada,
tracing e Bundle v3. A integracao coerente com a authority foi concluida pela PR #4.

Uma implementacao grande na worktree nao conta como entrega ate sobreviver a rebase, migrations,
tests e CI no mesmo commit que contem authority.

## Snapshot tecnico

```text
WORKTREE_PATH=/Users/apple/.codex/worktrees/4073/evidrun
SOURCE_BRANCH=task/implementar-runtime-kernel-genrico
SOURCE_BASE_SHA=71f5841e0b8123a629bdeaa028ae844a20a628f9
TARGET_BRANCH=main
TARGET_SHA_OBSERVED=101087964cb2361977085e9f62afd75d1dc58f6d
ACTIVE_THREAD_ID=019f8f98-bc6e-7752-ac92-42d9604835f3
```

O agente deve redescobrir esses valores antes de qualquer operacao Git. O worktree tinha alteracoes
nao commitadas; nao execute rebase, checkout ou limpeza enquanto o trabalho ativo nao estiver
congelado e revisado.

## Resultado obrigatorio

- `RunExecutionCoordinator`, queue, jobs, attempts, lease, heartbeat e fencing em `main`;
- worker separado e recovery testado;
- SubjectEnvelope exato persistido e verificavel;
- adapter deterministico preservado;
- adapter real Responses + read tool somente se a Run live e os testes adversariais passarem;
- API/CLI de enqueue, retry, inspect e export por Run;
- Bundle v3 auditavel, `references_only`, nao portatil e nao replayable;
- authority opt-in de `main` preservada;
- nenhum fallback de verifier de teste em producao;
- benchmark `CRL-CTX-002` ainda offline e deterministico.

## Nao objetivos

- generic tool framework alem da read tool explicitamente admitida;
- skills, graph protocol ou nested agents;
- checkpoint/progress coordinator;
- bounded exploration;
- grant generico de artifact;
- portable bundle, replay ou fork;
- Canvas ou frontend novo.

## Conflitos que precisam de resolucao semantica

### ADRs

`main` ja possui `ADR 0015` para authority. Preserve:

- `ADR 0014` para o Runtime Kernel;
- renumere o ADR de Subject real da worktree para `ADR 0016`;
- ajuste filename, `id`, title links, sources, docs index e manifest;
- nao reescreva o ADR de authority.

### Migrations

O historico final deve ser linear:

```text
0001_contract_foundation
-> 0002_runtime_kernel
-> 0003_human_authority
```

Reaponte `0003_human_authority.down_revision` para `0002_runtime_kernel`. Teste upgrade de:

- banco vazio;
- banco somente `0001`;
- banco criado pela `main` atual com tabelas de authority;
- banco com dados do demo;
- reopen depois do upgrade.

Nao edite rows para simular uma migration bem-sucedida.

### Composition root

O processo final precisa montar simultaneamente:

- `RuntimeKernel` e catalogo de adapters;
- `HumanAuthorityService` somente com opt-in;
- `UnavailableHumanAttestationVerifier` como default;
- authority router quando configurado;
- worker sem dependencia obrigatoria de credencial do provider para jobs offline;
- ArtifactStore e Repository compartilhando o mesmo `data_dir`.

### Contratos gerados

Regenerar JSON Schema, OpenAPI, TypeScript e manifest somente depois da reconciliacao da fonte
Python. Nunca resolver conflito escolhendo cegamente um arquivo gerado de uma das branches.

## Harness

```text
TASK_ID=WS-00
MAX_REPAIR_LOOPS=8
FULL_GATE_INTERVAL=3
REQUIRE_LIVE_PROVIDER_RUN=1
ALLOW_PROVIDER_SECRETS_IN_OUTPUT=0
ALLOW_SCHEMA_DRIFT=0
ALLOW_NEW_CAPABILITY_SCOPE=0
```

Estado persistido pelo agente durante a sessao:

```text
phase
base_sha
head_sha
dirty_files
focused_tests_passed
full_gates_passed
live_run_id
live_bundle_path
open_p0_p1
integration_conflicts
```

Nao grave tokens, assertion privada ou provider credential nesse estado.

## Loop de execucao

```text
DISCOVER
-> FREEZE_SCOPE
-> VERIFY_FOCAL
-> REVIEW_READ_ONLY
-> REPAIR
-> FREEZE_WORKTREE
-> REBASE_MAIN
-> RECONCILE
-> VERIFY_MIGRATIONS
-> VERIFY_FULL
-> LIVE_RUN
-> PR_REVIEW
-> MERGE_READY
```

### Condicionais

- Se a worktree ainda estiver sendo editada por outro turno, nao rebaseie; apenas inspecione e
  aguarde o freeze.
- Se o baseline focal falhar antes do rebase, corrija na source branch antes de integrar.
- Se o mesmo erro reaparecer por tres loops, convoque um subagente Judge read-only e revise a
  suposicao, nao apenas o sintoma.
- Se um fix exigir mudar autoridade humana, disclosure, terminal ou artifact access, pare e crie um
  ADR sucessor proposto; nao esconda a mudanca no Kernel.
- Se o provider live estiver indisponivel, mantenha testes fake verdes e marque o live gate como
  bloqueado; nao simule resultado real.
- Se uma Run live vazar hidden expected, credential, locator ou raw reasoning, isso e P0 e impede o
  merge.
- Se migrations gerarem dois heads, resolva a cadeia antes de qualquer PR.
- Se generated files divergirem, corrija a fonte e regenere; nao edite JSON/TypeScript manualmente.
- Se todos os gates passarem, encerre discovery; nao expanda o escopo para a proxima capability.

## Subagentes obrigatorios

O agente principal pode e deve usar subagentes em paralelo:

1. **Code Reviewer read-only:** queue, lease, fencing, idempotencia, crash recovery e DB transactions.
2. **Semantic Judge read-only:** SubjectEnvelope, tool boundary, hidden expected, evaluation e Bundle.
3. **Integration Reviewer read-only:** authority, migrations, API composition e docs.

Subagentes nao fazem merge nem alteram authority. Findings P0/P1 precisam de reproducao/teste antes
do fix; recomendacoes cosmeticas nao ampliam o PR.

## Testes focais

- claim concorrente com duas conexoes SQLite;
- heartbeat e lease generation antigos;
- crash antes e depois de `subject.invoked`;
- retry cria outra Run com `retry_of`;
- idempotency key igual/diferente;
- timeout conserva wall budget atraves de attempts;
- worker subprocess + dispose/reopen;
- SubjectEnvelope digest recomputavel;
- read tool nega input/path fora do envelope;
- evaluation exige evidence realmente retornada pela tool;
- output/arguments/results respeitam capture e classification;
- tampering de job/attempt/envelope/artifact invalida Bundle v3;
- authority challenge/replay/revocation continuam verdes.

## Verificacao final

Executar a suite do `AGENTS.md`, mais:

```bash
uv run alembic upgrade head
uv run python scripts/generate_schemas.py --check
node scripts/generate_contract_types.mjs --check
git diff --check
```

O teste live e separado do CI deterministico. Registre apenas `run:`, `event:` e `artifact:`
autorizados; nunca inclua credential ou corpo upstream livre no handoff.

## Handoff

O relatorio final precisa conter:

- commits e PR;
- base/final SHA;
- migration chain final;
- lista de capabilities realmente admitidas;
- Run IDs deterministica e live;
- bundles verificados;
- findings dos subagentes e seus fixes;
- gates completos com resultados;
- limites ainda rejeitados pela Admission;
- follow-up recomendado sem implementar WS-20/WS-30.
