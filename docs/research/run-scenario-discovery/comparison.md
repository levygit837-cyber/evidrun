---
id: research-run-scenario-discovery-comparison
type: research
title: Comparação do discovery orientado por cenários de Run
status: draft
authority: research
owner: core
created_at: 2026-07-22
updated_at: 2026-07-22
applies_to: discovery/run-contracts
sources:
  - user-conversation:2026-07-22-scenario-oriented-discovery
  - repository:product/run-laboratory-concept
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
observed_at: 2026-07-22
review_due: 2026-10-22
---

# Comparação do discovery orientado por cenários de Run

> Estado: análise de research, não decisão arquitetural. Os candidatos abaixo não alteram
> `ExperimentManifest v1`, não são schemas aprovados e não autorizam implementação.

## Dossiers comparados

1. [Cenário A — CRL-CTX-002 determinístico](scenario-a-crl-ctx-002.md)
2. [Cenário B — Blueprint de agente que cria outro agente](scenario-b-nested-agent-blueprint.md)
3. [Cenário C — Investigação qualitativa de pedidos duplicados](scenario-c-qualitative-incident.md)

Os dossiers foram comparados em duas dimensões:

- **presença e aplicabilidade:** o conceito é universal, condicional ou omitido por desenho;
- **lifecycle e ownership:** o dado é definição pré-Run, resolução de admissão, registro canônico de
  runtime ou projeção derivada, e qual fronteira deve controlá-lo.

“Aparece nos três dossiers” não significa automaticamente “pertence ao core do RunSpec”. Intenção,
por exemplo, é universal para o estudo, mas pertence ao Control Plane e não ao contexto do Subject
Agent.

## Matriz de presença por cenário

| Conceito | A — determinístico | B — nested agent | C — qualitativo | Classificação |
| --- | --- | --- | --- | --- |
| Identidade e revision | Necessário | Necessário | Necessário | Universal |
| Intenção do estudo | Necessária no laboratório | Necessária no laboratório | Necessária no laboratório | Universal no discovery; fora do contexto do Subject |
| Goal | Único e exato | Multi-entregável | Qualitativo | Universal |
| Subject/executor ref | Runner determinístico | Subject Agent com provider real | Subject Agent com provider real | Universal |
| Ambiente e workspace | Fixture offline | Sandbox com escrita confinada | Pacote somente leitura | Universal, com tipos distintos |
| Inputs versionados | Fixture | Brief, PR, policies e casos | Incident packet | Universal, payload de domínio |
| Interação inicial | Goal + Context Snapshot | System prompt + Goal + protocolo | System prompt + Goal + rubric pública | Universal como entrada; protocolo complexo é condicional |
| Evaluation Plan | Grader exato | Graders, gates e score vetorial | Judge, humano e score vetorial | Universal, composição variável |
| Stop conditions | Saída terminal ou falha | Goal, gates, capabilities, budgets ou humano | Entrega, evidência esgotada, budgets ou humano | Universal |
| Visibilidade e captura | Hidden answer e fixture | Hidden cases, artifacts e workspaces | Calibration, judge e incident packet | Universal |
| Limitações | Generalização e runner | Capabilities e replayability | Incerteza, judge e ausência de ground truth | Universal |
| Context Policy comparada | Essencial | Constante no fork proposto | Não aplicável | Módulo de domínio/contexto |
| Baseline/candidate | Essencial | Somente quando o fork for comparação controlada | Omitido por desenho | Módulo de experimento |
| Provider real | Omitido por desenho | Necessário | Necessário | Capability condicional resolvida por profile ref |
| Tools | Omitidas por desenho | Múltiplas, com escrita confinada | Busca somente leitura | Capability condicional |
| Skills | Omitidas por desenho | Duas capacidades lógicas | Omitidas por desenho | Capability condicional |
| Artifacts produzidos | Omitidos por desenho | Entregáveis centrais | Relatório pode ser output; artifact não é requisito central | Módulo condicional |
| Findings | Omitidos por desenho | Esperados ou inesperados | Essenciais ao discovery | Módulo condicional de runtime |
| Checkpoints | Omitidos por desenho | Quatro definitions | Omitidos por desenho | Módulo condicional |
| Fork e lineage | Omitidos por desenho | Permitido no checkpoint 2 | Omitido por desenho | Módulo condicional |
| Judge | Omitido por desenho | Possível depois de graders | Obrigatório e provisório | Evaluator condicional |
| Revisão humana | Não obrigatória | Gates/aprovações quando definidos | Adjudicação final obrigatória | Autoridade condicional |
| Linguagem de conclusão limitada | Pass/fail da fixture | Trade-offs e replayability | Estados epistêmicos explícitos | Policy de avaliação específica |

