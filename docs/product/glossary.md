---
id: product-glossary
type: contract
title: Glossário canônico
status: accepted
authority: normative
volatility: timeless
owner: product
created_at: 2026-07-22
updated_at: 2026-07-28
applies_to: domain
sources:
  - docs/adr/0018-lab-agent-copilot-scope.md
  - docs/adr/0020-workspace-project-run-environment-boundaries.md
  - docs/adr/0021-hierarchical-lab-agent-scope.md
  - docs/adr/0022-explicit-execution-trust-without-per-run-authentication.md
  - docs/contracts/execution-trust-v1.md
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun
verification_refs: []
---

# Glossário

- **Workspace:** fronteira durável do Control Plane para isolamento de dados, regras locais e futura
  sincronização. Contém Projects, mas nunca é materializado para uma Run.
- **Project:** linha coerente de investigação dentro de um Workspace. Organiza autoria, conversas,
  memória, proveniência e Runs relacionadas; não é diretório nem instância de agente.
- **Study:** raiz de autoria para uma pergunta, hipótese, avaliação, diagnóstico ou exploração; pode
  compilar uma Run ou uma matriz de Runs.
- **StudyIntent:** propósito e perguntas do laboratório; não é instrução automática do Subject.
- **Goal:** objetivo e limites entregues ao Subject; permanece separado da avaliação.
- **Scenario:** inputs, condições observáveis, limitações e provenance versionados para uma Run.
- **Experiment Manifest v1:** contrato legado compatível, importável para um Study.
- **Variant:** override tipado sobre um blueprint; variants pré-Run são irmãs.
- **RunSpec:** configuração atômica, imutável e compilada de scenario, variant e repetição.
- **Run Environment:** ambiente efêmero, admitido e materializado para uma única Run a partir de
  configuração versionada. O schema v1 ainda chama essa configuração de
  `WorkspaceTemplateRevision`; o conceito de produto não é um Workspace nem sinônimo de sandbox.
- **AdmissionRecord:** decisão pré-fila com inventário, Run Environment e capabilities efetivamente
  resolvidos.
- **Run:** tentativa ligada a RunSpec e AdmissionRecord exatos.
- **SubjectEnvelope:** visão mínima compilada para o Subject, sem dados do laboratório ou grader
  oculto.
- **Subject Evaluation Guidance:** disclosure público mínimo materializado antes da Run; não é o
  EvaluationPlan completo.
- **Subject Agent:** sistema sob teste dentro de uma Run; recebe apenas o `SubjectEnvelope`.
- **Lab Agent:** copiloto do control plane e superfície primária de trabalho do laboratório. Conduz
  formulação de hipótese, propõe drafts de qualquer contract de autoria, propõe métricas e graders,
  explica Runs e evidência, e opera as mesmas superfícies públicas que um humano. Não possui
  autoridade humana: não decide, não aceita, não atesta e não fala com o Subject. Ver
  [ADR 0018](../adr/0018-lab-agent-copilot-scope.md).
- **LabAgentEnvelope:** contexto declarado do Lab Agent — Workspace obrigatório, Project e foco
  opcionais, contracts visíveis, evidência autorizada por referência, sessão e catálogo de
  capabilities efetivas. Nunca contém credenciais nem concede acesso implícito a outro Project.
- **MemoryEntry:** entrada de memória operacional do Lab Agent sob isolamento obrigatório de
  Workspace e escopo opcional de Project, discriminada por `kind` (`rule`, `preference`, `decision`,
  `observation`, `episode`), append-only e promovida por humano. `observation` exige
  `evidence_refs`. Não é evidência e não entra no `SubjectEnvelope`.
- **Cue:** pergunta que uma `MemoryEntry` responde, escrita como o usuário perguntaria; é o campo de
  descoberta, não palavra-chave. **Anti-cue** declara o que a entrada não cobre.
- **Memory candidate:** entrada escrita pelo consolidador com `status=candidate`; não é elegível para
  retrieval até promoção humana.
- **authority subject:** conteúdo assinado numa attestation humana (`HumanSubjectEnvelope`, ADR
  0015). É objeto de assinatura, não um agente, e não se confunde com o Subject Agent.
