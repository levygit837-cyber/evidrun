# Evidrun

Laboratório local-first e auditável para testar como contexto, ferramentas, policies e ambientes
afetam agentes de IA.

O Evidrun não trata uma resposta isolada como prova. Cada comparação registra a variável alterada,
o contexto efetivamente entregue, a trilha de eventos, os graders, os ganhos, as perdas e os limites
da conclusão.

## Estado atual

A espinha canonica atravessa o pipeline completo de ponta a ponta, exercitada por superficies
publicas:

```text
contract register → authority accept → study compile → run admit → run enqueue
  → worker → run.completed → bundle export-run → bundle verify
```

O que existe hoje:

- Python 3.14, FastAPI, Pydantic, SQLAlchemy e SQLite/WAL;
- contracts revisionados para Study, Goal, Scenario, inventário, workspace, interação, avaliação e
  checkpoints, com digests imutáveis;
- compilação determinística em RunSpecs, admissão explícita e envelopes mínimos para Subject e
  evaluators;
- event ledger append-only encadeado por hash, com gates de fase;
- fila durável com job, attempt, lease, heartbeat, fencing e retry;
- Subject determinístico e Subject com modelo real, este último com tool de leitura confinada ao
  `SubjectEnvelope`;
- autoridade humana verificável opt-in, com autenticador local, verifier e revogação;
- evidence bundles v1/v2/v3 com verificação de cadeia e detecção de tamper;
- CLI, API, React e shell Electron multipágina;
- CLIProxyAPI local como provider padrão, com `deepseek-v4-flash` e `reasoning=max`;
- nenhuma API externa necessária para o benchmark determinístico `CRL-CTX-002`.

O benchmark comprova o funcionamento da infraestrutura. Ele não mede a capacidade de um LLM.

### Limites atuais

O runtime executável continua propositalmente menor que os contracts. Hoje ele suporta o runner
determinístico ou o Subject real, `single_turn`, workspace `in_process` e um estágio determinístico de
avaliação. Tools genéricas, skills, nested agents, protocolo em grafo, checkpoints automáticos,
Progress Artifacts, bounded exploration e restore/replay são representáveis, mas a admissão os
rejeita explicitamente em vez de fingir suportá-los.

Três lacunas afetam o uso do aplicativo instalado:

- não existe superfície pública para criar Workspace e Project; um banco novo depende de
  `evidrun demo`;
- o app desktop inicia a API, mas não o worker, então Runs enfileiradas pela UI não são processadas;
- autoria verificada é opt-in por `EVIDRUN_AUTHORITY=1`; no default o único corredor de aceitação é a
  fixture legada não humana.

Consulte [Study, revisions e Run canônica v1](docs/contracts/study-run-v1.md) para as fronteiras
completas e [o mapa de capabilities](docs/planning/mvp-capability-map.md) para o estado por
capability.

## Começar

```bash
uv sync --extra dev
pnpm install
uv run evidrun init
uv run evidrun doctor
uv run evidrun demo
uv run evidrun provider status
uv run evidrun provider doctor
```

Backend e browser:

```bash
uv run evidrun serve
pnpm dev:web
```

Electron:

```bash
pnpm desktop:dev
```

Testes e builds:

```bash
uv run pytest
uv run ruff check .
uv run pyright
pnpm typecheck:web
pnpm typecheck:desktop
pnpm test
pnpm build
```

## Navegação documental

Comece por [docs/index.md](docs/index.md). O repositório é a única fonte normativa: `docs/adr` para
decisões aceitas, `docs/contracts` para contratos, `docs/planning` para intenção temporal. Resultados
de runs permanecem no data store ou em bundles exportados.