### Campos que aparecem sempre

O conjunto mínimo observado no nível de discovery é:

- identidade estável e revision;
- intenção do estudo;
- Goal separado de avaliação;
- referência ao subject/executor;
- ambiente ou workspace template;
- inputs tipados e versionados;
- entrada ou protocolo inicial;
- Evaluation Plan;
- stop conditions;
- visibilidade/capture policy;
- limitações e linguagem de validade.

Esse conjunto não precisa ser um único objeto. Intenção, RunSpec compilado e Evaluation Plan possuem
owners e visibilidades diferentes.

### Campos que pertencem apenas a determinados domínios

- `context_policy`, Context Diff e pareamento de variants pertencem ao domínio de experimentos de
  contexto do cenário A.
- Bundle de agente, policy de PR, schemas de tools e provisionamento pertencem ao domínio do cenário
  B.
- Incident packet, taxonomia de hipóteses e vocabulário epistêmico pertencem ao domínio do cenário
  C.
- Rubric dimensions não devem ser enum global: cada Evaluation Plan referencia dimensões versionadas.
- Tool e skill payloads pertencem a adapters ou catálogos de capabilities, não ao core.

## Matriz de lifecycle e ownership

| Conceito ou dado | Lifecycle | Fonte canônica/owner | Visível ao Subject | Disposição candidata |
| --- | --- | --- | --- | --- |
| Study intent e hipótese | Pré-Run | Control Plane / laboratório | Não | Objeto ou revision própria referenciada pelo estudo |
| Goal | Pré-Run | Goal revision aceita | Sim | `GoalSpec` próprio, sem score |
| Scenario e inputs | Pré-Run | Scenario revision e artifact/input refs | Parcial, conforme mount | `ScenarioRevision` com inputs discriminados |
| Workspace template | Pré-Run | Environment/workspace catalog | Somente resultado compilado | `WorkspaceTemplateRevision` próprio |
| Provider profile ref | Pré-Run | Provider catalog | Identidade permitida | Reutilizar `ProviderProfile v1` |
| Provider/model reportado | Runtime | Provider invocation event | Não necessariamente | Registro de resolução/invocação, não manifest duplicado |
| System prompt e interação | Pré-Run | Prompt artifact e protocol revision | Sim quando entregue | `InteractionProtocolRevision` quando houver fluxo complexo |
| Capability requirements | Pré-Run | RunSpec compilado e catálogo | Allowlist resolvida | União discriminada de refs; payloads fora do core |
| Capability resolution | Admissão | Coordinator/serviço determinístico | Capabilities admitidas | Registro de admissão |
| CheckpointDefinition | Pré-Run | Checkpoint policy revision | Critérios permitidos | Contrato próprio e opcional |
| CheckpointRecord | Runtime | Event ledger + snapshot refs | Não automaticamente | Registro próprio, imutável e hasheado |
| Fork request e lineage | Pré-Run + runtime | Control Plane e nova Run | Somente contexto compilado | `ForkSpec` e lineage explícita |
| Context Snapshot | Runtime | Context service | Sim, por definição | Reutilizar lifecycle existente |
| Tool call/result | Runtime | Event ledger | Produzido/recebido pelo Subject | Events tipados; totals derivados |
| Skill lifecycle | Admissão + runtime | Resolver e event ledger | Skill admitida e contexto entregue | Events tipados; catálogo fora do core |
| Artifact content | Runtime | Artifact store | Conforme policy | Conteúdo fora do core; refs em `ArtifactManifest` |
| Finding | Runtime | Finding service + evidence refs | Pode propor | `FindingRecord` com adjudicação separada |
| Metric definition | Pré-Run | Evaluation Plan | Conforme transparência | Definição versionada e tipada |
| Metric observation/usage | Runtime | Event ledger/provider/tool records | Não necessariamente | Registros canônicos por invocation/event |
| Grade/judge evaluation | Runtime pós-span | Evaluation service | Não durante a Run | Avaliação imutável ancorada a event cursor/checkpoint |
| Human adjudication | Runtime pós-avaliação | Autoridade humana | Não automaticamente | `AdjudicationRecord` append-only |
| Stop cause | Runtime | Coordinator/event ledger | Estado terminal | Evento canônico |
| Scorecard consolidado | Derivado | Projector sobre avaliações/adjudicações | Após política de divulgação | Projeção versionada e reconstruível |
| Totais, gráficos e canvas | Derivado | Projectors | Conforme autorização | Fora do core canônico |
| Comparação e narrativa | Derivado | Comparison/report service | Não durante a Run | Projeção com refs para fontes canônicas |

