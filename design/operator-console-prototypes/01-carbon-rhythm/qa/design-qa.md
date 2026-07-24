# Design QA - Carbon Rhythm

## Resultado

**Passed.** A implementação final não mantém findings P0, P1 ou P2 abertos. P3 não foi perseguido neste passe, conforme o escopo de fechamento.

## Comparação de referência

- Referência: `reference/source.png`, 1440 x 1024.
- Implementação comparada: `qa/screenshots/11-lab-source-match-1440x1024.png`, viewport CSS 1440 x 1024.
- Estado comparado: rota Lab, evento `tool.completed: read_text`, estágio atual `Avaliação`, seleção independente `Leitura da tool`, Chat do operador aberto.
- Método: referência e screenshot final foram abertos juntos na mesma entrada de comparação visual.

A implementação preserva a composição principal da referência: command rail horizontal, hierarquia Study/Project, stepper de execução, inspector técnico, conversa, atividade observável, composer e Chat lateral. As diferenças deliberadas seguem o brief e os contratos do produto: dock padrão compacto em vez de thread alta, disclosure explícito de autoridade, IDs canônicos do stub, `ArtifactRef` sem grant e atividade pública em português.

## Iterações e correções

### Passe 1 - desktop inicial

Evidência: `qa/screenshots/01-lab-desktop-initial.png`.

- P1: o composer começava abaixo do primeiro viewport 1440 x 940.
- P2: o cabeçalho do Chat quebrava em linhas excessivas porque o dock visual era menor que o alvo.
- Correção: ritmo vertical do Lab reduzido, atividade observável ganhou viewport interno com scroll e o dock compacto passou a 320 px visuais, preservando alvos de 44 px.
- Pós-fix: `qa/screenshots/02-lab-desktop-final.png`; composer, Project selector e envio estão inteiros no primeiro viewport.

### Passe 2 - Study

Evidência intermediária inspecionada no navegador durante a revisão admitida.

- P2: a fórmula `cenário x variantes x repetições` quebrava o cenário em fragmentos e truncava o nome da segunda variante.
- Correção: fórmula reorganizada em duas linhas, com resultado separado e nomes de variantes livres para reflow.
- Pós-fix: `qa/screenshots/05-study-admitted-desktop.png`; cenário, duas variantes, repetição e total de RunSpecs continuam legíveis.

### Passe 3 - tablet

Evidência inicial: `qa/screenshots/07-lab-tablet-834x1112.png`.

- P1: o Chat fixed cobria título, disclosure e parte do stepper em 834 px.
- Correção: entre 768 e 1279 px o shell reserva uma coluna de 296 px e o Chat volta a `sticky`, sem overlay do canvas.
- Pós-fix: `qa/screenshots/07b-lab-tablet-full.png`; o viewport CSS é 834 x 1112 e a captura full-page registra o documento completo.

### Passe 4 - mobile

Evidência: `qa/screenshots/08-chat-mobile-sheet-390x844.png` e `qa/screenshots/10-lab-mobile-full.png`.

- P2: o launcher textual fechado poderia cobrir parte do inspector em 390 px.
- Correção: launcher móvel tornou-se um controle somente por ícone, mantendo nome acessível e alvo 44 x 44 px.
- Pós-fix: bottom sheet permanece acima da bottom navigation; fechado, o launcher ocupa somente 44 px.

## Validação funcional no navegador

- Lab: draft enviado por Enter; sequência local chegou a `Resposta capturada`; composer voltou ao estado disponível.
- Chat: snap para meia altura; nota adicionada; thread preservada ao navegar para Projects; close e reopen verificados no mobile.
- Projects: submit vazio exibiu validação inline; `Audit Trail` foi criado somente no estado React; Workspace permaneceu `Integration pending`.
- Study: revisão 03 manteve Enqueue nativamente disabled; revisão 04 local exibiu dois AdmissionRecords admitted e liberou Enqueue.
- Runs: sequência percorreu queued, preparing, running, evaluating e terminal; nenhuma Run canônica foi alegada.
- Console: nenhum warning ou error no fim do fluxo.

## Fix verification

O snapshot foi reaberto depois de uma revisão independente encontrar vazamento de escopo por Project e dois P2 de acessibilidade/layout. A verificação abaixo corresponde ao estado final recongelado.

### Isolamento por Project e gate de Admission

- Somente `Release Integrity` possui a Study `study:stub-release-integrity` neste stub.
- `Context Drift`, `Provider Gate` e Projects criados localmente exibem estados fail-closed em Lab, Study e Runs.
- Esses escopos não exibem revision IDs, Run IDs, eventos, evidence, start ou presets pertencentes a `Release Integrity`.
- O composer do Lab fica nativamente disabled sem Study; o Chat mantém um thread separado por Project.
- Em `Release Integrity`, a rota Runs permanece vazia enquanto a revisão contém Admission rejeitada. Start e presets surgem somente depois de criar a revisão 04 admitida e executar Enqueue.
- O reducer também rejeita diretamente `RUN_START` e `RUN_PRESET` sem a revisão admitida exata.

Evidências: `12-context-drift-lab-fail-closed-1440x1024.png`, `13-context-drift-study-fail-closed-1440x1024.png`, `14-context-drift-runs-fail-closed-1440x1024.png`, `15-release-integrity-runs-admission-gated-1440x1024.png` e `16-release-integrity-runs-admitted-enqueued-1440x1024.png`.

### P2 revalidados

- O diálogo Create Project contém Tab e Shift+Tab entre Fechar, Nome, Intenção, Cancelar e Criar; Escape fecha e restaura foco ao trigger.
- Em 834 x 1112, os filhos grid do Chat agora aceitam shrink. A medição final foi `innerWidth=834`, `clientWidth=819`, `document.scrollWidth=819`, `body.scrollWidth=819` e zero descendentes do Chat além do client width.

Evidências: `18-create-project-focus-trap-834x1112.png` e `19-projects-tablet-no-overflow-834x1112.png`.

### Gates pós-correção

- `npm test`: 12/12 testes passaram.
- `npm run build`: passou; 4.989 módulos transformados e pacote Sites preparado.
- `npm run test:sites`: 4/4 testes passaram.
- Chrome fresco: somente logs debug do Vite e info do React DevTools; zero warning e zero error.

## Matriz visual final

| Viewport | Evidência | Resultado |
| --- | --- | --- |
| 1440 x 940 | `02-lab-desktop-final.png` | command rail íntegra, dock 320 px, próximo passo visível |
| 1440 x 1024 | `11-lab-source-match-1440x1024.png` | comparação direta com a referência |
| 834 x 1112 | `07b-lab-tablet-full.png` | Chat em coluna reservada, sem overflow horizontal |
| 390 x 844 | `08-chat-mobile-sheet-390x844.png` | Chat bottom sheet acima da navegação |
| 390 px full page | `10-lab-mobile-full.png` | stepper vertical, conteúdo em uma coluna e composer acessível |
| 834 x 1112 | `19-projects-tablet-no-overflow-834x1112.png` | Chat restrito ao client width; nenhum overflow horizontal |

## Limites

- QA visual feita em Chrome; Safari/WebKit e dispositivo físico não foram executados.
- A captura full-page mantém elementos `fixed` na posição do viewport inicial, comportamento do capturador e não do layout ao rolar.
- Inspeção de contraste foi feita nos tokens e estados do CSS, sem alegar certificação WCAG.
- O backend é um stub determinístico local; não houve provider, credencial, filesystem externo ou efeito de produção.
