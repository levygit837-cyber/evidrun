---
id: operations-backup-recovery
type: operations
title: Backup e recuperação
status: proposed
authority: normative
owner: core
created_at: 2026-07-22
updated_at: 2026-07-23
applies_to: data
sources: []
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun/infrastructure/database/engine.py
  - src/evidrun/runs/worker.py
verification_refs:
  - tests/integration/test_runtime_kernel.py
  - tests/integration/test_runtime_queue.py
---

# Backup e recuperação

Backup consistente deve usar a API de backup SQLite ou checkpoint controlado, nunca copiar apenas o
arquivo principal enquanto WAL está ativo. Artifacts e metadata precisam acompanhar o snapshot.

Restore acontece em diretório isolado, valida migrations, foreign keys e event chains antes de
substituir dados ativos. Raw expirado não deve reaparecer por restore sem uma decisão explícita de
retenção.

Jobs queued e leased pertencem ao backup canônico. Depois do restore, um lease vencido é marcado
`expired` no próximo claim e gera outro attempt na mesma Run. O worker não reinvoca silenciosamente
quando o ledger contém `subject.invoked` sem `subject.responded`; essa Run termina failed e exige retry
explícito para novo processamento.
