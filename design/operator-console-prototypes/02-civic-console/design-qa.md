# Design QA: Civic Console

## Artefatos e estado comparado

- Fonte visual de verdade: `reference/source.png`.
- Implementação: `http://127.0.0.1:4302/`.
- Rota e estado principal: Lab, Project `Retrieval Quality`, Study `Respostas com fontes insuficientes`, `AdmissionRecord` rejected, nenhuma Run criada e nenhuma Evidence disponível.
- Evidência full-view combinada: `qa/screenshots/lab-comparison-1424x512.png`.
- Evidência de implementação antes da primeira correção: `qa/screenshots/lab-before-1440x1024.png`.
- Evidência de implementação aceita: `qa/screenshots/lab-after-1440x1024.png`.
- Evidência operacional desktop: `qa/screenshots/lab-desktop-1440x940.png`.
- Evidência responsiva original: `qa/screenshots/lab-tablet-834x1112.png`, `qa/screenshots/lab-mobile-390x844.png` e `qa/screenshots/study-mobile-390x844.png`.
- Estados adicionais: `qa/screenshots/projects-created-1440x940.png`, `qa/screenshots/study-admitted-1440x940.png`, `qa/screenshots/runs-completed-1440x940.png` e `qa/screenshots/lab-agent-complete-1440x940.png`.
- Evidência corretiva fresca: `qa/screenshots/fix-project-isolation-1440x667.jpg`, `qa/screenshots/fix-project-isolation-834x1112.jpg`, `qa/screenshots/fix-project-isolation-375x812.jpg`, `qa/screenshots/fix-runs-rejected-1425x930.jpg`, `qa/screenshots/fix-chat-persistence-1425x930.jpg`, `qa/screenshots/fix-chat-persistence-375x812.jpg`, `qa/screenshots/fix-project-dialog-1440x940.jpg` e `qa/screenshots/fix-project-dialog-375x812.jpg`.

A fonte mostra o Chat aberto. A implementação aceita inicia com um dock pequeno, conforme o finding P1-5 da auditoria da fonte e o brief. A rota, o conteúdo e o estado de Admission são equivalentes; a geometria do Chat é uma correção intencional e não foi tratada como erro de fidelidade.

## Viewports, pixels e normalização

| Evidência | CSS viewport | Raster salvo | Densidade | Uso |
| --- | ---: | ---: | ---: | --- |
| Fonte | 1440 x 1024 | 1440 x 1024 PNG | 1x | direção visual |
| Lab comparável | 1440 x 1024 | 1425 x 1013 | 1x | hierarquia e composição |
| Lab desktop | 1440 x 940 | 1425 x 930 | 1x | fluxo operacional |
| Lab tablet | 834 x 1112 | 819 x 1092 | 1x | breakpoint intermediário |
| Lab mobile | 390 x 844 | 375 x 812 | 1x | bottom navigation e dock |
| Project isolation desktop | 1440 x 940 | 1440 x 667 JPEG | 1x | fail-closed por Project |
| Project isolation tablet | 834 x 1112 | 834 x 1112 JPEG | 1x | fail-closed intermediário |
| Project isolation mobile | 390 x 844 | 375 x 812 JPEG | 1x | fail-closed e navegação inferior |
| Chat persistente desktop | 1440 x 940 | 1425 x 930 JPEG | 1x | thread, draft e estado aberto |
| Chat persistente mobile | 390 x 844 | 375 x 812 JPEG | 1x | bottom sheet persistente |
| Diálogo desktop | 1440 x 940 | 1440 x 940 JPEG | 1x | foco inválido e backdrop inert |
| Diálogo mobile | 390 x 844 | 375 x 812 JPEG | 1x | foco inválido e layout |
| Comparação combinada | 1424 x 512 | 1424 x 512 | 1x | fonte à esquerda, implementação à direita |

O Browser informou os CSS viewports acima. O conector do Chrome salvou o raster de página sem a área ocupada pela scrollbar, por isso a largura e a altura do arquivo de implementação são ligeiramente menores. A comparação combinada normalizou os dois lados para painéis iguais de 711 x 512, separados por 2 px, sem aumentar densidade. Essa diferença de captura não foi usada para alegações pixel-perfect.

## Evidência full-view

`qa/screenshots/lab-comparison-1424x512.png` coloca a fonte e a implementação no mesmo input visual. A comparação confirma:

- rail estreito em carvão, command strip compacto e canvas de porcelana fria;
- Project e Study como contexto primário;
- sequência Intent, StudyRevision, Admission, Run e Evidence;
- Admission como única região com superfície vermilion selecionada;
- ação corretiva primária e enqueue secundário desabilitado;
- feed do Lab Agent abaixo do workflow;
- Chat subordinado ao workflow, com a correção deliberada de iniciar recolhido.

A implementação é mais aberta do que a fonte: remove cards aninhados, desloca a prévia de RunSpec para Admission, mantém Run e Evidence vazios e separa Workspace. Essas diferenças são correções requeridas pela auditoria, não drift acidental.

## Evidência focada

Não foi necessário gerar crops adicionais. A fonte e as capturas aceitas foram abertas em resolução original para inspecionar Admission, Workspace, Chat, composer e tipografia; a comparação combinada foi usada para a composição geral. Copy pequena, nomes acessíveis e estados disabled/live foram verificados pelo DOM real do Browser, onde o raster reduzido não é adequado para leitura precisa. Não há fotografia, ilustração, logo raster ou asset gerado que exija uma comparação focada de crop ou qualidade.

## Superfícies de fidelidade obrigatórias

### Fontes e tipografia

- Família racional única: Aptos com fallbacks Helvetica/Arial; mono restrito a IDs, códigos e eventos.
- Hierarquia, pesos, line-height, letter-spacing e wrapping foram inspecionados em desktop, tablet e mobile.
- Corpo principal permanece em 15 px equivalente; metadados usam 12-13 px sem carregar decisões principais.
- Nenhuma truncação acionável permanece. No tablet, a explicação do workflow passou a quebrar em duas linhas sem entrar sob o dock.

### Espaçamento e ritmo

- Rail de 76 px, canvas amplo, grid aberto e apenas uma superfície de Admission.
- Botões são content-sized e os controles usam raio de 8-10 px.
- Shadow fria fica restrita a Chat, diálogo e overlays.
- Não há overflow horizontal nos três viewports obrigatórios.

### Cores e tokens

- Paleta limitada a porcelana, papel, fumaça, prata, carvão e um vermilion.
- Não há verde decorativo, cobalt, roxo, gradiente, glassmorphism ou AI glow.
- Success usa checks, labels e geometria, sem introduzir uma segunda cor semântica decorativa.

### Qualidade de imagem e assets

- A UI não precisa de fotografia ou ilustração.
- Todos os ícones visíveis vêm de `@phosphor-icons/react`; não há emoji, SVG artesanal, text glyph icon, CSS art ou asset raster aproximado.
- A fonte visual é usada apenas como referência e evidência de QA, não como uma camada rasterizada da interface.

### Copy e conteúdo

- UI prioritariamente em pt-BR; nomes técnicos como Project, StudyRevision, RunSpec, AdmissionRecord, Run, SubjectEnvelope, Bundle e ArtifactRef foram preservados.
- A copy evita afirmar autoridade humana, prontidão ampla, portabilidade, replay, grant, blob ou acesso por ArtifactRef.
- O bloco `Atividade observável` contém apenas eventos públicos factuais e declara que não expõe raciocínio privado ou grader oculto.

### Ícones, affordances e estados

- Project usa folder, Study notebook, Admission shield, Run play/pulse, Evidence archive/file-lock e leitura usa file-search.
- Empty, rejected, admitted, loading, failed, completed, disabled, active e selected têm texto ou geometria além da cor.
- Chat tem ações separadas para largura, altura, snaps, collapse e close; hold de 360 ms e snaps por teclado foram exercitados em teste.

### Responsividade e acessibilidade

- 1440 x 940: workflow amplo, sem overflow horizontal.
- 834 x 1112: workflow em duas colunas, Admission ocupa a largura e o dock não encobre a explicação.
- 390 x 844: navegação inferior, workflow em uma coluna, launcher de 56 px e Chat como bottom sheet sem cobrir a navegação.
- HTML semântico, labels, `aria-current`, `aria-live`, disabled real, foco visível e `prefers-reduced-motion` estão implementados.
- Contraste foi inspecionado visualmente. Uma afirmação formal de WCAG AA exigiria medição automatizada adicional.

## Findings atuais

Não há findings acionáveis P0, P1 ou P2 após as iterações abaixo.

### Follow-up polish

Nenhum P3 foi perseguido nesta rodada. O objetivo do handoff é preservar o estado aceito e não expandir escopo com refinamentos opcionais.

## Histórico de comparação

### Iteração 1: desktop 1440 x 1024

