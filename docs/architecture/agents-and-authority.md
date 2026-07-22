---
id: architecture-agents-authority
type: architecture
title: Agentes e autoridade
status: accepted
authority: normative
owner: core
created_at: 2026-07-22
updated_at: 2026-07-22
applies_to: agents
sources: []
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun/shared/ports.py
verification_refs: []
---

# Agentes e autoridade

## Lab Agent

Pode ler evidências autorizadas, explicar runs e criar drafts. Não aceita a própria proposta, não
acessa raw sem grant, não exclui dados e não executa efeitos externos sem decisão humana.

## Subject Agent

Recebe somente o manifest compilado, contexto da variant, tools permitidas, ambiente, budgets e
stop conditions. Não recebe chats do laboratório, hidden graders ou resultados de outras variants.

## Serviços determinísticos

Montagem de contexto, autorização, estado da run, retenção, event ledger e ordem dos graders não são
delegados a agentes. São serviços verificáveis.

