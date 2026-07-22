---
id: security-privacy-retention
type: security
title: Privacidade e retenção
status: accepted
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

# Privacidade e retenção

Metadata e conteúdo redigido permanecem até exclusão explícita. Raw sensível autorizado expira em
30 dias. Pin registra motivo, autor e nova expiração. Restricted nunca é salvo.

O sistema não pede chain-of-thought privado. Reasoning summary só é salvo se fornecido explicitamente
pelo provider e permitido pela capture policy.

Purge alcança stores e projeções gerenciadas. Cópias exportadas estão fora desse alcance e devem ser
apresentadas ao usuário antes da exportação.

