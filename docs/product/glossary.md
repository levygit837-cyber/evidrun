---
id: product-glossary
type: contract
title: Glossário canônico
status: accepted
authority: normative
owner: product
created_at: 2026-07-22
updated_at: 2026-07-22
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
- **Scenario:** tarefa e fixtures versionadas que uma run executa.
- **Experiment:** hipótese e plano lógico; cada alteração material cria uma revision.
- **Variant:** configuração comparável derivada de um baseline.
- **Run:** uma execução de uma variant sobre um scenario e repetição.
- **Subject Agent:** sistema sob teste.
- **Lab Agent:** agente do control plane que consulta evidências e cria drafts.
- **Context Policy:** regra de seleção, ordem, truncamento ou transformação.
- **Context Plan:** candidatos e decisões considerados antes da montagem.
- **Context Snapshot:** entrada efetivamente entregue numa invocação.
- **Context Diff:** diferença classificada entre snapshots.
- **Event:** observação append-only da execução.
- **Artifact:** conteúdo referenciado por uma run.
- **Grader:** avaliador versionado que produz um Grade.
- **Comparison:** leitura pareada de runs e seus trade-offs.
- **Evidence Bundle:** pacote portátil com manifest, eventos, grades, relatório e checksums.
- **General chat:** sessão sem escopo de entidade, ainda limitada ao workspace.
- **Context Mount:** inclusão explícita de conhecimento ou sessão anterior.

