---
id: planning-task-workspace-project-surface
type: implementation-task
title: WS-01 Superficie publica de Workspace e Project
status: proposed
authority: planning
volatility: snapshot
owner: product-engineering
created_at: 2026-07-23
updated_at: 2026-07-24
observed_at: 2026-07-24
review_due: 2026-08-07
applies_to: workspace-project-surface
sources:
  - docs/planning/mvp-implementation-roadmap.md
  - docs/adr/0010-verifiable-human-authority.md
  - docs/adr/0015-human-subject-envelope-and-authenticator-lifecycle.md
  - docs/architecture/agents-and-authority.md
  - docs/governance/documentation.md
  - CONTEXT.md
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
---

# WS-01 — Superficie de Workspace e Project

`workstream_state: queued`

## Resultado pratico

Um usuario com banco novo cria um Workspace e um Project usando somente superficie publica, e em
seguida registra um contract nesse Project. Nenhum passo exige `sqlite3`, script interno, fixture ou
`evidrun demo`.

Hoje isso e impossivel. Este brief resolve o bloqueio B1 do roadmap. Ele nao adiciona capability de
dominio: da entrada publica a um dominio que ja existe.

## Snapshot inicial

Verificado em `main` no dia 2026-07-24. Confirme cada ponto antes de editar, porque o corte se move.

- `Repository.create_workspace(name)` e `Repository.create_project(workspace_id, name)` existem em
  `src/evidrun/infrastructure/database/repository.py` (logo depois do `__init__`, antes de
  `save_contract_revision`). Ambos geram `new_id("ws")`/`new_id("prj")`, gravam `created_at=utc_now()`
  e retornam a row. Nao validam nada: nome vazio passa, `workspace_id` inexistente passa para o banco
  decidir.
- Os unicos consumidores desses metodos hoje sao `EvidrunService.bootstrap_demo`
  (`src/evidrun/runs/service.py`) e testes de integracao/acceptance. `bootstrap_demo` reusa o primeiro
  workspace de `latest_dashboard()` se houver algum, senao cria `"Laboratorio local"`; procura um
  project chamado `"Context Reliability Lab"` por nome e cria se nao achar. Esse padrao de
  reaproveitamento por nome e conveniencia de fixture, nao contrato: nao o promova a semantica de
  produto.
- Em `src/evidrun/entrypoints/api/app.py` existem apenas leituras: `GET /api/v1/workspaces` e
  `GET /api/v1/projects`, ambas retornando `repository.latest_dashboard()["workspaces"]` e
  `[...]["projects"]`. Nao existe nenhuma rota `POST` para essas entidades.
- Em `src/evidrun/entrypoints/cli/app.py` nao existe nenhum comando de workspace ou project. Os
  sub-apps Typer registrados sao `experiment`, `contract`, `study`, `run`, `bundle`, `chat`, `data`,
  `provider` e `authority`, mais os comandos de topo `init`, `doctor`, `serve` e `demo`.
- `ContractRevisionRow.project_id` e `ForeignKey("projects.id")` e o engine liga
  `PRAGMA foreign_keys=ON` (`src/evidrun/infrastructure/database/engine.py`). Logo,
  `contract register` num project inexistente estoura `IntegrityError: FOREIGN KEY constraint failed`
  vindo do driver, atravessando `save_contract_revision` sem tradução. Na CLI isso e traceback; na
  API, o `except Exception` de `register_contract` converte em HTTP 422 com o texto cru do SQLAlchemy.

### Fatos a redescobrir antes de escrever codigo

1. Qual e o shape exato devolvido por `Repository._workspace_dict` e `_project_dict` (perto do fim de
   `repository.py`), porque a resposta do `POST` precisa ser compativel com o que o `GET` ja devolve.
2. Se `apps/web/src/types.ts` (`DashboardData.workspaces`/`projects`) declara menos campos do que a
   API entrega, e se ampliar a resposta cria drift de tipo. Se criar, registre como Backend Contract
   Gap para WS-41; nao redesenhe o gerador de tipos aqui.
