---
id: contract-evidence-bundle-v2
type: contract
title: Evidence Bundle v2
status: implemented
authority: normative
owner: core
created_at: 2026-07-23
updated_at: 2026-07-23
applies_to: schema/evidence-bundle@2
sources:
  - docs/contracts/evidence-bundle.md
  - docs/adr/0009-study-run-contract-composition.md
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun/contracts/base.py
  - src/evidrun/evidence/export/comparison_v2.py
  - src/evidrun/evidence/verify/v2.py
  - src/evidrun/evidence/archive.py
verification_refs:
  - tests/integration/test_contract_api.py
  - tests/acceptance/test_demo_flow.py
---

# Conteúdo auditável

Evidence Bundle v2 amplia o v1 para auditar a composição Study/Run:

```text
bundle.json
comparison.json
contracts/<type>/<logical-id>@<revision>.json
run-specs/<id>.json
admissions/<id>.json
runs/<run-id>.json
events/<run-id>.jsonl
evaluations/<run-id>.json
checkpoints/<run-id>.json
artifact-manifest.json
report.md
checksums.json
```

O verificador confirma SHA-256 de arquivos, event chains, contract digests, RunSpec digests,
AdmissionRecord digests, EvaluationRecord digests e checkpoint hashes. Boundaries de evaluation e
checkpoint são validadas contra o ledger antes da persistência.

A verificação do ledger inclui sequência, hash chain, payload tipado, ator permitido, matriz
evento/fase, transições de lifecycle, pareamento Subject invoked/responded e ausência de eventos
reservados ou posteriores ao terminal. O primeiro `run.queued` precisa corresponder aos digests de
RunSpec/Admission e à identidade da Run; o terminal precisa corresponder ao Goal mode e às stop
conditions declaradas.

O verificador também exige que IDs de baseline/candidate sejam iguais entre bundle, comparison e
RunSpecs; que cada EvaluationRecord tenha exatamente um `evaluation.completed` correspondente; que
o terminal completed referencie o conjunto completo de records e cubra os stages requeridos pelo
EvaluationPlan; e que o artifact manifest seja exatamente o conjunto de entries derivado dos
RunSpecs e checkpoints, sem omissões ou entries extras.

Bundle v1 continua verificável e pode ser exportado pela opção explícita de compatibilidade. Exports
novos da API e CLI usam v2. Nenhum bundle inclui valor de credencial ou secret binding resolvido.

Conforme o [ADR 0011](../adr/0011-progress-artifacts-and-bundle-boundaries.md), o v2 atual declara
`profile=audit`, `artifact_content=references_only`, `portable=false` e `replayable=false`. Ele pode
conter refs sem os respectivos blobs ou grants; por isso não afirma portabilidade offline completa,
materialização de artifacts, restore ou replay.

`artifact-manifest.json` lista artifacts intencionalmente referenciados pelo escopo exportado, seu
papel, classification, digest e se o conteúdo foi incluído ou omitido. O manifest não é telemetria de
filesystem e não afirma enumerar todo arquivo lido, editado ou observado durante a Run. O verificador
confirma que o manifest corresponde às refs canônicas exportadas e preserva os flags não portáveis.

O Bundle v2 não inclui o SubjectEnvelope materializado como record próprio; embora
`subject.invoked` carregue seu digest alegado, o verificador não consegue recomputar esse digest sem
o envelope exato.

Um futuro export `portable` precisará manifest de completude, grants e autorização. Replay exigirá
contrato próprio e uma nova Run.
