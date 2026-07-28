---
id: planning-task-workspace-project-surface
type: implementation-task
title: WS-01 Superfície pública de Workspace e Project
status: verified
authority: planning
volatility: snapshot
owner: product-engineering
created_at: 2026-07-23
updated_at: 2026-07-27
observed_at: 2026-07-27
review_due: 2026-08-10
applies_to: workspace-project-surface
sources:
  - docs/planning/mvp-implementation-roadmap.md
  - docs/adr/0020-workspace-project-run-environment-boundaries.md
  - docs/contracts/workspace-project-surface-v1.md
  - docs/contracts/triage-error.md
  - docs/architecture/agents-and-authority.md
  - docs/governance/documentation.md
  - CONTEXT.md
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun/contracts/scope.py
  - src/evidrun/infrastructure/database/catalog.py
  - src/evidrun/infrastructure/database/read_model/queries.py
  - src/evidrun/entrypoints/api/routers/platform.py
  - src/evidrun/entrypoints/cli/commands/scopes.py
  - alembic/versions/0005_workspace_name_identity.py
  - alembic/versions/0006_project_name_identity.py
verification_refs:
  - tests/unit/test_scope_contracts.py
  - tests/integration/test_scope_surfaces.py
  - tests/integration/test_scope_migration.py
---

# WS-01 — Superfície pública de Workspace e Project

`workstream_state: delivered`

## Resultado prático

Em banco vazio, um usuário cria e lista Workspace e Project pela API ou CLI, sem fixture, script
interno ou edição de SQLite. Os mesmos nomes, payloads e erros valem nas duas superfícies. Em seguida,
o usuário registra uma contract revision no Project criado.

O corte implementa o
[contrato v1 da superfície](../../contracts/workspace-project-surface-v1.md). Ele não cria Run
Environment, sandbox, Lab Agent por Project, policy executável, acceptance ou Run.

## Entrega verificada

WS-01A e WS-01B foram fechados no mesmo branch em dois revisions Alembic lineares:
`0005_workspace_name_identity` e `0006_project_name_identity`. O corredor público parte de banco
vazio, cria Workspace e Project e registra a primeira contract revision por API ou CLI. As provas
cobrem normalização, duplicidade simples e concorrente, homônimos cross-Workspace, storage
indisponível, payload extra, leitura direta e migration vazia/legada/ambígua/downgrade.

O delta real antes de generated docs foi 1.377 linhas adicionadas e 14 removidas: 700 de testes, 202
de migration/schema compatível e 475 do contrato/store/read model/API/CLI. A faixa inicial foi
ultrapassada porque a matriz fail-closed e o caminho `Database.create_all()` para bancos locais
legados exigiram cobertura própria; a reavaliação não encontrou regra duplicada nas bordas nem
expansão para frontend, authority, Lab Agent ou Run Environment.

## Decisões já fechadas

- Workspace é a fronteira durável do Control Plane. Criá-lo não provisiona execução.
- Project é uma linha de investigação dentro de um Workspace, não pasta ou instância de agente.
- Workspace name é único no datastore; Project name é único no Workspace pai.
- Nomes colidem por NFKC + trim + colapso de whitespace + casefold. A capitalização de exibição é
  preservada; `name_key` não é público.
- Duplicata falha com conflito; não existe reaproveitamento silencioso ou `get-or-create`.
- A constraint no storage é a garantia contra race. A implementação inclui migration e backfill;
  colisão legada aborta sem renomear dados.
- Criação de escopo usa `ScopeError`, separado das seis fases de `TriageError`.
- Listagens de Workspace/Project usam read model direto, não uma fatia de `latest_dashboard()`.
- A API e a CLI são duas projeções do mesmo domínio, não duas semânticas.

Não há decisão de produto bloqueante para iniciar. Rename, archive/delete, idempotency key, sync,
ACL, metadata de propósito e policy de Run Environment permanecem deliberadamente fora do v1.

## Snapshot inicial histórico

Verificado em `main` no commit `b591f4c` em 2026-07-27. Redescubra antes de implementar:

- `CatalogStore.create_workspace` e `create_project` gravam rows diretamente, sem validação,
  normalização, verificação amigável de pai ou tradução de erro.
- `WorkspaceRow` e `ProjectRow` possuem `name`, mas não `name_key` nem constraints de unicidade.
- `ProjectRow.workspace_id` já é foreign key obrigatória. As migrations versionadas chegam a
  `0004_runtime_kernel`; escolha o próximo revision id livre depois de rebase, sem assumir que será
  `0005`.
- `GET /api/v1/workspaces` e `GET /api/v1/projects` existem, mas materializam o dashboard inteiro e
  extraem duas chaves. Não há `POST` correspondente.
- A CLI não possui sub-app `workspace` nem `project`.
- As projeções atuais já definem o shape compatível: Workspace expõe `id`, `name`, `created_at`;
  Project acrescenta `workspace_id`.
