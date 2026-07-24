# QA independente - Spatial Trace

Data: 23 de julho de 2026  
Fuso: America/Asuncion  
Escopo exclusivo: `design/operator-console-prototypes/04-spatial-trace`  
Resultado executivo do snapshot original: bloqueado por 2 achados P1 e 2 achados P2.  
Resultado vigente após a revalidação de 23 de julho de 2026: aprovado, sem P0/P1/P2 aberto.

## Snapshot e método

A auditoria foi executada contra uma cópia isolada do protótipo, criada antes da navegação, para não escrever build, cache, testes ou screenshots no workspace. Os quatro arquivos centrais do snapshot tinham estes SHA-256:

| Arquivo | SHA-256 |
| --- | --- |
| `src/App.jsx` | `36b42c1e0496cf5441bfaccedd8c78664aa3e4adb3b12bc4c2fb735e1a720090` |
| `src/routes/ProjectsView.jsx` | `79a0f8ae1b92e557b7ead6c154ef1014954b8483270d7a02dba7a0213667559c` |
| `src/components/AppShell.jsx` | `d794ab5ba9ea82b74d5613d69342e982cdc2f7fd5cb45b22feb2c40e05d83724` |
| `src/components/ChatDock.jsx` | `cba525dccb701b70b294381b8e45a4eaeae2d22889abb4d9ed231fdc13ccbbe2` |

Foram aplicadas as lentes de Product Design Audit, design-taste-frontend e Browser. O navegador embutido não estava disponível nesta sessão; a inspeção interativa usou o Chrome controlado, sem Playwright CLI. A triagem foi deliberadamente limitada a P0, P1 e P2. Nenhum protótipo irmão foi aberto ou usado como referência.

Durante o fechamento deste relatório, arquivos do alvo receberam alterações externas à auditoria depois da criação do snapshot. Essas alterações não foram tratadas como correções verificadas e não mudam o resultado abaixo. Qualquer tentativa de liberar o protótipo deve repetir a QA independente sobre um novo snapshot estável.

## Leitura de design

O protótipo se apresenta como um console técnico regulado para operadores: frio, espacial e verificável, com o fluxo Project -> StudyRevision -> RunSpecs -> Admissions -> Runs -> Avaliações -> Evidência como metáfora central.

| Dial | Leitura |
| --- | ---: |
| Seriedade | 7/10 |
| Densidade | 5/10 |
| Expressividade | 6/10 |

## Achados do snapshot original

Os quatro achados abaixo documentam o snapshot original. Todos foram reproduzidos novamente depois das correções e estão fechados na seção `Revalidation after fixes`.

Nenhum P0 foi observado.

### P1-01 - Study e Runs vazam records de outro Project

**Evidência reproduzível**

1. Em `/projects`, selecionar `Context Drift Review`.
2. Confirmar que o switcher superior e o mapa mostram `Context Drift Review`, cujo estágio é `revision` e cuja próxima ação é revisar o draft local.
3. Navegar para `/study`.
4. A tela continua exibindo a Study `Respostas com fontes insuficientes`, scenario `source-grounding-check`, `stub-runspec-direct-01`, `stub-runspec-evidence-01` e seus AdmissionRecords.
5. Navegar para `/runs`.
6. A tela continua exibindo e permite iniciar `stub-run-evidence-first`, inclusive seus eventos, EvaluationRecord e bundle, enquanto o switcher superior permanece em `Context Drift Review`.

O comportamento também foi reproduzido com um Project recém-criado, que declara `Study ainda não definido`. No snapshot, `App.jsx:56-61` renderiza `StudyView` e `RunsView` sem Project ou inventário vinculado; `StudyView.jsx:66-94` e `RunsView.jsx:78-110` leem os records stub globais.

Screenshots da sessão: `03-study-project-mismatch.jpg`, `04-runs-project-mismatch.jpg` e `05-runs-completed.jpg`.

**Impacto**

Este é um erro de escopo e de verdade operacional. Um operador pode interpretar Admission, Run e evidência de `Retrieval Quality` como pertencentes a `Context Drift Review` ou a um Project vazio. A falha quebra o desfecho central do protótipo e pode induzir enqueue ou leitura de evidência sob o contexto errado.

**Correção exigida**

O Project selecionado deve governar a Study, os RunSpecs, as Admissions, as Runs e a evidência renderizada. Para Project sem records vinculados, Study e Runs devem falhar fechado com estado vazio explícito e nenhum controle de enqueue/início. A correção precisa incluir teste que alterne entre cada Project, crie um Project vazio e confirme tanto a presença dos records corretos quanto a ausência dos records de outros escopos.

