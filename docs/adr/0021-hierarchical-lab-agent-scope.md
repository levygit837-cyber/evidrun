---
id: adr-0021
type: adr
title: Um Lab Agent com escopo hierárquico de sessão e memória
status: accepted
authority: normative
volatility: timeless
owner: product
created_at: 2026-07-27
updated_at: 2026-07-27
applies_to: lab-agent-scope-and-memory
sources:
  - docs/adr/0018-lab-agent-copilot-scope.md
  - docs/adr/0019-lab-agent-operational-memory.md
  - docs/adr/0020-workspace-project-run-environment-boundaries.md
supersedes:
  - docs/adr/0019-lab-agent-operational-memory.md
superseded_by: null
implementation_refs: []
verification_refs: []
---

# Contexto

O ADR 0018 deu ao Lab Agent escopo funcional amplo e o ADR 0019 isolou sua memória por Workspace.
Faltava decidir se cada Project teria um agente próprio, se um chat geral poderia ler todos os
Projects e como regras do Workspace coexistiriam com decisões e observações de uma única linha de
investigação. “Acesso ao app inteiro” podia ser interpretado incorretamente como acesso implícito a
todos os dados.

# Decisão

## O desenho possui um único papel e um runtime compartilhado de Lab Agent

Evidrun define um único papel de Lab Agent. Quando seu runtime for implementado, ele será
compartilhado entre os escopos e usará o mesmo catálogo de tools e a mesma fronteira de autoridade.
Criar um Project não cria modelo, processo, identidade, memória privada independente nem "agente
daquele Project". A continuidade percebida vem da sessão e da memória escopadas, não de uma instância
persistente por Project.

Escopo funcional amplo significa que novas capacidades públicas do produto podem ser oferecidas ao
Lab Agent. Não significa leitura ampla: cada invocação recebe um `LabAgentEnvelope` com escopo de
dados explícito e cada tool impõe esse escopo no repository.

## Sessões usam um escopo imutável e hierárquico

Toda sessão declara exatamente um Workspace. Ela pode declarar um Project do mesmo Workspace e,
opcionalmente, um foco (`Study`, `Run` ou `Comparison`) pertencente ao mesmo Project.

- **General chat:** `workspace_id` presente, `project_id` e foco ausentes. Pode listar identidades e
  metadata mínima de Projects para navegação, além de operar regras e preferências do Workspace. Não
  lê contracts, Runs, evidence ou memória específica de todos os Projects.
- **Project chat:** `workspace_id` e `project_id` presentes. Pode operar o conteúdo autorizado do
  Project e também regras/preferências de Workspace visíveis a qualquer Project.
- **Focused chat:** acrescenta uma entidade do mesmo Project e estreita o conjunto normal de leitura;
  não amplia o Project.

O escopo de uma sessão é imutável. Selecionar outro Project ou foco cria ou retoma uma sessão com o
novo escopo; não eleva silenciosamente uma sessão já aberta. “Project Room” é o nome possível dessa
projeção na UI, não um quarto tipo de agente.

Uma ref fornecida pelo modelo, pelo usuário ou pelo frontend não prova pertencimento. A tool resolve
a ref e verifica Workspace, Project, classification e grant aplicável antes da leitura ou escrita.
Refs de outro Project falham fechado. O prompt nunca é a fronteira de isolamento.

## Memória tem isolamento de Workspace e subescopo opcional de Project

Toda `MemoryEntry` mantém `workspace_id` obrigatório. `project_id` é opcional e, quando presente,
precisa pertencer ao mesmo Workspace.

Uma General chat recupera somente entradas de Workspace (`project_id=null`). Uma Project ou Focused
chat recupera a união de entradas de Workspace com entradas de seu Project exato; nunca entradas de
outro Project. `rule` e `preference` nascem no Workspace salvo quando explicitamente locais ao
Project. `decision`, `observation` e `episode` originadas numa Project chat nascem no Project. Uma
`observation` derivada de Run sempre herda o Project da Run.

Não existe retrieval cross-Project. Reutilização futura exige import ou seleção explícita com
proveniência, não uma busca global.

Este ADR substitui o escopo “Workspace sem exceção” do ADR 0019 pela hierarquia acima. Permanecem
vigentes as demais decisões: SQLite/FTS5, descoberta por cues sem indexar `body`, leitura em dois
estágios, append-only, promoção humana, evidência obrigatória para `observation`, ausência de
credenciais, memória fora do SubjectEnvelope e proveniência de uso em drafts.

# Alternativas rejeitadas

- Um agente persistente por Project: multiplica lifecycle, identidade, configuração e risco de drift
  sem produzir isolamento que um envelope e repository escopados não resolvam melhor.
- General chat com leitura automática de todos os Projects: transforma navegação em exfiltração
  implícita e torna impossível explicar qual contexto informou a resposta.
- Memória apenas por Workspace: mistura decisões e episódios de linhas de investigação independentes.
- Memória apenas por Project: duplica preferências e regras do usuário e perde consistência dentro do
  Workspace.
- Escopo imposto pelo prompt: uma ref inventada ou uma tool mal chamada atravessaria a fronteira.

# Consequências

Chat storage precisa representar e validar o escopo tipado; os campos genéricos `scope_type` e
`scope_id` existentes não bastam como contrato. Tools, drafts e logs de uso carregam o escopo efetivo
e refs consultadas. O contrato `MemoryEntry` ganha versão v2 e o WS-07 migra qualquer dado v1 sem
atribuir Project por inferência silenciosa.

O usuário pode manter uma conversa geral para organizar o Workspace e conversas por Project para
trabalho profundo, com comportamento consistente e um único Lab Agent. A UI pode mudar de Project
sem fingir que criou outro agente.
