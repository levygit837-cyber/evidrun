# Auditoria independente da imagem - Carbon Rhythm

## Findings

### P0

Nenhum bloqueador P0. A imagem estabelece hierarquia, materialidade e anatomia suficientes para orientar um protótipo React. A implementação deve usá-la como referência de composição e densidade, não como pixel copy.

### P1

#### P1.1 - As fronteiras de Chat, SubjectEnvelope e autoridade do draft não aparecem

- **Região visível:** coluna direita com o título `Chat` e a pergunta `O que mudou depois do deploy?`; bloco central rotulado apenas `Agente`.
- **Evidência:** o Chat repete a pergunta associada à Run, mas não há qualquer indicação de que esse Chat pertence ao operador e está fora do `SubjectEnvelope`. A resposta do Agente também não é marcada como draft.
- **Classificação:** incompatibilidade de domínio e autoridade, não preferência visual. A composição pode levar o builder a conectar o thread lateral ao Subject Agent ou a apresentar a resposta como decisão aceita.
- **Correção concreta:** exibir `Chat do operador` e uma linha persistente `Fora do SubjectEnvelope` no cabeçalho do dock. No preview central, usar `Agente · draft do Lab Agent` ou `Draft do Lab Agent` como texto secundário, sem transformar o aviso em um pill dominante. Modelar Chat, Subject e draft como fontes de estado separadas; nenhum conteúdo do dock entra no envelope por proximidade visual.

#### P1.2 - O estágio corrente e o evento inspecionado parecem ser o mesmo estado

- **Região visível:** workflow horizontal com `Avaliação` em laranja e card imediatamente abaixo com `tool.completed: read_text`.
- **Evidência:** `Avaliação` comunica claramente o estágio corrente, enquanto `tool.completed` pertence à etapa anterior, `Leitura da tool`. Como o card não informa qual etapa está selecionada, ele parece ser o detalhe de `Avaliação`.
- **Classificação:** ambiguidade do modelo de execução, não escolha estética.
- **Correção concreta:** manter estados independentes, por exemplo `currentStage="evaluation"` e `selectedStage="tool-read"`. Aplicar `aria-current="step"` somente a `Avaliação`; indicar seleção de `Leitura da tool` com outline, marcador ou `aria-pressed` quando os estágios abrirem o inspector. Titular o card `Evento selecionado · Leitura da tool`. Se os estágios não forem interativos, remover aparência e cursor de botão e abrir o inspector por uma lista de eventos real. Rotular a faixa como `Traço da demonstração` para não apresentá-la como o lifecycle canônico completo, que inclui admissão antes da Run.

#### P1.3 - O estado de execução contradiz o composer

- **Região visível:** spinner `Preparando resposta verificável`, composer com borda laranja em toda a volta e botão de envio cinza no canto inferior direito.
- **Evidência:** o spinner comunica Run em andamento; a borda laranja parece foco ativo; o campo convida a escrever; o avião de envio parece apenas de baixa ênfase, não inequivocamente desabilitado. O helper `Seja específico para melhores respostas.` não explica a indisponibilidade.
- **Classificação:** falha visual do estado mostrado. O comportamento efetivo continua não verificável na imagem estática.
- **Correção concreta:** dirigir `ExecutionStatus` e `Composer` pela mesma máquina de estados, no mínimo `idle | running | ready | failed | terminal`. Em `running`, usar `aria-busy="true"`; deixar a borda neutra e aplicar o laranja apenas em `:focus-within`. Se editar um próximo draft for permitido, manter o textarea editável, desabilitar apenas o envio e trocar o helper por `Envio disponível após a resposta atual`. Caso contrário, desabilitar todo o composer com explicação visível. Usar o atributo `disabled`, `aria-disabled` quando necessário e um tratamento além de opacidade para distinguir o botão.

#### P1.4 - O Chat domina o canvas e o preview de snap está cortado

- **Região visível:** dock entre aproximadamente x=990 e x=1380, com cerca de 390 px, e contorno tracejado entre x=1383 e o limite direito da imagem.
- **Evidência:** o dock ocupa aproximadamente 27% dos 1440 px e reduz a área operacional; o ghost tracejado termina fora do viewport e pode ser interpretado como um segundo painel permanente ou quebrado.
- **Classificação:** falha visível de layout e de comunicação do snap.
- **Correção concreta:** em desktop largo, usar `grid-template-columns: minmax(0, 1fr) clamp(17rem, 22vw, 20rem)` e `min-width: 0` no canvas. Renderizar `SnapPreview` de forma absoluta dentro do shell, somente durante long press ou comando equivalente, com `inset` que preserve todo o contorno no viewport. O preview deve ter fill tonal leve, label do destino e `pointer-events: none`, nunca aumentar a largura rolável da página.

