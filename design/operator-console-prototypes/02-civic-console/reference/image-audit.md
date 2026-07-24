# Auditoria independente da imagem: Civic Console

## Escopo, leitura e veredito

- Artefato auditado: `reference/source.png`, PNG RGB de 1440 x 1024.
- Evidência usada: somente o frame estático em resolução original, `IMAGE_BRIEF.md` e `reference/generation-notes.md`.
- Superfície: Lab Home do EvidRun Operator Console, com Project e Study ativos, workflow em revisão de Admission, atividade do Lab Agent, composer e Chat adaptativo.
- Objetivo do operador: entender o contexto ativo, localizar a falha de admissão, corrigir a revisão e só então enfileirar uma Run.
- Leitura de design: console operacional regulado para um operador técnico, com linguagem cívica contemporânea, disciplina suíça, baixa variância, movimento contido e densidade moderada.
- Dials observados: `DESIGN_VARIANCE: 4`, `MOTION_INTENSITY: 2`, `VISUAL_DENSITY: 5`.
- A orientação anti-slop foi aplicada apenas onde cabe a uma UI densa. Para esta superfície, padrões de dashboard devem seguir um sistema de produto consistente, com regiões funcionais e controles acessíveis, não regras de landing page.

O frame é uma base viável, mas não deve ser copiado pixel a pixel. A implementação deve preservar a hierarquia, o contraste sóbrio e a falha fechada, corrigindo os erros conceituais, a grade excessivamente cardificada, a anatomia do Chat e a copy inconsistente.

Não há P0 que impeça implementação significativa. O builder pode prosseguir, desde que trate os P1 como correções obrigatórias antes da validação visual e funcional.

## Findings

### P0

Nenhum finding P0. A imagem comunica Project, Study, etapa atual, falha de Admission, ação corretiva, composer e Chat com clareza suficiente para orientar uma primeira implementação.

### P1

#### P1-1 - A posição do RunSpec sugere que uma Run já existe

- Região visível: workflow central, coluna `4 Run`.
- Evidência: a Admission está bloqueada por `required source coverage missing`, mas a coluna seguinte contém `Prévia compilada` e `RunSpec` dentro da região Run.
- Tipo: verdade de domínio e hierarquia.
- Risco: o operador pode interpretar o preview como uma Run criada. Isso viola a leitura fail-closed: sem uma Admission admitida para o RunSpec exato, nenhuma Run nova existe.
- Correção concreta: mover `CompiledRunSpecPreview` para o fim de Revision ou para uma área de preview dentro de Admission. A região Run deve exibir um estado explícito e não factual, como `Nenhuma Run criada` e `Aguardando admissão`, sem ID, evento queued ou aparência de entidade persistida. `Enfileirar` permanece desabilitado e deve expor a causa pelo texto auxiliar e por `aria-describedby`.

#### P1-2 - Workspace e ArtifactRef estão incorporados à etapa Evidence

- Região visível: workflow central, coluna `5 Evidência`.
- Evidência: o mesmo bloco contém `Workspace`, `Integration pending` e `ArtifactRef ART-9F3A-2B17`.
- Tipo: verdade de domínio e arquitetura de informação.
- Risco: a composição transforma integração, evidência e acesso em uma única entidade. Também pode sugerir que um ArtifactRef concede leitura, montagem ou localização de conteúdo.
- Correção concreta: retirar Workspace das cinco etapas. Colocar `WorkspaceIntegrationDisclosure` no command strip ou em uma faixa lateral curta, com estado `Integração pendente`. Mostrar um ArtifactRef apenas quando vier de fixture canônica e estiver ancorado ao record correto. Não renderizar path, URL, locator, grant ou promessa de acesso. Na etapa Evidence, enquanto a Admission falha, usar um estado vazio como `Nenhuma evidência desta Run`, pois a Run ainda não existe.

#### P1-3 - `Sistema pronto` anuncia mais capacidade do que o frame comprova

- Região visível: canto superior direito do command strip.
- Evidência: o disclosure afirma `Sistema pronto`, enquanto a tela também declara `Demonstração local`, `Integration pending` e uma falha de Admission.
- Tipo: verdade de domínio e confiança.
- Risco: `pronto` pode ser lido como disponibilidade executável de provider, integração, enqueue e persistência, embora o frame seja um stub determinístico local.
- Correção concreta: usar `Prontidão do sistema` como rótulo neutro e abrir um disclosure com capacidades verificadas individualmente. No estado do protótipo, mostrar `Stub determinístico local`. Nunca derivar prontidão de uma cor ou de uma capability apenas representável.