### P1-02 - Project recém-criado mostra duas posições atuais incompatíveis

**Evidência reproduzível**

1. Selecionar `Context Drift Review`, cujo traço local estava em `StudyRevision` durante a exploração.
2. Acionar `Criar Project`.
3. Submeter `Citation Boundary` com o propósito `Verificar fronteiras de citação em dados locais.`.
4. O novo card é selecionado e declara `Posição atual: intent`; sua próxima ação é `Criar uma StudyRevision local`.
5. No mesmo painel, o traço mantém `StudyRevision` com `aria-current="step"` e o detalhe `Draft versionado`.

No snapshot, `ProjectsView.jsx:121` inicializa `traceStage` uma vez; `ProjectsView.jsx:124-127` o sincroniza apenas no handler de seleção; e `ProjectsView.jsx:206-208` cria/seleciona o novo Project sem atualizar o estágio local.

Screenshot da sessão: `07-project-created.jpg`.

**Impacto**

O mapa principal afirma simultaneamente que a posição atual é `intent` e `StudyRevision`. Como a posição no workflow é a proposta central da interface, o erro pode orientar o operador para o gate errado logo após criar um escopo.

**Correção exigida**

Derivar o estágio visível do `selectedProject.currentStage` ou sincronizar a seleção e o estágio de forma atômica. O teste de regressão deve criar um Project depois de explorar outro estágio e exigir que card, texto de próxima ação e único `aria-current="step"` concordem com `intent`.

### P2-01 - Project switcher declara listbox sem implementar seu teclado

**Evidência reproduzível**

1. Focar o botão do Project switcher e abri-lo.
2. O popup expõe `role="listbox"` com filhos `role="option"`.
3. O foco permanece no gatilho.
4. Pressionar `ArrowDown`: o foco e a opção ativa não mudam.
5. Pressionar `Escape`: `aria-expanded` continua `true` e o popup permanece aberto.

No snapshot, `AppShell.jsx:39-50` só fecha por clique fora; `AppShell.jsx:54-59` alterna por clique; e `AppShell.jsx:72-95` atribui papéis de listbox/option sem foco roving, `aria-activedescendant`, setas, Home/End, Enter/Space ou Escape.

**Impacto**

Usuários de teclado e leitores de tela recebem a promessa semântica de um listbox, mas não o modelo de interação esperado. A troca de Project fica mais custosa e imprevisível exatamente no controle global de escopo.

**Correção exigida**

Implementar um listbox completo, com foco na opção selecionada ao abrir, setas, Home/End, Enter/Space, Escape e retorno de foco ao gatilho; ou trocar para um padrão semântico mais simples que corresponda ao comportamento real. Adicionar teste navegável de teclado, não apenas click test.

### P2-02 - Chat perde o foco depois de enviar, tanto em sucesso quanto em falha

**Evidência reproduzível**

1. Abrir o Chat e focar `Mensagem para o Lab Agent`.
2. `Shift+Enter` cria corretamente uma nova linha.
3. Pressionar `Enter` para enviar.
4. Durante a atividade, o `textarea` fica `disabled`; o foco cai em `BODY`.
5. Depois do terminal de sucesso, o composer volta a habilitar, mas o foco permanece em `BODY`.
6. O próximo `Tab` vai para o skip link, não para o composer ou para um controle adjacente do Chat.
7. Repetir com uma mensagem contendo `falhar`: o mesmo ocorre no terminal de falha.

No snapshot, `ChatDock.jsx:147-171` inicia e termina a sequência sem restaurar foco; `ChatDock.jsx:319-332` desabilita simultaneamente textarea e botão durante `running`.

**Impacto**

O usuário de teclado perde o ponto de trabalho a cada envio e precisa atravessar novamente a página para continuar a conversa. O problema afeta o loop primário do Chat em todos os terminais.

**Correção exigida**

Manter o composer focável durante a execução usando `readOnly`/`aria-disabled` quando adequado, ou restaurar explicitamente o foco ao terminar em sucesso ou falha. O teste deve afirmar `document.activeElement` durante e depois dos dois terminais.

## Gates automatizados

Todos os comandos abaixo foram executados na cópia isolada do snapshot auditado.

