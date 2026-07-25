---
id: planning-index
type: planning
title: Planejamento temporal de implementacao
status: accepted
authority: planning
owner: product-engineering
created_at: 2026-07-23
updated_at: 2026-07-23
observed_at: 2026-07-23
review_due: 2026-07-30
applies_to: implementation-planning
sources:
  - docs/index.md
  - docs/governance/documentation.md
  - docs/governance/delivery-status.md
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
---

# Planejamento temporal

Esta pasta organiza trabalho executavel sem transformar backlog, branch ou experimento em
comportamento normativo. Ela pode registrar um snapshot do checkout, dependencias, ownership de
worktree, testes, riscos e instrucoes para agentes. O conteudo precisa ser revalidado na data em que
uma tarefa comecar.

## O que pertence aqui

- mapas temporais de capability;
- roadmap de implementacao por fatias verticais;
- briefs que podem ser entregues diretamente a Codex, Droid ou outro agente;
- condicoes de loop, bloqueio, follow-up e handoff;
- conflitos de integracao entre worktrees;
- criterios de saida de uma entrega ainda nao implementada.

## O que nao pertence aqui

- mudanca de contrato canonico;
- nova autoridade ou excecao de seguranca;
- alegacao de que uma branch ativa ja existe em `main`;
- resultado de teste sem a respectiva evidencia;
- roadmap apresentado como comportamento atual.

Mudanca normativa continua exigindo ADR sucessor. Contratos e arquitetura continuam em
`docs/contracts`, `docs/adr` e `docs/architecture`.

## Estado de uma task

O frontmatter descreve o estado do documento, nao o estado do codigo. Cada brief deve declarar no
corpo um `workstream_state` dentre:

- `queued`: pode ser iniciado quando as dependencias forem satisfeitas;
- `active`: existe uma worktree em execucao;
- `integration_pending`: implementacao existe, mas ainda nao esta em `main`;
- `blocked`: falta uma decisao ou dependencia externa identificada;
- `done_on_main`: merge e verificacao final foram confirmados.

`implemented_in_worktree` nunca equivale a `implemented` no repositorio. O status somente muda para
`done_on_main` depois de merge, CI e verificacao no commit de `main`.

## Contrato minimo de um brief para agente

Todo brief executavel deve conter:

1. resultado pratico e nao objetivos;
2. snapshot inicial e fatos que precisam ser redescobertos;
3. dependencias e ownership de paths;
4. invariantes normativas que nao podem ser relaxadas;
5. variaveis do harness;
6. loop de descoberta, implementacao, teste, ataque e reparo;
7. condicionais de parada ou escalacao;
8. testes focais, testes transversais e gates completos;
9. uso permitido de subagentes;
10. formato de handoff e follow-ups.

O template reutilizavel esta em
[Agent workstream](../templates/agent-workstream.md).

## Artefatos deste ciclo

- [Dispatch de workstreams para agentes](tasks/README.md)
- [Mapa de capabilities do MVP](mvp-capability-map.md)
- [Roadmap de implementacao do MVP](mvp-implementation-roadmap.md)
- [Acesso e materializacao de artifacts](tasks/20-artifact-access-and-capture.md)
- [Evaluation, checkpoints e Progress Artifacts](tasks/30-evaluation-checkpoint-progress.md)
- [Trust modes, sandbox e ReviewPackage](tasks/40-trust-sandbox-review-package.md)
- [Lab Agent e bounded exploration](tasks/50-lab-agent-bounded-exploration.md)

## Regra de manutencao

Ao iniciar uma task, atualize `observed_at`, branch, base SHA e dependencias. Ao encerrar, registre o
commit/PR no handoff, atualize o mapa de capabilities e marque o brief como superseded ou
`done_on_main`. Nao reescreva ADRs aceitos para fazer o roadmap parecer concluido.
