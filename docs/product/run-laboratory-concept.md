---
id: product-run-laboratory-concept
type: product
title: Ideias para Runs, contratos e checkpoints
status: draft
authority: incubation
owner: product
created_at: 2026-07-22
updated_at: 2026-07-22
applies_to: product/runs
sources:
  - user-conversation:2026-07-22-run-design-brainstorm
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
review_due: 2026-10-22
---

# Ideias para Runs, contratos e checkpoints

> Estado: brainstorming preservado. Este documento registra intenção, possibilidades e questões
> abertas. Não define ainda o `RunSpec`, não altera o `ExperimentManifest v1` e não autoriza
> implementação automática.

## Origem

O usuário imagina o Evidrun como um laboratório em que uma pessoa possa trazer uma ideia sobre como
melhorar a performance de um agente, ou escolher uma capacidade e um cenário que deseje testar. Um
Lab Agent entenderia o contexto amplo da pessoa, ajudaria a transformar a ideia em benchmark e
discutiria quais interações, ambientes, prompts, métricas e evidências seriam adequados.

As ideias foram escritas de forma exploratória antes de o projeto entrar em implementação ampla.
Devem ser preservadas porque podem orientar contratos futuros, mas não devem ser tratadas como
requisitos fechados.

## Intenção central

- Uma Run não deve começar a partir de parâmetros soltos ou de um prompt informal.
- Antes de iniciar, deve existir algum contrato obrigatório, aceito, imutável e verificável.
- Nem tudo pertence ao mesmo momento: algumas definições existem antes da Run, outras só podem ser
  observadas no runtime e outras são interpretação pós-Run.
- Os contratos precisam ser amplos o suficiente para diferentes problemas sem generalizar tudo em
  estruturas livres e ambíguas.
- O Lab Agent ajuda a descobrir e organizar o estudo, mas não aceita sozinho o contrato final.

## Vocabulário ainda em exploração

### Intenção ou objetivo semântico da Run

Registra por que a Run existe e o que o usuário está tentando compreender. Pode representar uma
hipótese de melhoria, uma avaliação de capacidade, um diagnóstico ou uma exploração mais aberta.
Essa intenção pode pertencer ao laboratório e não necessariamente ser mostrada ao Subject Agent.

### Goal

Representa o estado ou conjunto de tarefas ao qual o Subject Agent deve tentar chegar. Deve ser
logicamente possível dentro do ambiente e suficientemente claro para que seja possível observar
progresso ou evidência de conclusão.

Alcançar o Goal não significa automaticamente passar no teste. A execução ainda pode:

- violar constraints ou guardrails;
- gastar recursos de maneira inadequada;
- seguir um processo ruim;
- omitir evidência;
- produzir findings inesperados e valiosos;
- chegar ao resultado correto por um caminho não reproduzível.

Goals qualitativos podem existir, mas precisam ser ao menos avaliáveis por uma rubric, por evidência
ou por revisão humana. Se não houver nenhum procedimento de avaliação possível, o estudo deve ser
tratado como exploratório, e não como pass/fail.

### Provider e model specs

Uma Run real pode precisar registrar provider, protocolo, model ID solicitado, model ID reportado,
reasoning, parâmetros de geração, budgets e revisões. Ainda é uma questão aberta se essas definições
vivem diretamente no contrato da Run ou são resolvidas de perfis versionados durante a compilação.

### Prompts e interações condicionais

Uma Run pode possuir um ou vários prompts. O usuário imagina edges condicionais, como:

- se X acontecer, entregar o Prompt X;
- se Y acontecer, entregar o Prompt Y;
- após um marco, iniciar um novo tipo de comportamento;
- após falhas repetidas, introduzir diagnóstico ou recuperação.

Uma possível formalização futura é um `InteractionProtocol` versionado, com nodes, edges, triggers,
prioridades e limites de ativação. Isso ainda não foi aceito como contrato.

### System prompts

Pode existir um padrão seguro, mas o usuário deve conseguir experimentar System Prompts diferentes.
Uma possibilidade é compor camadas explícitas, como base do Subject Agent, cenário, variant e overlay
de retomada. A entrada exata entregue ao modelo precisaria ser registrada e hasheada.

### Condições e pontuação

O usuário quer definir comportamentos que influenciem pontuação positiva ou negativamente. Algumas
regras podem considerar raridade, dificuldade, tempo, eficiência ou padrões seguidos pelo agente.

Uma interpretação possível é separar o termo amplo “condições” em:

- preconditions de admissão;
- triggers de transição;
- critérios de checkpoint;
- stop conditions;
- scoring rules;
- hard constraints e guardrails.

Regras de score idealmente são definidas antes da Run. Findings realmente novos podem ser
preservados e avaliados, mas não deveriam causar alteração retroativa silenciosa de uma avaliação
controlada. Uma rubric aberta e limitada pode ser uma alternativa futura.

### Findings

Findings são achados produzidos ou descobertos durante a execução. Podem ser esperados ou
inesperados, positivos ou negativos. Um Finding provavelmente precisará de claim, tipo, escopo,
evidence refs, confiança, impacto e adjudicação.

O Subject Agent pode propor um Finding, mas não deveria atribuir pontos a si mesmo. Um serviço,
grader, judge separado ou humano poderia verificar e adjudicar o achado.

### Tool calls

Preservar cada tool call e permitir uma projeção detalhada do fluxo de execução:

- quando a tool foi oferecida;
- quando foi chamada;
- parâmetros permitidos ou redigidos;
- aprovação;
- latência;
- resultado;
- falha ou retry;
- relação causal com prompts, findings, artifacts e checkpoints.

