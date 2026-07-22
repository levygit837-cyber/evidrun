---
id: adr-0005
type: adr
title: SQLite e event ledger como evidência canônica
status: accepted
authority: normative
owner: core
created_at: 2026-07-22
updated_at: 2026-07-22
applies_to: evidence
sources: []
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun/infrastructure/database
  - src/evidrun/evidence/bundle.py
verification_refs:
  - tests/acceptance/test_demo_flow.py
---

# Decisão

SQLite é canônico para estado e eventos. Artifacts usam filesystem gerenciado. JSONL existe no bundle,
não como segunda base viva. Eventos são append-only e encadeados por hash.

# Consequências

Evita dual-write. Projeções FTS, Parquet e relatórios podem ser reconstruídas.

