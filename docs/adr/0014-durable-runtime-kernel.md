---
id: adr-0014
type: adr
title: Runtime Kernel durável com Run, attempt, lease e fencing
status: accepted
authority: normative
volatility: timeless
owner: core
created_at: 2026-07-23
updated_at: 2026-07-23
applies_to: runtime-kernel@1
sources:
  - docs/adr/0002-control-plane-and-execution-plane.md
  - docs/adr/0009-study-run-contract-composition.md
  - docs/contracts/study-run-v1.md
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun/runs/coordinator/attempt.py
  - src/evidrun/runs/worker.py
  - src/evidrun/runs/adapters/catalog.py
  - src/evidrun/infrastructure/database/repository.py
  - alembic/versions/0004_runtime_kernel.py
verification_refs:
  - tests/integration/test_runtime_kernel.py
  - tests/integration/test_runtime_queue.py
---

# Contexto

O pipeline anterior só era executável porque `EvidrunService` conhecia simultaneamente o benchmark
`CRL-CTX-002`, sua fixture, o runner scripted e o grader exato. O worker era apenas uma superfície de
processo, sem fila, lease ou retomada durável. Uma Run admitida fora desse bootstrap podia ser
representada, mas não atravessava o Execution Plane.

# Decisão

Execução passa a ser coordenada por um `RunExecutionCoordinator` genérico, alimentado por um catálogo
de adapters compartilhado pela admissão e pelo worker. A admissão só produz `admitted` quando runner,
input materializer, workspace, interaction e EvaluationPlan formam um adapter completo no catálogo
ativo. Incompatibilidade é descoberta antes do enqueue.

O subconjunto executável inicial permanece fechado: Goal `goal_state`, protocolo `single_turn`, uma
interação, workspace `in_process`, rede desabilitada, efeitos externos negados, input `public` ou
`internal`, exatamente um input Subject-visible `text/plain` UTF-8, `ContextPolicy`, budget de
`max_wall_seconds`, stops terminais `goal_complete`/`budget_exhausted` e um grader determinístico
booleano acionado por `subject.responded`.

Cada Run possui exatamente um `RunExecutionJob`. Cada reserva cria um `RunExecutionAttempt` com
ordinal e `lease_generation` próprios. Expiração ou release cria uma nova tentativa sobre a mesma
Run. Retry solicitado pelo usuário cria outra Run UUIDv7 e registra `retry_of`; uma Run completed não
é elegível ao endpoint de retry.

SQLite opera em WAL. Claim usa `BEGIN IMMEDIATE` para expirar lease vencido, reservar o job FIFO,
incrementar a geração e criar o attempt na mesma transação. Writes factuais do coordinator carregam
`job_id`, `attempt_id`, `worker_id` e geração; a validação do fencing ocorre na mesma transação da
escrita. Heartbeat atrasado não ressuscita lease e worker antigo não publica resposta, evaluation ou
terminal.

O `operation_key` é uma chave operacional privada por Run. Repetir uma operação com tipo e payload
idênticos retorna o evento existente; reutilizar a chave com outra semântica falha. Ela não integra o
envelope público nem o hash factual do Run Event.

O primeiro `run.running` inicia o wall clock científico. Attempts posteriores herdam o budget
restante. Crash antes de `subject.invoked` permite retomada convergente. Crash depois de
`subject.invoked` e antes de uma resposta durável termina a Run como failed por resultado
indeterminado; não ocorre reinvocação silenciosa.

O Context Snapshot selecionado vira artifact CAS canônico. O `SubjectEnvelope` semântico exato é
persistido antes de `subject.invoked`, e toda leitura revalida seu schema e digest. Nenhum locator,
path ou URL entra nos contratos, eventos ou bundles.

# Atomicidade e reconciliação

- enqueue valida RunSpec e AdmissionRecord exatos, cria Run, `run.queued` e job em uma transação;
- claim, heartbeat, release, reject e complete são cercados pela geração do lease;
- preparação é convergente por unicidade de snapshot, SubjectEnvelope e operation keys;
- invocação externa ocorre fora da transação, com fencing antes e depois;
- Subject response, evaluation e terminal possuem writes idempotentes e podem ser reconciliados;
- terminal já existente não gera outro terminal e apenas reconcilia o job/attempt;
- rejeição por inconsistência canônica não fabrica evidência científica.

# Consequências

API e CLI apenas enfileiram. `evidrun-worker` é o executor durável. O demo permanece síncrono para
compatibilidade, mas importa sua fixture no ArtifactStore, enfileira somente seus jobs e os drena com
o mesmo worker/coordinator.

Attempts são evidência operacional, enquanto o Run Event ledger continua sendo a autoridade factual
do lifecycle. O Evidence Bundle v3 exporta ambos e o SubjectEnvelope, mas permanece
`references_only`, não portátil e não replayable.

# Alternativas rejeitadas

- criar nova Run automaticamente ao expirar lease: confundiria recuperação operacional com nova
  observação científica;
- manter o benchmark como executor: impediria admissão e retomada genéricas;
- retry dentro da Run original: apagaria a distinção entre fato científico e tentativa operacional;
- reinvocar após crash sem resposta durável: poderia duplicar efeitos ou produzir dois resultados;
- incluir paths no ArtifactRef: transformaria identidade de conteúdo em autoridade de acesso.
