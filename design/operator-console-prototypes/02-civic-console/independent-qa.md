# QA independente: Civic Console

## Resultado executivo

O snapshot estabilizado foi aprovado. Não resta finding acionável P0, P1 ou P2 no escopo do protótipo `02-civic-console`.

| Severidade | Abertos |
| --- | ---: |
| P0 | 0 |
| P1 | 0 |
| P2 | 0 |

P3 não foi perseguido, conforme o protocolo de QA independente.

Esta assinatura foi feita depois da estabilização da fonte. Durante a primeira passagem foram reproduzidos quatro bloqueios — isolamento de Project, presets de Run capazes de contornar Admission rejected, perda da conversa ao trocar de rota e acessibilidade incompleta do diálogo. A implementação foi corrigida e cada risco foi revalidado no snapshot final; os findings intermediários não permanecem abertos.

## Findings acionáveis

Nenhum P0, P1 ou P2.

## Revalidação dos bloqueios intermediários

### 1. Isolamento de Project — passou

- No Chrome, selecionei `Disclosure Boundary` em Projects e naveguei para Study.
- A faixa de contexto continuou identificando `Disclosure Boundary`.
- A rota exibiu `Study indisponível para este Project` com `data-project-scope="locked"`.
- Não havia editor de revisão, lifecycle de Run, `REV-STUB-002`, variante ou record pertencente a `Retrieval Quality`.
- O mesmo fail-closed existe para Lab e Runs.
- O Chat desse Project inicia com zero mensagens e não reutiliza a conversa da fixture principal.
- A implementação final mantém `hasRuntimeFixture` explícito e usa `ProjectScopeLock` antes de montar Lab, Study ou Runs sem fixture.

Resultado: nenhum dado, estado de execução ou conversa atravessa o limite do Project selecionado.

### 2. Admission rejected e presets de Run — passou

- Com `REV-STUB-002` rejected, `Start Stub Run` permaneceu desabilitado.
- Loading, Failed, Completed e Idle também permaneceram desabilitados.
- A interface explicou: `Presets não criam uma Run sem AdmissionRecord admitted.`
- Nenhum `JOB-STUB-*` ou `ATTEMPT-STUB-*` apareceu nesse estado.
- Os handlers, o avanço automático e o reset da rota também verificam `canStart`.
- Após criar e compilar a revisão local com cobertura válida, o fluxo admitido habilitou a execução e percorreu queued → preparing → running → evaluating → terminal.

Resultado: não existe Run nova antes de Admission admitted para a revisão ativa.

### 3. Persistência e escopo do Chat — passou

- Enviei `Persistência final da conversa` no Lab; o Chat chegou a quatro mensagens.
- Naveguei Lab → Projects → Lab.
- A contagem permaneceu 4 → 4 e a mensagem continuou no feed.
- O teste final também cobre um draft ainda não enviado e confirma que ele sobrevive ao round-trip de rota.
- Mensagens e composer são controlados no `App` por Project; Projects sem fixture recebem estado vazio.
- Compact, half, tall, full, collapse e close continuam ações distintas.

Resultado: a conversa e o draft persistem entre rotas sem vazar para outro Project.

### 4. Diálogo Criar Project — passou

- Ao abrir, o foco foi para `Nome do Project`.
- Submit vazio manteve o foco nesse campo e aplicou `aria-invalid="true"`.
- Depois de preencher um nome válido, o próximo submit inválido moveu o foco para `Intent`.
- Tab no último controle voltou ao botão `Fechar diálogo`.
- Shift+Tab no primeiro controle voltou a `Criar Project`.
- Escape fechou o diálogo.
- O foco retornou a `Novo Project`.
- O conteúdo de fundo ficou `inert` e `aria-hidden` enquanto o diálogo estava aberto.

Resultado: foco inicial, validação, contenção bidirecional, Escape e retorno ao gatilho funcionam no DOM real.

## Cobertura funcional

| Superfície | Evidência independente | Resultado |
| --- | --- | --- |
| Lab | Estado rejected, Run e Evidence vazios, composer, Enter, Shift+Enter, foco pós-envio e presets idle/running/success/failure | Passou |
| Lab Agent | Sequência factual com preparação, leitura autorizada, `read_text`, resultado stub e resposta capturada; estados success e failure | Passou |
| Projects | Seleção de Project, workflow local, criação validada em React e diálogo acessível | Passou |
| Study | Revisão rejected bloqueia enqueue; revisão local corrigida só habilita depois de compilar e admitir | Passou |
| Runs | Job e attempt separados; fases ordenadas; Completed e Failed terminais; presets bloqueados sem Admission | Passou |
| Chat | Thread por Project, persistência entre rotas, snaps por teclado, collapse, close e bottom sheet móvel | Passou |
| Histórico | Rotas `/`, `/projects`, `/study` e `/runs` mantêm um único `main`; `popstate` possui listener com cleanup | Passou |
| Limites de evidência | Digest não é descrito como recomputável; Bundle é references-only, não portátil e não replayable | Passou |

## Responsividade e inspeção visual

### Desktop — 1440 × 940