#### P1-4 - O workflow ainda parece uma grade de cards de admin

- Região visível: faixa horizontal `Intent`, `Revisão`, `Admissão`, `Run` e `Evidência`.
- Evidência: cada etapa tem borda externa, card interno, número em badge e separadores; Admission adiciona mais um card dentro do card. Intent e Revision ficam estreitos, enquanto a sequência inteira é lida como cinco widgets.
- Tipo: hierarquia, legibilidade e taste.
- Risco: o workflow perde sua função de assinatura espacial e se aproxima do dashboard genérico que o brief exclui. Os painéis estreitos comprimem texto e tornam a etapa mais importante dependente de bordas.
- Correção concreta: implementar `WorkflowRegion` como regiões abertas em CSS Grid, usando espaço, alinhamento e tinta prata muito leve antes de bordas. Uma proporção desktop próxima de `0.8fr 0.9fr 1.45fr 0.85fr 0.85fr` preserva foco em Admission. Manter uma única superfície selecionada dentro de Admission. Usar apenas divisores locais entre estágios, sem card externo e interno em todas as colunas.

#### P1-5 - O Chat parece uma terceira coluna permanente e o snap preview não explica o destino

- Região visível: lado direito, painel alto `Chat`, grip circular e retângulo pontilhado atrás.
- Evidência: o painel ocupa quase toda a altura, contém muito vazio e reduz o canvas. O preview pontilhado fica parcialmente oculto pelo próprio painel e não deixa claro se a mudança será de largura, altura ou ambos.
- Tipo: interação e hierarquia.
- Risco: o Chat deixa de ser subordinado ao Project workflow, parece um inspector persistente e torna o gesto de hold/snap imprevisível.
- Correção concreta: iniciar em um dock compacto de 56-64 px ou em um `peek` curto com contagem e última mensagem. Expandir para thread de 272-304 px apenas por ação explícita. Mostrar previews somente enquanto o grip estiver pressionado, com duas geometrias claramente separadas e rótulos acessíveis. O painel expandido deve sobrepor a margem direita ou reservar espaço de modo deliberado, nunca criar uma terceira coluna simultânea com um futuro inspector.

### P2

#### P2-1 - As ações de Admission viram barras de largura quase total

- Região visível: card `Admission preflight`.
- Evidência: `Criar nova revisão` e `Enfileirar` ocupam quase toda a largura da superfície.
- Tipo: hierarquia de ação.
- Risco: o padrão aumenta peso visual, faz o disabled parecer uma segunda ação principal e contraria o requisito de botões content-sized.
- Correção concreta: usar uma linha de ações com `inline-flex`, `w-fit`, `gap-2` e labels em uma linha. `Criar nova revisão` é primário. `Enfileirar` fica como botão secundário desabilitado com ícone opcional de play e explicação adjacente, não como uma segunda barra.

#### P2-2 - A copy mistura pt-BR, inglês de produto e inglês operacional sem regra visível

- Regiões visíveis: subtítulo `Study:`, chip `DRAFT`, issue `required source coverage missing`, eventos `Preparing context`, `Tool call`, `Tool result captured` e ação `Abrir thread completa`.
- Evidência: termos canônicos como `RunSpec`, `ArtifactRef`, `SubjectEnvelope` e `source-grounding-check` convivem com rótulos de interface parcialmente traduzidos.
- Tipo: copy e consistência.
- Risco: a mistura dificulta distinguir nome canônico, evento técnico e texto para o operador.
- Correção concreta: definir uma tabela de terminologia antes de montar fixtures. Localizar UI para `Estudo`, `Rascunho`, `Preparando contexto`, `Chamada de ferramenta`, `Resultado capturado` e `Abrir conversa completa`. Preservar em inglês apenas identificadores e nomes canônicos deliberados, com estilo mono e hierarquia secundária. Confirmar uma única política para `Revision`/`Revisão` e `Admission`/`Admissão`.

#### P2-3 - Texto auxiliar e atividade observável estão abaixo da escala de leitura principal

