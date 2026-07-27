---
id: product-charter
type: charter
title: Charter do Evidrun
status: accepted
authority: normative
volatility: timeless
owner: product
created_at: 2026-07-22
updated_at: 2026-07-27
applies_to: product
sources:
  - obsidian:40.ideas/products/context-reliability-lab
  - docs/adr/0021-hierarchical-lab-agent-scope.md
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
---

# Charter do Evidrun

## Problema

Mudanças de prompt, contexto, memória e ferramentas são frequentemente justificadas por intuição
ou exemplos isolados. Sem controlar variáveis e preservar evidência, não é possível saber se houve
melhoria, qual mudança causou o efeito ou se o resultado se mantém.

## Proposta

O Evidrun transforma hipóteses sobre agentes em experimentos versionados, runs auditáveis,
comparações e relatórios que deixam ganhos, perdas e incerteza visíveis.

## Princípios

- benchmark-first;
- local-first;
- evidência antes de narrativa;
- uma variável primária por comparação causal;
- graders determinísticos antes de judges;
- contexto entregue é um objeto verificável;
- resultado negativo é informação útil;
- nenhuma dependência de chain-of-thought privado;
- humano mantém autoridade sobre aceitação, acesso sensível e efeitos externos.

## Público inicial

Desenvolvedores e pesquisadores que desejam avaliar suas próprias hipóteses de contexto e agents em
um ambiente local, inspecionável e reproduzível.

## Não objetivos iniciais

- plataforma SaaS multi-tenant;
- marketplace de prompts;
- ranking universal de modelos;
- execução irrestrita de shell;
- memória global automática, no sentido de contexto persistido sem isolamento de Workspace,
  subescopo de Project quando aplicável, proveniência ou promoção humana. O
  [ADR 0021](../adr/0021-hierarchical-lab-agent-scope.md) define o que substitui esse não-objetivo:
  memória operacional hierárquica, com proveniência e promoção humana;
- substituir frameworks de agentes existentes.
