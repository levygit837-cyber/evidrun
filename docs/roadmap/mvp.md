---
id: roadmap-mvp
type: roadmap
title: Roadmap do MVP
status: accepted
authority: planning
volatility: snapshot
owner: product
created_at: 2026-07-22
updated_at: 2026-07-28
applies_to: product
sources:
  - docs/adr/0020-workspace-project-run-environment-boundaries.md
  - docs/adr/0021-hierarchical-lab-agent-scope.md
  - docs/adr/0022-explicit-execution-trust-without-per-run-authentication.md
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
- contratos fechados para Study, Goal, Scenario, Agent Inventory, Run Environment
  (`WorkspaceTemplateRevision` no schema v1), Interaction,
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
- superfície pública de Workspace/Project por API e CLI, com nomes canônicos, `ScopeError`,
  constraints, migrations fail-closed e corredor até a primeira contract revision;
- executor de Runs supervisionado pelo Electron Main, separado da API, com estado observavel,
  restart, shutdown e smoke no CI;
- decisao normativa de trust para Run explicitamente nao verificada sem autenticacao por execucao,
  ainda sem implementacao de runtime;

## Proximo

O corte imediato e o [Minimo Confortavel](../planning/comfortable-minimum.md). Dele saem os itens
abaixo, nesta ordem de destrave:

- implementacao do `ExecutionTrustRecord`, selamento transitivo e caminho de compilacao/admissao nao
  verificado do WS-40; criar Workspace/Project nao materializa Run Environment;
- runtime de um unico Lab Agent copiloto conforme os ADRs 0018/0021, com sessoes escopadas,
  `LabAgentEnvelope`, loop de tools e proposta de draft sem decisao;
- contrato de contexto e criterios do Subject, para que duas variants irmas difiram de forma tipada
  na variavel primaria recebendo material identico por digest;
- batch de execucao com retry/backoff e rate limiting de provider, mais metricas minimas por Run
  (tokens, tool calls, duracao, terminal cause) e agregadas por variant (taxa de sucesso, `pass@k`,
  `pass^k`), como read model derivado do ledger. Custo entra como projecao; `max_cost` continua
  rejeitando a admissao;
- memoria operacional do Lab Agent conforme o ADR 0021: `MemoryEntry` com hard boundary de Workspace
  e Project opcional, descoberta por cue em dois estagios, consolidador em background e promocao
  humana de candidatos. Adjacente ao
  corredor: melhora drafts, mas o Minimo Confortavel fecha sem ela.

Depois do Minimo Confortavel:

- enforcement ponta a ponta de classification e capture policy em snapshots e eventos;
- autenticacao local opcional com cerimonia mais simples sobre o `ReviewPackage`, incluindo
  enrollment, recovery e rotacao; passkey de plataforma permanece opcional e exige decisao propria;
- pipeline executável de `human_review` e adjudicação required, preservando suas relações distintas;
- Artifact Access Grants e records de materialização;
- observer, scheduler, persistência e geração em background de Progress Artifact;
- entrega de guidance `pre_run` ao runner e interações auditadas para `on_request`/`post_run`;
- runtime de `bounded_exploration` conforme a taxonomia do ADR 0013, sem pass/fail;
- multi-turn admitido com coordinator de turnos e budget aplicado;
- approvals e resume;
- tool simulator e adapter de sandbox que prove o Run Environment efetivo na admissao;
- runtime real de tools, skills e nested agents;
- execução de protocolos em grafo;
- executor genérico de `EvaluationPlan`, incluindo triggers e todos os stages;
- runtime de triggers e validators de `CheckpointPolicy`;
- restore, replay, context extraction e fork por checkpoint;
- export `portable` separado do Bundle v2 auditável;
- significancia estatistica formal, deteccao de saturacao e estatistica em escala;
- LLM judges calibrados;
- PyInstaller, assinatura e notarização;
- analytics DuckDB/Parquet;
- sync opcional somente após ADR específico.

Roadmap não é comportamento existente. Cada item muda para implemented apenas com referências.
