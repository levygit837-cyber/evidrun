# Authoring revisions

`src/evidrun/contracts/authoring.py` defines the nine contract kinds a human authors and accepts. Each is an immutable `RevisionEnvelope` subtype with a `contract_type` literal and a typed `payload`. Together they describe what a Study is, what the Subject must do, the environment and interaction shape, how results are evaluated, and how the run matrix expands into individual runs.

None of these models execute anything. They are the input to the [compiler](compiler.md), which resolves them into RunSpecs.

## The nine revision types

| Revision | `payload` type | What it describes |
| --- | --- | --- |
| `StudyRevision` | `StudySpec` | The whole experiment: intent, evidence mode, goal, scenarios, run blueprint, variants, repetitions, comparisons. |
| `GoalRevision` | `GoalSpec` | The objective the Subject pursues, in `goal_state` or `bounded_exploration` mode. |
| `ScenarioRevision` | `ScenarioSpec` | The situation and its input bindings. |
| `AgentInventoryRevision` | `AgentInventorySpec` | The Subject runner, optional provider profile, and requested capabilities. |
| `WorkspaceTemplateRevision` | `WorkspaceTemplateSpec` | The runtime environment, mounts, network and effect policies. |
| `InteractionProtocolRevision` | `InteractionProtocolSpec` | Single-turn or graph interaction shape. |
| `EvaluationPlanRevision` | `EvaluationPlanSpec` | Dimensions, stages, disclosure, blinding, adjudication. |
| `CheckpointPolicyRevision` | `CheckpointPolicySpec` | Checkpoint definitions and capture. |
| `ProgressArtifactPolicyRevision` | `ProgressArtifactPolicySpec` | Progress summary definitions and triggers. |

All nine are collected in the `AuthoringRevision` discriminated union (keyed on `contract_type`) and in the `REVISION_MODELS` lookup used by `parse_revision`.

## Study

`StudySpec` is the top of the tree. It holds a `StudyIntent` (purpose, questions, optional hypothesis, scope, assumptions), an `EvidenceMode`, a single `goal_ref`, one or more `scenario_refs`, a `RunBlueprint`, a tuple of `VariantSpec` (defaulting to a single `default` variant), a repetition count, a `SeedStrategy`, and optional `ComparisonPlan`s.

`validate_matrix` enforces the rules that make a Study coherent:

- at least one scenario, all refs unique and of the right `ContractType`;
- variant ids unique;
- scenario overrides are forbidden when the matrix already has multiple scenarios (they would be ambiguous);
- every comparison references known variants;
- a `prospective_controlled` study must declare at least one comparison;
- variant `confounders` are only allowed in `exploratory` studies.

`StudyIntent` and its `IntentScope` (which forbids the same boundary being both included and excluded) capture why the Study exists. See [contracts and revisions](../../primitives/contracts-and-revisions.md).

## Goal

`GoalSpec` has a `mode` of `goal_state` or `bounded_exploration`, an `instruction`, and optional outcomes, learning targets, constraints, evidence expectations, and completion observations. `validate_goal_shape` requires unique outcome and constraint ids, at least one outcome for `goal_state`, and at least one learning target or outcome for `bounded_exploration`. `GoalConstraint.rule` is `must` or `must_not`.

Only `goal_state` runs are executable today; `bounded_exploration` is rejected at admission because the active runner emits only goal-state terminal results.

## Scenario and input bindings

`ScenarioSpec` carries a description, a required non-empty tuple of `InputBinding`s (unique ids), and optional observable conditions, limitations, and provenance.

An `InputBinding` is the unit of what the Subject or evaluator can see:

```python
class InputBinding(ContractModel):
    id: NonEmptyStr
    role: NonEmptyStr
    source: ArtifactRef
    visibility: Literal["subject", "evaluator", "laboratory", "subject_and_evaluator"]
    mount_access: Literal["read_only", "read_write"] = "read_only"
    mount_name: NonEmptyStr | None = None
```

Visibility drives disclosure: the [subject envelope compiler](compiler.md) only exposes `subject` and `subject_and_evaluator` bindings to the Subject, and the evaluator envelope only exposes `evaluator` and `subject_and_evaluator` bindings.

## Agent inventory

`AgentInventorySpec` names the `runner_ref` (a `CapabilityDescriptorRef`), an optional `provider_profile_id`, and tuples of `CapabilityRequirement` and `RuntimeRequirement`. Each `CapabilityRequirement` is a `tool` or `skill` with an interface version, requested permissions, an `exposure` (`schema_only`, `instructions`, or `instructions_and_schema`), instruction refs, and authority constraints. `validate_capability_keys` requires unique capability keys.

Admission resolves each requirement against the runtime catalog; any required capability that is unregistered, permission-escalating, or authority-short is a blocking failure.

## Workspace template

`WorkspaceTemplateSpec` describes the environment: a `runtime_kind`, an `ephemeral_per_run` lifecycle, mounts, write zones, a `NetworkPolicy`, an `ExternalEffectPolicy`, secret binding refs, a `SnapshotPolicy`, and a `CleanupPolicy`. The nested policies each validate their own allowlist/mode coherence (for example, `allowlist` network mode requires endpoint refs, and `retain_until_ttl` cleanup requires a TTL). `SecretBindingRef` restricts its `binding_id` to a lowercase pattern and a `keychain` or `environment` source.

