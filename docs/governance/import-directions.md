---
id: governance-import-directions
type: governance
title: Gate de direção de imports
status: implemented
authority: normative
volatility: current
owner: core
created_at: 2026-07-26
updated_at: 2026-07-26
applies_to: repository
sources:
  - docs/architecture/codebase-layout.md
  - docs/adr/0003-modular-monolith.md
supersedes: []
superseded_by: null
implementation_refs:
  - scripts/check_import_directions.py
  - scripts/import_directions_typescript.py
  - import-directions.toml
  - .github/workflows/ci.yml
verification_refs:
  - tests/unit/test_import_directions.py
---

# Gate de direção de imports

`scripts/check_import_directions.py` constrói arestas determinísticas somente a partir de arquivos
versionados retornados por `git ls-files`. O comando padrão produz diagnóstico textual e falha com
exit code `1` quando encontra violação:

```bash
uv run python scripts/check_import_directions.py
uv run python scripts/check_import_directions.py --format json
```

O JSON tem `schema_version`, quantidade de arquivos lidos e violações ordenadas por origem, destino,
regra e cadeia curta. O job Python da CI executa o gate depois de Ruff e antes dos gates e suítes
mais longos.

## Regras bloqueantes

- `PY-CONTRACTS-EXTERNALS`: `contracts` não importa FastAPI, SQLAlchemy, OpenAI, Electron ou React.
- `PY-CONTRACTS-LAYERS`: `contracts` não importa `infrastructure` nem `runs`.
- `PY-SHARED-UPWARD`: `shared` só importa o próprio `shared` dentro de `evidrun`.
- `PY-INFRASTRUCTURE-RUNS`: `infrastructure` não importa `runs`.
- `TS-RENDERER-NATIVE`: o Renderer não importa `electron`, `node:*`, bindings nativos nem Main ou
  preload por path relativo.
- `TS-MAIN-DOMAIN`: Electron Main não importa módulos de domínio Python nem features do Renderer.

Imports Python são lidos com `ast`, incluindo relativos, aliases e cadeias de re-exports estáticos de
`__init__.py`. Imports TypeScript/TSX/MJS/MTS/CTS são statements estáticos `import`/`export from`;
`require("literal")` em import assignment ou declaração também é coberto, e paths relativos são
resolvidos contra os paths versionados. Comentários, strings, templates e texto JSX não viram arestas.

## Exceções

O baseline normal é zero. `import-directions.toml` contém uma lista vazia e não pode esconder
violações novas. Uma exceção futura precisa corresponder exatamente a `source`, `destination` e
`rule`, além de declarar `reason`, `owner` e `expires`. Exceção vencida, duplicada, incompleta ou que
não corresponda mais a uma violação faz o comando falhar com erro de configuração. Exceções ativas
aparecem na saída textual.

## Limites do que o gate prova

O scanner prova a direção de imports estáticos nos arquivos versionados suportados. Ele não executa
módulos e não prova ausência de imports montados dinamicamente por `importlib`, `__import__`,
`require(variable)` ou `import(variable)`. Também não decide semanticamente se lógica de domínio foi
copiada para Electron Main sem um import proibido; esse caso continua exigindo revisão de código.

Arquivos não rastreados são ignorados por desenho. Antes de usar o comando como evidência local de
uma inclusão ou remoção, atualize o índice Git para refletir o diff que será enviado à CI.
