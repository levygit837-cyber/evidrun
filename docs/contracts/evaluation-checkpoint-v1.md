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

`HumanAdjudicationPolicy.required` e `authority` ainda são declarativos. O record humano exige estado
final e referência ao record anterior, mas não carrega um principal humano autenticado, e o runtime
não impede a conclusão da Run quando a adjudicação marcada como required está ausente. Esse vínculo
de autoridade deve ser fechado junto com a autenticação de decisões humanas antes de uso do Lab
Agent.

Na persistência, refs `run:` e `event:` são verificadas contra a Run e a boundary autorizada.
`artifact:` ainda é validado apenas pelo scheme; lookup, classification e autorização no artifact
manifest não estão integrados ao repository de evaluations. Até essa integração existir, a presença
de uma ref `artifact:` não prova sozinha que o evaluator estava autorizado a lê-la.

O schema v1 declara `public_dimension_ids` e `EvaluationStage.visible_to_subject`, mas o
`SubjectEnvelope` atual não materializa rubric ou dimensões públicas. Portanto esses campos ainda
não equivalem a disclosure efetivamente entregue. Antes de ativar avaliações em que transparência
ao Subject seja requisito, o humano precisa decidir se a parte pública integra o envelope canônico
ou se será entregue por outra interação explícita e auditada.

# CheckpointPolicy e CheckpointRecord

`CheckpointPolicyRevision` contém definições reutilizáveis com ID, ordem, trigger tipado, validators,
captura, obrigatoriedade e compatibility tags. Um record válido sempre ancora cursor e hash do
ledger e pode referenciar Context Snapshots, estado público do protocolo, manifest de artifacts,
workspace permitido, avaliações concluídas e a admissão exata da Run.

`CheckpointRecord` só é persistido após todos os validators passarem e após o repository confirmar
que sequence/hash pertencem à Run. O `checkpoint_hash` cobre o record normalizado. Falha de trigger
ou validação deve ser evento, não record parcial.

O que está implementado é o contrato e a validação de persistência de um record já produzido. O
coordinator ainda não observa triggers, executa validators ou cria checkpoints automaticamente; por
isso uma `CheckpointPolicyRevision` aceita não é, sozinha, evidência de que seus checkpoints serão
alcançados ou registrados pelo runtime atual.

Neste marco, checkpoint é evidência auditável. `replayability` e suas limitações são explícitos, mas
restore, replay, context extraction e fork executável não estão implementados.

As capturas `provider_resolution` e `agent_inventory` são ancoradas pelo par
`admission_record_id`/`admission_record_digest`, pois o `AdmissionRecord` contém tanto a resolução do
provider quanto o inventário resolvido. O repository exige que o par pertença à admissão exata da
Run e que a presença ou ausência de cada categoria de captura corresponda à definition. O record
ancora a evidência; ele não copia credenciais nem valores de secret bindings.

Context Snapshot e EvaluationRecord IDs são conferidos contra a Run. As capturas expressas como
`ArtifactRef` — estado de protocolo, manifest de artifacts e workspace snapshot — ainda não fazem
lookup no `ArtifactStore`; seu digest participa do `checkpoint_hash`, mas existência, classification
e autorização do blob continuam responsabilidade do futuro adapter de captura.