- `apps/web/src/types.ts` ainda omite `created_at` e `workspace_id` em parte de `DashboardData`; isso
  é gap de contrato para WS-41, não motivo para criar um segundo shape neste workstream.
- O erro de registrar contract em Project inexistente **já está corrigido** em `main`:
  `register.project_not_found` é tipado e seguro. WS-01 não o reimplementa; usa-o no corredor final.
- `bootstrap_demo` faz reaproveitamento por nome como conveniência de fixture. Isso não é contrato de
  produto e não deve contaminar a superfície nova.
- `ChatSessionRow` já guarda Workspace e scope genérico. Tipar Project/Focus pertence a WS-04; criar
  Project não cria sessão automaticamente.

## Seam de comportamento

O seam de aceitação mais alto é um banco temporário real acessado somente pelas superfícies públicas:

```text
fresh database
  -> create/list Workspace
  -> create/list Project no Workspace
  -> register contract revision no Project
  -> mesma observação pela API e CLI
```

Esse seam foi aceito junto com o plano do WS-01. Testes menores existem apenas para cobrir a função
pura de normalização, race/constraint e branches de migration que o corredor feliz não alcança. Não
crie outro seam de service somente para testar detalhes internos.

## Fatias de implementação

### WS-01A — Workspace público e identidade de nomes

Fatias todas as camadas para Workspace:

- contrato executável de nome e `ScopeError`, sem importar FastAPI ou SQLAlchemy;
- expansão/backfill/constraint de `Workspace.name_key`, com prova em banco vazio e legado;
- criação e leitura direta no agregado de catálogo/read model;
- `POST`/`GET` de Workspace e CLI `create`/`list` com o mesmo documento;
- colisão simples, Unicode/whitespace e concorrente traduzida para o mesmo código estável.

Entrega demonstrável: um banco vazio ganha seu primeiro Workspace pelas duas superfícies; repetir um
nome equivalente produz conflito tipado.

### WS-01B — Project público e corredor de autoria

Bloqueada por WS-01A porque reutiliza normalização, erro e convenções de superfície:

- expansão/backfill/constraint de `Project.name_key` escopada por `workspace_id`;
- criação com pai validado e leitura direta, inclusive filtro opcional por Workspace;
- `POST`/`GET` de Project e CLI `create`/`list` com o mesmo documento;
- mesmo nome permitido em Workspaces diferentes e conflito dentro do mesmo Workspace;
- corredor final registra uma contract revision no Project recém-criado e observa
  `register.project_not_found` para pai inexistente sem SQL cru.

Entrega demonstrável: um usuário parte de banco vazio e chega a uma revision registrada sem fixture.

As duas fatias cabem em janelas de contexto independentes, mantêm CI verde e são publicadas como
tickets separados. Não existe ticket horizontal de “fazer todos os models” ou “fazer todos os
entrypoints”.

## Estimativa de mudança

Estimativa para implementação e testes, excluindo generated docs:

| Fatia | Linhas novas | Linhas removidas | Principal fonte de volume |
| --- | ---: | ---: | --- |
| WS-01A | 340–500 | 5–30 | migration, contrato/erros, API+CLI e testes de Workspace |
| WS-01B | 300–450 | 10–35 | migration, Project vertical e corredor de registro |
| **Total** | **640–950** | **15–65** | aproximadamente metade é teste e migration |

É uma faixa, não budget de sucesso. Se o trabalho ultrapassar 1.050 linhas novas sem incluir
generated files, reavalie duplicação entre API/CLI, excesso de testes por detalhe ou expansão de
escopo antes de continuar.

## Contratos de superfície

### Sucesso

- `POST /api/v1/workspaces` e `POST /api/v1/projects` retornam HTTP 201.
- CLI usa `evidrun workspace create/list` e `evidrun project create/list`.
- API e CLI devolvem `WorkspaceDocument`/`ProjectDocument` com as mesmas chaves.
- `GET /projects` mantém listagem global para compatibilidade e aceita filtro opcional
  `workspace_id`; a tool futura do Lab Agent nunca usa a forma global.
- Ordenação é `created_at`, depois `id`.

### Erros

- `workspace.name_invalid` e `project.name_invalid`: HTTP 422 / CLI 2.
- `project.workspace_not_found`: HTTP 404 / CLI 4.
- `workspace.name_conflict` e `project.name_conflict`: HTTP 409 / CLI 5.
- `scope.storage_unavailable`: HTTP 503 / CLI 3.

O shape de `ScopeError` é estável e separado de `TriageError`. Mensagem humana não é interface de
controle. Nenhuma saída inclui SQL, driver, tabela, path, credencial ou nome de banco.

## Migration e compatibilidade

Use expandir–backfill–contrair no mesmo revision quando o backend suportado permitir upgrade atômico;
se o SQLite/Alembic exigir batch rebuild, preserve essa sequência observável dentro da migration.

Antes da constraint, compute todas as chaves e detecte:

