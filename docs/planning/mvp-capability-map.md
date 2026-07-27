---
id: planning-mvp-capability-map
type: planning
title: Mapa temporal de capabilities do MVP
status: accepted
authority: planning
volatility: snapshot
owner: product-engineering
created_at: 2026-07-23
updated_at: 2026-07-27
observed_at: 2026-07-27
review_due: 2026-08-23
applies_to: mvp-capabilities
sources:
  - docs/adr/0018-lab-agent-copilot-scope.md
  - docs/planning/comfortable-minimum.md
  - docs/roadmap/mvp.md
  - docs/architecture/system.md
  - docs/architecture/agents-and-authority.md
  - docs/architecture/data-and-evidence.md
  - docs/adr/0010-verifiable-human-authority.md
  - docs/adr/0011-progress-artifacts-and-bundle-boundaries.md
  - docs/adr/0013-bounded-exploration-terminal-semantics.md
  - docs/adr/0014-durable-runtime-kernel.md
  - docs/adr/0015-human-subject-envelope-and-authenticator-lifecycle.md
  - docs/adr/0016-real-subject-read-tool-and-tracing.md
  - docs/adr/0020-workspace-project-run-environment-boundaries.md
  - docs/adr/0021-hierarchical-lab-agent-scope.md
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
---

# Mapa temporal de capabilities

Este documento separa o que esta verificado em `main` do que continua apenas parcial, aceito ou em
incubacao. Ele nao promove nenhuma capability.

## Snapshot auditado

- escopos afetados por esta revisao rechecados em 2026-07-27 sobre `main` no commit `b591f4c`;
- este snapshot descreve o repositorio, nao uma worktree ativa.

## Legenda

- `verified_main`: implementado em `main` e coberto por testes locais/referencias atuais;
- `partial`: existe uma parte segura, mas o fluxo de produto ainda nao fecha;
- `accepted_only`: ADR/contrato aceito, sem runtime executavel;
- `incubating`: conceito ou research, ainda sem decisao normativa completa.

## Espinha canonica

O corredor completo foi exercitado por superficies publicas em 2026-07-24:
`contract register` -> `authority accept` -> `study compile` -> `run admit` -> `run enqueue` ->
`worker --once` -> `run.completed` -> `bundle export-run` -> `bundle verify`. O ledger emitiu a
sequencia integral de eventos e o Bundle v3 verificou todos os grupos de records.

A limitacao nao esta na espinha, e sim no acesso a ela e na largura do que ela aceita.

## Matriz

