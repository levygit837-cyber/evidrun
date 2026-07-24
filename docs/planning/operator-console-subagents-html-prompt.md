---
id: planning-prompt-operator-console-subagents-html
type: implementation-task
title: Prompt de exploração da Operator Console com sub-agents e HTML
status: draft
authority: planning
owner: web
created_at: 2026-07-23
updated_at: 2026-07-23
applies_to: design
sources:
  - docs/planning/tasks/10-mvp-operator-console.md
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
---

# Prompt mestre — exploração visual da Operator Console com sub-agents e HTML

## Papel

Você é o agente principal responsável por coordenar uma exploração de UI/UX para a Operator Console do Evidrun.
Seu trabalho é organizar sub-agents independentes que criem protótipos HTML completos.
Não altere contratos, domínio, API, runtime ou arquitetura normativa.
Não trate o protótipo visual como comportamento já implementado.
O objetivo é comparar direções de produto concretas por meio de HTML navegável.

## Fonte de verdade

Leia `docs/index.md` antes de iniciar.
Leia `docs/planning/tasks/10-mvp-operator-console.md` integralmente.
Consulte as fontes normativas citadas pela task quando uma decisão depender delas.
Respeite a distinção entre contrato, arquitetura, roadmap, planning e pesquisa.
Não invente endpoints, records, estados ou capabilities como se estivessem disponíveis.
Quando algo ainda não existir, apresente a capability como indisponível ou `integration_pending`.
Fixtures podem apoiar o protótipo, mas precisam ser identificadas visualmente como demonstração.
Nenhum estado simulado pode parecer uma Run real.

## Resultado esperado

Produza um batch de variantes HTML independentes.
Use exatamente um sub-agent por variante.
Cada sub-agent deve entregar exatamente um arquivo HTML.
Cada HTML deve cobrir os mesmos escopos mínimos para permitir comparação justa.
Cada HTML deve funcionar de forma autocontida no navegador.
Cada HTML deve conter entre 500 e 900 linhas.
O intervalo preferencial é de 600 a 800 linhas.
Use nomes semânticos para regiões, componentes, estados e ações.

## Regra central de coordenação

O agente principal não deve homogeneizar prematuramente as propostas.
Cada sub-agent recebe contexto limpo e independente.
Um sub-agent não deve ler o HTML produzido por outro durante a criação.
Um sub-agent não deve copiar a direção visual de outro.
Todos recebem o mesmo escopo funcional mínimo.
Cada um deve explorar uma hipótese de experiência claramente diferente.

## Quantidade padrão de variantes

Se o usuário não definir a quantidade, crie quatro variantes.
Cada variante deve explorar uma hipótese de experiência claramente diferente, definida no momento do
batch junto com o usuário. Não reutilize um conjunto fixo de variantes anteriores como padrão.
Elas são interpretações completas e concorrentes da mesma console.
Cada interpretação deve incluir todas as páginas mínimas descritas abaixo.

## Estrutura do batch

Antes de delegar, defina o objetivo do batch.
Registre as perguntas de design que o batch pretende responder.
Registre os critérios comuns de comparação.
Registre quais capabilities ainda são ausentes ou incertas.
Depois, escreva um briefing individual para cada sub-agent.
Cada briefing deve ter no mínimo 300 linhas.
O tamanho recomendado de cada briefing é aproximadamente 500 linhas.
O limite absoluto de cada briefing é 700 linhas.
Conte linhas reais antes de enviar o briefing.
Se tiver menos de 300 linhas, detalhe estados, fluxos e critérios.
Se ultrapassar 700 linhas, remova redundância sem perder restrições importantes.

## Conteúdo obrigatório de cada briefing

