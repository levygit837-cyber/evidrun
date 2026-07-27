---
id: product-judging-agent-concept
type: product
title: Agente julgador e intervenção na sessão do Subject
status: draft
authority: incubation
volatility: snapshot
owner: product
created_at: 2026-07-25
updated_at: 2026-07-26
applies_to: product/model-judge-and-intervention
sources:
  - user-conversation:2026-07-25-execution-graph-and-judge
  - docs/adr/0018-lab-agent-copilot-scope.md
  - docs/benchmarks/graders-and-judges.md
  - docs/adr/0012-subject-disclosure-and-terminal-semantics.md
  - docs/architecture/agents-and-authority.md
  - docs/research/run-scenario-discovery/scenario-c-qualitative-incident.md
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
review_due: 2026-10-25
---

# Agente julgador e intervenção na sessão do Subject

> Estado: ideia preservada para avaliação. Este documento não descreve runtime existente, não define
> contrato aceito e não autoriza implementação. Ele contém uma proposta que **entra em conflito
> parcial com ADR aceito**, e o conflito está explicitado abaixo em vez de contornado.

## Origem

A proposta tem duas partes que o pedido original apresentou juntas:

1. Adicionar `LLM-as-a-judge` como opção de benchmark escolhível na triagem, onde o humano define o
   objetivo do julgamento e as informações entregues ao agente julgador, e o julgador pode usar como
   conhecimento os documentos gerados do RunSpec.
2. Dar a esse julgador a capacidade de conduzir Runs **multi-turno** com o agente avaliado, com
   ferramentas de **interferência na sessão** — injetar prompt, hint, redirecionar. A justificativa:
   agentes não são determinísticos, então é difícil prever por código quando enviar o próximo prompt,
   e um julgador com contexto poderia servir como mecanismo primário de follow-up, ampliando o escopo
   dos benchmarks.

A distinção entre as duas partes é o ponto central deste documento. A primeira está em grande parte
desenhada. A segunda funde dois papéis que o design existente separa deliberadamente.

## Parte 1 — o julgador como avaliador: já desenhado

O vocabulário existe e as restrições são boas.

`EvaluationStage.kind` (`src/evidrun/contracts/authoring/evaluation.py:55-62`) já aceita
`model_judge`, ao lado de `integrity`, `deterministic_grader` e `human_review`.

`EvaluationRecord` (`src/evidrun/contracts/runtime/records.py:165-218`) impõe três invariantes ao
julgador:

- um julgador por modelo **nunca produz resultado final** — só `provisional`;
- ele é o único tipo que **deve** declarar provider e modelo resolvidos;
- nenhum outro tipo pode declarar provider ou modelo.

O "objetivo do julgamento definido pelo humano" já cabe: `EvaluationDimension`
(`evaluation.py:20-39`) tem `description`, `value_type`, `minimum`, `maximum` e `anchors` — uma rubric
versionada. `StudyIntent` guarda o propósito do laboratório. `hidden_input_refs` e inputs com
`visibility="evaluator"` entregam material que o Subject não vê.

O "julgador avalia enquanto o Subject continua" também tem mecanismo: `EvaluationBoundary` ancora toda
avaliação a `up_to_event_sequence` + `event_hash`, ou a um `checkpoint_id`. Um julgador pode ler um
prefixo congelado do histórico. `live-run-graph-concept.md:195` já menciona avaliadores em background
sobre segmentos estáveis, incluindo julgador por modelo.

O que falta, aqui, é execução: `_is_supported_evaluation`
(`src/evidrun/contracts/admission/checks/unsupported.py:170-183`) aceita **exatamente um** stage
`deterministic_grader`. Qualquer `model_judge` é rejeitado como `runtime:evaluation_pipeline`.

E falta vocabulário de evidência que a própria doutrina exige. `docs/benchmarks/graders-and-judges.md`
determina que "prompt, rubric, modelo, parâmetros, custo e incerteza do judge fazem parte da
evidência". O `EvaluationRecord` tem `provider_profile_id`, `provider_model` e `confidence` — **não tem
campo para prompt, rubric nem custo**. Um julgador implementado hoje não teria onde registrar metade
do que o documento normativo pede.

