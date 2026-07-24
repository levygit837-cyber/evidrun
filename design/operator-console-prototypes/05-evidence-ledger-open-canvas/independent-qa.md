# QA independente — Evidence Ledger Open Canvas

## Resultado executivo

**Aprovado no snapshot estabilizado de 23 jul 2026.** Não permanece achado acionável P0, P1 ou P2 no escopo pedido. A validação final cobriu as seis referências visuais, os estados correspondentes, os quatro fluxos de produto, Admission, Agent, Chat, teclado/foco, console e os viewports desktop, tablet e mobile.

Esta foi uma auditoria independente e read-only da implementação. Nenhum arquivo de produto foi alterado por esta QA; este relatório é a única escrita realizada no workspace atribuído.

## Achados bloqueantes

Nenhum.

- P0: 0
- P1: 0
- P2: 0

Durante a revalidação, o worktree recebeu correções em paralelo. Por isso, todos os gates e checks críticos abaixo foram repetidos depois da estabilização, e o resultado se refere somente ao estado final revalidado.

### Regressões críticas revalidadas como encerradas

| Área | Evidência final | Resultado |
| --- | --- | --- |
| Isolamento de Project | No browser, criei `Boundary QA Final`, naveguei para Study e obtive `Nenhuma Study vinculada`; a UI declarou que `CRL-CTX-002` permanece separada. O Chat mostrou `Project / Boundary QA Final · sem Study` e informou que o Project não possui Study, Run ou evidência. O teste automatizado também percorre Study, Chat e Runs sem expor records CRL. Guards explícitos estão em `src/routes/StudyRoute.jsx:55` e `src/routes/RunsRoute.jsx:86`; contexto e escopo do Chat são derivados do Project em `src/App.jsx:19-28` e `src/App.jsx:104`. | encerrada |
| Identidade do Start Stub Run | No browser, o estado terminal permaneceu `demo:run-stub-admitted`, `demo:job-stub-01`, `demo:attempt-01`; o ledger terminou em `event:demo-stub-09` e declarou que nenhum record canônico foi reutilizado. `src/state/runState.js:17-40`, `src/data/mockData.js:173-185` e `src/routes/RunsRoute.jsx:81-185` mantêm lifecycle e evidência ilustrativos separados da fixture capturada. | encerrada |
| Foco do diálogo | Envio vazio focou o primeiro campo inválido, `Nome do Project`, com os dois alertas presentes. O teste final confirmou contenção de Tab/Shift+Tab, Escape e restauração do trigger. O trap e cleanup estão em `src/components/primitives/Modal.jsx:10-51`; o foco de validação está em `src/routes/ProjectsRoute.jsx:59-68`. | encerrada |
| Workflow de Projects | Em 1440 × 940, o canvas mediu `clientWidth=853` e `scrollWidth=853`, sem scroll horizontal interno. StudyRevision, as duas branches, Admissions, Runs, Evaluations e Comparison permanecem na sequência vertical/duas colunas, com inspector separado. A estrutura responsiva está em `src/styles.css:1317-1416`. | encerrada |

## Escopo e método

Foram lidos `INDEPENDENT_QA_PROTOCOL.md`, `BUILD_BRIEF.md`, `design-qa.md`, `qa/manual-audit.md`, `qa/flow.md`, código, estado, dados e testes deste workspace. As skills Product Design `image-to-code` e `audit`, `design-taste-frontend` e Browser orientaram, respectivamente, fidelidade estrutural, auditoria de fluxo, hierarquia/anti-slop e validação no runtime.

Foram inspecionadas visualmente as seis imagens em `reference/` e as capturas já existentes em `qa/screenshots/`. As afirmações de QA anteriores foram tratadas como hipóteses; a aprovação abaixo deriva de inspeção do código, execução dos comandos e browser evidence em `http://localhost:4305/`.

## Gates determinísticos

Os comandos de build e Sites foram executados em uma cópia temporária do snapshot final, com o `node_modules` existente apenas referenciado, para não escrever artefatos adicionais no workspace auditado.

