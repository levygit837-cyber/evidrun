# Prompt Ultradesign — Evidrun Operator Console

## Papel

Você é responsável por criar um protótipo visual completo para o Evidrun Operator Console.
Use o workflow Ultradesign.
Produza uma direção visual inédita.
Não use como referência nenhum protótipo anterior do projeto.
Não preserve a aparência atual do frontend.
Não tente fazer uma pequena melhoria incremental.
Crie um sistema visual novo, coerente, preciso e sofisticado.
O resultado deve parecer desenhado por uma equipe de produto sênior.
O resultado deve ser um protótipo funcional e navegável.
O resultado deve permitir avaliar o fluxo completo, não apenas uma página isolada.

## Entrega obrigatória

Retorne um documento HTML completo.
Inclua todo o CSS necessário no próprio HTML.
Inclua todo o JavaScript necessário no próprio HTML.
O HTML deve abrir diretamente no navegador.
Não dependa de build step.
Não dependa de backend.
Não faça requests de rede.
Não use dados secretos.
Não use assets privados.
Use dados demonstrativos locais claramente identificados.
Implemente interações reais do protótipo com JavaScript local.
Implemente navegação entre as áreas principais.
Implemente os estados essenciais descritos neste briefing.
Preserve o estado básico da demonstração durante a navegação.
Não retorne explicações fora do HTML.

## Produto

Evidrun é um laboratório local-first para experimentos auditáveis com agentes de IA.
O produto transforma hipóteses em Studies versionados.
Studies compilam Specs executáveis.
Specs passam por validação estrutural.
Specs exatas passam por Admission.
Somente Specs admitidas podem originar Runs.
Runs preservam execução, eventos, avaliações e evidência.
O produto separa fatos, inferências, drafts e decisões humanas.
O produto não usa chain-of-thought privado como evidência.
O produto prioriza evidência antes de narrativa.
O público inicial é formado por desenvolvedores e pesquisadores técnicos.
O usuário precisa compreender operações complexas sem ler JSON bruto.
O usuário precisa confiar que a interface não está inventando capabilities.

## Objetivo da experiência

Sintetize todo o fluxo de criação em uma experiência contínua.
O fluxo principal é Study → Spec → Validation → Admission.
O fluxo deve parecer uma única atividade progressiva.
O usuário não deve sentir que está preenchendo vários produtos desconectados.
O usuário deve perceber claramente onde está no processo.
O usuário deve compreender o que ainda falta para executar.
O usuário deve conseguir corrigir problemas sem perder o contexto.
O usuário deve revisar o objeto exato antes da Admission.
O usuário deve decidir conscientemente quando enfileirar Runs.
Runs completas devem viver na área separada de Observability.
O fluxo de criação termina com um handoff explícito para Observability.

## Decisão de arquitetura de informação

Use duas áreas primárias de produto.
A primeira área é Create.
A segunda área é Observability.
Create contém Study, Spec, Validation e Admission.
Observability contém Runs, attempts, events, evaluations, evidence e Bundles.
Não crie uma aba independente para cada pequeno estágio de Create.
Não transforme Study, Spec, Validation e Admission em quatro produtos separados.
Apresente esses estágios como uma superfície contínua com progressão explícita.
Depois de Admission admitted, apresente a ação Queue Runs.
Depois do enqueue demonstrativo, direcione o usuário a Observability.
Mantenha a relação entre a Run e sua Study/Spec sempre inspecionável.

## Regra visual central

Não use composição baseada em cards.
Não use card grids.
Não use card dentro de card.
Não coloque cada seção em um retângulo arredondado.
Não coloque cada entidade em uma caixa flutuante.
Não represente o produto como um dashboard de widgets.
Não use blocos quadrados decorativos para criar hierarquia.
Não use blocos arredondados decorativos para criar hierarquia.
Não transforme cada status em uma pill.
Não use badge soup.
Não use glassmorphism.
Não use gradientes genéricos de produto de IA.
Não use sombras grandes como separador principal.
Não use bordas em volta de todo conteúdo.
Não imite a aparência padrão de shadcn dashboards.
Não use uma pilha de containers com o mesmo radius.
Não crie uma interface formada por dezenas de pequenas ilhas visuais.

