---
id: benchmark-scenario-authoring
type: protocol
title: Autoria de cenários
status: accepted
authority: normative
volatility: timeless
owner: evals
created_at: 2026-07-22
updated_at: 2026-07-22
applies_to: benchmarks/scenarios
sources: []
supersedes: []
superseded_by: null
implementation_refs:
  - benchmarks/scenarios/crl-ctx-002
verification_refs: []
---

# Autoria de cenários

Cada cenário possui ID estável, revision, objetivo, fixture, condições observáveis, grader e
limitações. Fixtures precisam ser determinísticas quando usadas no CI. Hidden fixtures e respostas
não são montadas no contexto do Subject Agent.

Mudança material em fixture ou grader cria nova revision. O README do cenário explica o que ele
mede e, principalmente, o que não mede.

