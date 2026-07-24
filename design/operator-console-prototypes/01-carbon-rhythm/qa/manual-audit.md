# Auditoria manual - Carbon Rhythm

## Escopo

- Protótipo React isolado em `01-carbon-rhythm`.
- Rotas: Lab (`/`), Projects (`/projects`), Study (`/study`) e Runs (`/runs`).
- Backend: stub determinístico local, sem provider, credencial ou efeito externo.
- Viewports-alvo: 1440 x 940, 834 x 1112 e 390 x 844.

## Funcionalidade

- [x] Navegação por pointer, teclado e browser history.
- [x] Composer: vazio disabled, Enter envia e Shift+Enter quebra linha.
- [x] Sequência observável completa e anúncio via live region.
- [x] Tool Call e Tool Result marcados como demonstração local.
- [x] Chat: abrir, compactar, expandir, fechar, long press e snaps por teclado.
- [x] Thread do Chat preservado entre rotas e isolado por Project.
- [x] Create Project com validação inline, estado local e sem Study herdada.
- [x] Stage selection atualiza inspector do Project.
- [x] Admission rejected bloqueia Enqueue.
- [x] Nova StudyRevision corrige o preflight em estado local.
- [x] Run stub avança por todas as fases e conserva terminal de falha.
- [x] Presets da Run aparecem somente após Admission admitted e Enqueue; reducer impede bypass.
- [x] Lab, Study e Runs falham fechado em todos os Projects sem Study vinculada.

## Responsividade

- [x] 1440 x 940 sem overflow horizontal e com composer completo no primeiro viewport.
- [x] 834 x 1112 sem overflow horizontal; Chat ocupa coluna reservada e não cobre o canvas.
- [x] 390 x 844 em uma coluna, bottom nav visível e Chat acima da navegação.
- [x] Texto longo e IDs quebram sem expandir o viewport.
- [x] Reflow entre os três breakpoints não oculta as ações persistentes.

## Qualidade visual

- [x] Um único tema carbono/grafite e um único acento laranja oxidado.
- [x] Sem verde decorativo, roxo, blue glow, glassmorphism ou gradientes.
- [x] Ícones exclusivamente Phosphor.
- [x] Radius consistente de 9 px para controles e 11 px para superfícies.
- [x] Body real entre 15-16 px; metadata não menor que 11.5 px salvo IDs/timestamps.
- [x] Current, selected, completed, future e rejected distintos além da cor.
- [x] Dock compacto preserva o canvas; previews ficam dentro do viewport.
- [x] Três marcas exatas no spinner Carbon Rhythm.

## Acessibilidade

- [x] Landmarks, headings e labels acessíveis.
- [x] Ordem de tabulação acompanha a leitura visual nos fluxos exercitados.
- [x] Foco visível de 2 px e retorno de foco em dialog/Chat.
- [x] Dialog mantém Tab e Shift+Tab contidos e Escape restaura o trigger.
- [x] Alvos de ícone com 44 x 44 px.
- [x] Estado disabled usa atributo nativo e explicação associada.
- [x] `aria-current`, `aria-pressed`, `aria-busy` e live regions coerentes.
- [x] Reduced motion desativa loops e transições não essenciais.
- [x] Contraste de texto e controles inspecionado nos tokens e estados finais.
- [x] Nenhuma alegação de conformidade WCAG feita apenas por screenshot.

## Evidências e resultado

Execução concluída em Chrome real, com viewport CSS controlado e DPR 1 na sessão:

- `02-lab-desktop-final.png`: Lab em 1440 x 940, composer inteiro no primeiro viewport.
- `04-projects-desktop.png`: Project criado localmente, Workspace ainda `Integration pending` e Chat persistido.
- `05-study-admitted-desktop.png`: revisão corrigida com dois AdmissionRecords admitted.
- `06-runs-terminal-desktop.png`: sequência determinística no estado terminal e seis refs staged.
- `07b-lab-tablet-full.png`: layout completo no viewport CSS 834 x 1112; a captura full-page tem altura documental maior.
- `08-chat-mobile-sheet-390x844.png`: bottom sheet do Chat acima da navegação móvel.
- `10-lab-mobile-full.png`: reflow completo de 390 px com stepper vertical e launcher reduzido.
- `11-lab-source-match-1440x1024.png`: implementação no mesmo viewport da referência `source.png`.
- `12` a `16`: isolamento de Project, gate de Admission e inventário liberado somente após Enqueue.
- `18-create-project-focus-trap-834x1112.png`: diálogo revalidado com foco contido.
- `19-projects-tablet-no-overflow-834x1112.png`: medição final sem overflow horizontal no tablet.

O fluxo do navegador confirmou composer, sequência observável, snaps, isolamento do Chat, Projects sem Study, gate fail-closed de Admission, focus trap e terminal da Run. O console ficou sem warnings ou errors. Os 12 testes automatizados cobrem browser history, Shift+Enter, long press, snaps por teclado, escopo por Project, bypass do reducer e foco do modal.

Resultado: aprovado. Nenhum finding P0, P1 ou P2 permanece aberto. Isto não é uma certificação formal de acessibilidade nem validação em produção.