Identifique a variante e sua hipótese central.
Explique o problema de produto que ela tenta resolver.
Defina a sensação desejada nos primeiros cinco segundos.
Defina a hierarquia de informação.
Defina a navegação principal.
Defina o papel da sidebar, caso exista.
Defina o papel da área principal.
Defina o papel de painéis auxiliares, caso existam.
Defina como Projects, Contracts, Study, Admission, Runs e Evidence se conectam.
Defina a primeira experiência de um usuário sem histórico.
Defina a experiência de cold start de um usuário recorrente.
Defina estados vazios, loading, erro, rejeição e indisponibilidade.
Defina a estratégia responsiva.
Defina expectativas de teclado, foco e accessible names.
Defina restrições contra padrões visuais genéricos.
Defina como o protótipo deve indicar dados demonstrativos.
Defina a lista de interações que precisam funcionar no HTML.
Defina os critérios de aceite específicos da variante.

## Escopo mínimo comum

Cada HTML deve oferecer uma visão navegável de Projects.
Cada HTML deve oferecer uma visão navegável de Contracts.
Cada HTML deve oferecer uma visão navegável de Study.
Cada HTML deve oferecer uma visão navegável de Admission.
Cada HTML deve oferecer uma visão navegável de Runs.
Cada HTML deve oferecer uma visão navegável de Run detail.
Cada HTML deve oferecer uma visão navegável de Evidence.
Cada HTML deve oferecer uma visão navegável de Authority.
Cada HTML deve oferecer uma visão navegável de Bundle.
Cada HTML deve oferecer uma superfície de Chat contextual com estados User, Agent e Activity.
O fluxo principal deve tornar visível a sequência Study → Admission → Run.
O protótipo pode usar dados locais estáticos claramente marcados.
O protótipo não deve fazer chamadas externas.
O protótipo não deve depender de build step.

## Chat e interações mínimas do Agent

Chat e command bar são complementares. A command bar localiza entidades e executa navegação ou
ações explícitas; o Chat sustenta conversa contextual, explicação e criação de drafts.

Inclua no mínimo:

- uma mensagem do User com identidade visual discreta, sem bolha exagerada;
- uma resposta do Agent ou um draft estruturado, visualmente distinto de dado registrado;
- um Activity Block recolhível com estados `active`, `completed`, `waiting` e `unavailable`;
- input de Chat com label acessível, submit, estado disabled e indicação inequívoca de demonstração;
- uma interação local para enviar mensagem demonstrativa;
- uma interação para expandir ou recolher o Activity Block;
- uma ação compacta para abrir o draft gerado, sem registrá-lo ou aceitá-lo automaticamente.

O Activity Block mostra somente progresso observável: `Preparing authorized context`,
`Reading authorized references`, `Draft prepared`, `Waiting for human confirmation`,
`Capability unavailable`, eventos de tool admitidos e estados factuais de Run quando houver fonte.
Nunca mostre chain-of-thought, raciocínio privado, hidden grader, expected answer ou conteúdo interno
do modelo. Não use o rótulo `Thinking` para conteúdo que sugira acesso ao raciocínio privado; quando
o briefing exigir esse nome visual, trate-o como título amigável para atividade observável e deixe
essa limitação explícita.

O Chat é uma demonstração de UI enquanto o Lab Agent runtime permanecer `incubating`. Não faça
request de rede, não alegue streaming real, não execute efeito externo, não produza decisão humana
e não transforme nome de ator em prova de autoridade.

## Fora de escopo

Não criar backend.
Não alterar contratos.
Não criar editor de graph protocol.
Não criar canvas visual de execução.
Não conectar o Chat a um runtime real do Lab Agent nesta etapa.
Não apresentar interação local demonstrativa como execução integrada.
Não prometer pause, resume ou múltiplos turnos se o runtime ativo não os suporta.
Não representar input classificado como executável.
Não representar autoridade humana por simples campo de texto.

## Primeira experiência

O primeiro viewport deve explicar o produto sem tutorial longo.
Evite uma homepage vazia composta apenas por uma inputbar.
Se houver command bar e input de Chat, diferencie propósito, placeholder, label e resultado.
A command bar pode representar busca, navegação ou ação explícita.
O input de Chat inicia ou continua conversa contextual e pode criar somente drafts demonstrativos.
O estado inicial deve oferecer uma ação primária inequívoca.
O estado inicial deve mostrar contexto recente sem virar dashboard genérico.
O estado inicial deve distinguir atividade recente de decisão pendente.
O estado inicial deve evitar métricas decorativas sem utilidade operacional.
O estado inicial deve dar acesso direto a `New Study`.
O CTA deve informar se cria draft, inicia validação ou abre um fluxo.

