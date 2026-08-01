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
  → Study Version + exact revision set
  → Seal Execution Revision Set
  → Build Execution Plans
  → Execution Plan
      authority axis
        complete accepted human coverage ──→ verified_revision_set
        incomplete/no accepted coverage ───→ unverified_revision_set
  → Record Execution Trust for the exact Execution Plan
  → Readiness Check
      ready ─────────────────────────→ Run
      blocked by design/setup ───────→ edit Study Design or Agent Setup; check again
      check failed/unavailable ──────→ recover dependency or inventory; check again
  → Evaluation
  → Comparison
  → Audit Evidence Bundle
```

`verified_revision_set` e `unverified_revision_set` são kinds do `ExecutionTrustRecord` persistido
para o conjunto exato de revisions e para o Execution Plan já compilado. Não são estados da Study Version.
O primeiro exige decisions `accepted` de autoridade humana verificada para toda a closure; o segundo
declara somente a ausência dessa cobertura completa. Ambos permanecem separados do Readiness Check.

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
| ideia, pergunta, hipótese | `Question or hypothesis` | ponto ainda informal da investigação | não chamar rascunho de Study aceito | sem record e sem autoridade implícita | conversa → draft | Laboratory, Study Builder |
| `Study` | `Study` | raiz de autoria que reúne a investigação | não confundir raiz lógica com uma versão aceita | draft/revisions; aceitação fica em decision separada | ideia → investigação estruturada | Laboratory, Study Builder, API |
| `StudyIntent` | `Study Purpose` | por que investigar, perguntas e decisão informada | não confundir intenção do laboratório com prompt | revision imutável; aceitação separada exige autoridade humana | pergunta → propósito versionado | Study Builder, review |
| `RevisionDecisionRecord` + `HumanAttestationRecord` | `Human Review Decision` | registra aceitação ou rejeição humana do conteúdo exato | não tratar campo de ator como prova de autoridade | append-only; somente autoridade humana verificada | revision + attestation → decision | review, API, CLI |
| `StudyRevision` | `Study Version` | raiz versionada que referencia o desenho completo | “revision” deixa de parecer revisão textual | imutável; decision e trust são records separados | módulos → raiz compilável | review, API, CLI |
| `GoalRevision` | `Agent Task` | objetivo e limites entregues ao Subject Agent | separar a tarefa da hipótese e da avaliação | revision imutável; aceitação humana é separada | propósito → tarefa visível | Study Builder, Subject Context |
| `ScenarioRevision` | `Scenario` | inputs, condições, limitações e provenance | não chamar de test case com pass/fail implícito | revision imutável; aceitação humana é separada | artifacts e condições → cenário | Study Builder, review |
| `VariantSpec` | `Variant` | override tipado comparado com variants irmãs | não confundir com versão histórica | parte imutável da Study Version; coberta pelo trust da closure | blueprint → diferença controlada | Study Builder, Comparison |
| `AgentInventoryRevision` | `Agent Setup` | requisitos de provider, runner, tools e skills | distinguir requisito de capability resolvida | revision imutável; aceitação humana é separada | requisitos → inventário solicitado | review, Readiness Check |
| `WorkspaceTemplateRevision` | `Run Environment` | ambiente efêmero de uma Run | não confundir com Workspace durável do Control Plane | revision imutável; materialização técnica após prontidão | configuração → ambiente admitido | review, Run detail |
| `InteractionProtocolRevision` | `Interaction Protocol` | forma e limites da interação | não usar “rules” para protocolo | revision imutável; aceitação humana é separada | passos permitidos → protocolo | Study Builder, review |
| `EvaluationPlanRevision` | `Evaluation Plan` | dimensões, stages, gates e disclosure | separar critérios da tarefa e do resultado | revision imutável; human stages exigem autoridade verificada | critérios → plano | Study Builder, Evaluation |
| policies | nome específico da policy | seleção, captura ou disclosure | impedir que “rules” esconda tipos diferentes | revision ou campo tipado; sem autoridade implícita | decisão de configuração → policy | Study Builder, review |
| budgets | `Resource Limits` | limites de tempo, tools, tokens ou custo | distinguir limite operacional de critério de qualidade | parte imutável do Execution Plan; sem autoridade própria | limites → gate de prontidão/runtime | review, Run detail |
| stop conditions | `Stop Conditions` | razões declaradas para encerrar | separar término de achievement ou pass/fail | parte imutável do Execution Plan; sem autoridade própria | condição → terminal factual | review, Run detail |
| compilação | `Build Execution Plans` | expansão determinística de scenarios, variants e repetitions | não sugerir que compilar executa | operação pura; não cria autoridade nem Run | Study Version selada → Execution Plans | Study Builder, CLI |
| `RunSpec` | `Execution Plan` | configuração atômica, exata e imutável | distinguir plano de execução realizada | imutável e anterior à Run; ligado ao trust exato | Study Version → plano | Study Builder, review, Run detail |
| `ExecutionTrustRecord` | `Execution Trust` | liga a closure selada ao RunSpec e declara confirmação humana verificada ou sua ausência | não transformar Study Version em “verificada” | imutável; kind verificado exige decisions humanas, não verificado pode ser criado pelo serviço | revision set + RunSpec digest → trust | review, Run detail, bundle |
| `AdmissionRecord` | `Readiness Check` | capabilities e compatibilidade técnica efetivas | não confundir com aprovação humana | decisão técnica pré-fila; não concede autoridade humana | Execution Plan → ready, blocked, failed ou unavailable | Study Builder, Run detail |
| `SubjectEnvelope` | `Subject Context` | allowlist mínima entregue ao Subject Agent | não confundir ref com acesso ou contexto irrestrito | derivado para a Run admitida; não concede autoridade | Goal + inputs permitidos + capabilities → contexto invocado | Run detail, ledger |
| `RunRecord` / `Run` | `Run` | uma tentativa factual ligada ao plano e prontidão exatos | não confundir com job, retry ou resultado | nasce somente após readiness `admitted`; criação é do sistema | plano pronto → Run | Runs, Run detail |
| `RunEvent` | `Run Event` | observação factual append-only | não chamar ledger de log descartável | append-only e válido por fase; ator não prova autoridade humana | fato → ledger | Trace, bundle |
| `Artifact` / `ArtifactRef` | `Artifact` / `Artifact Reference` | identifica conteúdo por digest sem conceder leitura | não tratar ref como path, grant ou blob materializado | identidade imutável; acesso exige grant separado | conteúdo → identidade referenciável | Run detail, Evaluation, bundle |
| `EvaluationRecord` | `Recorded Evaluation` | avaliação vetorial ancorada à Run | não confundir avaliação com conclusão do lifecycle | append-only; correção cria outro record; etapa humana exige autoridade verificada | Run + evidence → evaluation | Evaluation, bundle |
| `Comparison` | `Comparison` | leitura pareada de Runs e trade-offs | não prometer ranking universal | projeção derivada; não cria autoridade | Runs → comparação | API, bundle |
| `Evidence Bundle audit` | `Audit Evidence Bundle` | pacote verificável de records, refs e digests | não prometer blobs, replay ou portabilidade | export imutável verificável; não cria authority ou access grant | records → bundle | Evidence, CLI |

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
mostra `Blocked`, explica a incompatibilidade do runner e não cria Run. Isso não é rejeição humana nem
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
| fixtures | IDs, payloads canônicos e import dedicado permanecem estáveis; aliases não alteram `CRL-CTX-002` |
| documentação | prosa normativa explica os aliases em inglês e preserva os identificadores técnicos para auditoria |
| migração futura | qualquer rename persistido exige ADR sucessor, versão nova, expand-contract e testes de leitura dos artefatos anteriores |
