---
id: planning-worktree-cleanup-plan
type: planning
title: Registro da limpeza da worktree obsoleta 2280
status: accepted
authority: planning
volatility: snapshot
owner: core
created_at: 2026-07-25
updated_at: 2026-08-02
observed_at: 2026-08-02
review_due: 2026-09-02
applies_to: repository
sources:
  - docs/planning/tasks/README.md
  - docs/architecture/codebase-layout.md
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
---

# Registro da limpeza da worktree obsoleta 2280

Este documento registrava a **intencao** de excluir a worktree Codex 2280. A exclusao foi executada
e o documento agora registra o que aconteceu. Ele nao autoriza nenhuma nova exclusao.

## Estado medido em 2026-08-02

```text
~/Documentos/AProjects/evidrun  2d7ec43 [main]   ← unica worktree
```

| Fato | Medicao |
| --- | --- |
| Worktrees registradas | 1 (`git worktree list`) |
| Diretorios administrativos em `.git/worktrees` | nenhum |
| Branches locais | 1 (`main`) |
| Worktree `2280` | nao existe mais; media em `/Users/apple/...`, de um checkout macOS anterior |

A worktree nunca teve commit exclusivo: seu HEAD `1010879` era ancestral de `main`. O risco estava
apenas no conteudo nao rastreado, e esse conteudo foi preservado antes da exclusao.

## O que foi preservado, e onde

O conteudo nao rastreado da worktree foi commitado no branch remoto
`archive/codex-2280-uncommitted` (`c5d273f`, 2026-07-27, `archive: preserve Codex 2280 worktree
snapshot`). Ele carrega 71 arquivos que nao existem em `main`, incluindo os 53 de `droid-wiki/` e os
briefs `tasks/00-runtime-kernel-integration.md`, `tasks/10-mvp-operator-console.md` e
`tasks/40-trust-sandbox-review-package.md`.

A decisao original de descartar cada grupo continua valida e agora esta cumprida em `main`:

- **`docs/planning/` duplicado** — descartado. As versoes de `main` sao posteriores e revisadas em PR.
- **WS-00** — entregue. Coordinator, queue/lease/fencing, worker separado, adapter Responses com read
  tool, Bundle auditavel e authority opt-in existem em `main`; o Bundle evoluiu para v4 desde o plano.
- **WS-10** — decomposto em WS-01/02/03 mais WS-13 e WS-51, conforme
  [dispatch de workstreams](tasks/README.md).
- **`droid-wiki/`** — descartado. Era snapshot gerado, ancorado em `1010879`, descrevendo `Repository`
  e `AdmissionService` em formas que deixaram de existir. Regenerar contra `main` seria trabalho
  proprio com issue propria, nao restauracao deste snapshot.

## Branches de preservacao ainda abertos

Estes branches remotos existem apenas como rede de seguranca. Nenhum deles esta mergeado em `main`, e
nenhum deve ser tratado como trabalho pendente ou como fonte de comportamento atual:

| Branch | Data | Conteudo exclusivo |
| --- | --- | --- |
| `archive/codex-2280-uncommitted` | 2026-07-27 | 71 arquivos: `droid-wiki/` mais tres briefs superados |
| `backup/migration-stash-2026-07-29` | 2026-07-24 | stash de `task/mvp-operator-console` mais protótipos de design |
| `backup/migration-stash-base-2026-07-29` | 2026-07-23 | base do stash: `feat(design): add operator console prototypes` |
| `backup/migration-stash-untracked-2026-07-29` | 2026-07-24 | 59 arquivos untracked, incluindo `scripts/publish_wiki.py` |

Excluir qualquer um deles descarta conteudo que nao existe em outro lugar. Isso exige decisao humana
explicita, exatamente como a exclusao da worktree exigiu.

## Registro de mudancas

- 2026-07-25 — plano criado apos inspecao da worktree; nenhuma exclusao executada.
- 2026-07-27 — conteudo nao rastreado preservado em `archive/codex-2280-uncommitted` (`c5d273f`).
- 2026-08-02 — worktree confirmada ausente; documento convertido de plano em registro. Branch
  `fix/issue-120-resource-budget-proof` removido do remote por ter arvore identica a `main` apos o
  squash do PR #122.
