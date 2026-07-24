# Runtime records

`src/evidrun/contracts/runtime.py` holds the contracts produced during and after compilation: the executable spec, the admission decision, the disclosure envelopes, the evaluation and checkpoint records, the terminal results, and the typed payloads for every Run event. These are the records that get persisted and later re-verified in an [evidence bundle](../evidence.md).

## Key abstractions

| Type | Description |
| --- | --- |
| `RunSpec` | The fully-resolved, immutable execution spec for one matrix cell. |
| `ResolutionReason` / `AdmissionIssue` | Structured reasons and blocking issues attached to an admission. |
| `ResolvedCapability` / `ResolvedAgentInventory` | The runtime's resolution of requested capabilities and provider. |
| `AdmissionRecord` | The admit/reject decision plus resolved inventory and issue lists. |
| `SubjectWorkspace` / `SubjectEvaluationDimension` / `SubjectEvaluationGuidance` | Reduced views embedded in the subject envelope. |
| `SubjectEnvelope` | The closed allowlist the Subject sees. |
| `EvaluatorEnvelope` | The per-stage view the evaluator sees. |
| `RunRecord` | Canonical record of one Run and its lineage. |
| `EvaluationBoundary` / `DimensionValue` / `EvaluationRecord` | An evaluation result anchored to the ledger. |
| `CheckpointValidation` / `CheckpointRecord` | A checkpoint anchored to the ledger. |
| `ProgressStatement` / `ProgressArtifactContent` / `ProgressArtifactRecord` | Progress summaries (not executable yet). |
| `GoalStateTerminalResult` / `BoundedExplorationTerminalResult` | The two terminal goal results. |
| Event payload models + `normalize_event_payload` | Typed payloads for each event type and the phase/status tables. |

## RunSpec

`RunSpec` is the output of `StudyCompiler._materialize`. It embeds both the reference and the resolved payload for each contract slot (`goal_ref` + `goal`, `scenario_ref` + `scenario`, and so on), the variant id and repetition index, the seed, budgets, stop conditions, capture policy, optional context policy, extensions, and merged limitations.

`validate_checkpoint_pair` enforces coherence: a checkpoint ref and payload must be present together (same for progress artifacts), a `bounded_exploration` goal needs a bounded terminal stop condition, at least one stop condition must exist, and every ref must sit in its correct `ContractType` slot. The `digest` computed field content-addresses the whole spec; this digest is what admission, the run.queued event, and the run record all reference.

## AdmissionRecord and resolution

`AdmissionRecord` records `decision` (`admitted`/`rejected`), the `ResolvedAgentInventory`, `workspace_status`, `interaction_status`, and the `missing_requirements`, `denied_policies`, `issues`, and `warnings` collections. Its `run_spec_ref` must be `run-spec:{digest}` — content-addressed by the spec digest.

`validate_decision` re-derives whether the record is blocked (any missing requirement, denied policy, non-resolved workspace or interaction status, blocking issue, or failed required capability) and refuses an admitted record that is actually blocked or a rejected record with no blocking reason. This means an `AdmissionRecord` cannot lie about its own decision.

`ResolvedCapability.validate_resolution` mirrors this at the capability level: a `resolved` capability must carry an exact ref, adapter, and interface version and no reason, while an unresolved one must carry a reason and expose no effective resolution. `ResolvedAgentInventory.validate_requirement_ref` enforces the all-or-nothing provider fields — an offline inventory carries no provider fields, a provider inventory carries all of them.

## Subject and evaluator envelopes

`SubjectEnvelope` and `EvaluatorEnvelope` are the persisted shapes of what the [compiler](compiler.md) builds. The subject envelope holds the goal, visible inputs, interaction protocol, effective (resolved) capabilities, reduced workspace, budgets, stop conditions, and optional `SubjectEvaluationGuidance`. `SubjectEvaluationGuidance` validates that its plan ref is an evaluation plan and that it carries public dimensions. Both envelopes expose a computed `digest`; the run executor records the subject envelope digest in the `subject.invoked` event.

## RunRecord

`RunRecord` is the canonical description of a Run: its id, run-spec and admission ids and digests, study and scenario refs, variant id, repetition index, and optional `retry_of`. `validate_lineage_and_refs` checks the refs' contract types and forbids a Run retrying itself. `validate_run_uuid7` requires Run ids to embed a UUIDv7 (after stripping the `run_` prefix), which keeps ids sortable by creation time. The [database](../database.md) builds this record on demand from the stored run row and its contracts.

