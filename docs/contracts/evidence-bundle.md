---
id: contract-evidence-bundle-v1
type: contract
title: Evidence Bundle v1
status: implemented
authority: normative
owner: core
created_at: 2026-07-22
updated_at: 2026-07-25
applies_to: schema/evidence-bundle@1
sources: []
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun/evidence/export/comparison_v1.py
  - src/evidrun/evidence/archive.py
verification_refs:
  - tests/acceptance/test_demo_flow.py
---

# Evidence Bundle v1

ZIP auditável contendo:

```text
manifest.json
comparison.json
grades.json
report.md
events/<run-id>.jsonl
checksums.json
```

O verificador confirma SHA-256 de cada arquivo e reconstrói cada event chain. Bundles exportados
saem da gestão de retenção do aplicativo; o usuário deve ser informado antes da exportação de dados
sensíveis.

Este formato permanece exportável e verificável para compatibilidade. A exportação padrão nova usa
[Evidence Bundle v2](evidence-bundle-v2.md); v2 não reinterpreta nem invalida bundles v1.
Conforme o [ADR 0011](../adr/0011-progress-artifacts-and-bundle-boundaries.md), exportável não
significa portátil com todos os blobs nem replayable.
