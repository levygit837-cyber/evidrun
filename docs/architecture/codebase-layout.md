---
id: architecture-codebase-layout
type: architecture
title: Layout da codebase, costuras e orçamento estrutural
status: accepted
authority: normative
owner: core
created_at: 2026-07-24
updated_at: 2026-07-25
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
  - src/evidrun/contracts/admission/service.py
  - src/evidrun/contracts/admission/envelope.py
  - src/evidrun/runs/admission/catalog_checks.py
verification_refs:
  - tests/unit/test_code_budget.py
  - tests/unit/test_admission_oracle.py
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
│   │   ├── compiler.py     (530)  StudyCompiler + compiladores de envelope                        ▲
│   │   ├── admission/             ✅ service + envelope + checks/ por família
│   │   ├── evaluation.py          EvaluationValidator
│   │   ├── authority.py           HumanAttestationVerifier (Protocol) + Unavailable*
│   │   ├── legacy.py       (356)  convert() legado → v1 (257 linhas numa função)                 ▲
│   │   └── __init__.py     (143)  hub de re-export: 90 símbolos
│   ├── runs/                      execution plane
│   │   ├── adapters.py     (873)  catálogo + envelope + 2 Subjects + 2 graders                    ▲
│   │   ├── admission/             ✅ catalog_checks + scripted_checks + real_checks
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
│   │   │   ├── repository.py  (53)  ✅ raiz de composição: 9 agregados, zero query
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
└── scripts/                       validate_docs, generate_schemas, hooks
    ├── check_code_budget.py       CLI do gate
    └── code_budget/               policy, measure, report (violação vs. aviso), baseline
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

**`Repository` deixou de ser um módulo raso com implementação enorme.** Era 2.942 linhas, uma classe,
72 métodos, 50 públicos, com seis responsabilidades convivendo sem costura. Hoje `repository.py` tem
53 linhas e é raiz de composição: expõe nove agregados que compartilham um `UnitOfWork` e não executa
nenhuma query. A tabela abaixo é o estado atual dos agregados extraídos.

| Agregado | Módulo | Fronteira transacional |
| --- | --- | --- |
| ledger | `ledger/{store,appender,transitions,handlers}` | escreve evento e avança `RunRow.status` na mesma transação |
| fila/lease | `queue/{enqueue,lease,preparation,fencing}` | `BEGIN IMMEDIATE`, expiração de lease, `lease_generation` |
| contract registry | `registry.py` | verificação de autoridade humana no mesmo commit da decisão |
| evaluation/checkpoint | `evaluation/{records,checkpoints}` | grava record + evento factual atomicamente |
| catalog | `catalog.py` | uma transação por escrita, sem fencing |
| read-model | `read_model/{queries,dashboard,projections}` | somente leitura |

A costura de sessão que a decomposição promoveu a módulo (`unit_of_work.py`) já existia como
convenção privada: no baseline nenhum método público recebia sessão, e o único que operava dentro de
sessão alheia era `_append_event_once_in_session`. Como o estado de instância era mínimo
(`self.database` e `self.human_attestation_verifier`, sem cache mutável), a decomposição pôde ser por
composição de colaboradores.

**A decisão de admissão está fatiada em duas camadas, agora nomeadas.** `AdmissionService.admit`
(`contracts/admission/service.py`) não decide nada por conta própria: roda um checker por família
contra um `RuntimeCapabilityEnvelope` explícito e depois os validadores do par concreto de adapters,
dobrando os achados acumulados em um `AdmissionRecord`. **Toda chamada a `admit()` continua
executando as duas camadas**, sempre.

A divisão, antes implícita, hoje é declarada pelos tipos:

- `contracts/admission/checks/` decide contra o **envelope de capacidade declarado**
  (`RuntimeCapabilityEnvelope`), produzido por `RuntimeAdapterCatalog.capability_envelope()`;
- `runs/admission/` decide contra o **par concreto de adapters** resolvido para aquele RunSpec
  (`catalog_checks`, `scripted_checks`, `real_checks`), e sabe coisas que o envelope não representa.

O envelope deixou de ser oito kwargs montados à mão: `capability_envelope()` é a única fonte, e uma
capability só entra nele quando o adapter correspondente está montado — é por isso que o bloco de
provider, o catálogo de tools e a flag de raw capture ligam todos junto com `real_subject`.