- `innerWidth=1440`, `innerHeight=940`.
- Documento com scrollbar: `clientWidth=1425`, `scrollWidth=1425`; body também mediu 1425.
- Exatamente um `<main>`.
- Rail, command strip, workflow, Lab Agent e dock do Chat permaneceram legíveis e sem overflow horizontal.
- Admission rejected continuou sendo a única região de decisão com superfície vermilion.

### Tablet — 834 × 1112

- Projects: `clientWidth=834`, `scrollWidth=834`.
- O layout de Projects e o inspector mediram 724 px e refluíram em sequência, sem coluna cortada.
- Os quatro labels do rail permaneceram visíveis, cada item com aproximadamente 70 px.
- Study, com scrollbar vertical, mediu `clientWidth=819` e `scrollWidth=819`.
- Exatamente um `<main>` e nenhum overflow horizontal.

### Mobile — 390 × 844

- Viewport CSS de 390 × 844; documento com scrollbar em 375 × 375 de `clientWidth`/`scrollWidth`.
- Navegação inferior com quatro destinos, cerca de 91 × 59 px cada, dentro de uma faixa de 375 × 70 px.
- Study e Lab mantiveram título, contexto, workflow e ações em uma coluna.
- O Chat abriu como folha de 355 × 354 px, de `y=412` até `bottom=766`.
- A navegação inferior iniciou em `y=774`; sobreposição calculada: 0 px.
- Exatamente um `<main>` e nenhum overflow horizontal.

### Comparação com a referência

`reference/source.png` e a implementação foram inspecionadas em resolução original e pela composição lado a lado já registrada. A implementação preserva a direção visual da referência — rail estreito em carvão, command strip compacto, canvas claro, tipografia racional, workflow Intent → StudyRevision → Admission → Run → Evidence e vermilion reservado à decisão crítica — sem copiar os problemas de arquitetura visual identificados na fonte.

O uso de `design-taste-frontend` foi limitado às verificações relevantes para um console operacional: consistência, contraste, ritmo, densidade, hierarquia, estados e reflow. Regras específicas de landing pages não foram aplicadas a este dashboard.

## Evidência renderizada

As recapturas corretivas aceitas existem e seus nomes correspondem às dimensões reais do raster:

- `fix-project-isolation-1440x667.jpg`
- `fix-project-isolation-834x1112.jpg`
- `fix-project-isolation-375x812.jpg`
- `fix-runs-rejected-1425x930.jpg`
- `fix-chat-persistence-1425x930.jpg`
- `fix-chat-persistence-375x812.jpg`
- `fix-project-dialog-1440x940.jpg`
- `fix-project-dialog-375x812.jpg`

A antiga captura `lab-chat-mobile-390x844.png` não foi usada como evidência aceita: era um JPEG de 375 × 174 com extensão incorreta. `design-qa.md` e `qa/manual-audit.md` agora apontam para as recapturas JPEG válidas.

A captura desktop de isolamento possui somente 667 px de altura salva; por isso a verificação independente de desktop não dependeu dela isoladamente. O estado completo foi verificado no Chrome em viewport CSS 1440 × 940, e as versões tablet e mobile registram a superfície fail-closed completa.

## Gates determinísticos pós-estabilização

| Gate | Resultado |
| --- | --- |
| `npm test -- --run` | 2 arquivos, 13/13 testes, 0 falhas; duração 32,39 s |
| `npm run build` | Passou; Vite 6.4.2, 4.992 módulos, build em 21,75 s e pacote Sites preparado |
| `npm run test:sites` | 4/4 testes, 0 falhas |
| Console do Chrome | 0 warnings, 0 errors |
| Scan estático do renderer | Sem import de sibling, `electron`, `node:*`, provider, credencial, fetch, SVG artesanal, gradiente ou storage persistente |

Os imports `node:*` encontrados ficam restritos aos scripts de empacotamento e aos testes do worker, não ao renderer.

## Qualidade de implementação

- Estado da conversa e do composer foi elevado para um store controlado por Project sem adicionar dependência ou persistência indevida.
- `ProjectScopeLock` centraliza o comportamento fail-closed e evita duplicação de records.
- Runs usa `canStart` tanto na affordance quanto nos handlers e efeitos, reduzindo a possibilidade de bypass visual ou programático no stub.
- Timers da Run e do Lab Agent possuem cleanup; o listener de `popstate` também é removido no unmount.
- Ícones visíveis vêm de `@phosphor-icons/react`; não há emoji, SVG artesanal, glyph improvisado ou biblioteca concorrente.
- A UI não afirma autoridade humana, portabilidade, replay, blobs, grants ou recomputabilidade não implementada.

## Limites da assinatura

- QA de browser executada no Chrome conectado. Safari/WebKit e Firefox não foram validados.
- Não houve dispositivo touch físico, leitor de tela real ou auditoria automatizada completa de contraste.
- O long press de 360 ms foi coberto deterministicamente por teste; a ergonomia do gesto não foi medida em hardware físico.
- Provider, backend, Keychain, credenciais, persistência real e efeitos externos estão fora deste protótipo local.
- Esta passagem validou somente `02-civic-console`; os gates completos do repositório permanecem responsabilidade da integração global.

independent result: passed