## Como criar hierarquia sem cards

Use tipografia com intenção.
Use escala tipográfica disciplinada.
Use alinhamento rigoroso.
Use whitespace para separar assuntos.
Use ritmo vertical consistente.
Use divisores finos somente quando necessários.
Use mudanças amplas de plano de fundo.
Use trilhos de progressão.
Use colunas editoriais.
Use tabelas sem caixas externas quando os dados forem tabulares.
Use linhas contínuas para entidades relacionadas.
Use indentation para revelar hierarquia.
Use sticky context para manter o objeto atual visível.
Use disclosures para detalhes avançados.
Use transições sutis para mudanças de estado.
Use contraste e densidade para indicar prioridade.
Inputs podem ter contornos quando necessário.
Menus podem ter superfícies próprias quando abertos.
Dialogs podem ter superfícies próprias quando abertos.
Popovers podem ter superfícies próprias quando abertos.
Essas exceções não devem transformar o conteúdo da página em cards.

## Direção estética

Crie uma estética original para uma ferramenta científica contemporânea.
A interface deve parecer precisa sem parecer hospitalar.
A interface deve parecer técnica sem parecer terminal ou IDE genérica.
A interface deve parecer sofisticada sem parecer uma landing page.
A interface deve parecer calma mesmo quando exibe muitos dados.
A interface deve valorizar leitura prolongada.
A interface deve transmitir autoridade operacional.
A interface deve transmitir rastreabilidade.
A interface deve evitar espetáculo visual gratuito.
Escolha uma direção estética forte e mantenha-a em todas as views.
Você tem liberdade para escolher tema claro, escuro ou híbrido.
Você tem liberdade para escolher a família tipográfica.
Você tem liberdade para escolher a paleta.
Você tem liberdade para escolher a composição do shell.
Não herde cores ou componentes dos protótipos existentes.
Não use imagens dos protótipos existentes.
Não reproduza layouts dos protótipos existentes.

## Linguagem e terminologia

Use português brasileiro na interface.
Preserve nomes técnicos canônicos em inglês.
Use Study.
Use Spec.
Use Admission.
Use Run.
Use RunSpec quando o identificador técnico for importante.
Use AdmissionRecord quando o record for importante.
Use EvaluationRecord quando o record for importante.
Use SubjectEnvelope quando o envelope for importante.
Use ArtifactRef quando a identidade do artifact for importante.
Use Bundle quando a exportação for importante.
Evite inventar nomes amigáveis que apaguem entidades canônicas.
Use subtítulos curtos para explicar termos complexos.

## Shell global

Crie um shell consistente para Create e Observability.
Mantenha o Project atual sempre visível.
Use o Project demonstrativo Context Reliability Lab.
Permita trocar o Project por um controle funcional.
Mostre que o backend local está conectado.
Mostre que o worker está disponível.
Mostre o provider configurado sem revelar credencial.
Mostre Authority como unavailable ou opt-in quando apropriado.
Não transforme esses estados em quatro cards.
Não permita que health indicators dominem a interface.
Ofereça acesso a configurações.
Ofereça acesso a documentação.
Ofereça uma command surface discreta para localizar entidades.
Não confunda command surface com Chat.
Não faça Chat ser o centro da experiência.
Não implemente Chat funcional neste protótipo.

## Navegação principal

Use Create como destino primário para autoria.
Use Observability como destino primário para execução.
Permita alternar entre as duas áreas sem perder o Project atual.
Marque claramente a área ativa.
Evite uma sidebar cheia de seções pequenas.
Evite navegação que repita todos os estágios internos de Create.
Dentro de Create, use uma progressão contextual.
Dentro de Observability, use filtros e seleção de Runs.
Em viewport estreito, mantenha a navegação acessível e previsível.

