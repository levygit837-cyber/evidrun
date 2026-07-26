---
id: adr-0002
type: adr
title: Separar Control Plane e Execution Plane
status: accepted
authority: normative
owner: core
created_at: 2026-07-22
updated_at: 2026-07-26
applies_to: architecture
sources: []
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun/contracts/runtime/envelope.py
  - src/evidrun/contracts/compiler.py
verification_refs: []
---

# Decisão

Lab Agent pertence ao Control Plane; Subject Agent pertence ao Execution Plane. O Subject não recebe
chats, hidden graders ou resultados de outras variants. Serviços determinísticos controlam estado,
autoridade e evidência.

# Consequências

Não existe um “agente mestre” com acesso implícito a tudo. Context mounts são explícitos e auditáveis.