Sobre "usar os docs do RunSpec como conhecimento": isso precisa de cuidado. O RunSpec contém o
`evaluation_plan` inteiro, incluindo o parâmetro `expected` — o gabarito — e a identidade do provider.
Entregar o RunSpec ao julgador é diferente de entregá-lo ao Subject, e provavelmente aceitável, mas
exige recorte explícito por allowlist, como o `EvaluatorEnvelope` já faz
(`src/evidrun/contracts/compiler.py:384-411`). "O julgador lê os docs" não pode significar "o julgador
recebe o RunSpec bruto".

## Parte 2 — o julgador que interfere: novo, e em conflito

Aqui a proposta colide com quatro regras, em graus diferentes de dureza.

### 2.1 O julgador é definido como cego

`docs/benchmarks/graders-and-judges.md:21-23` (normativo, aceito):

> "Judges baseados em modelo são secundários, versionados, **cegos ao nome da variant quando possível**
> e calibrados com casos conhecidos."

`docs/research/run-scenario-discovery/scenario-c-qualitative-incident.md:189-192` detalha: o julgador
recebe a resposta anonimizada, e sempre que possível não recebe nome da variant, identidade do autor,
chat do laboratório ou scores anteriores.

Um julgador que conversa com o Subject ao vivo vê a sessão inteira, em ordem, com todo o contexto. É o
oposto de cego. Não é um detalhe de configuração: cegueira é a razão pela qual o julgamento dele tem
algum valor probatório.

### 2.2 Conduzir a Run não é delegado a agentes

`docs/architecture/agents-and-authority.md:72-75` (normativo, aceito):

> "## Serviços determinísticos
>
> Montagem de contexto, autorização, estado da run, retenção, event ledger e **ordem dos graders não
> são delegados a agentes**. São serviços verificáveis."

A proposta pede exatamente que um agente decida a sequência de interações. Essa é a colisão mais
direta, e ela é arquitetural, não incidental: o valor da evidência do Evidrun vem de que o instrumento
de medida é determinístico e auditável.

### 2.3 Output de evaluator não chega ao Subject — com uma cláusula de escape

ADR 0012:56, na seção de disclosure:

> "Chats, locators, credenciais, secret bindings, Progress Artifacts e outputs de evaluators
> permanecem ausentes **salvo contrato explícito de intervenção**."

Essa é a única abertura no corpo normativo. O ADR previu que um contrato de intervenção poderia
existir. Ele não existe. Até existir, output de julgador chegando ao Subject é violação de ADR aceito.

`live-run-graph-concept.md:198-202` tem a formulação mais próxima de um caminho legítimo:

> "O Subject Agent **não recebe automaticamente essa avaliação**, evitando feedback ou vazamento não
> previsto. Se uma Evaluation Plan permitir feedback durante a Run, a entrega desse feedback deve
> produzir um evento separado e uma edge explícita de intervenção."

Note a forma: evento separado, edge explícita. Intervenção como fato registrado, não como canal
lateral.

### 2.4 Interferência contamina a variável primária

Sob `prospective_controlled`, a intenção é que o diff material entre baseline e candidate corresponda
à `primary_variable` (`docs/contracts/study-run-v1.md:74-76`). O validador atual garante que a variável
é um slot tipado e proíbe confounders fora de exploração (`authoring/study.py:97-110,141-178`), mas
ainda não prova sozinho que o diff material contém exatamente uma mudança.
Um julgador que injeta conteúdo gerado por modelo introduz, em cada Run, uma variação não declarada e
não reproduzível. Duas Runs do mesmo RunSpec deixam de ser a mesma configuração. E o resultado passa a
medir a interação entre dois modelos, não a capacidade do avaliado.

Também vale o limite de `graders-and-judges.md:25`: "um judge nunca pode transformar evidence mode
observacional em causal". Um julgador interferente faz algo adjacente e mais problemático — participa
da geração do dado que depois julga.

## O problema real que a proposta identifica

O diagnóstico do pedido está correto, e vale separá-lo da solução proposta.

É verdade que agentes não são determinísticos e que decidir por código quando enviar o próximo prompt é
difícil. Um grafo com condicionais rígidas cobre os casos previstos e falha nos não previstos —
exatamente o que a `PredicateTrigger` com referência opaca tenta adiar.

