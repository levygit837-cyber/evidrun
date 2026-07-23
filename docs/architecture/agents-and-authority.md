---
id: architecture-agents-authority
type: architecture
title: Agentes e autoridade
status: accepted
authority: normative
owner: core
created_at: 2026-07-22
updated_at: 2026-07-23
applies_to: agents
sources: []
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun/contracts/base.py
  - src/evidrun/contracts/authority.py
  - src/evidrun/contracts/compiler.py
  - src/evidrun/contracts/runtime.py
  - src/evidrun/infrastructure/database/repository.py
  - src/evidrun/entrypoints/api/app.py
  - src/evidrun/entrypoints/cli/app.py
verification_refs:
  - tests/unit/test_contracts.py
  - tests/integration/test_contract_api.py
  - tests/integration/test_contract_cli.py
---

# Agentes e autoridade

## Lab Agent

Poderá ler evidências autorizadas, explicar Runs e criar drafts. O Lab Agent ainda não possui runtime
executável e, quando existir, não aceitará a própria proposta, não acessará raw sem grant, não excluirá
dados e não executará efeitos externos sem decisão humana.

O [ADR 0010](../adr/0010-verifiable-human-authority.md) é materializado por
`HumanAttestationRecord`, `VerifiedHumanDecisionAuthority` e `HumanAttestationVerifier`. Uma
attestation cobre a ação e o digest exatos; agentes não podem produzi-la ou preencher uma decisão em
nome do humano. O verifier default falha fechado porque nenhum adapter WebAuthn confiável está
instalado. Consequentemente, API e CLI recusam decisions humanas; posse do launch token não é prova
de presença ou autoridade humana.

O bootstrap de compatibilidade do `CRL-CTX-002` é uma exceção limitada: `repository_fixture` é uma
authority explicitamente não humana e materializa a aceitação preexistente de um benchmark
versionado. O repository só permite esse caminho pelo método dedicado
`import_legacy_contract_package`, após conferir o conjunto canônico completo de revisions e o digest
do pacote. Ele não se aplica a contracts externos ou a propostas criadas pelo Lab Agent.

## Subject Agent

Recebe somente o `SubjectEnvelope`, compilado por allowlist: Goal, inputs visíveis, protocolo visível,
capabilities efetivamente admitidas, workspace, budgets, stop conditions e, somente em
`disclosure=pre_run`, guidance público mínimo compilável. O runner ativo não consome esse guidance e
a admissão rejeita todo disclosure diferente de `none`. O Subject não recebe StudyIntent, hipótese
do laboratório, plan completo, chats, hidden graders, calibration, credenciais ou resultados de
outras variants.
`ArtifactRef` não concede acesso e campo novo do RunSpec não entra automaticamente no envelope.
`ArtifactRef` não possui `locator`, portanto paths e URLs de storage não são representáveis nos
inputs ou capability refs do Subject, nem nos inputs, hidden refs e instructions do Evaluator.

`subject.invoked` registra um `subject_envelope_digest`, mas o documento exato do SubjectEnvelope
materializado não possui record persistido nem arquivo próprio no Bundle v2. Assim o ledger preserva
a alegação do digest usado pelo runner, mas o export atual não permite recomputá-lo
independentemente. Essa limitação não autoriza reconstruir o envelope a partir do RunSpec, pois os
inputs materializados podem ser diferentes.

Tools e skills requeridas ficam no Agent Inventory; a admissão registra separadamente o que foi
resolvido. Capability opcional ausente não entra no envelope. Inventário não prova uso: o uso depende
dos eventos de lifecycle. O runtime real de tools, skills e nested agents ainda não existe.

## Serviços determinísticos

Montagem de contexto, autorização, estado da run, retenção, event ledger e ordem dos graders não são
delegados a agentes. São serviços verificáveis.
