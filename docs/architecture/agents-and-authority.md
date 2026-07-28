---
id: architecture-agents-authority
type: architecture
title: Agentes e autoridade
status: accepted
authority: normative
volatility: timeless
owner: core
created_at: 2026-07-22
updated_at: 2026-07-28
applies_to: agents
sources:
  - docs/adr/0022-explicit-execution-trust-without-per-run-authentication.md
  - docs/adr/0018-lab-agent-copilot-scope.md
  - docs/adr/0021-hierarchical-lab-agent-scope.md
  - docs/contracts/lab-agent-scope-v1.md
  - docs/contracts/execution-trust-v1.md
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

Existe um único papel e runtime de Lab Agent, não uma instância persistente por Project. Cada sessão
tem Workspace obrigatório, Project opcional e foco opcional dentro do mesmo Project. General chat
serve para navegação do Workspace sem leitura implícita de todos os Projects; Project chat lê o
Project exato e regras/preferências do Workspace pai; Focused chat estreita essa leitura a Study, Run
ou Comparison. O scope é imutável por sessão e cada tool o impõe no repository, nunca no prompt. O
contrato está aceito no [ADR 0021](../adr/0021-hierarchical-lab-agent-scope.md), mas o storage atual
ainda mantém somente `scope_type/scope_id` genéricos, sem essa validação tipada.

A fronteira do Lab Agent é de autoridade, não de capacidade. Ele não aceita a própria proposta, não
produz attestation, review ou adjudicação, não concede grant nem efeito externo, não escreve no
event ledger, não acessa `sensitive`/`restricted` sem grant próprio, não envia chat, hipótese ou
rubrica oculta ao Subject, e não apresenta draft ou Progress Artifact como fato. Quando uma ação
exige autoridade humana, ele produz um pedido de aprovação, nunca a decisão.

`hidden` é oculto do Subject, não do Lab Agent: hidden graders, calibração e a hipótese do
laboratório são invisíveis ao Subject por desenho do `SubjectEnvelope`, e o Lab Agent ajuda a
construí-los dentro do escopo do que o humano já vê.

O histórico [ADR 0010](../adr/0010-verifiable-human-authority.md) é materializado por
`HumanAttestationRecord`, `VerifiedHumanDecisionAuthority` e `HumanAttestationVerifier`. Uma
attestation cobre a ação e o digest exatos; agentes não podem produzi-la ou preencher uma decisão em
nome do humano. O verifier default falha fechado porque nenhum adapter WebAuthn confiável está
instalado. Consequentemente, API e CLI recusam decisions humanas; posse do launch token não é prova
de presença ou autoridade humana.

O [ADR 0022](../adr/0022-explicit-execution-trust-without-per-run-authentication.md) preserva essa
fronteira para todo claim humano e aceita um segundo caminho futuro: executar um conjunto fechado de
revisions como `unverified_revision_set`, sem transformar draft em accepted. O
`ExecutionTrustRecord` liga o conjunto e o RunSpec exatos e mantém trust separado de admissão e
isolamento. Essa decisão ainda não está implementada; até WS-40, o compiler continua resolvendo
somente revisions aceitas e a authority humana local continua opt-in.

O bootstrap de compatibilidade do `CRL-CTX-002` é uma exceção limitada: `repository_fixture` é uma
authority explicitamente não humana e materializa a aceitação preexistente de um benchmark
versionado. O repository só permite esse caminho pelo método dedicado
`import_legacy_contract_package`, após conferir o conjunto canônico completo de revisions e o digest
do pacote. Ele não se aplica a contracts externos ou a propostas criadas pelo Lab Agent.

## Subject Agent

Recebe somente o `SubjectEnvelope`, compilado por allowlist: Goal, inputs visíveis, protocolo visível,
capabilities efetivamente admitidas, Run Environment, budgets, stop conditions e, somente em
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
