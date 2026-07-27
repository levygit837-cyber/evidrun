---
id: product-charter
type: charter
title: Charter do Evidrun
status: accepted
authority: normative
volatility: timeless
owner: product
created_at: 2026-07-22
updated_at: 2026-07-26
applies_to: product
sources:
  - obsidian:40.ideas/products/context-reliability-lab
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
- memória global automática, no sentido de contexto persistido sem escopo de Workspace, sem
  proveniência ou promovido sem decisão humana. O [ADR 0019](../adr/0019-lab-agent-operational-memory.md)
  define o que substitui esse não-objetivo: memória operacional por Workspace, com proveniência e
  promoção humana;
- substituir frameworks de agentes existentes.

