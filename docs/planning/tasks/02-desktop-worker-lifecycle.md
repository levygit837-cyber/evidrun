---
id: planning-task-desktop-worker-lifecycle
type: implementation-task
title: WS-02 Lifecycle do worker no desktop
status: verified
authority: planning
volatility: snapshot
owner: desktop
created_at: 2026-07-23
updated_at: 2026-07-28
observed_at: 2026-07-28
review_due: 2026-08-07
applies_to: desktop-runtime
sources:
  - docs/planning/mvp-implementation-roadmap.md
  - docs/architecture/desktop-runtime.md
  - docs/adr/0002-control-plane-and-execution-plane.md
  - docs/adr/0004-python-core-typescript-ui-and-electron.md
  - docs/adr/0014-durable-runtime-kernel.md
supersedes: []
superseded_by: null
implementation_refs:
  - apps/desktop/src/main/executor-handshake.ts
  - apps/desktop/src/main/executor-lifecycle.ts
  - apps/desktop/src/main/index.ts
  - apps/desktop/src/preload/index.cts
  - apps/desktop/src/shared/desktop-contract.ts
  - src/evidrun/entrypoints/worker/app.py
verification_refs:
  - apps/desktop/src/main/executor-handshake.test.ts
  - apps/desktop/src/main/executor-lifecycle.test.ts
  - tests/unit/test_worker_entrypoint.py
  - scripts/smoke_desktop_supervision.mjs
---

# WS-02 — Lifecycle do worker no desktop

`workstream_state: done_on_main`

## Entrega verificada em `main`

O PR #91 foi integrado no commit `ced8a1d` em 2026-07-28 e adotou a opcao A: o Electron Main
supervisiona um executor separado da API. O contrato desktop distingue os estados do backend e do
executor; Main, preload e renderer propagam esse estado sem importar capacidades nativas no
renderer.

O ciclo inclui handshake autenticado em stdin, readiness, restart, shutdown ordenado e tratamento
de processo morto. O smoke `scripts/smoke_desktop_supervision.mjs` cobre o corredor do produto, e os
testes focais cobrem handshake, lifecycle e entrypoint Python. O CI do PR passou nos jobs Python e
Node; o bloqueio B2 do roadmap esta resolvido.

O estado e a acao de restart chegam ao `BackendRuntimeProvider`; o tratamento visual completo desse
estado continua pertencendo ao WS-51. Portanto, a entrega comprova supervisao e contrato consumivel
no renderer, nao uma interface final de operacao.

O texto abaixo preserva o brief e o snapshot que orientaram a implementacao. Ele e historico; nao
deve ser lido como trabalho ainda pendente.

## Resultado pratico

Uma Run enfileirada pela UI do aplicativo local atinge estado terminal sem que ninguem abra um
terminal e rode `evidrun-worker`. O aplicativo passa a supervisionar o Execution Plane, nao apenas o
Control Plane: quando o app esta aberto e o backend esta `ready`, existe exatamente um executor
durável ativo sobre aquele banco, e quando esse executor morre isso aparece na interface como estado,
nao como Run parada para sempre em `queued`.

Isto resolve o bloqueio B2 do roadmap. Nao e capability nova: `DurableRunWorker`, fila, lease e
fencing já existem e já foram exercitados por CLI. O que falta e lifecycle.

## Snapshot inicial

Fatos confirmados em `main` no momento da escrita. Redescubra cada um antes de editar, porque a
correcao desta task depende deles e nao de sua descricao aqui.

- `apps/desktop/src/main/backend-lifecycle.ts` faz `spawn` de `uv run evidrun serve
  --desktop-handshake` em dev e do binario `evidrun-backend` empacotado em `resources/backend`,
  escreve `{token, data_dir, parent_instance_id}` em stdin, le uma linha de readiness em stdout com
  timeout de 15s, e emite estados via `emitState`.
