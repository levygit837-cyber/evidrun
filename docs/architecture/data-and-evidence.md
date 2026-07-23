---
id: architecture-data-evidence
type: architecture
title: Dados e evidência
status: implemented
authority: normative
owner: core
created_at: 2026-07-22
updated_at: 2026-07-23
applies_to: evidence
sources: []
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun/infrastructure/database
  - src/evidrun/evidence/bundle.py
verification_refs:
  - tests/acceptance/test_demo_flow.py
  - tests/integration/test_contract_migration.py
  - tests/integration/test_checkpoint_repository.py
---

# Dados e evidência

SQLite é a fonte operacional para contract revisions e decisões, RunSpecs, admissions, runs,
eventos, snapshots, evaluations, checkpoints, grades legados, comparisons e chats. A migração é
aditiva: Runs antigas permanecem legíveis como `legacy_v1`; Runs novas ligam spec e admission.

Eventos são append-only por Run e encadeados por SHA-256 sobre JSON canônico. Payloads core
registrados são tipados antes da gravação. A cadeia detecta alterações, mas não equivale a assinatura
criptográfica.

Artifacts públicos ou internos usam CAS. Raw sensível usa ID opaco e AES-256-GCM. Conteúdo
restricted não pode ser persistido.

Essa garantia está implementada no `ArtifactStore`, não automaticamente em toda escrita do pipeline
de Run. O evento de resposta do Subject já aplica os modos metadata/redacted/disabled, e a admissão
rejeita `raw_encrypted` enquanto não há sink cifrado. Porém o demo usa fixture internal e
`ContextSnapshotRow.selected_content` continua fora desse enforcement. Até a classification dos
inputs e snapshots passar pelo mesmo boundary, o runner novo não deve receber conteúdo
sensitive/restricted nem ser apresentado como captura sensível completa.

JSONL existe dentro do Evidence Bundle. Bundle v1 permanece verificável; v2 carrega as revisions,
specs, admissions, evaluations e checkpoints da composição nova, além de hashes e event chains. FTS,
Parquet, Grade, scorecards e relatórios não são fontes canônicas. Grade e relatórios legados já são
projeções operacionais; FTS e Parquet continuam planejados.