## Primeira experiência em Create

Abra diretamente no trabalho ativo.
Não use uma homepage de marketing.
Não use uma página vazia com uma grande input bar.
Mostre uma Study draft em andamento.
Mostre o Project atual.
Mostre a intenção da Study.
Mostre a progressão geral do fluxo.
Mostre a próxima ação recomendada.
Mostre alterações ainda não validadas.
Mostre que os dados são demonstrativos.
Não use métricas decorativas no topo.

## Estrutura contínua de Create

Organize Create como uma composição progressiva.
Permita navegar por âncoras internas sem separar tudo em páginas.
Mantenha um resumo persistente da Study e do status atual.
Faça cada estágio ocupar uma região clara da mesma superfície.
Evite caixas externas em volta das regiões.
Use transições de densidade entre visão resumida e edição.
Permita recolher detalhes concluídos.
Permita reabrir detalhes concluídos.
Mostre dependências entre campos.
Mostre alterações que invalidam uma Admission anterior.

## Study demonstrativa

Nome da Study: Retenção de contexto sob pressão de tool results.
Objetivo: medir se uma política de contexto preserva evidência relevante após resultados extensos.
Hipótese: Structured Collapse reduz perda de constraints sem prejudicar o resultado final.
Project: Context Reliability Lab.
Modo de comparação: controlled prospective comparison.
Cenário principal: tool-result pressure.
Variante de controle: Full History.
Variante experimental: Structured Collapse.
Repetições: 3 por variante.
Total previsto: 6 Runs.
Mostre a matriz scenarios × variants × repetitions de forma legível.
Não transforme cada célula em um card.
Use uma matriz, faixa, tabela ou visualização contínua.
Mostre claramente a variável primária.
Mostre claramente o que permanece controlado.
Não use score ou porcentagem inventada.

## Edição da Study

Permita editar nome.
Permita editar objetivo.
Permita editar hipótese.
Permita selecionar cenários.
Permita configurar variantes.
Permita configurar repetitions.
Permita revisar a matriz resultante.
Use labels acessíveis.
Use help text somente quando necessário.
Não faça todos os campos ocuparem largura total no desktop.
Agrupe campos por significado, não por cards.
Mostre dirty state.
Mostre autosave demonstrativo.
Não alegue persistência real.

## Composição da Spec

Depois da Study, mostre a Spec compilável na mesma superfície.
Trate Spec como definição executável versionada.
Mostre revision atual.
Mostre digest demonstrativo.
Mostre alterações desde a revision anterior.
Mostre quais módulos estão completos.
Mostre quais módulos exigem atenção.
Não represente módulos como uma grade de cards.
Use uma lista estrutural, outline, rail ou composição editorial.
Permita selecionar um módulo e editar seus detalhes.

## Módulos da Spec

Inclua Goal.
Inclua Subject.
Inclua Inputs.
Inclua Context Policy.
Inclua Workspace.
Inclua Interaction.
Inclua Capability Requirements.
Inclua Evaluation Plan.
Inclua Budgets.
Inclua Stop Conditions.
Inclua Disclosure.
Inclua Capture Policy.
Inclua Authority requirements.
Mostre módulos unsupported com honestidade.
Não faça módulos unsupported parecerem configuráveis e executáveis.

## Goal

Use goal_state como tipo ativo.
Mostre objetivo compilado.
Mostre condição terminal goal_complete.
Mostre que Goal não equivale a avaliação de qualidade.
Não invente achievement automático.

## Subject

Mostre provider cliproxyapi-local.
Mostre model deepseek-v4-flash.
Mostre reasoning max.
Mostre que credencial está disponível sem revelar valor.
Mostre interface single_turn.
Mostre uma única interação admitida.
Mostre read_text como capability quando aplicável.
Não ofereça shell arbitrário.
Não ofereça tools não admitidas.