3. Se `latest_dashboard()` e chamado uma vez por request nas duas rotas de leitura e qual o custo
   real: ele carrega runs, comparisons, chats, grades e snapshots inteiros para devolver duas listas.
4. Se algum caminho alem de `bootstrap_demo` depende de "existe no maximo um workspace".
5. Como `_components` na CLI monta `Settings`/`Database`/`Repository` e onde `database.dispose()` e
   chamado, para nao vazar conexao nos comandos novos.

## Escopo

- `POST /api/v1/workspaces` criando um Workspace a partir de um nome validado.
- `POST /api/v1/projects` criando um Project dentro de um Workspace existente.
- Comandos CLI equivalentes, um sub-app novo com `create`/`list` para cada entidade, seguindo o
  padrao dos sub-apps existentes (`typer.Typer(...)` + `app.add_typer(...)`, saida via
  `console.print_json`, `database.dispose()` no `finally`).
- Validacao de entrada no dominio, nao apenas no DTO do FastAPI, para que API e CLI rejeitem o mesmo
  input com a mesma regra.
- Traducao de referencia invalida em erro de dominio legivel, incluindo o caso de registrar contract
  com `project_id` inexistente.
- Decisao explicita e documentada sobre qual e a leitura canonica de Workspace/Project.

## Paridade API/CLI

O repo trata divergencia entre API e CLI como defeito, nao como diferenca de superficie: os ADRs 0008,
0010, 0014 e 0015 e `docs/operations/runtime-worker.md` descrevem comportamento como "API e CLI"
fazendo a mesma coisa. Sustente isso estruturalmente:

- a regra de validacao vive num unico ponto do dominio/repository; API e CLI chamam o mesmo caminho;
- os campos aceitos na criacao sao os mesmos nos dois lados, com os mesmos defaults;
- o payload de sucesso tem as mesmas chaves nos dois lados;
- a mesma entrada invalida produz a mesma mensagem, variando so o envelope (HTTP status contra exit
  code e stderr);
- se um lado precisar de um campo que o outro nao tem, isso e sinal de que a regra esta no
  entrypoint errado. Mova para o dominio antes de continuar.

Escreva o teste de paridade no mesmo commit da segunda superficie, nao depois.

## Leitura canonica

`GET /api/v1/workspaces` e `GET /api/v1/projects` sao hoje fatias de `latest_dashboard()`: o
repository monta o dashboard completo (workspaces, projects, experiments, runs, comparisons, chats,
summary) e a rota devolve uma chave. Isso significa que a leitura de duas tabelas pequenas paga o
custo de agregacao do dashboard inteiro, e que qualquer mudanca no dashboard muda essas rotas.

Tome uma decisao e registre-a no PR:

- **manter** o dashboard como leitura canonica, aceitando o acoplamento, e documentar que essas rotas
  sao projecoes derivadas; ou
- **extrair** leituras proprias (`list_workspaces`/`list_projects` no repository) e manter o dashboard
  como agregado separado, com as duas rotas passando a consumir a leitura propria.

Se extrair, a resposta precisa permanecer compativel campo a campo com o que o dashboard devolvia
hoje, porque o frontend consome `DashboardData`. Nao introduza um segundo formato de Workspace ou
Project: duas formas do mesmo agregado e exatamente o drift que WS-41 vai ter que fechar.

Nao amplie escopo para paginacao, filtro ou ordenacao configuravel. A ordenacao atual e por
`created_at` ascendente; preserve-a.

## Erro util em vez de `IntegrityError`

O sintoma observado e um `FOREIGN KEY constraint failed` vazando do driver. Corrija a causa, nao o
texto:

- criar Project com `workspace_id` inexistente falha com erro de dominio que nomeia a entidade e o id
  recusado, antes de tocar o banco;
- registrar contract com `project_id` inexistente falha da mesma forma, com uma mensagem que diz o que
  fazer (criar o Project) em vez de expor SQL;
