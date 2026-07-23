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
  - src/evidrun/evidence/bundle.py
verification_refs:
  - tests/integration/test_contract_api.py
  - tests/acceptance/test_demo_flow.py
---

# Conteúdo

Evidence Bundle v2 adiciona à portabilidade do v1:

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
report.md
checksums.json
```

O verificador confirma SHA-256 de arquivos, event chains, contract digests, RunSpec digests,
AdmissionRecord digests, EvaluationRecord digests e checkpoint hashes. Boundaries de evaluation e
checkpoint são validadas contra o ledger antes da persistência.

Bundle v1 continua verificável e pode ser exportado pela opção explícita de compatibilidade. Exports
novos da API e CLI usam v2. Nenhum bundle inclui valor de credencial ou secret binding resolvido.
