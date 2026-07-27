---
id: contract-workspace-project-surface-v1
type: contract
title: Superfície pública de Workspace e Project v1
status: accepted
authority: normative
volatility: timeless
owner: core
created_at: 2026-07-27
updated_at: 2026-07-27
applies_to: schema/control-plane-scope@1
sources:
  - docs/adr/0020-workspace-project-run-environment-boundaries.md
  - docs/contracts/triage-error.md
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
---

# Superfície pública de Workspace e Project v1

Este contrato define criação e listagem das duas fronteiras duráveis do Control Plane. Está aceito,
mas ainda não implementado: os writes internos existentes não satisfazem validação, unicidade,
erros estáveis, API, CLI ou migration descritos aqui.

Criar Workspace ou Project não cria Run Environment, sandbox, processo, filesystem, credencial,
contract decision nem `HumanAttestationRecord`.

## Documentos públicos

`WorkspaceDocument`:

| Campo | Tipo | Regra |
| --- | --- | --- |
| `id` | id | gerado pelo sistema e estável |
| `name` | texto | forma normalizada de exibição |
| `created_at` | timestamp | UTC, atribuído pelo sistema |

`ProjectDocument` acrescenta:

| Campo | Tipo | Regra |
| --- | --- | --- |
| `workspace_id` | ref | Workspace pai existente |

`name_key` é detalhe persistido de identidade e nunca aparece no payload público.

## Comandos de criação

`CreateWorkspace` recebe exatamente `name`. `CreateProject` recebe exatamente `workspace_id` e
`name`. Campos de ator, authority, policy, runtime, template, sandbox ou configuração de Lab Agent
são recusados como não declarados.

As superfícies são:

| Operação | HTTP | CLI | Sucesso |
| --- | --- | --- | --- |
| criar Workspace | `POST /api/v1/workspaces` | `evidrun workspace create <name>` | HTTP 201 / exit 0 com `WorkspaceDocument` |
| listar Workspaces | `GET /api/v1/workspaces` | `evidrun workspace list` | lista de `WorkspaceDocument` |
| criar Project | `POST /api/v1/projects` | `evidrun project create <workspace-id> <name>` | HTTP 201 / exit 0 com `ProjectDocument` |
| listar Projects | `GET /api/v1/projects?workspace_id=<id>` | `evidrun project list --workspace-id <id>` | lista de `ProjectDocument` |

O filtro `workspace_id` de listagem é opcional para preservar a leitura humana global já exposta.
Quando presente, Workspace inexistente devolve `project.workspace_not_found`; quando ausente, a
operação lista todos os Projects visíveis ao operador local. Essa forma sem filtro não é uma tool do
Lab Agent e não concede escopo cross-Project.

API e CLI projetam as mesmas chaves e valores. A diferença permitida é somente o envelope de
transporte: status HTTP versus exit code e stdout/stderr. Listas são ordenadas por `created_at` e,
como desempate determinístico, `id`.

As leituras canônicas consultam Workspace e Project diretamente. O dashboard pode reutilizar essas
projeções, mas `GET /workspaces` e `GET /projects` não dependem de montar Runs, chats, comparisons ou
outras seções do dashboard.

## Normalização e identidade do nome

Uma única função pura do domínio transforma o input em `(name, name_key)`:

1. aplica Unicode NFKC;
2. remove whitespace no início e no fim;
3. substitui cada sequência interna de whitespace por um espaço ASCII;
4. rejeita a forma vazia;
5. deriva `name_key = name.casefold()`.

`name` preserva capitalização, acentos e caracteres significativos após NFKC/whitespace. A mesma
função é usada por API, CLI, repository e migration; DTOs não possuem uma segunda regra.

Unicidade:

- Workspace: `UNIQUE(name_key)` no datastore local;
- Project: `UNIQUE(workspace_id, name_key)`;
- o mesmo nome de Project é permitido em Workspaces diferentes.

