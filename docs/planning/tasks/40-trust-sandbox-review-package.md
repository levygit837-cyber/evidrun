---
id: planning-task-trust-sandbox-review-package
type: implementation-task
title: WS-40 Trust modes, Sandbox Run e ReviewPackage
status: proposed
authority: planning
owner: governance
created_at: 2026-07-23
updated_at: 2026-07-23
observed_at: 2026-07-23
review_due: 2026-08-06
applies_to: control-plane-trust
sources:
  - docs/adr/0010-verifiable-human-authority.md
  - docs/adr/0015-human-subject-envelope-and-authenticator-lifecycle.md
  - docs/planning/mvp-capability-map.md
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
---

# WS-40 — Trust modes, sandbox e ReviewPackage

`workstream_state: queued`

## Problema

Authority e opt-in, mas o compiler ainda resolve somente revisions aceitas. Na pratica, um usuario
nao consegue executar rapidamente um Study draft sem produzir uma aceitacao humana. Isso contradiz
o objetivo de sandbox rotineiro, embora preserve corretamente a seguranca.

Esta task cria um caminho explicitamente nao verificado; ela nao torna a autenticacao humana
opcional para claims humanos.

## Pre-condicao normativa

Criar ADR sucessor antes do codigo. O ADR deve decidir:

- identidade e digest do pacote sandbox;
- como drafts/proposed imutaveis sao selados para uma execucao;
- qual record declara trust sem se passar por `RevisionDecisionRecord`;
- quais restricoes sao obrigatorias;
- como funciona promocao para revisao humana;
- se uma promocao reexecuta a Run ou apenas aceita contracts para Runs futuras.

Recomendacao inicial a validar no ADR:

```text
ExecutionTrustRecord.kind = unverified_sandbox | verified_revision_set
```

`unverified_sandbox` referencia os documentos e digests exatos usados para compilar, mas nao altera
seu status para accepted. A Run e o bundle carregam trust explicitamente. Promocao nunca reescreve a
Run passada; cria decisions humanas para o pacote e uma nova Run quando evidencia verificada for
necessaria.

## ReviewPackage

Um `ReviewPackage` lista explicitamente:

- Study e todas as refs transitivas;
- digests;
- diff desde o pacote anterior;
- Subject disclosure;
- capabilities/permissoes;
- classifications;
- network/external effects;
- EvaluationPlan e hidden inputs sem expor seu conteudo ao Subject;
- riscos e limitacoes.

Uma confirmacao pode cobrir o pacote inteiro porque o digest inclui cada item. Ref nova ou digest
novo invalida o pacote; nao existe aprovacao aberta para referencias futuras.

## Restricoes do sandbox

- local-only;
- `public`/`internal`; nunca `sensitive` ou `restricted` neste marco;
- external effects `denied`;
- network no maximo `provider_only` para adapter explicitamente admitido;
- nenhuma human review/adjudication;
- nenhum claim `human_verified`;
- bundle e UI marcados `unverified_sandbox`;
- nenhuma promocao automatica;
- nenhuma alteracao da Run original;
- capabilities somente do catalogo seguro do Runtime Kernel.

## Harness

```text
TASK_ID=WS-40
MAX_REPAIR_LOOPS=10
FULL_GATE_INTERVAL=3
ADR_REQUIRED_BEFORE_CODE=1
ALLOW_FAKE_HUMAN=0
ALLOW_SANDBOX_PROMOTION_IN_PLACE=0
ALLOW_EXTERNAL_EFFECTS=0
```

Loop:

```text
MODEL threat and UX
-> WRITE successor ADR
-> HUMAN review of normative questions
-> IMPLEMENT trust/package contracts
-> IMPLEMENT compiler/admission path
-> IMPLEMENT API/CLI
-> ATTACK claim confusion and digest drift
-> REPAIR
-> INTEGRATE authority promotion
-> FULL GATES
```

### Condicionais

- Se o ADR nao fechar a fonte de verdade do sandbox package, nao implemente.
- Se qualquer resposta/API chamar sandbox de accepted/verified, P0.
- Se um agent endpoint puder completar authority confirmation, P0.
- Se a promocao puder alterar a Run original, rejeite o design.
- Se um diff de package omitir capability, hidden input ou disclosure, nao permita confirmacao.
- Se platform passkey/recovery surgir como requisito, abra follow-up; o autenticador local opt-in
  continua suficiente para o MVP local.

## Subagentes

- security reviewer read-only para confused authority e replay;
- product reviewer read-only para reduzir friccao cotidiana;
- contract reviewer read-only para digest/package/transitive refs.

## Testes obrigatorios

- draft sandbox compila sem Decision humana e preserva todos os digests;
- bundle/UI nunca afirmam human verified;
- sensitive/restricted/external effect rejeitados;
- package muda quando qualquer ref, permission, input ou disclosure muda;
- package nao aceita ref futura;
- challenge cobre package exato;
- agente nao completa confirmation;
- promocao cria decisions append-only e nova Run quando executada;
- revogacao impede novas confirmacoes sem invalidar historia;
- replay de challenge e action/target divergentes;
- API/CLI equivalentes;
- migrations empty/legacy/current.

## Criterio de saida

Um usuario executa um Study draft em sandbox sem autenticacao e recebe claims honestos. O mesmo
pacote pode ser revisado com uma confirmacao humana explicita, e qualquer execucao verificada nasce
como nova Run ligada ao pacote aceito.
