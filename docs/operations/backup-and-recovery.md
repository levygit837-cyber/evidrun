---
id: operations-backup-recovery
type: operations
title: Backup e recuperação
status: proposed
authority: normative
owner: core
created_at: 2026-07-22
updated_at: 2026-07-22
applies_to: data
sources: []
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
---

# Backup e recuperação

Backup consistente deve usar a API de backup SQLite ou checkpoint controlado, nunca copiar apenas o
arquivo principal enquanto WAL está ativo. Artifacts e metadata precisam acompanhar o snapshot.

Restore acontece em diretório isolado, valida migrations, foreign keys e event chains antes de
substituir dados ativos. Raw expirado não deve reaparecer por restore sem uma decisão explícita de
retenção.

