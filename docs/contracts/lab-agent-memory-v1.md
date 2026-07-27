---
id: contract-lab-agent-memory-v1
type: contract
title: Memória operacional do Lab Agent v1
status: accepted
authority: normative
owner: core
created_at: 2026-07-26
updated_at: 2026-07-26
applies_to: schema/lab-agent-memory@1
sources:
  - docs/adr/0019-lab-agent-operational-memory.md
  - docs/adr/0018-lab-agent-copilot-scope.md
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
---

# MemoryEntry

Contrato de uma entrada de memória operacional do Lab Agent, conforme o
[ADR 0019](../adr/0019-lab-agent-operational-memory.md). O contrato está aceito; nenhum runtime o
implementa ainda.

## Campos

| Campo | Tipo | Obrigatório | Regra |
| --- | --- | --- | --- |
| `id` | id | sim | identidade estável; não reusada após supersessão |
| `workspace_id` | ref | sim | escopo; nenhuma entrada existe fora de um Workspace |
| `kind` | enum | sim | `rule`, `preference`, `decision`, `observation`, `episode` |
| `title` | texto | sim | asserção única e legível; não é rótulo genérico |
| `cues` | lista de texto | sim | perguntas que a entrada responde, na forma como o usuário perguntaria; mínimo 1 |
| `anti_cues` | lista de texto | não | assuntos que a entrada não cobre |
| `body` | texto | sim | conteúdo: regra, racional, relato ou achado |
| `evidence_refs` | lista de ref | condicional | `run:`, `event:` ou `artifact:`; obrigatório e não vazio quando `kind=observation` |
| `provenance` | objeto | sim | origem discriminada: `chat_session`, `run`, `study_spec` ou `human_declaration` |
| `status` | enum | sim | `candidate`, `active`, `superseded`, `rejected` |
| `superseded_by` | id | condicional | obrigatório quando `status=superseded` |
| `rejection_reason` | texto | condicional | obrigatório quando `status=rejected` |
| `relates_to` | lista de id | não | relação declarada na escrita; nunca inferida na leitura |
| `sample_size` | inteiro | condicional | número de Runs que sustentam um `observation` |
| `created_at` | data | sim | — |
| `promoted_at` | data | condicional | obrigatório quando `status=active` |

`ArtifactRef` dentro de `evidence_refs` continua sem locator e continua não concedendo acesso.

## Regras de validação

Rejeitadas na escrita:

- `kind=observation` com `evidence_refs` vazio ou ausente;
- `kind=observation` sem `sample_size`;
- `cues` vazio;
- entrada sem `workspace_id`;
- `status=superseded` sem `superseded_by`;
- `status=rejected` sem `rejection_reason`;
- `status=active` sem `promoted_at`;
- `relates_to` apontando para entrada de outro Workspace;
- qualquer campo contendo credencial;
- `body` materializando conteúdo `sensitive` ou `restricted`.

## Ciclo de vida

```text
candidate --(promoção humana)--> active --(correção)--> superseded
candidate --(recusa humana)----> rejected
```

`candidate` **não é elegível para retrieval**. `rejected` é preservado com motivo, nunca apagado.

Correção não edita: cria entrada nova e marca a anterior como `superseded`. É append-only, como
`EvaluationRecord` e revisions.

Uma entrada `active` cujo `kind` é `observation` decai: `sample_size` e a idade das `evidence_refs`
são apresentados junto com o conteúdo, e a entrada nunca é apresentada como fato sem eles.

## Descoberta

Índice de texto sobre `title`, `cues` e `anti_cues`. **`body` não é indexado e não é buscável.**

Escopo obrigatório da consulta: `workspace_id` e `status=active`.

### memory_search

Entrada: `query`, `kind` opcional, `limit` com teto declarado.

Saída, por candidato: `id`, `title`, `cues`, `kind`, `sample_size` e `snippet`. **Não devolve `body`.**

### memory_read

Entrada: lista de `id`.

Saída: entradas completas, com `provenance` e `evidence_refs`.

Teto de entradas por turno aplicado antes de anunciar suporte. Id fora do Workspace da sessão, ou com
`status` diferente de `active`, é recusado — não truncado.

Não existe operação que devolva o conjunto completo, nem leitura por posição, offset ou intervalo de
linha. Intervalo de linha não é representável neste contrato.

## Proveniência de uso

Toda chamada de `memory_search` e `memory_read` é registrada na sessão de chat, com os ids
retornados e lidos.

Todo draft de contract proposto pelo Lab Agent declara `informed_by`: os ids das entradas que
informaram a proposta. Um draft sem esse campo é proposta sem proveniência e não deve ser
apresentado ao humano como fundamentado.

## Fronteiras

- Memória é do Control Plane. Nenhuma entrada, campo ou derivação entra no `SubjectEnvelope`.
- Memória não é evidência: não entra no event ledger, não é record canônico de Run e não aparece em
  Evidence Bundle como fato.
- Uma entrada nunca aceita, rejeita ou supersede uma revision de contract, e nunca substitui um
  `EvaluationRecord`.
- Promoção de memória é curadoria de contexto, não autoridade sobre evidência: não exige
  `HumanAttestationRecord`.
- Escopo é o Workspace, sem exceção. Não existe memória global nem compartilhada entre Workspaces.