- Regiões visíveis: disclosure sob o composer, linhas de `Atividade observável`, timestamps, `DRAFT`, `Integration pending` e ação no rodapé do Chat.
- Evidência: vários textos parecem próximos de 11-13 px, enquanto o brief pede corpo de 15-16 px e evita explicações minúsculas.
- Tipo: legibilidade e risco de contraste.
- Risco: informação de autoridade e disclosure pode ser ignorada. O contraste do disabled e de metadados parece plausível, mas não pode ser confirmado numericamente no raster.
- Correção concreta: usar corpo `15px/22px` ou `16px/24px`; compactos `13px/18px` apenas para metadados; mono `12-13px/18px` apenas para IDs e eventos. Manter a linha de autoridade em pelo menos `13px/18px`, com contraste AA no código. Validar tokens e estados com ferramenta de contraste, sem inferir conformidade pelo PNG.

#### P2-4 - O indicador de progresso próprio compete com um spinner circular genérico

- Regiões visíveis: sequência vermilion `Verificando referências autorizadas` acima do composer e primeira linha de `Atividade observável`.
- Evidência: o indicador principal usa marcas de registro, mas `Preparing context` usa um círculo segmentado. As marcas geradas têm ruído e contornos que parecem artefatos de raster.
- Tipo: sistema visual e comunicação de estado.
- Risco: duas linguagens de loading enfraquecem a assinatura do produto. Copiar literalmente o ruído da imagem produziria um componente frágil.
- Correção concreta: construir um único `RegistrationProgress` com quatro estados geométricos limpos, sem borda circular. Usar marcas retangulares curtas que se simplificam até uma linha final. Na atividade, reutilizar uma miniatura dessa mesma gramática ou um ícone de evento estático. Em `prefers-reduced-motion`, exibir a linha final sem animação e manter o texto de status em `aria-live="polite"`.

#### P2-5 - `Atividade observável` precisa deixar explícito que não é chain-of-thought

- Região visível: disclosure abaixo da resposta do Lab Agent.
- Evidência: o bloco contém progresso, Tool Call e Tool Result, mas o primeiro item genérico `Preparing context` pode ser lido como uma janela de pensamento.
- Tipo: disclosure e segurança conceitual.
- Risco: uma implementação ingênua pode adicionar reasoning privado, token stream ou hidden grader ao bloco.
- Correção concreta: modelar a UI como uma lista append-only de eventos públicos e permitidos, não como `Thinking`. Cada linha deve ter tipo, resumo factual, estado, timestamp e referência canônica quando existir. Não mostrar pensamentos, chats ocultos, grader oculto ou evidência fora do envelope autorizado. O título visível continua `Atividade observável`.

#### P2-6 - Controles do Chat são distinguíveis pelo desenho, mas não autoexplicativos

- Região visível: canto superior direito do Chat e grip na borda esquerda.
- Evidência: há ícones para expandir, altura, recolher e fechar, mas sem labels visíveis. O grip é um círculo neutro sem pista de hold. O badge à esquerda de `Abrir thread completa` não tem objeto ou ação imediatamente reconhecível.
- Tipo: iconografia e affordance.
- Risco: expandir, alterar altura e recolher podem ser confundidos; o hold não é descoberto pelo frame.
- Correção concreta: usar uma única família outline, como Phosphor, com peso global consistente. Sugestão: `ArrowsOut` para expandir, `ArrowsOutLineVertical` para altura, `CaretRight` ou `SidebarSimple` para recolher e `X` para fechar. Inserir `DotsSixVertical` dentro do grip circular e oferecer tooltip, `aria-label` e instrução curta na primeira interação. Remover o badge decorativo do rodapé; `ArrowSquareOut` após o label já comunica abrir a conversa.

#### P2-7 - O rail é mais largo e mais persistente do que a direção pede

- Região visível: navegação escura à esquerda.
- Evidência: o rail parece próximo de 96 px, e todos os labels permanecem visíveis, não apenas o ativo ou o hover.
- Tipo: espaço e responsividade.
- Risco: em 1440 px o custo é tolerável, mas em tablet agrava a compressão do workflow.
- Correção concreta: usar `w-[72px]` ou no máximo 80 px no desktop, com Lab ativo rotulado e tooltips para os demais itens. Em tablet, preservar ícones e recolher labels. Em mobile, converter a navegação primária em barra inferior ou menu compacto, sem miniaturizar o rail.