Mas há uma alternativa que preserva a separação de papéis: **o adaptativo mora na autoria, não na
execução.** Em vez de um agente decidir o próximo prompt durante a Run, um agente do laboratório
propõe um grafo mais rico *antes* da Run, com mais ramos e melhores gatilhos, que um humano aceita. A
execução continua determinística e auditável; a inteligência entra no desenho, não no instrumento.

Isso é exatamente o que o Lab Agent é desenhado para ser: o
[ADR 0018](../adr/0018-lab-agent-copilot-scope.md) declara seu escopo funcional como amplo — propor
drafts, propor métricas, explicar evidência — e limita apenas sua autoridade. Entre os limites de
autoridade, note o primeiro:

> "- enviar chat ao Subject;
> - editar event ledger;
> - conceder grant ou efeito externo;
> - transformar Progress Artifact em fato."

A primeira linha é precisamente a capacidade que a Parte 2 pede.

Uma segunda alternativa, se a interferência for realmente necessária: tratá-la como **variável
declarada e sob teste**, não como instrumento. Um Study cujo objeto é "o agente melhora quando recebe
hints adaptativos?" é legítimo — a interferência é a variável primária, e o julgador que a produz é
parte da configuração, versionado e registrado. O que não funciona é interferir e depois julgar a
mesma Run como se ela fosse observação limpa.

## Avaliação

**Parte 1 é boa e deveria avançar.** Julgador como avaliador cego, provisório, ancorado a boundary, com
rubric versionada. O contrato já está quase todo lá. As lacunas são conhecidas: admissão de mais de um
stage, campos de prompt/rubric/custo no record, e o recorte por allowlist do que o julgador lê. Isso
não exige ADR novo — exige runtime e três campos.

**Parte 2 não deveria avançar na forma proposta.** Fundir julgador e condutor custa a cegueira do
avaliador, a auditabilidade do instrumento e a comparabilidade entre Runs. Os três são a razão pela
qual este projeto existe em vez de um script que chama a API e imprime uma nota.

O que da Parte 2 vale preservar: a necessidade de multi-turno com direção adaptativa é real. Ela se
resolve pelo grafo de interação (`docs/product/interaction-graph-authoring-concept.md`) com um
coordinator determinístico, mais um Lab Agent que ajuda a *escrever* esse grafo. Se a adaptação em
tempo real se provar indispensável depois disso, ela volta como contrato de intervenção explícito —
com evento próprio, edge própria, e a Run marcada como tendo sofrido intervenção, sem promoção
automática a evidência causal.

Uma observação sobre sequência: a Parte 1 depende do coordinator de avaliação; a Parte 2 depende do
coordinator de turnos. Os dois passam por WS-50. Nenhuma das partes é bloqueada pela outra, mas ambas
são bloqueadas pelos três buracos de superfície do MVP
(`docs/planning/mvp-implementation-roadmap.md`). Julgador por modelo num produto onde o usuário não
consegue criar um Study próprio resolve o problema errado primeiro.

## Gate de promoção

Para a Parte 1:

- admissão aceitando mais de um stage e `kind="model_judge"`, com envelope declarando a capability;
- campos de prompt, rubric e custo no `EvaluationRecord`, conforme
  `graders-and-judges.md:23` já exige;
- allowlist explícita do que o julgador lê do RunSpec, com digest;
- calibração com casos conhecidos e teste de que o julgador permanece `provisional`;
- teste de cegueira: o julgador não recebe nome de variant nem scores anteriores.

Para a Parte 2, além de tudo acima:

- ADR sucessor decidindo se intervenção é instrumento ou variável;
- contrato explícito de intervenção, previsto pela cláusula de escape do ADR 0012:56;
- event types para intervenção, com digest do conteúdo injetado;
- regra de `evidence_mode` para Runs com intervenção, sem promoção automática a causal;
- coordinator de turnos com budget multi-turno aplicado;
- decisão sobre comparabilidade entre Runs que receberam intervenções diferentes.

Ver também: [Autoria de grafo de execução](interaction-graph-authoring-concept.md),
[Graders e judges](../benchmarks/graders-and-judges.md) e
[Canvas vivo e grafo de execução](live-run-graph-concept.md).
