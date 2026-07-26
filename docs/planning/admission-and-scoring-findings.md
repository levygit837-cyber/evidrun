---
id: planning-admission-and-scoring-findings
type: planning
title: Achados sobre admissão, scoring e fronteira de evidência
status: draft
authority: planning
volatility: snapshot
owner: product-engineering
created_at: 2026-07-25
updated_at: 2026-07-25
observed_at: 2026-07-25
review_due: 2026-08-08
applies_to: admission-and-scoring
sources:
  - docs/planning/mvp-capability-map.md
  - docs/planning/mvp-implementation-roadmap.md
  - docs/benchmarks/protocol.md
  - docs/benchmarks/graders-and-judges.md
  - docs/contracts/evaluation-checkpoint-v1.md
  - docs/contracts/study-run-v1.md
  - docs/adr/0009-study-run-contract-composition.md
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
---

# Achados sobre admissão, scoring e fronteira de evidência

Levantamento observado em `main` no commit `812b330`. Cada achado foi confirmado no código, não
inferido de documentação. Este documento registra intenção de correção; ele não descreve
comportamento implementado nem autoriza mudança de contrato.

Os bloqueios de superfície já registrados em `docs/planning/mvp-implementation-roadmap.md` (B1
workspace/project, B2 worker no desktop, B3 autoria default) não são repetidos aqui. O recorte deste
documento é outro: pontos onde o rigor do núcleo não alcança a borda, e a consequência cai sobre a
conclusão de um experimento ou sobre a confiança na evidência exportada.

## A1 — Projeção `GradeRow` funciona como agregação não declarada

`docs/adr/0009-study-run-contract-composition.md:49` estabelece que score agregado só existe com
projector declarado pelo plano. `docs/benchmarks/protocol.md:38-39` proíbe esconder trade-offs em um
score único. `src/evidrun/runs/admission/catalog_checks.py:108-114` rejeita a admissão de qualquer
plano que declare `aggregation`.

Mesmo assim, `src/evidrun/runs/service.py:190-198` produz:

```
- Baseline: `{baseline_score:.2f}`
- Candidate: `{candidate_score:.2f}`
- Delta: `{candidate_score - baseline_score:+.2f}`
```

Os valores vêm de `GradeRow.score`, que é `1.0 if passed else 0.0`
(`src/evidrun/evaluations/deterministic.py:18`, `src/evidrun/runs/adapters.py:692`). O
`EvaluationRecord` canônico guarda booleano (`adapters.py:513-520`); a projeção guarda float; a
projeção é a que alimenta o relatório e sofre subtração aritmética.

Com um grader e duas variants o número é aritmeticamente inofensivo — o delta só assume -1.00, 0.00 ou
+1.00. O problema é semântico: um campo chamado `Delta` com duas casas decimais convida a interpretar
magnitude onde só existe acerto ou erro, e institui por projeção o score global que a doutrina nega.

Direção de correção a decidir: ou `GradeRow` deixa de expor float e o relatório passa a expressar
estado de portão, ou o relatório declara explicitamente que o valor é booleano projetado. A segunda
opção é mais barata e menos honesta.

## A2 — Motivo de rejeição não alcança o operador

`src/evidrun/runs/service.py:137-138` monta a mensagem apenas com `missing_requirements` ou
`denied_policies`. `src/evidrun/entrypoints/api/app.py:327` e
`src/evidrun/entrypoints/cli/app.py:293` fazem o mesmo recorte.

Duas classes de rejeição não populam nenhuma das duas tuplas:

1. A camada de adaptadores. `src/evidrun/runs/admission/catalog_checks.py:37-51` só constrói
   `AdmissionIssue`, nunca requisito faltante ou política negada.
2. Capacidade obrigatória não resolvida. Os quatro ramos de
   `src/evidrun/contracts/admission/checks/inventory.py:100-167` só registram a entrada não-resolvida
   no inventário; o bloqueio vem de `src/evidrun/contracts/admission/service.py:115`.

Nessas rejeições a mensagem sai como `deterministic RunSpec was rejected: ` sem causa. O
`AdmissionRecord` persistido contém a evidência completa; ela apenas não chega a quem precisa corrigir
a revisão.

