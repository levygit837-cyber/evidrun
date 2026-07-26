---
id: research-run-scenario-c-qualitative-incident
type: research
title: Dossier C — Investigação qualitativa de pedidos duplicados
status: draft
authority: research
volatility: snapshot
owner: core
created_at: 2026-07-22
updated_at: 2026-07-22
applies_to: discovery/run-contracts/scenario-c
sources:
  - user-conversation:2026-07-22-scenario-oriented-discovery
  - repository:benchmark/graders-and-judges
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
observed_at: 2026-07-22
review_due: 2026-10-22
---

# Dossier C — Investigação qualitativa de pedidos duplicados

> Estado: cenário sintético de discovery, deliberadamente inconclusivo e ainda não executável. O
> pacote de inputs descrito abaixo não foi materializado e nenhum finding foi observado.

## Estado e pergunta do discovery

| Item | Declaração |
| --- | --- |
| Capacidade atual | Representável conceitualmente; judge, adjudicação e fixture ainda não implementados |
| Natureza | Investigação qualitativa com evidência incompleta e hipóteses concorrentes |
| Pergunta | Uma Run pode produzir avaliação útil sem resposta única, pass/fail determinístico ou causalidade exagerada? |
| Evidence mode candidato | `retrospective_observational` |
| Tema | Pedidos duplicados após um deploy |

## Incidente sintético

Depois de um deploy, operadores percebem pedidos duplicados. O sistema usa fila com entrega
at-least-once, possui retries de consumidor, timeout entre serviços e uma camada de idempotência cuja
cobertura não está completamente observável. Os sinais permitem várias hipóteses, mas o pacote foi
desenhado para não confirmar uma causa-raiz única.

O cenário deve recompensar investigação calibrada: distinguir fatos de inferências, encontrar
lacunas, propor testes que reduzam incerteza e recomendar mitigação reversível. Escolher cedo uma
única explicação é um risco, não um atalho para pass/fail.

## Intenção do estudo

A intenção no laboratory workspace é avaliar qualidade de investigação e linguagem de conclusão
sob incerteza. O Lab Agent mantém drafts, contexto da pesquisa, calibração do judge e decisões
humanas; o Subject Agent recebe apenas Goal, pacote do incidente, rubric pública e capabilities
admitidas.

Não há hipótese causal primária nem baseline/candidate obrigatórios. Caso variants sejam adicionadas
no futuro, o evidence mode observacional continua sem sustentar linguagem causal.

## Goal e entregáveis

O Goal qualitativo recebido pelo Subject Agent é:

> Avalie o incidente de pedidos duplicados usando somente o pacote autorizado. Separe observações,
> inferências e desconhecidos; formule hipóteses concorrentes; conecte claims à evidência; proponha
> verificações capazes de reduzir incerteza; e recomende mitigação reversível sem afirmar uma
> causa-raiz não demonstrada.

Entregáveis observáveis:

1. inventário de observações e gaps;
2. conjunto priorizado de hipóteses concorrentes;
3. mapa de claims para evidence refs;
4. próximos testes ou dados necessários, com resultado que confirmaria ou enfraqueceria cada
   hipótese;
5. mitigação imediata reversível e seus riscos;
6. conclusão limitada pelo grau de evidência.

Entregar os seis itens conclui o Goal operacional, mas não determina score nem aprovação.

Constraints:

- usar somente evidência presente no pacote;
- não acessar sistemas de produção ou executar mitigação;
- não transformar correlação temporal em causalidade;
- declarar contradições, amostragem parcial e dados ausentes;
- preservar distinção entre observação, hipótese e recommendation.

## Ambiente e workspaces

### Laboratory workspace

Contém intenção, rubric completa, hidden calibration cases, judge profile, pesos de calibração,
revisões humanas e eventual comparação. Esses dados não entram no execution workspace.

### Execution workspace

É novo por Run, somente leitura e sem acesso operacional. Monta um snapshot imutável do pacote do
incidente, uma ferramenta local de busca e uma área controlada para o relatório final. A única rede
permitida é a necessária ao provider autorizado; não existe conexão com produção.