## Inputs e disclosure

Mostre um input text/plain UTF-8.
Classificação demonstrativa: internal.
Mostre que sensitive e restricted são rejeitados pelo runtime atual.
Mostre Subject-visible content de forma resumida.
Não exponha conteúdo privado desnecessário.
Mostre disclosure none como executável.
Mostre pre_run como compilável porém não admitido pelo runner atual.
Não confunda ArtifactRef com acesso ao artifact.
Não exiba locator em ArtifactRef.

## Workspace e interação

Mostre workspace in_process.
Mostre network provider_only para o Subject real.
Mostre external effects denied.
Mostre single_turn ativo.
Mostre max_turns igual a 1.
Mostre configurações incompatíveis como unavailable.
Não ofereça pause ou resume.
Não ofereça runtime bounded exploration.

## Evaluation Plan

Mostre um grader determinístico booleano.
Mostre quando a avaliação é acionada.
Mostre que EvaluationRecord é append-only.
Não confunda evaluation com human review.
Não mostre human review como disponível se Authority estiver unavailable.
Não invente model judge ativo.
Use uma descrição humana curta do critério.
Permita inspecionar a configuração técnica em disclosure.

## Budgets e stop conditions

Mostre max_wall_seconds como budget ativo.
Use 900 segundos no exemplo.
Mostre goal_complete como stop terminal aceito.
Mostre budget_exhausted como stop terminal aceito.
Mostre token budget como unsupported no runtime atual.
Mostre cost budget como unsupported no runtime atual.
Mostre output budget como unsupported no runtime atual.
Mostre stop condition custom como unsupported.
Timeout deve aparecer como budget_exhausted, nunca completed.

## Validation

Validation acontece dentro da mesma experiência de Create.
Ofereça uma ação Validar Spec.
Mostre um estado validating curto e funcional.
Mostre o resultado da validação integrado à estrutura da Spec.
Não abra uma página genérica de resultados.
Não coloque cada issue em um card.
Use linhas, annotations, anchors e destaque contextual.
Separe errors de warnings.
Mostre o path técnico de cada issue quando útil.
Traduza a consequência operacional em português.
Permita clicar em uma issue para ir ao campo correspondente.
Permita corrigir a issue no protótipo.
Atualize o estado local depois da correção.

## Cenário de Validation inválida

Comece com uma incompatibilidade demonstrativa corrigível.
Use max_turns igual a 3 como valor inválido inicial.
Explique que o runner atual admite uma única interação.
Mostre a ação Corrigir para 1.
Inclua um warning de capability não disponível.
Use progress observer como capability unavailable.
Mostre que warning não é automaticamente um erro.
Depois da correção, permita validar novamente.
Mostre Validation succeeded sem celebração exagerada.

## Admission

Admission acontece depois da validação estrutural.
Admission decide executabilidade do RunSpec exato.
Mostre o digest exato sendo admitido.
Mostre o inventário efetivo de capabilities.
Mostre provider, model, reasoning e network efetivos.
Mostre workspace e interaction efetivos.
Mostre budgets e stops efetivos.
Mostre Authority requirement.
Mostre que Admission pode rejeitar mesmo uma Spec estruturalmente válida.
Não use um simples check verde como explicação suficiente.

## Cenário de Admission rejected

Inclua uma tentativa rejeitada demonstrativa.
Motivo: Progress Artifact policy exige observer indisponível.
Mostre a decisão rejected.
Mostre o AdmissionRecord demonstrativo.
Mostre o motivo estruturado.
Mostre a consequência operacional.
Não permita Queue Runs enquanto rejected.
Permita voltar ao módulo Capture Policy.
Permita remover a policy incompatível.
Permita executar Admission novamente.

## Cenário de Admission admitted