Direção de correção: incluir `issues` na composição da mensagem e nas respostas de API e CLI, mantendo
a ordem estável do fold.

## A3 — Máquina de estados triplicada, sem guarda de divergência

A tabela de transições existe em `src/evidrun/infrastructure/database/ledger/transitions.py:39-62`, é
reimplementada literalmente em `src/evidrun/evidence/bundle.py:380-403`, e o conjunto de terminais
aparece uma quarta vez em `src/evidrun/runs/coordinator.py:34-40`. `bundle.py` não importa
`transitions.py`. Não localizamos teste de divergência entre as cópias.

Consequência: alterar uma transição sem tocar nas outras produz um bundle que o exportador considera
válido e o verificador rejeita, ou o inverso. O segundo caso é o mais grave, porque um bundle inválido
verificado como válido é exatamente o que a verificação existe para impedir.

O padrão de proteção já existe no repositório para um caso análogo: o par
`RevisionDecisionSubject`/`RevisionDecisionRecord` tem comentário explícito de teste de drift
(`src/evidrun/authority/subject.py:36-39`).

Direção de correção: teste de drift entre as três cópias, ou importação da tabela canônica pelo
verificador. A duplicação pode ser intencional — um verificador que importa a implementação que ele
verifica perde independência —, e nesse caso o teste de drift é a resposta correta, não a
deduplicação.

## A4 — Teste de aceitação exercita o nível mais fraco de `verify`

`tests/acceptance/test_demo_flow.py:49-51` chama `export_comparison` (bundle v1) e afirma
`verification["valid"] is True`.

O v1 não escreve `bundle.json`. Sem manifesto, `record_results` fica `{}`
(`src/evidrun/evidence/bundle.py:534-546`) e `all({}.values())` é `True`. O campo `valid` sai
verdadeiro com base apenas em checksums e cadeia de eventos, sem nenhuma checagem de records. O campo
`audit_complete` sinaliza a diferença, e o teste não o verifica.

`docs/architecture/system.md` cita esse teste como verificação da arquitetura.

Direção de correção: o teste passa a asseverar `audit_complete` além de `valid`, ou passa a exercitar
`export_run` (v3).

## A5 — Referências `artifact:` não são autorizadas na avaliação

`_validate_evidence_refs` (`src/evidrun/infrastructure/database/evaluation/records.py:292-310`) trata
os schemes `run` e `event`. Não há ramo para `artifact:` — nenhuma consulta ao `ArtifactStore`, nenhuma
checagem de classificação ou audiência.

`docs/contracts/evaluation-checkpoint-v1.md:53-56` admite o limite. O registro aqui é para marcar que
ele é de scoring, não apenas de evidência: um `EvaluationRecord` pode citar
`artifact:<qualquer-coisa>` como justificativa de uma dimensão e ser aceito.

Depende de WS-20 (artifact access e capture) para ter onde ancorar a autorização.

## A6 — `verify` não prova procedência, e isso não está declarado

Não existe assinatura criptográfica em `src/evidrun/evidence/`. Quem detém o bundle pode reescrever
eventos e recalcular toda a cadeia de forma coerente. `verify` prova consistência interna e detecta
corrupção ou edição ingênua.

O manifesto já declara honestamente `portable: false` e `replayable: false`
(`src/evidrun/evidence/bundle.py:258-266`). A ausência de prova de origem não tem declaração
equivalente.

Direção de correção: um campo explícito no manifesto, na linha das razões de omissão já usadas em
`ArtifactManifestEntry`. Assinatura real é decisão de ADR, não deste documento.

## A7 — Rejeição por provider indisponível não é persistível

`src/evidrun/contracts/admission/checks/inventory.py:64-75` devolve `ResolvedProvider()` vazio quando
o perfil não resolve, porque `ResolvedAgentInventory` proíbe `provider_profile_id` sem digest, modelo,
reasoning e adapter (`src/evidrun/contracts/runtime.py:201-212`).

`src/evidrun/infrastructure/database/catalog.py:98` exige
`inventory.provider_profile_id == run_spec.agent_inventory.provider_profile_id`.