## Evaluation records

An `EvaluationRecord` is a result anchored to a point in the ledger. `EvaluationBoundary` requires either an event boundary (both `up_to_event_sequence` and `event_hash`) or a `checkpoint_id`, never both and never neither. `DimensionValue` carries the scored value, a rationale, optional confidence, and at least one `EvidenceRef`.

`EvaluationRecord.validate_adjudication` is the largest validator in the module. It enforces the append-only, authority-honest rules:

- human evaluations (`human_reviewer`, `human_adjudicator`) must be `final` and carry a verified `HumanAttestationRecord`; automated ones may not claim human authority or a precedence relation;
- a `human_adjudicator` must carry an `adjudicates` relation, a `human_reviewer` an `independent_review` relation;
- a `model_judge` stays `provisional` and must declare provider and model; no other source may declare them;
- when human attestation is present, its action, target digest (the plan), subject digest (`human_subject_digest()`), and timestamp must all line up with the record content.

`AdjudicatesEvaluationRelation` and `IndependentHumanReviewRelation` (the `HumanEvaluationRelation` union) carry the unique target/considered record refs. See [evaluation and checkpoints](../../primitives/evaluation-and-checkpoints.md) and, for how these are produced, [authority](../authority.md).

## Checkpoint and progress records

`CheckpointRecord` anchors a checkpoint to an event sequence and hash, carries the definition id and digest, capture refs, validations, and a `replayability` level. `validate_checkpoint` requires the policy ref to be a checkpoint policy, unique validators, all validations passed, and replayability limitations when not `deterministic`. Its identity field is `checkpoint_hash`.

`ProgressArtifactContent` and `ProgressArtifactRecord` describe a progress summary and its persisted record; `ProgressStatement` requires evidence refs for observations and interpretations. These are not produced by the current runtime — admission rejects any progress policy — but the contracts and the bundle verifier support them.

## Terminal results

Every terminal event carries a discriminated `TerminalGoalResult`:

- `GoalStateTerminalResult` with a `state` of `achieved`, `partially_achieved`, `not_achieved`, or `not_assessable`;
- `BoundedExplorationTerminalResult` with a `disposition`, a `stop_reason`, the `stop_condition_kind`, and optional learning summary and evidence.

The active runner only emits `GoalStateTerminalResult`.

## Event payloads and the phase tables

Each Run event type maps to a typed payload in `EVENT_PAYLOAD_MODELS`. `normalize_event_payload(event_type, payload)` validates the payload against its model and returns the canonical dump; the [database](../database.md) calls it on every append and the [evidence](../evidence.md) verifier calls it on every stored event.

Two tables encode the phase rules:

- `EVENT_ALLOWED_RUN_STATUSES` maps an event type to the run statuses in which it is valid (for example `subject.responded` is only valid while `running`, `evaluation.completed` only while `evaluating`).
- `UNSUPPORTED_RUNTIME_EVENT_TYPES` is the reserved set (pause/resume, tool, skill, checkpoint, progress) that the runtime refuses to append until its coordinator exists.

Notable payloads:

| Payload | Notes |
| --- | --- |
| `RunQueuedPayload` | Carries the run-spec and admission digests, checked against the stored contracts. |
| `ContextComposedPayload` | Snapshot id, policy id, strategy, char counts, omission flag, content hash. |
| `SubjectInvokedPayload` | Runner, network mode, subject envelope digest, optional guidance digest. |
| `SubjectRespondedPayload` | `validate_capture_shape` enforces the exact shape per capture mode — `metadata` carries no output, `redacted` uses the `[REDACTED]` marker, `disabled` carries nothing, `raw_encrypted` uses only `artifact:` refs. |
| `RunTerminalPayload` | Status, `TerminalGoalResult`, terminal cause, and unique evaluation/checkpoint refs. Shared by all terminal event types. |

See [events](../../primitives/events.md) for the ledger-level view.

## Entry points for modification

- A new event type needs a payload model, an `EVENT_PAYLOAD_MODELS` entry, and (usually) an `EVENT_ALLOWED_RUN_STATUSES` entry; if the runtime cannot emit it yet, add it to `UNSUPPORTED_RUNTIME_EVENT_TYPES`.
- Changing a record's fields changes its digest and can break stored-digest verification in the [database](../database.md) and [evidence](../evidence.md) systems.
- Evaluation append-only rules live in `validate_adjudication` here and in `EvaluationValidator` (`src/evidrun/contracts/evaluation.py`); keep them consistent.
