---
id: product-interaction-graph-authoring-concept
type: product
title: Autoria de grafo de execução com condicionais por evidência
status: draft
authority: incubation
volatility: snapshot
owner: product
created_at: 2026-07-25
updated_at: 2026-07-25
applies_to: product/interaction-protocol-authoring
sources:
  - user-conversation:2026-07-25-execution-graph-and-judge
  - docs/product/live-run-graph-concept.md
  - docs/product/semantic-execution-graph-concept.md
  - docs/contracts/study-run-v1.md
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
review_due: 2026-10-25
---

# Autoria de grafo de execução com condicionais por evidência

> Estado: ideia de autoria preservada para reuso. Este documento não descreve runtime existente, não
> define contrato aceito, não escolhe formato de arquivo e não autoriza implementação. Ele registra
> uma proposta de **superfície de autoria** sobre um contrato que já existe tipado.

## Origem

A proposta surgiu da observação de que agentes não são determinísticos, e por isso é difícil decidir
por código quando enviar o próximo prompt de uma sequência. A intenção declarada foi definir o
percurso completo de uma Run num arquivo — YAML ou formato de grafo — derivado de goal, scenario,
interaction e workspace, com condicionais baseadas no que o agente observavelmente fez.

Exemplo dado:

```text
Iniciar Run → Explorar → Aplicar fix
```

Com a condicional entre o primeiro e o segundo passo formulada como pergunta com evidência:

```text
Explorou o arquivo? (sim / não)
Evidência: chamou read
```

Se sim, segue para a correção. Se não, o agente recebe hints automaticamente — ou a Run muda
completamente de direção conforme as decisões do modelo avaliado.

## O que já existe: o grafo está tipado

Esta é a informação mais importante do documento. O vocabulário de grafo **já é contrato**, em
`src/evidrun/contracts/authoring/protocol.py:19-101`. O que falta é runtime e superfície de autoria,
não modelagem.

`InteractionProtocolSpec` (`protocol.py:74-96`) aceita
`mode: Literal["single_turn", "graph"]`, com `nodes` e `edges`. O validador exige nodes em modo
grafo, ids únicos, e que toda edge referencie node conhecido. Em `single_turn`, declarar nodes ou
edges é erro.

`InteractionNode` (`protocol.py:19-22`) tem cinco tipos: `prompt`, `await_subject`, `checkpoint`,
`human_approval`, `terminal`.

`InteractionEdge` (`protocol.py:66-71`) tem `source`, `target`, `trigger`, `priority` e
`max_activations` (`gt=0`).

Existem seis triggers, união discriminada por `kind` (`protocol.py:25-63`):

| Trigger | Campos | Cobre qual condicional |
| --- | --- | --- |
| `always` | — | transição incondicional |
| `event` | `event_type` | **"chamou read"** → `tool.completed` |
| `checkpoint_reached` | `checkpoint_definition_id` | marco validado atingido |
| `evaluator_signal` | `stage_id`, `signal` | avaliação intermediária sinalizou |
| `human_signal` | `signal` | humano interveio |
| `predicate` | `predicate_ref` | lógica versionada, referenciada |

O exemplo do usuário é expressável hoje no contrato, sem campo novo:

- "Iniciar Run → Explorar" — node `prompt` para node `await_subject`, edge com trigger `always`.
- "Explorou o arquivo? Evidência: chamou read" — edge com `EventTrigger(event_type="tool.completed")`
  saindo do node de espera.
- "Se não explorou, injeta hint" — segunda edge saindo do mesmo node, com `priority` menor, apontando
  para um node `prompt` cujo `content_ref` é o artifact do hint.
- "A Run muda de direção" — várias edges com triggers distintos, desempatadas por `priority`, com
  `max_activations` limitando laços.

A consequência prática: **o pedido não é uma extensão de contrato, é a construção do coordinator que
executa o contrato existente, mais uma superfície para escrevê-lo.**

## O que a admissão rejeita hoje

`src/evidrun/contracts/admission/envelope.py:65-66` fixa
`interaction_modes = frozenset({"single_turn"})`, e esse eixo não é ampliado pelo catálogo de
adapters em `src/evidrun/runs/adapters/catalog.py:79-108`.

`src/evidrun/contracts/admission/checks/interaction.py:25-43` rejeita em dois passos: modo fora do
envelope, e depois `max_turns != 1`, `system_prompt_ref` presente ou `initial_message_refs` não vazio.

Um grafo é rejeitado duas vezes: pelo modo e pela materialização de prompt. Isso está registrado em
`docs/contracts/agent-inventory-workspace-v1.md:52-58` e em
`docs/planning/mvp-capability-map.md:79` como `accepted_only`.

## Onde este documento se distingue dos dois já existentes

Já existem dois documentos de incubação sobre grafo, e a confusão entre eles é fácil.
`docs/product/semantic-execution-graph-concept.md:62-66` estabelece a separação de autoridade que este
documento respeita:

| Objeto | Origem | Função |
| --- | --- | --- |
| `InteractionProtocolGraph` | definição pré-Run | controlar interações, prompts, triggers e edges permitidas |
| `SemanticExecutionGraph` | eventos observados | interpretar a trajetória real |
| Canvas / `ContextDirectionMatrix` | projeção dos dois | inspeção humana |

