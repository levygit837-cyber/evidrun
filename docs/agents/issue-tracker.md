---
id: agents-issue-tracker
type: guide
title: Rastreador de issues das agent skills
status: accepted
authority: informative
volatility: timeless
owner: core
created_at: 2026-07-23
updated_at: 2026-07-23
applies_to: repository
sources: []
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
---

# Rastreador de issues: GitHub

As issues e os PRDs deste repositório ficam como issues do GitHub. Use a CLI `gh` para todas as operações.

## Convenções

- **Criar uma issue**: `gh issue create --title "..." --body "..."`. Use um heredoc para corpos com várias linhas.
- **Ler uma issue**: `gh issue view <number> --comments`, filtrando os comentários com `jq` e buscando também as labels.
- **Listar issues**: `gh issue list --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'` com os filtros `--label` e `--state` apropriados.
- **Comentar em uma issue**: `gh issue comment <number> --body "..."`
- **Aplicar / remover labels**: `gh issue edit <number> --add-label "..."` / `--remove-label "..."`
- **Fechar**: `gh issue close <number> --comment "..."`

Infira o repositório a partir de `git remote -v` — `gh` faz isso automaticamente quando executado dentro de um clone.

## Pull requests como superfície de triagem

**PRs as a request surface: no.** _(Defina como `yes` se este repositório tratar PRs externos como solicitações de funcionalidades; `/triage` lê esta flag.)_

Quando definida como `yes`, os PRs passam pelas mesmas labels e estados das issues, usando os equivalentes de `gh pr`:

- **Ler um PR**: `gh pr view <number> --comments` e `gh pr diff <number>` para o diff.
- **Listar PRs externos para triagem**: `gh pr list --state open --json number,title,body,labels,author,authorAssociation,comments` e depois manter apenas `authorAssociation` igual a `CONTRIBUTOR`, `FIRST_TIME_CONTRIBUTOR` ou `NONE` (descartar `OWNER`/`MEMBER`/`COLLABORATOR`).
- **Comentar / aplicar label / fechar**: `gh pr comment`, `gh pr edit --add-label`/`--remove-label`, `gh pr close`.

O GitHub compartilha um único espaço de números entre issues e PRs, portanto um `#42` isolado pode ser qualquer um dos dois — resolva com `gh pr view 42` e use `gh issue view 42` como fallback.

## Quando uma skill disser "publique no rastreador de issues"

Crie uma issue do GitHub.

## Quando uma skill disser "busque o ticket relevante"

Execute `gh issue view <number> --comments`.

## Operações de wayfinding

Usadas por `/wayfinder`. O **mapa** é uma única issue, com issues **filhas** como tickets.

- **Mapa**: uma única issue com a label `wayfinder:map`, contendo o corpo Notes / Decisions-so-far / Fog. `gh issue create --label wayfinder:map`.
- **Ticket filho**: uma issue vinculada ao mapa como sub-issue do GitHub (`gh api` no endpoint de sub-issues). Onde sub-issues não estiverem habilitadas, adicione o filho a uma lista de tarefas no corpo do mapa e coloque `Part of #<map>` no topo do corpo do filho. Labels: `wayfinder:<type>` (`research`/`prototype`/`grilling`/`task`). Depois de reivindicado, o ticket é atribuído ao dev que conduz o mapa.
- **Bloqueio**: as **dependências nativas de issues** do GitHub — a representação canônica e visível na UI. Adicione uma aresta com `gh api --method POST repos/<owner>/<repo>/issues/<child>/dependencies/blocked_by -F issue_id=<blocker-db-id>`, em que `<blocker-db-id>` é o **database id** numérico do bloqueador (`gh api repos/<owner>/<repo>/issues/<n> --jq .id`, _não_ o `#number` nem o `node_id`). O GitHub informa `issue_dependencies_summary.blocked_by` (somente bloqueadores abertos — a trava ativa). Onde as dependências não estiverem disponíveis, use como fallback uma linha `Blocked by: #<n>, #<n>` no topo do corpo do filho. Um ticket é desbloqueado quando todos os bloqueadores estão fechados.
- **Consulta da fronteira**: liste os filhos abertos do mapa (`gh issue list --state open`, limitado às sub-issues / à lista de tarefas do mapa), descarte qualquer um com bloqueador aberto (`issue_dependencies_summary.blocked_by > 0` ou uma issue aberta na linha `Blocked by`) ou com responsável; vence o primeiro na ordem do mapa.
- **Reivindicar**: `gh issue edit <n> --add-assignee @me` — a primeira escrita da sessão.
- **Resolver**: `gh issue comment <n> --body "<answer>"`, depois `gh issue close <n>` e então anexe um ponteiro de contexto (gist + link) a Decisions-so-far do mapa.