A criação nunca faz `get-or-create`. Input que colide depois da normalização falha com conflito,
inclusive sob duas transações concorrentes. Uma checagem amigável pode anteceder a escrita, mas a
constraint e a tradução pós-race são a garantia final.

## ScopeError

Criação de escopo não é uma das seis fases de triagem que antecedem uma Run. Portanto estes erros não
adicionam uma fase `catalog` a `TriageError`. `ScopeError` é um contrato separado com:

- `code`: identificador estável;
- `category`: `invalid`, `not_found`, `conflict` ou `unavailable`;
- `message`: texto humano livre e traduzível;
- `field_path`: campo culpado, quando aplicável;
- `remediation`: próxima ação, quando conhecida.

Catálogo:

| Código | Categoria | HTTP | CLI | Quando |
| --- | --- | ---: | ---: | --- |
| `workspace.name_invalid` | `invalid` | 422 | 2 | nome não produz forma válida |
| `workspace.name_conflict` | `conflict` | 409 | 5 | `name_key` já existe no datastore |
| `project.name_invalid` | `invalid` | 422 | 2 | nome não produz forma válida |
| `project.name_conflict` | `conflict` | 409 | 5 | `name_key` já existe no Workspace pai |
| `project.workspace_not_found` | `not_found` | 404 | 4 | Workspace pai não existe |
| `scope.storage_unavailable` | `unavailable` | 503 | 3 | persistência necessária falhou sem tradução mais específica |

Mensagens nunca expõem SQL, nome de tabela, path de banco, credencial ou payload interno. Código,
categoria, status/exit e shape são estáveis; mensagem não é chave de controle.

O erro `register.project_not_found` continua pertencendo à fase de registro de contract. Ele não é
renomeado para `ScopeError`, porque a operação recusada é registrar uma revision, não criar ou listar
um Project.

## Migration e bancos existentes

A implementação adiciona `name_key` persistido e constraints por migration Alembic, usando o próximo
revision id livre no momento do merge. O upgrade:

1. expande o schema com colunas inicialmente compatíveis;
2. normaliza cada nome existente com a função canônica;
3. detecta nome inválido ou colisões antes de instalar constraints;
4. aborta com diagnóstico acionável se houver conflito;
5. torna as colunas obrigatórias e instala as constraints somente depois de um backfill sem conflito.

Migration não renomeia, mescla, remove ou escolhe vencedor silenciosamente. O operador corrige os
dados e executa novamente. Bancos vazios, bancos legados e o schema corrente precisam ser cobertos.
Downgrade não pode descartar informação necessária sem uma regra explícita e testada.

## Autoridade e fronteiras

Criar Workspace/Project é operação rotineira do Control Plane. Não exige attestation e não produz
aceitação humana. O launch token local continua delimitando a API, mas não prova presença humana.

O contrato não inclui rename, archive, delete, sync, ACL, import em massa, template inicial,
idempotency key, frontend ou policy de Run Environment. Uma revisão futura precisa versionar
qualquer campo executável; preferências mutáveis de Workspace/Project nunca alteram uma Run sem
entrar no RunSpec e na admissão.

## Provas mínimas

- Banco vazio: criar Workspace, criar Project e registrar uma contract revision nesse Project por
  API e por CLI, sem fixture nem acesso direto ao SQLite.
- Colisões por case, whitespace e formas Unicode equivalentes devolvem conflito, nunca
  reaproveitamento silencioso.
- Projects de mesmo nome em Workspaces distintos são aceitos.
- Criação concorrente do mesmo nome produz um sucesso e um conflito tipado.
- Banco legado com nomes sem colisão migra preservando ids e formas de exibição; banco com colisão
  falha antes de instalar a constraint.
- Payload com campo de authority ou runtime é recusado e nenhum record de authority, Run ou Run
  Environment é criado.
- Listagens usam leitura direta e mantêm o shape já consumido pelo frontend.
