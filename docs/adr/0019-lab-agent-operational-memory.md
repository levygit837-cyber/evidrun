---
id: adr-0019
type: adr
title: Memória operacional do Lab Agent com descoberta por cue e promoção humana
status: accepted
authority: normative
owner: product
created_at: 2026-07-26
updated_at: 2026-07-26
applies_to: lab-agent-memory
sources:
  - docs/adr/0018-lab-agent-copilot-scope.md
  - docs/adr/0009-study-run-contract-composition.md
  - docs/adr/0005-canonical-evidence-storage.md
  - docs/product/charter.md
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
---

# Contexto

O Lab Agent é a superfície primária de trabalho do produto (ADR 0018). Sem estado durável, ele
recomeça de zero em cada sessão: reaprende as preferências do usuário, reencontra o que uma Run
anterior mostrou e repete perguntas já respondidas.

O charter lista **"memória global automática"** como não-objetivo (`docs/product/charter.md`). Esse
não-objetivo existe por duas razões que continuam válidas: memória automática produz afirmação sem
proveniência, e memória global atravessa a fronteira de Workspace que o domínio mantém.

Este ADR estreita esse não-objetivo em vez de contorná-lo. O que fica proibido é memória **global** e
**automática**. O que passa a ser permitido é memória **por Workspace**, **promovida por humano** e
**com proveniência**.

Uma proposta de arquivo Markdown único com títulos `###` e leitura por intervalo de linhas foi
considerada e rejeitada. A razão é concreta: o consolidador reescreve o arquivo, e qualquer inserção
desloca todos os offsets abaixo dela. Uma leitura por `start|end` obtida antes da reescrita passa a
devolver o meio de outra memória, sem erro e sem sinal. Um contexto errado silencioso é a pior classe
de falha para um produto cujo valor é evidência. Reconstruir estabilidade de offset exigiria
versionamento, invalidação e lock entre consolidador e agente — trabalho que o substrato SQLite já
resolve, dado que o repositório já opera SQLite/WAL como canônico (ADR 0005) e FTS5 está disponível
no ambiente.

# Decisão

## Substrato

A memória é um conjunto de `MemoryEntry` persistidos em SQLite, com índice de texto FTS5 sobre os
campos de descoberta. Não é arquivo, e a unidade de leitura é a entrada inteira, identificada por id.
Intervalo de linha não existe em nenhum contrato de memória.

Cada entrada é escopada a um Workspace. Não existe memória global, nem memória compartilhada entre
Workspaces.

## MemoryEntry

Campos normativos:

| Campo | Papel |
| --- | --- |
| `id` | identidade estável |
| `workspace_id` | escopo; obrigatório |
| `kind` | `rule`, `preference`, `decision`, `observation` ou `episode` |
| `title` | asserção única, legível, que descreve o conteúdo |
| `cues` | perguntas que esta entrada responde, na forma como o usuário perguntaria |
| `anti_cues` | assuntos que esta entrada **não** cobre |
| `body` | o conteúdo: relato, regra, racional ou achado |
| `evidence_refs` | `run:`, `event:` ou `artifact:`; obrigatório para `observation` |
| `provenance` | origem: sessão de chat, Run, spec ou declaração humana |
| `status` | `candidate`, `active`, `superseded` ou `rejected` |
| `superseded_by` | id sucessor, quando `status=superseded` |
| `rejection_reason` | motivo, quando `status=rejected` |
| `relates_to` | relações declaradas na escrita com entradas do mesmo Workspace |
| `sample_size` | número de Runs que sustentam um `observation` |
| `created_at` | data de criação |
| `promoted_at` | data da promoção, quando `status=active` |

## Cues são perguntas, não palavras-chave

`cues` contém as perguntas que a entrada responde, escritas como o usuário as faria. Isso é
normativo, não estilístico: casar pergunta com pergunta recupera melhor que casar pergunta com
resposta, e o autor da memória frequentemente não sabe qual termo o leitor futuro usará.

`anti_cues` existe para cortar falso positivo. Contexto irrelevante recuperado é mais danoso que
contexto ausente, porque o agente o trata como pertinente.

O autor de uma entrada — agente ou humano — deve escrever cues deliberadamente mais amplas que o
contexto específico que a originou.

## Descoberta em dois estágios

A busca ocorre sobre `title`, `cues` e `anti_cues`. **Nunca sobre `body`.**

1. `memory_search` devolve, por candidato: `id`, `title`, `cues`, `kind`, `status` e um snippet. Não
   devolve `body`.