Depois da correção, mostre admitted.
Mostre o novo AdmissionRecord.
Mostre que o record anterior permanece no histórico.
Mostre o digest admitido.
Mostre timestamp demonstrativo.
Mostre capabilities efetivamente admitidas.
Mostre Ready to execute.
Não crie Run automaticamente.
O humano ainda deve acionar Queue Runs.

## Handoff para execução

Após admitted, apresente uma faixa contínua de execução.
Não use um card de sucesso.
Mostre 6 Runs previstas.
Mostre 1 cenário.
Mostre 2 variantes.
Mostre 3 repetitions.
Mostre a Admission usada.
Ofereça Queue 6 Runs.
Ofereça revisar a matriz.
Ofereça copiar o digest.
Depois do enqueue demonstrativo, mostre os Run IDs criados.
Direcione para Acompanhar em Observability.
Não alegue que o enqueue foi real.

## Observability

Observability é uma área própria do produto.
Ela não deve parecer um dashboard de métricas.
Ela deve parecer uma superfície operacional de inspeção.
Mostre Runs relacionadas ao Project atual.
Permita filtrar por Study.
Permita filtrar por variant.
Permita filtrar por lifecycle status.
Permita buscar por Run ID.
Permita alternar entre lista e detalhe.
Não use cards para cada Run.
Use uma tabela, ledger ou lista contínua de alta legibilidade.

## Lista de Runs

Mostre as 6 Runs enfileiradas.
Inclua queued.
Inclua preparing.
Inclua running.
Inclua evaluating.
Inclua completed.
Inclua budget_exhausted.
Use timestamps coerentes.
Mostre variant e repetition.
Mostre job e attempt de forma secundária.
Mostre terminal quando existir.
Não invente porcentagem de progresso.
Use estado observável, não progress fictício.
Permita selecionar uma Run.

## Detalhe da Run

Abra uma Run completed por padrão ao entrar no detalhe.
Mostre Run ID.
Mostre origem na Study.
Mostre RunSpec ID.
Mostre AdmissionRecord ID.
Mostre variant e repetition.
Mostre lifecycle factual.
Mostre job e attempt.
Mostre worker e lease de forma acessível em detalhes operacionais.
Mostre que esses dados são demonstrativos.
Não coloque cada conjunto em um card.
Use regiões contínuas e alinhadas.

## Lifecycle da Run

Mostre run.queued.
Mostre run.preparing.
Mostre context.composed.
Mostre run.running.
Mostre subject.invoked.
Mostre tool.called para read_text.
Mostre tool.completed.
Mostre subject.responded.
Mostre run.evaluating.
Mostre evaluation.completed.
Mostre run.completed.
Use uma timeline ou ledger contínuo.
Permita expandir eventos.
Não mostre chain-of-thought.
Não mostre hidden grader.
Não mostre expected answer oculto.

## Subject e tool tracing

Mostre SubjectEnvelope digest.
Explique que o envelope exato foi persistido.
Mostre provider, model e reasoning efetivos.
Mostre contagem de rounds.
Mostre usage quando disponível.
Mostre read_text como tool admitida.
Mostre arguments e result apenas por refs seguras.
Não mostre path ou locator dentro de ArtifactRef.
Não revele raw reasoning.
Não revele credencial.
Não revele corpo livre de erro upstream.

## Evaluation

Mostre o EvaluationRecord terminal.
Mostre grader determinístico.
Mostre outcome booleano.
Mostre evidence refs associadas.
Mostre created_at.
Mostre que records são append-only.
Não use um grande score circular.
Não use donut chart.
Não invente confidence.
Use comparação direta e texto factual.

## Evidence

Mostre artifact manifest intencional.
Mostre ArtifactRefs relevantes.
Mostre SubjectEnvelope digest.
Mostre result artifact quando permitido.
Mostre evaluation artifact quando permitido.
Não descreva o manifest como inventário de todo arquivo observado.
Não prometa blobs portáveis.
Não prometa restore.
Não prometa replay.
Permita inspecionar relações entre records e artifacts.
Use uma visualização estrutural somente quando ajudar a compreensão.

