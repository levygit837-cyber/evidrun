---
id: adr-0003
type: adr
title: Monólito modular por capacidade
status: accepted
authority: normative
owner: core
created_at: 2026-07-22
updated_at: 2026-07-22
applies_to: repository
sources: []
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun
verification_refs: []
---

# Decisão

Um pacote Python organizado por capacidades, uma API, um worker e uma CLI. Não usar microserviços,
Redis, Kafka ou Kubernetes no MVP.

# Consequências

Menor working set e transações locais simples. Processos podem ser separados sem distribuir o domínio.

