---
id: contract-run-event-payloads-v1
type: contract
title: Catálogo de payloads de Run Event v1
status: implemented
authority: normative
owner: core
created_at: 2026-07-23
updated_at: 2026-07-25
applies_to: schema/run-event-payloads@1
sources:
  - docs/contracts/run-event.md
  - docs/adr/0009-study-run-contract-composition.md
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun/contracts/runtime
  - src/evidrun/infrastructure/database/repository.py
  - src/evidrun/runs/service.py
verification_refs:
  - tests/acceptance/test_demo_flow.py
  - tests/unit/test_contracts.py
  - tests/integration/test_admission_and_evaluation.py
---

# Catálogo tipado

O envelope e a hash chain de Run Event v1 permanecem inalterados. Para tipos registrados, o payload
é validado por modelo Pydantic fechado antes de entrar no ledger.

O marco implementa payloads tipados para fila, preparação, composição de contexto, invocação e
resposta do Subject, avaliação e término da Run. O subconjunto do ADR 0016 também autoriza
`capability.offered` e `tool.called` seguido por exatamente um `tool.completed`, `tool.denied` ou
`tool.failed`, sempre para capability admitida e sob lease válido. Pause/resume, skill,
`checkpoint.validation_failed` e `progress.*` permanecem reservados até existir o coordinator
correspondente. Schema registrado não significa evento factual autorizado fora desses subconjuntos.

`subject.responded` registra `output_digest` e o capture mode aplicado. `redacted` exige somente o
marcador `[REDACTED]`; `metadata` não aceita output/evidence; `disabled` não aceita conteúdo capturado;
e `raw_encrypted` aceita somente refs `artifact:`, nunca raw inline. O repository exige que o modo
seja exatamente o default do RunSpec. O adapter real do ADR 0016 admite `raw_encrypted` com opt-in e
grava um `output_ref` `sensitive` cifrado; adapters sem esse sink continuam falhando fechado na
admissão. Para `subject_turn_interval`, somente um `subject.responded` válido conta como turno.

Eventos factuais são phase-gated. `context.composed` ocorre em `preparing`;
`subject.invoked`/`subject.responded` em `running`; e `evaluation.completed` em `evaluating`.
Cada resposta exige exatamente uma invocação anterior não respondida, uma nova invocação exige que o
turno anterior tenha terminado e a Run não entra em evaluation antes da primeira resposta.

`evaluation.completed` precisa apontar para o `EvaluationRecord` persistido exato, com mesmo Run,
digest e gate, e não pode duplicar sua conclusão. `run.completed` exige resposta do Subject, refs de
evaluation com eventos de conclusão correspondentes e cobertura dos stages requeridos pelo
EvaluationPlan após a aplicação dos hard gates. Eventos após qualquer terminal são rejeitados.

O runner aplica `BudgetSpec.max_wall_seconds` à invocação do Subject. Timeout grava
`run.budget_exhausted` com Goal não assessable antes de propagar o erro; a Run permanece terminal
`budget_exhausted`, nunca `completed`.

O terminal é discriminado por `goal_result.goal_mode`: `goal_state` usa achievement e
`bounded_exploration` usa disposition e stop reason, sem pass/fail. O runner atual só emite
`goal_state`; a admissão rejeita bounded exploration. O vocabulário bounded implementado ainda depende
do [ADR 0013](../adr/0013-bounded-exploration-terminal-semantics.md).

Presença no inventário não equivale a uso. Futuras projeções de tools e skills usadas devem contar
os eventos de lifecycle correspondentes; essa projeção não faz parte do runtime atual. Conteúdo
capturado continua sujeito à classificação e capture policy.