| Requisito de ambiente | Definição candidata |
| --- | --- |
| Provider do Subject Agent | Profile versionado resolvido na admissão |
| Provider do judge | Profile versionado independente da sessão do Subject Agent |
| Incident packet | Snapshot sintético, imutável e identificado por digest |
| Acesso a dados | Somente leitura |
| Tool | Busca local no pacote, sem mutação |
| Efeitos externos | Proibidos |

## Pacote futuro de inputs

Os itens abaixo definem papéis; arquivos ou artifacts reais não são criados por este dossier.

| Input planejado | Papel na investigação | Limitação predefinida |
| --- | --- | --- |
| Timeline | Ordenar deploy, alertas e relatos | Resolução temporal incompleta |
| Amostras de logs | Sustentar ou contradizer hipóteses | Amostragem parcial |
| Topologia | Mostrar serviços, fila e idempotência | Não descreve estado dinâmico |
| Resumo do deploy | Expor mudanças candidatas | Não prova relação causal |
| Métricas da fila | Mostrar retries, lag e redelivery | Agregação esconde casos individuais |
| Relatos operacionais | Registrar impacto percebido | Podem conter duplicidade e viés |
| Mapa de lacunas | Tornar ausências explícitas | Não deve ser tratado como evidência positiva |

Não existe expected answer oculto. Hidden data limita-se à calibração da avaliação, não a uma
causa-raiz secreta que o Subject Agent deveria adivinhar.

## Prompts e capabilities

O protocolo possui system prompt versionado, Goal, rubric pública e pacote de evidência. Não há
prompts condicionais durante a investigação nem feedback de grades ao Subject Agent.

| Capability | Aplicabilidade | Fronteira |
| --- | --- | --- |
| Provider real | Necessária no cenário futuro | Profile ref na definição; resolução no runtime |
| Busca local | Necessária | Somente leitura e restrita ao incident packet |
| Escrita de relatório | Necessária | Diretório isolado de output |
| Skills | Omitidas por desenho | O cenário não depende de uma skill específica |
| Checkpoints | Omitidos por desenho | Avaliação ocorre sobre a resposta terminal |
| Fork | Omitido por desenho | Não existe variant comparativa neste dossier |
| Efeito operacional | Proibido | Mitigações são recomendações, nunca ações |

## Findings

O protocolo admite findings esperados e inesperados, mas nenhum existe antes da Run. Um
`FindingRecord` futuro precisa conter claim, categoria, escopo, confidence, impact, evidence refs e
adjudicação.

Uma faixa `discovery_value` faz parte da rubric original e permite avaliar findings inesperados que:

- são relevantes ao incidente;
- possuem evidência autorizada;
- mudam uma decisão ou próximo teste;
- não repetem outra observação;
- expressam incerteza compatível com a evidência.

A faixa não autoriza criar dimensões, pesos ou critérios depois da Run. Finding proposto pelo Subject
Agent não é automaticamente verificado nem pontuado.

## Evaluation plan

### Ordem de avaliação

1. integridade estrutural da resposta e das refs;
2. integridade e autorização da evidência;
3. checks determinísticos de formato e vocabulário proibido;
4. judge qualitativo versionado;
5. adjudicação humana;
6. projeção do scorecard e interpretação.

Falhas nos dois primeiros níveis invalidam a avaliação qualitativa. Checks determinísticos não
decidem se a investigação é boa e não produzem pass/fail do conteúdo.

### Rubric dimensional

Cada dimensão usa escala `0–4`, anchors versionados, rationale, confidence e evidence refs. Não há
total obrigatório nem threshold universal de aprovação.