- `BackendState.status` em `apps/desktop/src/shared/desktop-contract.ts` tem exatamente quatro
  valores: `starting`, `ready`, `failed`, `stopped`. `apps/web/src/types.ts` repete o mesmo union e
  `apps/web/src/app/BackendRuntimeProvider.tsx` o consome; `child.once("exit")` distingue `stopped`
  de `failed` pela flag `stopping`.
- `serve` em `src/evidrun/entrypoints/cli/app.py` faz o handshake, abre um socket loopback em porta
  efemera, imprime a readiness message e chama `server.run(sockets=[listener])`. Ele sobe uvicorn e
  retorna. Nenhum path do produto inicia executor de Run.
- `src/evidrun/entrypoints/worker/app.py` expoe o console script `evidrun-worker` (declarado em
  `pyproject.toml`), com `--data-dir`, `--worker-id`, `--once`, `--poll-interval`, `--lease-seconds`,
  `--heartbeat-seconds`. Sem `--once` ele instala handlers de `SIGINT`/`SIGTERM` que setam um
  `asyncio.Event` e chama `DurableRunWorker.run_forever(stop)`.
- `src/evidrun/runs/worker.py` implementa `process_once` (claim, heartbeat concorrente, execucao do
  attempt) e `run_forever`, que faz poll com `asyncio.wait_for(stop.wait(), timeout=poll_interval)`.
  O construtor rejeita `heartbeat_seconds >= lease_seconds / 2`.
- `Repository.claim_next_job` usa `BEGIN IMMEDIATE`, expira leases vencidos, reserva o job FIFO e
  incrementa `lease_generation`. `heartbeat_lease`, release, reject e complete passam por
  `_require_active_lease`, que levanta `LeaseLost` quando geracao, `worker_id`, attempt ou expiracao
  divergem.
- `scripts/smoke_desktop_handshake.mjs` cobre handshake, rejeicao 401 sem token e health autenticado.
  O script npm `test:handshake` existe em `package.json`.
- `.github/workflows/ci.yml` roda `uv sync`, `ruff`, `pyright`, `pytest`, `validate_docs`,
  `generate_schemas --check`, `git diff docs/_generated`, e no job node: `install`,
  `generate_contract_types --check`, `typecheck:web`, `typecheck:desktop`, `test:web`, `test:desktop`,
  `build`. **`test:handshake` nao roda no CI.** O script `test` agregado tambem nao o inclui.

### Fatos a redescobrir antes de decidir

- se o binario empacotado `evidrun-backend` expoe apenas `serve` ou o grupo completo de comandos;
  isso determina se o desktop empacotado consegue spawnar um segundo processo worker;
- como `apps/desktop/src/main/index.ts` sequencia `backend.start()`, `before-quit` e
  `window-all-closed`, porque o shutdown do worker precisa entrar na mesma ordem;
- se existe teste em `apps/desktop/src/main/backend-lifecycle.test.ts` que assume o conjunto atual de
  estados (mudar o union sem atualizar o teste e o typecheck do renderer quebra `pnpm test:desktop`);
- qual rota o wizard usa para enfileirar (`enqueue_run` em `src/evidrun/entrypoints/api/app.py`), para
  que o criterio de saida seja exercitado pelo caminho real e nao por um atalho.

## Decisao de projeto a tomar

Duas formas de fazer o app processar Runs. Escolha uma, registre a escolha no PR e implemente sem
manter as duas.

**A. Electron Main supervisiona um processo `evidrun-worker` separado.** Um segundo
`spawn`/lifecycle irmao de `BackendLifecycle`, com o mesmo `data_dir` do handshake.

- crash isolation: execucao de Run nao derruba a API. Um adapter que estoura memoria ou trava mata o
  worker; a UI continua respondendo e mostrando o ledger;
- fencing de lease: cada processo tem `worker_id` derivado de hostname/pid, ja distinto por
  construcao; um worker zumbi perde a corrida em `_require_active_lease`;
