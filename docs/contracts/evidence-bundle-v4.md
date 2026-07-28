---
id: contract-evidence-bundle-v4
type: contract
title: Evidence Bundle v4 com Execution Trust
status: accepted
authority: normative
volatility: timeless
owner: governance
created_at: 2026-07-28
updated_at: 2026-07-28
applies_to: schema/evidence-bundle@4
sources:
  - docs/contracts/evidence-bundle-v3.md
  - docs/contracts/execution-trust-v1.md
  - docs/adr/0022-explicit-execution-trust-without-per-run-authentication.md
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
---

# Evidence Bundle v4 com Execution Trust

O Bundle v4 preserva o perfil auditável e `references_only` do v3, mas torna o trust da execução um
record canônico verificável. Ele se aplica somente a uma Run ligada a `ExecutionTrustRecord`; uma
Run legada sem esse record permanece `not_recorded` e usa o exportador compatível aplicável, sem
inferência retroativa.

Este contrato está aceito, mas ainda não implementado. A existência deste documento não torna o
exportador v4 disponível até que os `implementation_refs` e `verification_refs` sejam preenchidos.

## Layout exato

```text
bundle.json
contracts/<type>/<logical-id>@<revision>.json
run-specs/<id>.json
admissions/<id>.json
runs/<run-id>.json
execution-trust/<trust-id>.json
revision-decisions/<decision-digest>.json  # somente no kind verificado
events/<run-id>.jsonl
evaluations/<run-id>.json
checkpoints/<run-id>.json
subject-envelopes/<run-id>.json  # presente quando a materialização foi alcançada
execution/jobs/<job-id>.json
execution/attempts/<job-id>.json
artifact-manifest.json
checksums.json
```

`bundle.json` declara `schema_version=4`, `kind=run`, `profile=audit`,
`artifact_content=references_only`, `portable=false` e `replayable=false`. Também apresenta:

```text
execution_trust.kind
execution_trust.trust_id
execution_trust.digest
isolation.kind
```

Trust e isolamento são campos independentes. `unverified_revision_set` nunca é traduzido para
`sandbox`, e `in_process` nunca é apresentado como isolamento forte.

## Record de trust

`execution-trust/<trust-id>.json` contém o `ExecutionTrustRecord` completo. O membro precisa:

- corresponder ao `trust_id` e digest declarados em `bundle.json`;
- reproduzir o `revision_set_digest` a partir de `project_id`, `study_ref` e `revision_refs`;
- ligar exatamente o RunSpec exportado por `run_spec_digest`;
- corresponder às refs e digests gravadas no AdmissionRecord e no RunRecord;
- possuir bindings vazios em `unverified_revision_set`;
- cobrir exatamente todas as revisions, em ordem canônica, no `verified_revision_set`.

No kind verificado, cada binding possui exatamente um
`revision-decisions/<decision-digest>.json`. O documento é o `RevisionDecisionRecord` completo,
inclusive sua autoridade e `HumanAttestationRecord` embutido. O digest precisa corresponder ao nome
do membro e ao binding; a decisão precisa ser `accepted`, cobrir a revision exata e passar pela
verificação humana. No kind não verificado, qualquer membro `revision-decisions/` é extra e invalida
o bundle.

As contract revisions listadas no trust são o conjunto exato exportado em `contracts/`. Ref ausente,
extra, futura, de outro Project, com digest divergente ou fora do conjunto selado invalida o bundle.

## Verificação isolada

O verificador v4 executa todas as validações do v3 e, sem consultar o SQLite original:

1. valida a allowlist exata de membros e todos os checksums;
2. recalcula cada contract revision e o RunSpec;
3. recalcula `revision_set_digest` e o digest completo do trust;
4. liga trust, RunSpec, AdmissionRecord e RunRecord por identidade e digest;
5. confirma a policy do kind não verificado;
6. no kind verificado, valida cobertura completa, digest, attestation e autoridade de cada decision
   humana exportada pelo binding canônico;
7. valida lifecycle, ledger, evaluations, checkpoints, SubjectEnvelope, job, attempts e artifact
   manifest conforme o v3.

Uma string de metadata, ausência de decision ou ator enviado por API não substitui o record. O
verificador rejeita trust omitido, duplicado, trocado entre Runs ou alterado mesmo quando o checksum
for refeito por um atacante.

## Rótulo humano

Toda projeção humana do bundle apresenta trust como texto e o separa do isolamento:

```text
Trust: Não verificada — sem confirmação humana das revisions
Isolamento: in_process
```

ou:

```text
Trust: Verificada — revisions confirmadas por autoridade humana
Isolamento: in_process
```

HTML ou PDF repete pelo menos o rótulo curto e `trust_id` no cabeçalho ou rodapé de cada página.
Cor, ícone e tooltip podem reforçar, mas não substituem o texto.

## Compatibilidade

- Bundles v1, v2 e v3 continuam com seus contratos, exportadores e verificadores próprios.
- O v3 não ganha membro opcional de trust e sua allowlist permanece inalterada.
- Run legada sem trust não é promovida para v4 nem classificada por inferência.
- O v4 continua auditável, não portátil e não replayable; não inclui blobs, grants, restore, secrets
  ou estado privado recuperável.
