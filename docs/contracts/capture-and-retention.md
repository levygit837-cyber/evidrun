---
id: contract-capture-retention-v1
type: contract
title: Captura e retenção v1
status: implemented
authority: normative
owner: security
created_at: 2026-07-22
updated_at: 2026-07-22
applies_to: data
sources: []
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun/infrastructure/artifacts/store.py
verification_refs:
  - tests/security/test_artifact_store.py
---

# Captura e retenção v1

Classificações: `public`, `internal`, `sensitive`, `restricted`.

Modos: `metadata`, `redacted`, `raw_encrypted`, `disabled`.

- Raw sensível exige opt-in e usa TTL padrão de 30 dias.
- Pin exige motivo e nova expiração.
- Restricted nunca é persistido.
- Purge remove o blob e preserva tombstone com digest e motivo.
- Raw não sincroniza por padrão.
- Credenciais ficam no keychain ou ambiente, não no ledger.

