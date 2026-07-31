---
id: governance-dependency-report
type: governance
title: Relatório de dependências e ciclos
status: implemented
authority: normative
volatility: current
owner: core
created_at: 2026-07-31
updated_at: 2026-07-31
applies_to: repository
sources:
  - docs/architecture/codebase-layout.md
  - docs/governance/import-directions.md
supersedes: []
superseded_by: null
implementation_refs:
  - scripts/check_dependency_report.py
  - scripts/dependency_report
  - scripts/import_graph.py
  - .github/workflows/ci.yml
verification_refs:
  - tests/unit/test_dependency_report.py
---

# Relatório de dependências e ciclos

`scripts/check_dependency_report.py` informa a forma do grafo de dependências. Ele nunca bloqueia um
merge: nesta primeira fase o objetivo é medir e observar falsos positivos antes de qualquer threshold
virar regra.

```bash
uv run python scripts/check_dependency_report.py
uv run python scripts/check_dependency_report.py --format json
uv run python scripts/check_dependency_report.py --base-ref origin/main --json-out report.json
```

O relatório lê o mesmo grafo normalizado do
[gate de direção de imports](import-directions.md). `scripts/import_graph.py` é a fonte única das
arestas: o gate aplica política bloqueante sobre ele e este relatório mede estrutura sobre o mesmo
grafo. Não existe segundo grafo nem segunda definição de aresta.

## Três estados de dependência

Cada aresta interna cai em exatamente um estado, e os três somam `internal_edge_count`:

- **permitida**: nenhuma regra a proíbe e nenhuma heurística a marca;
- **proibida**: `scripts/check_import_directions.py` a nomeia. O relatório não tem opinião própria
  sobre o que é proibido; ele repete o veredito do gate;
- **apenas suspeita**: nenhuma regra a proíbe, mas ambos os extremos estão em um ciclo, ou a aresta
  corre contra a direção conceitual documentada em
  [Layout da codebase](../architecture/codebase-layout.md).

Proibida vence suspeita: o veredito do gate não é suavizado em dica.

## Eixos medidos

- ciclos entre módulos e entre fatias, por componentes fortemente conexos;
- fan-in e fan-out por módulo;
- imports entre fatias, com marca de quem corre contra a direção conceitual;
- hubs de re-export, medidos pela superfície encaminhada por um `__init__` de pacote;
- dependências externas por fatia, separando runtime Python de Node;
- arestas novas contra o merge-base.

## Thresholds candidatos

`FAN_IN_CANDIDATE`, `FAN_OUT_CANDIDATE` e `REEXPORT_HUB_CANDIDATE` decidem apenas quais linhas são
impressas. Eles não afetam exit code e não são política aceita. Promover qualquer um a bloqueante é
decisão separada, tomada depois de observar este baseline.

## Exit codes

- `0`: o relatório foi produzido, qualquer que seja o achado;
- `2`: o relatório não pôde ser produzido, por fonte ilegível ou repositório inutilizável.

Não existe exit code `1`. Reservá-lo convidaria uma mudança futura a tornar um achado bloqueante por
acidente.

## Tratamento de imports por categoria

**Imports de tipo.** `from x import y` sob `if TYPE_CHECKING:` e `import type { Y } from 'x'` são
arestas normais. A dependência existe no código-fonte, é resolvida por type checker e restringe
refactor, então esconder essa aresta tornaria o grafo otimista. Hoje nenhum módulo de
`src/evidrun/` usa `TYPE_CHECKING`; a decisão vale para quando passar a usar.

**Imports lazy e dinâmicos.** `importlib.import_module`, `__import__`, `require(variable)` e
`import(variable)` não produzem aresta. O scanner lê AST e statements estáticos; um alvo montado em
runtime não é decidível sem executar o módulo. O relatório não afirma ausência dessas arestas, e
revisão de código continua responsável por elas.

**Código gerado.** Arquivos gerados versionados, como `apps/web/src/generated/contracts.ts`, são nós
do grafo: quem os importa tem dependência real. Eles não são excluídos da medição, mas um achado
sobre um arquivo gerado é endereçado no gerador, não no arquivo.

**Assets.** `./styles/index.css` e outros especificadores relativos que não resolvem para um nó
versionado aparecem como `dependency.unresolved_specifier`. São entradas de bundler, não pacotes; o
relatório os nomeia em vez de contá-los como dependência externa, para que a lacuna fique visível.

## Limites do que o relatório prova

O relatório prova a forma do grafo estático de arquivos versionados nos roots medidos. Ele não prova
que um módulo é profundo, que uma costura está no lugar certo, nem que o acoplamento observado é
errado: fan-in alto em `evidrun.contracts.base` é esperado para um módulo de vocabulário. Um achado
é convite a olhar, não veredito.

`--base-ref` compara contra o merge-base real. Quando o repositório não consegue resolvê-lo, a seção
de drift se declara não computada em vez de reportar diff vazio, porque "nenhuma aresta nova" e "não
sei" não são a mesma afirmação.

Arquivos não rastreados são ignorados por desenho, como no gate de direção. Antes de usar o relatório
como evidência local, atualize o índice Git.
