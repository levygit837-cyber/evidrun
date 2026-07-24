# Design QA

## Superfície e método

- Protótipo: `design/operator-console-prototypes/05-evidence-ledger-open-canvas`
- Browser controlado: extensão do Chrome
- Sessão: `EvidRun prototype QA`
- URL local verificada: `http://127.0.0.1:4305`
- Estados: dados determinísticos, sem serviços externos
- Critério de aprovação: browser evidence e zero achado acionável P0, P1 ou P2

Todas as seis referências foram abertas e inspecionadas em resolução original antes da implementação. O estado Lab também foi recapturado em 1586 x 992 e colocado junto da referência no mesmo quadro de comparação.

## Referências

| Estado de referência | Fonte | Dimensão |
| --- | --- | --- |
| Lab, primeiro uso | `reference/01-home-first-use.png` | 1586 x 992 |
| Lab, Chat ativo | `reference/02-home-active-chat.png` | 1586 x 992 |
| Projects | `reference/03-projects.png` | 1586 x 992 |
| Study e Admission | `reference/04-studies-admission.png` | 1586 x 992 |
| Run concluída | `reference/05-run-completed.png` | 1586 x 992 |
| Run live com Chat | `reference/06-run-live-chat.png` | 1586 x 992 |

## Capturas da implementação

| Estado | Evidência | Viewport |
| --- | --- | --- |
| Lab, primeiro uso | `qa/screenshots/01-lab-first-use-desktop-final.png` | 1440 x 940 |
| Lab, retorno | `qa/screenshots/01b-lab-return-desktop.png` | 1440 x 940 |
| Projects | `qa/screenshots/02-projects-desktop.png` | 1440 x 940 |
| Study rejeitada | `qa/screenshots/03-study-rejected-desktop.png` | 1440 x 940 |
| Study admitida | `qa/screenshots/03b-study-admitted-desktop.png` | 1440 x 940 |
| Run concluída | `qa/screenshots/04-run-completed-desktop.png` | 1440 x 940 |
| Run live | `qa/screenshots/05-run-live-desktop.png` | 1440 x 940 |
| Run live com Chat | `qa/screenshots/06-run-live-chat-desktop.png` | 1440 x 940 |
| Lab, tablet | `qa/screenshots/07-lab-return-tablet.png` | 834 x 1112 |
| Study, tablet final | `qa/screenshots/08-study-tablet.png` | 834 x 1112 |
| Lab, mobile | `qa/screenshots/09-lab-mobile.png` | 390 x 844 |
| Chat, mobile | `qa/screenshots/10-chat-mobile.png` | 390 x 844 |
| Lab para comparação exata | `qa/screenshots/compare-01-lab-implementation-1586x992.png` | 1586 x 992 |
| Referência e implementação juntas | `qa/screenshots/compare-01-lab-side-by-side.png` | quadro 1600 x 560, duas fontes 1586 x 992 |
| Projects corrigido, viewport | `qa/screenshots/fix-01-projects-workflow-desktop.png` | CSS 1440 x 940, raster 1425 x 930, density 1 |
| Projects corrigido, fluxo completo | `qa/screenshots/fix-01b-projects-workflow-full.png` | CSS 1440 x 940, full-page 1425 x 1400, density 1 |
| Projects para comparação | `qa/screenshots/fix-01c-projects-implementation-1586x992.png` | CSS 1586 x 992, raster 1571 x 983, density 1 |
| Projects lado a lado | `qa/screenshots/fix-01d-projects-side-by-side.png` | quadro 1600 x 560 |
| Project sem Study vinculada | `qa/screenshots/fix-02-study-scope-lock-desktop.png` | 1440 x 940 |
| Escopo do Chat separado | `qa/screenshots/fix-03-study-scope-chat-desktop.png` | 1440 x 940 |
| Stub Run terminal | `qa/screenshots/fix-04-stub-terminal-desktop.png` | CSS 1440 x 940, raster 1425 x 930, density 1 |
| Diálogo com primeiro erro focado | `qa/screenshots/fix-05-dialog-invalid-focus-desktop.png` | CSS 1440 x 940, raster 1425 x 930, density 1 |

## Leitura lado a lado

Comparação usada: `qa/compare-lab.html`, capturada em `qa/screenshots/compare-01-lab-side-by-side.png`.

Correspondências mantidas:

- shell claro com sidebar estreita, topbar discreto e conteúdo em canvas aberto;
- marca raster derivada da referência, sem SVG artesanal;
- Manrope para conteúdo e IBM Plex Mono para referências técnicas;
- preto azulado, cinza frio e cobalt como linguagem principal;
- composer como ação central, com estado vazio desabilitado;
- fluxo Converse, draft e revisão humana;
- contexto CRL-CTX-002 e distinção entre Chat, SubjectEnvelope e autoridade.

Diferenças deliberadas exigidas pelo brief:

- o protótipo expõe seletor de estado, presets determinísticos e contexto factual adicional para tornar todos os estados testáveis;
- o bloco de referência fica em rail lateral no desktop, deixando a proveniência visível sem apresentá-la como fato universal;
- o Lab inicial usa uma linha de processo editorial em vez de ícones soltos sob o composer;
- a nomenclatura de navegação segue as quatro rotas pedidas no brief.

## Histórico de iteração

