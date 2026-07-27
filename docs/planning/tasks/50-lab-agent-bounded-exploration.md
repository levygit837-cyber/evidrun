---
id: planning-task-lab-agent-bounded-exploration
type: implementation-task
title: WS-50 Lab Agent e bounded exploration
status: proposed
authority: planning
owner: laboratory
created_at: 2026-07-23
updated_at: 2026-07-23
observed_at: 2026-07-23
review_due: 2026-08-20
applies_to: lab-agent-runtime
sources:
  - docs/product/run-laboratory-concept.md
  - docs/research/run-scenario-discovery/scenario-c-qualitative-incident.md
  - docs/adr/0013-bounded-exploration-terminal-semantics.md
  - docs/architecture/agents-and-authority.md
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
---

# WS-50 — Lab Agent e bounded exploration

`workstream_state: queued`

## Resultado pratico

Permitir que o usuario converse com um Lab Agent para criar drafts e iniciar uma investigacao
limitada, sem entregar ao Subject o chat do laboratorio, hidden graders ou autoridade humana. A Run
termina por disposition e stop reason do ADR 0013 e produz evidence/progress navegavel.

## Dependencias

```text
WS-00 done_on_main
WS-30 done_on_main
WS-40 done_on_main
```

## Lab Agent

Pode:

- ler contracts e evidence autorizados;
- explicar Runs e limitations;
- propor Study/Goal/Scenario/EvaluationPlan drafts;
- criar ReviewPackage request;
- sugerir variants e follow-ups;
- iniciar sandbox somente pelo mesmo command path humano, sem autoridade adicional.

Nao pode:

- aceitar/rejeitar/superseder revision;
- criar human review/adjudication;
- ver hidden data fora de seu envelope;
- enviar chat ao Subject;
- editar event ledger;
- conceder grant ou efeito externo;
- transformar Progress Artifact em fato.

## Bounded exploration

Implementar:

- coordinator de turnos explicitamente admitido;
- budgets de wall time, turns e output realmente aplicados antes de anunciar suporte;
- stop conditions `evidence_saturation`, `bounded_completion`, budget, time, turn, human stop,
  guardrail e provider failure somente quando seus coordinators existirem;
- terminal `{disposition, stop_reason, stop_condition_kind}`;
- learning summary como artifact citado;
- evaluation vetorial opcional, sem score global obrigatorio;
- checkpoints/progress durante Runs longas.

`concluded` nao significa `achieved`, `passed` ou boa qualidade.

## Harness

```text
TASK_ID=WS-50
MAX_REPAIR_LOOPS=14
FULL_GATE_INTERVAL=3
ALLOW_LAB_AGENT_AUTHORITY=0
ALLOW_CHAT_IN_SUBJECT_ENVELOPE=0
ALLOW_EXPLORATION_PASS_FAIL=0
LIVE_MODEL_RUNS=2
```

Loop:

```text
DEFINE one qualitative dossier
-> BUILD Lab Agent draft path
-> COMPILE sandbox Study
-> ADMIT bounded runtime
-> EXECUTE deterministic/fake transport
-> EXECUTE live model when safe
-> INSPECT ledger/checkpoints/progress/evals
-> JUDGE theory vs behavior
-> REPAIR
-> FULL GATES
```

### Condicionais

- Se multi-turn budget nao puder ser imposto, Admission continua rejected.
- Se chat/hypothesis/hidden calibration chegar ao Subject, P0.
- Se stop reason nao corresponder a uma condition declarada, rejeite terminal.
- Se provider failure for apresentado como exploration concluded, corrija lifecycle.
- Se evidence saturation depender apenas da opiniao do proprio Subject, mantenha provisional ou use
  validator separado; nao declare fato.
- Se Lab Agent tentar acao humana, produza approval request, nunca decision.
- Se modelo live variar, preserve a Run negativa; nao ajuste grader para faze-la passar.

## Subagentes

- Lab authority reviewer read-only;
- bounded semantics Judge read-only;
- live Run critic read-only, que recebe bundle/eventos e tenta encontrar leakage ou claims sem
  evidence.

## Testes obrigatorios

- chat do laboratorio ausente do SubjectEnvelope;
- drafts criados sem decision;
- approval request sem attestation;
- turn/time/output budgets e human stop;
- evidence saturation valida/invalida;
- provider failure e guardrail;
- Progress Artifacts em varios marcos;
- model judge blind e human review pending;
- no pass/fail/achievement em bounded result;
- restart e retry sem perder disposition;
- bundle verificando learning summary/evidence refs;
- duas Runs live com fixtures ineditas, incluindo pelo menos uma falha util.

## Criterio de saida

O usuario descreve uma investigacao, recebe drafts do Lab Agent, executa em sandbox, acompanha
progresso e recebe uma conclusao limitada por evidencia. O sistema mostra claramente lifecycle,
disposition, stop reason e qualidade como eixos separados.

