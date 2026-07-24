# Data models

Evidrun persists state in SQLite. The SQLAlchemy models are in `src/evidrun/infrastructure/database/models.py`; the frozen contract models they store as JSON are generated into JSON Schema under `schemas/generated/contracts/`. This page indexes both. See [systems: database](../systems/database.md) for the persistence layer and [systems: contracts](../systems/contracts/index.md) for the contracts.

## SQLAlchemy tables

All models extend `Base` (a `DeclarativeBase`). IDs are string primary keys (prefixed UUIDv7 from `new_id`, except the content-addressed `art_<digest>`). Timestamps are timezone-aware UTC.

| Table | Model | Purpose |
| --- | --- | --- |
| `workspaces` | `WorkspaceRow` | The local data boundary; parent of projects and chats |
| `projects` | `ProjectRow` | A set of scenarios, experiments, and conversations under a workspace |
| `contract_revisions` | `ContractRevisionRow` | Immutable authoring revisions, unique by (contract_type, logical_id, revision), with the document JSON, digest, and status |
| `contract_decisions` | `ContractDecisionRow` | Accept/reject/supersede decisions on a revision, with actor, rationale, and decision digest |
| `run_specs` | `RunSpecRow` | Compiled atomic specs (study/scenario/variant/repetition), unique by digest |
| `admission_records` | `AdmissionRecordRow` | The pre-queue admission decision per RunSpec, with the record JSON and digest |
| `experiment_revisions` | `ExperimentRevisionRow` | Legacy `ExperimentManifest` revisions, unique by manifest hash |
| `runs` | `RunRow` | An attempt bound to a RunSpec and admission; `status` is an operational cache advanced with each lifecycle event |
| `run_events` | `RunEventRow` | The append-only ledger, unique by (run_id, sequence), hash-chained via `prev_event_hash` → `event_hash` |
| `context_snapshots` | `ContextSnapshotRow` | The context actually delivered in one invocation, with strategy, sizes, selected content, omissions, and content hash |
| `grades` | `GradeRow` | Legacy grade projection (score, passed, rationale, evidence) kept for compatibility |
| `checkpoint_records` | `CheckpointRecordRow` | Validated milestones, unique by (run_id, definition_id, up_to_event_sequence), with the checkpoint hash |
| `evaluation_records` | `EvaluationRecordRow` | Append-only evaluation results (source type, stage, record JSON, digest) |
| `comparisons` | `ComparisonRow` | A paired reading of a baseline and candidate run, with scores, delta, validity, and a markdown report |
| `chat_sessions` | `ChatSessionRow` | A chat session scoped to a workspace and optional entity |
| `chat_messages` | `ChatMessageRow` | Messages in a chat session (role, content) |

`RunRow.status` is a projection cache; the repository validates the state machine and advances the column in the same transaction that appends each lifecycle event, and `update_run` does not accept a direct status change. The `run_events` ledger stays the normative authority. Migrations live in `alembic/versions/` (`0001_contract_foundation.py`, `0003_human_authority.py`); `Database.create_all()` also creates tables directly at runtime.

## Generated contract schemas

`scripts/generate_schemas.py` emits one JSON Schema per contract into `schemas/generated/contracts/`, plus a combined catalog. These are generated from the frozen Pydantic models, never hand-edited. See [how-to-contribute: tooling](../how-to-contribute/tooling.md).

| Schema file | Contract |
| --- | --- |
| `study-revision-v1.json` | `StudyRevision` — the authoring root |
| `goal-revision-v1.json` | `GoalRevision` — the objective delivered to the Subject |
| `scenario-revision-v1.json` | `ScenarioRevision` — versioned inputs and conditions |
| `agent-inventory-revision-v1.json` | `AgentInventoryRevision` — required runner, provider, tools, skills |
| `workspace-template-revision-v1.json` | `WorkspaceTemplateRevision` — workspace shape |
| `interaction-protocol-revision-v1.json` | `InteractionProtocolRevision` — interaction shape |
| `evaluation-plan-revision-v1.json` | `EvaluationPlanRevision` — dimensions, stages, gates, disclosure |
| `checkpoint-policy-revision-v1.json` | `CheckpointPolicyRevision` — checkpoint definitions |
| `progress-artifact-policy-revision-v1.json` | `ProgressArtifactPolicyRevision` — progress artifact boundaries |
| `run-spec-v1.json` | `RunSpec` — the compiled atomic spec |
| `admission-record-v1.json` | `AdmissionRecord` — resolved inventory, workspace, capabilities |
| `subject-envelope-v1.json` | `SubjectEnvelope` — the allowlist view given to the Subject |
| `evaluation-record-v1.json` | `EvaluationRecord` — an anchored evaluation result |
| `evaluator-envelope-v1.json` | `EvaluatorEnvelope` — the view given to an evaluator |
| `checkpoint-record-v1.json` | `CheckpointRecord` — a validated milestone |
| `revision-decision-record-v1.json` | `RevisionDecisionRecord` — an accept/reject/supersede decision |
| `human-attestation-record-v1.json` | `HumanAttestationRecord` — verified-human evidence |
| `progress-artifact-content-v1.json` | `ProgressArtifactContent` — the summary content |
| `progress-artifact-record-v1.json` | `ProgressArtifactRecord` — the anchored progress record |
| `artifact-manifest-v1.json` | `ArtifactManifest` — the bundle's intentional artifact entries |
| `run-record-v1.json` | `RunRecord` — the attempt binding spec, admission, and events |
| `catalog-v1.json` | The discriminated union of every contract (input to the TS generator) |
| `run-event-payload-catalog-v1.json` | The union of `RunEventPayload` variants |

`schemas/generated/` also holds `openapi-v1.json` (the FastAPI OpenAPI document) and `experiment-manifest-v1.json` (the legacy manifest). The catalog is compiled into `apps/web/src/generated/contracts.ts` for the renderer.
