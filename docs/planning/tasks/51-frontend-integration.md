---
id: planning-task-frontend-integration
type: implementation-task
title: WS-51 Integração frontend de Workspace, Project e Lab Agent
status: proposed
authority: planning
volatility: snapshot
owner: frontend
created_at: 2026-07-27
updated_at: 2026-07-28
observed_at: 2026-07-28
review_due: 2026-08-24
applies_to: frontend-integration
sources:
  - docs/planning/mvp-implementation-roadmap.md
  - docs/adr/0020-workspace-project-run-environment-boundaries.md
  - docs/adr/0021-hierarchical-lab-agent-scope.md
  - docs/adr/0022-explicit-execution-trust-without-per-run-authentication.md
  - docs/contracts/workspace-project-surface-v1.md
  - docs/contracts/lab-agent-scope-v1.md
  - docs/contracts/agent-inventory-workspace-v1.md
  - docs/contracts/execution-trust-v1.md
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
---

# WS-51 — Integração frontend de Workspace, Project e Lab Agent

`workstream_state: blocked`

## Resultado prático

O app deixa clara a hierarquia Workspace → Project → Study/Run sem confundir o Workspace durável com
o Run Environment. O usuário navega um Workspace, entra em um Project Room, conversa com o mesmo Lab
Agent no scope correto, cria um experimento e acompanha Runs/evidência sem a UI inventar authority,
sandbox ou acesso cross-Project.

Este brief registra o comportamento futuro. Hoje Create ainda é rascunho/fixture, Laboratory é mock e
não existe Project Room integrado.

## Dependências

- WS-01: criação/listagem real e `ScopeError` de Workspace/Project;
- WS-03/WS-40: trust de execução não verificada e ReviewPackage, antes de Create executar drafts;
- WS-04: sessões, `LabAgentEnvelope`, tools e streaming reais;
- WS-06: batch e métricas para visão agregada do Project;
- WS-41: DTOs HTTP gerados para remover drift de tipos.

Partes visuais podem ser prototipadas antes, mas nenhuma integração muda de `integration_pending`
sem a capability correspondente em `main` e prova por adapter real.

## Modelo de navegação

### Workspace

Workspace switcher escolhe a hard boundary local. Sua superfície mostra Projects e regras gerais; não
oferece filesystem, sandbox, provider secret ou opções executáveis implícitas. Criar Workspace usa o
preset organizacional padrão e pede apenas nome no v1.

### Project Room

Project Room é uma projeção de UI, não novo agregado. Ele reúne, no mesmo scope:

- conversas do Project;
- Studies/contracts e drafts;
- Runs, batches, comparisons e métricas derivadas;
- evidence refs e artifacts autorizados;
- memória/candidatos do Project quando WS-07 existir.

O Room não é pasta e não possui “seu próprio agente”. O cabeçalho mostra o mesmo Lab Agent e o scope
ativo. Um nome de Project repetido em outro Workspace é válido; breadcrumb sempre inclui Workspace.

### Sessões

- General chat permanece no Workspace e pode criar/navegar Projects, sem carregar conteúdo de todos;
- Project chat pertence a um Project e pode usar regras/preferências do Workspace pai;
- Focused chat acrescenta Study, Run ou Comparison do mesmo Project;
- mudar Project/foco cria ou retoma outra sessão, preservando a anterior;
- a UI exibe scope e refs consultadas; nunca sugere contexto global implícito.

## Criação e erros

Formulários usam o contrato v1, sem normalização paralela no frontend. Podem antecipar feedback de
nome, mas o servidor continua a autoridade contra race. Erros são renderizados por `ScopeError.code`:

- invalid: ajuda de campo;
- not_found: pai deixou de existir e a navegação precisa ser atualizada;
- conflict: nome equivalente já existe no scope, sem selecionar/reusar silenciosamente;
- unavailable: retry explícito, sem transformar falha em sucesso local.

Payload não oferece actor, authority, sandbox, policy ou criação automática de Lab Agent.

## Run Environment e configurações

Configuração executável aparece no fluxo versionado de Study/RunSpec, não no formulário de Workspace
ou Project. A UI chama o conceito de **Run Environment** mesmo enquanto o schema v1 serializa
`WorkspaceTemplateRevision`/`RunSpec.workspace`.

O fluxo começa com preset seguro automatizado e mostra o estado de cada opção:

- `effective`: solicitada e admitida;
- `denied`: bloqueada por policy;
- `unsupported`: runtime não aplica;
- `unavailable`: adapter/recurso necessário ausente.

Opção desativada explica o motivo e não é enviada como se fosse executável. `in_process` é exibido
como `in_process`, nunca “sandbox seguro”. Network, mounts, write zones, secrets, effects, snapshot e
cleanup pertencem ao documento versionado e à admissão; não são preferências ocultas do Room.