- na API isso e um status HTTP deliberado, nao o `except Exception` generico repassando `str(exc)`;
- nome vazio, so espaco em branco, ou acima de um limite explicito e recusado com a mesma regra nos
  dois entrypoints;
- nenhuma mensagem de erro inclui path de banco, SQL, credencial ou nome de tabela interna.

Se corrigir `register_contract` exigir tocar o handler compartilhado, prefira validar a existencia do
project no caminho de dominio a alargar o `except`. Um `except IntegrityError` traduzindo string do
driver e conserto de sintoma: a checagem pertence ao dominio.

## Autoridade

Criar Workspace e criar Project sao acoes rotineiras e **nao** exigem autoridade humana verificada.
Isso e sustentado por codigo e por ADR, nao por conveniencia:

- `src/evidrun/authority/policy.py` define `CRITICAL_ACTIONS` como um conjunto fechado
  (`revision.accepted`, `revision.rejected`, `revision.superseded`, `evaluation.adjudicated`,
  `evaluation.reviewed`, `external_effect.authorized`). Criacao de entidade nao esta nele, e
  `requires_verified_human` so exige humano verificado para acao critica ou modo `PRIVILEGED`.
- O ADR 0015, secao "Politica de autonomia", declara que autenticacao e opcional para criar, testar e
  executar em sandbox, e obrigatoria apenas quando o sistema afirma autoridade humana, libera risco
  maior ou promove evidencia para verificado.
- O ADR 0010 reserva ao principal verificavel aceitacao, rejeicao, supersession, adjudicacao e
  autorizacao de efeito externo. Criacao de escopo nao esta nessa fronteira.

Limites que continuam valendo:

- criar Workspace ou Project **nao** produz, implica nem habilita nenhuma attestation, decision ou
  aceitacao. Nada nesses caminhos escreve `HumanAttestationRecord`, decision de revision ou qualquer
  campo lido como prova de autoridade;
- nao aceite `actor_id`, `actor_type`, `approved`, `verified` ou equivalente nos payloads de criacao.
  Um campo de ator fornecido pelo cliente nunca e prova de autoridade (AGENTS.md, invariantes de
  autoridade);
- as rotas novas ficam sob a mesma dependencia `authorize` das rotas existentes. Posse do launch token
  continua nao sendo prova de presenca humana; ela apenas delimita o sidecar local;
- nao adicione parametro de `AuthorityMode` a essas superficies. Nao existe modo em que criar um
  Project deva exigir cerimonia, e adicionar o parametro convida a usar `PRIVILEGED` como decoracao.

## Nao objetivos

Fora do corte, explicitamente:

- autoria assistida ou geracao de Workspace/Project por agente;
- importacao em massa, seed de template, catalogo de exemplos ou substituto de `evidrun demo`;
- multi-tenant, account, org, papel, permissao por usuario ou ACL por Project;
- sync, replicacao, backup, export ou restore de Workspace;
- rename, arquivamento, soft delete ou delete de Workspace/Project;
- integracao do wizard de Create do frontend (pertence a WS-51);
- refatorar `Repository` por agregado (pertence a WS-11);
- redesenho de `latest_dashboard()` como read-model geral;
- geracao de tipos HTTP (pertence a WS-41).

Se o trabalho comecar a exigir qualquer um destes, pare e escale. Nenhum deles e pre-requisito do
criterio de saida.

## Invariantes normativas

Nao relaxe nada abaixo para fazer a superficie caber:

- dominio Python nao importa FastAPI nem SQLAlchemy; a validacao nova vive no dominio/repository, os
  DTOs ficam no entrypoint (AGENTS.md, Fronteiras);
- agente, automacao e servico nunca afirmam ser humano nem transformam campo de ator em prova de
  autoridade (AGENTS.md; ADR 0010);
- autoridade humana continua exigindo `HumanAttestationRecord` verificado, e `repository_fixture`
  continua nao humano e restrito ao import dedicado do pacote `CRL-CTX-002` (AGENTS.md; ADR 0010);