- Finding P2: o dock recolhido renderizava o resumo da mensagem em orientação vertical ilegível.
- Finding P2: o dock encobria parte de `Workspace / Integration pending`.
- Fix: ocultar o resumo no dock desktop e reservar 72 px à direita no `SurfaceHeader`.
- Evidência anterior: `qa/screenshots/lab-before-1440x1024.png`.
- Evidência posterior: `qa/screenshots/lab-after-1440x1024.png`.
- Resultado posterior: dock legível, Workspace inteiro e nenhum overflow horizontal.

### Iteração 2: mobile 390 x 844

- Finding P2: o dock recolhido de 196 px cobria parte da ação primária da Study.
- Fix: reduzir o estado recolhido para um launcher de 56 px com ícone e contagem; o preview permanece dentro da folha aberta.
- Evidência posterior: `qa/screenshots/lab-mobile-390x844.png`, `qa/screenshots/study-mobile-390x844.png` e a recaptura válida `qa/screenshots/fix-chat-persistence-375x812.jpg`.
- Resultado posterior: launcher não cruza `Compilar e validar`; bottom sheet termina antes da navegação inferior; nenhum overflow horizontal.

### Iteração 3: tablet 834 x 1112

- Finding P2: a explicação da posição atual entrava sob o dock no limite superior do breakpoint.
- Fix: reservar 76 px no `WorkflowIntro` até 1040 px e restaurar 4 px no breakpoint móvel.
- Evidência posterior: `qa/screenshots/lab-tablet-834x1112.png`.
- Resultado posterior: texto quebra em duas linhas, não colide com o dock e o documento permanece sem overflow horizontal.

## Fix verification

### Iteração 4: bloqueios da QA independente

- P1 — isolamento de Project: selecionar `Disclosure Boundary` ou `Bundle Integrity` agora muda todo o contexto e falha fechado em Lab, Study e Runs. Nenhuma `StudyRevision`, `RunSpec`, variante, `AdmissionRecord`, Run, mensagem ou draft de `Retrieval Quality` é reutilizado sob outro Project.
- P1 — presets de Run: `Start Stub Run`, Loading, Failed, Completed e Idle permanecem `disabled` enquanto a revisão ativa possui `AdmissionRecord rejected`; handlers e avanço automático também verificam a admissão. O DOM não exibiu `JOB-STUB-*` ou `ATTEMPT-STUB-*` nesse estado.
- P1 — persistência de conversa: reducer, mensagens e composer passaram para estado controlado por Project no `App`; a thread, o estado do Chat e um draft não enviado sobreviveram à navegação Lab → Projects → Lab sem cruzar Projects.
- P2 — diálogo de criação: o background fica `inert`; o foco inicial vai para `Nome do Project`; submit inválido foca e marca o primeiro campo inválido; Tab e Shift+Tab ficam contidos; Escape fecha; e o foco retorna a `Novo Project`.
- Evidência: `qa/screenshots/fix-project-isolation-1440x667.jpg`, `qa/screenshots/fix-project-isolation-834x1112.jpg`, `qa/screenshots/fix-project-isolation-375x812.jpg`, `qa/screenshots/fix-runs-rejected-1425x930.jpg`, `qa/screenshots/fix-chat-persistence-1425x930.jpg`, `qa/screenshots/fix-chat-persistence-375x812.jpg`, `qa/screenshots/fix-project-dialog-1440x940.jpg` e `qa/screenshots/fix-project-dialog-375x812.jpg`.
- Browser fresco: viewports CSS solicitados em desktop, tablet e mobile; nenhum overflow horizontal crítico; zero warnings e zero errors.
- Gates pós-estabilização: `npm test` 13/13, `npm run build` concluído e `npm run test:sites` 4/4.
- Nenhum P3 foi perseguido.

## Interações e console

No Browser real foram exercitados: composer com Shift+Enter, envio com Enter, persistência de thread e draft entre rotas, isolamento de conversa por Project, sequência do Lab Agent, abertura e snaps do Chat, collapse versus close, revisão corrigida, compilação, Admission gating, bloqueio de todos os presets quando rejected, enqueue, lifecycle terminal, criação validada de Project, trap bidirecional do diálogo, Escape, foco inválido, retorno ao gatilho e rotas. O fluxo terminal exibiu `JOB-STUB-042`, `ATTEMPT-STUB-01` e o Tool Event ilustrativo somente após admissão. O Browser retornou zero logs de warning ou error na aplicação e na página de comparação.

## Final result

final result: passed