### P3

#### P3-1 - O command strip tem separadores demais para seis itens

- Região visível: faixa superior com Project, Study, scenario, demonstração, data e prontidão.
- Evidência: cada item recebe ícone e divisor vertical, criando uma sequência longa e uniforme.
- Tipo: polish e densidade.
- Correção concreta: agrupar Project e Study como contexto primário; manter cenário e demonstração como metadados; mover data ou detalhes secundários para o disclosure de contexto quando o espaço cair. Em Tailwind, preferir `gap-4` e dois divisores de grupo a `divide-x` em todos os itens.

#### P3-2 - Um divisor de largura total separa workflow e conversa

- Região visível: linha horizontal abaixo das cinco etapas.
- Evidência: a linha percorre o canvas inteiro apesar de o espaçamento já separar os blocos.
- Tipo: polish.
- Correção concreta: remover a linha ou limitá-la à largura do feed. Usar `mt-6 pt-6` e um divisor local somente se a hierarquia continuar ambígua.

#### P3-3 - O símbolo de laboratório se repete em três papéis

- Regiões visíveis: marca superior do rail, item `Lab` e avatar `Lab Agent`.
- Evidência: o mesmo motivo de frasco representa produto, destino de navegação e ator.
- Tipo: semântica de ícone.
- Correção concreta: preservar o frasco para `Lab`. Tratar a marca do produto como wordmark/mark separado e usar avatar tipográfico `LA` ou `IdentificationBadge` para o Lab Agent. Não substituir por robot, brain, sparkle ou estrela.

## O que o frame resolve bem

- O Project `Retrieval Quality` é imediatamente identificável no seletor superior e no título principal.
- O Study `Respostas com fontes insuficientes` está legível e próximo do Project.
- A etapa atual é clara por número, largura, contorno, conteúdo selecionado e falha com X. Ela não depende apenas do vermilion, embora a implementação deva adicionar `aria-current="step"` e um rótulo textual de estado.
- A próxima ação `Criar nova revisão` é óbvia.
- `Enfileirar` aparece secundário e desabilitado.
- IDs, timestamps e event names são visualmente secundários.
- User e Lab Agent são distinguíveis por estrutura, avatar, label e resposta.
- Tool Call e Tool Result têm anatomias e ícones diferentes, sem dominar a conversa.
- O spinner próprio está imediatamente acima do composer.
- O composer é largo, integrado ao Project e tem envio vazio claramente desabilitado.
- A disclosure de autoridade informa que o Lab Agent cria drafts e que Chat não integra o SubjectEnvelope.
- A paleta usa porcelana fria, carvão, prata e vermilion sem beige craft, roxo, cobalt glow ou verde decorativo.
- Vermilion está concentrado em falha, foco e ação corretiva.
- Shadows estão restritas ao Chat.
- Não há KPIs, gráfico inventado, balance scale, database verde, robot ou sparkle visível.
- Não há connector spaghetti. A ordem das etapas é entendida pela sequência espacial.
- Nenhum texto principal parece cortado no frame desktop. A distorção visível está concentrada nas marcas rasterizadas do spinner e na sobreposição do snap preview.

## Preserve

1. Shell clara com rail escuro, canvas de porcelana fria e Chat subordinado.
2. Project e Study no topo, com cenário e `Demonstração local` como limites explícitos.
3. Workflow de cinco estágios como assinatura principal, com Admission em foco.
4. Falha fechada de Admission com X, motivo curto, explicação humana e ação corretiva.
5. `Enfileirar` indisponível até Admission válida para o RunSpec exato.
6. RunSpec identificado como preview compilado, mas em posição corrigida.
7. Resposta curta do Lab Agent marcada como rascunho.
8. `Atividade observável` como disclosure de eventos públicos, sem reasoning privado.
9. File-search para Tool Call de leitura e document-check para Tool Result capturado.
10. Indicador de registro próprio imediatamente acima do composer.
11. Composer horizontal com Project integrado, anexar/ler fonte e envio desabilitado quando vazio.
12. Linha explícita de autoridade: Lab Agent só cria drafts; Chat não faz parte do SubjectEnvelope.
13. Chat com grip neutro, contagem de mensagens e controles de geometria.
14. Paleta de um único accent, mono limitado, radius moderado e shadow fria somente no elemento flutuante.

## Correct in code

