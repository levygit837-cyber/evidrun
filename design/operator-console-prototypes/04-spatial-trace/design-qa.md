# Design QA: Spatial Trace

Data: 2026-07-23  
Workspace: `design/operator-console-prototypes/04-spatial-trace`  
URL auditada: `http://localhost:4304`  
Modo de dados: stub local, deterministico e nao canonico

## Resultado exato

**APROVADO PARA O ESCOPO DO PROTOTIPO ISOLADO.**

O resultado esta sustentado por renderizacao e interacao em Chrome real, capturas desktop e mobile inspecionadas, 10 testes de comportamento, 4 testes do empacotamento Sites e build de producao concluido. Nao houve deploy ou publicacao.

Esta aprovacao nao valida backend real, persistencia canonica, autoridade humana, integracao de Workspace, portabilidade ou replay de bundle, compatibilidade Safari/WebKit nem conformidade WCAG completa.

## Design Read aplicado

- Publico: pesquisadores tecnicos e operadores de experimentos.
- Tarefa: atravessar Project, Study, Admission, Run e evidencia sem perder o contexto.
- Linguagem visual: evidencia operacional espacial, fria, verificavel e compacta.
- Assinatura: um traco continuo do workflow, com records posicionados como estados e nao como uma grade de dashboard generico.
- Paleta: porcelana fria, charcoal, prata, smoke e um unico accent vermilion.
- Tipografia: sans funcional para leitura e mono apenas para IDs, eventos e valores tecnicos.
- `DESIGN_VARIANCE=7`, `MOTION_INTENSITY=5`, `VISUAL_DENSITY=6`.

O uso material de `design-taste-frontend` manteve hierarquia editorial, bordas moderadas, motion curto e radius contido. A auditoria de Product Design orientou a verificacao completa do fluxo e levou a duas correcoes P2 antes da recaptura final.

## Escopo renderizado e exercitado

1. **Lab. Saude: boa.** O primeiro viewport comunica Project, Study ativa, proxima acao, traco e entrada do Chat.
2. **Projects. Saude: boa.** Selecao sem reload, criacao de draft, validacao inline, autofocus, Escape e contencao de foco foram exercitados.
3. **Study. Saude: boa.** A composicao `scenario x variants x repetitions` e as superficies distintas de StudyRevision e RunSpec foram verificadas.
4. **Admission. Saude: boa.** Admission rejeitada bloqueia enqueue; valores solicitado e suportado aparecem; a correcao cria uma revisao local nova sem reescrever o record anterior.
5. **Runs. Saude: boa.** O browser exibiu `queued -> preparing -> running -> evaluating -> completed`, com Job e attempt como filhos operacionais.
6. **Evidence inspector. Saude: boa.** Bundle `references_only`, `portable=false`, `replayable=false` e a limitacao do digest de SubjectEnvelope permanecem explicitos.
7. **Chat adaptativo. Saude: boa.** Enter, Shift+Enter, estados do Agent, blocos observaveis e snaps explicitos funcionaram.
8. **Persistencia e history. Saude: boa.** Thread e rota foram preservados ao navegar e usar o historico do browser.
9. **Mobile. Saude: boa.** O rail vira bottom navigation e o Chat abre como bottom sheet sem cobrir a navegacao.

## Evidencia visual inspecionada

| Captura | Estado verificado |
| --- | --- |
| `qa/screenshots/01-lab-desktop.jpg` | Lab desktop e contexto inicial |
| `qa/screenshots/02-projects-desktop.jpg` | Projects apos as correcoes P2 |
| `qa/screenshots/03-study-admission-desktop.jpg` | Study e Admission gating |
| `qa/screenshots/04-admission-correction-desktop.jpg` | Novo draft de correcao local |
| `qa/screenshots/05-runs-completed-desktop.jpg` | Run terminal completada |
| `qa/screenshots/06-runs-evidence-desktop.jpg` | Evidence inspector e bundle limitado |
| `qa/screenshots/07-chat-agent-desktop.jpg` | Blocos e estado final do Agent |
| `qa/screenshots/08-lab-mobile.jpg` | Lab mobile e bottom navigation |
| `qa/screenshots/09-study-mobile.jpg` | Study e Admission em reflow mobile |
| `qa/screenshots/10-chat-mobile.jpg` | Chat como bottom sheet mobile |

O viewport de layout foi verificado em 1440 x 660 e 390 x 660. A API de screenshot salvou algumas superficies em 1425 x 653 e 375 x 635; a auditoria visual considerou as dimensoes realmente salvas. O DOM reportou ausencia de overflow horizontal nos dois viewports.

## Achados reparados

- **P2: indices decorativos `01`, `02`, `03` em Projects.** Removidos porque acrescentavam informacao ficticia.
- **P2: conteudo comprimido contra o accent lateral apos a remocao.** Padding interno corrigido e `02-projects-desktop.jpg` recapturado.

Estado final da auditoria: nenhum P0, P1 ou P2 aberto dentro dos estados e viewports capturados. P3 nao foi perseguido neste encerramento.

## Verificacao automatizada final

