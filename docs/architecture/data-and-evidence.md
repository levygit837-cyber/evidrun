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
  - src/evidrun/contracts/authoring.py
  - src/evidrun/contracts/runtime.py
  - src/evidrun/contracts/compiler.py
  - src/evidrun/infrastructure/database
  - src/evidrun/evidence/bundle.py
verification_refs:
  - tests/acceptance/test_demo_flow.py
  - tests/unit/test_contracts.py
  - tests/integration/test_admission_and_evaluation.py
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

Conforme o [ADR 0011](../adr/0011-progress-artifacts-and-bundle-boundaries.md), `ArtifactRef`
identifica conteúdo por ID, digest, media type e classification; não possui locator de storage e não
prova existência, inclusão nem autorização de leitura. Grants e records de materialização separados
ainda não estão implementados.

Essa garantia está implementada no `ArtifactStore`, não automaticamente em toda escrita do pipeline
de Run. O runtime atual rejeita na admissão qualquer input `sensitive` ou `restricted`; somente
`public` e `internal` podem alcançar seu materializador. `SubjectRespondedPayload` limita o conteúdo
permitido por capture mode, e o repository exige que esse modo corresponda ao RunSpec. A admissão
rejeita `raw_encrypted` enquanto não há sink cifrado.

O demo usa fixture internal e `ContextSnapshotRow.selected_content` continua fora do
`ArtifactStore`. Portanto esses bloqueios reduzem a superfície do runtime atual, mas não devem ser
apresentados como captura sensível completa ou enforcement de classification em toda persistência.

JSONL existe dentro do Evidence Bundle. Bundle v1 permanece verificável; v2 carrega as revisions,
specs, admissions, evaluations e checkpoints da composição nova, além de hashes, event chains e um
`artifact-manifest.json`. O perfil atual é `audit`/`references_only`, com `portable=false` e
`replayable=false`. O artifact manifest enumera refs de artifacts intencionalmente materializados;
não é telemetria de toda leitura ou edição de arquivo. FTS, Parquet, Grade, scorecards e relatórios
não são fontes canônicas. Grade e relatórios legados já são projeções operacionais; FTS e Parquet
continuam planejados.

`ProgressArtifactPolicy`, `ProgressArtifactContent` e `ProgressArtifactRecord` possuem schemas
fechados, e o catálogo de Run Events tipa início, conclusão e falha do observer. O resumo é projeção
provisória append-only ancorada ao prefixo do ledger; não é inventário de arquivos nem substituto do
ledger. As únicas boundaries de policy são checkpoint alcançado e intervalo de turnos do Subject, em
que turno significa um evento válido `subject.responded`.

Observer, scheduler, persistência do record e gerador em background não existem. Uma policy de
Progress Artifact compila, mas a admissão a rejeita como
`runtime:background_progress_observer`. O repository também rejeita os eventos `progress.*` como
reservados; portanto o runtime atual não cria esses records ou eventos.
