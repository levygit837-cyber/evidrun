---
id: planning-task-lab-agent-memory
type: implementation-task
title: WS-07 Memoria operacional e consolidador
status: proposed
authority: planning
volatility: snapshot
owner: laboratory
created_at: 2026-07-26
updated_at: 2026-07-31
observed_at: 2026-07-31
review_due: 2026-08-23
applies_to: lab-agent-memory
sources:
  - docs/adr/0021-hierarchical-lab-agent-scope.md
  - docs/contracts/lab-agent-memory-v2.md
  - docs/contracts/lab-agent-scope-v1.md
  - docs/adr/0018-lab-agent-copilot-scope.md
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
---

# WS-07 — Memoria operacional e consolidador

`workstream_state: blocked`

## Resultado pratico

O Lab Agent para de recomecar de zero. Ele recupera regras do usuario, decisoes anteriores e achados
de Runs passadas por descoberta orientada a pergunta, e cada draft que propoe declara quais memorias o
informaram.

Depende de WS-04, porque memoria sem loop de tools nao tem consumidor. Nao depende de WS-05, WS-06,
WS-20, WS-30 nem WS-40.

## O que este brief NAO e

Nao e arquivo Markdown com titulos `###` e leitura por intervalo de linhas. Essa forma foi
considerada e rejeitada pelo ADR 0019 e preservada pelo ADR 0021: o consolidador reescreve o conteudo, offsets deslocam, e uma
leitura por `start|end` obtida antes da reescrita devolve o meio de outra memoria sem erro e sem
sinal. Contexto errado silencioso e a pior falha possivel para este produto.

Nao e memoria global nem busca cross-Project. Workspace e o hard boundary; `project_id` opcional
separa linhas de investigacao, conforme o ADR 0021.

Nao e evidencia. Nenhuma entrada entra no ledger, no bundle ou no `SubjectEnvelope`.

## Escopo

### Persistencia

Tabela `memory_entries` conforme
[Memoria operacional do Lab Agent v2](../../contracts/lab-agent-memory-v2.md), com migration
Alembic na ordem real de merge, mais indice FTS5 sobre `title`, `cues` e `anti_cues`.

`body` **nao** e indexado.

Indices obrigatorios cobrem `(workspace_id, project_id, status)` e o caso `project_id IS NULL`,
porque toda consulta e hierarquicamente escopada.

Validacao na escrita rejeita, no minimo: `kind=observation` sem `evidence_refs` ou sem `sample_size`,
`cues` vazio, ausencia de `workspace_id`, `status=superseded` sem `superseded_by`, `status=active` sem
`promoted_at`, Project fora do Workspace, `relates_to` cruzando Workspace/Project e `body`
materializando `sensitive`/`restricted`.

Como v1 nao foi implementado em `main`, a primeira migration cria o shape v2 diretamente. Se um
import explicito ou banco pre-release trouxer entries v1, preserve-as com `project_id=null`; nao
infira Project de title, cue, body ou ref. Reclassificacao cria nova entrada e supersede a anterior.

Correcao cria entrada nova e marca a anterior `superseded`. Nenhum caminho faz UPDATE de `body`.

### Tools

Exatamente duas capabilities de memoria expostas ao Lab Agent:

- `memory_search(query, kind?, limit)` — devolve `id`, `title`, `cues`, `kind`, scope,
  `sample_size` e snippet. **Nao devolve `body`.** General chat consulta apenas entries de Workspace;
  Project/Focused chat consulta entries de Workspace mais o Project exato. O repository deriva esse
  filtro da sessao; a tool nao aceita override.
- `memory_read(ids[])` — devolve entradas inteiras. Teto de entradas por turno aplicado antes de
  anunciar suporte. Id de outro Workspace, Project irmao ou com `status` diferente de `active` e
  recusado, nao truncado.

Nao existe operacao que devolva o conjunto completo, nem leitura por posicao, offset ou linha. O
guardrail e ausencia de capacidade, nao lista de proibicoes: nao ha o que bloquear porque nao ha
caminho.

### Consolidador em background

Worker separado que le sessoes de chat, Runs e specs dentro do scope que consolida e escreve
entradas com `status=candidate`.

Requisitos:

