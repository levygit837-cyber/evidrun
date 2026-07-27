---
id: planning-mvp-capability-map
type: planning
title: Mapa temporal de capabilities do MVP
status: accepted
authority: planning
owner: product-engineering
created_at: 2026-07-23
updated_at: 2026-07-23
observed_at: 2026-07-23
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
  - docs/adr/0015-human-subject-envelope-and-authenticator-lifecycle.md
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
---

# Mapa temporal de capabilities

Este documento separa o que esta em `main`, o que existe apenas na worktree ativa e o que continua
somente aceito ou representavel. Ele nao promove nenhuma capability.

## Snapshot auditado

- `main`: `101087964cb2361977085e9f62afd75d1dc58f6d`;
- worktree ativa: `/Users/apple/.codex/worktrees/4073/evidrun`;
- branch ativa do Kernel: `task/implementar-runtime-kernel-genrico`;
- base original dessa branch: `71f5841e0b8123a629bdeaa028ae844a20a628f9`;
- thread Codex observada: `019f8f98-bc6e-7752-ac92-42d9604835f3`;
- a worktree estava com alteracoes nao commitadas e a execucao live ainda estava ativa no momento do
  snapshot.

## Legenda

- `verified_main`: implementado em `main` e coberto por testes locais/referencias atuais;
- `implemented_worktree`: ha codigo e testes na worktree, mas ainda nao houve integracao em `main`;
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
| Runtime Kernel duravel | `implemented_worktree` | Fila, job, attempt, lease, heartbeat, fencing, worker, retry, SubjectEnvelope persistido e Bundle v3 aparecem na worktree; falta freeze, rebase, review, CI e merge. |
| Subject com modelo real | `implemented_worktree` | Adapter Responses, provider default e benchmark live aparecem na worktree; a Run live ainda precisa fechar seu veredito e integrar sem perder authority. |
| Tool minima de leitura | `implemented_worktree` | Tool confinada ao `SubjectEnvelope`, tracing e evaluator de citation aparecem na worktree; isso nao equivale a runtime generico de tools. |
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
| Console Web de operacao | `partial` | A UI atual executa e mostra apenas o demo CRL-CTX-002; nao ha authoring, admission, fila, Run detail generico ou authority UX. |
| Canvas | `incubating` | Conceitos existem; nao e requisito do MVP operacional. |

## Conflitos de integracao ja conhecidos

1. A worktree do Runtime nasceu antes do commit de authority em `main`.
2. As duas linhas criaram um `ADR 0015`; o ADR do Subject real deve ser renumerado depois do rebase.
3. Runtime criou `0002_runtime_kernel`; authority ja usa `0003_human_authority`, mas seu
   `down_revision` ainda aponta para `0001_contract_foundation` e deve ser linearizado.
4. API composition, Settings, Database engine, repository, docs index e artefatos gerados foram
   alterados nas duas linhas e precisam de reconciliacao semantica, nao apenas resolucao textual.
5. O teste de authority e os testes de Runtime precisam passar juntos no mesmo banco migrado.

## Lacuna de produto mais importante

O sistema ja distingue autoridade humana de automacao, mas ainda nao possui um fluxo pratico em que
um usuario possa experimentar um draft sem declarar falsa aceitacao humana. Antes do MVP, deve
existir uma decisao sucessora e um caminho tecnico para uma Run explicitamente
`unverified_sandbox`, com efeitos externos negados e sem promocao automatica para evidencia
verificada.

## Claims proibidos neste snapshot

- chamar a worktree ativa de comportamento de `main`;
- afirmar que todo `ArtifactRef` possui grant;
- chamar o autenticador local de passkey de plataforma;
- afirmar que o frontend cria Studies completos;
- tratar read tool como runtime generico de tools;
- chamar Bundle v3 de portatil ou replayable;
- afirmar que Progress Artifacts ou checkpoints sao gerados automaticamente.

