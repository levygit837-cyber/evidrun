---
id: product-pipeline-language
type: contract
title: Linguagem do pipeline de Study até Evidence
status: implemented
authority: normative
volatility: current
owner: product
created_at: 2026-07-31
updated_at: 2026-07-31
applies_to: product-language
sources:
  - docs/adr/0009-study-run-contract-composition.md
  - docs/adr/0023-natural-product-language-over-stable-contracts.md
  - docs/product/glossary.md
supersedes: []
superseded_by: null
implementation_refs:
  - CONTEXT.md
  - apps/web/src/app/AppShell.tsx
  - apps/web/src/features/create/CreatePage.tsx
  - apps/web/src/features/create/CreateStages.tsx
  - apps/web/src/features/observability/RunDetailPanel.tsx
  - apps/web/src/productLanguage.ts
verification_refs:
  - apps/web/src/productLanguage.test.ts
  - apps/web/src/features/create/CreatePage.test.tsx
  - apps/web/src/features/observability/ObservabilityPage.test.tsx
  - apps/web/src/features/observability/RunDetailPanel.test.tsx
---

# Objetivo

Uma pessoa deve conseguir explicar o caminho completo sem conhecer nomes de classes. Os nomes
exibidos permanecem em inglês; a prosa normativa permanece em português. Quando um nome de produto
difere do contrato, o identificador técnico aparece como referência secundária e nunca muda o
significado persistido.

# Pipeline

```text
Question or hypothesis
  → Study
  → Study Design
  → accepted or explicitly unverified Study Version
  → Execution Plan
  → Readiness Check
      blocked ──→ volta ao Study Design; nenhuma Run existe
      ready   ──→ Run
  → Evaluation
  → Comparison
  → Audit Evidence Bundle
```

O pipeline possui três separações que a interface sempre preserva:

- **Execution Plan** diz exatamente o que deverá acontecer;
- **Readiness Check** diz se esse plano pode acontecer com as capabilities atuais;
- **Run** registra a tentativa que efetivamente aconteceu.

Autoridade humana, lifecycle e qualidade são eixos independentes. Uma Run pode usar revisions sem
confirmação humana e ainda passar pelo Readiness Check técnico; uma Run concluída pode receber uma
Evaluation negativa; e uma Evaluation não reescreve a Run.

# Inventário e matriz de nomes

A decisão canônica é comum a toda a matriz: manter o nome técnico v1 nas superfícies persistidas e
usar o nome de produto como alias explícito na experiência humana. Nenhuma linha autoriza rename de
schema, campo ou record.

