# Auditoria manual: Spatial Trace

## Escopo

Auditoria combinada de UX e acessibilidade do protótipo isolado `04-spatial-trace`, executada em Chrome real contra `http://localhost:4304`. O fluxo auditado cobre Lab, Projects, Study, Admission, Runs, Evidence inspector e Chat adaptativo. Todos os dados observados são stubs locais e não canônicos.

## Objetivo do operador e alvo de acessibilidade

O operador deve conseguir manter o Project em contexto, entender a fase atual, corrigir uma incompatibilidade de Admission, iniciar uma Run stub e inspecionar referências de evidência sem confundir records ou autoridade. O alvo de acessibilidade desta auditoria é navegação por teclado e ponteiro, semântica e nomes acessíveis, foco visível, comunicação de estado, reflow mobile e motion reduzível.

## Passos auditados

1. **Lab e contexto inicial. Saúde: boa.** O primeiro viewport mostra Project, Study ativa, próxima ação, traço e entrada do Chat. O aviso de stub é explícito e o CTA leva ao gate relevante.
2. **Projects e criação local. Saúde: boa.** A seleção reposiciona o traço sem reload, o diálogo tem labels, erro inline, autofocus, Escape e contenção de Tab. O vínculo com Workspace aparece como indisponível e Project não é descrito como pasta.
3. **Study e compile preview. Saúde: boa.** `scenario x variants x repetitions` aparece como composição espacial compacta. RunSpec e StudyRevision têm superfícies distintas.
4. **Admission gating. Saúde: boa.** O botão rejeitado permanece desabilitado, o mismatch expõe valores solicitado e suportado, e a correção cria novo draft sem reescrever o AdmissionRecord anterior.
5. **Run lifecycle. Saúde: boa.** A sequência `queued -> preparing -> running -> evaluating -> terminal` foi observada no browser. Job e attempt aparecem como filhos operacionais, e a falha controlada não expõe exceção sensível.
6. **Evidence inspector e comparação. Saúde: boa.** O bundle declara `references_only`, `portable=false` e `replayable=false`. A limitação do digest do SubjectEnvelope aparece em texto direto. A comparação usa justaposição e geometria, sem ícone de balança.
7. **Chat adaptativo. Saúde: boa.** Enter envia, Shift+Enter cria linha, os blocos User, Agent, Atividade observável, Tool Call e Tool Result aparecem, e Tool Call/Result são marcados como stub. Collapse e close são ações separadas.
8. **Persistência e histórico. Saúde: boa.** O thread permaneceu ao navegar para Study e ao voltar pelo histórico do browser.
9. **Mobile e bottom sheet. Saúde: boa.** O rail vira bottom navigation e o Chat abre acima dela. A navegação continua visível e utilizável, sem overflow horizontal nos viewports auditados.

## Pontos fortes

- A assinatura visual é o traço real do workflow, não uma grade uniforme de cards.
- A cor vermilion é o único accent e success depende de checks e geometria preenchida.
- Project, StudyRevision, RunSpec, AdmissionRecord, Run, job e attempt permanecem visualmente e semanticamente distintos.
- O Chat não faz auto-scroll ao inserir novos blocos, preservando a posição do operador.
- O estado do Agent é anunciado em uma live region e o spinner é uma sequência de segmentos, não um círculo genérico.
- Phosphor Icons é a única família de ícones.

## Achados e correções

### P0

Nenhum achado P0 no escopo auditado.

### P1

Nenhum achado P1 aberto no estado final.

### P2 corrigidos

1. **Índices verticais decorativos em Projects.** A primeira captura usava `01`, `02` e `03` como decoração, contrariando o brief. Os índices foram removidos e substituídos por um accent lateral sem conteúdo fictício.
2. **Conteúdo do Project encostado no accent após a remoção.** A recaptura mostrou ícone e texto comprimidos contra a borda. O padding interno foi corrigido e a captura final foi refeita em `02-projects-desktop.jpg`.

Não restam achados P0, P1 ou P2 abertos dentro dos viewports e estados capturados.

### Segunda passagem após QA independente

A QA independente posterior encontrou quatro regressões de fluxo no snapshot anterior. Todas foram corrigidas e recapturadas:

1. **P1 corrigido: records cruzavam a fronteira do Project.** Study e Runs agora exigem vínculo explícito com o Project ativo. Context Drift Review, Tool Permission Audit e Projects novos recebem um gate fail-closed sem enqueue, Start Run ou records de Retrieval Quality.
2. **P1 corrigido: Project novo herdava StudyRevision no traço.** O traço acompanha `selectedProject.currentStage`; Citation Boundary QA ficou com `Intento` como único step atual.
3. **P2 corrigido: listbox não implementava teclado.** ArrowDown, ArrowUp, Home, End, Enter, Space e Escape foram exercitados, com foco nas options e retorno ao gatilho.
4. **P2 corrigido: o Chat perdia foco no envio.** O composer permanece focado e read-only durante a atividade, volta a editável após sucesso ou falha e entrega o próximo Tab ao grip adjacente.

Os quatro comportamentos têm cobertura automatizada e evidência Chrome fresca em `11-project-scope-study.png` a `14-chat-focus-retained.png`. Nenhum P0, P1 ou P2 permanece aberto nessa segunda passagem.

## Acessibilidade observada

- Estrutura semântica com `main`, `nav`, headings, regions, articles, description lists e dialog.
- Labels visíveis acima dos campos, helper text e erro com `role=alert`.
- Foco visível com outline de alto contraste.
- Operações centrais disponíveis por teclado, incluindo navegação, composer, snaps explícitos e fechamento do diálogo.
- `aria-current`, `aria-pressed`, `aria-expanded`, `aria-live` e nomes acessíveis refletem estado.
- `prefers-reduced-motion` desativa animações e Motion recebe fallback estático.
- Nenhum overflow horizontal foi detectado em 1440 x 660 ou 390 x 660.

## Limites da evidência

- Screenshots e DOM não provam conformidade WCAG completa.
- Não houve teste com leitor de tela, zoom de 200%, alto contraste do sistema ou dispositivo físico com touch.
- O in-app Browser não estava disponível; a auditoria usou o Chrome selecionado pelo runtime e não cobriu Safari/WebKit.
- O backend é inteiramente stub. Nenhuma chamada real, persistência canônica, HumanAttestationRecord ou integração de Workspace foi exercitada.
- A API de screenshot do Chrome salvou áreas de 1425 x 653 ou 1440 x 660 em desktop e 375 x 635 em mobile, embora o viewport de layout avaliado fosse 1440 x 660 e 390 x 660. As imagens foram inspecionadas na dimensão realmente salva.

## Evidência visual

- `qa/screenshots/01-lab-desktop.jpg`
- `qa/screenshots/02-projects-desktop.jpg`
- `qa/screenshots/03-study-admission-desktop.jpg`
- `qa/screenshots/04-admission-correction-desktop.jpg`
- `qa/screenshots/05-runs-completed-desktop.jpg`
- `qa/screenshots/06-runs-evidence-desktop.jpg`
- `qa/screenshots/07-chat-agent-desktop.jpg`
- `qa/screenshots/08-lab-mobile.jpg`
- `qa/screenshots/09-study-mobile.jpg`
- `qa/screenshots/10-chat-mobile.jpg`
- `qa/screenshots/11-project-scope-study.png`
- `qa/screenshots/12-project-scope-runs.png`
- `qa/screenshots/13-new-project-intent-trace.png`
- `qa/screenshots/14-chat-focus-retained.png`