Reproduzido: um RunSpec que declara um perfil ausente do catálogo gera `AdmissionRecord` válido com
`decision="rejected"`, e `save_admission_record` levanta
`ValueError: admission inventory does not match the RunSpec requirements`. Como
`src/evidrun/entrypoints/api/app.py:321-322` captura `Exception` e devolve 422, esse caso retorna erro
genérico em vez do record rejeitado que a API devolve em todas as outras rejeições.

`docs/architecture/codebase-layout.md:255-260` registra a correção que criou o esvaziamento, sem
mencionar o efeito na persistência.

Direção de correção a decidir: a igualdade em `catalog.py:98` passa a tolerar `None` quando a decisão
é `rejected`, ou `ResolvedProvider` ganha forma que expresse "declarado e não resolvido" sem violar o
invariante de resolução.

## A8 — `benchmarks/scenarios/crl-ctx-002/scenario.yaml` não tem leitor

O arquivo declara `revision: 1` e `expected: DB_POOL_EXHAUSTED`. Nenhum código o carrega — do
diretório, apenas `fixtures/long.log` é referenciado (`src/evidrun/runs/service.py:37`, e testes). Não
existe schema Pydantic para ele, em contraste com `ExperimentManifest`
(`src/evidrun/experiments/models.py:42`).

O `expected` efetivo vem de `benchmarks/experiments/crl-ctx-002-demo.yaml:44`, lido em
`src/evidrun/contracts/legacy.py:208`. Os dois arquivos declaram o mesmo valor e nada detecta
divergência: editar o do scenario não muda o comportamento e não gera erro.

