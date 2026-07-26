---
id: planning-task-web-page-seams
type: implementation-task
title: WS-13 Costuras das paginas web
status: accepted
authority: planning
owner: core
created_at: 2026-07-24
updated_at: 2026-07-26
observed_at: 2026-07-26
review_due: 2026-08-07
applies_to: web-page-seams
sources:
  - docs/architecture/codebase-layout.md
  - docs/adr/0017-structural-budget-and-named-seams.md
  - docs/adr/0004-python-core-typescript-ui-and-electron.md
supersedes: []
superseded_by: null
implementation_refs:
  - apps/web/src/features/observability
  - apps/web/src/features/laboratory
  - apps/web/src/features/create
verification_refs: []
---

# WS-13 — Costuras das paginas web

`workstream_state: delivered`

Nao bloqueado. Toca exclusivamente `apps/web/src/features/**` e pode correr em paralelo com WS-11,
WS-12 e WS-30, que nao tocam `apps/`.

## Resultado pratico

Tres paginas hoje concentram 2.333 linhas com state machine, derivacao de dados, formatacao e
apresentacao no mesmo arquivo. Depois desta entrega, cada pagina tem a logica de dados num modulo
testavel sem renderizar DOM, e a apresentacao em componentes que caem no orcamento de 500 linhas.

O resultado observavel e nulo: mesma UI, mesmos textos, mesmos roles ARIA, mesmos data-attributes,
mesma suite verde. O ganho e estrutural.

## Snapshot inicial

Medido em 2026-07-24.

| Arquivo | Linhas | Forma atual |
| --- | --- | --- |
| `features/observability/ObservabilityPage.tsx` | 918 | 2 componentes exportados + 12 locais; formatadores e mapas de status soltos no topo |
| `features/observability/observabilityModel.ts` | 310 | ✅ o padrao a seguir: modulo puro, sem JSX e sem hooks |
| `features/laboratory/LaboratoryPage.tsx` | 818 | 1 componente monolitico com 11 `useState`, 4 `useRef` e toda a state machine da demo |
| `features/create/CreatePage.tsx` | 597 | 1 componente com wizard de 4 etapas, 7 `useState`, mutation e classificacao de erro |

`observabilityModel.ts` ja estabelece a convencao: um modulo `*Model.ts` por feature com tipos de
search-state, constantes de dominio e funcoes puras de filtro, ordenacao e derivacao. `LaboratoryPage`
tem `DemoLaboratoryAdapter.ts` colocado, mas nenhuma logica de UI extraida. `CreatePage` nao tem
modulo companheiro nenhum.

### Duplicacao entre paginas

Quatro conceitos existem tres vezes, com implementacoes independentes:

- **badge de status:** `StatusMark` + `statusTone` + `statusLabels` (Observability), `ToolStatus`
  (Laboratory), `AdmissionBadge` + `admissionCopy` (Create). Apenas Create delega ao `StatusIndicator`
  de `ui/primitives.tsx`, que ja suporta cinco tones.
- **estado vazio, carregando e erro:** `ui/primitives.tsx` ja exporta `LoadingState`, `EmptyState` e
  `ErrorState`, e nenhuma das tres paginas os usa. Observability reimplementa `PageState` e
  `ListLoadingState` localmente.
- **classificacao de erro para exibicao:** `classifyFailure` por substring de mensagem (Create),
  ternario `instanceof TypeError` inline (Observability), `error instanceof Error ? ... : ...`
  (Laboratory).
- **popover dispensavel:** `ComposerMenu` (Laboratory) implementa combobox acessivel completo com
  roving focus, outside-click, Escape e Tab; o "mais filtros" de Observability reimplementa uma versao
  simples do mesmo padrao.

## Dependencias e ownership de paths

Pode editar:

- `apps/web/src/features/observability/**`, `laboratory/**` e `create/**`;
- `apps/web/src/ui/primitives.tsx`, apenas para ADICIONAR o que a consolidacao exigir, nunca para
  mudar a assinatura de um primitive que outra pagina ja consome;
- `code-budget.toml`, apenas para REMOVER entradas de baseline que a extracao tornou obsoletas.