## Cold start recorrente

Para usuários recorrentes, priorize continuidade.
Mostre o Project ativo de forma evidente.
Mostre trabalho pendente antes de dados históricos pouco acionáveis.
Mostre Runs recentes com estado factual e timestamp.
Mostre Admission rejeitada como algo que exige correção, não como falha genérica.
Mostre capability ausente como indisponível, não como botão morto.
Ofereça retorno rápido à última tela relevante.
Permita trocar de Project sem perder a noção do escopo atual.

## Legibilidade, botões e visualização de dados

Evite tratar cada ação como uma barra que ocupa a largura inteira da página.
Botões de desktop devem usar largura de conteúdo, labels curtos e agrupamento próximo ao objeto que
afetam. Botão full-width é reservado para mobile, submit de formulário estreito ou ação única dentro
de um dialog; não é o padrão visual da Console.

Uma linha de entidade pode ser clicável quando a navegação fizer parte de seu significado, mas as
ações secundárias da linha permanecem compactas e separadas. Não transforme uma lista inteira em uma
pilha de grandes botões contornados.

No viewport de referência de 1440 px, preserve uma área principal larga. Evite três colunas
persistentes quando isso reduzir o corpo abaixo de uma largura confortável. Informações terciárias
devem entrar por drawer, popover, dialog ou disclosure contextual. Painéis auxiliares só permanecem
abertos quando a tarefa realmente exige comparação simultânea.

Use corpo de 14–16 px, line-height legível e linhas de texto com aproximadamente 45–75 caracteres.
Não use fonte mono para parágrafos. Digests, IDs, timestamps, enum values e event names podem usar
mono em escala legível.

Não represente todos os dados como texto tabular. Quando a forma ajudar a decisão, use:

- matriz visual para `scenarios × variants × repetitions`;
- comparação pareada para `head-truncation` e `tail-preservation`;
- lifecycle trace para eventos observáveis;
- sequência compacta para Register, Compile, Admission e Enqueue;
- mapa simples de relações entre Run, EvaluationRecord e ArtifactRef;
- disclosure separado para integrity, audit completeness, portability e replayability do Bundle.

Visualização não autoriza métrica inventada. Não use donut, sparkline, porcentagem, health score ou
gráfico sem dado factual e fonte visível.

## Navegação e arquitetura de informação

Avalie se a navegação principal deve ser lateral, superior ou híbrida.
Se usar sidebar, atribua a ela função operacional real.
Se não usar sidebar, preserve acesso previsível a todas as áreas.
Mantenha o Project atual sempre identificável.
Mantenha o estado global de conexão visível sem dominar a tela.
Separe navegação de filtros contextuais.
Separe ações globais de ações da entidade atual.
Evite menus com rótulos vagos.
Use terminologia do Evidrun de forma consistente.
Não renomeie entidades canônicas apenas para parecer mais amigável.
Pode adicionar subtítulos explicativos sem alterar o nome canônico.

## Projects

Trate Project como escopo controlado de trabalho.
Permita selecionar um Project local.
Permita demonstrar criação de Project como draft visual.
Mostre caminho ou origem apenas quando isso não expuser locator proibido em contratos.
Não confunda conceito de Project com ArtifactRef.
Mostre resumo operacional do Project.
Mostre última atividade.
Mostre Studies, Specs ou Runs relacionados conforme a proposta.
Mostre separação clara entre contexto do Project e contexto global.
Inclua estado vazio para primeiro Project.
Inclua estado com múltiplos Projects.
Inclua transição visual ao trocar de Project.

## Contracts e Specs

