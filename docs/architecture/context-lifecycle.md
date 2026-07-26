---
id: architecture-context-lifecycle
type: architecture
title: Lifecycle do contexto
status: implemented
authority: normative
volatility: current
owner: core
created_at: 2026-07-22
updated_at: 2026-07-22
applies_to: contexts
sources: []
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun/contexts/engine.py
verification_refs:
  - tests/unit/test_context.py
---

# Lifecycle do contexto

1. A revision fixa uma `ContextPolicy`.
2. O composer recebe candidatos e budget.
3. Um `ContextPlan` registra regras, seleção e omissões.
4. O conteúdo entregue vira `ContextSnapshot` com hash.
5. A resposta e a grade referenciam o snapshot.
6. Comparações produzem `ContextDiff`.

O benchmark inicial implementa policies `head`, `tail` e `full`. Seleção semântica, sumarização e
retrieval serão adicionados como novas revisions, não como comportamento implícito.
