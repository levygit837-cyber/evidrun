---
id: architecture-codebase-layout
type: architecture
title: Layout da codebase, costuras e orçamento estrutural
status: accepted
authority: normative
owner: core
created_at: 2026-07-24
updated_at: 2026-07-24
applies_to: repository
sources:
  - docs/adr/0003-modular-monolith.md
  - docs/adr/0017-structural-budget-and-named-seams.md
  - docs/architecture/system.md
  - docs/planning/tasks/11-domain-seams.md
supersedes: []
superseded_by: null
implementation_refs:
  - scripts/check_code_budget.py
  - code-budget.toml
verification_refs:
  - tests/unit/test_code_budget.py
---

# Layout da codebase

Este documento tem duas metades que nunca devem ser lidas como uma só. A seção **Hoje** descreve o
que está no disco e é verificável por medição. A seção **Alvo** descreve a divisão para onde estamos
indo e não descreve comportamento implementado.

Vocabulário: **módulo** (interface + implementação), **costura** (o lugar onde a interface vive),
**adapter** (o concreto que satisfaz a interface em uma costura), **profundidade** (quanto
comportamento cabe atrás de uma interface pequena). Ver `skill://codebase-design`.

## Hoje

### Medição

Números de 2026-07-24, produzidos por `scripts/check_code_budget.py`.

| Escopo | Arquivos | Linhas |
| --- | --- | --- |
| `src/evidrun/**/*.py` | 68 | ~15.400 |
| `tests/**/*.py` | 30 | ~6.900 |
| `apps/web` + `apps/desktop` (`.ts`/`.tsx`) | 35 | 6.670 (1.603 gerados) |

Distribuição de tamanho em `src/` + `apps/` + `scripts/`: 76 arquivos com até 150 linhas, 14 entre
151 e 300, 3 entre 301 e 500, 4 entre 501 e 800, e 9 acima de 800. A cauda é curta e concentrada:
**seis arquivos carregam 8.500 linhas**, e a mediana do repositório é confortável. O problema não é
volume, é concentração.

### A árvore atual