#### P1.5 - `Alternar estado` não declara se está disponível ou desabilitado

- **Região visível:** coluna direita do card `tool.completed`, abaixo de `Abrir evidência`.
- **Evidência:** texto e ícone de `Alternar estado` têm contraste muito menor do que a ação acima. O controle parece desabilitado, mas não há motivo, label de estado ou diferença estrutural que confirme isso.
- **Classificação:** risco de usabilidade e acessibilidade. A imagem não prova seu comportamento.
- **Correção concreta:** se for ação disponível, elevar texto e ícone a contraste AA, adicionar hover, active e foco visível e manter o label `Alternar estado`. Se for futura ou indisponível, aplicar `disabled`, retirar da ordem de tabulação nativa e explicar `Disponível somente na demonstração interativa` ou o motivo real em texto associado. Não usar baixa opacidade como única semântica.

### P2

#### P2.1 - Parte da microcopy está pequena e suave demais para função operacional

- **Região visível:** status `Stub local ativo` no topo, metadata `Job / Tentativa / Run`, helper do composer e instrução no rodapé do Chat.
- **Evidência:** esses textos são visivelmente menores e menos contrastantes que o body principal; a instrução do Chat ainda aparece em itálico e quebra em duas linhas.
- **Limite:** a imagem permite apontar risco, mas não medir tamanho CSS nem razão de contraste exata.
- **Correção concreta:** usar body `16/24`, texto secundário no mínimo `14/20`, mono `13/18` apenas para IDs e eventos, e evitar peso abaixo de 400. Medir no DOM contraste de pelo menos 4.5:1 para texto normal e 3:1 para ícones, bordas de foco e componentes. Reservar o nível mais suave apenas a informação realmente descartável.

#### P2.2 - A instrução do dock descreve drag, não long press com snap

- **Região visível:** rodapé do Chat com `Segure e arraste para expandir o Chat para uma área maior`.
- **Evidência:** a frase promete arraste contínuo, enquanto a interação planejada é long press no grip para revelar destinos de snap.
- **Classificação:** incompatibilidade da interação descrita, não preferência de copy.
- **Correção concreta:** usar `Pressione e segure o grip para ver posições do Chat`. Após o threshold, mostrar destinos nomeados e permitir apontar para um deles. Oferecer o mesmo resultado por clique, menu e teclado; não depender de drag ou hold como única via.

#### P2.3 - Os estágios têm boa codificação de progresso, mas aparência de botão sem seleção explícita

- **Região visível:** cinco quadrados do workflow e seus conectores.
- **Evidência:** concluídos usam check e preenchimento, o corrente usa barras e laranja, e o futuro usa círculo e outline. Isso diferencia os estados por forma, label e contraste, não só por cor. Ao mesmo tempo, os quadrados elevados parecem botões e não mostram um estado selecionado separado.
- **Correção concreta:** implementar a faixa como `<ol>` semântica. Se houver inspeção, cada item pode conter um `<button>` com nome acessível `Leitura da tool, concluída, selecionada`; se não houver, usar elementos não interativos. Conectores ficam `aria-hidden`. Aumentar o contraste do check sobre o preenchimento e preservar label textual em todos os estados.

#### P2.4 - `Atividade observável` mistura idioma e ainda precisa de anatomia factual

- **Região visível:** disclosure abaixo da resposta do Agente, com `Preparing context`, `Tool call: read_text` e `Tool result captured`.
- **Evidência:** o título pt-BR delimita bem a área e não há chain-of-thought, mas os três itens em inglês quebram o registro da tela. `Preparing context` é genérico o bastante para ser confundido com raciocínio interno se ganhar texto livre na implementação.
- **Correção concreta:** usar `Preparando contexto`, `Chamada de tool: read_text` e `Resultado da tool capturado`, ou usar nomes de evento estáveis como `tool.call` e `tool.result` com descrição pt-BR. Cada linha deve ser um `ActivityItem` do tipo `status | tool-call | tool-result`, com ícone, label, resumo factual, timestamp e referência `event:` quando existir. Não criar um tipo `thinking` com prosa; não expor reasoning privado, grader ou conteúdo fora do envelope.

#### P2.5 - O spinner lê como medidor de áudio e não como três marcas resolvendo