| Capability | Estado observado | Evidencia e limite |
| --- | --- | --- |
| Revisions, digests, StudyCompiler e Admission | `verified_main` | Contratos fechados, persistencia e testes existem; compiler resolve somente revisions aceitas. |
| Ledger, lifecycle e Bundle v2/v3 auditavel | `verified_main` | Hash chain, phase gates e verificacao cruzada existem; bundles nao sao portateis nem replayable. |
| Autoridade humana opt-in | `verified_main` | Challenge, autenticador local, verifier, revogacao, API/CLI e testes existem. Desligada por padrao (`EVIDRUN_AUTHORITY`); autenticador de plataforma, recovery e rotacao continuam abertos. |
| Runtime Kernel duravel | `verified_main` | Fila, job, attempt, lease, heartbeat, fencing, worker, retry e SubjectEnvelope persistido existem e sao testados por subprocess real. |
| Subject com modelo real | `verified_main` | Adapter Responses com tool loop e provider default integrados; execucao ordinaria e testes deterministas nao dependem do provider live. |
| Tool minima de leitura | `verified_main` | A read tool e confinada ao `SubjectEnvelope`, com tracing por eventos e evaluator de citation; nao equivale a runtime generico de tools. |
| Criacao de Workspace/Project | `verified_main` | API e CLI criam/listam os mesmos documentos; nomes usam NFKC/whitespace/casefold, constraints e migrations `0005`/`0006`. Race, storage seguro, legado/colisao e corredor ate `contract register` possuem testes. Nao cria Run Environment, authority ou Lab Agent. |
| Run Environment | `partial` | `WorkspaceTemplateRevision`/`RunSpec.workspace` tipam configuracao e a admissao suporta somente o perfil estreito `in_process`. Nao existe sandbox forte, policy ceiling de Workspace, provisioning de filesystem, writes, secrets ou snapshot; unsupported rejeita. ADR 0020 separa o conceito do Workspace duravel. |
| Execucao de Runs no app instalado | `partial` | O desktop faz spawn apenas da API; nada inicia o worker. Runs enfileiradas pela UI nao sao processadas. Endereçado por WS-02. |
| Autoria usavel no produto instalado | `partial` | Com `EVIDRUN_AUTHORITY=1` o caminho verificado funciona ponta a ponta por CLI e API. No default o unico corredor de aceitacao e o `repository_fixture` nao humano do import legado. Endereçado por WS-03. |
| Artifact Store CAS/cifrado | `partial` | CAS e AES-GCM existem e sao testados; grants, materialization records, leitura por audiencia, TTL efetivo e enforcement ponta a ponta nao. |
| EvaluationPlan generico | `accepted_only` | A admissao rejeita planos com mais de um stage; model judge e orquestracao humana geral nao existem. |
| Checkpoint coordinator | `accepted_only` | Policy e record sao tipados e a persistencia isolada e testada; triggers e validators automaticos continuam reservados e a admissao rejeita `checkpoint_policy`. |
| Progress Artifact observer | `accepted_only` | Policy/content/record possuem schema; scheduler, observer e persistencia nao existem e a admissao rejeita a policy. |
| Disclosure de eval ao Subject | `partial` | `pre_run` e compilavel por allowlist; todo modo diferente de `none` rejeita a admissao. |
| Bounded exploration | `accepted_only` | Terminal discriminado e ADR 0013 existem; stop coordinator e runtime permanecem indisponiveis. |
| Trust de execucao nao verificada | `accepted_only` | `AuthorityMode.SANDBOX` e apenas rotulo legado de policy, sem ligacao com RunSpec, AdmissionRecord ou Run. Trust e Run Environment sao eixos separados; nao existe `ExecutionTrustRecord` nem `ReviewPackage`. |
| Lab Agent copiloto | `accepted_only` | ADRs 0018/0021 e contrato de scope v1 fixam um unico copiloto, sessoes Workspace/Project/Focused e zero authority. Chat storage generico existe; nao ha porta, adapter, scope enforcement ou consumidor, e endpoints nao possuem teste. Enderecado por WS-04. |
| Memoria operacional do Lab Agent | `accepted_only` | ADR 0021 e `MemoryEntry` v2 fixam hard boundary de Workspace e subescopo opcional de Project; nao existe tabela, indice FTS5, tool, consolidador nem superficie de promocao. Enderecado por WS-07. |
| Human review/adjudication | `partial` | Contratos, authority subject e persistencia existem; o branch humano de `save_evaluation_record` nao e exercitado por teste, e fila, UI e conclusao do EvaluationPlan nao fecham o fluxo. |
| Tools/skills genericas | `accepted_only` | Inventario e eventos sao representaveis; fora da read tool, coordinators continuam ausentes e os event types permanecem reservados no ledger. |
| Interaction graph/nested agents | `accepted_only` | Contratos sao tipaveis e a admissao rejeita honestamente. |
| Portable bundle/replay/fork | `accepted_only` | Audit bundles existem; blobs, grants, restore e lineage executavel nao. |
| Console desktop de operacao | `partial` | Shell multipagina existe em `main` e as tres paginas foram fatiadas por WS-13. Observability consome endpoints reais. Create ainda executa a fixture e Laboratory e mock; nao existem Workspace switcher, Project Room ou sessoes escopadas integradas. WS-51 documenta a integracao futura sem promove-la. |
| Contratos tipados de HTTP no frontend | `partial` | O pipeline Pydantic -> JSON Schema -> TypeScript existe e e verificado no CI, mas cobre o catalogo de dominio. Os DTOs de resposta consumidos pelas paginas sao escritos a mao, fora do gate de drift. |
| Canvas | `incubating` | Conceitos existem; nao e requisito do MVP operacional. |

## Lacuna de produto mais importante

O sistema distingue autoridade humana de automacao e executa uma Run auditavel de ponta a ponta. O
que falta e um caminho pratico para um usuario do app instalado criar um Study proprio: hoje isso
exige criar project por dentro do dominio, ligar uma variavel de ambiente e rodar o worker a mao.
Antes do MVP e preciso uma decisao sucessora sobre autoria default e um caminho tecnico para uma Run
explicitamente nao verificada, com efeitos externos negados e sem promocao automatica para
evidencia verificada.

A segunda lacuna, agora nomeada, e o Lab Agent: pelo ADR 0018 ele e a superficie primaria de trabalho
do produto, e nao existe em `src/evidrun/`. O corte que fecha ambas esta em
[Minimo Confortavel](comfortable-minimum.md).

## Claims proibidos neste snapshot

- afirmar que o draft local da pagina Create alimenta autoria canonica;
- afirmar que o app instalado processa Runs sem worker iniciado a parte;
- afirmar que autoria verificada esta ativa por padrao;
- afirmar que todo `ArtifactRef` possui grant;
- chamar o autenticador local de passkey de plataforma;
- tratar read tool como runtime generico de tools;
- chamar Bundle v2/v3 de portatil ou replayable;
- afirmar que Progress Artifacts ou checkpoints sao gerados automaticamente;
- descrever `AuthorityMode.SANDBOX` como trust de Run ou sandbox implementado;
- descrever `in_process` como sandbox seguro ou afirmar policy ceiling de Workspace implementada;
- descrever o Lab Agent como existente, ou a pagina Laboratory como integrada;
- apresentar `pass@k`, `pass^k` ou agregacao entre repeticoes como disponiveis;
- apresentar custo de execucao como budget aplicado: `max_cost` rejeita a admissao;
- afirmar que o provider possui retry, backoff ou rate limiting;
- descrever memoria operacional como existente, ou tratar `MemoryEntry` como evidencia de Run;
- afirmar que General chat pode ler todos os Projects ou que cada Project possui agente proprio;
- afirmar que memoria melhora a qualidade dos drafts antes de um Study que meca isso.
