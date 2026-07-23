---
id: contract-agent-inventory-workspace-v1
type: contract
title: Inventário de agente, admissão e workspace v1
status: implemented
authority: normative
owner: core
created_at: 2026-07-23
updated_at: 2026-07-23
applies_to: schema/agent-admission@1
sources:
  - docs/adr/0009-study-run-contract-composition.md
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun/contracts/authoring.py
  - src/evidrun/contracts/compiler.py
  - src/evidrun/contracts/runtime.py
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
o permitido e nunca pode exceder o pedido.

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

O catálogo de admissão é explícito. O runner determinístico aceita `single_turn` e workspace
`in_process`; provider pode ser omitido para execução offline. Protocolos em grafo, tools, skills ou
nested-agent runtime sem adapter catalogado produzem rejeição estruturada. Uma rejeição não cria Run
e não apresenta a capability como executável.