Use o nome canônico adequado ao contexto exibido.
Apresente revisions sem sugerir mutação de record anterior.
Mostre digest e status quando aplicável.
Permita visualizar preview resumido e detalhe.
Inclua CTA explícito para `New Study`.
Depois de uma revision válida e registrada, use `Compile RunSpecs` como ação contextual.
O CTA pode iniciar um draft guiado.
O draft não deve parecer registrado antes da validação.
Separe editar draft, validar e registrar.
Mostre issues estruturadas em linguagem operacional.
Preserve acesso ao detalhe técnico quando útil.
Inclua estados valid, invalid, draft e unsupported quando aplicáveis.
Não invente aprovação humana automática.

## Study

Permita selecionar uma Study.
Mostre revisão ou identidade relevante da Study.
Ofereça preview da compilação.
Mostre matriz de scenarios × variants × repetitions.
Evite tabela esmagada em viewport estreito.
Em mobile, use agrupamento ou disclosure progressivo.
Mostre a diferença entre configuração e resultado.
Não represente Study como Run executada.
Mostre problemas de compilação perto da origem.
Ofereça caminho claro para Admission após preview válido.

## Admission

Admission deve ser uma etapa explícita.
Nenhuma Run nova deve parecer existir antes de uma decisão admitted.
Mostre o RunSpec exato ao qual a Admission se refere.
Apresente preflight de modo compreensível.
Agrupe issues por impacto e possibilidade de correção.
Distinga rejected de unsupported.
Distinga erro técnico de incompatibilidade de capability.
Mostre capability obrigatória ausente como bloqueio real.
Não permita continuar visualmente quando a decisão é rejected.
Permita retornar à origem para corrigir um draft.
Mostre `admitted` como decisão registrada, não como decoração verde.

## Runs

Mostre fila apenas quando a capability existir na hipótese demonstrada.
Quando não existir, marque a integração como pendente.
Liste Run, job e attempt sem fundi-los em uma única identidade.
Mostre lifecycle com estados factuais.
Mostre SSE e reconnect como estado explícito quando representados.
Inclua estado de evento duplicado tratado pela interface.
Inclua estado terminal.
Timeout deve aparecer como `run.budget_exhausted`.
Não converta timeout em completed.
Não prometa pause ou resume.
Não prometa múltiplas interações.
Não anuncie budget não admitido pelo runner ativo.
Não use progresso inventado para preencher a tela.

## Run detail

Mostre identidade da Run.
Mostre relação com Study, scenario, variant e repetition quando aplicável.
Mostre AdmissionRecord associado.
Mostre lifecycle em ordem temporal.
Mostre SubjectEnvelope digest como alegação identificada.
Não trate o digest como envelope recomputável pelo bundle.
Mostre eventos válidos para a fase.
Cada evento factual deve apontar para record canônico quando aplicável.
Mostre evaluations separadamente de lifecycle.
Mostre terminal de forma inequívoca.
Não confunda Goal completion, qualidade e lifecycle.

## Evidence

Mostre artifact manifest como conjunto intencional de refs.
Não descreva manifest como inventário de todo arquivo observado.
Não adicione locator a ArtifactRef.
Não prometa leitura, montagem ou exportação apenas por existir uma ref.
Mostre checkpoints quando presentes.
Mostre Progress Artifacts somente quando a policy permitir.
Explique visualmente quando Progress Artifact está indisponível.
Não transforme resumo derivado em segunda fonte de verdade.
Mantenha referências `run:`, `event:` e `artifact:` visíveis quando houver afirmações factuais.
Separe evidência disponível de evidência ausente.

## Authority

Mostre authority como disabled, opt-in ou verificada conforme o cenário.
Não use campo de ator como prova de autoridade.
Não permita que agente, automação ou serviço afirme ser humano.
Human authority exige HumanAttestationRecord verificado.
Sem adapter confiável, a ação deve falhar fechado.
Mostre pedidos de aprovação como drafts aguardando humano.
Não exponha token, assertion ou credencial no DOM.
Não represente `repository_fixture` como humano.
Separe human review de adjudication.
Reforce o caráter append-only de records de avaliação e revisão.

## Bundle

