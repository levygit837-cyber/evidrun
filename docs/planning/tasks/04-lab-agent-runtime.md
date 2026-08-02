---
id: planning-task-lab-agent-runtime
type: implementation-task
title: WS-04 Runtime do Lab Agent copiloto
status: proposed
authority: planning
volatility: snapshot
owner: laboratory
created_at: 2026-07-26
updated_at: 2026-08-02
observed_at: 2026-08-02
review_due: 2026-08-29
applies_to: lab-agent-runtime
sources:
  - docs/adr/0018-lab-agent-copilot-scope.md
  - docs/planning/comfortable-minimum.md
  - docs/adr/0006-provider-neutral-openai-first.md
  - docs/adr/0008-cliproxyapi-deepseek-default.md
  - docs/adr/0021-hierarchical-lab-agent-scope.md
  - docs/contracts/lab-agent-scope-v1.md
  - docs/contracts/lab-agent-memory-v2.md
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
---

# WS-04 — Runtime do Lab Agent copiloto

`workstream_state: queued`

## Resultado pratico

O usuario conversa com um unico Lab Agent no app. General chat organiza o Workspace; Project chat
produz drafts tipados e explicacoes ancoradas em evidencia do Project; Focused chat estreita o
contexto para Study, Run ou Comparison. A pagina `Laboratory` deixa de ser mock sem inventar um
agente persistente por Project.

Nao inclui bounded exploration, multi-turn do Subject, nested agents nem efeitos externos. Esses
ficam em WS-50.

## Por que nao depende de WS-20/30/40

O brief WS-50 original acoplava o copiloto a artifact grants, evaluation generica e trust modes. Esse
acoplamento valia para bounded exploration. Conversar, ler contracts e evidencia ja autorizada e
propor drafts nao exige nenhum dos tres: exige loop de tools, envelope declarado e as superficies
publicas que ja existem em `main`.

Depende de WS-01 porque um draft precisa de um Project real e publicamente alcançavel para
aterrissar. Criar esse Project nao cria Lab Agent, sessao ou memoria automaticamente.

## Escopo

### LabAgentEnvelope

Implementar o [contrato de escopo v1](../../contracts/lab-agent-scope-v1.md) na fronteira do Control
Plane. O envelope contem Workspace obrigatorio, Project e foco opcionais, refs dos contracts e
revisions visiveis, refs de evidencia autorizada, historico da propria sessao e o catalogo de
capabilities e limitacoes efetivas do produto.

Nunca contem credencial. `ArtifactRef` continua sem locator e continua nao concedendo acesso: o
envelope carrega a referencia, e a leitura passa por tool que verifica autorizacao.

### Sessoes

O mesmo aggregate de chat representa as tres formas. Scope e imutavel por sessao:

- General chat lista identidade/metadata minima de Projects para navegacao, mas nao le o conteudo de
  todos eles;
- Project chat le somente o Project exato mais regras/preferencias do Workspace pai;
- Focused chat adiciona Study, Run ou Comparison do mesmo Project e estreita a leitura;
- trocar Project/foco cria ou retoma outra sessao; nao reescopa a sessao aberta e nao copia mensagens
  automaticamente.

Os campos genericos `scope_type/scope_id` existentes precisam ser projetados ou migrados para o
contrato tipado com validacao de pertencimento. Estado ambiguo falha fechado; nao infira Project do
texto do chat.

### Loop e tools

Loop de function calling com budget de turnos e de tool calls aplicado antes de anunciar suporte.
Tools minimas, todas escopadas no repository ao que o humano ja pode ver:

- ler contract revision por ref;
- listar e ler Runs, eventos e EvaluationRecords do Project da sessao;
- ler Comparison e metricas agregadas;
- ler o catalogo de capabilities admitidas e o motivo exato de uma rejeicao de admissao.

E uma tool de proposta, que nao decide:

- registrar draft de contract de autoria como revision `draft`, sem decisao.