- nenhuma Run nova existe antes de `AdmissionRecord.decision=admitted` para o RunSpec exato: criar
  Project nao encurta nem toca esse caminho;
- credencial, secret e path de banco nunca aparecem em resposta, log ou mensagem de erro (AGENTS.md);
- ADR aceito nao e reescrito; se a semantica de Workspace/Project mudar, crie ADR sucessor. Este
  brief nao prevê essa mudanca, e criar um ADR aqui esta fora de escopo;
- documentacao nao descreve roadmap como comportamento implementado (AGENTS.md, Fonte de verdade);
- `Workspace` e `Project` mantem o significado de `CONTEXT.md`: Workspace e fronteira local de dados,
  Project e conjunto de scenarios, experimentos e conversas dentro de um Workspace. Nao introduza
  `tenant` nem `account` como sinonimo.

## Ownership de paths

Pode editar:

- `src/evidrun/entrypoints/api/app.py`
- `src/evidrun/entrypoints/cli/app.py`
- `src/evidrun/infrastructure/database/repository.py`, limitado a `create_workspace`,
  `create_project` e a eventual leitura extraida; nenhum outro metodo
- `tests/integration/test_api.py`
- `tests/integration/test_contract_cli.py`
- testes novos sob `tests/integration/`
- `docs/planning/tasks/README.md`, apenas a linha de estado da WS-01
- este arquivo, para atualizar `workstream_state` e `status`

Nao pode editar:

- `src/evidrun/contracts/compiler.py`, `src/evidrun/runs/adapters.py`, `src/evidrun/runs/worker.py`
  e o restante de `src/evidrun/runs/`
- `src/evidrun/runs/service.py`, incluindo `bootstrap_demo`. Ela e a referencia comportamental atual;
  reescrevê-la aqui apaga o unico caminho que hoje funciona. Se ela ficar redundante depois desta
  superficie, registre no handoff em vez de tocar
- `src/evidrun/authority/`
- `src/evidrun/infrastructure/database/models.py`. Nada neste corte exige coluna nova; se parecer
  exigir, o escopo cresceu
- `apps/desktop/` e `apps/web/`
- `docs/adr/`, `AGENTS.md`, `CONTEXT.md`
- `docs/planning/mvp-implementation-roadmap.md`
- as worktrees de WS-02 e WS-03

Sem migration neste corte. As tabelas `workspaces` e `projects` ja existem com as colunas
necessarias. Se voce concluir que precisa de migration, isso e sinal de escopo crescendo: escale.

## Loop de execucao

```text
TASK_ID=WS-01
BASE_REQUIRES=none
PARALLEL_WITH=WS-02,WS-03
MAX_REPAIR_LOOPS=6
FULL_GATE_INTERVAL=3
ALLOW_NEW_MIGRATION=0
ALLOW_AUTHORITY_SURFACE_CHANGE=0
```

```text
DISCOVER superficies e consumidores atuais de workspace/project
-> DECIDE leitura canonica (dashboard slice contra leitura propria)
-> IMPLEMENT validacao no dominio
-> IMPLEMENT rota POST
-> IMPLEMENT comando CLI equivalente
-> PROVE paridade API/CLI com teste
-> INTEGRATE contract register num project criado pela superficie nova
-> ATTACK entrada invalida, referencia inexistente, duplicidade, concorrencia
-> REPAIR
-> FULL GATES
```

### Condicionais

- Se a validacao aparecer duplicada no handler HTTP e no comando CLI, extraia para o dominio antes de
  seguir. Duas copias da mesma regra e o defeito, nao o atalho.
- Se `latest_dashboard()` tiver que crescer para atender a criacao, pare: a resposta do `POST` deve
  vir da row criada, nao de uma releitura do dashboard.
- Se traduzir o erro de FOREIGN KEY exigir `except IntegrityError`, redesenhe: valide a existencia do
  project no caminho de dominio.
- Se um caminho de criacao parecer precisar de credencial, attestation ou `AuthorityMode`, releia a
  secao de autoridade. Criar escopo e rotineiro; se o requisito real for outro, ele nao pertence a
  este brief.
