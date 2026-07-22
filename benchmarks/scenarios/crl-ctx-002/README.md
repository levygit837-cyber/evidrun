---
id: benchmark-crl-ctx-002
type: protocol
title: CRL-CTX-002 — Causa-raiz no final do log
status: implemented
authority: normative
owner: core
created_at: 2026-07-22
updated_at: 2026-07-22
applies_to: benchmark/crl-ctx-002@1
sources: []
supersedes: []
superseded_by: null
implementation_refs:
  - benchmarks/scenarios/crl-ctx-002/scenario.yaml
  - src/evidrun/subject_runners/scripted.py
verification_refs:
  - tests/acceptance/test_demo_flow.py
---

# CRL-CTX-002 — Causa-raiz no final do log

Este cenário verifica o pipeline Evidrun com uma mudança controlada de `context_policy`.

O baseline preserva o início do arquivo e omite o marcador decisivo. O candidate preserva o final.
O grader exige que a causa apareça tanto na resposta quanto na evidência citada.

O resultado não mede capacidade de modelo: o subject runner é intencionalmente determinístico.

