---
id: contract-evaluation-checkpoint-v1
type: contract
title: Evaluation e checkpoint records v1
status: implemented
authority: normative
owner: core
created_at: 2026-07-23
updated_at: 2026-07-25
applies_to: schema/evaluation-checkpoint@1
sources:
  - docs/adr/0009-study-run-contract-composition.md
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun/contracts/authoring
  - src/evidrun/contracts/authority.py
  - src/evidrun/contracts/compiler.py
  - src/evidrun/contracts/evaluation.py
  - src/evidrun/contracts/runtime
  - src/evidrun/infrastructure/database/repository.py
verification_refs:
  - tests/unit/test_contracts.py
  - tests/integration/test_admission_and_evaluation.py
  - tests/integration/test_checkpoint_repository.py
---

# EvaluationPlan e EvaluationRecord

`EvaluationPlanRevision` declara dimensões tipadas, stages ordenados, triggers, hard gates,
disclosure, blinding, aggregation opcional, adjudicação humana e limitações. Sem projector de
aggregation, o resultado oficial permanece um vetor de dimensões, gates e incertezas; não existe
score global implícito.

`EvaluationRecord` discrimina `deterministic_grader`, `model_judge`, `human_reviewer` e
`human_adjudicator`. Ele fixa Run, plan revision/digest, evaluator efetivo, boundary verificável,
valores dimensionais, gate, rationale, confidence, evidence refs e status. Evidence refs aceitam
somente `run:`, `event:` ou `artifact:`. Model judge permanece provisório. Hard gate falho impede
stages posteriores quando o plano assim os ordena.

O [ADR 0010](../adr/0010-verifiable-human-authority.md) distingue review humana primária de
adjudicação. `human_reviewer` exige `independent_review` e pode declarar quais records considerou sem
afirmar precedência. `human_adjudicator` exige `adjudicates` e targets explícitos; o repository verifica
que pertencem à mesma Run, plan e stage e que evaluator/verifier estão autorizados pelo
`HumanAdjudicationPolicy`. Ambos são finais, append-only e exigem `HumanAttestationRecord` validado;
nenhum sobrescreve record anterior.

O schema e as relações existem, mas nenhum adapter WebAuthn ou pipeline humano está instalado. O
verifier default falha fechado. Se `HumanAdjudicationPolicy.required=true`, a admissão rejeita a Run
como `runtime:verified_human_adjudication`; o runtime atual não inicia uma Run que depois fingiria ter
recebido adjudicação.

Na persistência, refs `run:` e `event:` são verificadas contra a Run e a boundary autorizada.
`artifact:` ainda é validado apenas pelo scheme; lookup, classification e autorização no artifact
manifest não estão integrados ao repository de evaluations. Até essa integração existir, a presença
de uma ref `artifact:` não prova sozinha que o evaluator estava autorizado a lê-la.

`EvaluationDisclosure.subject` declara `none`, `pre_run`, `on_request` ou `post_run`, dimensões
públicas e se escala/anchors podem ser mostrados. `none` não materializa guidance. Em `pre_run`, o
compiler produz `SubjectEvaluationGuidance` apenas com esses campos e omite stages, evaluator,
parameters, hidden inputs e expected answer. Esse é comportamento do compiler puro, não do runner
ativo. Como o runner recebe somente objective e context, a admissão rejeita qualquer modo diferente
de `none` como `runtime:subject_evaluation_guidance_delivery`, conforme o
[ADR 0012](../adr/0012-subject-disclosure-and-terminal-semantics.md).

O runtime de evaluation continua estreito: admite somente um deterministic grader booleano,
acionado por `subject.responded`, com parâmetro `expected`. Qualquer outro conjunto de stages,
triggers ou dimensões é válido como contrato, mas rejeitado como `runtime:evaluation_pipeline`.

No ledger, `evaluation.completed` só pode ocorrer em `evaluating` e precisa corresponder ao
EvaluationRecord persistido exato, incluindo digest e gate. Um mesmo record não recebe duas
conclusões. `run.completed` exige refs com eventos de conclusão correspondentes e cobertura de todos
os stages ainda requeridos pelo EvaluationPlan depois dos hard gates; não basta anexar um record
arbitrário ao terminal.

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
isso a admissão rejeita qualquer `CheckpointPolicyRevision` como
`runtime:checkpoint_coordinator`. Uma policy aceita não é, sozinha, evidência de que seus checkpoints
serão alcançados ou registrados pelo runtime atual.

Pelo mesmo motivo, `checkpoint.validation_failed` é um payload reservado e o repository de eventos
o rejeita no runtime ativo. A API de persistência de um CheckpointRecord já produzido continua sendo
uma validação de record, não um coordinator executável.

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

Progress Artifacts definidos pelo [ADR 0011](../adr/0011-progress-artifacts-and-bundle-boundaries.md)
possuem policy, content, record e payloads de evento separados. Um trigger `checkpoint_reached`
precisa referenciar uma definition da CheckpointPolicy materializada; o outro trigger permitido é
`subject_turn_interval`, em que turno significa `subject.responded` válido. Progress Artifact não
entra no `CheckpointRecord` v1. Observer, persistência e geração em background não existem, logo a
admissão rejeita a policy como `runtime:background_progress_observer`.