The active runtime only admits `in_process` runtime kind with read-only mounts that exactly match a subject-visible scenario input, no write zones, no secrets, no snapshots, and `discard` cleanup. Anything else is rejected.

## Interaction protocol

`InteractionProtocolSpec` is `single_turn` or `graph`. Graph mode uses `InteractionNode`s and `InteractionEdge`s with typed `InteractionTrigger`s (`always`, `event`, `checkpoint_reached`, `evaluator_signal`, `human_signal`, `predicate`). `validate_graph` forbids nodes/edges in `single_turn` mode, requires unique node ids in `graph` mode, and checks that edges reference known nodes.

The runtime admits only `single_turn` with `max_turns == 1`, no system prompt ref, and no initial message refs. Graph protocols compile but are rejected at admission.

## Evaluation plan

`EvaluationPlanSpec` is the richest authoring contract. It holds `EvaluationDimension`s, `EvaluationStage`s, an `EvaluationDisclosure`, a `BlindingPolicy`, an optional `AggregationSpec`, and a `HumanAdjudicationPolicy`.

- `EvaluationDimension`: `boolean`, `number`, or `category`, with optional numeric min/max and anchors. Only numeric dimensions may declare a scale.
- `EvaluationStage`: an `integrity`, `deterministic_grader`, `model_judge`, or `human_review` kind, an evaluator ref, an `EvaluationTrigger` (`run_terminal`, `checkpoint`, or `event`), output dimensions, a `hard_gate` flag, and parameters.
- `SubjectEvaluationDisclosure`: `none`, `pre_run`, `on_request`, or `post_run`. `none` cannot expose any guidance; any enabled mode requires public dimension ids.
- `HumanAdjudicationPolicy`: if `required`, it needs an adjudicator ref, adjudicable stages, and an attestation verifier ref; optional adjudication authority is not supported in v1.

`validate_evaluation_plan` requires at least one dimension and stage, unique ids, and that stages, disclosure, and adjudication only reference known dimensions and stages.

Admission accepts exactly one shape: a single `deterministic_grader` stage triggered by an `event` on `subject.responded`, producing one boolean dimension, with an `expected` parameter. Everything else (model judge, multiple stages, required adjudication, non-`none` disclosure) is rejected. See [evaluation and checkpoints](../../primitives/evaluation-and-checkpoints.md).

## Checkpoint and progress-artifact policies

`CheckpointPolicySpec` holds `CheckpointDefinition`s with unique ids and orders. Each definition has a typed `CheckpointTrigger` (`manual`, `event`, `protocol_node`, `predicate`), validator refs, and a `CheckpointCaptureSpec` selecting what to snapshot. `ProgressArtifactPolicySpec` holds `ProgressArtifactDefinition`s with a `checkpoint_reached` or `subject_turn_interval` trigger, a summarizer ref, fixed authority constraints, and a max output length. Progress artifacts count `subject.responded` events as turns.

Both are compilable but rejected at admission: the checkpoint coordinator and the background progress observer do not exist yet.

## Run blueprint, variants, and overrides

`RunBlueprint` is the reusable execution recipe inside a Study: the four required contract refs (agent inventory, workspace, interaction protocol, evaluation plan), optional checkpoint and progress refs, an optional `ContextPolicySpec`, `BudgetSpec` budgets, a required tuple of `StopCondition`s, a `CapturePolicySpec`, and extensions. `validate_stops` requires at least one stop condition and checks every ref sits in its correct slot.

`VariantSpec` gives each matrix cell an id, label, `VariantOverrides`, optional confounders, and notes. `VariantOverrides` can replace any slot; `validate_ref_slots` checks each override ref matches its contract type. The compiler applies overrides on top of the blueprint per variant.

Supporting types:

| Type | Purpose |
| --- | --- |
| `BudgetSpec` | `max_wall_seconds` plus optional turn/token/tool/cost caps. Only wall time (and `max_turns` of 1) is admitted. |
| `StopCondition` | A terminal or pause condition; `predicate` kind needs a predicate ref. Only terminal `goal_complete`/`budget_exhausted` are admitted. |
| `CapturePolicySpec` | `default_mode` of `metadata`, `redacted`, `raw_encrypted`, or `disabled`; `raw_encrypted` is rejected at admission. |
| `ComparisonPlan` | Baseline vs candidate variant and the primary variable (a typed slot or `extension:` prefix). |
| `SeedStrategy` | `deterministic`, `fixed`, or `per_repetition`. |
| `VARIANT_SLOTS` | The frozen set of comparable slot names used by `ComparisonPlan` and the compiler's differ. |

## parse_revision

`parse_revision(document)` is the entry point for turning a stored or received JSON document back into a typed revision. It reads `contract_type`, looks up the model in `REVISION_MODELS`, and validates. The [database](../database.md) and [evidence](../evidence.md) systems use it to rehydrate contracts and recompute digests.

```python
def parse_revision(document: object) -> RevisionEnvelope:
    contract_type = ContractType(str(document.get("contract_type")))
    return REVISION_MODELS[contract_type].model_validate(document)
```

## Entry points for modification

- New authoring field: add it to the spec, keep the validators consistent, and remember the digest changes.
- New contract kind: add a `ContractType` member, a revision subtype, an entry in `REVISION_MODELS` and `AuthoringRevision`, and slot handling in the [compiler](compiler.md).
- Making an authored-but-rejected feature run: the gate is in [admission](compiler.md), not here.
