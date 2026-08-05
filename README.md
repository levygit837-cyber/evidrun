<div align="center">

# Evidrun

**Laboratório local-first e auditável para avaliar agentes de IA.**

[![CI](https://github.com/levygit837-cyber/evidrun/actions/workflows/ci.yml/badge.svg)](https://github.com/levygit837-cyber/evidrun/actions/workflows/ci.yml)
[![Python 3.14](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Node 24](https://img.shields.io/badge/Node-24-339933?logo=nodedotjs&logoColor=white)](https://nodejs.org/)
[![License: Proprietary](https://img.shields.io/badge/license-proprietary-6b7280)](LICENSE)

</div>

## Navegação rápida

[Estado](#estado-atual) · [Execução](#começar) · [Documentação](#navegação-documental) · [Licença](#licença)

O Evidrun testa como contexto, ferramentas, policies e ambientes afetam agentes de IA.

O Evidrun não trata uma resposta isolada como prova. Cada comparação registra a variável alterada,
o contexto efetivamente entregue, a trilha de eventos, os graders, os ganhos, as perdas e os limites
da conclusão.

## Estado atual

A espinha canônica atravessa o pipeline completo de ponta a ponta, exercitada por superfícies
públicas:

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
- evidence bundles v1/v2/v3/v4 com verificação de cadeia e detecção de tamper;
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

Duas lacunas afetam o uso do aplicativo instalado:

- a tela Create ainda mantém rascunho local e faz bootstrap da fixture, em vez de usar o corredor de
  autoria já disponível na API e na CLI;
- o runtime do Lab Agent já existe em `src/evidrun/lab/`, com loop limitado, catálogo fechado de
  tools, leitura escopada e drafts sujeitos a revisão humana, mas o backend ainda não oferece o
  adapter `send/stream/cancel`; por isso a página Laboratory continua em modo de integração.

Criar Workspace e Project já possui superfície pública em API e CLI, o app desktop supervisiona API e
worker separados, e o backend compila e admite uma Run explicitamente não verificada com
`execution_trust_id`. Autoria verificada por autoridade humana continua opt-in por
`EVIDRUN_AUTHORITY=1`.

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
pnpm dev
```

Electron:

```bash
pnpm desktop:dev
```

Para listar ambientes, serviços isolados, testes e builds disponíveis:

```bash
pnpm commands
```

`pnpm run help` é um alias equivalente. `pnpm help` sem `run` pertence ao próprio pnpm e mostra a
ajuda do gerenciador de pacotes.

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

Na verificação limpa de 4 de agosto de 2026 passaram 761 testes Python, 103 testes web e 40 testes
desktop. O benchmark com provider real permaneceu ignorado por ser opt-in. Ruff, Pyright, budgets
estruturais, geração de contracts, builds e validação documental também passaram.

## Navegação documental

Comece por [docs/index.md](docs/index.md). O repositório é a única fonte normativa: `docs/adr` para
decisões aceitas, `docs/contracts` para contratos, `docs/planning` para intenção temporal. Resultados
de runs permanecem no data store ou em bundles exportados.

## Licença

Código-fonte público para avaliação de portfólio. Todos os direitos reservados; consulte
[LICENSE](LICENSE).
