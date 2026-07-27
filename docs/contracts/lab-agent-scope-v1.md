---
id: contract-lab-agent-scope-v1
type: contract
title: Escopo de sessão e envelope do Lab Agent v1
status: accepted
authority: normative
volatility: timeless
owner: core
created_at: 2026-07-27
updated_at: 2026-07-27
applies_to: schema/lab-agent-scope@1
sources:
  - docs/adr/0018-lab-agent-copilot-scope.md
  - docs/adr/0021-hierarchical-lab-agent-scope.md
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
---

# Escopo de sessão e envelope do Lab Agent v1

Este contrato está aceito e ainda não possui runtime. Ele define a mesma fronteira para chat,
envelope, tools e memória, evitando que cada superfície interprete `scope_type/scope_id` de forma
diferente.

## LabAgentSessionScope

| Campo | Tipo | Obrigatório | Regra |
| --- | --- | --- | --- |
| `workspace_id` | ref | sim | hard boundary da sessão |
| `project_id` | ref | não | quando presente, pertence ao Workspace |
| `focus_kind` | enum | condicional | `study`, `run` ou `comparison`; exige `project_id` |
| `focus_id` | ref | condicional | identidade do foco; exige `focus_kind` e pertence ao Project |

Formas válidas:

| Forma | Campos | Leitura normal |
| --- | --- | --- |
| General chat | somente `workspace_id` | metadata de navegação, regras e preferências do Workspace |
| Project chat | `workspace_id` + `project_id` | conteúdo autorizado do Project mais regras/preferências do Workspace |
| Focused chat | Project chat + foco | subconjunto normalmente relacionado ao foco declarado |

Não são válidos: sessão sem Workspace, Project de outro Workspace, foco sem Project, foco de outro
Project, dois focos ou scope genérico desconhecido.

O scope é imutável durante a sessão. Mudar Workspace, Project ou foco cria ou retoma outra sessão.
Mensagens antigas não são copiadas automaticamente para o novo scope e um resumo não concede
acesso às refs que menciona.

## LabAgentEnvelope

O envelope contém:

- `scope` exato;
- ref da sessão e histórico autorizado da própria sessão;
- refs de contracts/revisions visíveis;
- refs de evidência autorizada, sem locator;
- capabilities e limites efetivamente oferecidos ao Lab Agent;
- refs de memória recuperadas conforme o contrato v2, quando essa capability existir.

Ele não contém credenciais, bytes de Artifact por consequência de uma ref, conteúdo de outro
Project, chat de outra sessão, nem qualquer authority adicional. O digest do envelope cobre scope e
refs; trocar Project produz outro documento e outro digest.

## Enforcement de tool

Toda tool recebe o scope a partir da sessão validada, não de argumentos produzidos pelo modelo. Uma
tool pode receber uma ref de alvo, mas resolve seu pertencimento antes de retornar dados ou produzir
draft.

General chat pode listar ids, nomes e metadata mínima de Projects do Workspace para navegação. Não
lista contracts, Runs, EvaluationRecords, artifacts, mensagens ou MemoryEntries de cada Project.

Project chat pode operar as superfícies públicas autorizadas para o Project exato. Focused chat usa
o mesmo limite e pode estreitar a query ao foco. Nenhuma forma lê outro Project por id conhecido,
texto de busca, relation, ref indireta ou resultado de memória.

Falha de pertencimento é indistinguível de alvo não visível para o agente e não revela metadata do
outro scope. O repository registra a tool, a sessão, o scope, as refs solicitadas e as refs
efetivamente retornadas; conteúdo sensível segue os contratos de grant/classification.

## Drafts e autoridade

Um draft criado pelo Lab Agent herda o Project da sessão. General chat pode ajudar a navegar ou criar
um Project, mas precisa entrar numa Project chat antes de registrar draft de contract de autoria. O
cliente não fornece `project_id` divergente para sobrepor a sessão.

Draft nunca é decision. O Lab Agent não produz `HumanAttestationRecord`, human review, adjudicação,
grant, efeito externo ou evento factual de Run. Pedido de aprovação preserva scope e digest do draft,
sem preencher decisão em nome do humano.

## Compatibilidade de storage

Os campos atuais `ChatSessionRow.scope_type/scope_id` são uma costura de persistência genérica, não o
contrato final. A implementação pode migrá-los ou projetá-los para o shape tipado, mas precisa:

- validar pertencimento no write e no read;
- preservar ids, ordem e mensagens existentes;
- recusar estado ambíguo em vez de inferir Project por conteúdo do chat;
- manter General chat como Workspace scope, nunca como global.

“Project Room” é somente apresentação de uma Project chat com suas entidades relacionadas. Não cria
outro schema de sessão nem outro Lab Agent.

## Provas mínimas

- uma ref de outro Workspace ou Project é recusada no repository mesmo se o prompt pedir acesso;
- General chat lista Project metadata, mas não retorna conteúdo de Project;
- Project chat vê regras de Workspace e conteúdo do próprio Project, nunca do vizinho;
- Focused chat rejeita entidade que não pertença ao Project;
- trocar Project não muta o scope nem o histórico da sessão original;
- draft herda o Project do scope e permanece sem decision;
- nenhum campo novo entra no SubjectEnvelope.