Totais e gráficos podem ser derivados do event ledger, evitando múltiplas fontes de verdade.

### Tokens de input e output

Registrar usage por invocation e permitir gráficos de:

- tokens por minuto;
- tokens por fase;
- tokens por Goal ou tarefa;
- tokens entre checkpoints;
- tokens antes e depois de compactações;
- custo por resultado ou score.

O sistema deve diferenciar usage informado pelo provider, estimado, parcial e indisponível. Métricas
derivadas não devem fingir precisão que o provider não forneceu.

### Skills

Observar quantas skills foram utilizadas, quais foram e em que momento. “Usada” ainda precisa de
definição, pois uma skill pode estar disponível, exposta, carregada, invocada, concluída ou falhar.
Versão, hash, contexto adicionado e tools relacionadas podem fazer parte da evidência futura.

### Compaction

Registrar quantas vezes o contexto foi compactado, mas também preservar informações mais úteis:

- trigger;
- policy;
- contexto antes e depois;
- tokens removidos;
- summary ou transformação;
- conteúdo preservado e omitido;
- possível perda de informação;
- efeito posterior no comportamento.

### Checkpoints

Checkpoints são marcos seguros e observáveis no progresso da Run. Uma Run pode concluir sem atingir
um checkpoint, atingir alguns ou atingir todos. O número de checkpoints não deve ser automaticamente
interpretado como qualidade.

O usuário quer que checkpoints sejam reutilizáveis. Exemplo: uma Run cria um agente em quatro
marcos; uma execução futura pode preservar o estado até o checkpoint 2 e testar variáveis diferentes
a partir dali.

Uma possível distinção futura:

- `CheckpointDefinition`: pré-Run, define trigger, estado exigido e o que capturar;
- `CheckpointRecord`: runtime, registra o marco realmente atingido e seu snapshot imutável.

Um checkpoint poderia preservar, conforme a capacidade do ambiente:

- cursor do event ledger;
- Context Snapshot;
- estado do protocolo de prompts;
- progresso do Goal;
- manifest de artifacts;
- snapshot do execution workspace;
- estado observável das tools;
- métricas acumuladas;
- hash do checkpoint.

O estado interno privado de um modelo não pode ser restaurado. Uma retomada precisa declarar
limitações e nível de replayability.

## Formas possíveis de reutilizar um checkpoint

Ainda não há decisão, mas três operações parecem semanticamente diferentes:

1. `restore`: restaura contexto, artifacts e workspace capturados; herda estado anterior;
2. `replay`: inicia uma nova Run e tenta reproduzir o caminho até o checkpoint;
3. `context_extraction`: inicia um ambiente limpo e monta apenas conhecimento ou artifacts
   selecionados do checkpoint.

Uma execução derivada deve provavelmente ser uma nova Run com lineage explícita, nunca uma reabertura
silenciosa de uma Run terminal.

## Contratos candidatos

Os nomes abaixo são candidatos, não contratos aprovados:

- `StudyIntent`;
- `GoalSpec`;
- `ScenarioRevision`;
- `WorkspaceTemplateRevision`;
- `InteractionProtocolRevision`;
- `EvaluationPlanRevision`;
- `CheckpointPolicyRevision`;
- `RunSpec` compilado;
- `FindingRecord`;
- `UsageEvent`;
- `CheckpointRecord`;
- `RunOutcome` e `Scorecard`.

## Fluxo candidato do Lab Agent

1. receber a ideia informal;
2. identificar se é capability, improvement, regression, diagnostic ou exploratory;
3. separar intenção, Goal, hipótese e critérios;
4. propor baseline, candidate e variável primária quando aplicável;
5. detectar confounders, impossibilidades e vazamento de hidden graders;
6. propor workspace, tools, skills, prompts, métricas e checkpoints;
7. mostrar o que será visível ou oculto do Subject Agent;
8. criar drafts;
9. aguardar aceitação humana;
10. compilar um contrato imutável antes da execução;
11. explicar resultados e limitações após a Run.

## Dados canônicos e projeções

Uma direção promissora é manter eventos e snapshots como dados canônicos e construir projeções para
totais, gráficos e relatórios. Exemplos:

```text
Canônico: cada tool call
Derivado: total de tool calls e grafo de tools

Canônico: usage por invocation
Derivado: tokens por minuto e por checkpoint

Canônico: cada compaction
Derivado: total de compactações e economia acumulada
```

Essa separação reduz inconsistência sem perder observabilidade.

## Questões abertas

- Qual é o conjunto mínimo realmente universal do `RunSpec`?
- Quando exatamente o contrato congela: acceptance, compilation, admission ou queue?
- Como representar predicados de edges sem permitir lógica arbitrária insegura?
- Quais dimensões devem existir em todo scorecard?
- Quando um Finding inesperado pode influenciar o score atual?
- O que torna um checkpoint “seguro” e compatível com outra Run?
- Como medir replayability quando provider ou ambiente não são determinísticos?
- Como separar tempo ativo do agente, espera humana, latência de provider e tempo de tool?
- Quais dados brutos são necessários e quais projeções podem ser reconstruídas?
- Como permitir extensões de domínio sem transformar tudo em `dict[str, Any]`?

## Regra de promoção

Nenhuma seção deste documento se torna normativa por existir aqui. Uma ideia deve ser discutida,
reduzida a uma decisão explícita e então promovida para ADR ou contract com versão, ownership,
implementation refs e verification refs.

Ver também: [Canvas vivo e grafo de execução](live-run-graph-concept.md).
