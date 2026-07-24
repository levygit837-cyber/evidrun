# Civic Console: notas de geração

## Artefato

- Imagem final: `reference/source.png`.
- Dimensão final verificada: `1440 x 1024` pixels, PNG RGB.
- Foi feita exatamente uma geração com ImageGen.
- A saída nativa tinha `1487 x 1058` pixels. Ela foi redimensionada para a dimensão obrigatória, sem recorte e sem nova geração. A proporção nativa era praticamente igual à proporção alvo.
- A imagem foi inspecionada em resolução original com `view_image`.
- Nenhum arquivo React, CSS ou de comportamento foi alterado.
- Esta imagem é referência de direção visual. Não deve ser copiada literalmente nem tratada como especificação funcional.

## Direção adotada

A direção combina uma sala contemporânea de registros públicos com disciplina suíça de produto. A tela usa porcelana fria como superfície dominante, carvão profundo como âncora e um único vermelhão contido para bloqueio, seleção e foco. Fumaça e prata separam regiões sem criar uma coleção de cards.

O layout foi orientado pelos seguintes valores:

- variância visual 4;
- movimento implícito 2;
- densidade 5;
- tipografia sans racional, com mono reservado a IDs e eventos;
- raio consistente próximo de 9 px;
- ícones outline de uma única família;
- workflow espacial como assinatura, com o estado de Admissão em primeiro plano;
- Chat adaptativo subordinado ao Project workflow.

O filtro anti-slop foi aplicado para evitar gradiente roxo, brilho azul, gráficos inventados, KPIs falsos, glassmorphism, robôs, sparkles, excesso de pills, conectores e decoração que tente explicar estado por cor.

## Elementos que vale preservar

1. O rail escuro de 72 px com Lab ativo e Projects, Study e Runs em uma coluna curta.
2. O command strip compacto com Project, Study, scenario, estado local e data.
3. A leitura imediata de `Retrieval Quality` e do Study `Respostas com fontes insuficientes`.
4. A sequência espacial Intent, Revision, Admission, Run e Evidence, com Admission maior e selecionada.
5. O bloqueio de `Admission preflight` com X, motivo direto, frase humana e ação de criar revisão.
6. A distinção entre ação primária e `Enfileirar` desabilitado.
7. O rótulo de `RunSpec` como `Prévia compilada`, sem sugerir que uma Run já existe.
8. Workspace como conceito de integração pendente, sem prometer montagem, acesso ou leitura de conteúdo.
9. A conversa curta, o rótulo de draft e o disclosure `Atividade observável`.
10. Tool Call e Tool Result como eventos discretos e visualmente distintos, com file-search e document-check.
11. O spinner próprio de carimbos de registro que se resolve em uma linha, posicionado imediatamente acima do composer.
12. O composer horizontal com Project integrado, foco vermelhão, controles de fonte e envio desabilitado.
13. A declaração explícita de que o Lab Agent cria drafts e Chat não integra o SubjectEnvelope.
14. O Chat lateral com grip neutro e affordances de expandir, ajustar altura, recolher e fechar.

## Falhas visíveis observadas

Estas falhas não justificam uma segunda geração, mas devem orientar a implementação:

1. O `RunSpec` aparece dentro da região Run. Mesmo com `Prévia compilada`, a posição pode sugerir que uma Run já existe. O implementador deve mantê-lo em Revision ou Admission e deixar Run claramente ainda não criada.
2. Workspace aparece dentro da região Evidence. Isso reduz a separação conceitual pedida no brief. Ele deve virar uma integração lateral ou uma faixa própria fora das cinco etapas.
3. As etapas ainda se parecem demais com cards dentro de cards. O resultado aproxima a composição de um admin dashboard. Na implementação, as etapas devem ser regiões abertas, definidas primeiro por espaço, alinhamento e tintas sutis.
4. `Criar nova revisão` e `Enfileirar` ocupam quase toda a largura do bloco. O brief pede botões content-sized. A implementação deve reduzir as ações ao conteúdo e manter o disabled como controle secundário.
5. O preview pontilhado do Chat não comunica claramente um estado simultaneamente mais largo e mais alto. Parte dele fica escondida pelo dock, e o dock atual já é alto e contém muito vazio.
6. `Sistema pronto` é forte demais para um stub local que contém uma falha de admissão. Prefira um disclosure como `Prontidão do sistema` com detalhe `Stub determinístico local`, sem anunciar capacidades não executáveis.
7. Há mistura de registro linguístico: `Study:`, `DRAFT` e `Abrir thread completa` convivem com pt-BR. A implementação deve escolher termos deliberadamente e revisar toda a copy. `Estudo`, `Rascunho` e `Abrir conversa completa` são alternativas mais consistentes.
8. Os nomes das etapas `Revision` e `Admission` saíram traduzidos como `Revisão` e `Admissão`. O implementador deve confirmar se os nomes canônicos de produto ficam em inglês ou se toda a navegação será localizada. Não misturar os dois padrões por acidente.
9. A linha de disclosure sob o composer está pequena em relação ao corpo recomendado de 15-16 px.
10. `Preparing context` usa um pequeno spinner circular. O indicador principal de carimbos está correto, mas o loader circular secundário enfraquece a linguagem própria.
11. O ID `ART-9F3A-2B17` é ilustrativo e não deve entrar em fixture ou implementação sem um ArtifactRef canônico. `ArtifactRef` identifica conteúdo, não concede acesso e não possui locator.
12. A malha de cinco regiões ainda é bastante regular. A ampliação da etapa Admission ajuda, mas a versão implementada deve usar proporções e whitespace para escapar do padrão de cinco cards equivalentes.

## Recomendações para o implementador

- Use a imagem como referência de hierarquia, ritmo, cor e estados. Reconstrua a UI com componentes reais e contratos existentes.
- Considere uma shell desktop com colunas aproximadas `72px minmax(0, 1fr) clamp(248px, 20vw, 288px)`. O Chat pode recolher para um dock estreito em larguras menores.
- Modele o workflow como grid de regiões abertas, com proporções aproximadas `0.8fr 0.9fr 1.5fr 1fr 0.9fr`. Admission recebe espaço extra por ser o foco atual.
- Use uma única superfície selecionada dentro de Admission. Não coloque um card externo em cada etapa e outro card dentro dele.
- Posicione a prévia compilada de RunSpec antes da região Run. A região Run deve comunicar ausência de Run sem inventar um novo status factual.
- Posicione Workspace fora da sequência Intent a Evidence. Mantenha `Integration pending` como estado de integração, não como evidência nem como permissão de acesso.
- Preserve a falha fechada: sem coverage obrigatória, `Enfileirar` continua desabilitado. Não apresente aprovação humana, authority ou decisão humana implícita.
- Não reintroduza locator em ArtifactRef nem prometa blob, grant, replay, restore ou portabilidade.
- Use uma família como Phosphor Outline em peso consistente. Não misture bibliotecas nem desenhe SVGs simbólicos novos.
- Implemente o spinner como quatro marcas retangulares curtas que diminuem progressivamente até uma linha. Em `prefers-reduced-motion`, mostre a linha final estática e mantenha o texto de estado.
- Faça o grip revelar previews de snap apenas durante hold. O preview pode usar uma superfície prata de baixa opacidade e borda simples, sem blur de fundo.
- Em largura abaixo de aproximadamente 1200 px, recolha Chat primeiro. Em largura menor, permita que o workflow vire uma sequência vertical ou uma faixa horizontal controlada, sem reduzir corpo e explicações a texto minúsculo.
- Garanta corpo de 15-16 px, contraste WCAG AA, foco visível, ícone mais rótulo para estados, e alvo de toque adequado.
- Mantenha a copy curta, funcional e sem resultados inventados. Revise separadamente termos canônicos, termos localizados e eventos técnicos.
- Preserve `Demonstração local` como limite explícito. Não descreva o stub, o runtime bounded, integração, persistência ou futuras capacidades como comportamento implementado.

