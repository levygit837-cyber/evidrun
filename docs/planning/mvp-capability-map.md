---
id: planning-mvp-capability-map
type: planning
title: Mapa temporal de capabilities do MVP
status: accepted
authority: planning
owner: product-engineering
created_at: 2026-07-23
updated_at: 2026-07-24
observed_at: 2026-07-24
review_due: 2026-07-30
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

- `main` observado: `ea0d8f94c40240b32e7cd7c5048fe53c8d4f0764`;
- Runtime Kernel integrado por PR #4 em `ffc513137d343e015cede7f15f14ed5e749db2b4`;
- exploracao visual da Operator Console integrada por PR #6 em
  `b244bfc22ae8c6c83e3ce73842be20d79257e67e`;
- orientacao de agentes integrada por PR #7 em
  `ea0d8f94c40240b32e7cd7c5048fe53c8d4f0764`;
- este snapshot descreve o repositorio, nao uma worktree ativa.

## Legenda

- `verified_main`: implementado em `main` e coberto por testes locais/referencias atuais;
- `partial`: existe uma parte segura, mas o fluxo de produto ainda nao fecha;
- `accepted_only`: ADR/contrato aceito, sem runtime executavel;
- `incubating`: conceito ou research, ainda sem decisao normativa completa.

## Matriz

| Capability | Estado observado | Evidencia e limite |
| --- | --- | --- |
| Revisions, digests, StudyCompiler e Admission | `verified_main` | Contratos fechados, persistencia e testes existem; compiler continua resolvendo somente revisions aceitas. |
| Ledger, lifecycle e Bundle v2 auditavel | `verified_main` | Hash chain, phase gates e verificacao cruzada existem; Bundle v2 nao e portatil nem replayable. |
| Autoridade humana opt-in | `verified_main` | `main` possui challenge, autenticador local, verifier, revogacao, API/CLI e testes; autenticador de plataforma, recovery e rotacao continuam abertos. |
| Uso sem autenticacao em sandbox | `partial` | `AuthorityPolicy` libera acoes rotineiras, mas revisions draft/proposed ainda nao compilam para uma Run; nao existe um caminho canonico de Sandbox Run. |
| Runtime Kernel duravel | `verified_main` | Fila, job, attempt, lease, heartbeat, fencing, worker, retry, SubjectEnvelope persistido e Bundle v3 foram integrados pela PR #4; Bundle v3 continua `references_only`, nao portatil e nao replayable. |
| Subject com modelo real | `verified_main` | Adapter Responses, provider default e benchmark live opt-in foram integrados; execucao ordinaria e testes deterministas nao dependem do provider live. |
| Tool minima de leitura | `verified_main` | A read tool e confinada ao `SubjectEnvelope`, com tracing e evaluator de citation; isso nao equivale a runtime generico de tools. |
| Artifact Store CAS/cifrado | `partial` | CAS e AES-GCM existem; grants, materialization records, leitura por audiencia, TTL e enforcement ponta a ponta ainda nao. |
| EvaluationPlan generico | `accepted_only` | O runtime principal suporta somente um corredor deterministico; model judge, varios stages e orquestracao humana geral nao existem. |
| Checkpoint coordinator | `accepted_only` | Policy e record sao tipados/persistiveis; triggers e validators automaticos continuam reservados. |
| Progress Artifact observer | `accepted_only` | Policy/content/record e eventos possuem schema; scheduler, observer, persistencia atomica e geracao nao existem. |
| Disclosure de eval ao Subject | `partial` | `pre_run` e compilavel por allowlist; todo modo diferente de `none` bloqueia a admissao do runtime em `main`. |
| Bounded exploration | `accepted_only` | Terminal discriminado e ADR 0013 existem; stop coordinator e runtime permanecem indisponiveis. |
| Lab Agent | `incubating` | Chat storage e conceitos existem; nao ha agent runtime que crie drafts, consulte evidence ou produza requests de aprovacao. |
| Human review/adjudication | `partial` | Contratos, authority subject e persistencia existem; fila, UI, trigger e conclusao do EvaluationPlan nao fecham o fluxo. |
| Tools/skills genericas | `accepted_only` | Inventario e eventos sao representaveis; fora da read tool da worktree, coordinators continuam ausentes. |
| Interaction graph/nested agents | `accepted_only` | Contratos sao tipaveis e a admissao rejeita honestamente. |
| Portable bundle/replay/fork | `accepted_only` | Audit bundles existem; blobs, grants, restore e lineage executavel nao. |
| Console Web de operacao | `partial` | A UI de produto ainda mostra o demo CRL-CTX-002. Cinco prototipos React independentes exploram Lab, Projects, Study e Runs, mas nao sao `apps/web`, nao usam backend real e nao promovem capabilities. |
| Canvas | `incubating` | Conceitos existem; nao e requisito do MVP operacional. |

## Integracoes encerradas neste snapshot

Os conflitos de ADR, migrations, composition root, contracts gerados e testes conjuntos entre
authority e Runtime Kernel foram resolvidos na PR #4. ADR 0014 descreve o Kernel, ADR 0015 preserva
a authority e ADR 0016 descreve Subject real, read tool e tracing. Novos workstreams devem partir da
cadeia integrada em `main`, sem repetir o plano de rebase historico da WS-00.

## Lacuna de produto mais importante

O sistema ja distingue autoridade humana de automacao, mas ainda nao possui um fluxo pratico em que
um usuario possa experimentar um draft sem declarar falsa aceitacao humana. Antes do MVP, deve
existir uma decisao sucessora e um caminho tecnico para uma Run explicitamente
`unverified_sandbox`, com efeitos externos negados e sem promocao automatica para evidencia
verificada.

## Claims proibidos neste snapshot

- chamar prototipos de design de Console operacional conectada;
- afirmar que todo `ArtifactRef` possui grant;
- chamar o autenticador local de passkey de plataforma;
- afirmar que o frontend cria Studies completos;
- tratar read tool como runtime generico de tools;
- chamar Bundle v3 de portatil ou replayable;
- afirmar que Progress Artifacts ou checkpoints sao gerados automaticamente.
