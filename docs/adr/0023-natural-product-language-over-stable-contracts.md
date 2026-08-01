---
id: adr-0023
type: adr
title: Linguagem de produto natural sobre contratos estáveis
status: accepted
authority: normative
volatility: timeless
owner: product
created_at: 2026-07-31
updated_at: 2026-07-31
applies_to: product-language
sources:
  - docs/adr/0009-study-run-contract-composition.md
  - docs/contracts/study-run-v1.md
supersedes: []
superseded_by: null
implementation_refs:
  - CONTEXT.md
  - apps/web/src/productLanguage.ts
  - docs/product/glossary.md
  - docs/product/pipeline-language.md
verification_refs:
  - apps/web/src/productLanguage.test.ts
  - apps/web/src/features/create/CreatePage.test.tsx
  - apps/web/src/features/observability/ObservabilityPage.test.tsx
---

# Contexto

Os contratos v1 distinguem corretamente autoria, compilação, prontidão técnica, execução, avaliação
e evidência, mas seus nomes internos não formam sozinhos uma narrativa de produto. A interface
misturava `Study`, `RunSpecs`, `Admission` e `Runs` sem explicar o que existe em cada etapa, fazendo
objetos diferentes parecerem sinônimos.

# Decisão

A interface usa nomes de produto naturais **em inglês** e mantém o identificador técnico como
referência secundária quando auditoria, suporte ou interoperabilidade precisarem dele. O funil
principal é:

```text
Study Design → Execution Plans → Readiness Check → Runs → Evaluation → Evidence
```

`Study Purpose` descreve por que o laboratório investiga; `Agent Task` descreve o que chega ao
Subject Agent. `Execution Plan` é a forma visível de `RunSpec`; `Readiness Check` é a forma visível de
`AdmissionRecord`; e `Run` continua sendo a tentativa factual. Esses três conceitos nunca são
colapsados.

Os identificadores de classes, campos, schemas, endpoints, comandos, eventos, tabelas e documentos
persistidos v1 não são renomeados. Rotas também permanecem estáveis. A camada de nomes é explícita e
centralizada, não uma coleção de traduções ocasionais.

`Readiness Check` significa somente compatibilidade técnica e disponibilidade de capabilities. Não
significa aprovação, aceitação humana, trust verificado, qualidade ou sucesso. Da mesma forma,
`Evaluation` não altera o lifecycle da Run, e `Evidence` não promete portabilidade ou replay.

# Alternativas consideradas

## Renomear o domínio canônico e os contratos v1

Rejeitada nesta decisão. A migração quebraria ou versionaria API, CLI, schemas, eventos, banco e
bundles sem ser necessária para tornar o fluxo compreensível. Uma futura renomeação persistida exige
ADR sucessor, versão nova e estratégia expand-contract.

## Manter os nomes internos como únicos rótulos da interface

Rejeitada. Tooltips e documentação não resolvem uma sequência cuja leitura primária continua
ambígua.

## Traduzir os nomes exibidos para português

Rejeitada por direção de produto. A documentação normativa permanece em português, mas os nomes das
visualizações e conceitos exibidos permanecem em inglês.

# Consequências

A UI pode evoluir sua explicação sem reescrever records históricos. Testes de linguagem protegem a
distinção entre plano, prontidão e Run e a estabilidade das rotas e chaves machine-readable. Código
e documentação que introduzam outro rótulo para esses conceitos devem atualizar primeiro o mapa
normativo de linguagem.
