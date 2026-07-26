---
id: operations-runtime-worker
type: operations
title: Execução durável de Runs
status: implemented
authority: normative
volatility: current
owner: core
created_at: 2026-07-23
updated_at: 2026-07-23
applies_to: runtime-kernel@1
sources:
  - docs/adr/0014-durable-runtime-kernel.md
  - docs/adr/0016-real-subject-read-tool-and-tracing.md
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun/entrypoints/worker/app.py
  - src/evidrun/entrypoints/cli/app.py
  - src/evidrun/entrypoints/api/app.py
verification_refs:
  - tests/integration/test_runtime_kernel.py
  - tests/integration/test_runtime_queue.py
---

# Fluxo operacional

O fluxo nominal é:

```text
register revisions -> accept -> compile -> admit -> enqueue
-> worker claim -> prepare -> execute -> evaluate -> terminal -> export
```

API e CLI não executam o Subject. Elas persistem a Run e o job e retornam imediatamente. Inicie um
worker separado:

```bash
uv run evidrun-worker --data-dir ./data
```

Para processar no máximo um job:

```bash
uv run evidrun-worker --data-dir ./data --once
```

Os defaults são poll de 1 segundo, lease de 30 segundos e heartbeat de 10 segundos. O heartbeat deve
ser estritamente menor que metade do lease. `--worker-id` é opcional; sem ele, o identificador combina
hostname, PID e UUID.

O aplicativo Electron ainda não supervisiona esse processo: ele faz spawn apenas de
`evidrun serve --desktop-handshake`, que sobe a API. Uma Run enfileirada pela interface permanece
`queued` até que um worker seja iniciado por fora. Fechar essa lacuna é a WS-02.

# API e CLI

Enqueue e retry exigem uma AdmissionRecord admitida para o RunSpec exato e uma chave de
idempotência. Retry exige uma AdmissionRecord nova, criada depois do terminal da Run de origem; não
é permitido reutilizar a admission antiga:

```bash
uv run evidrun run enqueue RUN_SPEC_ID \
  --admission-id ADM_ID --idempotency-key request-123 --data-dir ./data

uv run evidrun run retry RUN_ID \
  --admission-id ADM_ID --idempotency-key retry-123 --data-dir ./data

uv run evidrun run inspect RUN_ID --data-dir ./data
uv run evidrun bundle export-run RUN_ID --data-dir ./data
uv run evidrun bundle verify ./data/exports/RUN_ID.evidrun.zip
```

Na API, as operações equivalentes são `POST /api/v1/run-specs/{id}/runs`,
`POST /api/v1/runs/{id}/retries`, `GET /api/v1/runs/{id}` e
`POST /api/v1/runs/{id}/evidence-bundles`. Enqueue e retry exigem o header `Idempotency-Key`.

# Recuperação

Uma tentativa com lease expirado vira `expired`; o próximo claim cria outro attempt na mesma Run.
Antes de `subject.invoked`, a preparação pode ser repetida. Depois de uma invocação sem resposta
durável, o worker não reinvoca e encerra a Run como failed por resultado indeterminado. Um novo
processamento exige retry explícito, que cria outra Run com `retry_of`.

Quando a policy é `raw_encrypted`, o Subject result é persistido como artifact cifrado antes da
avaliação. Crash depois de `subject.responded` e antes do EvaluationRecord permite ao próximo attempt
reconstruir o result, avaliar e terminar sem nova chamada ao provider. Uma tool call pendente é
fechada como `tool.failed` antes do terminal; uma Run terminal não aceita chamada aberta.

`max_wall_seconds` começa no primeiro `run.running`. Reinício, novo attempt ou heartbeat não zeram o
budget. Quando o tempo já acabou, a recuperação grava `run.budget_exhausted` sem chamar o runner.

SQLite usa WAL. Backup consistente deve incluir a API de backup/checkpoint do SQLite e o diretório de
artifacts. Copiar somente `evidrun.db` enquanto WAL está ativo não é um backup válido.

Uma `OperationalError` transitória do SQLite, antes de existir `subject.invoked` pendente, libera o
attempt com `transient_storage_error` e recoloca o job na fila. Se o storage não permitir provar e
gravar essa liberação, ou se houver invocação externa pendente, o worker falha explicitamente e deixa
o lease expirar; ele não rejeita a Run nem inventa um terminal científico.

# Subject real e tracing

O primeiro adapter real usa o provider default, network `provider_only` e uma única capability
`read_text`. O modelo não recebe paths ou o hidden expected. O ledger registra provider/model/
reasoning, capability oferecida, arguments/result refs, contagem de rounds, tool calls, usage e um
digest agregado do trace. Credencial, raw reasoning e corpo livre de erro upstream não são
persistidos.

O provider atual exige `tool_choice=auto`; o runtime ainda obriga ao menos uma leitura antes de
aceitar a resposta terminal. Continuação é stateless e reenvia apenas o transcript mínimo porque o
proxy não garante `previous_response_id` persistido. Consulte o
[ADR 0016](../adr/0016-real-subject-read-tool-and-tracing.md) e o
[benchmark live](../benchmarks/live-read-agent.md).

# Limites

Bundle v3 é auditável em isolamento, porém `references_only`: não transporta todos os blobs nem
concede acesso ao ArtifactStore. Ele não é restore, replay ou bundle portátil.
