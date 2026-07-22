---
id: architecture-data-evidence
type: architecture
title: Dados e evidência
status: implemented
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

# Dados e evidência

SQLite é a fonte operacional para revisions, runs, eventos, snapshots, grades, comparisons e chats.
Eventos são append-only por run e encadeados por SHA-256 sobre JSON canônico. A cadeia detecta
alterações, mas não equivale a assinatura criptográfica.

Artifacts públicos ou internos usam CAS. Raw sensível usa ID opaco e AES-256-GCM. Conteúdo
restricted não pode ser persistido.

JSONL existe dentro do Evidence Bundle. FTS, Parquet e relatórios são projeções reconstruíveis.

