---
id: docs-index
type: architecture
title: Índice da documentação Evidrun
status: implemented
authority: normative
owner: core
created_at: 2026-07-22
updated_at: 2026-07-22
applies_to: repository
sources: []
supersedes: []
superseded_by: null
implementation_refs:
  - scripts/validate_docs.py
verification_refs:
  - docs/_generated/manifest.json
---

# Documentação Evidrun

## Leitura inicial

1. [Charter](product/charter.md)
2. [Glossário](product/glossary.md)
3. [Arquitetura do sistema](architecture/system.md)
4. [Agentes e autoridade](architecture/agents-and-authority.md)
5. [Dados e evidência](architecture/data-and-evidence.md)
6. [Protocolo de benchmarks](benchmarks/protocol.md)
7. [Roadmap](roadmap/mvp.md)

## Autoridade

Contratos e ADRs aceitos são normativos. Arquitetura descreve o estado atual. Research é temporal.
Roadmap é intenção futura. Relatórios são projeções geradas de evidência e não são mantidos à mão.

O manifest completo é gerado em `_generated/manifest.json` a partir do frontmatter dos documentos.

