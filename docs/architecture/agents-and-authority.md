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

O contrato e o registry rejeitam qualquer `actor_type` diferente de `human`, mas a API loopback
atual ainda não autentica um principal ou role humano separado: um caller autorizado informa
`actor_id` e o servidor constrói o record humano. Enquanto o Lab Agent não existe, isso é uma
fronteira operacional; antes de dar a ele acesso à API de decisão, um mecanismo de autoridade deve
impedir que a simples posse do launch token seja interpretada como prova de ação humana.

O bootstrap de compatibilidade do `CRL-CTX-002` é uma exceção limitada: ele materializa a aceitação
preexistente de um benchmark versionado no repositório. Essa migração não se aplica a contracts
externos ou a propostas criadas pelo Lab Agent.

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
