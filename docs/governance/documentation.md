---
id: governance-documentation
type: governance
title: Governança documental
status: implemented
authority: normative
owner: core
created_at: 2026-07-22
updated_at: 2026-07-22
applies_to: docs
sources: []
supersedes: []
superseded_by: null
implementation_refs:
  - scripts/validate_docs.py
verification_refs:
  - docs/_generated/manifest.json
---

# Governança documental

Frontmatter é canônico; manifest e índices são gerados. IDs são únicos. ADR aceito é superseded,
não reescrito. Research usa `observed_at` e `review_due`. Roadmap não descreve comportamento atual.

`implemented` exige `implementation_refs`. `verified` exige também `verification_refs`. Referências
devem apontar para paths existentes. CI executa o validador documental e falha em divergências.

Documentos são escritos em português brasileiro; IDs, rotas, schemas e filenames permanecem em
inglês ASCII estável.