| Nome técnico atual | Nome de produto | Conceito e propósito | Problema evitado | Lifecycle e autoridade | Entrada → saída | Superfícies |
| --- | --- | --- | --- | --- | --- | --- |
| ideia, pergunta, hipótese | `Question or hypothesis` | ponto ainda informal da investigação | não chamar rascunho de Study aceito | sem record ou autoridade implícita | conversa → draft | Laboratory, Study Builder |
| `StudyIntent` | `Study Purpose` | por que investigar, perguntas e decisão informada | não confundir intenção do laboratório com prompt | revision de autoria; humano aceita ou execução declara trust não verificado | pergunta → propósito versionado | Study Builder, review |
| `StudyRevision` | `Study Version` | raiz versionada que referencia o desenho completo | “revision” deixa de parecer revisão textual | imutável; decisão append-only | módulos → raiz compilável | review, API, CLI |
| `GoalRevision` | `Agent Task` | objetivo e limites entregues ao Subject Agent | separar a tarefa da hipótese e da avaliação | revision de autoria | propósito → tarefa visível | Study Builder, Subject Context |
| `ScenarioRevision` | `Scenario` | inputs, condições, limitações e provenance | não chamar de test case com pass/fail implícito | revision de autoria | artifacts e condições → cenário | Study Builder, review |
| `VariantSpec` | `Variant` | override tipado comparado com variants irmãs | não confundir com versão histórica | parte do Study antes da Run | blueprint → diferença controlada | Study Builder, Comparison |
| `AgentInventoryRevision` | `Agent Setup` | requisitos de provider, runner, tools e skills | distinguir requisito de capability resolvida | revision de autoria | requisitos → inventário solicitado | review, Readiness Check |
| `WorkspaceTemplateRevision` | `Run Environment` | ambiente efêmero de uma Run | não confundir com Workspace durável do Control Plane | revision de autoria, materializada após prontidão | configuração → ambiente admitido | review, Run detail |
| `InteractionProtocolRevision` | `Interaction Protocol` | forma e limites da interação | não usar “rules” para protocolo | revision de autoria | passos permitidos → protocolo | Study Builder, review |
| `EvaluationPlanRevision` | `Evaluation Plan` | dimensões, stages, gates e disclosure | separar critérios da tarefa e do resultado | revision de autoria | critérios → plano | Study Builder, Evaluation |
| policies | nome específico da policy | seleção, captura ou disclosure | impedir que “rules” esconda tipos diferentes | revision tipada | decisão de configuração → policy | Study Builder, review |
| budgets | `Resource Limits` | limites de tempo, tools, tokens ou custo | distinguir limite operacional de critério de qualidade | parte do Execution Plan | limites → gate de prontidão/runtime | review, Run detail |
| stop conditions | `Stop Conditions` | razões declaradas para encerrar | separar término de achievement ou pass/fail | parte do Execution Plan | condição → terminal factual | review, Run detail |
| compilação | `Build Execution Plans` | expansão determinística de scenarios, variants e repetitions | não sugerir que compilar executa | operação pura, sem criar Run | Study Version → Execution Plans | Study Builder, CLI |
| `RunSpec` | `Execution Plan` | configuração atômica, exata e imutável | distinguir plano de execução realizada | imutável e anterior à Run | Study Version → plano | Study Builder, review, Run detail |
| `AdmissionRecord` | `Readiness Check` | capabilities e compatibilidade técnica efetivas | não confundir com aprovação humana | decisão técnica pré-fila | Execution Plan → ready ou blocked | Study Builder, Run detail |
| `RunRecord` / `Run` | `Run` | uma tentativa factual ligada ao plano e prontidão exatos | não confundir com job, retry ou resultado | nasce somente após readiness `admitted` | plano pronto → Run | Runs, Run detail |
| `RunEvent` | `Run Event` | observação factual append-only | não chamar ledger de log descartável | append-only por fase | fato → ledger | Trace, bundle |
| `EvaluationRecord` | `Recorded Evaluation` | avaliação vetorial ancorada à Run | não confundir avaliação com conclusão do lifecycle | append-only; correção cria outro record | Run + evidence → evaluation | Evaluation, bundle |
| `Comparison` | `Comparison` | leitura pareada de Runs e trade-offs | não prometer ranking universal | projeção derivada | Runs → comparação | API, bundle |
| `Evidence Bundle audit` | `Audit Evidence Bundle` | pacote verificável de records, refs e digests | não prometer blobs, replay ou portabilidade | export imutável verificável | records → bundle | Evidence, CLI |

# O que “rules” significa

`Rules` não é um conceito canônico isolado. A interface usa sempre a categoria exata:

- `Agent Task` para objetivo e limites semânticos do Subject;
- `Scenario Conditions` para condições observáveis;
- `Evaluation Criteria` para qualidade e gates;
- `Policies` pelo nome específico para seleção, captura ou disclosure;
- `Resource Limits` para budgets;
- `Stop Conditions` para término.

# Cenários de validação

## Uma Run simples

Um Study com um Scenario, uma Variant e uma repetição gera um Execution Plan. O Readiness Check
resolve as capabilities e retorna `Ready`; somente então uma Run nasce. A pessoa consegue apontar o
plano, a checagem e a tentativa como três objetos diferentes.

## Matriz de variants

Um Study com dois Scenarios, duas Variants e uma repetição gera quatro Execution Plans. Continuamos
com um Study, quatro planos e, após readiness individual, até quatro Runs. Variant não significa nova
Study Version e compilação não significa execução.

## Readiness bloqueada

Um Execution Plan solicita disclosure `pre_run`, que o runtime atual não suporta. O Readiness Check
mostra `Blocked`, explica a capability ausente e não cria Run. Isso não é rejeição humana nem
Evaluation negativa.

## Evaluation posterior

Uma Run termina e preserva seus Run Events. Uma Evaluation posterior cria um record append-only
ancorado nessa boundary. Resultado negativo, adjudicação futura ou correção não alteram o lifecycle
nem sobrescrevem a Run ou avaliações anteriores.

# Compatibilidade

| Superfície | Decisão atual |
| --- | --- |
| UI | usa os nomes de produto em inglês e explicações contextuais |
| rotas | `/create`, `/laboratory` e `/observability` permanecem estáveis |
| API e CLI | comandos, endpoints, campos e payloads v1 permanecem estáveis; help pode mostrar o nome de produto junto ao técnico |
| schemas e eventos | nomes e versões permanecem estáveis |
| banco e ledger | tabelas, IDs, digests e records permanecem estáveis |
| bundles | paths internos e verificadores permanecem estáveis |
| migração futura | qualquer rename persistido exige ADR sucessor, versão nova, expand-contract e testes de leitura dos artefatos anteriores |