## Bundle

Mostre ação Export Bundle.
Depois da ação demonstrativa, mostre resultado de verificação.
Separe integrity.
Separe audit completeness.
Separe portability.
Separe replayability.
Use integrity verified no exemplo concluído.
Use audit completeness verified no exemplo concluído.
Use portability false.
Use replayability false.
Use mode references_only.
Explique que auditável não significa portável ou replayable.
Não coloque esses quatro conceitos em quatro cards.
Use uma composição comparativa contínua.

## Estados de erro e recuperação

Inclua uma Run budget_exhausted acessível pela lista.
Mostre que max_wall_seconds terminou a Run.
Não represente como completed.
Inclua um attempt expirado em detalhes operacionais.
Mostre um attempt posterior quando a recuperação é permitida.
Não invente reinvocação silenciosa após outcome indeterminado.
Mostre Retry como ação humana explícita quando aplicável.
Explique que Retry cria outra Run.

## Authority

Mostre Authority unavailable no estado demonstrativo principal.
Explique que ator textual não prova autoridade humana.
Não permita aceitar em nome do humano por campo de texto.
Não mostre botão de human review funcional sem adapter confiável.
Se mostrar configuração opt-in, marque como unavailable neste protótipo.
Não revele launch token.
Não revele attestation payload sensível.

## Dados demonstrativos

Marque globalmente Demo data.
Marque ações locais como Prototype interaction.
Não misture fixture com dado conectado.
Use IDs plausíveis, mas claramente demonstrativos.
Use timestamps coerentes.
Use America/Asuncion como timezone exibido.
Use datas consistentes dentro da mesma sessão.
Não use lorem ipsum.
Use conteúdo de produto realista e conciso.

## Interações obrigatórias

Alternar entre Create e Observability.
Trocar Project em um seletor local.
Editar o nome da Study.
Alterar repetitions.
Expandir e recolher módulos da Spec.
Executar Validation.
Navegar de uma issue até o campo inválido.
Corrigir max_turns de 3 para 1.
Executar Validation novamente.
Executar Admission e receber rejected.
Navegar ao Capture Policy incompatível.
Remover Progress Artifact policy.
Executar Admission novamente e receber admitted.
Acionar Queue 6 Runs.
Ir para Observability.
Filtrar Runs por status.
Selecionar uma Run.
Expandir eventos do lifecycle.
Alternar entre Run completed e budget_exhausted.
Executar Export Bundle demonstrativo.
Ver o resultado separado da verificação.

## Feedback das interações

Toda ação deve produzir feedback perceptível.
Não use toasts para toda ação.
Prefira mudanças locais próximas ao objeto afetado.
Use toast apenas para feedback transitório global.
Mostre loading states breves.
Evite skeleton cards.
Use placeholders estruturais contínuos quando necessário.
Mantenha focus depois de ações importantes.
Não faça mudanças de layout abruptas sem transição.

## Responsividade

Projete primeiro para desktop amplo em 1440 × 900.
O HTML também deve funcionar em tablet.
O HTML também deve funcionar em mobile.
Não reduza desktop para uma pilha infinita de cards no mobile.
Preserve a progressão de Create em telas estreitas.
Transforme contextos secundários em disclosures ou drawers.
Mantenha ações críticas alcançáveis.
Mantenha tabelas utilizáveis com estratégia responsiva.
Permita scroll horizontal localizado quando indispensável.
Não esconda estados de trust no mobile.
Não dependa de hover.

## Acessibilidade

Use landmarks semânticos.
Use heading hierarchy coerente.
Use labels reais.
Use buttons para ações.
Use links para navegação.
Implemente focus visible.
Implemente navegação por teclado.
Use contraste suficiente.
Não transmita status apenas por cor.
Use ícone e texto quando necessário.
Respeite prefers-reduced-motion.
Forneça accessible names para icon buttons.
Mantenha target sizes adequados.
Não use texto minúsculo para dados importantes.