Toda chamada de tool e rastreada. O usuario tem que poder ver o que o agente leu.
`project_id` vindo como argumento do modelo nunca sobrepoe o scope da sessao; ref cross-Project e
recusada sem revelar metadata do alvo.

### Memoria

Memoria operacional hierarquica pertence a [WS-07](07-lab-agent-memory.md) e nao esta no escopo desta entrega.
Duas obrigacoes de WS-04 existem para nao fechar a porta:

- o loop de tools aceita capabilities novas sem mudar sua assinatura, para que `memory_search` e
  `memory_read` entrem como duas tools a mais e nao como refactor;
- o draft proposto carrega `informed_by`, mesmo vazio enquanto memoria nao existe. Adicionar
  proveniencia depois de a UI ja consumir drafts custa mais que declarar o campo agora.

### Provider

Reusa `ProviderPort` e o profile default do ADR 0008. Nao introduz provider novo e nao muda o default.
A presenca do provider nao promove nenhuma capability do Subject.

### Superficie

Os endpoints de chat existem (`POST /api/v1/chat/sessions`, `GET`, `POST .../messages`) e possuem
cobertura de integração para criação, listagem escopada por Workspace, ordem estável e mensagens.
Esta entrega amplia a cobertura e adiciona o caminho de streaming que
`apps/web/src/data/adapters.ts` hoje recusa com `integration_pending`.

## Invariantes que nao podem ser relaxadas

- **Zero autoridade.** Nenhum caminho do Lab Agent produz `HumanAttestationRecord`, decisao de
  revision, `human_review` ou adjudicacao. Acao que exige humano gera pedido de aprovacao.
- **Zero escrita no ledger.** O Lab Agent nao chama `append_event` por nenhum caminho.
- **Zero vazamento para o Subject.** Chat, hipotese, StudyIntent e rubrica oculta nao entram no
  `SubjectEnvelope`. O compilador do envelope continua allowlist fechada.
- **Draft nao e fato.** Toda proposta e apresentada como draft, com o contrato exato que seria
  registrado. Metrica sem Run e projecao, nao resultado.
- **Dominio nao importa provider.** `contracts/` e o dominio continuam sem HTTP.
- **Sem grant nao le classificado.** `sensitive` e `restricted` continuam negados.
- **Scope no repository.** Prompt, UI e ref conhecida nao concedem outro Workspace/Project.
- **Um Lab Agent.** Project Room e sessao escopada, nao outro agente, model profile ou memory store.

## Testes obrigatorios

- chat do laboratorio ausente do `SubjectEnvelope` compilado, para o mesmo Study;
- draft registrado sem decisao, e revision permanece nao aceita;
- pedido de aprovacao produzido sem attestation;
- tentativa de decisao pelo Lab Agent falha fechada, com o mesmo codigo que a API humana usa;
- budget de turnos e de tool calls aplicado, com terminal observavel;
- leitura de `sensitive` sem grant negada;
- rejeicao de admissao explicada com o codigo real, nao parafraseada;
- endpoints de chat cobertos, incluindo streaming e cancelamento;
- draft proposto expoe `informed_by`, vazio enquanto memoria nao existe.
- General chat lista Project metadata sem retornar contracts/Runs de Projects;
- Project chat le regras do Workspace e o proprio Project, mas recusa Project irmao;
- Focused chat recusa foco de outro Project;
- trocar Project preserva scope e mensagens da sessao original;
- draft herda `project_id` da sessao, sem aceitar override do modelo/cliente.

## Criterio de saida

Uma pessoa navega o Workspace em General chat, entra em um Project chat, descreve uma hipotese,
recebe drafts de Study, Scenario, Variants e EvaluationPlan, ve quais evidencias o agente leu,
aceita os drafts pelo caminho humano e chega a um RunSpec compilado. O mesmo Lab Agent muda de scope
sem ler outro Project e nenhum passo afirma autoridade que nao existe.