1. Mover RunSpec para Revision ou Admission e representar Run como ainda não criada.
2. Separar Workspace de Evidence e retirar qualquer ArtifactRef ilustrativo sem record canônico.
3. Trocar `Sistema pronto` por disclosure de prontidão baseado em capability verificada.
4. Reconstruir as etapas como regiões abertas, não cards aninhados.
5. Reduzir o estado inicial do Chat e tornar o snap preview inequívoco.
6. Converter as ações de Admission em botões content-sized.
7. Aplicar uma política explícita de localização e terminologia canônica.
8. Elevar escala e contraste de disclosure, atividade, metadados e ações secundárias.
9. Unificar a gramática de progress com o indicador de registros, sem círculo genérico.
10. Dar labels, tooltips, foco visível e nomes acessíveis aos controles do Chat.
11. Reduzir o rail para 72-80 px e planejar seu colapso.
12. Simplificar divisores no command strip, workflow e atividade.
13. Não copiar ruído, desalinhamento, contorno irregular ou sobreposição acidental do PNG.

## Implement beyond the image

### Component boundaries

- `OperatorShell`: rail, command strip, canvas e camada do Chat.
- `PrimaryNavRail`: Lab, Projects, Study e Runs com route state real.
- `ProjectContextStrip`: Project, Study, scenario, demonstração e prontidão.
- `WorkflowBoard`: ordenação e layout dos cinco `WorkflowRegion`.
- `WorkflowRegion`: heading, estado semântico, resumo e slot de conteúdo.
- `AdmissionIssue`: failure code, explicação, record alvo e ações.
- `CompiledRunSpecPreview`: preview somente leitura antes de Run.
- `RunEmptyState`: ausência explícita de Run enquanto não admitida.
- `WorkspaceIntegrationDisclosure`: conceito separado do workflow.
- `ConversationFeed`, `UserMessage` e `AgentDraftMessage`.
- `ObservableActivityDisclosure` e `ObservableEventRow`.
- `RegistrationProgress`: sequência visual, texto ao vivo e fallback reduced-motion.
- `EvidenceComposer`: selector de contexto, fonte/anexo, input e envio.
- `AdaptiveChatDock`, `ChatGrip` e `ChatSnapPreview`.
- Inspector futuro como popover, drawer temporário ou bottom sheet, nunca terceira coluna persistente ao lado do Chat.

### Desktop, tablet e mobile

- Desktop, `>= 1280px`: rail de 72-80 px; canvas com `minmax(0, 1fr)`; workflow em cinco regiões; Chat em dock compacto e thread expandida de 272-304 px. Admission recebe cerca de 1.4-1.5 vezes a largura de uma etapa comum.
- Tablet, `768-1279px`: recolher Chat antes de comprimir texto; ocultar labels inativos do rail; manter Admission expandida e converter as demais etapas em faixa horizontal com snap controlado ou sequência vertical. Não reduzir corpo abaixo de 15 px.
- Mobile, `< 768px`: usar workflow vertical ordenado, com Admission aberta e demais etapas em resumo; transformar Chat em sheet de tela inteira; tornar composer sticky acima de `env(safe-area-inset-bottom)`; converter o rail em navegação inferior ou menu compacto. O command strip vira duas linhas ou um disclosure, não uma faixa ilegível.
- Em todos os tamanhos: garantir reflow a 200% de zoom, alvos mínimos de 44 x 44 px e ausência de scroll horizontal na página.

### Spinner customizado

- Anatomia: label de estado, trilho de quatro marcas e uma linha final.
- Frames: `impressão irregular`, `registro alinhado`, `contorno limpo`, `linha resolvida`. O código deve usar geometria limpa; o ruído do PNG não é especificação.
- Movimento: apenas `transform` e `opacity`, com sequência curta e motivada por progresso. Evitar loop permanente quando houver progresso determinável.
- Acessibilidade: `role="status"`, `aria-live="polite"`, texto visível e fallback estático em `prefers-reduced-motion`.
- Falha: substituir vermilion animado por X e mensagem direta. Sucesso não usa verde; usa linha resolvida, label e geometria.

### Atividade observável, Thinking e tools

