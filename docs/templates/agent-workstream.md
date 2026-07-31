---
id: template-agent-workstream
type: template
title: Template de workstream para agente
status: accepted
authority: planning
volatility: snapshot
owner: core
created_at: 2026-07-23
updated_at: 2026-07-23
applies_to: implementation-planning
sources:
  - docs/planning/README.md
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
---

# Template de workstream

Copie este formato para `docs/planning/tasks/NN-task-name.md`. Substitua todos os placeholders e
remova secoes nao aplicaveis. O brief e temporal; mudanca normativa continua exigindo ADR.

## Identidade

```text
TASK_ID=WS-NN
WORKSTREAM_STATE=queued
RECOMMENDED_BRANCH=task/name
BASE_REF=origin/main
PRIMARY_PATHS=...
SHARED_PATHS=...
FORBIDDEN_PATHS=...
```

Materialize esta identidade como `changes/<issue>.toml` usando o
[template de contrato de mudança](change-contract.toml). `PRIMARY_PATHS` vira `scope.expected`,
`FORBIDDEN_PATHS` vira `scope.forbidden`, e descoberta legítima entra em `scope.expansions` com
rationale. Paths esperados orientam e geram warning; proibições explícitas continuam bloqueantes.

## Resultado pratico

Descreva em linguagem de produto o que um usuario ou outro componente consegue fazer no final.

## Estado inicial deterministico

- SHAs observados;
- worktrees/branches existentes;
- comportamento confirmado;
- contracts/ADRs relevantes;
- capacidades apenas representaveis;
- baseline de testes.

Todo fato temporal deve ser redescoberto no inicio da execucao.

## Escopo e nao objetivos

Liste entregas verticais e exclusoes. Uma capability so conta quando atravessa:

```text
contract -> persistence -> service -> runtime -> event -> API/CLI -> bundle -> tests
```

## Invariantes

Copie apenas invariantes aplicaveis do `AGENTS.md` e dos ADRs. Nao enfraqueca authority,
SubjectEnvelope, classification, lifecycle ou evidence para facilitar o codigo.

## Harness

```text
MAX_IMPLEMENTATION_LOOPS=10
MAX_IDENTICAL_FAILURES=3
FULL_GATE_INTERVAL=3
ALLOW_SCOPE_EXPANSION=0
ALLOW_SECRET_OUTPUT=0
```

Estado minimo por loop:

```json
{
  "phase": "discover|plan|implement|verify|attack|repair|integrate|handoff",
  "base_sha": "...",
  "head_sha": "...",
  "changed_paths": [],
  "tests_passed": [],
  "tests_failed": [],
  "open_p0_p1": [],
  "open_decisions": [],
  "next_action": "..."
}
```

Nao versionar estado com credenciais ou informacao sensivel.

## Loop

```text
DISCOVER
-> PLAN vertical slice
-> IMPLEMENT smallest complete slice
-> VERIFY focused
-> ATTACK invariants
-> REPAIR proven findings
-> REVIEW read-only
-> FULL GATES periodically
-> repeat or HANDOFF
```

## Condicionais padrao

- Baseline falha antes de edits: documente e isole; nao atribua a task.
- Mesmo erro por tres loops: reavalie a suposicao com subagente Judge.
- Mudanca normativa: pare, proponha ADR sucessor e solicite decisao humana.
- Dependencia ausente: mantenha capability rejected/unsupported; nao crie adapter fake em producao.
- Generated drift: corrija fonte e regenere.
- P0/P1 comprovado: adicione regressao antes do fix.
- Apenas sugestao cosmetica: nao expanda escopo.
- Budget da sessao perto do fim: deixe checkpoint/handoff; nao declare conclusao falsa.

## Subagentes

Defina de dois a tres papeis bounded e preferencialmente read-only:

- code reviewer;
- semantic/security Judge;
- docs/API/UX reviewer.

O agente principal integra findings e preserva ownership da worktree.

## Testes

Liste:

- unitarios;
- integracao;
- adversariais;
- migration/restart;
- live opcionais ou obrigatorios;
- full gates do `AGENTS.md`.

## Criterio de saida

Deve ser observavel e binario. Evite “codigo criado” ou “parece funcionar”.

## Handoff

- resumo do resultado;
- commits/PR/SHA;
- paths alterados;
- testes e evidencia;
- limitations;
- findings de subagentes;
- decisoes humanas abertas;
- follow-up recomendado.
