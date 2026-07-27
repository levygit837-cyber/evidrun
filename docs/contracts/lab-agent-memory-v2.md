---
id: contract-lab-agent-memory-v2
type: contract
title: Memória operacional hierárquica do Lab Agent v2
status: accepted
authority: normative
volatility: timeless
owner: core
created_at: 2026-07-27
updated_at: 2026-07-27
applies_to: schema/lab-agent-memory@2
sources:
  - docs/adr/0021-hierarchical-lab-agent-scope.md
  - docs/contracts/lab-agent-scope-v1.md
supersedes:
  - docs/contracts/lab-agent-memory-v1.md
superseded_by: null
implementation_refs: []
verification_refs: []
---

# MemoryEntry v2

Este contrato sucede o v1 somente para acrescentar subescopo de Project e regras de retrieval
hierárquico. Mantém SQLite/FTS5, cues, leitura em dois estágios, append-only, promoção humana e
proveniência de uso. Está aceito; nenhum runtime de memória está implementado.

## Campos

| Campo | Tipo | Obrigatório | Regra |
| --- | --- | --- | --- |
| `id` | id | sim | identidade estável; não reutilizada após supersessão |
| `workspace_id` | ref | sim | hard boundary; nenhuma entrada existe fora de Workspace |
| `project_id` | ref | não | subescopo; quando presente pertence ao `workspace_id` |
| `kind` | enum | sim | `rule`, `preference`, `decision`, `observation`, `episode` |
| `title` | texto | sim | asserção única e legível; não é rótulo genérico |
| `cues` | lista de texto | sim | perguntas que a entrada responde; mínimo 1 |
| `anti_cues` | lista de texto | não | assuntos que a entrada não cobre |
| `body` | texto | sim | regra, racional, relato ou achado |
| `evidence_refs` | lista de ref | condicional | `run:`, `event:` ou `artifact:`; obrigatório para `observation` |
| `provenance` | objeto | sim | `chat_session`, `run`, `study_spec` ou `human_declaration` |
| `status` | enum | sim | `candidate`, `active`, `superseded`, `rejected` |
| `superseded_by` | id | condicional | obrigatório quando `status=superseded` |
| `rejection_reason` | texto | condicional | obrigatório quando `status=rejected` |
| `relates_to` | lista de id | não | relações declaradas na escrita e visíveis no mesmo scope |
| `sample_size` | inteiro | condicional | número de Runs que sustenta `observation` |
| `created_at` | data | sim | — |
| `promoted_at` | data | condicional | obrigatório quando `status=active` |

`ArtifactRef` continua sem locator e não concede acesso.

## Escolha do subescopo

- `rule` e `preference` são de Workspace por default. Podem ser de Project somente quando a
  declaração disser que vale exclusivamente para aquela linha de investigação.
- `decision`, `observation` e `episode` originadas numa Project/Focused chat são do Project.
- `observation` derivada de Run herda obrigatoriamente o Project resolvido pela Study/RunSpec.
- General chat só produz entrada de Workspace; não infere Project a partir de texto ou ref citada.
- O humano pode declarar explicitamente uma entrada de Workspace, mas não pode omitir o Project de
  uma provenance de Run.

O v1 nunca foi implementado em `main`, portanto a primeira migration pode criar diretamente o shape
v2. Se um import explícito ou banco pré-release contiver entries v1, elas permanecem com
`project_id=null`; nada tenta deduzir Project de `body`, title, cue ou relation. Reclassificação
posterior cria nova entrada/supersessão explícita.

## Regras de validação

Rejeitadas na escrita:

- ausência de `workspace_id`;
- `project_id` que não pertence ao Workspace;
- `kind=observation` sem `evidence_refs` não vazio ou sem `sample_size`;
- provenance de Run sem o Project exato da Run;
- `cues` vazio;
- `status=superseded` sem `superseded_by`;
- `status=rejected` sem `rejection_reason`;
- `status=active` sem `promoted_at`;
- entry de Workspace relacionada a entry de Project;
- entry de Project relacionada a outro Project; ela pode relacionar entry do mesmo Project ou de
  Workspace visível a ele;
- qualquer campo contendo credencial;
- `body` materializando conteúdo `sensitive` ou `restricted`.

## Ciclo de vida

```text
candidate --(promoção humana)--> active --(correção)--> superseded
candidate --(recusa humana)----> rejected
```

`candidate` não é elegível para retrieval. Correção cria entrada nova e preserva a anterior;
mudança de scope também é correção, não UPDATE de conteúdo ou `project_id`.

`observation` ativa é exibida com `sample_size`, idade e evidence refs e nunca como fato sem eles.

## Descoberta hierárquica

FTS5 indexa somente `title`, `cues` e `anti_cues`. `body` não é indexado nem buscável.

O repository deriva o filtro do `LabAgentSessionScope`:

```text
General chat:
  workspace_id = session.workspace_id
  AND project_id IS NULL
  AND status = active

Project/Focused chat:
  workspace_id = session.workspace_id
  AND (project_id IS NULL OR project_id = session.project_id)
  AND status = active
```

Não existe parâmetro de tool que substitua esse filtro.

### memory_search

Entrada: `query`, `kind` opcional e `limit` com teto declarado.

Saída por candidato: `id`, `title`, `cues`, `kind`, `workspace_id`, `project_id`, `sample_size` e
`snippet`. Não devolve `body`. Ranking não pode fazer uma entry de outro scope aparecer como hit
parcial ou contagem agregada.

### memory_read

Entrada: lista de `id`. Saída: entries completas autorizadas, com provenance e evidence refs.

Teto por turno é aplicado antes de anunciar suporte. Id de outro Workspace, de outro Project ou com
status diferente de `active` é recusado, não omitido silenciosamente. Não existe operação de dump,
offset, intervalo de linha ou “todas as memórias”.

## Consolidação e promoção

O consolidador roda fora do request de chat, é idempotente por janela de origem e escreve
`candidate`. Ele lê somente fontes autorizadas no scope que está consolidando. Para
`kind=observation`, precisa resolver evidence refs e Project reais; sem isso, não escreve a entry e
não rebaixa o kind para contornar a validação.

Promoção é curadoria de contexto, não authority sobre evidência: não exige
`HumanAttestationRecord`, não aceita contract e não substitui `EvaluationRecord`.

## Proveniência de uso e fronteiras

Toda chamada de `memory_search`/`memory_read` registra sessão, scope, ids retornados e ids lidos. Todo
draft fundamentado declara `informed_by`; Project e Workspace das entries precisam ser compatíveis
com o scope do draft.

MemoryEntry é Control Plane, não Event, record de Run ou fato de bundle. Nenhuma entry, cue, body ou
derivação entra no SubjectEnvelope. Não existe memória global nem compartilhada entre Workspaces ou
Projects por busca implícita.

## Provas mínimas

- General chat recupera entry de Workspace e não recupera entry de Project;
- Project chat recupera entries do Workspace pai e do próprio Project, mas não de Project irmão;
- termo exato em outro scope não altera hit, count ou snippet;
- `body` não aparece em `memory_search` e termo apenas no `body` não produz hit;
- `candidate`, id cross-scope e teto por turno falham conforme o contrato;
- Run observation recebe Project canônico e exige refs/sample size;
- migration v1 preserva entries como Workspace scope sem inferência;
- draft registra `informed_by` e nenhuma memória alcança o Subject.
