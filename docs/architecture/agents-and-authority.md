---
id: architecture-agents-authority
type: architecture
title: Agentes e autoridade
status: accepted
authority: normative
volatility: timeless
owner: core
created_at: 2026-07-22
updated_at: 2026-07-26
applies_to: agents
sources:
  - docs/adr/0018-lab-agent-copilot-scope.md
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun/contracts/base.py
  - src/evidrun/contracts/authority.py
  - src/evidrun/contracts/compiler.py
  - src/evidrun/contracts/runtime
  - src/evidrun/infrastructure/database/repository.py
  - src/evidrun/entrypoints/api/app.py
  - src/evidrun/entrypoints/cli/app.py
verification_refs:
  - tests/unit/test_contract_revisions.py
  - tests/unit/test_contract_compilation.py
  - tests/integration/test_contract_api.py
  - tests/integration/test_contract_cli.py
---

# Agentes e autoridade

## Lab Agent

O Lab Agent é o copiloto do laboratório e a superfície primária de trabalho do produto. Seu escopo
funcional é o app inteiro, conforme o [ADR 0018](../adr/0018-lab-agent-copilot-scope.md): conduzir a
formulação de uma hipótese, propor drafts de qualquer contract de autoria, propor dimensões de
avaliação e graders novos, explicar Runs, evidência e rejeições de admissão, e operar as mesmas
superfícies públicas que um humano opera.

Ele ainda não possui runtime executável. Nada em `src/evidrun/` o implementa hoje, e a página
`Laboratory` é mock.

A fronteira do Lab Agent é de autoridade, não de capacidade. Ele não aceita a própria proposta, não
produz attestation, review ou adjudicação, não concede grant nem efeito externo, não escreve no
event ledger, não acessa `sensitive`/`restricted` sem grant próprio, não envia chat, hipótese ou
rubrica oculta ao Subject, e não apresenta draft ou Progress Artifact como fato. Quando uma ação
exige autoridade humana, ele produz um pedido de aprovação, nunca a decisão.

`hidden` é oculto do Subject, não do Lab Agent: hidden graders, calibração e a hipótese do
laboratório são invisíveis ao Subject por desenho do `SubjectEnvelope`, e o Lab Agent ajuda a
construí-los dentro do escopo do que o humano já vê.

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

`subject.invoked` registra um `subject_envelope_digest`. O Runtime Kernel persiste o documento exato
como `SubjectEnvelopeRecord`, revalida seu digest na leitura e o exporta no Bundle v3 por Run. O
Bundle v2 de comparison permanece inalterado e não contém esse record; portanto ele não permite
recomputar o envelope independentemente.

Tools e skills requeridas ficam no Agent Inventory; a admissão registra separadamente o que foi
resolvido. Capability opcional ausente não entra no envelope. Inventário não prova uso: o uso depende
dos eventos de lifecycle. O subconjunto do ADR 0016 executa exatamente a capability
`read-artifact-text` pelo adapter real e registra oferta, chamada e terminal sob fencing. Skills,
outras tools e nested agents continuam sem runtime e são rejeitados na admissão.

## Serviços determinísticos

Montagem de contexto, autorização, estado da run, retenção, event ledger e ordem dos graders não são
delegados a agentes. São serviços verificáveis.
