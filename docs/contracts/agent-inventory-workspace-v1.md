---
id: contract-agent-inventory-workspace-v1
type: contract
title: Inventário de agente, admissão e workspace v1
status: implemented
authority: normative
owner: core
created_at: 2026-07-23
updated_at: 2026-07-25
applies_to: schema/agent-admission@1
sources:
  - docs/adr/0009-study-run-contract-composition.md
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun/contracts/authoring
  - src/evidrun/contracts/compiler.py
  - src/evidrun/contracts/runtime
verification_refs:
  - tests/unit/test_contracts.py
  - tests/integration/test_contract_api.py
---

# Requisitos e resolução

`AgentInventoryRevision` declara Subject, runner, profile de provider opcional, capability requirements
e runtime requirements. Cada capability é `tool` ou `skill`, possui ref/version/digest, obrigatoriedade,
versão mínima de interface, permissões solicitadas, exposição, artifacts de instrução e constraints de
autoridade.

`ResolvedAgentInventory` é criado somente na admissão e fixa runner, provider/model/reasoning quando
aplicável, adapter, schemas, contexto materializado, permissões efetivas e status de cada capability:
`resolved`, `unsupported`, `denied` ou `unavailable`. Permissão efetiva é interseção do solicitado com
o permitido e nunca pode exceder o pedido. `ArtifactRef` não possui `locator`, portanto schema refs,
instruction refs e context refs não podem carregar paths ou URLs de storage.

Capability obrigatória não resolvida rejeita a admissão. Capability opcional ausente continua no
record auditável, mas não é oferecida ao Subject. A presença no inventário não prova uso: oferta,
carregamento, invocação, aprovação e resultado são eventos distintos.

# Workspace de execução

`WorkspaceTemplateRevision` descreve apenas o execution workspace: runtime lógico, lifecycle efêmero
por Run, mounts nomeados, write zones, network policy, external-effect policy, refs opacas de secret
bindings, snapshot policy e cleanup policy. O laboratory workspace não é montado.

Valores de credenciais não fazem parte de nenhum contrato, evento, log ou bundle. Budgets pertencem
ao `RunSpec`, pois podem variar por Study e variant.

# Admissão atual

O catálogo de admissão é explícito. O runner determinístico aceita um `single_turn` direto, com
`max_turns=1` e sem artifacts de system prompt ou mensagens iniciais, além do workspace
`in_process`; provider pode ser omitido para execução offline. O adapter real do ADR 0016 aceita o
provider profile exato, network `provider_only`, uma única capability `read-artifact-text` e capture
`raw_encrypted` com opt-in. Protocolos em grafo, tools diferentes, skills ou nested-agent runtime sem
adapter catalogado produzem rejeição estruturada. Uma rejeição não cria Run nem apresenta a
capability como executável.

Todo adapter executa `max_wall_seconds`; `max_turns` pode ser omitido ou igual a 1. O adapter real
também executa `max_tool_calls` entre 1 e 8. Budgets de input/output tokens ou custo, tool budget no
adapter offline e `max_turns > 1` rejeitam a admissão. Stops aceitos são somente `goal_complete` e
`budget_exhausted`, ambos terminais, e o stop de budget é obrigatório.
Pause, predicates, human stop, guardrail ou provider error exigem coordinator indisponível.

Qualquer input de cenário classificado como `sensitive` ou `restricted` também rejeita a admissão
do runtime ativo, independentemente da visibilidade, porque ele ainda não possui materialization
boundary classificada. Somente inputs `public` e `internal` são admitidos.

A mesma regra fail-closed se aplica a contratos mais amplos: Progress Artifact policy exige o
observer ausente; CheckpointPolicy exige coordinator; bounded exploration exige terminal compatível;
adjudicação humana required exige verifier/runtime; qualquer disclosure diferente de `none` exige
um runner que consuma guidance; e EvaluationPlan fora do grader determinístico suportado exige
pipeline genérico.
Todos são representáveis, mas atualmente bloqueiam a admissão com motivo estruturado.

Para `in_process`, `workspace_status=resolved` exige runtime e policies compatíveis e que cada mount
seja um input Subject-visible idêntico, read-only e autorizado pelo cenário. Write zones, secret
bindings, workspace snapshot e retenção diferente de `discard` são rejeitados como não suportados.
O adapter ainda não provisiona filesystem nem consulta um artifact catalog externo; o runner
determinístico materializa seu único input como Context Snapshot referenciado por identidade e
digest; nenhum contrato possui locator de storage.
