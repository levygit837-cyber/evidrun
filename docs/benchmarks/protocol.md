---
id: benchmark-protocol-v1
type: protocol
title: Protocolo de benchmarks e evals
status: accepted
authority: normative
volatility: timeless
owner: evals
created_at: 2026-07-22
updated_at: 2026-07-22
applies_to: benchmarks
sources:
  - obsidian:context-reliability-lab/protocolo
supersedes: []
superseded_by: null
implementation_refs:
  - benchmarks
verification_refs:
  - tests/acceptance/test_demo_flow.py
---

# Protocolo de benchmarks e evals

Uma comparação declara hipótese, variável primária, baseline, candidate, scenarios, repetições,
budgets, graders e stop conditions.

Hierarquia:

1. integridade estrutural;
2. integridade da evidência;
3. graders determinísticos;
4. métricas e constraints;
5. revisão humana;
6. LLM judge opcional;
7. interpretação.

Modos: `prospective_controlled`, `counterfactual_replay` e `retrospective_observational`.
Somente o primeiro, com variável isolada, sustenta linguagem causal limitada. Trade-offs de custo,
latência e constraints nunca são escondidos em um score único.

