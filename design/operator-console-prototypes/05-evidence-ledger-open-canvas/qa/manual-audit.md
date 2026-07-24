# Auditoria manual do protótipo

## Escopo

Auditoria combinada de UX, comportamento responsivo e riscos de acessibilidade do protótipo isolado `05-evidence-ledger-open-canvas`. A validação foi feita em Chrome controlado, com o servidor local na porta 4305, dados determinísticos e sem provider, backend, repositório ou adapter de autoridade reais.

## Objetivo do usuário e alvo de acessibilidade

O operador precisa orientar uma investigação, entender a proveniência entre StudyRevision, RunSpec, AdmissionRecord, Run, EvaluationRecord e Comparison, distinguir estados ilustrativos de records capturados e consultar evidência sem atribuir autoridade humana ou capacidade não implementada. O alvo desta auditoria foi navegação por teclado, semântica estrutural, reflow nos viewports pedidos, feedback de estado e recuperação de erros. Não é uma certificação WCAG.

## Passos auditados

1. **Lab, primeiro uso: saudável.** A entrada principal, o aviso de stub, o estado vazio e a separação entre Chat e SubjectEnvelope são legíveis. O botão de envio inicia desabilitado.
2. **Lab Agent, retorno: saudável.** Enter dispara o reducer determinístico, `Atividade observável` expõe progresso e o foco retorna ao composer no estado terminal. Tool Call e Tool Result só aparecem sob o rótulo de contexto ilustrativo autorizado.
3. **Projects e inspector: saudável.** A revisão se divide em dois RunSpecs e converge em uma Comparison. A seleção de um nó atualiza o inspector; Workspace permanece uma fronteira separada e pendente.
4. **Criação local de Project: saudável.** O diálogo retém foco, valida nome e descrição, mostra mensagens específicas e fecha após criação local bem-sucedida.
5. **Study e Admission: saudável.** O head RunSpec é rejeitado por `max_turns=3` contra o suporte ativo de uma interação. O tail RunSpec é admitido e apenas então habilita enqueue.
6. **Run concluída: saudável.** A fixture CRL apresenta exatamente nove eventos, sem eventos de tool, com job e attempt separados e limitações do Bundle explícitas.
7. **Run live ilustrativa: saudável.** A sequência com `read_text` fica fora da fixture CRL, usa identidade de demonstração e não anuncia persistência.
8. **Chat adaptativo: saudável.** Abrir, ampliar, colapsar e fechar são operações distintas. O contexto acompanha a rota; o slider aceita teclado e os snaps persistem entre navegações.
9. **Tablet 834 x 1112: saudável após correção.** O shell mantém sidebar, as colunas secundárias refluem e os utilitários do topbar viram botões de ícone sem colisão.
10. **Mobile 390 x 844: saudável após correção.** A sidebar dá lugar à navegação inferior, o Chat vira bottom sheet e cada mudança de rota volta ao topo sem overflow horizontal do documento.

## Pontos fortes

- Hierarquia visual fria e editorial, com baixa ornamentação, bordas discretas e cobalt reservado para ação, seleção e proveniência.
- Labels humanos dominam a leitura; IDs técnicos usam IBM Plex Mono e permanecem secundários.
- Estados reais da fixture, estados locais e estados ilustrativos são rotulados de forma distinta.
- Admission falha fechado; autoridade indisponível não é apresentada como autoridade humana.
- `SubjectEnvelope digest`, `references_only`, `portable=false` e `replayable=false` preservam os limites do domínio.
- Os componentes interativos têm nomes acessíveis, foco visível e controles de teclado cobertos por teste.

## Achados corrigidos durante a auditoria

- **P2, navegação lateral:** `Study & Admission` quebrava em duas linhas em desktop. Espaçamento e tipografia foram ajustados sem reduzir a área clicável.
- **P2, primeiro uso:** três cartões genéricos diluíam a leitura do fluxo. Foram convertidos em uma sequência editorial com conectores de ícone reais.
- **P1, topbar tablet:** os rótulos Documentação e Configurações colidiam no viewport de 834 px. No intervalo de tablet, os controles conservam nome acessível e mostram apenas os ícones.
- **P1, troca de rota mobile:** a posição de scroll da tela anterior podia esconder o título da nova rota. Navegação e `popstate` agora restauram o início e focam o conteúdo sem scroll adicional.

## Riscos e limites

- Não restou achado acionável P0, P1 ou P2 no escopo capturado.
- Contraste foi avaliado visualmente, sem medição colorimétrica automatizada.
- Leitores de tela reais, zoom de sistema, alto contraste do sistema operacional e navegação por voz não foram executados.
- O Browser disponível nesta sessão foi a extensão do Chrome; o browser interno não estava disponível. Safari, Firefox e dispositivos físicos não foram validados.
- Pointer hold de 350 ms e animações foram cobertos pela implementação e testes, mas a sensação tátil em trackpad e touch físico permanece fora do escopo.
- Nenhum comportamento de backend, provider, persistência, autoridade, exportação ou integridade remota foi inferido a partir do stub.

## Evidência visual aceita

- `qa/screenshots/01-lab-first-use-desktop-final.png`
- `qa/screenshots/01b-lab-return-desktop.png`
- `qa/screenshots/02-projects-desktop.png`
- `qa/screenshots/03-study-rejected-desktop.png`
- `qa/screenshots/03b-study-admitted-desktop.png`
- `qa/screenshots/04-run-completed-desktop.png`
- `qa/screenshots/05-run-live-desktop.png`
- `qa/screenshots/06-run-live-chat-desktop.png`
- `qa/screenshots/08-study-tablet.png`
- `qa/screenshots/09-lab-mobile.png`
- `qa/screenshots/10-chat-mobile.png`
- `qa/screenshots/compare-01-lab-side-by-side.png`

## Resultado

Saudável para o objetivo de protótipo local isolado. A auditoria não identifica diferença P0, P1 ou P2 que ainda prejudique hierarquia, compreensão ou uso nos fluxos e viewports pedidos.

