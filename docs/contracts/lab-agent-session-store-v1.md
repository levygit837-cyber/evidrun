---
id: contract-lab-agent-session-store-v1
type: contract
title: Persistência de sessão e rastro do Lab Agent v1
status: accepted
authority: normative
volatility: timeless
owner: core
created_at: 2026-08-02
updated_at: 2026-08-02
applies_to: schema/lab-agent-session-store@1
sources:
  - docs/adr/0021-hierarchical-lab-agent-scope.md
  - docs/adr/0024-lab-agent-native-tool-runtime.md
  - docs/contracts/lab-agent-scope-v1.md
  - docs/contracts/lab-agent-tools-v1.md
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
---

# Persistência de sessão e rastro do Lab Agent v1

Este contrato declara como sessão, mensagem e rastro de tool são persistidos, e o que a migração do
storage genérico atual precisa preservar. Está aceito e ainda não possui runtime.

Formas de sessão e regras de pertencimento pertencem ao [escopo v1](lab-agent-scope-v1.md). Este
documento trata apenas de armazenamento e leitura.

## Ponto de partida medido

O storage existente não satisfaz o ADR 0021. Medido em `main` no commit `c967c16`:

| Fato | Estado |
| --- | --- |
| `ChatSessionRow.scope_type` | `String` anulável, sem enum |
| `ChatSessionRow.scope_id` | `String` anulável, sem chave estrangeira |
| validação de pertencimento | ausente na escrita e na leitura |
| `create_chat_session` | aceita `scope_type` e `scope_id` como texto livre |
| listagem de sessões | sem filtro por Workspace |
| cobertura de teste | nenhuma |

O contrato de escopo v1 descreve esses campos como "costura de persistência genérica". A medição mostra
algo mais forte: a listagem sem filtro é violação ativa de fronteira, porque projeta `workspace_id` de
toda sessão de todo Workspace. Corrigir isso é pré-requisito do runtime.

## Sessão

| Campo | Tipo | Obrigatório | Regra |
| --- | --- | --- | --- |
| `id` | id | sim | gerado pelo sistema, estável |
| `workspace_id` | ref | sim | Workspace existente; hard boundary |
| `project_id` | ref | não | quando presente, pertence ao `workspace_id` |
| `focus_kind` | enum | condicional | `study`, `run` ou `comparison`; exige `project_id` |
| `focus_id` | ref | condicional | pertence ao Project; exige `focus_kind` |
| `title` | texto | sim | rótulo humano, não identidade |
| `created_at` | timestamp | sim | UTC, atribuído pelo sistema |

O scope é imutável após a criação. Não existe operação de atualização de `workspace_id`, `project_id`,
`focus_kind` ou `focus_id`. Trocar de Project ou de foco cria ou retoma outra sessão.

Rejeitado na escrita: ausência de `workspace_id`; `project_id` de outro Workspace; foco sem
`project_id`; foco que não pertence ao Project; `focus_kind` sem `focus_id` ou o inverso; scope
desconhecido.

A validação de pertencimento acontece na escrita **e** na leitura. Só na escrita seria insuficiente:
uma linha gravada antes da constraint, ou por caminho interno, atravessaria a fronteira na leitura.

## Mensagem

| Campo | Tipo | Obrigatório | Regra |
| --- | --- | --- | --- |
| `id` | id | sim | gerado pelo sistema |
| `session_id` | ref | sim | sessão existente |
| `role` | enum | sim | `human`, `agent` ou `system_note` |
| `content` | texto | sim | conteúdo da mensagem |
| `sequence` | inteiro | sim | monotônico por sessão, sem lacuna |
| `created_at` | timestamp | sim | UTC |

`role` é enum fechado. O texto livre atual permite qualquer valor, o que torna impossível distinguir
mensagem humana de mensagem de agente com garantia — e essa distinção é a base de toda a fronteira de
autoridade.

`sequence` existe porque ordem por timestamp é ambígua sob escrita concorrente, e o transcript enviado
ao provider precisa ser reproduzível.

Mensagens são append-only. Correção cria mensagem nova; não existe update nem delete.

## Rastro de tool

