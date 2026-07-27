---
id: planning-task-batch-and-minimal-metrics
type: implementation-task
title: WS-06 Batch, resiliencia de provider e metricas minimas
status: proposed
authority: planning
volatility: snapshot
owner: core
created_at: 2026-07-26
updated_at: 2026-07-26
observed_at: 2026-07-26
review_due: 2026-08-23
applies_to: batch-and-metrics
sources:
  - docs/planning/comfortable-minimum.md
  - docs/adr/0014-durable-runtime-kernel.md
  - docs/adr/0005-canonical-evidence-storage.md
  - docs/operations/runtime-worker.md
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
---

# WS-06 — Batch, resiliencia de provider e metricas minimas

`workstream_state: queued`

## Resultado pratico

Um Study com varias variants e varias repeticoes executa como lote, sobrevive a falha parcial e
produz numeros comparaveis entre variants. Sem isso, repeticao nao tem valor e nenhuma metrica de
confiabilidade existe.

Depende de WS-02: enquanto o app instalado nao inicia o worker, o lote e enfileirado e nao processado.

## Ponto de partida real

Duas coisas ja existem e nao precisam ser construidas:

- `StudyCompiler.compile` (`src/evidrun/contracts/compiler.py`) ja produz `tuple[RunSpec, ...]`
  iterando `variants x repetitions`. A matriz e compilada hoje.
- `subject.responded` ja grava `input_tokens`, `output_tokens` e `tool_calls` em `metadata`
  (`src/evidrun/runs/adapters/subject_responses.py`). Duracao e derivavel dos timestamps do ledger.

O que falta e execucao em lote, resiliencia de provider e a projecao agregada.

## Escopo

### Batch de execucao

- enfileirar todos os RunSpecs de um Study numa operacao idempotente;
- progresso agregado do lote: enfileiradas, executando, terminadas por causa;
- cancelamento do lote que nao corrompe Runs ja terminadas;
- concorrencia configuravel, porque o limite real e o provider e nao a maquina;
- falha parcial preserva o resto. Uma Run que falha por provider nao invalida o lote.

O lote e uma projecao sobre `run_execution_jobs`, nao uma entidade nova de evidencia. O ledger por Run
continua sendo a autoridade.

### Resiliencia de provider

Hoje `infrastructure/providers/openai_responses.py` nao tem retry, backoff nem rate limiting: erro de
transporte vira `ProviderRequestError` e propaga. Rodar um lote real contra API vai bater 429.

- retry com backoff exponencial e jitter para erros retryable, com teto declarado;
- respeito a rate limit anunciado pelo provider;
- distincao observavel entre falha de provider e falha do Subject. Falha de provider nao e resultado
  negativo do experimento.

### Metricas minimas

Por Run: tokens de entrada e saida, tool calls, duracao, terminal cause e o vetor do
`EvaluationRecord`.

Agregado sobre repeticoes, por variant: taxa de sucesso, `pass@k`, `pass^k`, e a diferenca entre
variants com indicacao de incerteza.

Custo entra como projecao derivada de tokens e tabela de preco por modelo. **Nao** como budget: hoje
`max_cost` e rejeitado na admissao (`contracts/admission/checks/unsupported.py`) e continua rejeitado
enquanto nao houver enforcement real. Projetar custo nao promove a capability.

## Invariantes que nao podem ser relaxadas

- **Read model derivado.** A agregacao e projecao reconstruivel a partir do ledger, nunca segunda
  fonte de verdade. Nenhuma metrica agregada e persistida como fato de evidencia.
- **Nao agregue por varredura do ledger.** `run_events` tem indice por `run_id` e payload como texto
  JSON. A projecao le de estrutura propria, alimentada na escrita ou materializada, nao de full scan
  com parse em Python.
- **Falha de provider nao e resultado.** Nao converta erro de transporte em terminal do experimento,
  e nao apresente Run falha como amostra da variant.
- **Repeticao nao e retry.** `repetition_index` faz parte do RunSpec; retry pertence ao attempt. Nao
  misture as duas contagens ao calcular `pass@k`.
- **Timeout continua terminal proprio.** `max_wall_seconds` termina por `run.budget_exhausted`, nunca
  `completed`.
- **Sem custo aplicado.** `max_cost` permanece rejeitado na admissao.

## Testes obrigatorios

- lote enfileirado e idempotente sob repeticao da mesma operacao;
- falha parcial: uma Run falha por provider, as demais completam, o lote reporta ambas as classes;
- cancelamento do lote nao altera Run terminada;
- retry de provider com backoff, e teto respeitado sem loop infinito;
- 429 tratado como retryable e esgotamento reportado como falha de provider, nao do Subject;
- `pass@k` e `pass^k` corretos para casos conhecidos, incluindo k=1 onde sao iguais;
- retry de attempt nao conta como repeticao no calculo;
- projecao de custo com tabela ausente reporta indisponivel em vez de zero;
- `max_cost` continua rejeitando a admissao.

## Criterio de saida

Um Study com duas variants e cinco repeticoes cada roda como lote no app instalado, um erro de
provider e visivel como erro de provider, e a leitura final mostra taxa de sucesso, `pass@k` e
`pass^k` por variant com o caminho para o transcript de qualquer Run individual.
