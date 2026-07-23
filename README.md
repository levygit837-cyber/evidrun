# Evidrun

Laboratório local-first e auditável para testar como contexto, ferramentas, policies e ambientes
afetam agentes de IA.

O Evidrun não trata uma resposta isolada como prova. Cada comparação registra a variável alterada,
o contexto efetivamente entregue, a trilha de eventos, os graders, os ganhos, as perdas e os limites
da conclusão.

## Estado atual

A primeira espinha executável está implementada com o benchmark determinístico `CRL-CTX-002`:

- Python 3.14, FastAPI, Pydantic, SQLAlchemy e SQLite/WAL;
- manifest imutável e validado;
- event ledger append-only encadeado por hash;
- context plans, snapshots e diffs;
- subject runner e grader determinísticos;
- comparação e relatório;
- evidence bundle com checksums e verificação da cadeia;
- contracts revisionados para Study, Goal, Scenario, inventário, workspace, interação, avaliação e
  checkpoints;
- compilação determinística em RunSpecs, admissão explícita e envelopes mínimos para Subject e
  evaluators;
- CLI, API, React e Electron dev shell;
- CLIProxyAPI local como provider padrão, com `deepseek-v4-flash` e `reasoning=max`;
- nenhuma API externa necessária para o benchmark de referência.

Esse benchmark comprova o funcionamento da infraestrutura. Ele não mede a capacidade de um LLM.

O fluxo canônico novo é:

```text
revisions aceitas → Study compila RunSpecs → admissão resolve capacidades → Run → event ledger
                                                      ↘ evaluations e checkpoints ancorados
```

O runtime executável continua propositalmente menor que os contracts: hoje ele suporta o runner
determinístico, `single_turn` e workspace `in_process`. Tools, skills, nested agents, protocolo em
grafo e restore/replay de checkpoints são representáveis ou planejáveis, mas ainda não são
executáveis. Consulte [Study, revisions e Run canônica v1](docs/contracts/study-run-v1.md) para as
fronteiras completas.

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

Comece por [docs/index.md](docs/index.md). Decisões aceitas ficam em `docs/adr`, contratos em
`docs/contracts` e resultados de runs permanecem no data store ou em bundles exportados.

O Obsidian é uma área de pesquisa e incubação; o repositório é a fonte normativa.