- Não criar uma superfície visível chamada `Thinking` que revele chain-of-thought.
- Se houver um nome interno `ThinkingBlock`, sua saída pública deve ser apenas um resumo factual permitido e preferencialmente o componente deve se chamar `ObservableActivity`.
- Header: `Atividade observável`, disclosure, contagem opcional e `aria-expanded`.
- Progress row: ícone da gramática de registro, verbo curto, estado e timestamp secundário.
- Tool Call: file-search, label localizado, nome técnico `read_text` em mono e referência do evento quando existente.
- Tool Result: document-check, estado `capturado`, tamanho ou tipo quando permitido e ArtifactRef canônico quando existir.
- Erro de tool: file-warning ou warning-circle, mensagem operacional e retry explícito. Não reutilizar o X de Admission para todo erro.
- Linhas organizadas por `gap-2` e um divisor local, sem uma tabela cheia de hairlines.

### Chat snap states

- `closed`: Chat removido por ação explícita.
- `dock`: estado inicial estreito, com label, contagem e indicador de mensagem.
- `peek`: preview curto da última mensagem, sem ocupar a altura toda.
- `thread`: conversa normal, 272-304 px de largura.
- `threadTall`: mesma largura, maior altura.
- `workspace`: mais largo e mais alto, somente após snap explícito.
- `sheet`: adaptação mobile de tela inteira.

O grip só revela `threadTall` e `workspace` durante hold. Teclado deve oferecer os mesmos destinos sem depender de long-press. Close, collapse e resize são ações distintas, com focus ring e anúncio de mudança de estado.

### Icon replacements and discipline

- Usar uma única família outline no produto, com stroke global consistente.
- Preservar folder/bounding-box para Project, notebook/document-search para Study, shield/gate para Admission, play/pulse para Run e archive/file-lock/fingerprint para Evidence.
- Comparison, quando implementada, usa `GitDiff`, `ArrowsLeftRight` ou duas variantes lado a lado. Nunca balance scale.
- Database, quando aparecer, usa charcoal ou silver. Nunca verde decorativo.
- Substituir o badge ambíguo de `Abrir thread completa` por nenhum ícone inicial; manter apenas `ArrowSquareOut`.
- Reservar o frasco para Lab. Usar avatar tipográfico ou `IdentificationBadge` para Lab Agent.
- Não usar robot, brain, sparkle, estrela, emoji, SVG simbólico inventado ou badges decorativos.

### Spacing, radius e type tokens

- Spacing base: `4, 8, 12, 16, 24, 32px`.
- Padding do canvas: `24px` em desktop, `16px` em tablet e mobile.
- Gap entre seções principais: `24-32px`; gap interno: `8-16px`.
- Radius: painéis `10px`, controles `8px`, chips técnicos `6px`. Pills somente quando a forma tiver função.
- Title: `32px/38px`, peso 650-700.
- Stage heading: `16-18px/24px`, peso 600.
- Body: `15-16px/22-24px`.
- Compact metadata: `13px/18px`.
- Mono IDs/events: `12-13px/18px`.
- Um único vermilion sem glow; neutrals frios consistentes; shadow apenas no Chat e em overlays reais.

## Limites de evidência e verificações obrigatórias

O frame estático não comprova:

1. Ordem de tabulação, navegação completa por teclado ou atalhos.
2. Focus rings, focus trap do Chat/sheet e retorno de foco ao fechar.
3. Hover, active, pressed e disabled reais.
4. Que `Enfileirar` não dispara por teclado, API ou estado obsoleto.
5. Route transitions entre Lab, Projects, Study e Runs.
6. Estados de loading, vazio, falha de provider, falha de tool, timeout, budget exhausted, completed e terminal.
7. Atualização append-only de eventos, records, reviews e adjudicações.
8. Reduced motion e ausência de animação no spinner para essa preferência.
9. Hold/long-press, cancelamento, snap preview e resize do Chat.
10. Reflow em tablet, mobile, zoom de 200% e teclado virtual.
11. Leitura por screen reader, nomes acessíveis, live regions e semântica de heading/list/step.
12. Contraste WCAG numérico, target size e visibilidade de disabled.
13. Persistência, acesso, conteúdo ou recomputabilidade de ArtifactRef.
14. Existência real de Run, provider, Workspace, integração ou capability.

Esses itens são lacunas funcionais e de verificação, não defeitos visuais confirmados pelo PNG. Devem ser implementados e testados com estados reais, fixtures determinísticas e inspeção em browser.

builder disposition: proceed with corrections
