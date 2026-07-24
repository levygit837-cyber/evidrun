---
id: planning-task-mvp-operator-console
type: implementation-task
title: WS-10 Console operacional do MVP
status: accepted
authority: planning
owner: web
created_at: 2026-07-23
updated_at: 2026-07-23
observed_at: 2026-07-23
review_due: 2026-07-30
applies_to: apps/web
sources:
  - docs/planning/mvp-implementation-roadmap.md
  - docs/architecture/system.md
  - docs/architecture/desktop-runtime.md
  - docs/contracts/desktop-bridge.md
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
---

# WS-10 — Console operacional do MVP

`workstream_state: queued`

## Contexto abstrato

A UI atual e uma demonstracao excelente do CRL, mas nao e uma ferramenta geral: ela chama
`/demo/bootstrap`, assume duas Runs e apresenta scores fixos. Esta task cria a estrutura de produto
que permite authoring, admissao, execucao e evidence inspection sem aguardar o merge do Kernel.

O Droid deve trabalhar em worktree propria e construir contra um port de API testavel. Quando um
endpoint ainda nao estiver em `main`, a UI usa fixture/mock somente nos testes e mostra a capability
como indisponivel em producao. Nenhum estado simulado pode parecer uma Run real.

## Worktree e ownership

```text
TASK_ID=WS-10
RECOMMENDED_BRANCH=task/mvp-operator-console
BASE_REF=origin/main
PRIMARY_PATHS=apps/web/src,apps/web/tests
SHARED_PATHS=package.json,pnpm-lock.yaml,docs/planning
FORBIDDEN_PATHS=src/evidrun,alembic,schemas/generated,apps/web/src/generated/contracts.ts
```

Se o Runtime Kernel for mesclado durante a task, rebaseie e integre o client gerado em um commit
separado. Antes disso, nao copie DTOs nao commitados da outra worktree.

## Resultado obrigatorio

Uma console navegavel e responsiva com:

1. **Projects:** selecionar/criar projeto local.
2. **Contracts:** validar, registrar e listar revisions; visualizar digest e status.
3. **Study:** selecionar Study, compilar preview e mostrar cenarios x variants x repetitions.
4. **Admission:** executar preflight e traduzir issues estruturadas para linguagem operacional.
5. **Runs:** enfileirar quando a capability existir; listar Run/job/attempt e acompanhar SSE.
6. **Run detail:** lifecycle, SubjectEnvelope digest, events, evaluations e terminal.
7. **Evidence:** artifact manifest, checkpoints e Progress Artifacts quando presentes.
8. **Authority:** mostrar disabled/opt-in, credenciais e confirmacao explicita sem expor token ao
   renderer.
9. **Bundle:** exportar e exibir o resultado separado de integrity, audit completeness, portability
   e replayability.

## Arquitetura tecnica

- introduzir um `EvidrunApiPort` pequeno e orientado a use cases;
- separar DTO de transporte de view-model;
- usar TanStack Query para server state e TanStack Router para rotas reais;
- manter `window.evidrunDesktop` apenas no client de conexao;
- nunca importar Electron/Node no renderer;
- nao usar o dashboard agregado como unica fonte das telas detalhadas;
- tratar SSE/reconnect como estado explicito;
- cada capability da UI deriva de resposta/feature detection, nao de constante decorativa.

Modos do port:

```text
API_MODE=main
API_MODE=kernel_merged
API_MODE=test_fixture
```

`test_fixture` so e selecionavel por injecao de teste. O bundle de producao nao inclui um botao que
troque para backend fake.

## Harness Droid

```text
MAX_IMPLEMENTATION_LOOPS=12
MAX_IDENTICAL_FAILURES=3
FULL_GATE_INTERVAL=3
VISUAL_QA_REQUIRED=1
ACCESSIBILITY_QA_REQUIRED=1
MOBILE_QA_REQUIRED=1
ALLOW_BACKEND_EDITS=0
ALLOW_GENERATED_DTO_EDITS=0
```

Estado entre loops:

```json
{
  "phase": "discover|contract|slice|verify|visual|review|repair|handoff",
  "base_sha": "...",
  "api_mode": "main|kernel_merged|test_fixture",
  "completed_screens": [],
  "contract_gaps": [],
  "test_failures": [],
  "visual_findings": [],
  "open_p0_p1": []
}
```

O arquivo de estado, se usado, fica fora do Git ou em diretorio temporario. Nao persistir launch
token, assertion ou credencial.

## Loop

```text
DISCOVER current API and UI
-> DEFINE information architecture
-> DEFINE API port and fixtures
-> IMPLEMENT one vertical screen
-> TEST states and errors
-> VISUAL inspect desktop/mobile
-> ACCESSIBILITY inspect keyboard/names/focus
-> REVIEW contract truthfulness
-> REPAIR P0/P1
-> repeat next screen
-> FULL GATES
-> HANDOFF
```

### Condicionais

- Se um endpoint nao existir, registre `Backend Contract Gap` e use fixture no teste; nao crie
  backend nesta worktree.
- Se o Kernel for mesclado, rebaseie somente com worktree limpa e substitua fixtures pelas rotas
  reais gradualmente.
- Se a resposta real divergir do mock, o backend e a fonte; corrija port/view-model e adicione teste
  de contrato.
- Se a UI precisar de campo de dominio bruto, crie um view-model no client; nao importe Python
  schema ou Electron.
- Se authority estiver desabilitada, mostre opt-in indisponivel; nao permita decisao humana por
  campo de texto.
- Se a mesma falha visual/logica reaparecer tres vezes, chame um subagente reviewer e reduza a
  superficie do componente.
- Se testes focais passarem mas um fluxo nao puder ser exercitado sem mock, entregue-o como
  `integration_pending`, nao como concluido.

## Subagentes

1. **UX flow reviewer read-only:** tenta completar Study -> admission -> Run sem conhecimento do
   codigo.
2. **API contract reviewer read-only:** compara ports, fixtures e OpenAPI disponivel.
3. **Accessibility/visual judge read-only:** teclado, focus, labels, contraste, mobile e estados de
   erro/loading/empty.

O agente principal integra findings. Subagentes nao alteram backend nem arquivos gerados.

## Testes obrigatorios

- unit tests do API port e error mapping;
- contract fixtures validadas contra schemas/OpenAPI quando disponiveis;
- React Testing Library para loading, empty, rejected, unsupported, failed e terminal;
- navegacao por teclado e accessible names;
- SSE reconnect, evento duplicado e terminal;
- authority disabled/enabled sem token no DOM;
- matrix preview e admission issues;
- bundle status sem confundir auditavel/portatil/replayable;
- viewport desktop, tablet e mobile;
- pelo menos um fluxo Playwright contra backend local quando WS-00 estiver integrado.

Depois, executar os gates completos do `AGENTS.md`.

## Nao objetivos

- Canvas visual;
- editor de graph protocol;
- chat funcional do Lab Agent;
- code editor completo;
- alteracao de contratos;
- tool/skill configurator;
- design que esconda estados de confianca ou capability ausente.

## Handoff

Entregar:

- mapa de rotas e screenshots desktop/mobile;
- screens concluidas e `integration_pending`;
- API contract gaps com request/response esperados;
- testes executados;
- findings de UX/accessibility;
- lista exata de fixtures ainda usadas;
- passos de rebase/integracao depois de WS-00.