```text
npm run build
  PASS - Vite 6.4.2, 4982 modulos transformados
  PASS - dist/client/index.html
  PASS - CSS 48.42 kB, gzip 10.25 kB
  PASS - JS 462.97 kB, gzip 138.18 kB
  PASS - arquivos de Sites preparados

npm test
  PASS - 1 arquivo
  PASS - 10 testes

npm run test:sites
  PASS - 4 testes
  FAIL - 0

scans estaticos
  PASS - sem em dash ou en dash em source, HTML e QA
  PASS - sem Lucide, emoji ou fixture CRL externa
  PASS - sem referencia a sibling prototype
```

Os testes cobrem navegacao e history, criacao de Project, Admission gating e correcao, sequencia da Run, eventos permitidos, blocos do Agent, snaps explicitos do Chat e o preview/aplicacao do grip apos aproximadamente 350 ms.

## Fix verification

A revisao independente registrada em `independent-qa.md` encontrou dois P1 e dois P2 no snapshot anterior. Os quatro foram corrigidos e repetidos em testes automatizados e em uma nova sessao Chrome contra o estado final.

| Finding | Correcao | Prova final |
| --- | --- | --- |
| P1-01, records de outro Project em Study/Runs | A Study stub agora declara `projectId` explicito. `App` resolve o vinculo pelo Project selecionado e Study/Runs falham fechado quando ele nao existe. Context inspector e CTA do Lab seguem a mesma fronteira. | Context Drift Review, Tool Permission Audit e um Project novo nao mostram `stub-revision-07`, enqueue, `stub-run-evidence-first`, Start Run ou bundle. Retrieval Quality continua mostrando seus records. Capturas 11 e 12. |
| P1-02, novo Project herdava StudyRevision no traco | `ProjectsView` sincroniza `traceStage` sempre que `selectedProject.id` ou `selectedProject.currentStage` muda. | A criacao de Citation Boundary QA resultou em um unico `aria-current=step` em `Intento`, alinhado a `currentStage=intent` e a proxima acao. Captura 13. |
| P2-01, listbox sem teclado | O switcher usa foco roving entre options e implementa ArrowDown, ArrowUp, Home, End, Enter, Space, Escape e retorno de foco ao gatilho. | Chrome confirmou foco inicial na option selecionada, troca por setas, selecao por Enter e Space, fechamento por Escape e `aria-expanded=false` com foco restaurado. |
| P2-02, composer perdia foco | O textarea fica `readOnly` durante a atividade em vez de `disabled`, e `send` restaura o foco no composer. | Chrome confirmou `activeElement.id=lab-agent-composer`, `bodyFocused=false`, `readOnly=true` durante a atividade e `readOnly=false` apos o terminal. O proximo Tab foi para o grip do Chat, nao para o skip link. Captura 14. |

Evidencia browser fresca:

- `qa/screenshots/11-project-scope-study.png`
- `qa/screenshots/12-project-scope-runs.png`
- `qa/screenshots/13-new-project-intent-trace.png`
- `qa/screenshots/14-chat-focus-retained.png`

Resultado dos gates depois das correcoes:

```text
npm run build
  PASS - Vite 6.4.2, 4982 modulos transformados
  PASS - CSS 48.42 kB, gzip 10.25 kB
  PASS - JS 462.97 kB, gzip 138.18 kB

npm test
  PASS - 1 arquivo
  PASS - 10 testes

npm run test:sites
  PASS - 4 testes
  FAIL - 0
```

Os testes novos cobrem todos os Projects seed, um Project criado sem records, ausencia de records cruzados, sincronizacao do traco, teclado completo do switcher e foco durante e depois dos terminais de sucesso e falha. A sessao Chrome fresca usou viewport 1427 x 661 e nao registrou erro ou warning de aplicacao. Estado final desta verificacao: nenhum P0, P1 ou P2 aberto no escopo reparado.

## Acessibilidade observada

- HTML semantico, headings, regions, articles, description lists, dialog e labels visiveis.
- Foco visivel e operacoes centrais disponiveis por teclado.
- `aria-current`, `aria-pressed`, `aria-expanded`, `aria-live`, erros com `role=alert` e nomes acessiveis coerentes com o estado.
- `prefers-reduced-motion` desativa animacoes e Motion recebe fallback estatico.
- Active, disabled e success nao dependem apenas de cor.
- Logs de erro e warning do browser permaneceram vazios durante o fluxo auditado.

## Limites remanescentes

- Nao houve teste com leitor de tela, zoom de 200%, alto contraste do sistema ou dispositivo fisico com touch.
- O in-app Browser nao estava disponivel; a sessao usou Chrome real e nao cobriu Safari/WebKit.
- Todos os records, eventos e tool blocks sao stubs locais. Nenhuma credencial, provider real, chamada externa ou evidencia canonica foi usada.
- Nenhum `HumanAttestationRecord` foi criado e nenhuma acao e apresentada como autoridade humana.
- O bundle demonstra referencias e verificacoes da UI, nao blobs, grants, restore, replay ou estado privado recuperavel.

O roteiro deterministico reproduzivel esta em `qa/flow.yaml`; a auditoria combinada de UX e acessibilidade esta em `qa/manual-audit.md`.
