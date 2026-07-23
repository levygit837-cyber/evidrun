---
id: architecture-agents-authority
type: architecture
title: Agentes e autoridade
status: accepted
authority: normative
owner: core
created_at: 2026-07-22
updated_at: 2026-07-23
applies_to: agents
sources: []
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun/shared/ports.py
  - src/evidrun/contracts/compiler.py
verification_refs:
  - tests/unit/test_contracts.py
---

# Agentes e autoridade

## Lab Agent

Pode ler evidências autorizadas, explicar runs e criar drafts. Decisões de revision aceitas pelo
registry exigem `actor_type=human`. O Lab Agent não aceita a própria proposta, não acessa raw sem
grant, não exclui dados e não executa efeitos externos sem decisão humana.

## Subject Agent

Recebe somente o `SubjectEnvelope`: Goal, inputs visíveis, protocolo visível, capabilities
efetivamente admitidas, workspace, budgets e stop conditions. Não recebe StudyIntent, hipótese do
laboratório, chats, hidden graders, calibration, credenciais ou resultados de outras variants.

Tools e skills requeridas ficam no Agent Inventory; a admissão registra separadamente o que foi
resolvido. Capability opcional ausente não entra no envelope. Inventário não prova uso: o uso depende
dos eventos de lifecycle. O runtime real de tools, skills e nested agents ainda não existe.

## Serviços determinísticos

Montagem de contexto, autorização, estado da run, retenção, event ledger e ordem dos graders não são
delegados a agentes. São serviços verificáveis.