- **Região visível:** centro inferior, imediatamente acima do composer.
- **Evidência:** a posição e o label são corretos, mas a imagem mostra cinco traços verticais, com um traço central laranja, o que se aproxima mais de um equalizador estático do que das três marcas pedidas.
- **Correção concreta:** criar `ExecutionSpinner` com exatamente três marcas, cada uma com largura de 2 px e alturas distintas em torno de 12, 20 e 28 px. Animar somente `transform: scaleY()` e `opacity`, com fases deslocadas; manter o acento no estado corrente, não em todas as marcas. Incluir `role="status"`, `aria-live="polite"` e o texto visível. Em `prefers-reduced-motion: reduce`, parar a animação e conservar uma composição estática reconhecível.

#### P2.6 - Controles do Chat e grip precisam de ações mais distinguíveis

- **Região visível:** três ícones no canto superior direito do dock e grip circular no divisor central.
- **Evidência:** expandir e compactar usam glifos pequenos e próximos; o primeiro glifo de painéis não explica claramente compactação. O grip é visível, mas o alvo aparente é menor que um alvo confortável.
- **Correção concreta:** adotar uma única família Phosphor com peso global de 1.75: `SidebarSimple` para compactar, `ArrowsOutSimple` para expandir, `X` para fechar e `DotsSixVertical` para o grip. Colocar cada ícone em alvo mínimo de 44 x 44 px, com `aria-label`, tooltip e foco de 2 px. O grip pode continuar circular, mas seu botão e hit area não devem depender apenas do círculo desenhado.

#### P2.7 - Cenário e variantes não formam contexto verificável no frame

- **Região visível:** o cenário `deployment-log-trace` aparece apenas dentro da frase do Agente; `summary-first` e `evidence-first` não aparecem. O card do evento mostra apenas Job, Tentativa e Run.
- **Evidência:** Project, Study, Job, Tentativa e Run estão bem separados, mas a variante ativa não pode ser identificada de relance.
- **Classificação:** omissão de contexto de domínio, não preferência por mais metadata.
- **Correção concreta:** acrescentar uma linha secundária compacta no inspector ou sob o subtítulo da Study, por exemplo `Cenário: deployment-log-trace` e `Variante: evidence-first`. Não criar outro card nem inventar métricas. Preservar `Job`, `Tentativa` e `Run` como campos distintos.

#### P2.8 - `Abrir evidência` parece disponível antes de o estágio Evidência concluir

- **Região visível:** ação `Abrir evidência` no card enquanto `Evidência` permanece como etapa futura em outline.
- **Evidência:** a imagem não esclarece se a ação abre um artifact já capturado, uma referência do evento selecionado ou um bundle futuro.
- **Classificação:** risco de capability e acesso. Uma imagem estática não demonstra resolver, montar ou ler um `ArtifactRef`.
- **Correção concreta:** habilitar a ação somente quando houver referência canônica e adapter de acesso admitido. Se o evento só possui uma ref sem grant de leitura, mostrar `Ver referência` ou desabilitar `Abrir evidência` com motivo. Nunca inferir acesso a partir do ícone, do label ou da existência do `ArtifactRef`.

### P3

#### P3.1 - O ícone grande do evento parece um controle independente

- **Região visível:** quadrado com `>_` à esquerda de `tool.completed: read_text`.
- **Evidência:** borda forte, tamanho e separação fazem o símbolo parecer clicável, embora o card já seja o inspector.
- **Correção concreta:** se for apenas identificador do tipo de evento, reduzir para 32-36 px, retirar tratamento de botão e usar `aria-hidden="true"`. Se abrir detalhes, convertê-lo em botão real com label `Ver detalhes da chamada read_text` e estados completos.

#### P3.2 - A lista observável usa uma hairline em cada linha

- **Região visível:** três linhas internas do disclosure `Atividade observável`.
- **Evidência:** o grupo continua legível, mas cada item recebe separador horizontal, reforçando um visual de tabela que o restante da tela evita.
- **Correção concreta:** manter uma borda no container e uma divisão após o cabeçalho; agrupar as linhas com `gap: 8px` e mudança tonal ou padding de 12-16 px. Preservar a ordem e os ícones, sem converter os itens em cards.

#### P3.3 - O composer está mais alto do que a tarefa mostrada exige

- **Região visível:** bloco inferior de aproximadamente 130 px de altura, para placeholder de uma linha e uma barra de contexto.
- **Evidência:** a largura é adequada, mas a altura compete com a atividade e reforça aparência de caixa decorativa.
- **Correção concreta:** usar altura inicial de 104-112 px, textarea autoexpansível de 2 a 5 linhas e barra inferior de 40-44 px. Preservar largura, contexto de Project e foco visível. Não fixar altura máxima sem overflow interno acessível.