| Gate | Resultado final | Evidência |
| --- | --- | --- |
| `npm test` | passou | 1 arquivo; 10/10 testes; 0 falhas |
| `npm run build` | passou | Vite transformou 4.992 módulos; build de produção concluído; `dist/server/index.js` e `dist/.openai/hosting.json` preparados na cópia temporária |
| `npm run test:sites` | passou | 4/4 testes; asset existente, fallback de rota, bloqueio de fallback para API/write e arquivos de empacotamento |
| Console do browser | passou | somente logs de conexão Vite e aviso informativo do React DevTools; 0 warning e 0 error |

## Cobertura de rotas e interações

| Área | Checks executados | Resultado |
| --- | --- | --- |
| Navegação global | `/`, `/projects`, `/study`, `/runs`; botões desktop e bottom nav; Back de Runs para Study; retorno ao Lab; reset de scroll; exatamente um `main` | passou |
| Lab / Agent | first-use e returning; composer vazio desabilitado; envio realista; cursor customizado acima do input; User, Activity, Tool Call, Tool Result e Agent; `read_text` apenas em contexto autorizado/ilustrativo; estados idle, running, success e failure; foco devolvido ao composer | passou |
| Projects | três Projects stub; busca e switcher; criação local validada; inspector por nó; StudyRevision → duas RunSpecs → Admissions/Runs/Evaluations → Comparison; Workspace separado e integração pendente | passou |
| Study / Admission | seleção e draft de revisão; matriz `scenario × variants × repetitions`; compile preview; head-truncation rejeitado por `unsupported_execution_contract` com enqueue desabilitado; tail-preservation admitido com enqueue habilitado; revisão local volta a bloquear enqueue | passou |
| Runs / Evidence | Completed com nove eventos factuais e sem tools; Failed sem `run.completed`; Live com `tool.called · read_text` explicitamente ilustrativo; Start Stub Run por queued, preparing, running, evaluating e terminal, mantendo IDs/refs `demo:`; job e attempt separados; sem pause/resume; limitações do SubjectEnvelope e Bundle v3 exibidas | passou |
| Chat | dock lateral inicial; thread compacta e ampla; snaps compact/half/tall/full por teclado; collapse, expand e close distintos; thread preservada entre rotas; contexto acompanha Project/Study/Run; mobile como bottom sheet acima da navegação | passou |
| Teclado e foco | skip link recebeu foco visível e levou a `main#main-content`; diálogo conteve foco, focou o primeiro erro, fechou com Escape e restaurou o trigger; composer manteve Shift+Enter e envio por Enter | passou |

## Comparação com as seis referências

| Referência | Estado correspondente verificado | Avaliação |
| --- | --- | --- |
| `01-home-first-use.png` | Lab first-use | Direção preservada: entrada orientada a intenção, sequência operacional e status local legível; a implementação adapta a composição sem perder hierarquia. |
| `02-home-active-agent-chat.png` | Lab ativo + Chat | Direção preservada: ledger incremental e Chat contextual coexistem sem sobrepor navegação; Agent não recebe conteúdo fora do envelope declarado. |
| `03-projects-open-canvas.png` | Projects returning | Relação principal agora cabe sem scroll horizontal interno em desktop; branches e convergência são compreensíveis sem ler IDs; inspector mantém detalhes secundários fora do fluxo. |
| `04-study-admission.png` | Study head rejected e tail admitted | Rejeição e admissão permanecem distinguíveis por decisão, copy e estado do controle, não apenas por cor. |
| `05-run-completed.png` | Run Completed | Nove eventos factuais da fixture, Comparison capturada e Evidence/Bundle reproduzem a intenção com limites explícitos de recomputabilidade, portabilidade e replay. |
| `06-run-live-chat.png` | Live ilustrativa + Chat | Tool Call `read_text` e Chat ficam claramente separados da fixture CRL e se adaptam ao viewport; nenhuma tool é atribuída à história factual capturada. |