| Gate | Resultado |
| --- | --- |
| `npm test` | passou: 1 arquivo, 7/7 testes |
| `npm run build` | passou: Vite 6.4.2, 4.982 módulos transformados, CSS 49,47 kB, JS 457,06 kB |
| `npm run test:sites` | passou: 4/4 testes |
| Console do navegador | passou: 0 erros e 0 warnings |
| `<main>` | passou: exatamente um nas quatro rotas |
| Overflow horizontal | passou em 1440x940, 834x1112 e 390x844 |
| Navegação responsiva | passou: rail no desktop/tablet e bottom nav no mobile |
| Foco visível inicial | passou: skip link com outline sólido de 3 px |

Os testes automatizados existentes não detectaram os quatro bloqueadores acima. O verde da suíte, portanto, não representa aprovação do fluxo completo.

## Cobertura do fluxo principal

1. **Lab:** abriu em `/`, manteve o Project selecionado e mostrou escopo, workflow e próxima ação no primeiro viewport. Não misturou superfícies de Study ou Runs.
2. **Projects:** seleção de Projects atualizou o switcher e o mapa sem reload. O diálogo validou nome vazio, criou o Project e deixou explícito que Workspace/filesystem não estão integrados. O desalinhamento P1-02 ocorreu no traço após a criação.
3. **Study e compilação:** a equação `1 scenario x 2 variantes x 1 repetição = 2 RunSpecs` ficou legível. A troca de Project revelou o vazamento P1-01.
4. **Admission:** a variante `direct-answer` rejeitada mostrou `max_turns` solicitado 3 contra suportado 1 e manteve enqueue desabilitado. `Corrigir em novo draft` preservou o record rejeitado e apresentou uma correção separada. A variante `evidence-first` admitida permitiu enqueue stub.
5. **Run:** o lifecycle observado foi `Na fila -> Preparando -> Executando -> Avaliando -> Terminal`. A sequência factual foi `run.queued`, `attempt.prepared`, `subject.invoked`, `tool.called`, `tool.completed`, `subject.responded`, `evaluation.completed`, `run.completed`. A falha terminou por `run.failed` sem stack ou exceção sensível. Nenhum controle de pause/resume foi anunciado.
6. **Evidência:** o inspector mostrou `artifact_content=references_only`, `portable=false` e `replayable=false`; não prometeu blobs, restore ou replay. Job e attempt permaneceram operacionais e subordinados à Run.
7. **Chat em sucesso:** envio vazio ficou bloqueado; `Shift+Enter` e `Enter` tiveram funções distintas; o spinner customizado apareceu acima do composer. O thread exibiu Agent, User, atividade observável, Tool Call, Tool Result e Agent. Tool Call/Result estavam marcados como `Demonstração stub`; nenhuma cadeia privada de raciocínio foi exposta.
8. **Chat em falha e persistência:** a mensagem com `falhar` produziu terminal controlado. Fechar, recolher, reabrir e trocar de rota preservou thread, estado e snap. As geometrias observadas no desktop foram aproximadamente 410x390, 410x526, 410x733 e 780x896 para compacto, meio, alto e thread completo.
9. **Navegação e teclado:** links das quatro rotas e Back do navegador mantiveram uma única superfície primária coerente. Skip link e foco visível passaram. O switcher e a continuidade de foco do Chat falharam conforme P2-01 e P2-02.

## Inspeção visual e responsiva

### Desktop - 1440x940

- Hierarquia forte: rail, Project global, título de rota, superfície de trabalho e Chat se distinguem sem depender apenas de cor.
- O primeiro viewport comunica escopo, posição do workflow e próxima ação.
- A paleta porcelana/carvão com um único acento vermelhão sustenta o caráter técnico sem virar um painel genérico de cards.
- Phosphor é usado de forma consistente; o ícone de banco de dados aparece como referência neutra, não como ação primária; nenhum ícone de balança aparece na comparação.
- Não houve overflow horizontal nem conteúdo primário cortado.

### Tablet - 834x1112

- O rail permanece legível com Lab, Projects, Study e Runs.
- A Study reorganiza suas duas variantes sem colisão e mantém os dois estados de Admission comparáveis.
- O Chat recolhido ocupa o canto inferior direito sem esconder a navegação primária.
- Não houve overflow horizontal.

### Mobile - 390x844

- O rail desaparece e o bottom nav permanece visível com as quatro rotas.
- Com Chat recolhido, o launcher termina acima do bottom nav.
- Com Chat aberto em snap alto, a sheet ocupou `left=8`, `right=367`, `top=76`, `bottom=760`; o nav começou em `top=768`, portanto continuou alcançável.
- O thread, composer e botão de fechar permaneceram utilizáveis, e a troca de rota não descartou mensagens.
- Não houve overflow horizontal.

## Acessibilidade e qualidade de implementação

