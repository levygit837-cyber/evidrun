---
id: planning-task-subject-context-contract
type: implementation-task
title: WS-05 Contexto e criterios do Subject
status: proposed
authority: planning
volatility: snapshot
owner: core
created_at: 2026-07-26
updated_at: 2026-07-26
observed_at: 2026-07-26
review_due: 2026-08-23
applies_to: subject-context
sources:
  - docs/planning/comfortable-minimum.md
  - docs/adr/0012-subject-disclosure-and-terminal-semantics.md
  - docs/adr/0016-real-subject-read-tool-and-tracing.md
  - docs/contracts/study-run-v1.md
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
---

# WS-05 — Contexto e criterios do Subject

`workstream_state: queued`

## Resultado pratico

Duas variants de um mesmo Study passam a poder diferir de forma tipada e auditavel na dimensao que a
hipotese investiga, recebendo o mesmo material de referencia.

Hoje isso nao e expressavel, e por isso o cenario que motiva o produto nao roda: "gerar um plano antes
de implementar versus implementacao direta, mesmo contexto" exige que a diferenca entre as variants
seja um objeto do contrato, nao texto solto.

## O problema exato

O `SubjectEnvelope` e uma allowlist fechada e compila Goal, inputs visiveis, protocolo visivel,
capabilities admitidas, workspace, budgets e stop conditions. Isso e suficiente para uma Run
determinista de fixture.

O que falta e a autoria: nao existe vocabulario para declarar **de onde vem** o contexto de um
experimento real. Material de referencia, estado inicial, criterios visiveis ao Subject e a dimensao
de variacao entre variants nao tem forma tipada.

Sem isso, `Variant` degenera em override de string e a comparacao perde a propriedade que a torna
causal: uma variavel primaria isolada.

## Escopo

Contrato de contexto de Scenario, suficiente para uma comparacao de variavel primaria unica:

- material de referencia declarado por `ArtifactRef`, entregue identicamente a todas as variants
  irmas;
- criterios e limites visiveis ao Subject, separados do EvaluationPlan e do StudyIntent;
- dimensao de variacao tipada: o que exatamente difere entre baseline e candidate, e a garantia de que
  o resto e identico por digest;
- `Context Snapshot` registrado no ledger com o digest do que foi efetivamente entregue.

A allowlist do envelope e estendida deliberadamente, item por item, com justificativa por campo. Campo
novo de RunSpec continua nao entrando no envelope automaticamente.

## Invariantes que nao podem ser relaxadas

- **Allowlist fechada.** Cada campo novo do envelope e uma decisao explicita, nao consequencia de
  existir no RunSpec.
- **`ArtifactRef` sem locator.** Path, URL e storage locator continuam nao representaveis em nenhum
  contrato de envelope.
- **`ArtifactRef` nao concede acesso.** Referencia identifica conteudo; leitura depende de capability
  admitida.
- **Nada do laboratorio atravessa.** StudyIntent, hipotese, plan completo, chats, hidden graders,
  calibracao e resultado de outra variant continuam fora.
- **Digest de identidade.** Se duas variants irmas afirmam receber o mesmo material, o contrato tem
  que provar isso por digest, nao por convencao.
- **Classificacao.** `sensitive` e `restricted` continuam rejeitados pelo runtime ativo.

## Testes obrigatorios

- duas variants irmas com material identico produzem o mesmo digest de material e envelopes que
  diferem exatamente na dimensao declarada;
- campo novo de RunSpec fora da allowlist nao aparece no envelope compilado;
- material `sensitive` rejeita a admissao;
- `Context Snapshot` gravado com o digest do que foi entregue, verificavel no bundle;
- envelope sem StudyIntent, hipotese, hidden grader e resultado de irma, por assercao explicita;
- ausencia de locator em todo campo de ref.

## Criterio de saida

Um Study com duas variants que diferem apenas em "gerar plano antes de implementar" compila,
admite e executa, e o bundle prova que ambas receberam o mesmo material. O que difere esta declarado
no contrato, nao inferido do texto.