As referências foram usadas como direção visual, não como exigência de clonagem literal. As mudanças de composição são coerentes com o brief e não removem hierarquia, affordance ou informação operacional crítica.

## Observações por viewport

### Desktop — 1440 × 940

- Um único `main`; sem overflow horizontal do documento.
- Sidebar, topbar, canvas e Chat não colidem.
- Projects: workflow sem overflow horizontal interno (`853/853`), branches completas e Comparison alcançável por scroll vertical normal.
- Chat compacto, half, tall e full permaneceu dentro do viewport; collapse e close não apagaram a thread.

### Tablet — 834 × 1112

- Um único `main`; sem overflow horizontal.
- Sidebar permaneceu legível e mobile nav permaneceu oculta.
- Em Study, a topbar terminou em `y=64` e o H1 começou em `y=114`, sem sobreposição.
- Labels de navegação e controles críticos permaneceram acessíveis.

### Mobile — 390 × 844

- Um único `main`; sem overflow horizontal; route change terminou em `scrollY=0`.
- Sidebar ficou oculta e a bottom nav ficou visível; seu topo foi medido em `y=776` para `innerHeight=844`.
- Chat se comportou como bottom sheet, coexistiu com a bottom nav e conservou collapse/close.
- Títulos, ações e conteúdo operacional passaram a fluxo vertical sem mistura entre rotas.

## Qualidade de código e fidelidade de domínio

- `App.jsx` coordena routing e estado compartilhado, enquanto Lab, Projects, Study, Runs, Chat, shell e primitives permanecem em componentes separados; não há App monolítico.
- Timers do Chat/Agent, progressão da Run e `requestAnimationFrame` do modal têm cleanup.
- State transitions do Start Stub Run são determinísticas e testadas; IDs canônicos e ilustrativos não são misturados.
- Admission rejeitada não habilita enqueue; nenhuma Run nova é alegada antes de Admission admitida para o RunSpec exibido.
- Completed preserva os nove eventos factuais da fixture; Live e Stub usam somente refs `demo:` e avisos explícitos.
- `read_text` aparece somente no fluxo ilustrativo autorizado. Não há tools na fixture CRL concluída.
- Não há controles ativos de pause/resume, exposição de private reasoning ou promessa de blobs, grants, restore, replay ou portabilidade.
- Project, Study, Run, Comparison, Agent, Chat e Workspace mantêm fronteiras operacionais distintas; Project local sem records falha fechado para Study/Runs e não herda evidência CRL.
- Renderer/source não importa `electron`, `node:*`, provider real ou workspace irmão; não foram encontrados secrets, tokens, API keys ou chamadas reais de provider.
- Iconografia usa Phosphor; a Comparison usa visual de barras, sem balança metafórica; não há emoji decorativo ou SVG improvisado.
- `prefers-reduced-motion` e foco visível estão implementados; nomes acessíveis e controles semânticos foram confirmados no DOM do browser.

## Limites da evidência

- O browser in-app não estava disponível; a validação visual/interativa usou Chrome, conforme o fallback documentado da skill Browser.
- O preflight de user context não retornou contexto conectado; nenhuma informação externa foi usada como evidência. A conclusão é exclusivamente do workspace e do runtime local.
- O gesto físico de long press por aproximadamente 350 ms não pôde ser reproduzido com fidelidade suficiente pela automação. Preview e snap foram verificados por controles de teclado e pelos estados expostos; este limite não revelou um P0/P1/P2.
- Não houve teste com leitor de tela real, Safari/WebKit, dispositivo físico/touch real, rede real, backend real, provider real ou deploy.
- Capturas novas foram inspecionadas em sessão e não persistidas, respeitando a regra de escrever somente este relatório. As capturas existentes do workspace continuam como evidência em disco.

## Conclusão

Os gates determinísticos passam, o browser evidencia os fluxos e viewports pedidos, os quatro riscos críticos observados durante a execução foram encerrados e revalidados, e não permanece diferença P0/P1/P2 que prejudique hierarquia, compreensão, autoridade, proveniência ou uso do protótipo local.

independent result: passed
