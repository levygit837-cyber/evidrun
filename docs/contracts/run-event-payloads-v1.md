---
id: contract-run-event-payloads-v1
type: contract
title: Catálogo de payloads de Run Event v1
status: implemented
authority: normative
owner: core
created_at: 2026-07-23
updated_at: 2026-07-23
applies_to: schema/run-event-payloads@1
sources:
  - docs/contracts/run-event.md
  - docs/adr/0009-study-run-contract-composition.md
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun/contracts/runtime.py
  - src/evidrun/infrastructure/database/repository.py
  - src/evidrun/runs/service.py
verification_refs:
  - tests/acceptance/test_demo_flow.py
  - tests/unit/test_contracts.py
---

# Catálogo tipado

O envelope e a hash chain de Run Event v1 permanecem inalterados. Para tipos registrados, o payload
é validado por modelo Pydantic fechado antes de entrar no ledger.

O marco implementa payloads tipados para fila, preparação, composição de contexto, invocação e
resposta do Subject, avaliação e término da Run. O catálogo também reserva eventos de lifecycle de
capabilities: oferta, carregamento, invocação, conclusão ou falha de skill; chamada, aprovação,
negação, conclusão ou falha de tool.

Presença no inventário não equivale a uso. Projeções de tools e skills usadas contam os eventos de
lifecycle correspondentes. Conteúdo capturado continua sujeito à classificação e capture policy.
