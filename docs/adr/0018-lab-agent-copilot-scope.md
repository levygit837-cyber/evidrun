---
id: adr-0018
type: adr
title: Lab Agent como copiloto do laboratório, com fronteira de autoridade
status: accepted
authority: normative
owner: product
created_at: 2026-07-26
updated_at: 2026-07-26
applies_to: lab-agent
sources:
  - docs/adr/0002-control-plane-and-execution-plane.md
  - docs/adr/0009-study-run-contract-composition.md
  - docs/adr/0010-verifiable-human-authority.md
  - docs/product/run-laboratory-concept.md
  - docs/architecture/agents-and-authority.md
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
---

# Contexto

O ADR 0002 posicionou o Lab Agent no Control Plane e o Subject Agent no Execution Plane. Essa
decisão continua válida e não é revista aqui.

O que derivou foi a descrição do Lab Agent. O glossário o resumiu como "agente do control plane que
consulta evidências e cria drafts". O brief WS-50 lista seis permissões contra sete proibições. A
arquitetura afirma que "o papel do Lab Agent está definido" sem dizer qual é. O resultado
observável é que a documentação define o Lab Agent pelo seu complemento: um leitor de evidência com
uma lista de coisas que não pode fazer.

Isso não corresponde à intenção de produto. O Lab Agent é a superfície primária de trabalho do
aplicativo. A premissa do Evidrun é que montar um benchmark específico custa horas de trabalho
técnico especializado, e que a pessoa com a hipótese frequentemente não é a pessoa capaz de
formalizá-la. Um assistente periférico não resolve isso. O agente precisa conduzir o trabalho:
entender a intenção informal, propor o desenho do experimento, explicar o que os dados dizem e
propor o próximo passo.

A confusão tem uma causa identificável: **limite de autoridade foi redigido como limite de
capacidade**. As restrições dos ADRs 0009 e 0010 dizem que o Lab Agent não decide, não aceita e não
atesta. Nenhuma delas diz que ele não pode propor, calcular, explicar, comparar ou operar as
superfícies públicas do produto.

# Decisão

## Escopo declarado positivamente

O Lab Agent é o copiloto do laboratório. Seu escopo funcional é o app inteiro. Ele pode:

- conduzir a formulação: transformar uma pergunta informal em StudyIntent, hipótese, variável
  primária e comparação candidata, perguntando o que falta;
- propor drafts de qualquer contract de autoria: Study, Goal, Scenario, Variant, Agent Inventory,
  EvaluationPlan, ComparisonPlan e CheckpointPolicy;
- propor dimensões de avaliação, rubricas e graders novos, incluindo o desenho de métricas que o
  produto ainda não possui;
- explicar Runs, eventos, evidência, admissões rejeitadas e o motivo exato de uma rejeição;
- ler e comparar EvaluationRecords, Comparisons e projeções de métrica dentro do que o humano já
  pode ver;
- propor follow-ups, variants adicionais e repetições;
- operar as mesmas superfícies públicas que um humano opera (CLI e API), com a mesma autorização,
  nunca com autorização adicional;
- explicar suas próprias limitações e a diferença entre draft, fato e projeção.

Uma capacidade nova do produto pertence ao Lab Agent por padrão. A exceção exige justificativa
neste ADR ou num sucessor, não o inverso.

## Fronteira: autoridade, não capacidade

O Lab Agent não possui autoridade humana e não a simula. Ele não pode:

- aceitar, rejeitar ou superseder uma revision, nem preencher uma decisão em nome do humano;
- produzir `HumanAttestationRecord`, `human_review` ou adjudicação;
- conceder Artifact Access Grant, efeito externo ou acesso a `sensitive`/`restricted` sem grant
  válido para o próprio Lab Agent;
- enviar chat, hipótese, rubrica oculta ou resultado de outra variant ao Subject;
- escrever, editar ou reordenar o event ledger;
- apresentar draft, sugestão ou Progress Artifact como fato.

Quando uma ação exige autoridade humana, o Lab Agent produz um pedido de aprovação, nunca a
decisão.

**"Hidden" é oculto do Subject, não do Lab Agent.** Hidden graders, calibração e a hipótese do
laboratório são invisíveis ao Subject por desenho do `SubjectEnvelope`. O Lab Agent ajuda a
construí-los e portanto os vê, dentro do escopo do que o humano já vê. Classificação
`sensitive`/`restricted` continua exigindo grant.

## Contexto do Lab Agent é declarado

O Lab Agent recebe um `LabAgentEnvelope`: escopo de workspace e project, contracts e revisions
visíveis, evidência autorizada por referência, histórico da própria sessão de chat e o catálogo de
capabilities e limitações efetivas do produto.

O envelope é explícito por três razões. O ADR 0002 já proíbe "um agente mestre com acesso implícito
a tudo". Um agente que responde sobre evidência precisa citar a referência exata que leu. E um
contexto declarado é a única forma de o produto explicar ao usuário por que o agente respondeu o
que respondeu.

Credenciais nunca entram no envelope.

## Separação de nomes

Três termos usam a palavra "subject" e não são o mesmo:

- **Subject Agent** — o sistema sob teste dentro de uma Run; recebe `SubjectEnvelope`;
- **authority subject** — o conteúdo assinado numa attestation humana (`HumanSubjectEnvelope`,
  ADR 0015); é o objeto de uma assinatura, não um agente;
- **Lab Agent** — o copiloto do Control Plane; nunca é Subject de uma Run que ele mesmo propôs.

# Consequências

O Lab Agent deixa de ser descrito por proibição. Sua ausência passa a ser a lacuna de produto mais
importante, não um item de largura tardia: hoje ele não existe em `src/evidrun/`, e a página
`Laboratory` é mock.

O runtime mínimo do Lab Agent não depende de artifact grants, evaluation genérica ou trust modes.
Conversar, ler evidência autorizada e propor drafts exige loop de tools, envelope e as superfícies
públicas que já existem. A dependência de WS-50 sobre WS-20, WS-30 e WS-40 valia para bounded
exploration, não para o copiloto, e é separada.

O escopo amplo aumenta a superfície de teste adversarial. Todo caminho novo do Lab Agent exige
prova de que ele não produziu autoridade, não vazou para o Subject e não apresentou draft como
fato. Essa é a garantia que o rigor do produto vende.

A fronteira permanece verificável porque é estrutural: o Lab Agent chama as mesmas superfícies
públicas, e essas superfícies já falham fechadas sem attestation verificada.