Mostre exportação como capability independente.
Separe integrity de audit completeness.
Separe portability de replayability.
Separe disponibilidade de blobs de presença de refs.
Não prometa restore.
Não prometa replay.
Não prometa estado privado recuperável.
Mostre resultado da verificação de lifecycle.
Mostre resultado da verificação de records e eventos.
Mostre resultado da verificação do conjunto de artifact entries.
Não reduza verificação a checksum isolado.

## Dados demonstrativos

Use dados locais coerentes e pequenos.
Marque-os como `Demo data` ou `Fixture de interface`.
Não use rótulos que sugiram produção.
Não use percentual de sucesso sem base demonstrada.
Prefira exemplos alinhados ao vocabulário do Evidrun.
Evite conteúdo excessivo que esconda a hierarquia.
Inclua pelo menos um caso feliz.
Inclua pelo menos um caso rejected.
Inclua pelo menos um caso unsupported.
Inclua pelo menos um caso terminal por budget exhausted.

## Estados obrigatórios

Inclua loading.
Inclua empty.
Inclua success.
Inclua invalid.
Inclua rejected.
Inclua unsupported.
Inclua failed.
Inclua disconnected.
Inclua reconnecting quando houver streaming.
Inclua terminal completed.
Inclua terminal budget exhausted.
Inclua authority disabled.
Inclua integration pending.
Os estados podem ser acionados por controles de demonstração discretos.
Os controles de demonstração devem ser claramente separados da interface do produto.

## Interações obrigatórias

Todas as áreas principais devem ser navegáveis sem recarregar a página.
O HTML deve permitir trocar de Project.
O HTML deve permitir abrir e fechar detalhes.
O HTML deve permitir iniciar `New Study` como draft autorado.
O HTML deve permitir avançar visualmente entre draft, validation e preview.
O HTML deve bloquear avanço após Admission rejected.
O HTML deve permitir inspecionar uma Run.
O HTML deve permitir alternar entre eventos, evaluations e evidence.
O HTML deve permitir testar pelo menos um estado vazio.
O HTML deve permitir testar pelo menos um erro.
O HTML deve permitir testar viewport estreito sem overflow horizontal acidental.
As interações devem funcionar com mouse e teclado.

## HTML

Entregue um único arquivo `.html` por sub-agent.
Inclua estrutura, estilos e scripts no mesmo arquivo.
Use HTML semântico.
Use CSS organizado por tokens, layout, componentes, estados e responsividade.
Use JavaScript mínimo e legível para demonstrar interações.
Não dependa de framework.
Não dependa de CDN.
Não dependa de pacote externo.
Não faça fetch de recursos externos.
Não exija servidor para funcionar.
O arquivo deve abrir diretamente no navegador.
O protótipo deve continuar compreensível se JavaScript falhar parcialmente.

## Ícones e linguagem visual

Nunca use emoji como ícone de interface.
Use SVG inline simples e semanticamente adequado.
Todo ícone interativo precisa de nome acessível.
Evite excesso de pills.
Evite glassmorphism decorativo.
Evite glow neon sem função.
Evite gradiente roxo e azul associado a estética genérica de IA.
Evite cards repetidos como solução universal.
Evite três métricas fictícias alinhadas apenas para preencher espaço.
Evite dashboard genérico desconectado do fluxo operacional.
Evite headline de marketing dentro de uma ferramenta operacional.

## Direção visual

Cada variante deve assumir uma direção clara.
A direção deve ser reconhecível sem sacrificar legibilidade.
Use uma paleta controlada.
Use escala tipográfica coerente.
Use espaçamento consistente.
Use contraste suficiente.
Use densidade compatível com uma ferramenta operacional.
Varie ritmo entre visão geral e detalhe.
Use cor para semântica, mas nunca como único canal.
Evite simetria rígida em todas as telas.
Evite assimetria que prejudique a leitura de records.
Priorize confiança, precisão e rastreabilidade.

## Animação e transições

