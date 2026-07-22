---
id: adr-0007
type: adr
title: Repositório como fonte normativa da documentação
status: accepted
authority: normative
owner: core
created_at: 2026-07-22
updated_at: 2026-07-22
applies_to: docs
sources:
  - obsidian:40.ideas/products/context-reliability-lab
supersedes: []
superseded_by: null
implementation_refs:
  - docs
  - scripts/validate_docs.py
verification_refs:
  - docs/_generated/manifest.json
---

# Decisão

Contratos, ADRs e arquitetura atual ficam no Git. Obsidian mantém MOC, pesquisa e incubação, sem
espelhar documentos normativos.

# Consequências

Frontmatter é validado; manifest é gerado; research expira; ADRs são superseded e não reescritos.