- **Agent Inventory:** requisitos de runner, provider, tools, skills e runtime de uma Run.
- **Resolved Agent Inventory:** snapshot hasheado do que a admissão realmente resolveu.
- **Context Policy:** regra de seleção, ordem, truncamento ou transformação.
- **Context Plan:** candidatos e decisões considerados antes da montagem.
- **Context Snapshot:** entrada efetivamente entregue numa invocação.
- **Context Diff:** diferença classificada entre snapshots.
- **Event:** observação append-only da execução.
- **Artifact:** conteúdo identificado por digest e metadata; `ArtifactRef` não possui locator de
  storage e a referência não concede acesso.
- **Artifact Access Grant:** autorização futura, separada da identidade, que limita consumer,
  finalidade, operações, classification e prazo.
- **Progress Artifact:** resumo provisório, derivado e append-only ancorado a uma boundary; seus
  schemas existem, mas o observer/persistência runtime não. Não é inventário de arquivos nem segunda
  fonte de verdade.
- **EvaluationPlan:** dimensões, stages, gates, disclosure, blinding e agregação opcional.
- **EvaluationRecord:** resultado vetorial, ancorado e append-only produzido por grader, judge ou
  humano.
- **Human review:** avaliação humana primária declarada como stage do plano.
- **Human adjudication:** decisão humana posterior sobre precedência entre records, sem sobrescrita.
- **Human Attestation:** evidência tipada de verificação humana que cobre principal, ação e conteúdo
  exatos; sem adapter confiável, a operação falha fechada.
- **Repository Fixture Authority:** importa aceitação de fixture legado por caminho interno; é
  explicitamente não humana.
- **Execution Revision Set:** conjunto fechado e ordenado da Study e de todas as revisions
  necessárias para compilá-la, escopado a um Project e identificado por digest canônico.
- **Execution Trust Record:** record imutável que liga um RunSpec exato a um Execution Revision Set
  e declara `unverified_revision_set` ou `verified_revision_set`; trust não descreve isolamento.
- **ReviewPackage:** projeção legível do Execution Revision Set, das diferenças e das condições
  efetivas para revisão humana; não é attestation nem concede autoridade.
- **ReviewTarget:** documento canônico mínimo que liga o digest do Execution Revision Set aos
  digests ordenados de todos os RunSpecs revisados; é identidade semântica, não relatório visual.
- **Checkpoint:** marco validado e ancorado no ledger; não significa restore ou replay.
- **Bounded exploration result:** resultado em dois eixos: disposition operacional e stop reason
  factual; nenhum deles é pass/fail ou score.
- **Grader:** avaliador versionado que produz EvaluationRecord; Grade é projeção legada.
- **Comparison:** leitura pareada de runs e seus trade-offs.
- **pass@k:** probabilidade de ao menos um acerto em k tentativas do mesmo RunSpec lógico; mede
  potencial. Exige repetições.
- **pass^k:** probabilidade de acertar todas as k tentativas; mede confiabilidade. Divergem com k.
- **Batch de execução:** lote de RunSpecs de um mesmo Study enfileirado numa operação, com progresso
  agregado e cancelamento. A matriz já é compilada por `StudyCompiler`; o lote é de execução.
- **Evidence Bundle audit:** pacote verificável de records, refs e digests; não promete todos os
  blobs nem replay.
- **Evidence Bundle portable:** perfil futuro com blobs autorizados e manifest de completude para o
  uso offline declarado.
- **General chat:** sessão do Lab Agent escopada ao Workspace, sem Project ou foco. Pode navegar
  identidades de Projects, mas não recebe acesso implícito ao conteúdo de todos eles.
- **Project chat:** sessão do Lab Agent escopada a exatamente um Project e às regras/preferências do
  Workspace pai. Não lê outro Project nem representa um agente próprio daquele Project.
- **Focused chat:** sessão de Project adicionalmente estreitada a um Study, Run ou Comparison do
  mesmo Project.
- **Context Mount:** inclusão explícita de conhecimento ou sessão anterior.
