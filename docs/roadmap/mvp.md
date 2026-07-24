---
id: roadmap-mvp
type: roadmap
title: Roadmap do MVP
status: accepted
authority: planning
owner: product
created_at: 2026-07-22
updated_at: 2026-07-23
applies_to: product
sources: []
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
---

# Roadmap do MVP

## Implementado nesta iniciação

- fundação documental e ADRs;
- manifest, context policy, deterministic runner e grader;
- SQLite/WAL, hash chain e evidence bundle;
- API, CLI, React e Electron dev shell;
- captura sensível criptografada como adapter;
- benchmark CRL-CTX-002 e testes.
- contratos fechados para Study, Goal, Scenario, Agent Inventory, Workspace, Interaction,
  EvaluationPlan e CheckpointPolicy;
- compilação determinística de variants/repetitions, RunSpec, SubjectEnvelope e admissão;
- persistência aditiva de revisions, decisões, specs, admissions, evaluations e checkpoints;
- payloads tipados do Run Event v1, Evidence Bundle v2, API/CLI local e DTOs TypeScript gerados;
- adapter do Experiment Manifest v1 e demo CRL-CTX-002 executado pelo pipeline Study;
- authority tipada por `HumanAttestationRecord`, verifier fail-closed e separação entre review,
  adjudicação e repository fixture não humano;
- schemas de Progress Artifact e seus eventos, com admissão fechada enquanto o observer não existe;
- disclosure `pre_run` compilável por allowlist, com admissão ativa restrita a `none`;
- payload terminal discriminado por Goal mode, ainda sem runtime de bounded exploration;
- Bundle v2 explicitamente `audit`/`references_only`, não portátil e não replayable, com artifact
  manifest de refs intencionais;
- ledger com phase gates, cross-links factuais e cobertura do EvaluationPlan no terminal completed;
- Bundle v2 verificando lifecycle, contratos queued/terminal, comparison, evaluations e completude do
  artifact manifest.
- authority humana local opt-in com subject assinado, challenge de uso unico, autenticador de
  software, revogacao, verifier e API/CLI; o default continua fail-closed quando a feature esta
  desabilitada.

## Em execucao fora de `main`

A worktree `task/implementar-runtime-kernel-genrico` implementa queue duravel, job/attempt,
lease/heartbeat/fencing, worker, SubjectEnvelope persistido, API/CLI de execucao, Bundle v3 e um
primeiro Subject real com read tool fechada. Esse trabalho permanece temporalmente
`implemented_in_worktree`: ainda precisa ser congelado, rebaseado sobre a authority ja mesclada,
revisado, validado e integrado antes de ser descrito como comportamento de `main`.

O brief de integracao esta em
[WS-00](../planning/tasks/00-runtime-kernel-integration.md).

## Proximas ondas

1. integrar o Runtime Kernel e o Subject real sem perder authority;
2. construir a Console Web do MVP em paralelo, inicialmente por ports e fixtures honestas;
3. implementar Artifact Access Grants, materializacao e capture/classification ponta a ponta;
4. tornar EvaluationPlan, CheckpointPolicy e Progress Artifact executaveis;
5. criar trust mode `unverified_sandbox` e ReviewPackage sem falsa autoridade humana;
6. implementar Lab Agent limitado a drafts e runtime de `bounded_exploration`;
7. integrar frontend, sidecar e worker em dossiers end-to-end do MVP.

Depois do MVP entram generic tools/skills, approvals/resume, graph/nested agents, portable bundle,
restore/replay/fork, Canvas, analytics, packaging e sync.

O detalhamento, dependencias e gates estao em
[Roadmap executavel do MVP](../planning/mvp-implementation-roadmap.md).

Roadmap não é comportamento existente. Cada item muda para implemented apenas com referências.
