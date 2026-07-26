---
id: contract-evidence-bundle-v3
type: contract
title: Evidence Bundle v3 por Run
status: implemented
authority: normative
volatility: timeless
owner: core
created_at: 2026-07-23
updated_at: 2026-07-25
applies_to: schema/evidence-bundle@3
sources:
  - docs/contracts/evidence-bundle-v2.md
  - docs/adr/0014-durable-runtime-kernel.md
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun/evidence/export/run_v3.py
  - src/evidrun/evidence/verify/v3.py
  - src/evidrun/evidence/verify/dispatch.py
  - src/evidrun/evidence/verify/records.py
  - src/evidrun/contracts/runtime
verification_refs:
  - tests/integration/test_runtime_kernel.py
  - tests/integration/test_runtime_queue.py
---

# Escopo

Evidence Bundle v3 exporta uma Run canônica terminal, independente de comparison:

```text
bundle.json
contracts/<type>/<logical-id>@<revision>.json
run-specs/<id>.json
admissions/<id>.json
runs/<run-id>.json
events/<run-id>.jsonl
evaluations/<run-id>.json
checkpoints/<run-id>.json
subject-envelopes/<run-id>.json  # presente quando a materialização foi alcançada
execution/jobs/<job-id>.json
execution/attempts/<job-id>.json
artifact-manifest.json
checksums.json
```

`bundle.json` declara `schema_version=3`, `kind=run`, `profile=audit`,
`artifact_content=references_only`, `portable=false` e `replayable=false`. Grade, quando usada por
compatibilidade, continua uma projeção e não é a fonte canônica da avaliação.

# Verificação isolada

O verificador não consulta o SQLite original. Além de checksums e lista completa de membros, ele
revalida todos os contracts, RunSpec, AdmissionRecord, RunRecord, ledger e EvaluationRecords. O
SubjectEnvelope é reconstruído pelo schema fechado, tem o digest recalculado e precisa corresponder
ao RunSpec, ao inventário admitido e ao digest de `subject.invoked`. Se a Run falhou antes da
materialização, o membro pode estar ausente somente quando não existem `context.composed`,
`capability.offered`, `subject.invoked` ou `subject.responded`.

O artifact manifest precisa corresponder exatamente às refs intencionais: `scenario_input`,
`subject_input_materialized`, `tool_arguments`, `tool_result`, `run_output` e eventuais artifacts de
checkpoints. Nenhum membro extra — mesmo coberto por checksum — ou artifact omitido é aceito. O
bundle preserva somente refs; ele não promete blob, grant, restore ou replay.

Job e attempts também têm seus digests verificados. Attempts devem possuir ordinais e gerações
monotônicos, pertencer ao job e não representar duas tentativas canonicamente ativas na mesma
geração. Timestamps de lease, heartbeat, expiração e término também precisam ser coerentes. O job
precisa pertencer à Run exportada. O ledger exige que cada `tool.called` use capability oferecida e
tenha exatamente um `tool.completed`, `tool.denied` ou `tool.failed`.

# Compatibilidade

Bundles v1 e v2 continuam com exportadores e verificadores próprios. Comparison pela API e CLI segue
em v2. Export por Run usa v3. O v2 continua declarando honestamente que não contém o documento exato
do SubjectEnvelope e, portanto, não recomputa seu digest.
