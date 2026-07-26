---
id: planning-mvp-capability-map
type: planning
title: Mapa temporal de capabilities do MVP
status: accepted
authority: planning
owner: product-engineering
created_at: 2026-07-23
updated_at: 2026-07-26
observed_at: 2026-07-24
review_due: 2026-08-07
applies_to: mvp-capabilities
sources:
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
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
---

# Mapa temporal de capabilities

Este documento separa o que esta verificado em `main` do que continua apenas parcial, aceito ou em
incubacao. Ele nao promove nenhuma capability.

## Snapshot auditado

- observado em 2026-07-24 sobre `main` no commit `eec0caa`;
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
| Criacao de Workspace/Project | `partial` | Os metodos existem no `Repository` e sao exercitados indiretamente, mas nao ha rota `POST` nem comando CLI. Banco novo tem zero projects; registrar contract sem project falha com erro de integridade cru. Endereçado por WS-01. |
| Execucao de Runs no app instalado | `partial` | O desktop faz spawn apenas da API; nada inicia o worker. Runs enfileiradas pela UI nao sao processadas. Endereçado por WS-02. |
| Autoria usavel no produto instalado | `partial` | Com `EVIDRUN_AUTHORITY=1` o caminho verificado funciona ponta a ponta por CLI e API. No default o unico corredor de aceitacao e o `repository_fixture` nao humano do import legado. Endereçado por WS-03. |
| Artifact Store CAS/cifrado | `partial` | CAS e AES-GCM existem e sao testados; grants, materialization records, leitura por audiencia, TTL efetivo e enforcement ponta a ponta nao. |
| EvaluationPlan generico | `accepted_only` | A admissao rejeita planos com mais de um stage; model judge e orquestracao humana geral nao existem. |
| Checkpoint coordinator | `accepted_only` | Policy e record sao tipados e a persistencia isolada e testada; triggers e validators automaticos continuam reservados e a admissao rejeita `checkpoint_policy`. |
| Progress Artifact observer | `accepted_only` | Policy/content/record possuem schema; scheduler, observer e persistencia nao existem e a admissao rejeita a policy. |
| Disclosure de eval ao Subject | `partial` | `pre_run` e compilavel por allowlist; todo modo diferente de `none` rejeita a admissao. |
| Bounded exploration | `accepted_only` | Terminal discriminado e ADR 0013 existem; stop coordinator e runtime permanecem indisponiveis. |
| Trust modes e Sandbox Run | `accepted_only` | `AuthorityMode.SANDBOX` existe como rotulo de politica de autonomia, sem qualquer ligacao com RunSpec, AdmissionRecord ou Run. Nao existe `ExecutionTrustRecord` nem `ReviewPackage`. |
| Lab Agent | `incubating` | Chat storage e conceitos existem; nao ha porta, adapter nem consumidor. O `LabAgentPort` e o pacote `lab_agent`, ambos sem implementacao, foram removidos na #18. Os endpoints de chat nao possuem teste. |
| Human review/adjudication | `partial` | Contratos, authority subject e persistencia existem; o branch humano de `save_evaluation_record` nao e exercitado por teste, e fila, UI e conclusao do EvaluationPlan nao fecham o fluxo. |
| Tools/skills genericas | `accepted_only` | Inventario e eventos sao representaveis; fora da read tool, coordinators continuam ausentes e os event types permanecem reservados no ledger. |
| Interaction graph/nested agents | `accepted_only` | Contratos sao tipaveis e a admissao rejeita honestamente. |
| Portable bundle/replay/fork | `accepted_only` | Audit bundles existem; blobs, grants, restore e lineage executavel nao. |
| Console desktop de operacao | `partial` | Shell multipagina existe em `main`. Observability consome endpoints reais e tem testes. Create e rascunho local cujo botao final executa a fixture `CRL-CTX-002`, ignorando os campos digitados. Laboratory e mock; o adapter de producao apenas emite `integration_pending`. |
| Contratos tipados de HTTP no frontend | `partial` | O pipeline Pydantic -> JSON Schema -> TypeScript existe e e verificado no CI, mas cobre o catalogo de dominio. Os DTOs de resposta consumidos pelas paginas sao escritos a mao, fora do gate de drift. |
| Canvas | `incubating` | Conceitos existem; nao e requisito do MVP operacional. |

## Lacuna de produto mais importante

O sistema distingue autoridade humana de automacao e executa uma Run auditavel de ponta a ponta. O
que falta e um caminho pratico para um usuario do app instalado criar um Study proprio: hoje isso
exige criar project por dentro do dominio, ligar uma variavel de ambiente e rodar o worker a mao.
Antes do MVP e preciso uma decisao sucessora sobre autoria default e um caminho tecnico para uma Run
explicitamente `unverified_sandbox`, com efeitos externos negados e sem promocao automatica para
evidencia verificada.

## Claims proibidos neste snapshot

- afirmar que o draft local da pagina Create alimenta autoria canonica;
- afirmar que o app instalado processa Runs sem worker iniciado a parte;
- afirmar que autoria verificada esta ativa por padrao;
- afirmar que todo `ArtifactRef` possui grant;
- chamar o autenticador local de passkey de plataforma;
- tratar read tool como runtime generico de tools;
- chamar Bundle v2/v3 de portatil ou replayable;
- afirmar que Progress Artifacts ou checkpoints sao gerados automaticamente;
- descrever `AuthorityMode.SANDBOX` como Sandbox Run implementada.
