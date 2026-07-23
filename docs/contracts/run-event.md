---
id: contract-run-event-v1
type: contract
title: Run Event v1
status: implemented
authority: normative
owner: core
created_at: 2026-07-22
updated_at: 2026-07-23
applies_to: schema/run-event@1
sources: []
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun/infrastructure/database/repository.py
  - src/evidrun/contracts/runtime.py
verification_refs:
  - tests/acceptance/test_demo_flow.py
---

# Run Event v1

Envelope obrigatório:

```text
event_id, schema_version, run_id, sequence, type, occurred_at_utc,
actor_type, actor_id, classification, payload, correlation_id,
causation_id, prev_event_hash, event_hash
```

`sequence` é monotônico dentro da run. `event_hash` cobre o envelope sem o próprio hash.
`prev_event_hash` liga o evento ao predecessor. Retry cria nova run; eventos anteriores não mudam.
Payloads core são fechados e validados pelo
[catálogo de payloads v1](run-event-payloads-v1.md). Tipo não registrado é rejeitado antes do ledger.
