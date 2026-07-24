# QA independente — Command Deck

Data: 23 de julho de 2026  
Workspace avaliado: `design/operator-console-prototypes/03-command-deck`  
Escopo: revisão independente, read-only, do protótipo React conforme `INDEPENDENT_QA_PROTOCOL.md`.

## Findings

Não permanece finding P0, P1 ou P2 no estado final revisado. Três problemas observados no primeiro passe — lifecycle terminal inconsistente em Runs, foco incompleto no modal de Project e legibilidade/navegação no breakpoint de tablet — foram corrigidos concorrentemente durante a auditoria. Eles foram retirados da lista de blockers somente após reinspeção do código final e repetição dos gates determinísticos.

Não expandi a rodada para findings P3 depois do pedido de encerramento. Isso não transforma detalhes cosméticos não investigados em garantia de ausência.

## Verificação das correções que eliminaram blockers

| Área | Evidência do problema no primeiro passe | Estado final verificado |
| --- | --- | --- |
| Lifecycle de Runs | Uma versão intermediária permitia discrepância entre fase terminal, outcome, evidence e botão Start | `src/routes/RunsRoute.jsx:25-53` agora representa failed como Terminal sem inventar Evaluating; `src/routes/RunsRoute.jsx:75-85` atualiza fase terminal e outcome no mesmo callback. Testes cobrem terminal completed, failed e commit atômico |
| Modal de Project | `Shift+Tab` escapava de `[role="dialog"][aria-modal="true"]` e Escape não devolvia foco ao acionador | `src/routes/ProjectsRoute.jsx:15-52` contém o foco no modal; `src/routes/ProjectsRoute.jsx:135-144` restaura o botão “Novo Project”. Teste final cobre reverse trap e retorno por Escape |
| Navegação em tablet | Em `834 × 1112`, o primeiro passe e o screenshot aceito mostravam apenas ícones | A regra que ocultava `.command-nav__link span` foi removida. `src/styles.css:2057-2074` mantém label, gap e tamanho explícitos abaixo de `900px` |
| Tipografia operacional | Chat, tool results, composer e event track usavam corpos de `9–12px` | O CSS final usa `14px` para event labels/IDs (`src/styles.css:1261-1277`), mensagens/Activity (`src/styles.css:1730-1795`), tool call/result (`src/styles.css:1832-1865`) e composer (`src/styles.css:1924-1934`) |

## Gates determinísticos

Os três comandos foram repetidos depois das alterações concorrentes finais.

| Gate | Resultado final | Evidência objetiva |
| --- | --- | --- |
| `npm test` | Passou | 1/1 arquivo; 10/10 testes; 0 falhas |
| `npm run build` | Passou | Vite 6.4.2; 4.982 módulos transformados; build e preparo de Sites concluídos |
| `npm run test:sites` | Passou | 4/4 testes; 0 falhas, 0 cancelados, 0 ignorados |
| Console do navegador | Passou no passe runtime | 0 mensagens `warn` e 0 mensagens `error` na sessão auditada |
| Landmarks e rotas | Passou no passe runtime | Exatamente um `main`; `#/lab`, `#/projects`, `#/study` e `#/runs` alcançáveis |

Build verde não foi usado como substituto para inspeção visual ou de interação.

## Cobertura de rotas e interações

| Rota | Estados e interações exercitados | Resultado |
| --- | --- | --- |
| `#/lab` | Dock e abertura do Chat; layouts compact/half/tall/full; colapso e reabertura; Enter, `Shift+Enter`, vazio, sucesso e falha local; spinner; Activity; Tool Call/Result; retorno de foco; draft e thread preservados entre rotas | Passou |
| `#/projects` | Troca de Project; inspeção de etapa futura; abertura do diálogo; validação de campos; criação local; Escape e navegação por teclado | Fluxo passou; correção final de trap/retorno de foco confirmada por código e teste automatizado |
| `#/study` | Project bloqueado; demonstrações Admitida e Rejeitada; duas admissões; motivos de rejeição; enqueue habilitado somente após admissão | Passou |
| `#/runs` | Identidades separadas de Run/job/attempt/Admission; ready/loading/completed/failed; timeline; evidence; comparação sem declarar vencedor | Fluxo passou; semântica terminal final confirmada por código e três testes focados |
| Navegação global | Lab → Projects → Study → Runs, Back do navegador e retorno ao Lab | Passou; uma única rota e um único `main` por vez |
| Chat entre rotas | Draft não enviado e thread preservados ao trocar de rota | Passou |

