# RunSpec and admission

A `RunSpec` is the atomic, immutable, fully-resolved configuration for one cell of a Study's run matrix. An `AdmissionRecord` is the pre-queue decision that says whether the active runtime can run that spec exactly as written. A `Run` is an attempt bound to one exact RunSpec and one exact AdmissionRecord. Together they are the boundary between authoring intent and execution.

## The concept

`StudyCompiler` expands an accepted Study into one RunSpec per `(scenario, variant, repetition)` combination. Each RunSpec embeds both the reference and the resolved payload for every contract slot, so its digest content-addresses the entire execution configuration — change any input and you get a different spec. A RunSpec is a compile-time artifact; it does not decide whether it can actually run.

That decision is admission. `AdmissionService.admit(spec)` checks the spec against the runtime's registered capabilities and allowed modes and returns an `AdmissionRecord` with `decision=admitted` or `decision=rejected`. Admission is the fail-closed gate: the contracts can express far more than the runtime executes, and this is where the gap is enforced. No Run exists before an `AdmissionRecord` with `decision=admitted` for the exact RunSpec digest.

## The model

`RunSpec` (`src/evidrun/contracts/runtime.py`) — key fields:

| Field | Notes |
| --- | --- |
| `goal_ref` + `goal`, `scenario_ref` + `scenario`, etc. | Ref plus resolved payload for each contract slot. |
| `variant_id`, `repetition_index` | Which matrix cell this spec is. |
| `seed` | From the Study's seed strategy. |
| `budgets` | `BudgetSpec`; only `max_wall_seconds` (and `max_turns` of 1) is admitted. |
| `stop_conditions` | At least one; only terminal `goal_complete`/`budget_exhausted` admitted. |
| `capture_policy` | `default_mode` for what the ledger stores. |
| `context_policy` | Optional; present for context-driven specs like the benchmark. |
| `extensions`, `limitations` | Typed extension slots and merged limitations. |
| `digest` | Computed; referenced by admission, `run.queued`, and the run record. |

`AdmissionRecord` (`src/evidrun/contracts/runtime.py`) — key fields:

| Field | Notes |
| --- | --- |
| `decision` | `admitted` or `rejected`. |
| `run_spec_ref` | Must be `run-spec:{digest}` — content-addressed by the spec. |
| `resolved_inventory` | `ResolvedAgentInventory` — what admission actually resolved. |
| `workspace_status`, `interaction_status` | Resolution status per area. |
| `missing_requirements`, `denied_policies`, `issues`, `warnings` | Blocking reasons plus non-blocking warnings. |

`AdmissionIssue` carries a `category`, `subject_ref`, and a `ResolutionReason` code (`unsupported`, `denied`, `unavailable`, `digest_mismatch`).

## Invariants

- **Content-addressed and immutable.** A RunSpec's digest covers the whole spec; admission and every event reference that digest.
- **Coherent spec.** `RunSpec.validate_checkpoint_pair` requires a checkpoint ref and payload together (same for progress artifacts), a bounded terminal stop condition for a `bounded_exploration` goal, at least one stop condition, and every ref in its correct `ContractType` slot.
- **Admission cannot lie.** `AdmissionRecord.validate_decision` re-derives whether the record is blocked (any missing requirement, denied policy, unresolved status, blocking issue, or failed required capability) and refuses an `admitted` record that is actually blocked or a `rejected` record with no blocking reason.
- **Resolution honesty.** A `resolved` capability must carry an exact ref, adapter, and interface version and no reason; an unresolved one must carry a reason and expose no effective resolution. A provider inventory carries all provider fields or none.
- **Fail closed.** Admission rejects everything the runtime cannot honor exactly: non-`single_turn` interaction, non-`in_process` workspace, `sensitive`/`restricted` inputs, disclosure other than `none`, `raw_encrypted` capture, any tool/skill/checkpoint/progress policy, `bounded_exploration`, any evaluation shape other than one deterministic boolean grader, required human adjudication, and any budget beyond wall-clock. See the [admission checks table](../systems/contracts/compiler.md).

## Where it appears in code

| File | Role |
| --- | --- |
| `src/evidrun/contracts/compiler.py` | `StudyCompiler._materialize` builds RunSpecs; `AdmissionService.admit` decides them. |
| `src/evidrun/contracts/runtime.py` | `RunSpec`, `AdmissionRecord`, `AdmissionIssue`, `ResolvedCapability`, `ResolvedAgentInventory`, `RunRecord`. |
| `src/evidrun/runs/service.py` | `_execute_spec` requires an admitted record before creating a Run. |
| `src/evidrun/infrastructure/database/repository.py` | Persists specs, admissions, and runs; re-verifies digests. |

## Cross-links

- [Compilation and admission](../systems/contracts/compiler.md) — the full compiler and the complete admission-checks table.
- [Runtime records](../systems/contracts/runtime.md) — every runtime record's fields and validators.
- [Study to Run lifecycle](../features/study-to-run-lifecycle.md) — where these sit in the end-to-end flow.
- [Events](events.md) — what an admitted spec produces when it runs.
