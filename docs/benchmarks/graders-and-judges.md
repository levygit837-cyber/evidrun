---
id: benchmark-graders-judges
type: protocol
title: Graders e judges
status: accepted
authority: normative
volatility: timeless
owner: evals
created_at: 2026-07-22
updated_at: 2026-07-22
applies_to: evaluations
sources: []
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun/evaluations
verification_refs: []
---

# Graders e judges

Graders determinísticos têm precedência. Judges baseados em modelo são secundários, versionados,
cegos ao nome da variant quando possível e calibrados com casos conhecidos. Prompt, rubric, modelo,
parâmetros, custo e incerteza do judge fazem parte da evidência.

Um judge nunca pode transformar evidence mode observacional em causal.

