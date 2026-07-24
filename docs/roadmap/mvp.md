---
id: roadmap-mvp
type: roadmap
title: Roadmap do MVP
status: accepted
authority: planning
owner: product
created_at: 2026-07-22
updated_at: 2026-07-24
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
- Runtime Kernel duravel com queue, job, attempts, lease, heartbeat, fencing, worker e retry;
- persistencia do SubjectEnvelope exato e Bundle v3 por Run, ainda `references_only`, nao portatil e
  nao replayable;
- Subject real opt-in, read tool confinada ao envelope e tracing factual;

## Próximo

- enforcement ponta a ponta de classification e capture policy em snapshots e eventos;
- adapter WebAuthn/passkey, cerimônia humana, enrollment/recovery e canal UI/CLI para produzir a
  attestation já contratada;
- pipeline executável de `human_review` e adjudicação required, preservando suas relações distintas;
- Artifact Access Grants e records de materialização;
- observer, scheduler, persistência e geração em background de Progress Artifact;
- entrega de guidance `pre_run` ao runner e interações auditadas para `on_request`/`post_run`;
- runtime de `bounded_exploration` conforme a taxonomia do ADR 0013, sem pass/fail;
- Lab Agent com Pydantic AI;
- approvals e resume;
- tool simulator e sandbox;
- runtime real de tools, skills e nested agents;
- execução de protocolos em grafo;
- executor genérico de `EvaluationPlan`, incluindo triggers e todos os stages;
- runtime de triggers e validators de `CheckpointPolicy`;
- restore, replay, context extraction e fork por checkpoint;
- export `portable` separado do Bundle v2 auditável;
- repetições e análise estatística;
- LLM judges calibrados;
- PyInstaller, assinatura e notarização;
- analytics DuckDB/Parquet;
- sync opcional somente após ADR específico.

Roadmap não é comportamento existente. Cada item muda para implemented apenas com referências.
