---
id: planning-tasks-index
type: planning
title: Dispatch de workstreams para agentes
status: accepted
authority: planning
owner: product-engineering
created_at: 2026-07-23
updated_at: 2026-07-23
observed_at: 2026-07-23
review_due: 2026-07-30
applies_to: agent-workstreams
sources:
  - docs/planning/README.md
  - docs/planning/mvp-implementation-roadmap.md
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
---

# Dispatch de workstreams

## Agora

| Agente | Worktree | Brief | Relacao |
| --- | --- | --- | --- |
| Codex | worktree existente `task/implementar-runtime-kernel-genrico` | [WS-00](00-runtime-kernel-integration.md) | Integrar primeiro |
| Droid | nova worktree a partir de `origin/main` | [WS-10](10-mvp-operator-console.md) | Pode rodar em paralelo |

WS-10 nao deve consumir arquivos nao commitados de WS-00. Ele usa ports e fixtures. Depois de WS-00
ser mesclado, WS-10 rebaseia e substitui cada fixture de integracao pelo endpoint real correspondente.

## Prompt de dispatch — Codex

```text
Continue exclusivamente na worktree atual do Runtime Kernel. Leia AGENTS.md, docs/index.md,
docs/planning/mvp-capability-map.md e
docs/planning/tasks/00-runtime-kernel-integration.md por completo. O objetivo agora e encerrar o
escopo, revisar, testar e integrar o trabalho com a authority ja presente em main. Nao expanda para
Artifact Grants, Progress Observer, bounded exploration, generic skills, graph ou Canvas. Use
subagentes read-only para code review, semantic Judge e integration review conforme o brief. Nao
faça rebase enquanto houver outro turno editando a worktree; congele primeiro. So declare conclusao
depois de migrations lineares, suite completa, Run live segura, PR/CI e merge.
```

## Prompt de dispatch — Droid

```text
Crie uma worktree propria a partir do origin/main mais recente e use a branch
task/mvp-operator-console. Leia AGENTS.md, docs/index.md,
docs/planning/mvp-implementation-roadmap.md e
docs/planning/tasks/10-mvp-operator-console.md por completo. Trabalhe apenas no frontend e em seus
testes. Nao altere Python, migrations, schemas gerados ou contracts.ts enquanto o Runtime Kernel nao
estiver mesclado. Construa um EvidrunApiPort e fixtures explicitamente restritas aos testes; producao
nunca pode parecer conectada a um backend fake. Execute o harness por loops, use subagentes read-only
de UX, API contract e accessibility, e entregue screenshots, testes e Backend Contract Gaps. Se o
Kernel entrar em main durante a tarefa, rebaseie com worktree limpa e integre em commit separado.
```

## Regras de worktree

- cada agente possui uma branch e uma worktree;
- nenhum agente edita a worktree do outro;
- arquivo gerado e regenerado depois do rebase, nunca copiado entre worktrees;
- migrations sao numeradas conforme a ordem real de merge;
- shared files (`docs/index.md`, package lock, generated contracts) ficam para o commit de integracao;
- se duas branches precisarem alterar o mesmo contrato normativo, interrompa o paralelo e resolva a
  decisao antes de continuar;
- merge de WS-00 precede a integracao real de WS-10.

## Depois do Kernel

| Ordem | Brief | Pode compartilhar onda |
| --- | --- | --- |
| 1 | [WS-20 Artifact access/capture](20-artifact-access-and-capture.md) | WS-40, com migrations separadas |
| 1 | [WS-40 Trust sandbox/ReviewPackage](40-trust-sandbox-review-package.md) | WS-20 |
| 2 | [WS-30 Evaluation/checkpoint/progress](30-evaluation-checkpoint-progress.md) | frontend adapters |
| 3 | [WS-50 Lab Agent/bounded exploration](50-lab-agent-bounded-exploration.md) | integracao final da UI |

## Handoff entre agentes

Todo agente entrega:

- base SHA, head SHA e branch;
- arquivos sob ownership alterados;
- migrations e generated files;
- testes focais e gates completos;
- findings P0/P1 e regressions;
- capabilities promovidas e ainda rejeitadas;
- Backend Contract Gaps ou decisoes humanas abertas;
- proximo brief desbloqueado.