## Autoridade e evidência

- draft do Lab Agent é visualmente draft e exige ação humana quando o contrato de authority pedir;
- pedido de aprovação não aparece como decisão concluída;
- trust, isolamento, lifecycle, disposition e qualidade são eixos separados;
- lista e detalhe da Run exibem sempre texto explícito, como
  `Trust: Não verificada — sem confirmação humana` e `Isolamento: in_process`;
- cor, ícone e tooltip apenas reforçam o texto; projeção exportável ou imprimível repete o rótulo de
  trust e o `trust_id` em cada página, para que screenshot ou página isolada preserve o significado;
- `ArtifactRef` não vira botão de abrir bytes sem grant/materialização;
- memória não aparece como fato de Run;
- mudar Project nunca mistura Runs, evidence ou memory de outro scope.

## Não objetivos

Canvas, filesystem browser, ACL multiusuário, sync/cloud, rename/delete/archive, agent por Project,
contexto global automático, editor livre de JSON/YAML, restore/replay e configuração de secrets.

## Testes obrigatórios

- breadcrumb/switcher distingue Workspaces com Projects homônimos;
- General chat não renderiza conteúdo de Project sem seleção explícita;
- troca de Project preserva sessão anterior e abre scope novo;
- refs cross-Project não aparecem mesmo se adapter devolver erro com id conhecido;
- conflict de nome nunca faz auto-select da entidade existente;
- Create associa draft ao Project ativo e recusa mismatch de scope;
- Run Environment é configurado no documento versionado e opções unsupported permanecem desativadas;
- `in_process` nunca recebe rótulo de sandbox seguro;
- listas e detalhes distinguem os dois kinds de trust pelo texto canônico do Execution Trust v1;
- trust e isolamento continuam legíveis sem cor e em snapshot de impressão/exportação;
- estados de loading/failure/retry/cancel e reduced motion continuam cobertos;
- nenhum caminho frontend cria decision, attestation ou Run antes de admission `admitted`.

## Ownership e harness

Ownership principal: `apps/web/`, adapters HTTP gerados/consumidos e testes visuais/Electron do
corredor. Mudança de contrato Python pertence ao workstream produtor (WS-01/03/04/06/40/41), não é
redefinida no frontend. `apps/desktop/` muda somente quando lifecycle/bridge for realmente necessário.

```text
TASK_ID=WS-51
BASE_REQUIRES=WS-01,WS-03,WS-04,WS-06,WS-40,WS-41
ALLOW_FIXTURE_AS_REAL=0
ALLOW_SCOPE_CLIENT_ONLY=0
ALLOW_IN_PROCESS_SANDBOX_CLAIM=0
ALLOW_FAKE_HUMAN=0
```

```text
REDISCOVER capabilities reais e DTOs
-> INTEGRATE Workspace switcher e ScopeError
-> INTEGRATE Project Room e sessoes escopadas
-> INTEGRATE Create com Study/Run Environment versionado
-> INTEGRATE batch/observability/trust
-> ATTACK cross-Project, stale scope, authority e unsupported options
-> VISUAL QA desktop + browser + reduced motion
-> FULL GATES
```

## Condicionais de parada

- Se o backend nao impuser scope, mantenha a UI em `integration_pending`; filtro client-side nao e
  isolamento.
- Se um DTO precisar ser escrito a mao fora do pipeline de WS-41, registre o gap e pare antes de
  duplicar contrato.
- Se Create precisar aceitar uma revision sem o trust path decidido, nao improvise authority.
- Se uma opcao de Run Environment nao tiver capability admitida, desabilite com motivo; nao remova o
  gate backend.
- Se Project Room exigir ler outro Project, abra uma decisao explicita de import/comparison; nao use
  query global.

## Revisões permitidas

Use reviewers read-only independentes para: scope/cross-Project, truthfulness de authority/trust,
acessibilidade/reduced motion e contrato HTTP. Subagentes não editam o mesmo arquivo em paralelo e
nenhum reviewer promove fixture ou mock a capability.

## Gates completos

Rode a suíte integral do `AGENTS.md`, mais o corredor E2E web + sidecar + worker e inspeção visual das
formas General/Project/Focused, conflitos de nome, Run Environment unsupported e estados de trust.
O handoff inclui screenshots/transcrição, base/head/branch, DTOs alterados, capabilities ainda
`integration_pending`, findings P0/P1 e gaps remetidos aos workstreams donos.

## Critério de saída

Um usuário cria/seleciona Workspace e Project reais, entra no Project Room, usa o Lab Agent escopado,
cria um Study, vê o Run Environment solicitado e efetivo, executa pelo trust path admitido e navega
até a evidência da Run. A mesma navegação não expõe outro Project nem descreve capability ausente
como integrada.