- observabilidade: o estado do worker e um estado de processo real, do mesmo tipo que o backend ja
  publica. Reinicio e uma acao explicita;
- shutdown: exige `SIGTERM` ordenado e espera do exit antes do quit, senao o lease fica pendurado ate
  expirar;
- custo: mais um processo, mais um caminho de packaging, e depende do binario empacotado aceitar o
  entrypoint do worker.

**B. O loop roda dentro do processo de `serve`.** `serve` sobe uvicorn e uma task asyncio com
`run_forever`.

- um processo, packaging inalterado, shutdown acoplado ao do servidor;
- perde crash isolation: uma falha nao tratada no loop degrada ou derruba a API junto;
- observabilidade fica pior: o estado do executor deixa de ser visivel de fora e viraria mais um
  campo de health, nao um lifecycle;
- risco de fronteira: `serve` e Control Plane. O ADR 0002 separa Control e Execution Plane e o ADR
  0014 e explicito de que API e CLI apenas enfileiram, enquanto `evidrun-worker` e o executor
  durável. Fundir os dois num processo enfraquece essa separacao no ponto exato em que ela e barata
  de manter.

**Recomendacao: A.** O motivo decisivo nao e elegancia, e que a evidencia nao pode depender da
sobrevivencia do executor. Uma Run que morre no meio precisa deixar a API viva para que o ledger e o
estado terminal continuem consultaveis, e o modelo de attempt/lease do ADR 0014 foi desenhado
assumindo executor que pode morrer e ser substituido. B tambem transformaria um crash de adapter em
indisponibilidade de leitura de evidencia, que e o oposto do produto.

Se durante a descoberta o binario empacotado nao expuser o worker, a resposta correta e corrigir o
packaging (adicionar o entrypoint) ou spawnar `evidrun-backend worker`, nao migrar para B por
conveniencia. Se essa correcao for impossivel dentro do escopo, pare e escale com o achado; nao
entregue B silenciosamente sob o nome de A.

## Escopo

- lifecycle supervisionado do executor de Run no Electron Main, irmao do lifecycle do backend,
  compartilhando o `data_dir` que o handshake ja resolve;
- estado do worker observavel no contrato desktop e no renderer, com a mesma semantica que o backend
  ja tem: crash e estado, nao silencio;
- reinicio do worker pela UI, sem exigir restart do backend nem do app;
- shutdown limpo em `before-quit`, com espera pelo exit para nao deixar lease pendurado;
- garantia de executor unico por banco enquanto o app roda, e comportamento definido quando um
  `evidrun-worker` externo ja esta ativo sobre o mesmo `data_dir`;
- `test:handshake` no CI;
- extensao do smoke para cobrir Run enfileirada -> terminal.

## Nao objetivos

- packaging assinado, notarizacao e distribuicao publica (`osxSign`/`osxNotarize` em
  `forge.config.cjs` continuam gated por env var e fora desta task);
- multiplos workers em escala, pool, autoscaling ou distribuicao entre maquinas;
- qualquer mudanca em contrato de dominio, admissao, envelope ou ledger;
- capability nova de execucao: nenhum adapter novo, nenhum runner novo;
- retry automatico de Run que falhou por motivo de dominio; expiracao de lease continua criando
  attempt, nunca Run nova (ADR 0014).

## Ownership de paths

Pode editar:

- `apps/desktop/src/main/**` (lifecycle, index, testes de main);
- `apps/desktop/src/preload/**` e `apps/desktop/src/shared/desktop-contract.ts`;
- `apps/web/src/types.ts`, `apps/web/src/env.d.ts` e `apps/web/src/app/BackendRuntimeProvider.tsx`
  somente no que for necessario para refletir o novo estado observavel;
- o comando `serve` em `src/evidrun/entrypoints/cli/app.py`, e `src/evidrun/entrypoints/worker/app.py`
  apenas se a supervisao exigir uma flag ou sinal novo de lifecycle;
