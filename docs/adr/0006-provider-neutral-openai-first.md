---
id: adr-0006
type: adr
title: Núcleo neutro com OpenAI primeiro
status: accepted
authority: normative
owner: agents
created_at: 2026-07-22
updated_at: 2026-07-22
applies_to: agents
sources:
  - https://openai.github.io/openai-agents-python/
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun/shared/ports.py
verification_refs: []
---

# Decisão

Tipos de provider ficam em adapters. Lab Agent usará Pydantic AI inicialmente. O primeiro Subject
Runner real usará Responses diretamente; Agents SDK será adapter adicional.

# Consequências

O benchmark inicial não depende de provider. Paridade multiprovider não será simulada antes do
segundo adapter real.