## Ícones e gráficos

Use ícones consistentes.
Não use emoji como ícone de interface.
Não use ícones dentro de quadrados decorativos repetidos.
Não use ilustrações genéricas de IA.
Não use gráficos sem dado factual.
Não use KPIs decorativos.
Use visualização somente quando melhorar uma decisão.
Use matriz para scenarios × variants × repetitions.
Use timeline para lifecycle.
Use relações estruturais para provenance quando útil.
Use comparação direta para variants.

## Motion

Use motion com propósito operacional.
Use transições para expansão e troca de estado.
Use duração curta e controlada.
Não use animações contínuas decorativas.
Não use parallax.
Não use partículas.
Não use brilho pulsante para parecer futurista.
Running pode ter um indicador discreto e acessível.
Respeite reduced motion.

## Densidade e legibilidade

Proteja a densidade informacional.
Não desperdice grandes áreas com headlines decorativas.
Não use corpo de texto longo onde uma linha factual basta.
Use monospace somente para IDs, digests, timestamps e event names.
Não use monospace para parágrafos.
Permita scan rápido.
Permita inspeção profunda por disclosure.
Use linhas de texto confortáveis.
Evite três colunas persistentes quando comprimirem o conteúdo principal.
Use contextual panels apenas quando a tarefa exigir comparação simultânea.

## Qualidade visual

O protótipo deve ter uma linguagem reconhecível própria.
Todos os detalhes devem parecer parte do mesmo sistema.
Typography, spacing, borders e motion devem obedecer a regras consistentes.
Estados disabled devem ser legíveis.
Estados unavailable devem ser diferentes de disabled por permissão.
Rejected deve ser diferente de failed.
Failed deve ser diferente de budget_exhausted.
Admitted deve ser diferente de completed.
Draft deve ser diferente de record persistido.
Não dependa de cor saturada para produzir acabamento.
Priorize precisão de composição.

## Restrições de verdade do produto

Não criar Run antes de Admission admitted.
Não tratar Validation succeeded como Admission admitted.
Não tratar admitted como execução iniciada.
Não tratar actor name como autoridade humana.
Não mostrar sensitive ou restricted como executável.
Não mostrar max_turns maior que 1 como admitido.
Não mostrar tools arbitrárias como disponíveis.
Não mostrar pause ou resume como implementados.
Não mostrar bounded exploration como implementado.
Não tratar timeout como completed.
Não tratar Bundle como automaticamente portável.
Não tratar ArtifactRef como acesso ou locator.
Não tratar canvas como fonte canônica.
Não mostrar fixture como backend real.

## Critérios de aceite do protótipo

Existe um único HTML completo.
O HTML contém CSS suficiente para a direção visual final.
O HTML contém JavaScript suficiente para as interações essenciais.
O protótipo abre sem build.
Create e Observability são navegáveis.
Study → Spec → Validation → Admission funciona como fluxo contínuo.
O cenário invalid → corrected funciona.
O cenário rejected → corrected → admitted funciona.
Queue Runs ocorre somente após admitted.
Runs são visualizadas em Observability.
Run completed e budget_exhausted podem ser inspecionadas.
Lifecycle events podem ser expandidos.
Bundle verification pode ser demonstrada.
Dados demonstrativos estão claramente marcados.
Não há composição dominante por cards.
Não há reutilização dos protótipos existentes.
O resultado funciona em desktop e mobile.
O resultado tem acabamento visual consistente.
O HTML retornado é o artifact principal de design.

## Instrução final

Use sua melhor capacidade de design visual e de produto.
Resolva o sistema inteiro como uma experiência coerente.
Não produza uma coleção de telas visualmente desconectadas.
Não simplifique o briefing para uma única página.
Não substitua hierarquia por cards.
Não explique suas decisões fora do documento.
Retorne somente o HTML completo, funcional e autocontido.
