---
id: architecture-system
type: architecture
title: Arquitetura do sistema
status: implemented
authority: normative
owner: core
created_at: 2026-07-22
updated_at: 2026-07-23
applies_to: repository
sources: []
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun
  - apps/web
  - apps/desktop
verification_refs:
  - tests/acceptance/test_demo_flow.py
  - tests/integration/test_admission_and_evaluation.py
  - tests/integration/test_contract_api.py
---

# Arquitetura do sistema

O Evidrun é um monólito modular com três planes:

- **Control Plane:** projetos, Studies, revisions, decisões humanas e chats; o papel do Lab Agent
  está definido, mas seu runtime ainda não existe.
- **Execution Plane:** compilador, admissão, coordinator, worker, Subject Runner e workspace.
- **Evidence Plane:** event ledger, snapshots, artifacts, checkpoints, evaluations e bundles.

O fluxo novo é `StudyRevision aceita → compilação → RunSpec → admissão → Run → eventos`. Revisions,
specs e admissions são imutáveis. Checkpoints e evaluations se ancoram a sequence/hash do ledger.
Status, comparison, Grade, relatório e grafo permanecem projeções.

`RunRow.status` é um cache operacional. O repository valida a máquina de estados e avança a coluna
na mesma transação que grava cada evento de lifecycle; `update_run` não aceita mudança direta de
status. O event ledger continua sendo a autoridade normativa e permite verificar ou reconstruir
essa projeção.

Eventos factuais são aceitos somente na fase permitida e com seus records canônicos ligados.
Invocações e respostas do Subject são pareadas; evaluation só começa depois de uma resposta;
`evaluation.completed` aponta para o EvaluationRecord exato; e `run.completed` exige os records e
stages requeridos pelo EvaluationPlan. Eventos de pause/resume, tools, skills, checkpoint e Progress
Artifact permanecem reservados e são rejeitados enquanto seus coordinators não existem.

Superfícies:

- CLI Python;
- FastAPI em loopback;
- worker local;
- React renderer;
- Electron Main e preload.

Electron gerencia o lifecycle do backend, mas não contém regras de domínio. O React usa a mesma API
no browser e no aplicativo desktop. SQLite é canônico localmente; JSONL é exportação.

No estágio atual o coordinator executa o runner determinístico localmente pelo pipeline novo. O
runtime admite apenas `single_turn`, workspace `in_process` e capabilities catalogadas. Um protocolo
em grafo é tipável e compilável, mas é rejeitado na admissão. A interface de worker já é uma
superfície separada, mas leases e execução assíncrona durável pertencem ao próximo marco. A execução
genérica de todos os stages de um `EvaluationPlan` também não existe: o demo executa somente seu
grader determinístico; ordem e hard gates já são validados quando `EvaluationRecord`s são
persistidos.

O runner recebe somente objective e context, executa uma única interação e aplica
`max_wall_seconds` com timeout. Ao excedê-lo, grava `run.budget_exhausted` como terminal e não
`run.completed`. Budgets de tokens, tool calls ou custo, `max_turns > 1`, pause e stops fora de
`goal_complete`/`budget_exhausted` terminal bloqueiam a admissão. Todo disclosure de evaluation
diferente de `none` também bloqueia a admissão, ainda que `pre_run` seja compilável pelo contrato
puro de SubjectEnvelope.

A admissão também falha fechado para checkpoint coordinator, Progress Artifact observer, pipeline de
evaluation fora do grader determinístico suportado, adjudicação humana required, disclosure dinâmico
e terminal de bounded exploration. Esses contratos serem tipáveis e compiláveis não anuncia
capacidade executável. Decisions humanas possuem schema e verifier protocol, mas API/CLI recusam o
fluxo enquanto não houver adapter WebAuthn confiável.
