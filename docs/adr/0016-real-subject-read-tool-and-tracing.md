---
id: adr-0016
type: adr
title: Subject real com tool de leitura, tracing cercado e avaliação fundamentada
status: accepted
authority: normative
owner: core
created_at: 2026-07-23
updated_at: 2026-07-23
applies_to: runtime-kernel@2
sources:
  - docs/adr/0014-durable-runtime-kernel.md
  - docs/adr/0008-cliproxyapi-deepseek-default.md
  - docs/contracts/run-event-payloads-v1.md
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun/runs/adapters/subject_responses.py
  - src/evidrun/runs/adapters/tool_read_text.py
  - src/evidrun/runs/coordinator/tool_trace.py
  - src/evidrun/infrastructure/providers/openai_responses.py
  - src/evidrun/infrastructure/database/repository.py
verification_refs:
  - tests/integration/test_live_agent_runtime.py
  - tests/live/test_real_agent_benchmark.py
---

# Contexto

O ADR 0014 estabeleceu fila, attempt, lease, fencing e execução genérica para o primeiro adapter
determinístico offline. Ele reservou eventos de tool porque ainda não existiam coordinator, boundary
de artifacts nem avaliação capaz de provar que uma resposta veio de conteúdo efetivamente lido.

O primeiro Subject com modelo real precisa ampliar esse subconjunto sem criar um pipeline paralelo,
sem entregar o hidden expected ao agente e sem transformar identidade de artifact em acesso amplo ao
filesystem.

# Decisão

O catálogo de produção passa a registrar um segundo adapter de Subject, identificado exatamente por
`evidrun.runner/responses-read-agent-v1`, e um evaluator determinístico identificado por
`evidrun.evaluator/exact-read-answer-v1`. O provider continua sendo o perfil default decidido no ADR
0008: `cliproxyapi-local`, modelo `deepseek-v4-flash` e `reasoning=max`.

Uma Run desse adapter só é admitida quando declara simultaneamente:

- Goal `goal_state`, protocolo `single_turn` e `max_turns=1`;
- workspace `in_process`, network `provider_only` e efeitos externos `denied`;
- exatamente um input Subject-visible `text/plain`, `public` ou `internal`;
- capability requerida `evidrun.tool/read-artifact-text-v1`, interface 1, exposição
  `schema_only`, permissão `read:subject_artifacts` e constraint `subject-envelope-only`;
- runtime requirement `provider_tool_loop`;
- `ContextPolicy`, `max_wall_seconds`, `max_tool_calls` entre 1 e 8 e stops terminais
  `goal_complete`/`budget_exhausted`;
- capture `raw_encrypted` com opt-in explícito;
- uma stage booleana `exact-read-answer-v1` disparada por `subject.responded`.

Rounds internos de provider e tool permanecem uma única interação do Subject. Eles não aumentam
`max_turns`; são limitados por `max_tool_calls`, pelo wall clock iniciado em `run.running` e pelo
lease ativo.

O adapter v1 aplica `transport_max_output_tokens=768` a cada request como limite fechado de
transporte, não como budget científico configurável. Por isso uma Run que declara
`budgets.max_output_tokens` continua rejeitada na admissão. O valor efetivamente aplicado é gravado
nos metadados permitidos de `subject.responded`, junto com usage e digest agregado do trace.

# Tool boundary

`read_text(input_id, start_line, max_lines)` aceita apenas um `input_id` presente no
`SubjectEnvelope`, line number positivo e no máximo 80 linhas por chamada. A tool não aceita path,
URL, glob, artifact ID arbitrário ou locator. O runtime resolve o conteúdo materializado pelo
ArtifactStore do projeto e devolve JSON com linhas numeradas.

O schema entregue ao provider é fechado e `strict=true`. O provider real observado rejeita
`tool_choice=required`, mas aceita o mesmo schema com `tool_choice=auto`; portanto o adapter usa
`auto` como detalhe de transporte e rejeita qualquer resposta terminal produzida sem ao menos uma
chamada autorizada. Essa validação local preserva a obrigação científica de leitura.