| Iteração | Evidência | Achado | Severidade | Correção | Resultado |
| --- | --- | --- | --- | --- | --- |
| 0 | `01-lab-first-use-desktop.png` | `Study & Admission` quebrava e três cartões iguais diluíam o fluxo | P2 | redução de gap e sequência editorial com setas Phosphor | corrigido |
| 1 | captura tablet anterior | Documentação e Configurações colidiam no topbar a 834 px | P1 | utilitários viraram botões de ícone no breakpoint de tablet | corrigido |
| 2 | captura mobile anterior | scroll preservado escondia o título após navegar | P1 | reset de scroll e foco com `preventScroll` em navigate e popstate | corrigido |
| 3 | `08-study-tablet.png`, `09-lab-mobile.png` | reflow, topbar e início de rota íntegros | verificação | sem mudança adicional | aprovado |
| 4 | `compare-01-lab-side-by-side.png` | linguagem visual, densidade e hierarquia coerentes com a referência | verificação | sem mudança adicional | aprovado |
| 5 | QA independente | Project local herdava Study, Runs e contexto CRL | P1 | guards fail-closed, contexto derivado do Project e threads separadas por escopo | corrigido |
| 6 | QA independente | Start Stub Run trocava para ID e ledger canônicos no terminal | P1 | lifecycle, IDs, refs, provenance e Bundle do stub ficaram integralmente `demo:` | corrigido |
| 7 | QA independente | diálogo não continha foco nem focava o primeiro erro | P1 | trap Tab/Shift+Tab, Escape, retorno ao trigger e foco determinístico do erro | corrigido |
| 8 | QA independente | workflow truncava labels e escondia Comparison em scroll horizontal | P2 | sequência vertical em duas colunas, labels quebráveis e convergência no fluxo normal | corrigido |
| 9 | `fix-01d-projects-side-by-side.png`, `fix-02-study-scope-lock-desktop.png`, `fix-04-stub-terminal-desktop.png` | recaptura final após os quatro fixes | verificação | sem mudança adicional | aprovado |

## Fix verification

O snapshot final foi revalidado no Chrome e por uma auditoria independente registrada em `independent-qa.md`.

### 1. Isolamento de Project

- Foi criado `Boundary QA Project` somente em estado React.
- `/study` apresentou `Nenhuma Study vinculada`; `/runs` apresentou `Nenhuma Run vinculada`.
- A UI declara que CRL-CTX-002 permanece uma fixture separada e oferece uma troca explícita para a fixture, sem herdar records.
- O Chat atualizou para `Project / Boundary QA Project · sem Study` e depois `sem Run`.
- Mensagens de um thread CRL não aparecem no thread do novo Project.
- Evidência: `fix-02-study-scope-lock-desktop.png` e `fix-03-study-scope-chat-desktop.png`.

### 2. Lifecycle do Start Stub Run

- O estado terminal permaneceu `demo:run-stub-admitted`, `demo:job-stub-01` e `demo:attempt-01`.
- O ledger terminou em `event:demo-stub-09`, com nove eventos ilustrativos.
- Comparação, RunSpec, AdmissionRecord, SubjectEnvelope digest e Bundle canônicos não aparecem durante o stub.
- O preset Completed continua sendo a única projeção da fixture CRL estável.
- Evidência: `fix-04-stub-terminal-desktop.png`.

### 3. Foco do diálogo

- Shift+Tab a partir do container inicial move para o último controle e Tab no último controle retorna ao primeiro.
- Submit inválido foca `Nome do Project`; após nome válido, o próximo submit inválido foca `Descrição`.
- Escape e fechamento restauram foco ao botão `Criar Project` que abriu o diálogo.
- Evidência: `fix-05-dialog-invalid-focus-desktop.png` e teste automatizado dedicado.

### 4. Workflow de Projects

- Em CSS viewport 1440 x 940, `.workflow-canvas` mediu `clientWidth=853` e `scrollWidth=853`.
- StudyRevision, duas branches, Admissions, Runs, Evaluations e Comparison permanecem legíveis na sequência normal.
- Labels de objeto quebram linha em vez de usar ellipsis; IDs técnicos continuam secundários.
- Comparison é alcançada por scroll vertical normal, sem clipping ou scroll horizontal silencioso.
- Evidência completa: `fix-01b-projects-workflow-full.png`; comparação no mesmo input: `fix-01d-projects-side-by-side.png`.

### Gates após estabilização

- `npm test`: 10 de 10 testes passaram.
- `npm run build`: 4.992 módulos transformados e pacote Sites preparado.
- `npm run test:sites`: 4 de 4 testes passaram.
- Console final: zero warning e zero error.
- `independent-qa.md`: `independent result: passed`, zero P0, P1 e P2.

## Verificações funcionais ligadas ao visual

- Navegação por quatro rotas e histórico atualiza path e contexto do Chat.
- Composer vazio permanece desabilitado; Enter envia e Shift+Enter preserva nova linha.
- O reducer do Agent percorre running e terminal com região viva e restauração de foco.
- Seleção no grafo atualiza inspector; formulário local mostra erros e confirma criação.
- Enqueue só habilita para `decision=admitted` do RunSpec selecionado.
- Run concluída mostra nove eventos e não mostra tools; Run live mostra `read_text` apenas no contexto ilustrativo separado.
- Chat persiste entre rotas, distingue colapsar de fechar e responde a teclado no slider de snaps.
- Documento sem overflow horizontal em 1440, 834 e 390 px; scroll interno é reservado para conteúdo técnico e para o canvas do grafo.
- Console do browser encerrou sem warning ou error.

## Pendências não bloqueantes

- Medição automatizada de contraste e auditoria com leitor de tela real.
- Safari, Firefox, zoom de sistema e dispositivo touch físico.
- Integrações reais de backend, provider, authority adapter, persistência e Bundle permanecem fora do protótipo.

## Resultado final

final result: passed

Browser evidence presente e nenhum achado acionável P0, P1 ou P2 permanece no escopo pedido.