Use animação apenas quando explicar mudança de estado ou hierarquia.
Transições devem ser curtas e previsíveis.
Evite animações contínuas sem função.
Evite parallax.
Evite elementos flutuando apenas por estética.
Respeite `prefers-reduced-motion`.
Foco não pode desaparecer durante transição.
Painéis devem abrir sem deslocamento caótico.
Mudança de Project deve comunicar troca de escopo.
Mudança de estado deve preservar contexto.

## Responsividade

Projete primeiro uma estrutura robusta, não apenas um screenshot desktop.
Valide desktop amplo.
Valide notebook.
Valide tablet.
Valide mobile estreito.
Sidebar deve colapsar de forma deliberada.
Tabelas devem adaptar sem cortar conteúdo crítico.
Timeline deve permanecer legível.
CTAs devem manter área de toque adequada.
Texto auxiliar não pode ficar microscópico.
Modais não devem ultrapassar viewport.
Não esconda informação crítica apenas no hover.

## Acessibilidade

Use landmarks semânticos.
Use uma hierarquia correta de headings.
Use botões para ações e links para navegação.
Associe labels a inputs.
Forneça accessible names.
Implemente foco visível.
Preserve ordem de tabulação lógica.
Permita fechar overlays por teclado.
Não prenda foco fora de modal ativo.
Use `aria-live` somente para mudanças relevantes.
Garanta contraste de texto e controles.
Não dependa apenas de cor para status.

## Definição das hipóteses de variante

Não use um conjunto fixo e pré-nomeado de variantes. Para cada batch, defina as hipóteses junto com
o usuário antes de delegar. Cada hipótese deve descrever uma direção de experiência distinta e
completa da mesma console, cobrindo o escopo mínimo comum.

Para cada variante, o batch deve registrar:
- um nome curto e semântico próprio daquela rodada;
- a hipótese central e o problema de produto que ela tenta resolver;
- a sensação desejada nos primeiros cinco segundos;
- a arquitetura de informação e a navegação principal;
- como a sequência Study → Admission → Run fica visível e gated;
- as restrições contra padrões visuais genéricos.

As direções podem variar em densidade, progressive disclosure, contexto persistente de Project,
ênfase em inspeção de evidência ou outra hipótese acordada. Nenhuma variante deve copiar a direção
visual de outra, e todas devem respeitar as fontes de verdade e os limites de capability.

## Uso de skills pelos sub-agents

Instrua cada sub-agent a usar `design-taste-frontend`.
Instrua cada sub-agent a consultar skills de Product Design quando úteis.
Use `product-design:audit` para revisão posterior, não para substituir criação.
Não force uma skill quando ela não se aplicar ao estágio.
Skills orientam qualidade, mas não substituem as fontes de verdade do repositório.
O briefing específico da variante prevalece sobre preferências genéricas de uma skill.

## Delegação

Crie um sub-agent separado para cada variante.
Forneça a cada sub-agent somente a task, fontes necessárias e briefing da variante.
Peça que o sub-agent explique a hipótese em um comentário curto no topo do HTML.
Peça que o sub-agent planeje internamente antes de editar.
Peça que o sub-agent entregue o arquivo na pasta `design/`.
Use nomes de arquivo previsíveis e semânticos que reflitam a hipótese acordada da variante.
Padrão sugerido: `design/operator-console-<slug-da-hipotese>.html`.
Não permita que dois sub-agents editem o mesmo arquivo.
Não permita alterações fora de `design/` durante a exploração.

## Autonomia dos sub-agents

Cada sub-agent deve tomar decisões visuais próprias.
Cada sub-agent deve justificar escolhas por meio do resultado, não por ensaio longo.
Cada sub-agent pode reinterpretar layout dentro das restrições.
Cada sub-agent deve manter os escopos mínimos comuns.
Cada sub-agent deve criar interações reais no HTML.
Cada sub-agent deve revisar seu próprio resultado antes de concluir.
Cada sub-agent deve informar limitações conhecidas.
Cada sub-agent deve confirmar a contagem de linhas.

## Revisão do agente principal