```
evidrun/
├── src/evidrun/                   monólito modular Python (ADR 0003)
│   ├── shared/                    vocabulário sem dependências para cima
│   │   ├── types.py               ids, canonical_json, sha256_json, utc_now   [fan-in 19: o mais usado]
│   │   ├── settings.py            Settings, paths, EVIDRUN_AUTHORITY
│   │   ├── capabilities.py        capability_ref()            ⚠ importa contracts.base
│   │   └── ports.py               Protocols: LabAgent, SubjectRunner, Provider, Approval, Trace
│   │                              ⚠ 4 dos 9 Protocols têm zero implementação
│   ├── contracts/                 a LINGUAGEM do domínio: modelos Pydantic + validação, sem I/O
│   │   ├── base.py         (356)  ContractModel, ArtifactRef, RevisionEnvelope, autoridade humana
│   │   ├── authoring.py    (871)  65 classes: Goal/Scenario/Study/Workspace/Protocol/Evaluation   ▲
│   │   ├── runtime.py     (1060)  46 classes: RunSpec, records, payloads de evento               ▲
│   │   ├── compiler.py    (1156)  StudyCompiler + AdmissionService.admit (567 linhas)            ▲
│   │   ├── evaluation.py          EvaluationValidator
│   │   ├── authority.py           HumanAttestationVerifier (Protocol) + Unavailable*
│   │   ├── legacy.py       (356)  convert() legado → v1 (257 linhas numa função)                 ▲
│   │   └── __init__.py     (143)  hub de re-export: 90 símbolos
│   ├── runs/                      execution plane
│   │   ├── adapters.py    (1043)  catálogo + 2 Subjects + 2 graders + validate_spec              ▲
│   │   ├── coordinator.py  (773)  RunExecutionCoordinator.execute_attempt (190 linhas)           ▲
│   │   ├── composition.py         build_runtime_kernel: a única raiz de composição do runtime
│   │   ├── service.py             bootstrap_demo
│   │   └── worker.py              loop de claim/heartbeat/release
│   ├── evidence/
│   │   └── bundle.py      (1624)  export v1/v2/v3 + verify ramificado por schema_version         ▲
│   ├── authority/                 ✅ a fatia vertical mais bem formada do repo
│   │   ├── models.py, repository.py    persistência própria
│   │   ├── crypto.py, verifier.py, authenticator.py, challenge.py, policy.py
│   │   ├── service.py, subject.py, router.py
│   ├── infrastructure/
│   │   ├── database/
│   │   │   ├── engine.py   (114)  Database: engine, sessionmaker, migrations aditivas
│   │   │   ├── models.py   (298)  20 Row classes SQLAlchemy
│   │   │   └── repository.py (2942)  ⛔ God Object: 1 classe, 72 métodos, 50 públicos          ▲▲▲
│   │   ├── artifacts/store.py     CAS por projeto, cifrado
│   │   └── providers/             openai_responses, credentials (Keychain)
│   ├── contexts/engine.py         composição de contexto
│   ├── evaluations/deterministic.py
│   ├── subject_runners/scripted.py
│   ├── experiments/models.py      manifest legado
│   ├── providers/profile.py       ProviderProfile
│   ├── entrypoints/
│   │   ├── api/app.py      (623)  create_app com 38 rotas numa função de 542 linhas             ▲
│   │   ├── cli/app.py      (609)  10 Typer apps, 25 comandos
│   │   └── worker/app.py          entrypoint do worker
│   └── (stubs sem código)         approvals, comparisons, conversations, lab_agent,
│                                  projects, scenarios, workspaces
│                                  ⚠ 5 dos 7 conceitos JÁ existem dentro de Repository
├── apps/
│   ├── web/src/
│   │   ├── api/client.ts          HTTP + SSE
│   │   ├── data/{contracts,adapters}.ts   interfaces de adapter + implementações
│   │   ├── generated/contracts.ts (1603)  gerado, isento de orçamento
│   │   ├── ui/primitives.tsx      Button/Input/StatusIndicator/LoadingState/EmptyState/ErrorState
│   │   │                          ⚠ subutilizado: 3 páginas reimplementam badge e estado vazio
│   │   └── features/
│   │       ├── observability/  ObservabilityPage.tsx (918) + observabilityModel.ts (310) ✅ padrão
│   │       ├── laboratory/     LaboratoryPage.tsx (818) + DemoLaboratoryAdapter.ts       ▲
│   │       └── create/         CreatePage.tsx (597)                                       ▲
│   └── desktop/src/{main,preload,shared}/    lifecycle do backend, sem domínio
├── tests/{unit,integration,acceptance,security,live,support}/
├── schemas/generated/             OpenAPI + JSON Schema, gerados
├── docs/{adr,architecture,contracts,benchmarks,operations,planning,governance,agents,product}/
├── code-budget.toml               política + ratchet do orçamento estrutural
└── scripts/                       validate_docs, generate_schemas, check_code_budget, hooks
```

`▲` marca arquivo no ratchet do orçamento. `⛔` marca o God Object.

### Como as pastas conversam

O fluxo canônico atravessa o repositório em uma direção. Cada seta é um import real, medido.

```
                 AUTORIA                    ADMISSÃO                 EXECUÇÃO              EVIDÊNCIA
                 (humano decide)            (falha fechado)          (worker)              (auditor)

  entrypoints/cli ──┐
  entrypoints/api ──┼──► contracts/authoring ──► contracts/compiler ──► runs/coordinator ──► evidence/bundle
  authority/router ─┘      parse_revision           StudyCompiler         execute_attempt      export_run_v3
                            RevisionEnvelope         ↓ RunSpec              ↓                    verify()
                                 │                AdmissionService      runs/adapters             ▲
                                 │                    .admit()          Subject + grader          │
                                 │                      │  ▲                  │                   │
                                 │                      │  └── validate_spec ─┘                   │
                                 │                      │      (2ª camada de rejeição)            │
                                 ▼                      ▼                  ▼                      │
                          ┌──────────────────────────────────────────────────────────────────────┐│
                          │  infrastructure/database/repository.py  — TODOS param aqui           ││
                          │  ledger · fila/lease · contract registry · evaluation · read-model    ├┘
                          └──────────────────────────────────────────────────────────────────────┘
                                 │                                            │
                                 ▼                                            ▼
                          infrastructure/artifacts/store.py           infrastructure/database/engine.py
                          (CAS cifrado por projeto)                   (SQLite/WAL, sessionmaker)

  apps/desktop/main ──spawn──► entrypoints/api  ◄──HTTP/SSE── apps/web/api/client
  (lifecycle, sem domínio)                                     ↑
                                                        apps/web/data/adapters
                                                               ↑
                                              features/{create,laboratory,observability}
```