## Contratos candidatos

Os três dossiers justificam investigar contratos separados, e não adicionar todos os conceitos ao
`ExperimentManifest v1`.

| Candidato | Responsabilidade proposta | Por que não deve ser um campo livre no manifest |
| --- | --- | --- |
| `StudyIntent` | Intenção, hipótese, pergunta e escopo do laboratório | Possui visibilidade e autoridade diferentes do Subject Agent |
| `GoalSpec` | Estado desejado, entregáveis e constraints | Goal não pode incorporar score ou hidden graders |
| `ScenarioRevision` | Tarefa, inputs, limitações e condições observáveis | Mudanças materiais precisam de revision e digest próprios |
| `WorkspaceTemplateRevision` | Mounts, isolamento, rede, escrita e efeitos permitidos | Ambientes A, B e C têm formas incompatíveis sem tipos discriminados |
| `InteractionProtocolRevision` | Prompts, nodes, triggers e limites de interação | Cenário A não deve carregar estrutura condicional vazia |
| `EvaluationPlanRevision` | Graders, rubric, judges, ordem, metrics e gates | Avaliação precisa congelar antes da Run e evoluir por revision |
| `CheckpointDefinition` | Trigger, critérios, captura e compatibilidade | É definição pré-Run e módulo opcional |
| `CheckpointRecord` | Marco atingido, cursor, hashes, snapshots e validações | É evidência de runtime, não configuração |
| `ForkSpec` e lineage | Origem, modo, conteúdo herdado e variável alterada | Nova Run não pode reabrir ou mutar a original |
| `FindingRecord` | Claim, tipo, confidence, impact, refs e adjudicação | Findings são runtime e não pertencem ao Goal ou score |
| `ArtifactManifest` | Refs, digests, classificação, provenance e relações | Conteúdo e schemas de domínio ficam no artifact store/adapters |
| `AdjudicationRecord` | Decisão humana e rationale sobre avaliação anterior | Judge não pode ser sobrescrito retroativamente |
| `RunSpec` compilado | Entrada imutável e admitida da execução | Deve referenciar revisions aceitas, sem absorver chats ou segredos |
| `RunOutcome` | Estado terminal, constraints e refs de avaliações | Goal alcançado e qualidade precisam continuar separados |
| Scorecard projection | Visão vetorial sobre avaliações e adjudicações | É reconstruível e pode ter diferentes apresentações versionadas |

Esses nomes continuam candidatos da pesquisa. Criar schemas exige reduzir cada responsabilidade,
definir versão, owner, compatibilidade, implementação e verificação.

### Reutilização de contratos atuais

- `ProviderProfile v1` deve ser referenciado, não copiado para `RunSpec`.
- `Run Event v1` continua sendo o envelope append-only; novos eventos exigirão payloads tipados e
  versionados.
- `Context Snapshot` e seu lifecycle continuam válidos para o conteúdo realmente entregue.
- Capture/retention continua governando artifacts, prompts, snapshots e avaliações.
- Evidence Bundle precisará de versão sucessora somente quando novos records forem promovidos.