- `scripts/smoke_desktop_handshake.mjs` (ou um smoke irmao), `package.json` scripts,
  `.github/workflows/ci.yml`, `apps/desktop/forge.config.cjs` e
  `apps/desktop/resources/backend/README.txt` quando o packaging do entrypoint mudar.

Nao pode editar:

- `src/evidrun/contracts/**`, `src/evidrun/runs/coordinator.py`, `src/evidrun/runs/adapters.py`;
- `src/evidrun/infrastructure/database/repository.py` e `alembic/versions/**`: fila, lease, fencing e
  ledger sao pre-existentes e permanecem intactos. Se a supervisao parecer exigir mudanca de
  `claim_next_job` ou de `_require_active_lease`, o desenho da supervisao esta errado;
- `src/evidrun/runs/worker.py` na sua semantica de claim/heartbeat/terminal;
- ADRs e docs normativos. Esta task nao cria ADR. Se ela concluir que a separacao Control/Execution
  Plane precisa mudar, pare e escale.

## Invariantes normativas

- `AGENTS.md`: Electron Main gerencia lifecycle e capacidades desktop e nao implementa dominio.
  Supervisionar processo, traduzir exit code em estado e reiniciar e lifecycle. Decidir se uma Run
  pode executar, escrever evento, interpretar payload de ledger ou reenfileirar job nao e.
- `AGENTS.md`: Renderer nunca importa `electron`, `node:*` ou bindings nativos. O estado do worker
  chega ao renderer por `contextBridge`/IPC ja existente, nunca por acesso direto a processo.
- `AGENTS.md`: dominio Python nao importa Electron. O worker nao ganha conhecimento de que foi
  iniciado por um app.
- ADR 0002 e ADR 0014: API e CLI enfileiram; o executor durável e separado. Nenhum caminho novo
  executa Run dentro de um request HTTP.
- ADR 0014: fencing e por `lease_generation` validado na mesma transacao da escrita. Reinicio de
  worker nunca reaproveita `worker_id` de um processo cujo exit nao foi observado.
- ADR 0014: expiracao de lease cria attempt novo sobre a mesma Run. Reinicio pelo app nao pode
  produzir Run nova nem apagar attempt anterior.
- `docs/architecture/desktop-runtime.md`: token, porta e instance ID ficam apenas em memoria. O
  lifecycle do worker nao grava token, path de banco ou credencial em log, arquivo ou argv visivel.
- Crash e estado observavel, como ja vale para o backend. Worker morto com fila nao vazia nunca
  aparece como app saudavel.

## Loop de execucao

```text
TASK_ID=WS-02
BASE_REQUIRES=none
MAX_REPAIR_LOOPS=8
ALLOW_DOMAIN_EDITS=0
ALLOW_LEDGER_EDITS=0
ALLOW_IN_PROCESS_EXECUTOR=0
```

```text
DISCOVER lifecycle atual, contrato de estados, entrypoint empacotado
-> DECIDE processo separado vs in-process, registre a escolha
-> REPRODUCE B2: app aberto, Run enfileirada, fila nao drena
-> IMPLEMENT supervisao do worker no Main
-> IMPLEMENT estado observavel ponta a ponta (main -> preload -> renderer)
-> IMPLEMENT restart e shutdown ordenado
-> ATTACK crash, kill -9, dois workers, quit durante Run
-> REPAIR
-> INTEGRATE smoke: enqueue -> terminal
-> WIRE CI
-> FOCAL GATES
```

### Condicionais

- Se o binario empacotado nao expuser o worker, corrija o packaging; nao migre para executor
  in-process para contornar.
- Se o estado do worker exigir consultar a fila, exponha isso pela API existente do backend; o Main
  nao abre o SQLite.
- Se dois executores conseguirem progredir sobre o mesmo banco sem `LeaseLost`, trate como P0 e prove
  onde o fencing nao foi exercido antes de mudar qualquer outra coisa.