Leitura do grafo em uma frase: **autoria produz revisions imutáveis, compilação produz um RunSpec,
admissão decide se aquele RunSpec pode existir como Run, o worker executa sob lease com fencing, e o
bundle exporta o que o ledger registrou.** Nada disso é reversível: uma Run não existe antes de
`AdmissionRecord.decision=admitted`, e o ledger é a autoridade normativa da Run.

### Onde o desenho já está bom

Três coisas funcionam e devem ser copiadas, não redesenhadas.

`authority/` é a fatia vertical de referência: modelos, persistência, crypto, policy, serviço e
router convivem numa pasta, e o resto do sistema fala com ela por uma interface pequena
(`HumanAttestationVerifier`, um Protocol em `contracts/authority.py`). Essa é uma costura real: tem
dois adapters de verdade (`LocalWebAuthnVerifier` e `UnavailableHumanAttestationVerifier`), e o
sistema falha fechado quando o adapter não é confiável.

`runs/composition.py` é a única raiz de composição do runtime, com 52 linhas. Quem quiser trocar
provider, materializer ou catálogo tem um lugar para fazer isso.

`observabilityModel.ts` separa derivação de dados de apresentação num módulo puro e testável sem
renderizar nada. É o padrão que as outras duas páginas web ainda não seguem.

### Onde o desenho está errado

**`Repository` é um módulo raso com implementação enorme.** 2.942 linhas, uma classe, 72 métodos,
50 públicos. Cinco responsabilidades convivem sem costura entre elas:

| Agregado | Métodos | Linhas | Fronteira transacional |
| --- | --- | --- | --- |
| ledger | `append_event` (481), `_event_transition` (61), `_append_event_once_in_session` (71), `save_subject_response` (66), `_validate_evidence_boundary` | ~700 | escreve evento e avança `RunRow.status` na mesma transação |
| fila/lease | `enqueue_run` (154), `claim_next_job` (85), `heartbeat/assert/release/reject/complete_lease`, `prepare_run_execution` (139), 7 helpers de fencing | ~640 | `BEGIN IMMEDIATE`, expiração de lease, `lease_generation` |
| contract registry | `save_contract_revision` (52), `decide_contract_revision`, `import_legacy_contract_package` (60), `_persist_contract_decision` (58), `contract_registry` (35), 3 getters | ~250 | verificação de autoridade humana no mesmo commit da decisão |
| evaluation/checkpoint | `save_evaluation_record` (223), `save_deterministic_evaluation` (126), `save_checkpoint_record` (118), `save_grade`, 2 validadores de fronteira | ~510 | grava record + evento factual atomicamente |
| catalog | `create_workspace`, `create_project`, `create_run` (58), `save_run_spec`, `save_admission_record` (70), `save_experiment_revision`, `save_comparison`, `save_snapshot`, `create_chat_session`, `add_chat_message`, `save_subject_envelope` | ~380 | uma transação por escrita, sem fencing |
| read-model | `latest_dashboard` (45), 12 getters, 7 `_*_dict` | ~380 | somente leitura |

Dois fatos medidos que decidem o desenho da decomposição:

1. **Nenhum método público recebe sessão.** Todos abrem `with self.database.session()`. O único que
   opera dentro de uma sessão alheia é `_append_event_once_in_session`, um `@staticmethod` que
   recebe `session` explicitamente. A costura de sessão portanto **já existe** como convenção
   privada — a decomposição a promove, não a inventa.
2. **O estado de instância é mínimo:** `self.database` e `self.human_attestation_verifier`. Nada de
   cache mutável compartilhado. Decompor por composição de colaboradores é possível sem inventar
   contexto.

Só dois métodos públicos não têm nenhum chamador externo (`update_run`, `project_id_for_run_spec`).
Os outros 48 são interface real, o que significa que a extração é um trabalho de migração de
chamadores, não de renomeação interna.

**A decisão de admissão está fatiada em duas camadas que ninguém declarou.** `AdmissionService.admit`
faz 26 checagens em 567 linhas acumulando quatro listas locais (`missing`, `denied_policies`,
`warnings`, `issues`). Na linha 990 ela chama `self.execution_validators`, que
`RuntimeAdapterCatalog.admission_service()` preenche com `self.validate_spec` — outras 24 checagens
em `runs/adapters.py`. Ou seja: **toda chamada a `admit()` executa as duas camadas**, sempre.

A divisão entre elas não é arbitrária, mas também não é explícita em lugar nenhum:

- `admit` decide contra um **envelope de capacidade declarado** que o catálogo injeta
  (`network_modes`, `supported_budget_fields`, `supports_raw_encrypted_capture`,
  `runtime_capabilities`, `workspace_runtime_kinds`, `interaction_modes`);
- `validate_spec` decide contra o **par concreto de adapters** resolvido para aquele RunSpec
  (scripted vs. real), e sabe coisas que o envelope não representa.

O risco é deriva silenciosa: `admission_service()` monta o envelope à mão a partir dos mesmos
adapters que `validate_spec` inspeciona. Duas leituras da mesma verdade, sincronizadas por atenção
humana. Há sobreposição semântica confirmada em rede (`network_modes` no envelope vs.
`offline_network`/`provider_network` nos adapters), capture (`supports_raw_encrypted_capture` vs.
`offline_raw_capture`/`recoverable_subject_output`) e budgets (`supported_budget_fields` vs.
`offline_tool_budget`/`max_tool_calls`). Nenhuma duplicata produz mensagem idêntica, então hoje isso
não é bug observável — é dívida que só aparece quando alguém adiciona uma capability em um lado.

**Nenhum teste asserta `reason.code` nem `reason.detail`.** A suíte cobre decisão
(`admitted`/`rejected`) e tokens de `missing_requirements`, não as mensagens. Consequência direta
para o refactor: a rede de segurança existente **não** detecta troca de mensagem ou de código de
rejeição. Ramos sem cobertura nenhuma que localizamos: digest divergente de runner no registry,
`mount_authority`, `read_write_mount`, `runtime_kind` não suportado, e
`credential_available=False` em `_validate_real_spec`.

**`bundle.py` mistura três formatos e sua verificação.** Export v1 (42–87), v2 (88–229), v3
(230–345), `verify` (347–563) despachando por `schema_version`, `_verify_v2_*` (564–919),
`_verify_v3_*` (920–1213), validação de record de evaluation e checkpoint (1214–1435) e utilitários
de zip/manifest (1436–1625).

**Os 7 pacotes stub são uma promessa contraditória.** `projects/`, `workspaces/`, `comparisons/`,
`conversations/`, `scenarios/` prometem uma fatia vertical cujo conteúdo já mora dentro de
`Repository` (`ProjectRow`, `WorkspaceRow`, `ComparisonRow`, `ChatSessionRow` e seus métodos).
`approvals/` e `lab_agent/` prometem capacidade que não existe. Um agente que abre a pasta lê
"ainda não implementado" e um que grepa `create_project` encontra código funcionando.

**Três violações de direção de import**, todas pequenas e todas reais:
`shared/capabilities.py → contracts.base`, `shared/settings.py → providers`, e
`infrastructure/{database,artifacts} → contracts`. A última é hidratação legítima de contrato (o
repository desserializa `RunSpec` e `EvaluationRecord`), mas `repository.py` também importa
`EVENT_ALLOWED_RUN_STATUSES` e `UNSUPPORTED_RUNTIME_EVENT_TYPES` de `contracts/runtime.py` e impõe
regra de fase de Run — isso é regra de domínio executando na camada de infraestrutura.

## Alvo

Nada nesta seção está implementado. Cada bloco é um workstream com issue própria.

### Princípio

Uma pasta por capacidade, e dentro dela uma costura nomeada por variação real. `contracts/`
permanece horizontal de propósito: é o vocabulário compartilhado, e um vocabulário sem I/O não é uma
camada, é um dicionário.

Três regras que decidem onde um arquivo novo vai morar:

1. **Se duas coisas precisam commitar juntas, moram no mesmo módulo.** Atomicidade define pasta.
2. **Se algo varia por adapter, a variação vira costura; se não varia, não vira.** Um adapter
   significa costura hipotética. Dois significam costura real.
3. **Se um arquivo passa de 500 linhas, ele está escondendo uma costura.** Ver ADR 0017.

### A árvore alvo