Isso também torna inverificável a regra de `docs/benchmarks/scenario-authoring.md:26` ("mudança
material em fixture ou grader cria nova revision"): o `revision` do scenario não é lido, e
`legacy.py:210-213` fixa `revision=1` no `EvaluationPlanRevision` gerado. Reimportar um YAML editado
produz outra revisão 1 com payload diferente.

O digest do `RunSpec` protege uma Run já admitida. Nada protege a identidade estável do critério entre
Runs.

Direção de correção: ou `scenario.yaml` ganha leitor e schema, ou é removido e a documentação de
autoria de cenário passa a apontar o manifesto como única declaração.

## A9 — `GraderSpec.type` é aceito e descartado

`src/evidrun/experiments/models.py:38` declara `type: str` sem `Literal`, com `extra="allow"`.
`src/evidrun/contracts/legacy.py:208-209` descarta o campo e fixa
`capability_ref("evidrun.evaluator", "exact-root-cause-legacy-v1")`. Um manifesto com
`type: llm_judge` é compilado como grader determinístico de substring. `graders[1:]` é ignorado sem
erro.

A admissão barra o resultado uma camada depois, exigindo `evaluator_ref` compatível
(`src/evidrun/runs/admission/catalog_checks.py:118-130`). Mas a falha é silenciosa no ponto onde
deveria ser explícita, e o adapter legado é o caminho de entrada de todo manifesto v1.

Direção de correção: `GraderSpec.type` como `Literal["deterministic"]`, e erro explícito para
`len(graders) != 1`.

## Correções documentais pontuais

Não são achados de código; são divergências entre documento normativo e comportamento atual.

- `docs/contracts/study-run-v1.md:37-38` afirma que API e CLI não aceitam decisão humana. Com
  `EVIDRUN_AUTHORITY=1` ambos aceitam e persistem (`src/evidrun/entrypoints/cli/app.py:566-601`,
  `src/evidrun/authority/router.py:145-169`). A afirmação vale apenas para o endpoint legado
  `POST /api/v1/contracts/revisions/{id}/decisions`, que é 503 fixo.
- `docs/contracts/study-run-v1.md:102-104` afirma que o digest do SubjectEnvelope não é recomputável a
  partir do bundle. Verdadeiro para o v2, falso para o v3, que exporta o envelope
  (`src/evidrun/evidence/bundle.py:289-292`) e o recomputa na verificação (`bundle.py:1001-1013`).
- `docs/planning/mvp-implementation-roadmap.md:70-77` descreve `Repository` com 2943 linhas e
  `AdmissionService.admit` com ~570 linhas. Após `812b330`,
  `src/evidrun/infrastructure/database/repository.py` tem 53 linhas e
  `src/evidrun/contracts/admission/service.py` tem 140, com `checks/` decomposto.
- `docs/planning/tasks/README.md:39-40` e `docs/planning/tasks/11-domain-seams.md:29` marcam WS-11 e
  WS-12 como `blocked`, apesar do trabalho estar em `main`.
- `docs/planning/tasks/01-workspace-project-surface.md` localiza `create_workspace`/`create_project`
  em `repository.py`; eles estão em `src/evidrun/infrastructure/database/catalog.py:49-62`.
- `docs/benchmarks/graders-and-judges.md:15-16` declara
  `implementation_refs: [src/evidrun/evaluations]` e `verification_refs: []`. O diretório contém
  apenas o grader de substring; nada de judge. O documento é `authority: normative` sem âncora de
  verificação.
- `docs/templates/experiment.md:28` pede seção `Guardrails`. `ExperimentManifest` é `extra="forbid"`
  (`src/evidrun/experiments/models.py:43`) e não tem o campo — um YAML fiel ao template falha na
  validação. `docs/templates/scenario.md:20-26` pede `Variável`, `Condições observáveis` e
  `Hidden data`, ausentes do `scenario.yaml` real.
- `docs/architecture/context-lifecycle.md:24-26` descreve um `ContextPlan` que não localizamos como
  tipo. `ContextComposer.compose` devolve dict que vira `ContextSnapshotRow` diretamente
  (`src/evidrun/runs/coordinator.py:461-478`). Pode ser diferença de nomenclatura; não confirmado.

## Vocabulário declarável e inalcançável

Registro para leitura de tipos, não pedido de mudança. Cada item cria expectativa que o runtime não
cumpre:

- `digest_mismatch` (`src/evidrun/contracts/admission/issues.py:30`) nunca é emitido. Falha de digest
  de runner usa `unsupported` (`checks/inventory.py:44-48`), por decisão explicitada em
  `checks/envelope.py:45-49`. Os dois modos de falha de runner ficam indistinguíveis no record.
- `workspace_status == "unavailable"` está no `Literal` e nenhum dos sete ramos de
  `checks/workspace.py:31-100` o produz.
- `IssueCategory = "capability"` não tem produtor na camada 1.
- `AdmissionIssue(blocking=False)` é construível e nenhum chamador em `src/` o usa; o único canal
  não-bloqueante real é `warnings`.
- Trigger de avaliação `kind="checkpoint"` tem validação implementada
  (`src/evidrun/infrastructure/database/evaluation/records.py:270-278`) e é inalcançável, porque a
  admissão rejeita toda `CheckpointPolicyRevision`.
- `workspace_runtime_kinds`, `interaction_modes` e `external_effect_modes` nunca são passados por
  `capability_envelope()` (`src/evidrun/runs/adapters.py:771-779`). Ficam nos defaults do dataclass. A
  promessa de que capability entra no envelope quando o adapter é montado vale para provider, tools,
  captura e budget; nesses três eixos, o único caminho é editar o default.
- `max_wall_seconds` nunca aparece em `supported_budget_fields` embora seja o único budget aplicado
  (`src/evidrun/runs/coordinator.py:735-742`), o que torna o campo enganoso lido isoladamente.
- `check_workspace` avalia classificação em todos os `input_bindings`, incluindo os invisíveis ao
  Subject (`checks/workspace.py:34-38`). Combinado com a rejeição de `evaluation_hidden_inputs`, não
  há caminho para dado de referência classificado no lado do evaluator.

## Nota de higiene

`except PermissionError, ValueError:` em `src/evidrun/runs/adapters.py:431`,
`src/evidrun/runs/admission/catalog_checks.py:170` e `src/evidrun/evidence/bundle.py:901` é a forma
sem parênteses do PEP 758, válida sob `requires-python = ">=3.14,<3.15"`. Confirmado com `ast.parse`.
Não é defeito; registrado porque a forma sugere erro de sintaxe em leitura rápida.