O SubjectEnvelope observado explicita a allowlist e mantém Chat/hidden grader fora do envelope. As cópias de comparação, bundle e evidência não prometeram adjudicação, replay, blobs ou portabilidade não demonstrados.

## Desktop, tablet e mobile

| Faixa | Observação |
| --- | --- |
| Desktop `1440 × 940` | Hierarquia densa e clara; console e Chat sem overflow horizontal; painel expandido e quatro snap states funcionaram; foco visível no envio por teclado |
| Tablet `834 × 1112` | Primeiro passe sem overflow horizontal. O CSS final preserva os rótulos visíveis da navegação em vez de reduzi-la a icon-only |
| Mobile `390 × 844` | Quatro rotas sem overflow horizontal; navegação inferior presente; Chat em bottom sheet acima da nav; colapso preservou dock e nav |

O sistema visual é coerente: grafite/prata com um único acento cobalto, densidade de console B2B consistente e ícones Phosphor em vez de emoji ou SVG artesanal. Não apareceu verde para estado operacional/de banco, nem ícone de balança para comparação. A responsividade observada não dependeu de scroll horizontal.

## Observações de qualidade de código

- `App.jsx` permanece pequeno e delega rotas, shell, Chat e UI para componentes separados; não há componente monolítico dominante.
- Os dados de demonstração são locais e determinísticos. Não encontrei segredo, token, chamada a provider real nem import de workspace irmão no código revisado.
- Timers do Runs e do stub do Lab, bem como listeners de teclado/pointer do Chat, têm cleanup. O gesto contínuo usa refs e não apresentou atualização React de alta frequência como motor visual.
- Controles principais são elementos semânticos com nomes acessíveis. O modal final contém foco e restaura o acionador.
- Keys observadas são estáveis e os estados de erro/vazio/loading/sucesso são explícitos.
- Existe override de `prefers-reduced-motion`; a sessão não demonstrou animação decorativa obrigatória.
- A arquitetura preserva as fronteiras do protótipo: nenhum domínio externo, provider real, credential ou import de variante irmã apareceu no bundle revisado.

## Pontos fortes depois dos findings

- A interface faz o console parecer operacional, não um conjunto genérico de cards: IDs, records, lifecycle, gates e evidence refs têm boa estrutura de informação.
- As fronteiras de autoridade e disclosure são descritas com honestidade; o Lab permanece um stub local e não finge provider, humano ou execução externa.
- Empty/loading/failure/success do Lab são visual e semanticamente distintos, e a falha local não inventa evidência.
- Admission rejeita fechado e expõe os motivos; comparação apresenta records sem declarar vencedor.
- Back/forward, troca de Project e persistência do Chat funcionaram sem mistura de rotas.
- As correções finais aumentaram a legibilidade sem trocar o caráter denso do Command Deck.

## Evidências e skills usados

- Product Design `audit`: usado para estruturar a inspeção por fluxo, estado, severidade, evidência, impacto e correção.
- `design-taste-frontend`: aplicado apenas aos critérios pertinentes a uma ferramenta operacional — hierarquia, densidade, legibilidade, ícones, estados, foco, responsividade e motion — e não como brief de landing page.
- Browser skill: usada para inspeção runtime, navegação real, teclado, viewports, screenshots inline, console e landmarks. O Browser in-app não estava disponível; a skill selecionou uma sessão Chrome como fallback.
- Evidência corrente do workspace: código, testes, build, documentos locais de QA e screenshots aceitos. Claims pré-existentes foram tratados como hipóteses, não como prova.

## Limites da evidência

- A sessão Chrome permitiu inspeção funcional e visual, mas não substitui Safari/WebKit, leitor de tela real, dispositivo físico ou auditoria formal de acessibilidade; não afirmo conformidade WCAG completa.
- O long-press do handle não foi reproduzido de forma confiável pelo driver visual. O teste automatizado cobre o limiar de `351ms`, mas isso não prova ergonomia em toque físico.
- Para preservar o protocolo read-only, screenshots produzidos nesta execução foram inspecionados inline e não gravados; somente este relatório foi salvo.
- As correções finais de Runs, modal, rótulos de tablet e tipografia chegaram depois do encerramento do passe visual. Elas foram verificadas por inspeção de código e testes finais, mas não receberam um segundo passe browser nem novos screenshots aceitos. O screenshot aceito de tablet, portanto, documenta o estado anterior icon-only e está defasado em relação ao CSS final.
- Não foram abertas nem comparadas variantes irmãs, e nenhuma memória ou claim de outro agente foi usada como evidência de QA.

independent result: passed
