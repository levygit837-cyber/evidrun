---
id: docs-index
type: architecture
title: Índice da documentação Evidrun
status: implemented
authority: normative
owner: core
created_at: 2026-07-22
updated_at: 2026-07-23
applies_to: repository
sources: []
supersedes: []
superseded_by: null
implementation_refs:
  - scripts/validate_docs.py
verification_refs:
  - docs/_generated/manifest.json
---

# Documentação Evidrun

## Leitura inicial

1. [Charter](product/charter.md)
2. [Glossário](product/glossary.md)
3. [Arquitetura do sistema](architecture/system.md)
4. [Agentes e autoridade](architecture/agents-and-authority.md)
5. [Dados e evidência](architecture/data-and-evidence.md)
6. [Protocolo de benchmarks](benchmarks/protocol.md)
7. [Runtime de providers](architecture/provider-runtime.md)
8. [Roadmap](roadmap/mvp.md)

## Contratos de execução

- [Study, revisions e Run canônica v1](contracts/study-run-v1.md)
- [Inventário de agente, admissão e workspace v1](contracts/agent-inventory-workspace-v1.md)
- [Evaluation e checkpoint records v1](contracts/evaluation-checkpoint-v1.md)
- [Run Event v1](contracts/run-event.md) e seu
  [catálogo de payloads](contracts/run-event-payloads-v1.md)
- [Evidence Bundle v1](contracts/evidence-bundle.md) e
  [Evidence Bundle v2](contracts/evidence-bundle-v2.md)
- [Experiment Manifest v1](contracts/experiment-manifest.md), mantido por compatibilidade

## Autoridade

Contratos e ADRs aceitos são normativos. Arquitetura descreve o estado atual. Research é temporal.
Roadmap é intenção futura. Relatórios são projeções geradas de evidência e não são mantidos à mão.

O manifest completo é gerado em `_generated/manifest.json` a partir do frontmatter dos documentos.

## Ideias em incubação

Os documentos abaixo preservam brainstorming do produto. Eles não são contratos, decisões aceitas
nem promessa de implementação. Partes deles só se tornam normativas quando promovidas para ADRs ou
contracts revisados e aceitos.

- [Runs, contratos e checkpoints](product/run-laboratory-concept.md)
- [Canvas vivo e grafo de execução](product/live-run-graph-concept.md)
- [Matriz de contexto e grafo semântico da execução](product/semantic-execution-graph-concept.md)
- [Discovery orientado por cenários de Run](research/run-scenario-discovery/comparison.md)