Nao pode editar:

- `apps/web/src/generated/contracts.ts`, que e gerado;
- `apps/web/src/api/client.ts` e `apps/web/src/data/{contracts,adapters}.ts` — as interfaces de
  adapter injetadas por prop nao mudam nesta entrega;
- `apps/desktop/**`;
- nada em `src/evidrun/`.

## Invariantes que nao podem ser relaxadas

- **Nenhuma mudanca observavel de UI.** Mesmos textos, roles, `aria-label`, `data-*` e ordem de
  elementos. Os testes existentes renderizam pelo componente exportado da pagina e nao importam
  simbolos internos, logo a extracao para arquivos-satelite nao quebra import de teste — mas tambem
  nao autoriza mudar o que eles observam.
- **Renderer nunca importa `electron`, `node:*` ou binding nativo** (AGENTS.md).
- **Nenhuma afirmacao factual nova.** Laboratory continua sendo demo mockada e diz isso; Create
  continua marcando "Integracao pendente" onde a integracao esta pendente. Extrair codigo nao promove
  capacidade de UI.
- **CSS fica onde esta.** `*.css` por feature nao e objeto desta entrega.

## Loop de trabalho

1. **Descobrir.** Rode `pnpm test:web` e registre a lista de testes verdes como baseline. Sao 22
   testes nas tres paginas.
2. **Consolidar primeiro o que ja existe.** Antes de extrair, troque `PageState` e `ListLoadingState`
   pelos `LoadingState`/`EmptyState`/`ErrorState` de `primitives.tsx`, e unifique os tres badges de
   status em torno de `StatusIndicator`. Isso remove codigo em vez de mover.
3. **Extrair Observability.** Mover formatadores e mapas de status para `observabilityModel.ts`;
   separar cada painel (`RunList`, `RunDetailPanel`, `TracePanel`, `EvaluationPanel`, `EvidencePanel`,
   `ExecutionPanel`) em arquivo proprio; extrair as queries, o stream SSE e os filtros para
   `useObservabilityWorkspace.ts`.
4. **Extrair Laboratory.** A state machine de fases (`empty → ready → submitting → active → stopping →
   completed/cancelled/failed/unavailable`) vira `useLaboratoryDemo(adapter)`; `ComposerMenu` e
   `AuditActivity` viram arquivos proprios; constantes e tipos vao para `laboratoryModel.ts`.
5. **Extrair Create.** Tipos, `initialStudy`, `admissionCopy`, `resultLink` e `classifyFailure` vao
   para `createModel.ts`; a state machine do wizard e a mutation viram `useStudyDraft.ts`;
   `StudyCollectionEditor` vira arquivo proprio.
6. **Atacar.** Depois de cada extracao, confirme que o guard sincrono de duplo submit de Laboratory
   (`submitLockRef`) e o de Create (`submissionInFlight` + debounce de 150 ms) continuam bloqueando; o
   cap de 160 px do textarea continua; o roving focus de tabs e de menu continua; e a rejeicao por
   `evaluationDisclosure === "pre_run"` continua aparecendo em Create.
7. **Reparar.** Qualquer teste que precise mudar para passar e sinal de regressao, nao de progresso.

## Condicoes de parada e escalacao

Pare e escale se:

- consolidar um badge exigir mudar a assinatura de um primitive que outra pagina consome;
- a extracao de um hook exigir mudar a interface de adapter em `data/contracts.ts`;
- um teste existente comecar a falhar de forma que so passe com mudanca de texto ou de role.

## Testes focais e gates

Focais: `ObservabilityPage.test.tsx` (7 testes), `LaboratoryPage.test.tsx` (9),
`CreatePage.test.tsx` (6), e `router.test.ts`.

Gates: `pnpm typecheck:web`, `pnpm test:web`, `pnpm build` e
`uv run python scripts/check_code_budget.py`.

## Handoff

Entregue base SHA, head SHA e branch; os arquivos criados por feature com contagem de linhas; quais
componentes locais foram substituidos por primitives em vez de movidos; as entradas de `[baseline]`
removidas de `code-budget.toml`; e a confirmacao explicita de que nenhum teste foi alterado para
passar.