`live-run-graph-concept.md` e `semantic-execution-graph-concept.md` tratam do **segundo e terceiro**:
como interpretar e visualizar a trajetória depois que ela aconteceu. Este documento trata do
**primeiro**: como um humano escreve o percurso antes da Run, e o que falta para executá-lo.

A distinção importa porque a projeção semântica pode ser prototipada sobre o ledger sem runtime de
grafo — está dito em `semantic-execution-graph-concept.md:88-90` — enquanto o grafo de interação
exige coordinator. São trilhas independentes.

## O que falta, em ordem de dependência

**1. Formato de autoria.** Hoje contratos são modelos Pydantic serializados em JSON canônico com
digest. Não existe authoring em YAML para grafo. O manifesto legado v1 é YAML
(`src/evidrun/experiments/models.py`), mas é adapter de compatibilidade, não superfície de autoria.
Um formato novo precisa preservar o digest semântico: a normalização em `contracts/base.py:38-65`
remove nulls e coleções vazias antes do hash, então dois YAML equivalentes precisam hashar igual.

**2. Coordinator de turnos.** Falta a máquina que percorre nodes, avalia triggers, resolve `priority`,
respeita `max_activations` e materializa cada prompt como evento. Isso é o que WS-50 pede
(`docs/planning/tasks/50-lab-agent-bounded-exploration.md`), incluindo budget multi-turn realmente
aplicado — a linha 108 daquele brief é explícita: se o budget não puder ser imposto, a admissão
continua rejeitando.

**3. Eventos de materialização de prompt.** Um node `prompt` que entrega conteúdo ao Subject precisa
de event type próprio, com digest do que foi entregue. Não existe no ledger. Os tipos reservados hoje
(`src/evidrun/contracts/runtime/events.py:268-281`) cobrem pause/resume, skills, tool approval,
checkpoint falho e progress — nenhum cobre injeção de prompt.

**4. `run.paused` e `run.resumed`.** Um node `human_approval` depende deles. Ambos têm payload
registrado e permanecem reservados como não executáveis (`events.py:268-290`).

**5. Semântica de predicado.** `PredicateTrigger` carrega apenas uma referência opaca. A lógica vive
fora do contrato, e isso é deliberado: `run-laboratory-concept.md:289-290` mantém como pergunta aberta
como registrar e executar predicados versionados sem admitir lógica arbitrária insegura. Um grafo com
condicionais compostas cai direto nessa pergunta.

## Riscos específicos desta superfície

**Hints injetados são uma variável não declarada.** Se o grafo injeta um hint quando o agente não
explorou, duas Runs do mesmo RunSpec podem receber conteúdo diferente. Sob
`prospective_controlled`, o diff material entre baseline e candidate deve ser exatamente a
`primary_variable` (`docs/contracts/study-run-v1.md:74-76`). Um grafo com ramificação condicional
introduz variação que não está na variável primária.

Isso não invalida a ideia — significa que ela pertence naturalmente a `exploratory` com confounders
declarados, ou exige que o conjunto de caminhos possíveis seja tratado como parte da configuração
congelada, não como variação. A segunda leitura é mais interessante e precisa de decisão: **o grafo é
parte da variável ou parte do ambiente?**

**Um caminho não percorrido é informação.** Se a Run desviou porque o agente não explorou, o relatório
precisa dizer isso. Um grafo que silenciosamente corrige o agente e depois reporta sucesso mede a
capacidade do grafo, não do agente. A trajetória percorrida tem que ser evidência de primeira classe,
não detalhe de implementação.

**Hints podem virar gabarito.** Um hint suficientemente específico entrega a resposta. A allowlist do
SubjectEnvelope (ADR 0012:38-46) existe para impedir vazamento de `StudyIntent`, hipótese e expected
answer. Conteúdo de node `prompt` precisa passar pela mesma disciplina de allowlist e digest que os
inputs, não por um canal paralelo.

**Laços.** `max_activations` limita por edge, não globalmente. Um grafo com ciclos precisa de teto de
turnos aplicado pelo coordinator, não confiado à topologia.

## Avaliação

A ideia é sólida e o repositório já concordou com ela — o contrato foi desenhado para isso. O trabalho
é de runtime, e a dependência crítica é o coordinator de turnos, que também bloqueia bounded
exploration, checkpoints e a maior parte da IDEIA de judge interferente
(`docs/product/judging-agent-concept.md`).

A pergunta de design que ainda não tem resposta não é técnica: é se o grafo conta como parte da
configuração sob teste ou como parte do instrumento de medida. Enquanto isso não estiver decidido, um
grafo ramificado produz Runs comparáveis apenas dentro do mesmo caminho percorrido.

## Gate de promoção

Antes de sair de incubação:

- decisão sobre grafo como variável versus instrumento, com consequência declarada para `evidence_mode`;
- event types para materialização de prompt e para desvio de caminho, com payload e digest;
- coordinator de turnos com budget aplicado, admitido explicitamente pelo envelope;
- disciplina de allowlist para conteúdo de node `prompt`;
- decisão sobre predicados versionados;
- trajetória percorrida como record exportável no bundle;
- ADR sucessor, porque a decisão altera o que a admissão aceita.

Ver também: [Canvas vivo e grafo de execução](live-run-graph-concept.md),
[Matriz de contexto e grafo semântico da execução](semantic-execution-graph-concept.md) e
[Agente julgador e intervenção na sessão](judging-agent-concept.md).
