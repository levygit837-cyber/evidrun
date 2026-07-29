---
id: planning-tasks-index
type: planning
title: Dispatch de workstreams para agentes
status: accepted
authority: planning
volatility: snapshot
owner: product-engineering
created_at: 2026-07-23
updated_at: 2026-07-28
observed_at: 2026-07-28
review_due: 2026-08-23
applies_to: agent-workstreams
sources:
  - docs/planning/README.md
  - docs/planning/mvp-implementation-roadmap.md
  - docs/architecture/codebase-layout.md
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
---

# Dispatch de workstreams

## Agora

A espinha canonica ja atravessa registro, aceitacao verificada, compile, admissao, fila, worker,
terminal e bundle verificado. O corte atual nao adiciona capability: ele torna essa espinha
alcancavel por um usuario e abre as costuras que a largura consome.

O layout-alvo de arquivos e o grafo de conversa entre pastas estao em
[Layout da codebase](../../architecture/codebase-layout.md), com a decisao normativa no
[ADR 0017](../../adr/0017-structural-budget-and-named-seams.md). Nenhum brief redefine o alvo.

O corte atual segue o [Minimo Confortavel](../comfortable-minimum.md): tornar a espinha alcancavel,
depois entregar o corredor Lab Agent -> RunSpec -> contexto do Subject -> batch -> metricas ->
observabilidade.

| Estado | Brief | Proxima acao |
| --- | --- | --- |
| `delivered` | [WS-01 Superficie de Workspace/Project](01-workspace-project-surface.md) | API/CLI, nome canonico, constraints, migrations e corredor ate contract verificados |
| `delivered` | [WS-02 Lifecycle do worker no desktop](02-desktop-worker-lifecycle.md) | PR #91 integrado; executor supervisionado no app resolve B2 |
| `delivered` | [WS-03 Decisao de autoria default](03-default-authoring-authority.md) | ADR 0022 aceito; caminho B e contrato de trust fechados |
| `delivered` | [WS-11/12 Costuras do dominio](11-domain-seams.md) | Entregue em `812b330` e `62ddec8`; desbloqueia WS-20/30/40 |
| `delivered` | [WS-13 Costuras das paginas web](13-web-page-seams.md) | Entregue; brief esta `verified` com refs de implementacao e teste |
| `queued` | [WS-04 Runtime do Lab Agent copiloto](04-lab-agent-runtime.md) | WS-01 entregue; nao depende de WS-20/30/40 |
| `queued` | [WS-05 Contexto e criterios do Subject](05-subject-context-contract.md) | Decisao de contrato; precede batch util |
| `queued` | [WS-06 Batch, resiliencia de provider e metricas minimas](06-batch-and-minimal-metrics.md) | Depende de WS-02; paralelo com WS-05 |
| `queued` | [WS-07 Memoria operacional e consolidador](07-lab-agent-memory.md) | Depende de WS-04; nao depende de WS-05, WS-06, WS-20, WS-30 nem WS-40 |
| `blocked` | [WS-20 Artifact access/capture](20-artifact-access-and-capture.md) | Costuras entregues; aguarda priorizacao apos o Minimo Confortavel |
| `blocked` | [WS-30 Evaluation/checkpoint/progress](30-evaluation-checkpoint-progress.md) | Costuras entregues; aguarda priorizacao apos o Minimo Confortavel |
| `in_progress` | [WS-40 Trust nao verificado/ReviewPackage](40-execution-trust-review-package.md) | Corredor não verificado e Bundle v4 entregues na fatia atual; ReviewPackage/kind verificado ainda pendentes |
| `queued` | [WS-50 Bounded exploration e multi-turn](50-lab-agent-bounded-exploration.md) | Reescopado: so bounded exploration. O copiloto saiu para WS-04 |
| `blocked` | [WS-51 Integracao frontend](51-frontend-integration.md) | Project Room e scopes definidos; aguarda WS-01/03/04/06/40/41 |

O frontend agora possui brief de integracao, mas continua bloqueado. A fatia multipagina existe em
`main`: Observability consome endpoints reais, Create e rascunho local mais bootstrap da fixture,
Laboratory e mock. O brief WS-51 nao promove nenhuma dessas lacunas a capability.

## Regra de paralelismo

O paralelismo e limitado por arquivo compartilhado, nao por vontade:

- Onda 0 tem tres frentes sem intersecao de arquivo. Pode correr junto.
- As costuras de dominio (WS-11/12) foram seriais e inline, e ja aterrissaram: `Repository` virou raiz
  de composicao e `admit` virou composicao de checkers. Uma capability nova agora nasce em
  `contracts/admission/checks/` mais o envelope do catalogo, sem editar o mesmo trecho de arquivo.
- WS-13 (`apps/web/`) e a costura de `bundle.py` dentro de WS-30 (`evidence/`) tocam arvores disjuntas
  de WS-11/12 e podem correr em paralelo com elas.
- Onda 2 e paralela de verdade porque, depois das costuras, cada frente tem ownership distinto.
- O orcamento estrutural (`uv run python scripts/check_code_budget.py`) e gate de todas as frentes.
  Entrada de `[baseline]` em `code-budget.toml` so pode ser removida, nunca aumentada.

## Regras de worktree

- cada agente possui uma branch e uma worktree;
- nenhum agente edita a worktree do outro;
- arquivo gerado e regenerado depois do rebase, nunca copiado entre worktrees;
- migrations sao numeradas conforme a ordem real de merge;
- shared files (`docs/index.md`, package lock, generated contracts) ficam para o commit de integracao;
- se duas branches precisarem alterar o mesmo contrato normativo, interrompa o paralelo e resolva a
  decisao antes de continuar.

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
