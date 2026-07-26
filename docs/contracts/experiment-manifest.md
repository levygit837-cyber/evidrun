---
id: contract-experiment-manifest-v1
type: contract
title: Experiment Manifest v1
status: implemented
authority: normative
volatility: timeless
owner: core
created_at: 2026-07-22
updated_at: 2026-07-23
applies_to: schema/experiment-manifest@1
sources: []
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun/experiments/models.py
  - src/evidrun/contracts/legacy.py
verification_refs:
  - tests/unit/test_manifest.py
---

# Experiment Manifest v1

O manifest YAML é validado por Pydantic e compilado para JSON canônico. Uma revision aceita é
imutável e identificada por digest.

Campos obrigatórios: `schema_version`, `id`, `project_id`, `title`, `objective`, `hypothesis`,
`evidence_mode`, `scenario_refs`, `baseline_variant`, `variants`, `primary_variable`,
`subject_profile`, `context_policies`, `capture_policy`, `repetitions`, `graders` e
`comparison_plan`.

Uma variant que declare `confounders` força a validade `exploratory`. O baseline e todas as policies
referenciadas precisam existir na mesma revision.

O contrato continua válido e seus digests históricos não mudam. O adapter de compatibilidade o
converte em revisions modulares e RunSpecs para execução pelo pipeline Study, mantendo expected
answers apenas no EvaluationPlan.

No runtime atual, somente o bootstrap do benchmark versionado no próprio repositório sintetiza as
decisões de aceitação necessárias à migração, com rationale explícita de import. Isso representa a
aceitação preexistente daquele fixture confiável. O método dedicado
`import_legacy_contract_package` confere a identidade fechada de todas as revisions do
`CRL-CTX-002`, seus refs e o digest integral do pacote; `repository_fixture` não passa pelo método
comum de decision. Isso não autoriza imports genéricos a marcarem propostas novas como decisões
humanas. Um import externo deve passar pelo lifecycle normal de draft/proposed e decisão humana.

Para manter o benchmark offline compatível com o runner executável, o adapter materializa apenas os
stops terminais `goal_complete` e `budget_exhausted`; ele não adiciona `provider_error`. O budget
`max_wall_seconds` é aplicado pelo runtime e timeout produz `run.budget_exhausted`.
