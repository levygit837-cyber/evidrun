---
id: contract-experiment-manifest-v1
type: contract
title: Experiment Manifest v1
status: implemented
authority: normative
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
aceitação preexistente daquele fixture confiável; não é uma autorização para imports genéricos
marcarem propostas novas como decisões humanas. Um import externo deve passar pelo lifecycle normal
de draft/proposed e decisão humana.
