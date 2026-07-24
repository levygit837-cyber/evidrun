# Design QA — frontend Electron multipágina

Data: 2026-07-24

Branch: `task/electron-frontend`

Referências congeladas: Laboratory `candidate-01` e Observability `observability-classic`.
`run-forensics-classic` permaneceu fora desta entrega.

## Método

- As referências HTML e a implementação foram servidas por `localhost` e inspecionadas no
  navegador interno do Codex.
- Referência e implementação foram comparadas juntas, no mesmo input, e não apenas por capturas
  isoladas.
- Os viewports obrigatórios foram exercitados em 1440×940, 1100×760 e 880×650.
- Foram auditados os estados inicial, preenchido, ativo, sucesso, falha/rejeição e
  backend/capability indisponível, conforme aplicável a cada página.
- Cada página recebeu auditoria UI/UX read-only, aplicação de correções e reauditoria. Depois das
  três páginas, uma auditoria cross-page validou shell, semântica, responsividade e claims.
- As imagens do navegador interno excluem o chrome externo; as capturas finais compactas possuem
  raster real de 880×650 e a captura intermediária de Create possui raster real de 1100×760.

Diretório das evidências:

`/Users/apple/.codex/visualizations/2026/07/24/019f955e-0b16-7860-a248-1ba1f4c6e4f4`

## Laboratory — `passed`

Estados verificados: composição central, primeiro envio, resposta ativa, atividade auditável,
conclusão, falha/retry, cancelamento, capability indisponível e reduced motion.

Correções do ciclo de auditoria:

- eliminados scroll e contenção incorretos do composer;
- reforçados nomes e limites de Demo para que nenhuma atividade pareça vir do backend;
- ajustados densidade, quebra de conteúdo e estados de tool activity;
- corrigido contraste dos chevrons e ações contextuais.

Evidências principais:

- `evidrun-source/laboratory-1440x940-exact.jpg`;
- `evidrun-implementation/laboratory-fixed-1440x940.jpg`;
- `evidrun-implementation/laboratory-tool-completed-1440x940.jpg`;
- `evidrun-implementation/laboratory-failed-1440x940.jpg`;
- `laboratory-comparison-1440x940-v2-stacked.jpg`;
- `evidrun-implementation/laboratory-crosspage-880x650.jpg`.

Resultado final da reauditoria: nenhum P0, P1 ou P2.

## Create — `passed`

Estados verificados: draft local, navegação Study → RunSpecs → Admission → Runs, preservação de
campos, stale por alteração real, operação pendente, sucesso do bootstrap canônico, falha/retry e
boundaries `integration_pending`.

Correções do ciclo de auditoria:

- separada a edição/navegação do ato que realmente invalida outputs posteriores;
- reforçada a distinção entre preview Demo e fixture canônica não humana;
- removidos rótulos redundantes e elevada a legibilidade dos dados importantes;
- mantido um único CTA sticky, sem duplo submit.

Evidências principais:

- `evidrun-source/create-1440x940-exact.jpg`;
- `evidrun-implementation/create-v3-1440x940.jpg`;
- `evidrun-implementation/create-final-1100x760.jpg`;
- `evidrun-implementation/create-crosspage-880x650.jpg`;
- `create-comparison-1440x940-v3-stacked.jpg`.

Resultado final da reauditoria: nenhum P0, P1 ou P2.

## Observability — `passed`

Estados verificados: loading, lista, resultado filtrado vazio, Run selecionada, split desktop,
substituição lista/detalhe em compacto, Trace, Evaluation, Evidence, Execution, stream terminal,
backend desconectado e conteúdo indisponível.

Correções do ciclo de auditoria:

- removido overflow horizontal de lista e detalhe;
- preservados e exibidos `digest`, `media_type` e `classification` quando um `ArtifactRef` completo
  existe, sem conceder acesso ao conteúdo;
- elevados facts, eventos, tabs e valores relevantes para 12–13 px;
- substituído o rótulo incorreto da lista por `Lista de Runs`;
- completado o ciclo de foco do popover de filtros com `aria-controls`, Escape, retorno de foco e
  fechamento por clique externo.

Evidências principais:

- `evidrun-source/observability-1440x940-exact.jpg`;
- `evidrun-implementation/observability-final-filled-1440x940.jpg`;
- `evidrun-implementation/observability-crosspage-880x650.jpg`;
- `observability-comparison-1440x940-v4-stacked.jpg`.

Resultado final da reauditoria: nenhum P0, P1 ou P2.

## Auditoria cross-page — `passed`

Correções finais compartilhadas:

- links do sidebar compacto receberam nome acessível e tooltip visível em hover/foco;
- `StatusIndicator` passou a 12 px e recebeu cores com contraste textual maior que 4,5:1;
- o falso seletor de projeto virou informação estática;
- o topbar passou a reutilizar o ícone Lucide da rota;
- a evidência inválida de Create foi recapturada em 1100×760 real.

A captura `evidrun-implementation/crosspage-tooltip-focus-880x650.jpg` comprova nome acessível,
focus ring e tooltip de 12 px sem ampliar a largura do documento.

Resultado final da reauditoria cross-page: nenhum P0, P1 ou P2. A inspeção visual não equivale a
uma certificação WCAG completa com tecnologia assistiva real.

## Corredor real verificado

No navegador interno, com o backend local conectado, foi executado o seguinte corredor:

1. abrir Create;
2. avançar por RunSpecs e Admission;
3. executar `CRL-CTX-002` pelo `/api/v1/demo/bootstrap`;
4. receber somente as duas Runs retornadas pelo backend;
5. abrir a Run baseline em Observability;
6. inspecionar Trace, Evaluation, Evidence e Execution.

Runs observadas:

- baseline: `run_019f95a0-a3e1-74a8-840e-620b44d3e987`;
- candidate: `run_019f95a0-a566-718d-a1b2-03f3eed9bd23`.

O corredor foi repetido dentro da janela Electron real com um `--user-data-dir` temporário e
isolado, conforme a regra de QA por worktree. O renderer iniciou em `#/laboratory`, reportou
`Backend ready`, navegou para Create e retornou:

- baseline: `run_019f95c8-779a-766e-b6a6-c8f781cae204`;
- candidate: `run_019f95c8-780a-7453-9cd7-bff27d5d28b8`.

Essa baseline foi aberta em Observability e as quatro tabs foram exercitadas no renderer Electron.
Todas reportaram `horizontalOverflow: false`, e a coleta final retornou `rendererErrors: []`.

A interface manteve os limites factuais: fixture `repository_fixture`, Evidence sem grant de
acesso e Bundle v3 `references_only`, não portátil e não replayable.

Uma primeira abertura contra o diretório histórico padrão de Application Support encontrou uma
migração SQLite antiga com foreign-key inconsistente. Nenhum dado foi apagado manualmente e não foi
tentada correção destrutiva para contornar esse estado. O gate desta fatia usa o diretório de QA
isolado exigido pelo plano; a recuperação/migração do banco histórico permanece uma questão
separada do frontend.

## Resultado

| Área | Resultado |
| --- | --- |
| Laboratory | `passed` |
| Create | `passed` |
| Observability | `passed` |
| Consistência cross-page | `passed` |
| Overflow horizontal nos três viewports | `passed` |
| Navegação e foco principal por teclado | `passed` |
| Claims de Demo, autoridade, artifacts e replay | `passed` |

Gate visual final: **passed**.
