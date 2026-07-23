---
id: contract-capture-retention-v1
type: contract
title: Captura e retenção v1
status: implemented
authority: normative
owner: security
created_at: 2026-07-22
updated_at: 2026-07-23
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
- O `ArtifactStore` rejeita restricted antes da persistência.
- Purge remove o blob e preserva tombstone com digest e motivo.
- Raw não sincroniza por padrão.
- Credenciais ficam no keychain ou ambiente, não no ledger.

Os itens acima são aplicados pelo `ArtifactStore`. O pipeline Study/Run ainda não roteia Context
Snapshots e payloads de eventos por esse store nem executa secret scanning em strings livres. Por
isso `CapturePolicySpec` é contrato validado, mas não deve ser apresentado como enforcement completo
fora do store até um successor de implementação fechar essas superfícies.
