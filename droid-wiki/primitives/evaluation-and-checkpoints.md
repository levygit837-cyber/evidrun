# Evaluation and checkpoints

Evaluation records are how a Run's results become evidence: vectorized, anchored to a point in the ledger, and append-only. Checkpoints are validated milestones anchored the same way. Both are declared by authoring policies and produced (or, mostly, reserved) at runtime. This page covers the concepts; for field-level detail see [runtime records](../systems/contracts/runtime.md).

## Evaluation: plan and record

An `EvaluationPlanRevision` declares typed dimensions, ordered stages, triggers, hard gates, disclosure, blinding, optional aggregation, and human adjudication. Without an aggregation projector, the official result stays a vector of dimensions, gates, and uncertainties — there is no implicit global score. Cost, latency, and constraint trade-offs are never hidden inside a single number.

An `EvaluationRecord` is the anchored result. It fixes the Run, the plan revision and digest, the effective evaluator, a verifiable boundary, the dimension values, the gate, rationale, confidence, evidence refs, and status. Its `source_type` discriminates four kinds:

- `deterministic_grader` — automated, final, no human authority.
- `model_judge` — provisional, must declare provider and model.
- `human_reviewer` — a primary human evaluation; final; carries an `independent_review` relation.
- `human_adjudicator` — a precedence decision over existing records; final; carries an `adjudicates` relation with explicit targets.

Human review and adjudication are distinct: review is a planned stage that produces a primary human evaluation and need not supersede anything; adjudication is a later append-only decision about which record prevails, referencing the records it judges without overwriting them. Both require a validated `HumanAttestationRecord` — see [human authority](../features/human-authority.md).

## Boundaries, dimensions, and gates

An `EvaluationBoundary` anchors a record to the ledger: either an event boundary (both `up_to_event_sequence` and `event_hash`) or a `checkpoint_id`, never both and never neither. A `DimensionValue` carries the scored value, a rationale, optional confidence, and at least one `EvidenceRef` (`run:`, `event:`, or `artifact:`). A hard gate that fails prevents later stages when the plan orders them that way.

## Checkpoints

A `CheckpointRecord` anchors a validated milestone to an event sequence and hash. It carries the definition id and digest, capture refs, validations, and a `replayability` level, and its identity field is `checkpoint_hash`. A record is persisted only after every validator passes and the repository confirms the sequence and hash belong to the Run. A checkpoint is auditable evidence that a milestone was reached — it does not mean restore, replay, context extraction, or executable fork, and those are not implemented.

## Bounded exploration terminals

A terminal event carries a discriminated `TerminalGoalResult`. `GoalStateTerminalResult` uses a `state` (`achieved`, `partially_achieved`, `not_achieved`, `not_assessable`). `BoundedExplorationTerminalResult` is two-axis: an operational `disposition` and a factual `stop_reason`, plus the stop condition kind and optional learning summary and evidence. Neither axis is pass/fail or a score; lifecycle, goal conclusion, and quality stay separate. The active runner emits only `GoalStateTerminalResult`.

## The model at a glance

| Type | Role |
| --- | --- |
| `EvaluationPlanSpec` | Authoring contract: dimensions, stages, disclosure, blinding, adjudication policy. |
| `EvaluationRecord` | Anchored, append-only result; `source_type` selects the kind. |
| `EvaluationBoundary` | Event boundary or checkpoint id — exactly one. |
| `DimensionValue` | Scored value + rationale + confidence + evidence refs. |
| `HumanEvaluationRelation` | `AdjudicatesEvaluationRelation` or `IndependentHumanReviewRelation`. |
| `CheckpointPolicySpec` / `CheckpointRecord` | Checkpoint definitions and the anchored, validated record. |
| `GoalStateTerminalResult` / `BoundedExplorationTerminalResult` | The two terminal goal results. |

## Invariants

- **Anchored.** Every record ties to a verifiable ledger boundary; `run:` and `event:` refs are checked against the Run and its authorized boundary on persistence.
- **Append-only.** Evaluation records, reviews, and adjudications never overwrite a prior record; a correction is a new record.
- **Authority honest.** Human evaluations must be `final` and carry a verified attestation; automated ones may not claim human authority or a precedence relation. A `model_judge` stays `provisional`.
- **Exact completion link.** `evaluation.completed` must point at the exact persisted record (same run, digest, gate) with no duplicate conclusion; `run.completed` must cover the stages the plan still requires after hard gates.
- **Checkpoint validity.** A `CheckpointRecord` is persisted only after all validators pass and the boundary is confirmed; a trigger or validation failure must be an event, not a partial record.

## Current limits

The evaluation runtime is narrow: it admits exactly one deterministic boolean grader, triggered by `subject.responded`, with an `expected` parameter. Any other set of stages, triggers, or dimensions is a valid contract but rejected at admission as `runtime:evaluation_pipeline`. Model judges, multiple stages, non-`none` disclosure, and required human adjudication are all rejected. The checkpoint coordinator does not exist, so any `CheckpointPolicyRevision` is rejected as `runtime:checkpoint_coordinator`; what is implemented is the contract and the persistence-time validation of an already-produced record. `artifact:` evidence refs are validated only by scheme today — lookup, classification, and authorization against the artifact manifest are not yet integrated.

## Where it appears in code

| File | Role |
| --- | --- |
| `src/evidrun/contracts/runtime.py` | `EvaluationRecord`, `EvaluationBoundary`, `DimensionValue`, `CheckpointRecord`, terminal results; `validate_adjudication`. |
| `src/evidrun/contracts/evaluation.py` | `EvaluationValidator` — gate results, stage visibility, human-relation boundary. |
| `src/evidrun/contracts/authoring.py` | `EvaluationPlanSpec`, `CheckpointPolicySpec`, and their nested types. |
| `src/evidrun/evaluations/deterministic.py` | `ExactCauseGrader` — the one executable grader. |
| `docs/contracts/evaluation-checkpoint-v1.md` | The normative contract description. |

## Cross-links

- [Runtime records](../systems/contracts/runtime.md) — the full field-level view and `validate_adjudication`.
- [Authority](../systems/authority.md) — how human review and adjudication are produced and verified.
- [Events](events.md) — the boundaries evaluation and checkpoints anchor to.
- [Human authority](../features/human-authority.md) — the review-versus-adjudication policy.