### Camada dona de cada eixo de sobreposição

Os quatro eixos onde as duas camadas afirmam a mesma verdade têm dona declarada. A regra é: o
envelope responde "este runtime declara suportar a forma?"; o adapter responde "o par resolvido
executa exatamente isto?". As duas perguntas são distintas, então ambas continuam sendo feitas.

| Eixo | Dona da forma declarada | Dona do requisito concreto |
| --- | --- | --- |
| rede | `checks/workspace.py` via `envelope.network_modes` | `scripted_checks` (`offline_network`), `real_checks` (`provider_network`) |
| capture | `checks/interaction.py` via `envelope.supports_raw_encrypted_capture` | `scripted_checks` (`offline_raw_capture`), `real_checks` (`recoverable_subject_output`) |
| budgets | `checks/unsupported.py` via `envelope.supported_budget_fields` | `scripted_checks` (`offline_tool_budget`), `real_checks` (`max_tool_calls`) |
| evaluator | `checks/unsupported.py` (`runtime:evaluation_pipeline`) | `catalog_checks` (`evaluator_adapter`), `scripted_checks`, `real_checks` |

**A ordem de acumulação é contrato, não detalhe.** `missing_requirements`, `denied_policies` e
`issues` são tuplas persistidas que o ledger e o bundle leem de volta. Reordenar as chamadas de
checker em `service.py` muda a saída observável de qualquer spec que viole mais de uma família, e a
cadeia `elif` de workspace permanece uma decisão ordenada única por esse motivo.

**O oráculo de equivalência agora existe.** `tests/unit/test_admission_oracle.py` percorre 62
RunSpecs cobrindo cada ramo das duas camadas e trava decisão, statuses, `missing_requirements`,
`denied_policies`, warnings, inventário resolvido e a tripla
`(category, subject_ref, reason.code, reason.detail, blocking)` de cada issue, byte a byte, contra
`tests/unit/admission_oracle.json`. Os cinco ramos antes sem cobertura nenhuma — digest divergente de
runner, `mount_authority`, `read_write_mount`, `runtime_kind` não suportado e
`credential_available=False` — passaram a ser exercitados.

Um defeito latente apareceu ao exercitar o ramo de provider pela primeira vez: `admit` preenchia
`provider_profile_id` sem digest, model, reasoning e adapter quando o profile não era resolvido, e o
validador de `ResolvedAgentInventory` rejeitava essa combinação — `admit()` levantava
`ValidationError` em vez de devolver `decision=rejected`. Corrigido: um profile não resolvido deixa o
bloco de provider inteiro vazio.

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

A árvore abaixo é o destino, não um retrato do disco. Dois blocos já aterrissaram e estão marcados
com `✅ ENTREGUE`: `infrastructure/database/` (WS-11) e os dois pacotes `admission/` (WS-12). Todo o
resto continua sendo workstream futuro com issue própria, e nada não marcado descreve comportamento
implementado.

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
│   ├── admission/                  ✅ ENTREGUE em WS-12                               [WS-12]
│   │   ├── service.py              orquestra: roda checkers, monta AdmissionRecord
│   │   ├── envelope.py             RuntimeCapabilityEnvelope: o que o runtime declara suportar
│   │   ├── checks/                 um módulo por família; entregue agrupado em quatro módulos
│   │   │                           (inventory, workspace, interaction, unsupported) em vez dos
│   │   │                           dez abaixo; a divisão fina permanece alvo
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
│   ├── admission/                  ✅ ENTREGUE em WS-12: a 2ª camada, agora nomeada   [WS-12]
│   │   ├── catalog_checks.py        ← validate_spec: o que só o par de adapters sabe
│   │   ├── scripted_checks.py       ← _validate_scripted_spec
│   │   └── real_checks.py           ← _validate_real_spec
│   ├── adapters/                   ← adapters.py (873) dividido por papel
│   │   ├── catalog.py              RuntimeAdapterCatalog + declaração do envelope
│   │   │                           ⚠ o envelope já é declarado, mas ainda em adapters.py
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
├── infrastructure/database/         ✅ ENTREGUE em WS-11                              [WS-11]
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