## Preserve

- A leitura em dois segundos no canvas esquerdo: Study, disclosure local, workflow, evento selecionado e composer.
- A command rail horizontal com `Lab` ativo e o switcher de `Release Integrity`, sem sidebar ChatGPT-like.
- A Study `Diagnóstico de regressões após deploy` como heading dominante, com Project abaixo e IDs visualmente secundários.
- O workflow horizontal como assinatura visual no desktop, incluindo check e preenchimento sem verde, laranja oxidado para o corrente e outline para o futuro.
- A separação de `Job`, `Tentativa` e `Run`, com o Run ID em mono e baixa ênfase.
- A distinção Usuário/Agente por labels e ritmo vertical, sem bolhas de chat em toda parte.
- `Atividade observável` como disclosure integrado, restrito a fatos observáveis.
- A posição do spinner imediatamente acima do composer.
- O composer largo, com seletor de Project integrado e CTA de envio compacto.
- A paleta única de carbono, grafite, off-white, prata e laranja oxidado. Não há verde decorativo, glow azul ou roxo, rainbow status, robô, cérebro, sparkle, balança ou database verde.
- A profundidade por campos tonais, os shadows discretos e a quantidade contida de superfícies.
- A ausência de KPIs, gráficos genéricos, tabela de eventos grande e cards de métricas.

## Correct in code

### Limites e estado

- Tornar explícitos `Chat do operador · Fora do SubjectEnvelope` e `Draft do Lab Agent`.
- Separar `currentStage`, `selectedStage` e `selectedEvent`; não derivar um do outro pela posição visual.
- Rotular o workflow como traço da demonstração, sem tratá-lo como lifecycle completo ou como prova de admissão.
- Unificar spinner, resposta e composer em uma máquina de estados que cubra idle, running, ready, failed e terminal.
- Definir de forma inequívoca enabled, disabled, hover, active e focus para `Alternar estado`, `Abrir evidência` e envio.
- Manter `Demonstração local` visível em todos os estados do stub e não promover conteúdo ilustrativo a fato de Run.

### Component boundaries recomendados

- `OperatorShell`: grid do rail, canvas e dock; controla breakpoints, overflow e landmarks.
- `CommandRail`: marca, destinos, Project switcher e status do stub.
- `StudyHeader`: Study, Project, disclosure, cenário e variante.
- `RunTrace`: `<ol>` dos estágios, estado corrente e seleção independente.
- `EventInspector`: tipo de evento, resumo autorizado, Job, Tentativa, Run e ações condicionadas a capability.
- `ConversationPreview`: labels Usuário/Agente e status de draft, sem possuir o Chat lateral.
- `ObservableActivity`: disclosure e lista append-only de `ActivityItem` públicos.
- `ExecutionStatus`: spinner, label e anúncio live; não contém o composer.
- `Composer`: draft local, seletor de Project, helper e envio governados pelo estado de execução.
- `AdaptiveChatDock`: thread do operador e controles de snap; não conhece nem compila `SubjectEnvelope`.
- `SnapPreview`: overlay transitório dentro do viewport, sem alterar layout ou scroll width.

### Layout responsivo

- **Desktop, 1280 px ou mais:** rail em uma linha; canvas flexível; dock de 272-320 px; padding principal de 32-48 px; workflow horizontal; composer no fluxo inferior, não absoluto.
- **Tablet, 768-1279 px:** compactar o dock antes de comprimir o workflow. Exibir uma rail lateral de 56-64 px ou botão `Abrir Chat`; quando aberto, usar aside de 320-360 px com backdrop e foco gerenciado. Reduzir o rail superior sem quebrar a navegação em duas linhas. Manter o inspector em uma coluna e ações abaixo da metadata.
- **Mobile, abaixo de 768 px:** uma coluna; destinos principais em menu; workflow como stepper vertical com labels completos; inspector logo após o estágio selecionado; `Atividade observável` recolhida por padrão; composer sticky no rodapé com `env(safe-area-inset-bottom)`; Chat como sheet ou dialog de largura total, acionado por botão explícito. Não transportar grip, long press ou ghost de desktop para touch pequeno.

### Tokens recomendados

- Escala espacial baseada em 4 px: `4, 8, 12, 16, 24, 32, 48`.
- Heading da Study: aproximadamente `36/42`, peso 600-650; body `16/24`; secundário `14/20`; mono `13/18` apenas para IDs e eventos.
- Radius: superfícies 10-12 px; controles 8-10 px; círculo apenas para grip ou icon button circular.
- Cores iniciais coerentes com a imagem: carbono `#101416`, grafite `#1A1D1E`, off-white `#ECE7DE`, prata `#A8A49C` e laranja oxidado `#D9652C`. Ajustar por medição de contraste, não por cópia dos pixels rasterizados.
- Focus ring: 2 px em laranja, offset de 2 px e contraste não textual mínimo de 3:1.