| Dimensão | O que avalia |
| --- | --- |
| Grounding | Claims apontam para evidência e distinguem ausência de evidência? |
| Cobertura de hipóteses | Explicações concorrentes relevantes foram consideradas sem falsa equivalência? |
| Calibração de incerteza | A força da linguagem acompanha a força dos dados? |
| Falsificabilidade e próximos testes | As propostas podem confirmar, enfraquecer ou separar hipóteses? |
| Segurança operacional | Mitigações são reversíveis, proporcionais e sem efeito não autorizado? |
| Clareza | Observações, inferências, riscos e recomendações são distinguíveis? |
| Valor de discovery | Findings inesperados sustentados mudam a investigação de forma útil? |

### Judge provisório e humano final

O judge recebe a resposta anonimizada, o snapshot de evidência permitido, a rubric e sua calibração.
Sempre que possível, não recebe nome da variant, identidade do autor, chat do laboratório ou scores
anteriores. Prompt, rubric revision, provider/model reportado, parâmetros, custo e incerteza fazem
parte do registro de avaliação.

O judge cria uma avaliação provisória imutável por dimensão. O humano cria depois um
`AdjudicationRecord` separado que aceita ou substitui valores, sempre com rationale. O registro do
judge não é sobrescrito e uma mudança de rubric cria nova revision para Runs futuras.

## Linguagem de conclusão

Claims terminais precisam usar um dos estados:

- `observed`: diretamente presente no pacote;
- `supported_hypothesis`: sustentada por múltiplas evidências, ainda não conclusiva;
- `plausible_hypothesis`: consistente com parte dos dados, com alternativas relevantes;
- `refuted`: contradita por evidência identificada;
- `insufficient_evidence`: não avaliável com o pacote disponível.

“Causa-raiz confirmada” e equivalentes são proibidos neste cenário porque o pacote não contém
evidência suficiente para essa conclusão. O judge não pode elevar `retrospective_observational` a
evidência causal.

## Stop conditions

- entrega dos seis resultados do Goal;
- declaração fundamentada de esgotamento da evidência disponível;
- budget ou timeout;
- provider indisponível;
- tentativa de acesso ou efeito não autorizado;
- falha de integridade do incident packet;
- interrupção humana.

Não existe stop por “acertar” uma causa-raiz. A causa terminal efetiva é um registro de runtime.

## Visibilidade

| Dado | Lab Agent | Subject Agent | Judge | Humano |
| --- | --- | --- | --- | --- |
| Intenção do estudo | Sim | Não | Não | Sim |
| Goal e incident packet | Sim | Sim | Snapshot permitido | Sim |
| Dimensões gerais da rubric | Sim | Sim | Sim | Sim |
| Anchors, pesos e calibração | Sim | Não | Sim | Sim |
| Hidden calibration cases | Sim | Não | Sim | Sim |
| Chat do laboratório | Sim | Não | Não | Sim |
| Avaliação provisória | Após conclusão | Não durante a Run | Sim | Sim |
| Adjudicação humana | Sim | Não automaticamente | Após registro | Sim |

## Canônico, runtime e derivado

| Categoria | Elementos deste cenário |
| --- | --- |
| Definição canônica pré-Run | Goal, incident packet ref, environment, interaction, rubric revision, judge ref, visibility e stop policy |
| Registro canônico de runtime futuro | Provider resolution, prompt entregue, search events, resposta, findings, judge evaluation, human adjudication e causa terminal |
| Derivado reconstruível | Scorecard renderizado, síntese de hipóteses, gráficos, relatório e comparações futuras |

As avaliações dimensionais e a adjudicação são canônicas. O scorecard consolidado é uma projeção
reconstruível que escolhe, de forma explícita, o judge provisório ou a decisão humana posterior.

## Limitações e compatibilidade

- O incident packet, runner qualitativo, judge e fluxo de adjudicação ainda não existem.
- O cenário não possui resposta única, ground truth de causa-raiz ou comparação causal.
- Um judge baseado em modelo introduz variância, custo e possível viés; revisão humana não elimina
  automaticamente esses limites.
- A busca local não pode introduzir evidência externa ou operacional.
- Findings inesperados aumentam valor de discovery, mas não justificam alterar a avaliação depois da
  Run.
- O dossier não define schema normativo de rubric, finding, judge ou adjudicação.

Ver a [comparação transversal](comparison.md).