```
src/evidrun/
├── contracts/                      vocabulário: modelos + validação, zero I/O
│   ├── base.py                     (mantém)
│   ├── authoring/                  ← authoring.py (871) dividido por família de revision
│   │   ├── goal.py  scenario.py  study.py  workspace.py  protocol.py  evaluation.py
│   │   └── parse.py                parse_revision + despacho por tipo
│   ├── runtime/                    ← runtime.py (1060) dividido por papel
│   │   ├── spec.py                 RunSpec e satélites
│   │   ├── records.py              Admission/Run/Evaluation/Checkpoint/Progress records
│   │   ├── envelope.py             SubjectEnvelope, EvaluatorEnvelope
│   │   ├── events.py               payloads + EVENT_ALLOWED_RUN_STATUSES
│   │   │                           + UNSUPPORTED_RUNTIME_EVENT_TYPES
│   │   └── execution.py            RunExecutionJob, RunExecutionAttempt
│   ├── admission/                  ← AdmissionService.admit (567) virado composição   [WS-12]
│   │   ├── service.py              orquestra: roda checkers, monta AdmissionRecord
│   │   ├── envelope.py             RuntimeCapabilityEnvelope: o que o runtime declara suportar
│   │   ├── checks/                 um módulo por família; cada checker é (spec, env) -> issues
│   │   │   ├── runner.py           runner registrado + digest
│   │   │   ├── provider.py         profile disponível + digest
│   │   │   ├── capability.py       registry, interface version, permissões, authority_constraints
│   │   │   ├── input_class.py      sensitive/restricted
│   │   │   ├── workspace.py        runtime_kind, mounts, read_write, write_zones, secrets
│   │   │   ├── policy.py           network, external_effect
│   │   │   ├── interaction.py      protocolo, max_turns, materialização single-turn
│   │   │   ├── capture.py          capture mode
│   │   │   ├── unsupported.py      progress artifact, checkpoint, bounded exploration,
│   │   │   │                       adjudicação humana, disclosure, pipeline multi-stage
│   │   │   └── budget.py           budgets + stop conditions
│   │   └── issues.py               construção canônica de AdmissionIssue
│   ├── compiler.py                 StudyCompiler + SubjectEnvelopeCompiler (sem admissão)
│   ├── legacy/                     ← legacy.py; convert() (257) por seção de pacote
│   ├── evaluation.py  authority.py
│   └── __init__.py                 hub de re-export (mantém: é a interface pública do vocabulário)
├── runs/
│   ├── admission/                  a 2ª camada, agora nomeada                          [WS-12]
│   │   ├── catalog_checks.py        ← validate_spec: o que só o par de adapters sabe
│   │   ├── scripted_checks.py       ← _validate_scripted_spec
│   │   └── real_checks.py           ← _validate_real_spec
│   ├── adapters/                   ← adapters.py (1043) dividido por papel
│   │   ├── catalog.py              RuntimeAdapterCatalog + declaração do envelope
│   │   ├── subject_scripted.py  subject_responses.py
│   │   ├── grader_cause.py  grader_read_answer.py
│   │   ├── tool_read_text.py  materializer.py
│   ├── coordinator/                ← coordinator.py (773) por fase
│   │   ├── attempt.py              execute_attempt
│   │   ├── prepare.py  resume.py
│   ├── composition.py  service.py  worker.py
├── evidence/                       ← bundle.py (1624)                                  [WS-30]
│   ├── export/{comparison_v1,comparison_v2,run_v3}.py
│   ├── verify/{dispatch,v2,v3,records}.py
│   └── archive.py                  zip, checksum, manifest
├── infrastructure/database/                                                            [WS-11]
│   ├── engine.py                   (mantém)
│   ├── models.py                   (mantém)
│   ├── unit_of_work.py             ★ a costura nova: sessão explícita + agregados vinculados
│   ├── ledger/
│   │   ├── appender.py             hash chain, operation_key, sequência
│   │   ├── transitions.py          máquina de fase + event types reservados
│   │   └── handlers/               um módulo por família de evento factual
│   ├── queue/
│   │   ├── enqueue.py              enqueue_run
│   │   ├── lease.py                claim/heartbeat/assert/release/reject/complete + fencing
│   │   └── preparation.py          prepare_run_execution
│   ├── registry.py                 contract revisions e decisões
│   ├── evaluation/{records.py,checkpoints.py}
│   ├── catalog.py                  escritas de entidade de topo
│   └── read_model/{dashboard.py,projections.py}
└── (stubs removidos)               approvals, comparisons, conversations, lab_agent,
                                    projects, scenarios, workspaces
```

`★` é o ponto que faz o resto funcionar. `UnitOfWork` expõe a sessão e os agregados vinculados a ela;
uma operação que precisa de atomicidade entre agregados (gravar evento e avançar status, preparar
execução sob fencing) fica no agregado dono da atomicidade e chama colaboradores **passando a
sessão**, nunca abrindo uma nova. Sem esse módulo, decompor `Repository` transforma uma transação em
duas e quebra o fencing de lease.

### O grafo alvo

