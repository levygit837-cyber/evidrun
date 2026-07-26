---
id: product-glossary
type: contract
title: Glossário canônico
status: accepted
authority: normative
volatility: timeless
owner: product
created_at: 2026-07-22
updated_at: 2026-07-23
applies_to: domain
sources: []
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun
verification_refs: []
---

# Glossário

- **Workspace:** fronteira local de dados e futura sincronização.
- **Project:** conjunto de cenários, experimentos e conversas relacionados.
- **Study:** raiz de autoria para uma pergunta, hipótese, avaliação, diagnóstico ou exploração; pode
  compilar uma Run ou uma matriz de Runs.
- **StudyIntent:** propósito e perguntas do laboratório; não é instrução automática do Subject.
- **Goal:** objetivo e limites entregues ao Subject; permanece separado da avaliação.
- **Scenario:** inputs, condições observáveis, limitações e provenance versionados para uma Run.
- **Experiment Manifest v1:** contrato legado compatível, importável para um Study.
- **Variant:** override tipado sobre um blueprint; variants pré-Run são irmãs.
- **RunSpec:** configuração atômica, imutável e compilada de scenario, variant e repetição.
- **AdmissionRecord:** decisão pré-fila com inventário, workspace e capabilities efetivamente
  resolvidos.
- **Run:** tentativa ligada a RunSpec e AdmissionRecord exatos.
- **SubjectEnvelope:** visão mínima compilada para o Subject, sem dados do laboratório ou grader
  oculto.
- **Subject Evaluation Guidance:** disclosure público mínimo materializado antes da Run; não é o
  EvaluationPlan completo.
- **Subject Agent:** sistema sob teste.
- **Lab Agent:** agente do control plane que consulta evidências e cria drafts.
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
- **Checkpoint:** marco validado e ancorado no ledger; não significa restore ou replay.
- **Bounded exploration result:** resultado em dois eixos: disposition operacional e stop reason
  factual; nenhum deles é pass/fail ou score.
- **Grader:** avaliador versionado que produz EvaluationRecord; Grade é projeção legada.
- **Comparison:** leitura pareada de runs e seus trade-offs.
- **Evidence Bundle audit:** pacote verificável de records, refs e digests; não promete todos os
  blobs nem replay.
- **Evidence Bundle portable:** perfil futuro com blobs autorizados e manifest de completude para o
  uso offline declarado.
- **General chat:** sessão sem escopo de entidade, ainda limitada ao workspace.
- **Context Mount:** inclusão explícita de conhecimento ou sessão anterior.
