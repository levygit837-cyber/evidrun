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
  - src/evidrun/infrastructure/artifacts/store.py
verification_refs:
  - tests/security/test_artifact_store.py
---

# Privacidade e retenção

No `ArtifactStore`, metadata e conteúdo redigido permanecem até exclusão explícita. Raw sensível
autorizado expira em 30 dias; pin registra motivo, autor e nova expiração; restricted é rejeitado.
Esses controles ainda não cobrem automaticamente Context Snapshots, payloads de eventos ou strings
livres de contracts. A proibição de persistir restricted continua normativa, mas o pipeline de Run
deve receber somente dados internal até aplicar classification e capture policy de ponta a ponta.

O sistema não pede chain-of-thought privado. Reasoning summary só é salvo se fornecido explicitamente
pelo provider e permitido pela capture policy.

O purge implementado recebe um `artifact_id`, remove seu blob e preserva tombstone. Cascata para
snapshots, eventos e projeções ainda não existe. Cópias exportadas estão fora desse alcance e devem
ser apresentadas ao usuário antes da exportação.
