---
id: planning-task-lab-agent-bounded-exploration
type: implementation-task
title: WS-50 Bounded exploration e multi-turn do Subject
status: proposed
authority: planning
volatility: snapshot
owner: laboratory
created_at: 2026-07-23
updated_at: 2026-07-31
observed_at: 2026-07-31
review_due: 2026-08-23
applies_to: bounded-exploration-runtime
sources:
  - docs/adr/0018-lab-agent-copilot-scope.md
  - docs/adr/0020-workspace-project-run-environment-boundaries.md
  - docs/adr/0021-hierarchical-lab-agent-scope.md
  - docs/contracts/lab-agent-scope-v1.md
  - docs/product/run-laboratory-concept.md
  - docs/research/run-scenario-discovery/scenario-c-qualitative-incident.md
  - docs/adr/0013-bounded-exploration-terminal-semantics.md
  - docs/architecture/agents-and-authority.md
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
---

# WS-50 — Bounded exploration e multi-turn do Subject

`workstream_state: blocked`

## Reescopo

Este brief cobria duas coisas: o copiloto do laboratorio e o runtime de bounded exploration. O
[ADR 0018](../../adr/0018-lab-agent-copilot-scope.md) as separou.

O copiloto saiu para [WS-04](04-lab-agent-runtime.md), porque conversar, ler evidencia autorizada e
propor drafts nao depende de artifact grants, evaluation generica nem trust modes. O que sobra aqui e
o que genuinamente depende deles: multi-turn admitido, coordinator de turnos e semantica terminal em
dois eixos.

## Resultado pratico

Uma Run admite mais de um turno do Subject com budget realmente aplicado, e termina por disposition e
stop reason do ADR 0013 em vez de pass/fail.

Isso e o que destrava o cenario canonico do produto com tools e autonomia real: hoje a admissao
rejeita `max_turns > 1` honestamente, porque o coordinator nao existe.

## Dependencias

```text
WS-30 evaluation executavel
WS-40 trust modes
```

O Runtime Kernel de que esta task depende ja esta integrado em `main`.

## Fronteira do Lab Agent nesta task

O Lab Agent participa a partir de uma Project/Focused chat, iniciando a execucao nao verificada pelo
mesmo command path humano, sem autoridade adicional. A
fronteira completa esta no ADR 0018 e nao e redefinida aqui: ele nao aceita revision, nao cria review
ou adjudicacao, nao envia chat ao Subject, nao escreve no ledger, nao concede grant e nao transforma
Progress Artifact em fato.

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
DEFINE one qualitative dossier no Project da sessao
-> BUILD Lab Agent draft path
-> COMPILE pacote nao verificado
-> ADMIT bounded runtime
-> MATERIALIZE Run Environment admitido, nunca o Workspace do Control Plane
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

Uma Run admite mais de um turno com budget de turno, tempo e output aplicados de verdade, e termina
com `{disposition, stop_reason, stop_condition_kind}` correspondendo a uma condition declarada. O
sistema mostra lifecycle, disposition, stop reason e qualidade como eixos separados, e nenhum deles
como pass/fail.

A autoria assistida que precede essa Run pertence a [WS-04](04-lab-agent-runtime.md).