2. `memory_read` devolve entradas inteiras, por id, com teto declarado de entradas por turno.

O julgamento de relevância pertence ao agente, no estágio 2. O sistema não infere relevância em
runtime.

Relação entre entradas é declarada na escrita (`relates_to`), nunca inferida na leitura. Inferência
de relação em runtime é caro, não determinístico e não auditável.

## Guardrail por ausência de capacidade

O limite de leitura não é uma lista de ações proibidas. É a ausência das capacidades
correspondentes: as únicas operações de memória expostas ao Lab Agent são `memory_search` e
`memory_read`, e não existe operação que devolva o conjunto completo nem que leia por posição.

Isso segue o mesmo princípio da admissão: capacidade representável não é anunciada como executável, e
o que não é anunciado não é executável. Enumerar proibições sempre deixa um caso de fora; não expor a
capacidade não deixa.

O teto de entradas por turno é budget aplicado antes de anunciar suporte, não recomendação.

## Verdade por kind

`rule` e `preference` são declarações do humano. Não exigem evidência e permanecem válidas até
supersessão.

`decision` exige racional e data.

`observation` **exige `evidence_refs`**. Uma entrada `observation` sem `run:`, `event:` ou
`artifact:` é rejeitada na escrita. Isso não é política nova: o repositório já determina que
resultados de Run não viram fatos sem essas referências. `sample_size` acompanha a entrada, porque um
achado sobre uma Run e um achado sobre trinta não têm a mesma força.

`episode` registra o que houve numa sessão. Decai rápido e nunca é apresentado como fato.

## Append-only e supersessão

Correção nunca edita conteúdo: cria uma entrada nova e marca a anterior como `superseded`, com
`superseded_by` apontando para a sucessora. É a mesma regra de `EvaluationRecord` e de revisions
(ADR 0009).

Consequência deliberada: o consolidador não destrói contexto, e a divergência histórica permanece
inspecionável.

## Promoção humana

O consolidador em background analisa conversas, Runs e specs e escreve entradas com
`status=candidate`. Uma entrada `candidate` **não é elegível para retrieval**.

A promoção para `active` é decisão humana. Rejeição preserva a entrada com motivo, sem apagá-la.

A promoção é decisão de curadoria de contexto, não decisão de autoridade sobre evidência: ela não
exige `HumanAttestationRecord` e não é aceitação de contract. Uma entrada de memória nunca aceita,
rejeita ou supersede uma revision, e nunca substitui um EvaluationRecord.

## Proveniência de uso

Toda leitura de memória é registrada por sessão, e todo draft que o Lab Agent propõe carrega quais
entradas o informaram.

Essa é a parte não óbvia e é obrigatória. Se as propostas do copiloto dependem de estado mutável
invisível, dois pedidos idênticos produzem Studies diferentes e o comportamento do laboratório deixa
de ser auditável. Pior: memória derivada de um Study com grader oculto pode contaminar o desenho de
outro Study **através do humano**, e nenhuma allowlist de `SubjectEnvelope` detecta esse caminho.
Proveniência declarada é o que torna essa contaminação visível.

## Fronteiras

- Memória é do Control Plane. Nenhuma entrada entra no `SubjectEnvelope`, por nenhum caminho. A
  allowlist fechada permanece a fronteira.
- Memória não é evidência. Ela não entra no event ledger, não é record canônico e não aparece em
  Evidence Bundle como fato de Run.
- Classificação é respeitada: `sensitive` e `restricted` não são materializados em `body`. Uma
  entrada referencia por `ArtifactRef`, que continua sem locator e continua não concedendo acesso.
- Credencial nunca entra em memória, em nenhum campo.
- Escopo é o Workspace. Sem exceção.

# Consequências

O não-objetivo do charter passa a ser lido como "memória global automática", e este ADR é a
autoridade sobre o que substitui: memória por Workspace, promovida por humano, com proveniência.

O usuário ganha uma superfície para ver e corrigir o que o agente aprendeu sobre ele. Isso é feature
de confiança, não overhead de processo.

O custo de contexto por consulta é o do estágio 1: alguns candidatos com título, cues e snippet, em
vez do conjunto completo. O corpo só é pago para o que o agente escolheu.

O efeito da memória sobre a qualidade dos drafts é mensurável pelo próprio produto, como um Study com
variants `sem memória`, `só cues` e `cues mais corpo` sobre o mesmo material. Enquanto essa medição
não existir, o ganho da memória é hipótese declarada, não resultado.