Depois das entregas, abra cada HTML no navegador.
Não avalie apenas o código-fonte.
Teste desktop e mobile.
Teste navegação por teclado.
Teste as interações obrigatórias.
Verifique erros no console.
Verifique overflow e clipping.
Verifique estados falsamente representados.
Verifique aderência à task WS-10.
Verifique se o arquivo está entre 500 e 900 linhas.
Verifique se não há recursos externos.
Verifique se não houve alteração fora de `design/`.

## Revisores especializados

Após a implementação, use revisores read-only.
Um revisor deve avaliar fluxo de UX sem ler o código primeiro.
Um revisor deve avaliar verdade contratual e representação de capability.
Um revisor deve avaliar acessibilidade, responsividade e qualidade visual.
Revisores não editam os HTMLs.
Revisores produzem findings objetivos com severidade.
O agente principal remove duplicatas e conflitos entre findings.
Correções P0 e P1 voltam ao sub-agent autor da variante.
Correções não devem apagar a identidade visual da proposta.

## Rubrica comparativa

Avalie cada variante em clareza inicial.
Avalie cada variante em continuidade no cold start.
Avalie cada variante em arquitetura de informação.
Avalie cada variante em compreensão de Study → Admission → Run.
Avalie cada variante em tratamento de capability indisponível.
Avalie cada variante em verdade dos estados.
Avalie cada variante em inspeção de Run detail.
Avalie cada variante em compreensão de Evidence.
Avalie cada variante em compreensão de Authority.
Avalie cada variante em compreensão de Bundle.
Avalie cada variante em responsividade.
Avalie cada variante em acessibilidade.
Avalie cada variante em qualidade visual.
Avalie cada variante em originalidade sem slop.
Avalie cada variante em densidade de contexto útil.
Avalie cada variante em facilidade de implementação futura.

## Escala de pontuação

Use notas inteiras de 1 a 5 por critério.
Nota 1 significa falha grave ou ausência.
Nota 2 significa solução fraca com lacunas importantes.
Nota 3 significa solução adequada com compromissos visíveis.
Nota 4 significa solução forte e bem resolvida.
Nota 5 significa solução excepcional e pronta para orientar implementação.
Toda nota deve ter evidência observável.
Não some pontos sem registrar justificativa.
Não use média isolada para decidir o vencedor.
P0 aberto impede seleção como direção final.
P1 aberto exige correção antes da seleção.

## Métricas auxiliares

Conte quantas ações principais competem no primeiro viewport.
Conte quantos níveis de navegação são necessários para chegar a Run detail.
Conte quantos estados obrigatórios podem ser demonstrados.
Conte quantos elementos dependem apenas de hover.
Conte quantos controles não possuem nome acessível.
Conte ocorrências de overflow em viewports de teste.
Conte recursos externos requisitados.
Conte avisos ou erros de console.
Registre a faixa de linhas do HTML.
Registre a quantidade aproximada de contexto útil por view.
Use contagens como apoio, não como substituto de julgamento de design.

## Densidade de contexto útil

Defina contexto útil como informação necessária para entender ou agir.
Não conte ornamentação.
Não conte dados repetidos em sidebar e conteúdo.
Não conte métricas sem decisão associada.
Não premie quantidade bruta de texto.
Avalie se o usuário consegue responder: onde estou?
Avalie se o usuário consegue responder: o que aconteceu?
Avalie se o usuário consegue responder: o que está bloqueado?
Avalie se o usuário consegue responder: qual é a próxima ação segura?
Avalie se o usuário consegue responder: qual evidência sustenta esta afirmação?

## Ciclo de seleção

Apresente as variantes ao usuário como opções comparáveis.
Mostre uma síntese curta da hipótese de cada uma.
Mostre pontos fortes observados.
Mostre riscos ou lacunas observadas.
Peça que o usuário selecione apenas uma variante por rodada.
Não misture variantes antes da seleção.
Aceite feedback textual sobre a variante escolhida.
Transforme feedback em mudanças específicas e verificáveis.
Faça uma rodada de refinamento por vez.
Reavalie a variante após cada rodada.
Não declare direção final sem confirmação do usuário.

## Pergunta ao usuário

