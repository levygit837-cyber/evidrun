---
id: adr-0012
type: adr
title: Disclosure mínimo do Subject e semântica terminal por Goal
status: superseded
authority: normative
owner: core
created_at: 2026-07-23
updated_at: 2026-07-23
applies_to: contracts/subject-terminal@1
sources:
  - docs/adr/0009-study-run-contract-composition.md
  - docs/contracts/study-run-v1.md
  - docs/contracts/evaluation-checkpoint-v1.md
supersedes: []
superseded_by: docs/adr/0013-bounded-exploration-terminal-semantics.md
implementation_refs:
  - src/evidrun/contracts/authoring.py
  - src/evidrun/contracts/runtime.py
  - src/evidrun/contracts/compiler.py
  - src/evidrun/infrastructure/database/repository.py
verification_refs:
  - tests/unit/test_contracts.py
  - tests/acceptance/test_demo_flow.py
---

# Contexto

O ADR 0009 separa `StudyIntent`, `Goal`, avaliação e visão do Subject. Essa fronteira precisa ser
allowlist, não uma tentativa de remover campos proibidos depois de serializar o RunSpec. Também é
necessário impedir que uma exploração limitada seja forçada a declarar pass/fail por reutilizar a
semântica terminal de um Goal de estado.

# Decisão

## Subject disclosure

O `SubjectEnvelope` é compilado a partir de uma allowlist fechada. Pode conter somente:

- Goal e constraints destinadas ao Subject;
- inputs visíveis e materializados por grants admitidos;
- interação/prompt explicitamente visível;
- capabilities resolvidas e exposição efetivamente autorizada;
- workspace lógico, budgets e stop conditions necessários à execução;
- disclosure público de avaliação compilado separadamente, quando declarado.

O disclosure público de avaliação inclui apenas IDs, descrições, escalas e anchors marcados como
públicos. Ele nunca inclui hidden inputs, calibration, expected answer, evaluator/model identity,
stage parameters privados, rationale futura, resultados de outra variant, StudyIntent ou hipótese.
`visible_to_subject=true` isolado não materializa conteúdo; o compiler precisa produzir o objeto
público exato e seu digest. Toda entrega posterior gera evento e não altera retroativamente o
envelope inicial.

Campos novos do RunSpec não entram automaticamente no SubjectEnvelope. `ArtifactRef` sem grant não
é input. Chats, locators, credenciais, secret bindings, Progress Artifacts e outputs de evaluators
permanecem ausentes salvo contrato explícito de intervenção.

## Término

Lifecycle terminal, conclusão do Goal e qualidade são eixos separados:

- lifecycle: `completed`, `failed`, `cancelled`, `budget_exhausted` ou `guardrail_stopped`;
- `goal_state`: `achieved`, `partially_achieved`, `not_achieved` ou `not_assessable`;
- qualidade: vetor de `EvaluationRecord`s, sem score implícito.

Para `Goal.mode=goal_state`, o evento terminal inclui `goal_state`. Para
`Goal.mode=bounded_exploration`, ele não usa achievement ou pass/fail; registra uma disposition de
exploração — `evidence_sufficient`, `evidence_exhausted`, `limit_reached`, `human_stopped` ou
`guardrail_stopped` —, a stop condition correspondente, evidence refs e limitações. A disposition
não é score e não afirma que a investigação foi boa.

Uma exploração nunca ganha linguagem causal ou aprovação por apenas atingir budget, produzir muitos
artifacts ou declarar que terminou.

# Compatibilidade e estado de implementação

Esta branch compila um `SubjectEnvelope` fechado, filtra inputs por visibilidade e omite Intent, plan
completo, hidden calibration e expected answers. `ArtifactRef` não possui `locator` estruturalmente
em nenhum contrato. `EvaluationDisclosure.subject.mode=none` não materializa guidance.

O compiler puro continua capaz de produzir `SubjectEvaluationGuidance` para `pre_run`, contendo
somente dimensões declaradas e, conforme flags, escala e anchors; stages, evaluator identity,
parameters e hidden inputs continuam ausentes. Isso não torna o modo executável. O runner ativo
recebe apenas objective e context, portanto a admissão rejeita todo disclosure diferente de `none`,
incluindo `pre_run`, como `runtime:subject_evaluation_guidance_delivery`.

`RunTerminalPayload` agora é uma união discriminada por `goal_mode`. O branch `goal_state` preserva
achievement; o branch `bounded_exploration` não aceita `state` nem pass/fail. O runner determinístico
atual, porém, só emite `goal_state`, e a admissão rejeita exploração limitada como
`runtime:bounded_exploration_terminal`. Assim a união é validável, mas bounded exploration ainda não
é uma capacidade executável.

O [ADR 0013](0013-bounded-exploration-terminal-semantics.md) sucede somente a taxonomia bounded
descrita na seção de término: `disposition` passa a registrar o estado operacional da exploração e
`stop_reason` registra separadamente a causa factual da parada. As decisões deste ADR sobre
allowlist, disclosure, separação entre lifecycle/Goal/qualidade e proibição de pass/fail para
exploração permanecem vigentes.

## Questões críticas em aberto

- Qual interface do runner consumirá guidance `pre_run` e quais eventos/regras materializarão
  disclosure posterior sem vazar dados ocultos nem alterar retroativamente o envelope inicial?

# Alternativas rejeitadas

- Serializar RunSpec e remover uma denylist: campos futuros poderiam vazar silenciosamente.
- Expor toda rubric porque uma dimensão é pública: vaza calibration, parâmetros ou expected answer.
- Usar `not_assessable` como resultado universal de exploração: ainda mistura eixos semanticamente
  diferentes.
- Tratar `completed` como `achieved` ou qualidade aprovada: confunde lifecycle, Goal e evaluation.

# Consequências

- O schema terminal é uma união discriminada pelo Goal mode; o branch bounded segue o ADR 0013 e
  permanece rejeitado pelo runtime ativo.
- O compiler de disclosure público possui testes negativos contra os campos ocultos centrais;
  novos campos devem manter essa cobertura.
- Runtimes rejeitam modos cujo envelope ou terminal semantics não consigam cumprir.
- Relatórios mostram lifecycle, Goal/disposition e qualidade em seções separadas.