- Se o frontend for necessario para provar o criterio de saida, voce esta no brief errado: o criterio
  e provado por CLI e API.
- Se um teste existente comecar a depender de "existe exatamente um workspace", corrija o teste, nao
  a superficie.
- Se WS-02 ou WS-03 pedir mudanca em `entrypoints/cli/app.py`, combine a ordem por mensagem direta
  antes de editar. Esse arquivo e o unico ponto de contato plausivel entre as tres frentes da Onda 0.

## Testes focais

Nenhum teste de "o metodo existe". Cada um defende um contrato observavel:

- criar Workspace e depois Project retorna ids estaveis, e os `GET` passam a lista-los;
- criar Project com `workspace_id` inexistente e recusado com erro de dominio, sem `IntegrityError`
  nem texto de SQL na resposta;
- registrar contract com `project_id` inexistente e recusado com mensagem que nomeia o project e
  nao expoe SQL;
- nome vazio e nome so com espaco sao recusados identicamente pela API e pela CLI;
- paridade: mesma entrada valida pelos dois entrypoints produz as mesmas chaves de payload; mesma
  entrada invalida produz a mesma mensagem;
- nenhum payload de criacao aceita campo de ator/autoridade: campo extra e recusado
  (`extra="forbid"`) e nao existe caminho que grave attestation ou decision;
- criar dois Workspaces com o mesmo nome nao e tratado como reaproveitamento silencioso; a semantica
  escolhida esta explicitada em teste;
- corredor ponta a ponta em banco vazio: criar Workspace, criar Project, registrar contract, sem
  `evidrun demo` e sem tocar o banco;
- a resposta das rotas de leitura permanece compativel com `DashboardData` do frontend.

Gates: rode `uv run pytest`, `uv run ruff check .`, `uv run pyright` e
`uv run python scripts/validate_docs.py`. Os gates de `pnpm` sao obrigatorios no commit final se
qualquer arquivo em `apps/` tiver mudado; neste corte nao deveriam mudar. Rode a suite completa do
`AGENTS.md` no commit final. O benchmark `CRL-CTX-002` continua offline e deterministico.

## Parada e escalacao

Pare e escale, sem improvisar, se:

- o criterio de saida exigir migration, coluna nova ou mudanca em `models.py`;
- provar a paridade exigir mudar o contrato de autoridade;
- a decisao sobre leitura canonica implicar quebrar `DashboardData` para o frontend;
- `bootstrap_demo` tiver que ser reescrita para o corredor novo funcionar;
- dois reparos consecutivos falharem pela mesma causa: diagnostique a causa raiz e mude de abordagem
  em vez de ajustar detalhe;
- uma frente da Onda 0 pedir edicao concorrente do mesmo trecho de `entrypoints/cli/app.py`.

## Criterio de saida

Em banco vazio, sem editar SQLite e sem `evidrun demo`, um usuario executa criacao de Workspace,
criacao de Project e `contract register` nesse Project, e o registro conclui. O mesmo corredor
funciona pela API com os mesmos campos e as mesmas mensagens de erro. Registrar contract com project
inexistente devolve erro de dominio legivel, nao `FOREIGN KEY constraint failed`. Nenhuma attestation,
decision ou aceitacao e criada por esses caminhos.

## Handoff

Entregue, conforme o dispatch em `README.md`:

- base SHA, head SHA e branch;
- arquivos sob ownership alterados;
- migrations e generated files (esperado: nenhum);
- transcricao real do corredor de saida por CLI e por API;
- decisao tomada sobre leitura canonica e sua justificativa;
- testes focais e gates executados;
- findings P0/P1 e regressoes;
- Backend Contract Gaps abertos, em especial drift entre resposta da API e `apps/web/src/types.ts`,
  endereçado a WS-41;
- se `bootstrap_demo` ficou redundante, a recomendacao, sem executa-la;
- proximo brief desbloqueado.
