---
id: contract-capture-retention-v1
type: contract
title: Captura e retenção v1
status: implemented
authority: normative
volatility: timeless
owner: security
created_at: 2026-07-22
updated_at: 2026-07-26
applies_to: data
sources: []
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun/contracts/runtime
  - src/evidrun/contracts/compiler.py
  - src/evidrun/infrastructure/artifacts/store.py
  - src/evidrun/infrastructure/database/repository.py
verification_refs:
  - tests/security/test_artifact_store.py
  - tests/unit/test_contract_admission.py
  - tests/unit/test_contract_evaluation.py
  - tests/integration/test_admission_and_evaluation.py
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

Os itens acima são aplicados pelo `ArtifactStore`. No pipeline Study/Run, o runtime atual admite
somente inputs `public` ou `internal`; qualquer input `sensitive` ou `restricted` rejeita a admissão
porque não existe boundary classificada de materialização. O adapter real do ADR 0016 admite
`raw_encrypted` com opt-in e persiste a resposta como artifact `sensitive` cifrado; adapters sem esse
sink continuam rejeitando o modo.

`SubjectRespondedPayload` aplica o shape correspondente ao modo: `redacted` aceita somente o marcador
`[REDACTED]`; `metadata` não aceita output ou evidence; `disabled` também não aceita metadata; e
`raw_encrypted` aceita apenas refs `artifact:`, nunca conteúdo inline. Na persistência, o
`capture_mode` do evento precisa ser exatamente o `CapturePolicySpec.default_mode` do RunSpec.

Essas garantias não equivalem a enforcement ponta a ponta: Context Snapshots e todos os payloads de
evento ainda não passam pelo `ArtifactStore`, e strings livres não recebem secret scanning.

`ArtifactRef` preserva identidade e classification, mas não concede acesso. Grants e materialization
records decididos pelo [ADR 0011](../adr/0011-progress-artifacts-and-bundle-boundaries.md) ainda não
estão implementados.