Depois de validar o batch, faça uma pergunta objetiva.
Pergunte qual variante deve avançar para refinamento.
Liste A, B, C e D com uma frase de diferenciação cada.
Permita resposta livre além da escolha.
Não faça várias perguntas simultâneas.
Não peça decisões que possam ser verificadas no repositório.

## Refinamento da escolhida

Reative apenas o sub-agent autor da variante escolhida.
Forneça o feedback consolidado.
Peça mudanças limitadas ao HTML daquela variante.
Preserve a hipótese visual escolhida.
Corrija findings P0 e P1.
Melhore gaps de interação identificados.
Valide novamente no navegador.
Atualize a rubrica comparativa da escolhida.
Registre decisões de design em documento temporário somente se solicitado.
Não promova decisões para ADR ou contrato nesta etapa.

## Critérios de aceite do batch

Existem quatro HTMLs quando a quantidade padrão é usada.
Cada HTML foi produzido por um sub-agent independente.
Cada HTML contém entre 500 e 900 linhas reais.
Cada briefing enviado contém entre 300 e 700 linhas reais.
Cada HTML cobre o escopo mínimo comum.
Cada HTML funciona sem rede e sem build.
Cada HTML possui interações demonstráveis.
Cada HTML diferencia fixture de execução real.
Cada HTML trata Admission como gate anterior à Run.
Cada HTML respeita limites de Authority, Evidence e Bundle.
Cada HTML possui estados loading, empty, rejected, unsupported, failed e terminal.
Cada HTML é navegável por teclado em seus fluxos principais.
Cada HTML funciona em desktop e mobile.
Cada HTML evita emojis e recursos externos.
Cada HTML foi inspecionado visualmente.
Cada HTML foi revisado por critérios comuns.
Os resultados comparativos possuem evidência observável.

## Falhas que exigem correção

Run criada visualmente antes de Admission admitted.
Capability ausente apresentada como executável.
Fixture apresentada como dado real.
Autoridade humana inferida de campo de texto.
Token ou credencial presente no DOM.
ArtifactRef com locator.
Bundle descrito automaticamente como portátil ou replayable.
Timeout apresentado como completed.
Progress Artifact inventado sem policy adequada.
Manifest descrito como inventário de todos os arquivos.
Chat apresentado como runtime integrado apesar de a capability continuar `incubating`.
Activity Block expondo chain-of-thought, hidden grader, expected answer ou raciocínio privado.
Botões de largura total usados como padrão e comprimindo o conteúdo da página.
Três colunas persistentes tornando corpo, labels ou ações estreitos e difíceis de ler.
Dependência externa quebrando execução offline.
Interação crítica inacessível por teclado.
Layout inutilizável em mobile.
HTML fora da faixa de linhas.
Briefing do sub-agent fora da faixa de linhas.

## Formato do relatório final

Comece pelo resultado do batch.
Liste os arquivos produzidos.
Explique a hipótese de cada variante em uma frase.
Informe a contagem de linhas de cada HTML.
Informe quais viewports foram verificados.
Informe quais interações foram testadas.
Informe findings P0 e P1, mesmo que a lista esteja vazia.
Apresente a tabela de notas com justificativas curtas.
Separe claramente protótipo concluído de integração pendente.
Separe claramente dados demonstrativos de dados reais.
Finalize pedindo a escolha de uma única variante.

## Comando final de execução

Agora leia as fontes de verdade.
Defina o batch e seus critérios comuns.
Escreva quatro briefings independentes entre 300 e 700 linhas.
Delegue uma variante a cada sub-agent.
Garanta que cada sub-agent crie um único HTML entre 500 e 900 linhas em `design/`.
Não permita dependências externas nem alterações fora de `design/`.
Espere todas as variantes ficarem prontas.
Inspecione cada uma no navegador em desktop e mobile.
Execute a revisão de UX, verdade contratual e acessibilidade.
Corrija findings P0 e P1 com o sub-agent autor.
Compare as variantes usando a mesma rubrica.
Entregue o relatório e peça ao usuário que escolha uma única direção para refinamento.
