# Auditoria manual: Civic Console

## Escopo

- Superfície: protótipo React isolado do Operator Console.
- Rotas: Lab, Projects, Study e Runs.
- Objetivo: corrigir uma StudyRevision rejeitada, validar Admission e executar uma Run local determinística.
- Viewports obrigatórios: 1440 x 940, 834 x 1112 e 390 x 844.

## Resultado

- Implementação funcional criada a partir de `reference/source.png`.
- P1 da referência corrigidos por construção:
  - RunSpec permanece na região Admission como prévia anterior à Run.
  - Run e Evidence começam explicitamente vazios.
  - Workspace está separado das cinco etapas.
  - Prontidão descreve somente o stub determinístico local.
  - O workflow usa regiões abertas e uma única superfície selecionada.
  - Chat começa em dock sobreposto, não como terceira coluna persistente.
- P2 da referência corrigidos por construção:
  - Ações content-sized.
  - UI em pt-BR com nomes técnicos preservados.
  - Corpo de 15 px e metadados de 12-13 px.
  - Gramática única de progresso geométrico.
  - Atividade observável sem raciocínio privado.
  - Controles do Chat possuem nome acessível e destino explícito.

## Checklist funcional

- [x] Navegação por pointer no Browser, teclado e histórico nos testes automatizados.
- [x] Composer vazio, Enter, Shift+Enter, foco e sequência determinística.
- [x] Presets idle, running, success e failure disponíveis no controle local.
- [x] Criação local de Project e validação do diálogo.
- [x] Diálogo contém Tab e Shift+Tab, fecha com Escape, foca o primeiro campo inválido e devolve foco ao gatilho.
- [x] Projects sem fixture falham fechado em Lab, Study e Runs, sem records ou conversa cruzados.
- [x] Admission rejected bloqueia enqueue; revisão corrigida habilita após compilação.
- [x] Admission rejected também bloqueia todos os presets de Run e não cria job ou attempt.
- [x] Run percorre queued, preparing, running, evaluating e terminal.
- [x] Job e attempt permanecem separados.
- [x] Thread, estado do Chat e draft não enviado persistem entre rotas e permanecem isolados por Project.
- [x] Chat collapse, close, largura, alturas, hold preview e snaps por teclado.

## Checklist responsivo

- [x] 1440 x 940 sem scroll horizontal e com Chat subordinado.
- [x] 834 x 1112 sem overflow; workflow em duas colunas e Admission em largura total.
- [x] 390 x 844 com navegação inferior, workflow em uma coluna e Chat em bottom sheet.
- [x] Textos longos e estados quebram linha sem truncar controles nos três viewports.

## Checklist visual

- [x] Paleta limitada a porcelana, carvão, prata, fumaça e vermelhão.
- [x] Sem verde, azul, roxo, glow, glassmorphism ou cards genéricos repetidos.
- [x] Ícones Phosphor com peso consistente.
- [x] Radius de 8-10 px e shadow fria restrita ao Chat e overlays.
- [x] Referência e implementação comparadas no mesmo input visual em `qa/screenshots/lab-comparison-1424x512.png`.

## Checklist de acessibilidade

- [x] Ordem semântica, navegação por teclado e foco visível.
- [x] Labels, nomes acessíveis, `aria-current`, `aria-live` e disabled real.
- [x] Controles principais com área prática de interação; launcher mobile mede 56 x 56 px.
- [x] `prefers-reduced-motion` possui fallback estático no indicador próprio.
- [x] Contraste inspecionado visualmente; conformidade WCAG completa não é afirmada sem medição adicional.

## Iterações do Browser QA

1. Desktop: removido resumo vertical ilegível do dock e reservado espaço para Workspace.
2. Mobile: dock reduzido de 196 px para launcher de 56 px após sobrepor `Compilar e validar`.
3. Tablet: reservado espaço do `WorkflowIntro` após colisão com o dock.
4. QA independente: Project scoping, presets rejected, persistência do Chat e acessibilidade do diálogo corrigidos e recapturados.

As três correções foram recapturadas nos mesmos breakpoints. Não restou finding P0, P1 ou P2.

## Evidência e limites

- Browser real: Chrome conectado, aplicação em `http://127.0.0.1:4302/`.
- Console: zero warnings e zero errors nos fluxos e na comparação.
- Capturas corretivas aceitas: `qa/screenshots/fix-project-isolation-1440x667.jpg`, `qa/screenshots/fix-project-isolation-834x1112.jpg`, `qa/screenshots/fix-project-isolation-375x812.jpg`, `qa/screenshots/fix-runs-rejected-1425x930.jpg`, `qa/screenshots/fix-chat-persistence-1425x930.jpg`, `qa/screenshots/fix-chat-persistence-375x812.jpg`, `qa/screenshots/fix-project-dialog-1440x940.jpg` e `qa/screenshots/fix-project-dialog-375x812.jpg`.
- Testes automatizados: 13/13 Vitest e 4/4 Sites worker.
- Build: Vite production build concluído.
- Limites: não houve teste formal com leitor de tela, medição automatizada de contraste, matriz multi-browser ou validação em dispositivo físico. Esses limites não bloquearam o protótipo local, mas impedem uma alegação de conformidade ou produção.
