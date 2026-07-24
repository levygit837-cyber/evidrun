# Run esperada — fronteiras mínimas de evidência

> Projeção humana determinística de uma fixture de teste. Não é contrato, evento canônico nem
> resultado de produção.

## Identidade canônica

- RunRecord: presente e ligado aos digests exatos de RunSpec e AdmissionRecord.
- Scenario: `runtime-search-index-scenario@1`.
- Variant: `default`; repetição: `1`.
- AdmissionRecord: `admitted` antes da criação da Run.

## Visão entregue ao Subject

- Goal: Identifique a causa-raiz usando somente o registro autorizado.
- Input: `search-incident-log` (`text/plain`,
  `internal`), somente por ArtifactRef.
- Rede: `disabled`; efeitos externos:
  `denied`.

## Evidência canônica da execução

- Ledger: `run.queued → run.preparing → context.composed → run.running → subject.invoked → subject.responded → run.evaluating → evaluation.completed → run.completed`.
- Terminal: `run.completed`; Goal: `achieved`.
- EvaluationRecord: `exact-search-cause-v1` / `deterministic_grader` /
  `passed`.
- Âncoras de evidência: `event:subject.responded`.

## Omitido por desenho

- Provider, tools, skills, checkpoints, findings, fork, judge e revisão humana.
- Study intent, hipótese, oracle oculto, conteúdo bruto do Artifact e output de outra Run.

## Limite da afirmação

Esta fixture verifica separação e rastreabilidade das evidências no caminho offline atual. Ela não
mede capacidade de LLM, não demonstra estabilidade estatística e não promove os candidatos do
discovery a schema ou API.
