---
id: contract-study-run-v1
type: contract
title: Study, revisions e Run canônica v1
status: implemented
authority: normative
owner: core
created_at: 2026-07-23
updated_at: 2026-07-23
applies_to: schema/study-run@1
sources:
  - docs/adr/0009-study-run-contract-composition.md
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun/contracts/base.py
  - src/evidrun/contracts/authoring.py
  - src/evidrun/contracts/compiler.py
  - src/evidrun/contracts/runtime.py
verification_refs:
  - tests/unit/test_contracts.py
  - tests/integration/test_contract_api.py
---

# Envelope de revision

Contratos de autoria usam modelos Pydantic congelados e fechados. O envelope contém
`schema_version`, `contract_type`, `logical_id`, `revision`, `project_id`, `title`, `payload` e o
`digest` calculado. O digest semântico cobre schema, tipo, identidade lógica, número da revision e
payload normalizado; identidade de storage, timestamps e decisões não participam dele.

`ContractRef` fixa `contract_type`, `logical_id`, `revision` e `digest`. Conteúdo anterior nunca é
editado. Uma correção cria nova revision. `RevisionDecisionRecord` é append-only, exige ator humano e
registra decisão, rationale, timestamp e digest decidido.

# Study e Goal

`StudyIntent` registra purpose, questions, hypothesis opcional, decisão que poderá ser informada,
scope e assumptions. Ele não é incluído no `SubjectEnvelope`.

`GoalRevision` é separado do Intent e possui `goal_state` ou `bounded_exploration`. `goal_state`
exige outcome observável. `bounded_exploration` exige learning target ou outcome e, no `RunSpec`, uma
condição terminal limitada além de mera conclusão declarada. Goal não contém score, threshold,
grader, judge, expected answer oculto ou resultado de outra variant.

`StudyRevision` referencia Goal, cenários e um blueprint comum. Declara evidence mode, variants,
repetitions, seed strategy, comparações, limitations e tags. Quando variants são omitidas, o modelo
normalizado cria `default`.

# Scenario e variants

`ScenarioRevision` tipa descrição, input bindings, condições observáveis, limitações e provenance.
Cada input referencia um artifact, declara classificação, visibilidade e forma de montagem. Oracle,
calibration e expected answer pertencem ao `EvaluationPlan`, não ao cenário visível ao Subject.

`VariantSpec` substitui somente refs e slots tipados: Goal, scenario, agent inventory, workspace,
interaction protocol, evaluation plan, checkpoint policy, context policy, budgets, stop conditions,
capture policy ou extensão registrada. Parâmetro interno materialmente diferente exige nova revision
do módulo correspondente.

Em `prospective_controlled`, o diff material entre baseline e candidate deve ser exatamente a
`primary_variable`. Em `exploratory`, múltiplas diferenças são permitidas com confounders declarados,
sem inferência causal automática.

# Compilação e Run

O compilador resolve somente revisions aceitas, confere digests e gera uma matriz determinística de
`RunSpec`s. Cada spec materializa todas as refs e os payloads necessários à execução, incluindo
budgets, stop conditions, capture policy e limitações. Seu digest é estável sobre JSON canônico.

Uma Run só é criada após `AdmissionRecord.decision == admitted`. `RunRecord` liga `run_id`, RunSpec,
admission, Study, scenario, variant, repetição e eventual `retry_of`. Lifecycle e estado terminal são
derivados de eventos; a coluna operacional de status não é fonte canônica.

# SubjectEnvelope

O envelope mínimo do Subject contém Goal, inputs visíveis, interação visível, capabilities
efetivamente resolvidas, workspace, budgets e stop conditions. Ele exclui Intent, hipótese do
laboratório, outras variants, hidden graders, calibration data, chats, segredos e decisões internas.
Para Runs com Context Policy, o compiler do envelope exige inputs já materializados e rejeita
locators de storage; o runner determinístico referencia o Context Snapshot selecionado por digest.

Cada stage recebe um `EvaluatorEnvelope` separado com suas dimensões, inputs autorizados, hidden
inputs declarados e blinding policy. Ele não recebe automaticamente StudyIntent ou outras variants.