- Há exatamente um `<main>` por rota e um skip link funcional.
- `prefers-reduced-motion` aparece no CSS e os componentes principais consultam `useReducedMotion`.
- Os ícones vêm de uma biblioteca consistente; não foram encontrados emoji, SVG artesanal, Lucide ou assets falsificados por texto.
- Não foram encontrados secrets, provider real ou chamada de rede da aplicação. Tool calls, enqueue e Runs permanecem claramente stubs.
- Timers do Chat e da máquina de Run possuem cleanup. A implementação está dividida por shell, rotas, Chat, traço e hooks, sem concentrar tudo no `App`.
- As duas falhas de teclado são localizadas, mas bloqueiam a aprovação por afetarem controles primários.

## Pontos fortes confirmados

- A direção visual é própria e coerente com o nome Spatial Trace.
- Study, RunSpec, AdmissionRecord, Run, Job, attempt, EvaluationRecord e Evidence Bundle são apresentados como entidades distintas.
- A rejeição por capability incompatível falha fechado e a correção preserva a semântica append-only.
- A interface não transforma Chat em autoridade humana nem o inclui no SubjectEnvelope.
- O lifecycle de Run, o terminal por timeout/falha e as limitações de bundle são comunicados sem prometer capacidades ausentes.
- O Chat oferece estados determinísticos, atividade observável e stubs explicitamente rotulados, sem simular ações reais.

## Limites desta evidência

- Navegador verificado: Chrome. Safari/WebKit não foi validado.
- Não houve leitor de tela real, zoom de 200%, alto contraste do sistema ou dispositivo touch físico.
- O long press do grip não foi validado em interação física porque a superfície de controle disponível não ofereceu duração de hold confiável; somente os botões explícitos de snap e a cobertura automatizada existente foram verificados.
- Os dados e execuções são stubs offline. Nenhuma integração externa ou autoridade humana real foi inferida.
- Os screenshots novos ficaram somente em `/private/tmp/evidrun-spatial-qa.fQjQQm/qa-current/` para respeitar a regra de que apenas este relatório poderia ser escrito no workspace. As dez capturas pré-existentes em `qa/screenshots/` também foram inspecionadas, mas não tratadas como prova suficiente por si só.
- Como o alvo mudou externamente depois do congelamento, os bloqueadores só podem ser considerados resolvidos após nova execução independente dos passos acima sobre o estado final.

## Revalidation after fixes - 23 de julho de 2026

Horário da execução: 22:32-22:40 em America/Asuncion.  
Alvo final: `http://localhost:4304/`, servido diretamente por `design/operator-console-prototypes/04-spatial-trace`.  
Navegador: Chrome real, porque o Browser embutido permaneceu indisponível.  
Escopo: somente os quatro achados anteriores, gates automatizados, console, `<main>` e overflow desktop/tablet/mobile. Nenhum protótipo irmão foi inspecionado.

### Estado revalidado

Os checksums dos arquivos diretamente envolvidos nas correções foram:

| Arquivo | SHA-256 |
| --- | --- |
| `src/App.jsx` | `be8e62506a49df8b9c33f540e69e9a4f7b679d66b3b5ca50acfb5b20d2480f1a` |
| `src/routes/ProjectsView.jsx` | `e696a7d1587f80af4f499d6592eb21c89c081b1060378323bd736a711b648800` |
| `src/components/AppShell.jsx` | `1c2f0d3755497b4e75ca840b002c3cd4f6e4ec9ff260f7d520925890a38156a9` |
| `src/components/ChatDock.jsx` | `174629b1ecaffd7237bbc31bb105680045accea15e5bae9c2beaa3d267240186` |
| `src/routes/StudyView.jsx` | `5470386a91c5d7fffe3631745c75313b713a288b19458fa7e0767f84fdaa8cd0` |
| `src/routes/RunsView.jsx` | `4f62ea72902409fddad69c5f97221fab58a054ba6ece337816399494bb429fb6` |
| `tests/app.test.jsx` | `c3c7ba47e3b6a6ca58545e21ae69f3f2f4da143911b35a889ac19824d1fd463b` |

### Resultado dos quatro regressions

