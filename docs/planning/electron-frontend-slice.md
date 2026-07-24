---
id: planning-electron-frontend-slice
type: planning
title: Fatia multipágina do frontend Electron
status: implemented
authority: planning
owner: product-engineering
created_at: 2026-07-24
updated_at: 2026-07-24
observed_at: 2026-07-24
review_due: 2026-07-31
applies_to: electron-frontend-slice
sources:
  - docs/architecture/desktop-runtime.md
  - docs/planning/mvp-capability-map.md
  - docs/research/aidesigner-ultradesign-integration.md
supersedes: []
superseded_by: null
implementation_refs:
  - apps/web/src/app/AppShell.tsx
  - apps/web/src/app/router.tsx
  - apps/web/src/data/adapters.ts
  - apps/web/src/features/laboratory/LaboratoryPage.tsx
  - apps/web/src/features/create/CreatePage.tsx
  - apps/web/src/features/observability/ObservabilityPage.tsx
verification_refs:
  - apps/web/src/app/router.test.ts
  - apps/web/src/features/laboratory/LaboratoryPage.test.tsx
  - apps/web/src/features/create/CreatePage.test.tsx
  - apps/web/src/features/observability/ObservabilityPage.test.tsx
---

# Fatia multipágina do frontend Electron

Este documento registra a implementação observada na branch `task/electron-frontend`. Ele não
promove essa branch a `main`, não amplia contratos Python e não declara o MVP operacional encerrado.

## Comportamento implementado

- shell compartilhado com as rotas hash `/laboratory`, `/create` e `/observability`;
- renderer isolado de Electron, Node e bindings nativos;
- conexão com o sidecar encapsulada por provider, cliente e adapters compartilhados;
- Laboratory como demonstração local determinística, persistentemente identificada como `Demo`;
- Create com draft local navegável e corredor conectado limitado ao bootstrap da fixture canônica
  `CRL-CTX-002`;
- Observability conectada aos endpoints atuais para Runs, events, evaluations, checkpoints e Bundle
  v3, com lista/detalhe responsivos;
- Bundle v3 descrito como `references_only`, `portable=false` e `replayable=false`;
- fontes e ícones empacotados localmente, sem dependência de CDN no renderer.

## Fronteiras explícitas

Laboratory não usa Lab Agent, provider ou histórico real. Seus eventos de mensagem e atividade vêm
do `DemoLaboratoryAdapter` e existem apenas durante a sessão atual.

O draft da página Create não é enviado ao endpoint de bootstrap. A ação conectada executa o pacote
canônico `CRL-CTX-002`, que é uma `repository_fixture` não humana. A interface não cria Study,
RunSpec, AdmissionRecord ou autoridade humana a partir dos campos locais.

Observability projeta somente records retornados pelo backend. `ArtifactRef` preserva identidade,
mas não concede acesso ao conteúdo. A janela forense é um filtro read-only por sequência e não
oferece replay, restore, simulation ou rewind executável.

## Fora desta fatia

- Lab Agent real e streaming de chat do backend;
- autoria canônica completa, acceptance humana e artifact ingest/access;
- runtime multi-turn, checkpoint coordinator e Progress Artifact observer;
- replay, restore, fork ou bundles portáteis;
- worker supervisionado pelo frontend;
- sidecar Python distribuível, DMG, assinatura e notarização.

O fechamento dessas capabilities continua dependente dos workstreams do roadmap executável. A
existência desta interface não transforma integrações pendentes em comportamento disponível.