O provider também opera com Responses não persistidas. A continuação não depende de
`previous_response_id`: o adapter reenvia somente o transcript mínimo delimitado — objective,
inventário permitido, function call e function output — em cada round. Não entra novo conteúdo no
Subject além do que já estava no envelope e no resultado autorizado da tool.

# Tracing e persistência

Cada capability resolvida gera `capability.offered` antes de `run.running`. Cada chamada gera:

```text
tool.called(call_id, capability_ref, arguments_ref, input_digest)
  -> exatamente um de:
     tool.completed(call_id, capability_ref, result_ref)
     tool.denied(call_id, rationale)
     tool.failed(call_id, capability_ref, reason)
```

Arguments e results são artifacts canônicos. Os eventos exigem o lease ativo na mesma transação,
validam capability admitida e usam operation keys derivadas do `call_id`. Um worker antigo não pode
publicar resultado depois de perder fencing. Recuperação fecha uma chamada pendente com
`tool.failed` antes do terminal indeterminado; uma Run terminal não pode conter tool call aberta.

O fato `subject.invoked` registra runner, network, provider profile, modelo, reasoning e adapter, mas
nunca credencial. `subject.responded` registra usage permitida, quantidade de rounds/tool calls e um
digest agregado de requests/responses e IDs do provider. Raw response, Chain-of-Thought e IDs livres
não entram no ledger.

A resposta semântica completa do Subject é persistida como artifact `sensitive` cifrado por projeto
antes da avaliação. O evento carrega apenas ref, digest e refs de evidência. Se o processo cair depois
de `subject.responded`, outro attempt decripta esse artifact, reexecuta somente o evaluator e termina
a mesma Run sem reinvocar o modelo.

# Avaliação

O output final deve ser um único JSON com exatamente `answer` e `evidence`. Cada citation contém
exatamente `input_id` e `line`. O evaluator lê apenas `tool.completed.result_ref` persistido, exige
que a linha citada tenha sido devolvida e compara por igualdade o campo estruturado
`ROOT_CAUSE_CODE=<expected>`. Substring, campo extra, citation inventada, distractor negado ou texto
fora do JSON recebem `false`.

O `expected` permanece no EvaluatorEnvelope. Ele não aparece no SubjectEnvelope, nas instruções do
runner nem no artifact inventory entregue ao Subject.

# Consequências

- o Runtime Kernel executa tanto o adapter offline legado quanto o primeiro Subject real pelo mesmo
  coordinator, fila, worker e ledger;
- timeout ou estouro de tool calls termina `run.budget_exhausted` com Goal `not_assessable`;
- erro do provider termina `run.failed` com código sanitizado, sem corpo livre upstream;
- pedido fora do envelope gera `tool.denied`; se o Subject ainda responder, a avaliação pode concluir
  `not_achieved` sem confundir erro de resposta com indisponibilidade de infraestrutura;
- Bundle v3 inclui arguments, results e output refs no artifact manifest, mas continua
  `references_only`, não portátil e não replayable;
- uma única Run live prova integração do sistema, não capacidade geral ou superioridade do modelo.

# Alternativas rejeitadas

- entregar path ao modelo: romperia a allowlist do SubjectEnvelope;
- usar conhecimento geral/trivia como primeiro benchmark: não prova uso da tool e aumenta risco de
  memorização e contaminação;
- avaliar somente o texto final: permitiria alegar uma citation nunca observada;
- armazenar output cru no ledger: violaria capture e ampliaria disclosure;
- reinvocar o provider após invocation sem resposta: pode duplicar execução não transacional;
- aceitar verifier humano por endpoint ou environment: criaria um fallback de autoridade de
  produção; a composição de teste continua sendo a única exceção controlada.
