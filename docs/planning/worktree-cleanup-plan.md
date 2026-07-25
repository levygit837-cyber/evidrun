---
id: planning-worktree-cleanup-plan
type: planning
title: Plano de exclusao da worktree obsoleta 2280
status: draft
authority: planning
owner: core
created_at: 2026-07-25
updated_at: 2026-07-25
observed_at: 2026-07-25
review_due: 2026-08-08
applies_to: repository
sources:
  - docs/planning/tasks/README.md
  - docs/architecture/codebase-layout.md
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
---

# Plano de exclusao da worktree obsoleta 2280

Este documento registra intencao de limpeza. Ele **nao** executa a exclusao: `git worktree remove`
descarta trabalho nao commitado sem confirmacao, e a worktree contem 53 arquivos nao rastreados que
nunca existiram em `main`. A exclusao exige decisao humana explicita.

## Estado medido em 2026-07-25

```text
/Users/apple/Documents/evidrun              1198992 [main]         ← worktree principal, ativa
/Users/apple/.codex/worktrees/2280/evidrun  1010879 (detached)     ← obsoleta
```

| Fato | Medicao |
| --- | --- |
| HEAD da worktree | `1010879 feat(authority): verifiable human authority per ADR 0010 (#3)`, de 2026-07-23 |
| `1010879` e ancestral de `main`? | sim |
| Commits na worktree ausentes de `main` | **nenhum** (`git log main..HEAD` vazio) |
| Commits em `main` desde `1010879` | 12 |
| Ultima escrita na worktree | 2026-07-23 17:41 |
| Arquivos nao rastreados | 53 (10 em `docs/planning/`, 1 template, 52 md em `droid-wiki/`) |

Como nao ha commit exclusivo, **nenhum trabalho versionado se perde**. O risco esta exclusivamente no
conteudo nao rastreado.

## O que existe so na worktree, e o que fazer com cada coisa

### 1. `docs/planning/` — versao anterior, ja superada

Nove arquivos com o mesmo path que arquivos hoje em `main`, todos com conteudo diferente:
`README.md`, `mvp-capability-map.md`, `mvp-implementation-roadmap.md`, `tasks/README.md`,
`tasks/20-artifact-access-and-capture.md`, `tasks/30-evaluation-checkpoint-progress.md`,
`tasks/40-trust-sandbox-review-package.md`, `tasks/50-lab-agent-bounded-exploration.md`,
`templates/agent-workstream.md`.

**Decisao: descartar.** As versoes em `main` sao posteriores e foram revisadas em PRs. As da worktree
sao o rascunho de 2026-07-23 que originou aquelas.

### 2. `docs/planning/tasks/00-runtime-kernel-integration.md` (WS-00) e `10-mvp-operator-console.md` (WS-10)

Dois briefs que nao existem em `main` com esses nomes. Ambos com `status: accepted`.

**WS-00 ja foi entregue.** O brief exigia coordinator, queue/lease/fencing, worker separado, adapter
real Responses com read tool, Bundle v3 auditavel e authority preservada. Todos verificados presentes
em `main`:

| Resultado obrigatorio do WS-00 | Onde esta em `main` |
| --- | --- |
| `RunExecutionCoordinator`, queue, lease, fencing | `runs/coordinator.py`, `infrastructure/database/queue/` |
| worker separado | `entrypoints/worker/app.py` |
| adapter real Responses + read tool | `ResponsesReadAgentAdapter` em `runs/adapters.py` |
| Bundle v3 | `export_run_v3` em `evidence/bundle.py` |
| authority opt-in | `authority/service.py` |

O brief tambem cita um `WORKTREE_PATH` de uma **terceira** worktree (`4073`) que nao existe mais, e um
`TARGET_SHA_OBSERVED` que hoje esta 12 commits atras. E documento de coordenacao de uma migracao
concluida.

**WS-10 (`workstream_state: queued`) foi decomposto.** O console operacional aparece hoje como
WS-01/02/03 (Onda 0) mais WS-13 e WS-51 em `docs/planning/tasks/README.md`.

**Decisao: descartar, mas conferir antes.** Se algum nao-objetivo ou invariante do WS-00 nao estiver
representado em nenhum brief atual, extraia essa linha para o brief correspondente **antes** de
excluir. E o unico item deste plano que exige leitura, nao so verificacao.

### 3. `droid-wiki/` — 52 arquivos, 3.761 linhas

Wiki gerada automaticamente em 2026-07-23, ancorada no commit `1010879` (`.wiki-meta.json` declara
`commitHash` e `generatedAt`). Descreve arquitetura, systems, primitives e "by the numbers".

**Esta obsoleta de forma verificavel.** `by-the-numbers.md` afirma "Python under `src/`: 10,622 lines
across 62 files", medido antes de WS-11 e WS-12, que juntos criaram 44 arquivos novos. As paginas
`systems/database.md` e `systems/contracts/compiler.md` descrevem `Repository` e `AdmissionService`
nas formas que deixaram de existir.

**Decisao: descartar.** Nunca foi versionada, nunca foi referenciada por `docs/index.md`, e um wiki
gerado a partir de um commit e reprodutivel a partir de qualquer outro. Manter uma copia de 3.761
linhas que descreve uma arquitetura extinta cria exatamente o risco que o `AGENTS.md` proibe:
documentacao que contradiz o codigo.

Se o valor desejado for a wiki e nao aquele snapshot, o caminho e regenerar contra `main`, como
trabalho proprio com issue propria.

## Ordem de execucao proposta

```text
1. ler 00-runtime-kernel-integration.md e 10-mvp-operator-console.md
   └─ extrair para os briefs atuais qualquer invariante ou nao-objetivo ainda nao representado
2. confirmar de novo que nao ha commit exclusivo:
   git -C <worktree> log --oneline main..HEAD     → deve sair vazio
3. arquivar o que for decidido preservar (copiar para main como mudanca revisada em PR)
4. remover a worktree:
   git worktree remove --force /Users/apple/.codex/worktrees/2280/evidrun
5. git worktree prune
6. confirmar: git worktree list mostra apenas a worktree principal
```

O passo 4 usa `--force` porque a worktree tem alteracoes nao commitadas; sem `--force` o Git recusa,
e essa recusa e a protecao. **Nao passe `--force` antes de concluir os passos 1 a 3.**

## Riscos

- **Perda de intencao, nao de codigo.** Os briefs WS-00/WS-10 registram decisoes de coordenacao. O
  codigo esta em `main`; o raciocinio pode nao estar.
- **`git worktree remove --force` e irreversivel** para conteudo nao rastreado. Nao ha stash, nao ha
  reflog para arquivo untracked.
- **O stash `stash@{0}`** (`On task/mvp-operator-console: safety: pre-merge uncommitted information
  preserved in PRs 7-9`) pertence ao repositorio, nao a worktree, e **sobrevive** a exclusao. Ele nao
  faz parte deste plano.

## Registro de mudancas

- 2026-07-25 — plano criado apos inspecao da worktree; nenhuma exclusao executada.
