---
id: planning-task-evaluation-checkpoint-progress
type: implementation-task
title: WS-30 Evaluation engine, checkpoints e Progress Artifacts
status: proposed
authority: planning
owner: evidence
created_at: 2026-07-23
updated_at: 2026-07-23
observed_at: 2026-07-23
review_due: 2026-08-13
applies_to: evaluation-runtime
sources:
  - docs/contracts/evaluation-checkpoint-v1.md
  - docs/adr/0011-progress-artifacts-and-bundle-boundaries.md
  - docs/benchmarks/graders-and-judges.md
  - docs/planning/tasks/20-artifact-access-and-capture.md
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
---

# WS-30 — Evaluation, checkpoints e progress

`workstream_state: queued`

## Contexto abstrato

O Kernel produz uma resposta; o Evidence Plane precisa transformar essa resposta em avaliacao,
marcos e resumos sem criar uma segunda verdade. EvaluationRecord, CheckpointRecord e Progress
Artifact compartilham a mesma boundary do ledger e devem ser orquestrados pelo mesmo conjunto de
regras de idempotencia, grants e terminal coverage.

## Resultado obrigatorio

### Evaluation engine

- coordinator generico para stages ordenados;
- registry de graders deterministas;
- triggers `event`, `run_terminal` e `checkpoint` realmente executados;
- multiplas dimensoes e hard gates;
- failure/retry por stage sem duplicar records;
- aggregation somente quando projector versionado existir;
- model judge opcional com `EvaluatorEnvelope` minimo, blinding e output estruturado;
- fila de `human_review`/adjudication required ligada a authority, sem fingir conclusao final.

### Checkpoint coordinator

- observacao de triggers suportados;
- validators versionados;
- captura autorizada;
- record atomico somente quando todos os validators passam;
- evento de falha sem checkpoint parcial;
- nenhuma alegacao de restore/replay.

### Progress observer

- trigger por checkpoint ou intervalo de `subject.responded`;
- leitura do prefixo exato do ledger;
- summarizer deterministico primeiro, model observer opcional depois;
- statements citados por evidence refs;
- artifact + record + evento em operacao reconciliavel;
- sempre `provisional`, sem score, Goal state ou feedback ao Subject.

## Dependencias

```text
WS-00 done_on_main
AND WS-20 done_on_main
```

Authority de `main` e usada para records humanos. Sem authority habilitada, evaluation humana fica
pending; o runtime nao fabrica record.

## Harness

```text
TASK_ID=WS-30
MAX_REPAIR_LOOPS=12
FULL_GATE_INTERVAL=3
DETERMINISTIC_FIRST=1
MODEL_JUDGE_LIVE_OPTIONAL=1
ALLOW_RESTORE_REPLAY=0
ALLOW_PROGRESS_FEEDBACK_TO_SUBJECT=0
```

Loop vertical por capability:

```text
SELECT one accepted trigger/stage
-> IMPLEMENT pure decision logic
-> PERSIST with boundary/idempotency
-> EMIT factual event
-> VERIFY bundle offline
-> ATTACK future refs/duplicates/order/crash
-> REPAIR
-> PROMOTE capability in Admission
-> next capability
```

Nao promova todos os contracts de uma vez. Cada trigger/stage sai de `unsupported` somente depois do
seu teste vertical.

### Condicionais

- Se stage required nao executar, Run pode terminar tecnicamente, mas evaluation projection fica
  pending; nao marque resultado avaliativo final.
- Se hard gate falhar, stages posteriores bloqueados nao produzem records vazios.
- Se model judge receber hidden field proibido, P0.
- Se progress summary citar evento futuro ou nao autorizado, rejeite output e grave falha do
  observer.
- Se checkpoint capture falhar, nao persista record parcial.
- Se crash ocorrer entre artifact e record, retry reconcilia por boundary/definition, sem duplicar.
- Se a implementacao exigir restore, abra task futura; nao expanda esta.

## Subagentes

- eval semantics Judge read-only para hard gates, precedence e blinding;
- checkpoint adversary read-only para triggers, cursor/hash e atomicidade;
- progress reviewer read-only para hallucinated claims, leakage e segunda fonte de verdade.

## Testes obrigatorios

- multi-stage deterministico com gate passed/failed/not_applicable;
- stage ausente, repetido, fora de ordem e trigger incorreto;
- model judge provisional, schema invalido, timeout e blind fields;
- human review pending, attestation valida/invalida e adjudication precedence;
- checkpoint trigger duplicado, validator falho e capture ausente;
- progress por checkpoint e a cada N respostas;
- event ref futura, artifact sem grant e statement sem evidence;
- crash/retry em todas as fronteiras de persistencia;
- terminal cobre exatamente os records requeridos;
- Bundle tampering de boundary, relation, checkpoint e progress;
- nenhum record de progress contem file inventory, score ou chain-of-thought.

## Criterio de saida

Uma Run executa um EvaluationPlan multi-stage, produz checkpoint automatico e gera Progress Artifact
citado. O bundle offline revalida todas as boundaries. Human review required pode ficar pending de
forma honesta e completar somente com attestation valida.