```
  entrypoints/{api,cli,worker}          apps/web + apps/desktop
          │                                     │  HTTP/SSE apenas
          ▼                                     ▼
  ┌───────────────────────────────────────────────────────┐
  │ contracts/  (vocabulário: modelos + validação, sem I/O)│◄── authority/ (fatia vertical)
  │   authoring/ ─► compiler ─► admission/service          │
  │                              ▲ checks/ (por família)   │
  └───────────────────────────────┼───────────────────────┘
          │                       │ envelope declarado
          ▼                       │
  runs/                           │
    adapters/catalog ─────────────┘  ★ única fonte do envelope
    admission/catalog_checks ────────► issues do par concreto
    coordinator/ ──────────────┐
          │                    │
          ▼                    ▼
  infrastructure/database/unit_of_work
    ├── ledger/     (autoridade normativa da Run)
    ├── queue/      (lease + fencing)
    ├── registry/   (decisões humanas)
    ├── evaluation/ (records append-only)
    ├── catalog/    (entidades de topo)
    └── read_model/ (projeções; só leitura)
          │
          ▼
  engine (SQLite/WAL)      artifacts/store (CAS cifrado)      evidence/ (export + verify)
```

Direções proibidas, que o orçamento não pega e a revisão pega:
`contracts/ → infrastructure/`, `contracts/ → runs/`, `shared/ → qualquer coisa`,
`infrastructure/ → runs/`, e `apps/web → electron` ou `node:*`.

As três violações atuais de direção resolvem assim: `shared/capabilities.py` vira
`contracts/capabilities.py` (é vocabulário, não utilidade); `shared/settings.py` para de importar
`providers` recebendo o profile por parâmetro; e a imposição de fase de Run sai de `repository.py`
para `ledger/transitions.py`, que continua lendo a tabela de `contracts/runtime/events.py` — ler
uma tabela declarativa de contrato é hidratação, executar a regra de fase dentro do SQL é
vazamento.

### O que a extração NÃO pode mudar

Refactor não promove capability. Toda capability hoje rejeitada continua rejeitada com o mesmo
código (`unsupported`, `denied`, `unavailable`) e a mesma mensagem observável. Como a suíte atual não
asserta mensagem nem código, a extração de admissão exige um oráculo novo — um teste de equivalência
que percorra RunSpecs cobrindo cada ramo e trave decisão, códigos e mensagens — antes de mover a
primeira linha. Sem esse oráculo não existe "sem perda de precisão", só esperança.

Igualmente intocável: ordem e hash chain do ledger, atomicidade de `claim_next_job` e
`prepare_run_execution`, a natureza append-only de records de evaluation, e o fato de que
`ArtifactRef` não carrega `locator`.

### Ordem de execução

```
WS-11 repository        ─► read_model → registry → evaluation → catalog → ledger → queue
   (serial por agregado, suíte completa verde entre cada um; queue por último porque
    concentra BEGIN IMMEDIATE e fencing)
        │
        ├─► WS-12 admissão   (depende de nada de WS-11, mas compete por compiler.py)
        ├─► WS-30 bundle     (independente: só evidence/)
        └─► WS-13 páginas web (independente: só apps/web/)
```

WS-11 é serial de propósito. WS-12, WS-30 e WS-13 tocam árvores disjuntas e podem rodar em paralelo
entre si e com WS-11, porque nenhum deles edita `infrastructure/database/`.

## Como um agente navega isto

Um agente que chega neste repositório com uma tarefa deve responder três perguntas antes de abrir
arquivo, e cada resposta tem um endereço fixo:

**"Isso é contrato?"** Se a mudança altera o shape de um documento persistido, exportado ou
mostrado ao Subject, o endereço é `docs/contracts/` primeiro e `contracts/` depois — e provavelmente
precisa de ADR. Contrato não se ajusta de passagem.

**"Isso é capacidade nova?"** Se sim, ela nasce rejeitada. O caminho é
`contracts/admission/checks/` mais o envelope em `runs/adapters/catalog.py`. Anunciar capacidade
antes do adapter é a falha que o sistema inteiro foi desenhado para impedir.

**"Isso é projeção?"** Status, dashboard, comparison, relatório e grafo são projeções do ledger.
Mudam em `infrastructure/database/read_model/` e nunca viram segunda fonte de verdade.

O orçamento estrutural existe para que essas três perguntas continuem respondíveis. Um arquivo de
2.942 linhas não tem endereço: ele é o endereço de tudo.
