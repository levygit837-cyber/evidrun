EVIDRUN CLASSIC DESIGN
OBSERVABILITY OPERACIONAL
Gere uma página completa em HTML.
Retorne somente HTML.
Inclua CSS e JavaScript no próprio HTML.
Idioma principal: português.
Viewport principal: desktop.
Também seja responsivo.

PAPEL DA PÁGINA
Esta é uma nova página complementar do mesmo protótipo EvidRun.
Ela não substitui Create, Laboratory ou Run Detail.
Ela aprofunda Observability para múltiplas Runs passadas e atividade do agente.
É um protótipo visual com dados Demo, não integração do runtime.

SHELL E ESTILO APROVADOS
Preserve o app shell claro da Laboratory refinada.
Sidebar esquerda próxima de 240 px.
Marca EVIDRUN.
Áreas: Create, Laboratory e Observability.
Observability deve estar ativa.
Projeto: Context Reliability Lab.
Provider: cliproxyapi-local.
Authority: Indisponível.
Health: ok.
Fundo #fcfcfd.
Superfície branca.
Texto #1a1d24.
Muted #6b7280.
Linha #e2e4e9.
Marca #3144eb.
Sucesso #10b981.
Alerta #f59e0b.
Erro #ef4444.
Display Archivo.
Texto Inter.
Dados JetBrains Mono.
Bordas de 1 px.
Raios pequenos.
Sombras mínimas.
Movimento preciso entre 200 e 360 ms.
Não use dark mode, glassmorphism ou gradientes decorativos.

OBJETIVO DE PRODUTO
Permitir que um operador encontre uma Run, entenda seu estado real e inspecione atividade relevante
sem ler JSON bruto.
Não transformar em dashboard de métricas gigantes.
Não usar cards em grade.
Usar linhas, tabela editorial, recuos e espaço para hierarquia.

CABEÇALHO
Título Observability.
Subtexto curto: Runs admitidas, execução e evidência preservada.
Mostrar etiqueta Dados de demonstração.
Incluir pesquisa por Run ID, Study, variant ou evento.
Incluir seletor de período.
Incluir filtros Status, Study, Trust e Provider.
Filtros devem funcionar e atualizar a lista.
Incluir controle Limpar filtros.

RESUMO COMPACTO
Usar uma faixa linear pequena, não cards.
Mostrar contagens Demo para Running, Evaluating, Completed, Failed e Budget exhausted.
Não inventar percentuais de sucesso.
Não chamar visitantes, eventos ou execuções de sucesso sem base.

LISTA DE RUNS
Criar uma tabela/lista densa e legível.
Colunas: Run, Study/variant, trust, provider, phase/status, attempt, duração e horário.
Usar IDs e digests plausíveis, marcados Demo.
Estados possíveis: queued, preparing, running, evaluating, completed, failed e budget_exhausted.
Não incluir uma Run rejected, pois nenhuma Run existe antes de Admission admitted.
Admission rejected pode aparecer apenas como issue separado fora da tabela de Runs.
Uma linha pode mostrar retry_of e geração de lease.
Seleção por clique e teclado deve atualizar o inspector.
Hover e selected state discretos.

INSPECTOR DA RUN SELECIONADA
Abrir como painel lateral interno ou split view, sem modal grande.
Manter a tabela visível.
Mostrar RunSpec, AdmissionRecord, job, attempt e SubjectEnvelope digest.
Mostrar trust mode Demo sem fingir autoridade humana.
Mostrar lifecycle atual e terminal quando houver.
Mostrar refs canônicas run:, event: e artifact: quando aplicável.

ATIVIDADE DO AGENTE
No inspector, criar tabs funcionais: Lifecycle, Agent activity, Evaluation e Infrastructure.
Lifecycle usa sequência canônica:
run.queued
run.preparing
context.composed
capability.offered
run.running
subject.invoked
tool.called
tool.completed
subject.responded
run.evaluating
evaluation.completed
run.completed
Mostrar somente eventos compatíveis com a Run selecionada.
Cada evento pode expandir detalhes inline.
Agent activity mostra a read tool admitida e seus resultados Demo.
Não sugerir runtime genérico de tools.
Evaluation mostra vetor de dimensões e gates, não score global inventado.
Infrastructure mostra job, attempt, lease, heartbeat e fencing.

INTERAÇÕES
Pesquisar e filtrar Runs.
Selecionar uma Run.
Abrir e fechar o inspector.
Trocar tabs do inspector.
Expandir e recolher evento.
Usar botão discreto Simular atualização Demo para fazer uma Run running avançar para evaluating e
completed sem afirmar conexão real.
Mostrar loading linear curto durante a simulação.
Permitir reset dos dados Demo.
Escape fecha menus e inspector quando aplicável.

ESTADOS IMPORTANTES
Lista carregando.
Lista vazia por filtros.
Backend disconnected/reconnecting como banner contextual de Demo.
Run failed.
Run budget_exhausted.
Run terminal completed.
Admission issue separado, sem criar Run falsa.

RESPONSIVIDADE
Em telas menores, tabela vira lista linear.
Inspector vira overlay lateral com divisor fino.
Filtros continuam acessíveis.
Não cortar IDs ou controles essenciais.

RESTRIÇÕES DE VERDADE
Lab Agent runtime continua incubating.
Read tool é a única tool real verificada no runtime atual.
Checkpoint coordinator e Progress Artifact observer não estão executáveis.
Human review UI não fecha o fluxo e não pode aparecer concluída sem autoridade.
Bundle v3 é references_only, portable=false e replayable=false.
Marcar fixtures como Demo.

ANTI-PADRÕES
Não use cards por toda parte.
Não use métricas gigantes.
Não use chat bubbles.
Não use emojis.
Não use fundo escuro.
Não use gradientes decorativos.
Não use cantos excessivamente redondos.
Não use em dash ou en dash visível.
Não prometa replay, restore, blobs, grants ou autoridade humana.

QUALIDADE
Entregue uma página operacional, auditável e detalhada.
Implemente as interações em JavaScript.
Use estados ARIA e foco visível.
Respeite prefers-reduced-motion.
Retorne somente HTML completo.