| Finding original | Reprodução no estado final | Resultado |
| --- | --- | --- |
| P1-01, records cruzados entre Projects | Selecionado `Context Drift Review`: `/study` mostrou `Nenhuma Admission representada para este Project.`, sem `stub-revision-07`, RunSpecs ou enqueue; `/runs` mostrou `Nenhuma Run representada para este Project.`, sem `stub-run-evidence-first`, Start Run ou `Bundle v2 stub`. O mesmo foi repetido com o Project novo `Citation Boundary Revalidated`. | Fechado |
| P1-02, novo Project herdava `StudyRevision` | Após criar `Citation Boundary Revalidated`, o card selecionado declarou `currentStage=intent`, a próxima ação foi `Criar uma StudyRevision local` e existiu exatamente um `aria-current="step"`, em `Intento` com `href=/projects`. | Fechado |
| P2-01, listbox sem teclado | `ArrowDown` e `ArrowUp` no gatilho abriram o listbox com foco na opção selecionada. Dentro dele, `ArrowDown`, `ArrowUp`, `Home` e `End` moveram o foco corretamente, inclusive wrap. `Enter` selecionou `Tool Permission Audit`; `Space` selecionou `Retrieval Quality`; `Escape` fechou. Enter, Space e Escape retornaram o foco ao gatilho com `aria-expanded=false`. | Fechado |
| P2-02, composer perdia foco | Em sucesso e falha, durante `running`, `activeElement.id=lab-agent-composer`, `bodyFocused=false`, `readOnly=true` e `aria-busy=true`. Nos dois terminais, o mesmo composer continuou focado, voltou a `readOnly=false` e `aria-busy=false`. O próximo `Tab` foi para `Segure para escolher o encaixe do Chat`, não para o skip link. | Fechado |

### Gates repetidos

Os comandos foram executados numa cópia isolada do estado final, sem escrever build ou cache no workspace.

| Gate | Resultado final |
| --- | --- |
| `npm test` | passou: 1 arquivo, 10/10 testes, 0 falhas |
| `npm run build` | passou: Vite 6.4.2, 4.982 módulos, CSS 51,31 kB (gzip 10,73 kB), JS 462,97 kB (gzip 138,18 kB) |
| `npm run test:sites` | passou: 4/4 testes, 0 falhas |
| Console Chrome | passou: `[]` para erros, warnings e warnings normalizados |
| Quatro rotas | passou: Lab, Projects, Study e Runs mantiveram exatamente um `<main>` |

### Viewports e overflow

| Viewport | Estrutura observada | Overflow horizontal |
| --- | --- | --- |
| Desktop 1440x940 | `mainCount=1`; rail e Chat aberto; `clientWidth=1425`, `scrollWidth=1425` | não |
| Tablet 834x1112 | `mainCount=1`; rail `flex`, mobile nav oculto; `clientWidth=834`, `scrollWidth=834` | não |
| Mobile 390x844 | `mainCount=1`; rail oculto, mobile nav `grid`; `clientWidth=375`, `scrollWidth=375` | não |

No mobile com Chat aberto, a sheet terminou em `bottom=760` e o bottom nav começou em `top=768`; a navegação permaneceu descoberta e alcançável.

### Screenshots aceitos nesta revalidação

As capturas foram salvas e abertas novamente antes de serem aceitas:

- `/private/tmp/evidrun-spatial-revalidate.BAo3MS/qa-current/02-switcher-keyboard.jpg`
- `/private/tmp/evidrun-spatial-revalidate.BAo3MS/qa-current/03-context-study-gate.jpg`
- `/private/tmp/evidrun-spatial-revalidate.BAo3MS/qa-current/04-context-runs-gate.jpg`
- `/private/tmp/evidrun-spatial-revalidate.BAo3MS/qa-current/05-new-project-intent.jpg`
- `/private/tmp/evidrun-spatial-revalidate.BAo3MS/qa-current/06-new-project-study-gate.jpg`
- `/private/tmp/evidrun-spatial-revalidate.BAo3MS/qa-current/07-new-project-runs-gate.jpg`
- `/private/tmp/evidrun-spatial-revalidate.BAo3MS/qa-current/08-chat-success-focus.jpg`
- `/private/tmp/evidrun-spatial-revalidate.BAo3MS/qa-current/09-chat-failure-focus.jpg`
- `/private/tmp/evidrun-spatial-revalidate.BAo3MS/qa-current/10-tablet.jpg`
- `/private/tmp/evidrun-spatial-revalidate.BAo3MS/qa-current/11-mobile.jpg`

### Decisão

Os quatro blockers anteriores estão fechados no estado final revalidado. Nenhum novo P0, P1 ou P2 apareceu nos fluxos e viewports pedidos. Permanecem apenas os limites gerais já documentados para Safari/WebKit, leitor de tela real, zoom de 200%, alto contraste e dispositivo touch físico; eles não foram convertidos em achados nesta revalidação focada.

Bloqueadores remanescentes: nenhum P0/P1/P2.

independent result: passed
