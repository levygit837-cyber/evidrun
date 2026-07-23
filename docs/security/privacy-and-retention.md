---
id: security-privacy-retention
type: security
title: Privacidade e retenção
status: accepted
authority: normative
owner: security
created_at: 2026-07-22
updated_at: 2026-07-23
applies_to: data
sources: []
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun/contracts/runtime.py
  - src/evidrun/contracts/compiler.py
  - src/evidrun/infrastructure/artifacts/store.py
  - src/evidrun/infrastructure/database/repository.py
verification_refs:
  - tests/security/test_artifact_store.py
  - tests/unit/test_contracts.py
  - tests/integration/test_admission_and_evaluation.py
---

# Privacidade e retenção

No `ArtifactStore`, metadata e conteúdo redigido permanecem até exclusão explícita. Raw sensível
autorizado expira em 30 dias; pin registra motivo, autor e nova expiração; restricted é rejeitado.
O runtime de Run atual rejeita na admissão todo input `sensitive` ou `restricted`, pois ainda não
possui boundary classificada de materialização. Apenas `public` e `internal` seguem para esse adapter.

Na resposta do Subject, o payload valida a forma permitida por `metadata`, `redacted`,
`raw_encrypted` ou `disabled`, e o repository exige que o modo corresponda exatamente ao RunSpec.
O adapter real do ADR 0016 aceita `raw_encrypted` somente com opt-in e grava o resultado em artifact
`sensitive` cifrado; adapters sem esse sink continuam bloqueados. Esses controles ainda não cobrem
automaticamente Context Snapshots, todos os demais payloads de evento ou strings livres de contracts.

O sistema não pede chain-of-thought privado. Reasoning summary só é salvo se fornecido explicitamente
pelo provider e permitido pela capture policy.

O purge implementado recebe um `artifact_id`, remove seu blob e preserva tombstone. Cascata para
snapshots, eventos e projeções ainda não existe. Cópias exportadas estão fora desse alcance e devem
ser apresentadas ao usuário antes da exportação.