- roda como processo proprio, nao dentro do request de chat;
- e idempotente sobre a mesma janela de origem: reprocessar nao duplica entrada;
- escreve `provenance` discriminada apontando para a origem exata;
- para `kind=observation`, extrai `evidence_refs` reais da Run. Se nao conseguir, **nao escreve a
  entrada** — nao inventa ref e nao rebaixa o kind para contornar a validacao;
- observation de Run herda o Project canonico; rule/preference usa Workspace por default e
  decision/observation/episode de Project chat usa o Project;
- escreve `cues` como perguntas e nao como palavras-chave, deliberadamente mais amplas que o contexto
  de origem, mais `anti_cues` quando a entrada tem vizinhanca confundivel.

### Promocao humana

Superficie para listar `candidate`, promover para `active` e recusar com motivo. `candidate` nunca
aparece em `memory_search`.

Promocao e curadoria de contexto, nao autoridade sobre evidencia: nao exige
`HumanAttestationRecord`. Isso e deliberado e permanece no ADR 0021.

### Proveniencia de uso

Toda chamada de `memory_search`/`memory_read` registrada na sessao, com ids retornados e lidos.

Todo draft proposto pelo Lab Agent carrega `informed_by` com os ids que o informaram. Draft sem esse
campo nao e apresentado como fundamentado.

## Invariantes que nao podem ser relaxadas

- **Scope hierarquico imposto no repositorio.** Workspace e hard boundary; Project opcional nunca e
  argumento livre de prompt/tool.
- **`body` fora do indice.** Buscar no corpo reintroduz o custo que o desenho de dois estagios existe
  para evitar.
- **`candidate` invisivel ao retrieval.** Memoria nao promovida nao informa draft.
- **`observation` sem ref nao existe.** A regra do repositorio sobre resultados de Run vale aqui.
- **Append-only.** Nenhum UPDATE destrutivo de conteudo.
- **Zero no `SubjectEnvelope`.** Nenhuma entrada, campo ou derivacao, por nenhum caminho.
- **Zero no ledger.** Memoria nao e evento e nao e record canonico.
- **Credencial nunca entra.** Em nenhum campo.
- **Relacao declarada na escrita.** Nada de inferencia de relevancia em runtime.

## Testes obrigatorios

- `memory_search` de outro Workspace nao retorna nada, mesmo com termo exato correspondente;
- General chat nao recupera entry de Project; Project chat recupera Workspace + proprio Project;
- Project chat nunca recupera entry de Project irmao nem revela sua contagem;
- `memory_search` nunca inclui `body` na resposta;
- termo presente somente no `body` nao produz hit;
- `memory_read` de id `candidate` e recusado; de id de outro Workspace, recusado;
- `memory_read` de id de Project irmao e recusado;
- teto de entradas por turno aplicado, com terminal observavel;
- `kind=observation` sem `evidence_refs` rejeitado na escrita;
- correcao produz entrada nova e preserva a anterior como `superseded` com ponteiro;
- entrada `rejected` preservada com motivo;
- consolidador idempotente: duas passagens na mesma janela nao duplicam;
- consolidador que nao consegue extrair ref nao escreve `observation`;
- observation de Run recebe o Project real e migration v1 nao infere Project;
- draft proposto carrega `informed_by` com os ids efetivamente lidos;
- nenhuma entrada de memoria aparece no `SubjectEnvelope` compilado, por assercao explicita;
- nenhuma escrita em `run_events` por caminho de memoria.

## Medicao do proprio recurso

O ganho da memoria e hipotese declarada, nao resultado, ate ser medido. A medicao usa o proprio
produto: Study com variants `sem memoria`, `so cues` e `cues mais corpo` sobre o mesmo material, com
metrica de quantas correcoes humanas o draft precisou.

Enquanto essa medicao nao existir, nenhum doc afirma que memoria melhora a qualidade dos drafts.

## Criterio de saida

O usuario declara uma preferencia de Workspace e uma decisao de Project; ambas aparecem como
`candidate` e sao promovidas. Em sessao posterior do mesmo Project, o Lab Agent recupera as duas por
perguntas que nao usam as mesmas palavras. Em General chat, recupera somente a preferencia; em
Project irmao, nunca recupera a decisao. O draft mostra quais memorias o informaram, nenhum caminho
le o conjunto completo e nenhuma memoria alcanca o Subject.