- Se `run_forever` nao encerrar dentro do timeout de shutdown, escalone para `SIGKILL` apenas depois
  de um `SIGTERM` esperado, e documente no PR que a Run interrompida sera retomada por expiracao de
  lease, nao por Run nova.
- Se mudar o union de `BackendState` (ou introduzir um estado de worker paralelo), atualize
  `apps/web/src/types.ts`, o provider do renderer e os testes de main no mesmo commit; drift ali
  quebra `typecheck:desktop`.
- Se o smoke estendido ficar dependente de rede ou de provider externo, ele nao serve para o CI;
  reduza a Run exercitada ao corredor offline e deterministico.

## Ataques obrigatorios

- worker morto por `SIGKILL` com Run em execucao: o app mostra estado de falha e a Run e retomada em
  novo attempt depois da expiracao do lease, sem Run nova e sem evento terminal inventado;
- backend morto e worker vivo, e o inverso: os dois estados sao distinguiveis na UI;
- `evidrun-worker` externo ja rodando sobre o mesmo `data_dir` quando o app inicia: nenhuma Run e
  executada duas vezes; o segundo executor perde por `LeaseLost` ou nao e iniciado;
- quit do app durante Run ativa: shutdown nao trava indefinidamente e nao deixa processo orfao;
- restart do worker em sequencia rapida: nao acumula processos, nao vaza handle de stdio;
- readiness que nunca chega: o timeout produz `failed` com mensagem, nao promessa de `ready`.

## Testes focais e gates

Focais (nao rode a suite completa a cada loop):

- `pnpm test:desktop` para o lifecycle e o mapeamento de exit code em estado;
- `pnpm typecheck:desktop` e `pnpm typecheck:web` para o contrato de estados;
- `pnpm test:handshake` estendido, com a assercao nova de que uma Run enfileirada atinge terminal;
- `uv run pytest` restrito aos testes do entrypoint do worker, se a flag de lifecycle mudar.

Gate final: a suite obrigatoria completa do `AGENTS.md`, mais `pnpm test:handshake`, no commit final.

CI: adicione `test:handshake` ao job node do `.github/workflows/ci.yml`, depois de `pnpm build`, com o
setup Python que o script exige (ele invoca `uv run evidrun`). Confirme que ele falha quando a
supervisao do worker e removida; um gate que passa com o bug presente nao e gate.

## Condicoes de parada e escalacao

Pare e escale, sem contornar:

- se a decisao de projeto exigir alterar a fronteira Control/Execution Plane (ADR sucessor, decisao
  humana);
- se garantir executor unico exigir schema, tabela de advisory lock ou mudanca em `Repository`;
- se o unico caminho para o app empacotado processar Runs for empacotar um segundo binario e isso
  colidir com packaging/assinatura, que sao non-goal aqui;
- se um ataque revelar duplicidade real de execucao: isso e P0 de dominio e nao se resolve no
  lifecycle desktop.

## Criterio de saida

Com o aplicativo aberto e nenhum terminal envolvido: enfileirar uma Run pela UI resulta em estado
terminal no ledger e na tela. Matar o processo worker torna isso visivel como estado de falha na
interface, e reiniciar pelo app retoma o processamento sem criar Run nova. `pnpm test:handshake` roda
no CI e cobre enqueue ate terminal.

## Handoff

- base SHA, head SHA, branch;
- decisao registrada entre processo separado e executor in-process, com o motivo;
- arquivos alterados sob ownership, e nenhum fora dele;
- evidencia do criterio de saida: `run:` do exercicio ponta a ponta pelo app e a sequencia de eventos
  observada;
- resultado dos ataques, incluindo o de dois executores;
- diff do CI e prova de que o gate novo falha sem a supervisao;
- estados de UI novos ou renomeados, para o brief de frontend consumir;
- findings P0/P1 e decisoes humanas abertas.
