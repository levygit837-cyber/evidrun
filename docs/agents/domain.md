---
id: agents-domain-docs
type: guide
title: Consumo de documentos de domínio pelas agent skills
status: accepted
authority: informative
volatility: timeless
owner: core
created_at: 2026-07-23
updated_at: 2026-07-23
applies_to: repository
sources: []
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
---

# Documentos de domínio

Como as skills de engenharia devem consumir a documentação de domínio deste repositório ao explorar a base de código.

Layout: **single-context**.

## Antes de explorar, leia estes itens

- **`CONTEXT.md`** na raiz do repositório.
- **`docs/adr/`** — leia os ADRs relacionados à área em que você está prestes a trabalhar.
- **`docs/index.md`** — fonte de verdade deste repositório (ver `AGENTS.md`); leia antes de alterar contratos ou arquitetura.

Se algum desses arquivos não existir, **prossiga silenciosamente**. Não sinalize sua ausência nem sugira criá-lo antecipadamente. A skill `/domain-modeling` (alcançada por `/grill-with-docs` e `/improve-codebase-architecture`) os cria de forma lazy quando termos ou decisões são realmente resolvidos.

## Estrutura de arquivos

Repositório single-context:

```
/
├── CONTEXT.md
├── docs/adr/
│   ├── 0001-benchmark-first-and-local-first.md
│   └── ...
└── src/
```

## Use o vocabulário do glossário

Quando sua saída nomear um conceito de domínio (no título de uma issue, em uma proposta de refatoração, uma hipótese ou um nome de teste), use o termo conforme definido em `CONTEXT.md`. Não derive para sinônimos que o glossário evita explicitamente.

Se o conceito necessário ainda não estiver no glossário, isso é um sinal — ou você está inventando uma linguagem que o projeto não usa (reconsidere), ou existe uma lacuna real (registre-a para `/domain-modeling`).

## Sinalize conflitos com ADRs

Se sua saída contradisser um ADR existente, revele isso explicitamente em vez de sobrescrevê-lo silenciosamente:

> _Contradiz o ADR-0010 (autoridade humana verificável) — mas vale reabri-lo porque…_
