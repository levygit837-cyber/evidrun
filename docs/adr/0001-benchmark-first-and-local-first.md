---
id: adr-0001
type: adr
title: Benchmark-first e local-first
status: accepted
authority: normative
volatility: timeless
owner: core
created_at: 2026-07-22
updated_at: 2026-07-22
applies_to: product
sources:
  - obsidian:context-reliability-lab/adr-0001
supersedes: []
superseded_by: null
implementation_refs:
  - benchmarks
  - src/evidrun
verification_refs:
  - tests/acceptance/test_demo_flow.py
---

# Contexto

Hipóteses de contexto precisam ser testadas com baixo atrito e sem entregar raw a um serviço remoto.

# Decisão

O produto começa por benchmarks auditáveis e armazenamento local. Cloud e sync são adapters futuros.

# Consequências

SQLite, artifacts locais e execução offline são defaults. Resultado negativo continua preservado.

