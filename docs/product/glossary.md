---
id: product-glossary
type: contract
title: Glossário canônico
status: accepted
authority: normative
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
- **Subject Agent:** sistema sob teste.
- **Lab Agent:** agente do control plane que consulta evidências e cria drafts.
- **Agent Inventory:** requisitos de runner, provider, tools, skills e runtime de uma Run.
- **Resolved Agent Inventory:** snapshot hasheado do que a admissão realmente resolveu.
- **Context Policy:** regra de seleção, ordem, truncamento ou transformação.
- **Context Plan:** candidatos e decisões considerados antes da montagem.
- **Context Snapshot:** entrada efetivamente entregue numa invocação.
- **Context Diff:** diferença classificada entre snapshots.
- **Event:** observação append-only da execução.
- **Artifact:** conteúdo referenciado por uma run.
- **EvaluationPlan:** dimensões, stages, gates, disclosure, blinding e agregação opcional.
- **EvaluationRecord:** resultado vetorial e ancorado produzido por grader, judge ou humano.
- **Checkpoint:** marco validado e ancorado no ledger; não significa restore ou replay.
- **Grader:** avaliador versionado que produz EvaluationRecord; Grade é projeção legada.
- **Comparison:** leitura pareada de runs e seus trade-offs.
- **Evidence Bundle:** pacote portátil verificável; v2 acrescenta revisions, specs, admissions,
  checkpoints e evaluations.
- **General chat:** sessão sem escopo de entidade, ainda limitada ao workspace.
- **Context Mount:** inclusão explícita de conhecimento ou sessão anterior.
