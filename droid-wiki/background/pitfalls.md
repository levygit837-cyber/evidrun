# Pitfalls

These are the danger zones in Evidrun: the places where the code compiles, the types check, and a reviewer still catches a broken invariant. They come from the invariants in `AGENTS.md` and the accepted ADRs. Read [design decisions](design-decisions.md) for the rationale behind each.

## The runtime is smaller than the contracts

The single most important thing to understand. Evidrun models a large surface of contracts (tools, skills, nested agents, graph protocols, checkpoints, progress artifacts, model judges, human adjudication, bounded exploration, non-`none` disclosure, token/cost budgets). The executable runtime is much narrower: a deterministic scripted subject runner, `single_turn` interaction, `in_process` workspace, `max_wall_seconds` as the only budget, and one deterministic grader. Everything else is representable and compilable but rejected at admission. A capability being typable does not make it executable. When you add runtime support, remove the corresponding closed gate deliberately and add a test proving the new path is admitted. See [systems: contracts compiler and admission](../systems/contracts/compiler.md).

## Fail closed, everywhere

Capabilities that are representable but not executable are rejected at admission, not silently ignored. The admission service and repository refuse non-`single_turn` interaction, budgets beyond `max_wall_seconds`, disclosure other than `none`, reserved events, sensitive or restricted inputs, and human decisions without a trusted verifier. Every rejection is a specific entry in `missing_requirements`, `denied_policies`, or a blocking `AdmissionIssue`. Do not "helpfully" degrade a missing control into a permissive default; absence of a control is a rejection, not a downgrade.

## Never treat an actor field as proof of authority

An agent, automation, or service must never claim to be human, fill a decision on the human's behalf, or turn an actor field into proof of authority. `actor_type=human` without a verified binding is only `human_asserted`. Verified human authority requires a `HumanAttestationRecord` bound to an authenticated principal and explicit confirmation. Without a trusted adapter, the API, CLI, and repository fail closed. `repository_fixture` is explicitly non-human and enters only through the dedicated import of the complete canonical `CRL-CTX-002` package. Agents may create drafts and approval requests, nothing more. See [systems: authority](../systems/authority.md).

## ArtifactRef has no locator; do not reintroduce storage paths into envelopes

`ArtifactRef` identifies content by id, digest, media type, and classification. It has no `locator` in any contract, and it grants no access, mount, export, or read. Do not reintroduce a path, URL, or storage locator into `SubjectEnvelope`, `EvaluatorEnvelope`, `ResolvedAgentInventory`, or bundles. Possession of a ref is never authorization; access needs a separate grant that does not exist yet. See [security: privacy and retention](../security/privacy-and-retention.md).

## Event phase gating

A factual event is accepted only in the valid phase for the Run and only with its canonical record linked. Subject invocations and responses are paired; evaluation only starts after a response; `evaluation.completed` must point to the exact `EvaluationRecord`; `run.completed` requires the records and stages the plan demands. Events for pause/resume, tools, skills, checkpoints, and progress artifacts stay reserved and are rejected until their coordinators exist. Do not emit a reserved event to "reserve a slot"; the repository rejects it.

## Append-only records; corrections create new records

`EvaluationRecord`s, reviews, and adjudications are append-only. A correction creates a new record; it never mutates or overwrites an existing one. Adjudication references the records it judges and declares precedence without erasing them. The same holds for progress artifacts: a correction is a new artifact or an append-only adjudication, never an in-place edit. This is what keeps historical divergence auditable.

## The SubjectEnvelope allowlist does not auto-flow new fields

The `SubjectEnvelope` is a closed allowlist compiled from specific sources, not a denylist over a serialized RunSpec. A new field on a RunSpec, contract, artifact, or evaluation does not automatically enter the envelope. If you add a field the Subject should see, you must add it to the allowlist compiler and its digest deliberately, with negative tests proving hidden fields (Intent, hypothesis, other variants, hidden inputs, calibration, expected answers, evaluator identity, chats, credentials, locators) still do not leak. `visible_to_subject=true` alone does not materialize content; the compiler must produce the exact public object and its digest.

## Disclosure other than none is rejected

`pre_run` evaluation guidance is still compilable into the pure `SubjectEnvelope`, but the active runner receives only objective and context, so admission rejects every disclosure mode other than `none` (including `pre_run`) as `runtime:subject_evaluation_guidance_delivery`. Do not assume that because guidance compiles it will be delivered.

## Timeout is a terminal budget event, not a completion

A `max_wall_seconds` timeout terminates the Run via `run.budget_exhausted`. Do not convert it into `completed`, and do not omit the terminal event. Lifecycle, goal state, and quality are separate axes; reaching a limit is never achievement. For bounded exploration, `disposition` and `stop_reason` are independent, and neither is pass/fail.

## Docs are a checked artifact

Do not describe roadmap as implemented behavior, and do not write run outcomes into docs without `run:`, `event:`, or `artifact:` references. Accepted ADRs are superseded by new ADRs, never rewritten. `scripts/validate_docs.py` and the `docs/_generated` diff in CI will catch a stale manifest or a broken reference, but they cannot catch a claim that overstates what the runtime does. See [how to contribute](../how-to-contribute/index.md).