- nome que normaliza para vazio;
- colisão de Workspace;
- colisão de Project dentro do mesmo Workspace.

Falhe antes de mudar ids ou nomes. O diagnóstico pode informar ids e quantidade de colisões, mas não
escolhe vencedor. Teste upgrade em banco vazio, baseline legado e schema corrente. A migration precisa
conviver linearmente com qualquer revision que WS-02 ou outra worktree integre primeiro; rebase e
renumere em vez de criar branch de Alembic acidental.

## Autoridade e isolamento

- Criar Workspace/Project não exige ou produz `HumanAttestationRecord`.
- Payloads usam `extra=forbid` e recusam ator, authority, accepted, verified, runtime, sandbox,
  secret ou policy.
- Possuir launch token só autoriza acesso local à API; não prova humano.
- Criar Project não cria Study, RunSpec, AdmissionRecord, Run, Lab Agent, chat ou memória.
- Nenhuma Run existe antes de admissão `admitted` para o RunSpec exato.
- O Workspace do Control Plane nunca é montado no Subject ou transformado em Run Environment.

## Ownership provável

O implementador pode alterar somente a costura necessária:

- contrato puro de scope/nome/erro no domínio;
- models, agregado de catálogo, projeções/read model e uma migration Alembic linear;
- schema/router da API de plataforma;
- sub-apps CLI de Workspace/Project e registro no root;
- testes unitários, de migration e integração da superfície;
- schemas/docs gerados pelos comandos canônicos, quando aplicável;
- este brief e dispatch apenas para estado/handoff.

Não toca runtime de Run, authority, SubjectEnvelope, `WorkspaceTemplateRevision`, web/desktop,
`bootstrap_demo`, Lab Agent/memory ou worktree de WS-02. Se uma mudança necessária cair nessa lista,
pare e demonstre a dependência antes de ampliar o corte.

## Loop de execução

```text
TASK_ID=WS-01
BASE_REQUIRES=none
PARALLEL_WITH=WS-02,WS-03
MAX_REPAIR_LOOPS=6
FULL_GATE_INTERVAL=3
ALLOW_NEW_MIGRATION=1
ALLOW_AUTHORITY_SURFACE_CHANGE=0
ALLOW_RUN_ENVIRONMENT_CHANGE=0
```

```text
REDISCOVER main, migrations e worktrees concorrentes
-> IMPLEMENT WS-01A vertical
-> PROVE banco vazio, legado, duplicidade e race
-> IMPLEMENT WS-01B vertical
-> PROVE API/CLI e contract register no Project criado
-> ATTACK Unicode, cross-Workspace, campos extras e storage failure
-> REPAIR sem duplicar regra nas bordas
-> FULL GATES
```

## Testes focais

- nomes vazios, equivalentes por NFKC, case e whitespace;
- forma de exibição preservada e `name_key` nunca exposta;
- um sucesso e um conflito sob criação concorrente equivalente;
- Project pai inexistente e filtro de listagem com Workspace inexistente;
- mesmo Project name aceito em dois Workspaces e recusado duas vezes no mesmo;
- API/CLI com payload de sucesso idêntico e códigos de erro equivalentes;
- leitura direta não monta dashboard inteiro;
- migration preserva ids/names e falha fechada em colisão;
- campos de authority/runtime recusados sem side effect;
- corredor em banco vazio até `contract register`;
- resposta permanece compatível com o shape de dashboard consumido pelo frontend.

## Gates completos

```bash
uv run pytest
uv run ruff check .
uv run python scripts/check_code_budget.py
uv run pyright
pnpm typecheck:web
pnpm typecheck:desktop
pnpm test
pnpm build
uv run python scripts/validate_docs.py
```

O benchmark `CRL-CTX-002` continua offline e determinístico.

## Parada e escalação

Pare se:

- uma colisão legada exigir decisão humana sobre qual nome/entidade preservar;
- a migration formar branch com revision integrada por outra worktree;
- API e CLI só conseguirem paridade duplicando validação ou tradução;
- compatibilidade exigir remover campo já entregue ao frontend;
- implementação parecer exigir policy, sandbox, Lab Agent, authority ou mudança em RunSpec;
- dois reparos consecutivos falharem pela mesma causa.

## Critério de saída

Em banco vazio, sem fixture e sem acesso direto ao SQLite, API e CLI criam/listam Workspace e Project
com unicidade determinística e erros seguros. Uma contract revision é registrada no Project criado.
Nomes equivalentes nunca geram duplicata ou reaproveitamento silencioso; Projects iguais em
Workspaces diferentes continuam válidos. Nenhum caminho cria authority, Run ou Run Environment.

## Handoff

Entregue base/head/branch, migration id efetivo, arquivos alterados, transcrições reais do corredor
API e CLI, matriz de migration vazio/legado/colisão, testes e gates, estimativa real de linhas,
findings P0/P1, gaps para WS-41 e o ticket desbloqueado. Preserve separadamente qualquer trabalho
concorrente de WS-02.