| Campo | Tipo | Obrigatório | Regra |
| --- | --- | --- | --- |
| `id` | id | sim | gerado pelo sistema |
| `session_id` | ref | sim | sessão existente |
| `turn_sequence` | inteiro | sim | turno dentro da sessão |
| `tool_name` | texto | sim | nome do catálogo |
| `arguments_digest` | digest | sim | digest canônico dos argumentos |
| `requested_refs` | lista de ref | não | refs que a chamada pediu |
| `returned_refs` | lista de ref | não | refs efetivamente devolvidas |
| `outcome` | enum | sim | `completed`, `refused` ou `failed` |
| `refusal_code` | enum | condicional | obrigatório quando `outcome=refused` |
| `scope_snapshot` | objeto | sim | scope efetivo no momento da chamada |
| `created_at` | timestamp | sim | UTC |

`requested_refs` e `returned_refs` são campos separados de propósito. A diferença entre os dois
conjuntos é a evidência de que o enforcement recusou algo, e é o que permite ao humano ver o que o
agente tentou ler. Um único campo apagaria a tentativa.

`arguments_digest` em vez dos argumentos brutos: argumento pode conter texto longo de draft, e o rastro
não é cópia do conteúdo. O digest é suficiente para provar repetição exata, que é o que o
[loop v1](lab-agent-loop-v1.md) precisa detectar.

O rastro é do Control Plane e vive **fora** do event ledger. O ledger é a autoridade normativa da Run e
o Lab Agent não escreve nele. Nenhuma linha de rastro é Event, nenhuma entra em bundle e nenhuma
alcança o `SubjectEnvelope`.

## Leitura escopada

Toda leitura deriva seu filtro do scope da sessão, nunca de parâmetro do cliente:

```text
listar sessões:
  workspace_id = <workspace da requisição>

General chat, navegação de Projects:
  workspace_id = session.workspace_id
  -> devolve id, name, created_at; nada mais

Project/Focused chat, conteúdo:
  workspace_id = session.workspace_id
  AND project_id = session.project_id

Focused chat, leitura estreitada:
  filtro de Project mais a entidade em foco
```

Não existe parâmetro de API, CLI ou tool que substitua esse filtro. Não existe leitura sem
`workspace_id`. Não existe agregação que cruze Projects.

Um id conhecido de outro Project produz o mesmo resultado que um id inexistente, conforme
[erros v1](lab-agent-errors-v1.md): a recusa não revela existência.

## Migração

A migração converte `scope_type`/`scope_id` no shape tipado e precisa:

- preservar ids, ordem e conteúdo de toda sessão e mensagem existentes;
- manter `workspace_id` como fronteira de toda sessão migrada;
- recusar estado ambíguo em vez de inferir Project;
- nunca deduzir Project a partir de título, conteúdo de mensagem ou ref citada;
- atribuir `sequence` por ordem de `created_at` estável, com desempate determinístico por `id`;
- normalizar `role` desconhecido para `system_note`, preservando o valor original no conteúdo.

Falha fechada: uma linha cujo `scope_type` não mapeie para forma válida, ou cujo `scope_id` não resolva
para entidade do Workspace, interrompe a migração com erro que nomeia a linha. Ela não é convertida em
General chat por conveniência, porque isso silenciosamente ampliaria escopo.

O contrato de memória v2 já decidiu que entries v1 permanecem com `project_id=null` sem inferência. A
mesma regra vale aqui e pela mesma razão.

## Composição no repository

O store do Lab Agent é um agregado novo no repository, alcançável por atributo, compartilhando o mesmo
`UnitOfWork` dos demais. Ele não é adicionado ao `CatalogStore`: catálogo é registro genérico de
entidades e a validação de pertencimento tipada é responsabilidade própria.

## Provas mínimas

- sessão sem `workspace_id` é recusada;
- `project_id` de outro Workspace é recusado na escrita e na leitura;
- foco sem Project, e foco de outro Project, são recusados;
- scope é imutável: não existe caminho de atualização;
- listagem de sessões filtra por Workspace e não projeta sessão de outro;
- General chat devolve apenas id, nome e data de Projects;
- Project chat lê o próprio Project e recusa Project irmão com o código de não visível;
- `role` fora do enum é recusado;
- `sequence` é monotônico e sem lacuna por sessão;
- mensagem é append-only;
- rastro distingue `requested_refs` de `returned_refs`;
- rastro registra `refusal_code` em toda recusa;
- nenhuma linha de rastro é Event nem entra em bundle;
- migração preserva ids, ordem e conteúdo, e falha fechada em scope ambíguo;
- migração não infere Project a partir de texto.
