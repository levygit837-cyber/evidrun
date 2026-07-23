---
id: contract-evaluation-checkpoint-v1
type: contract
title: Evaluation e checkpoint records v1
status: implemented
authority: normative
owner: core
created_at: 2026-07-23
updated_at: 2026-07-23
applies_to: schema/evaluation-checkpoint@1
sources:
  - docs/adr/0009-study-run-contract-composition.md
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun/contracts/authoring.py
  - src/evidrun/contracts/evaluation.py
  - src/evidrun/contracts/runtime.py
  - src/evidrun/infrastructure/database/repository.py
verification_refs:
  - tests/unit/test_contracts.py
  - tests/integration/test_checkpoint_repository.py
---

# EvaluationPlan e EvaluationRecord

`EvaluationPlanRevision` declara dimensões tipadas, stages ordenados, triggers, hard gates,
disclosure, blinding, aggregation opcional, adjudicação humana e limitações. Sem projector de
aggregation, o resultado oficial permanece um vetor de dimensões, gates e incertezas; não existe
score global implícito.

`EvaluationRecord` discrimina `deterministic_grader`, `model_judge` e `human_adjudicator`. Ele fixa
Run, plan revision/digest, evaluator efetivo, boundary verificável, valores dimensionais, gate,
rationale, confidence, evidence refs e status. Evidence refs aceitam somente `run:`, `event:` ou
`artifact:`. Adjudicação humana acrescenta record final referenciando o anterior; não sobrescreve o
judge. Hard gate falho impede stages posteriores quando o plano assim os ordena.

# CheckpointPolicy e CheckpointRecord

`CheckpointPolicyRevision` contém definições reutilizáveis com ID, fase, trigger tipado, validators,
captura, obrigatoriedade e compatibility tags. Um record válido sempre ancora cursor e hash do
ledger e pode referenciar context snapshot, estado público do protocolo, artifacts, workspace
permitido, inventário e avaliações concluídas.

`CheckpointRecord` só é persistido após todos os validators passarem e após o repository confirmar
que sequence/hash pertencem à Run. O `checkpoint_hash` cobre o record normalizado. Falha de trigger
ou validação deve ser evento, não record parcial.

Neste marco, checkpoint é evidência auditável. `replayability` e suas limitações são explícitos, mas
restore, replay, context extraction e fork executável não estão implementados.