## O que não deve existir no core

- schemas específicos de tools ou argumentos vendor-specific;
- implementação, instruções ou conteúdo de skills;
- corpo de system prompts;
- regras específicas de PR, fila, pedidos ou incidentes;
- protocolo específico de framework para criar um agente-filho;
- credenciais, API keys ou valores recuperados do Keychain;
- conteúdo de artifacts e fixtures;
- nomes fixos de rubric dimensions;
- contadores mantidos paralelamente ao event ledger;
- posições, cores, edges ou estado de layout do grafo de UI;
- um saco de extensões baseado em `dict[str, Any]` sem discriminador e versão.

O core pode manter refs, envelopes, digests, classifications, lineage e interfaces de capabilities.
Payloads de domínio devem usar modelos discriminados e versionados ou artifacts referenciados.

## Canônico versus derivado

Princípio comum aos três cenários:

```text
Canônico: tool call individual, usage por invocation e checkpoint record
Derivado: totais de tools, tokens por checkpoint e nodes do canvas

Canônico: grade por dimensão, avaliação do judge e adjudicação humana
Derivado: scorecard consolidado e narrativa de resultado

Canônico: artifact/finding refs e relações causais registradas
Derivado: grafo, agrupamentos, rankings e resumo de findings
```

Uma projeção pode possuir schema e versão sem virar fonte de verdade. Regenerá-la não altera events,
grades, findings ou decisões humanas.

## Imutabilidade e avaliação

- Acceptance congela revisions; compilation resolve refs; admission verifica capabilities; queue não
  pode mudar silenciosamente nenhuma delas.
- Mudança material em Goal, input, fixture, rubric, grader, checkpoint ou scoring rule cria nova
  revision e vale apenas para Runs futuras.
- Finding inesperado pode ser preservado e adjudicado dentro de uma faixa aberta predefinida; não
  autoriza editar a rubric da Run concluída.
- Judge produz avaliação separada e provisória. Humano acrescenta adjudicação; não reescreve o
  registro anterior.
- Uma Run derivada de checkpoint é uma nova Run com lineage, nunca continuação mutável da original.

## Gate do discovery

| Gate | Estado neste discovery | Evidência | Pendência antes de promover contratos |
| --- | --- | --- | --- |
| Representar sem depender excessivamente de `dict[str, Any]` | Atendido conceitualmente | Módulos e candidatos possuem responsabilidades discriminadas | Prototipar schemas fechados e validar extensibilidade |
| Evitar manifests cheios de `null` | Atendido | A omite modules; B e C declaram somente capabilities aplicáveis | Definir composição e regras de omissão na compilação |
| Não misturar Goal e pontuação | Atendido | Os três Goals terminam antes das seções de Evaluation Plan | Formalizar `GoalSpec` e `EvaluationPlanRevision` separados |
| Não misturar execution e laboratory workspace | Atendido | Cada dossier possui fronteiras e matriz de visibilidade | Contratar mounts, grants e compilação do workspace |
| Não misturar canônico e gráfico derivado | Atendido | Matriz de lifecycle e seção de projeções | Definir projectors e versionar output schemas |
| Não alterar avaliação retroativamente | Atendido | Revisions imutáveis, judge preservado e adjudicação append-only | Definir política de supersession e migração de projections |
| Não depender de funcionalidades inexistentes | Atendido para representação | B termina em `unsupported_capabilities`; C declara lacunas; A permanece executável | Implementação futura só após contratos, threat model e gates próprios |

## Conclusão do discovery

Os três cenários podem ser representados sem transformar todos os conceitos em campos universais. O
núcleo comum é menor que qualquer dossier completo; tools, skills, checkpoints, fork, findings,
judge e revisão humana entram como módulos tipados ou records próprios.

O gate está atendido no papel, mas não autoriza promoção imediata. A próxima decisão deve selecionar
um contrato candidato de cada vez, testar seu schema fechado contra os três dossiers e criar ADR
sucessor apenas quando uma decisão aceita realmente mudar.
