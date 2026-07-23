---
id: adr-0013
type: adr
title: Semântica terminal de bounded exploration em dois eixos
status: accepted
authority: normative
owner: core
created_at: 2026-07-23
updated_at: 2026-07-23
applies_to: contracts/subject-terminal/bounded-exploration@1
sources:
  - docs/adr/0012-subject-disclosure-and-terminal-semantics.md
  - docs/contracts/study-run-v1.md
supersedes:
  - docs/adr/0012-subject-disclosure-and-terminal-semantics.md
superseded_by: null
implementation_refs:
  - src/evidrun/contracts/runtime.py
  - src/evidrun/contracts/compiler.py
  - src/evidrun/infrastructure/database/repository.py
verification_refs:
  - tests/unit/test_contracts.py
  - tests/integration/test_admission_and_evaluation.py
---

# Contexto

O ADR 0012 decidiu que bounded exploration não usa achievement nem pass/fail, mas sua lista original
misturou o estado operacional da investigação com a causa que encerrou a Run. O schema implementado
já separa esses conceitos. Este successor fecha somente essa taxonomia; todas as demais decisões do
ADR 0012 permanecem vigentes.

# Decisão

O resultado terminal de `Goal.mode=bounded_exploration` usa dois eixos independentes:

- `disposition`: `concluded`, `incomplete` ou `not_assessable`;
- `stop_reason`: `evidence_saturation`, `bounded_completion`, `budget_limit`, `time_limit`,
  `turn_limit`, `human_stop`, `guardrail` ou `provider_failure`.

`disposition` descreve somente se a exploração limitada alcançou uma conclusão operacional
interpretável dentro de suas regras. `stop_reason` registra por que a execução parou. Um limite de
budget, tempo ou turnos não implica `concluded`; da mesma forma, `concluded` não afirma qualidade,
verdade, causalidade ou aprovação.

O payload também registra `stop_condition_kind`, que precisa existir no RunSpec, e pode carregar
`learning_summary_ref` e evidence refs autorizadas. Lifecycle terminal, disposition e qualidade
continuam eixos distintos.

# Escopo da supersession

Este ADR substitui apenas a lista de dispositions de bounded exploration do ADR 0012 pela separação
em `disposition` e `stop_reason`. Ele não altera a allowlist do SubjectEnvelope, disclosure,
visibilidade de evaluation, estados de `goal_state` nem a proibição de transformar exploração em
pass/fail.

# Estado de implementação

O `RunTerminalPayload` implementa a união discriminada e a taxonomia acima. O repository confere que
o Goal mode e a stop condition pertencem ao RunSpec. O runner determinístico ainda não produz esse
branch, e a admissão rejeita `bounded_exploration` como
`runtime:bounded_exploration_terminal`. Portanto a decisão é representável e validável, mas não é
uma capacidade executável.

# Alternativas rejeitadas

- Usar o motivo da parada como disposition: mistura causa factual com estado da investigação.
- Tratar qualquer limite atingido como conclusão: cria sucesso implícito.
- Reutilizar achievement de `goal_state`: reintroduz pass/fail em uma exploração.

# Consequências

- Relatórios exibem disposition e stop reason separadamente.
- Projectors não inferem qualidade ou causalidade a partir de nenhum dos dois campos.
- O runtime bounded só pode ser habilitado quando conseguir produzir ambos a partir do ledger e da
  stop policy admitida.
