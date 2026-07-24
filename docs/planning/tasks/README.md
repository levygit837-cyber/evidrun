---
id: planning-tasks-index
type: planning
title: Dispatch de workstreams para agentes
status: accepted
authority: planning
owner: product-engineering
created_at: 2026-07-23
updated_at: 2026-07-24
observed_at: 2026-07-24
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

| Estado | Brief | Proxima acao |
| --- | --- | --- |
| `done_on_main` | [WS-00 Runtime Kernel](00-runtime-kernel-integration.md) | Preservar os limites integrados pela PR #4 |
| `queued` | [WS-10 Operator Console](10-mvp-operator-console.md) | Implementar em `apps/web` a partir de `origin/main`; usar os prototipos apenas como research visual |
| `queued` | [WS-20 Artifact access/capture](20-artifact-access-and-capture.md) | Pode iniciar em paralelo com WS-40, com ownership separado |
| `queued` | [WS-40 Trust sandbox/ReviewPackage](40-trust-sandbox-review-package.md) | Pode iniciar em paralelo com WS-20, sem criar falsa authority |

WS-10 parte do Kernel ja integrado. Os cinco prototipos em
`design/operator-console-prototypes` sao executaveis e testados como exploracao, mas nao devem ser
copiados como se fossem a arquitetura final, nem apresentados como backend real.

## Regras de worktree

- cada agente possui uma branch e uma worktree;
- nenhum agente edita a worktree do outro;
- arquivo gerado e regenerado depois do rebase, nunca copiado entre worktrees;
- migrations sao numeradas conforme a ordem real de merge;
- shared files (`docs/index.md`, package lock, generated contracts) ficam para o commit de integracao;
- se duas branches precisarem alterar o mesmo contrato normativo, interrompa o paralelo e resolva a
  decisao antes de continuar;
- merge de WS-00 precede a integracao real de WS-10.

## Sequencia restante

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
