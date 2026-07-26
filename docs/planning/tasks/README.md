---
id: planning-tasks-index
type: planning
title: Dispatch de workstreams para agentes
status: accepted
authority: planning
volatility: snapshot
owner: product-engineering
created_at: 2026-07-23
updated_at: 2026-07-24
observed_at: 2026-07-24
review_due: 2026-08-07
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

| Estado | Brief | Proxima acao |
| --- | --- | --- |
| `queued` | [WS-01 Superficie de Workspace/Project](01-workspace-project-surface.md) | Pode iniciar imediatamente, em paralelo com WS-02 e WS-03 |
| `queued` | [WS-02 Lifecycle do worker no desktop](02-desktop-worker-lifecycle.md) | Pode iniciar imediatamente; nao toca dominio Python |
| `queued` | [WS-03 Decisao de autoria default](03-default-authoring-authority.md) | ADR sucessor; decisao humana, precede WS-40 |
| `delivered` | [WS-11/12 Costuras do dominio](11-domain-seams.md) | Entregue em `812b330` e `62ddec8`; desbloqueia WS-20/30/40 |
| `blocked` | [WS-20 Artifact access/capture](20-artifact-access-and-capture.md) | Aguarda costuras |
| `blocked` | [WS-30 Evaluation/checkpoint/progress](30-evaluation-checkpoint-progress.md) | Aguarda costuras |
| `blocked` | [WS-40 Trust sandbox/ReviewPackage](40-trust-sandbox-review-package.md) | Aguarda WS-03 e costuras |
| `queued` | [WS-13 Costuras das paginas web](13-web-page-seams.md) | Pode iniciar imediatamente; so toca `apps/web/src/features/**` |
| `blocked` | [WS-50 Lab Agent/bounded exploration](50-lab-agent-bounded-exploration.md) | Aguarda WS-20, WS-30 e WS-40 |

O frontend nao tem brief de integracao ativo. A fatia multipagina existe em `main`: Observability
consome endpoints reais, Create e rascunho local mais bootstrap da fixture, Laboratory e mock. A
integracao real pertence a WS-51 e depende de WS-41 e WS-50. WS-13 e ortogonal a isso: extrai as
paginas existentes sem mudar o que elas fazem.

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
