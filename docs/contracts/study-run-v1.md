---
id: contract-study-run-v1
type: contract
title: Study, revisions e Run canônica v1
status: implemented
authority: normative
volatility: timeless
owner: core
created_at: 2026-07-23
updated_at: 2026-07-28
applies_to: schema/study-run@1
sources:
  - docs/adr/0009-study-run-contract-composition.md
  - docs/adr/0020-workspace-project-run-environment-boundaries.md
  - docs/adr/0022-explicit-execution-trust-without-per-run-authentication.md
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun/contracts/base.py
  - src/evidrun/contracts/authoring
  - src/evidrun/contracts/compiler.py
  - src/evidrun/contracts/runtime
verification_refs:
  - tests/unit/test_contract_revisions.py
  - tests/unit/test_contract_compilation.py
  - tests/unit/test_contract_invariants.py
  - tests/integration/test_contract_api.py
---

# Envelope de revision

Contratos de autoria usam modelos Pydantic congelados e fechados. O envelope contém
`schema_version`, `contract_type`, `logical_id`, `revision`, `project_id`, `title`, `payload` e o
`digest` calculado. O digest semântico cobre schema, tipo, identidade lógica, número da revision e
payload normalizado; identidade de storage, timestamps e decisões não participam dele.

`ContractRef` fixa `contract_type`, `logical_id`, `revision` e `digest`. Conteúdo anterior nunca é
editado. Uma correção cria nova revision. `RevisionDecisionRecord` é append-only e registra decisão,
rationale, timestamp, digest decidido e uma authority discriminada. `verified_human` exige
`HumanAttestationRecord` cobrindo o conteúdo exato; `repository_fixture` é não humano e reservado ao
import dedicado do pacote canônico `CRL-CTX-002`. Decisions comuns não aceitam essa authority. O
verifier default falha fechado. O adapter WebAuthn local existe como opt-in quando
`EVIDRUN_AUTHORITY` está habilitado; sem ele, API/CLI recusam decisão humana. Consulte o
[ADR 0010](../adr/0010-verifiable-human-authority.md). O caminho aceito para compilação sem decision
humana está no [ADR 0022](../adr/0022-explicit-execution-trust-without-per-run-authentication.md),
mas ainda não está implementado neste contrato.

# Study e Goal

`StudyIntent` registra purpose, questions, hypothesis opcional, decisão que poderá ser informada,
scope e assumptions. Ele não é incluído no `SubjectEnvelope`.

`GoalRevision` é separado do Intent e possui `goal_state` ou `bounded_exploration`. `goal_state`
exige outcome observável. `bounded_exploration` exige learning target ou outcome e, no `RunSpec`, uma
condição terminal limitada além de mera conclusão declarada. Goal não contém score, threshold,
grader, judge, expected answer oculto ou resultado de outra variant.

O [ADR 0012](../adr/0012-subject-disclosure-and-terminal-semantics.md) separa o término:
`goal_state` usa achievement; `bounded_exploration` usa disposition e stop condition, nunca
pass/fail. `RunTerminalPayload` já é uma união discriminada, mas o runner atual só emite
`goal_state`; a admissão rejeita bounded exploration como
`runtime:bounded_exploration_terminal`. A separação entre disposition e stop reason segue o
[ADR 0013](../adr/0013-bounded-exploration-terminal-semantics.md), mas ainda não habilita esse runtime.

`StudyRevision` referencia Goal, cenários e um blueprint comum. Declara evidence mode, variants,
repetitions, seed strategy, comparações, limitations e tags. Quando variants são omitidas, o modelo
normalizado cria `default`.

# Scenario e variants

`ScenarioRevision` tipa descrição, input bindings, condições observáveis, limitações e provenance.
Cada input referencia um artifact, declara classificação, visibilidade e forma de montagem. Oracle,
calibration e expected answer pertencem ao `EvaluationPlan`, não ao cenário visível ao Subject.

`VariantSpec` substitui somente refs e slots tipados: Goal, scenario, agent inventory, Run
Environment (campo `workspace` preservado no schema v1),
interaction protocol, evaluation plan, checkpoint policy, context policy, budgets, stop conditions,
Progress Artifact policy, capture policy ou extensão registrada. Parâmetro interno materialmente
diferente exige nova revision do módulo correspondente.

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

O envelope mínimo do Subject é uma allowlist fechada e contém Goal, inputs visíveis, interação visível, capabilities
efetivamente resolvidas, Run Environment, budgets e stop conditions. Ele exclui Intent, hipótese do
laboratório, outras variants, hidden graders, calibration data, chats, segredos e decisões internas.
Para Runs com Context Policy, o compiler do envelope exige inputs já materializados e rejeita
mudança da metadata de autoridade; o runner determinístico referencia o Context Snapshot selecionado
por digest. `ArtifactRef` não possui `locator` estruturalmente, portanto SubjectEnvelope,
EvaluatorEnvelope e ResolvedAgentInventory não podem carregar paths ou URLs de storage.
Com `EvaluationDisclosure.subject.mode=pre_run`, um objeto separado materializa somente as dimensões
públicas declaradas e, conforme flags, escala e anchors. Essa compilação pura preserva o contrato
futuro, mas o runner ativo recebe somente objective e context: a admissão aceita apenas `none` e
rejeita `pre_run`, `on_request` e `post_run`.
Progress Artifact ou outro conteúdo não entra automaticamente por estar referenciado no RunSpec.

O evento `subject.invoked` contém o digest calculado do SubjectEnvelope, porém o envelope
materializado não é persistido como record nem exportado pelo Bundle v2. O digest presente no ledger
não é hoje recomputável a partir do bundle.

Cada stage recebe um `EvaluatorEnvelope` separado com suas dimensões, inputs autorizados, hidden
inputs declarados e blinding policy. Ele não recebe automaticamente StudyIntent ou outras variants.
