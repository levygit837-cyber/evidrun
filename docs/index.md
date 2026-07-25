---
id: docs-index
type: architecture
title: Índice da documentação Evidrun
status: implemented
authority: normative
owner: core
created_at: 2026-07-22
updated_at: 2026-07-24
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
4. [Layout da codebase, costuras e orçamento estrutural](architecture/codebase-layout.md)
5. [Agentes e autoridade](architecture/agents-and-authority.md)
6. [Dados e evidência](architecture/data-and-evidence.md)
7. [Protocolo de benchmarks](benchmarks/protocol.md)
8. [Runtime de providers](architecture/provider-runtime.md)
9. [Roadmap](roadmap/mvp.md)
10. [Planejamento temporal de implementacao](planning/README.md)

O primeiro benchmark com Subject real está em
[recuperação fundamentada por tool](benchmarks/live-read-agent.md).

## Contratos de execução

- [Study, revisions e Run canônica v1](contracts/study-run-v1.md)
- [Inventário de agente, admissão e workspace v1](contracts/agent-inventory-workspace-v1.md)
- [Evaluation e checkpoint records v1](contracts/evaluation-checkpoint-v1.md)
- [Run Event v1](contracts/run-event.md) e seu
  [catálogo de payloads](contracts/run-event-payloads-v1.md)
- [Evidence Bundle v1](contracts/evidence-bundle.md) e
  [Evidence Bundle v2](contracts/evidence-bundle-v2.md), além do
  [Evidence Bundle v3 por Run](contracts/evidence-bundle-v3.md)
- [Experiment Manifest v1](contracts/experiment-manifest.md), mantido por compatibilidade

## Operação do Runtime Kernel

- [Execução durável de Runs](operations/runtime-worker.md)

## Planejamento executavel

- [Mapa temporal de capabilities](planning/mvp-capability-map.md)
- [Roadmap executavel do MVP](planning/mvp-implementation-roadmap.md)
- [Dispatch e estado dos workstreams](planning/tasks/README.md)

Planejamento registra intencao, dependencias e estado temporal. Ele nao substitui contratos, ADRs
ou evidencia de comportamento implementado.

## Decisões sucessoras

- [ADR 0010 — autoridade humana verificável e adjudicação](adr/0010-verifiable-human-authority.md)
- [ADR 0011 — Progress Artifacts, acesso e bundles](adr/0011-progress-artifacts-and-bundle-boundaries.md)
- [ADR 0012 — Subject disclosure e semântica terminal (histórico)](adr/0012-subject-disclosure-and-terminal-semantics.md)
- [ADR 0013 — bounded exploration em dois eixos](adr/0013-bounded-exploration-terminal-semantics.md)
- [ADR 0014 — Runtime Kernel durável](adr/0014-durable-runtime-kernel.md)
- [ADR 0015 — HumanSubjectEnvelope, autenticador local e ciclo de vida de credencial](adr/0015-human-subject-envelope-and-authenticator-lifecycle.md)
- [ADR 0016 — Subject real, read tool e tracing](adr/0016-real-subject-read-tool-and-tracing.md)
- [ADR 0017 — orçamento estrutural e costuras nomeadas](adr/0017-structural-budget-and-named-seams.md)

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