### Spinner e estados observáveis

- `ExecutionSpinner` tem três marcas, transform e opacity apenas, fases deslocadas e fallback estático para reduced motion.
- `ActivityItem(status)` comunica apenas estado público curto, como `Preparando contexto`.
- `ActivityItem(tool-call)` usa `TerminalWindow` ou `FileText`, nome da tool, argumentos permitidos resumidos e ref `event:` quando houver.
- `ActivityItem(tool-result)` usa `FileCheck`, resultado capturado, tamanho ou tipo quando permitido e ref canônica. Não renderiza conteúdo sensível por padrão.
- Não criar uma seção `Thinking`; não exibir chain-of-thought, grader, hidden state ou texto livre de raciocínio.

### Estados e ícones do Chat

- Estado persistido: `closed | compact | expanded | full-height`.
- Estado transitório: `previewTarget: null | expanded | full-height`.
- Long press revela o preview, mas clique abre um menu com os mesmos destinos; teclado usa Enter ou Space e setas para escolher.
- Usar uma família Phosphor: `FolderSimple`, `Notebook` ou `FileMagnifyingGlass`, `PlayCircle` ou `Pulse`, `FingerprintSimple`, `TerminalWindow`, `FileCheck`, `SidebarSimple`, `ArrowsOutSimple`, `X`, `DotsSixVertical` e `PaperPlaneTilt`.
- Não desenhar SVGs manualmente. Ícones sem texto visível recebem nome acessível; ícones decorativos ficam fora da árvore de acessibilidade.

## Implement beyond the image

### Estados e comportamento que a imagem não especifica

- Ordem de tabulação, atalhos, operação dos estágios, disclosure, Project switcher, composer e Chat por teclado.
- Aparência e persistência do foco, foco inicial, retorno de foco ao fechar Chat e eventual focus trap em dialog.
- Hover, active, pressed, selected, enabled e disabled de todas as ações.
- Transições entre Lab, Projects, Study e Runs, assim como loading e erro de rota.
- Progressão entre Contexto, Subject, Leitura da tool, Avaliação e Evidência, incluindo falha e terminal.
- Semântica do timeout: `run.budget_exhausted` deve permanecer terminal e não virar completed.
- Reduced motion para spinner, mudança de estágio, expansão do dock e previews de snap.
- Threshold, cancelamento, pointer capture, perda de pointer e escolha do destino no long press.
- Colapso real em tablet/mobile, zoom a 200%, reflow, safe areas e comportamento com teclado virtual.
- Anúncios para screen reader, labels dos ícones, leitura do stepper e atualização de status via `aria-live`.
- Contraste calculado no CSS final. A inspeção raster não certifica WCAG.

### Contratos e capabilities a implementar explicitamente

- Chat do operador fora do `SubjectEnvelope`; o Subject recebe somente o envelope compilado e admitido.
- Draft do Lab Agent sem autoridade humana; aceitação e efeitos externos continuam pertencendo ao humano com attestation verificável.
- Run criada somente após `AdmissionRecord.decision=admitted` para o RunSpec exato. O traço visual não substitui AdmissionRecord.
- `tool.call`, `tool.result`, selected event e terminal ligados aos records e fases válidas; fatos mostrados devem carregar refs `run:`, `event:` ou `artifact:` quando aplicável.
- `Abrir evidência` condicionado a resolver e autorizar o conteúdo. `ArtifactRef` identifica conteúdo, mas não concede acesso.
- O estado `Demonstração local` não anuncia execução de capability incompatível ou indisponível.
- Estados de loading, failure e terminal com copy própria; não inventar completion, achievement ou pass/fail.

### Limites visuais específicos

- Não há copy principal cortada ou distorcida no canvas esquerdo.
- O único corte evidente é o ghost tracejado de snap no limite direito.
- Kerning, antialiasing, pequenos desalinhamentos e desenho exato dos glifos vêm do raster e não devem ser reproduzidos literalmente.
- A imagem não demonstra scroll, resize, drag, long press, foco, navegação, persistência, erro, terminal ou acesso a evidence.
- A grande área vazia no Chat pode continuar calma; não deve ser preenchida com mensagens, métricas ou cards fictícios para justificar o espaço.

builder disposition: proceed with corrections
