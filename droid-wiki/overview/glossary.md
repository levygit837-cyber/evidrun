# Glossary

The domain vocabulary Evidrun uses across contracts, code, and docs. The canonical source is `docs/product/glossary.md`; the terms below mirror it. Understanding the distinction between authoring contracts, compiled specs, and evidence records is the fastest way to read the codebase.

## Structure and authoring

- **Workspace** — the local boundary for data and future sync.
- **Project** — a set of related scenarios, experiments, and conversations.
- **Study** — the authoring root for a question, hypothesis, evaluation, diagnosis, or exploration; it can compile one Run or a matrix of Runs.
- **StudyIntent** — the lab's purpose and questions; not an automatic instruction to the Subject.
- **Goal** — the objective and limits delivered to the Subject; kept separate from evaluation.
- **Scenario** — versioned inputs, observable conditions, limitations, and provenance for a Run.
- **Variant** — a typed override on a blueprint; pre-Run variants are siblings.
- **Experiment Manifest v1** — a compatible legacy contract, importable into a Study.

## Compilation and admission

- **RunSpec** — the atomic, immutable, compiled configuration of a scenario, variant, and repetition.
- **AdmissionRecord** — the pre-queue decision with the inventory, workspace, and capabilities actually resolved.
- **Run** — an attempt bound to an exact RunSpec and AdmissionRecord.
- **Agent Inventory** — the runner, provider, tools, skills, and runtime requirements of a Run.
- **Resolved Agent Inventory** — a hashed snapshot of what admission actually resolved.

## Disclosure and the Subject

- **Subject Agent** — the system under test.
- **SubjectEnvelope** — the minimal, allowlist-compiled view given to the Subject, with no lab data or hidden grader.
- **Subject Evaluation Guidance** — minimal public disclosure materialized before the Run; not the full EvaluationPlan.
- **Lab Agent** — the control-plane agent that queries evidence and creates drafts (runtime not yet built).

## Context

- **Context Policy** — a rule for selection, ordering, truncation, or transformation.
- **Context Plan** — the candidates and decisions considered before assembly.
- **Context Snapshot** — the input actually delivered in one invocation.
- **Context Diff** — the classified difference between snapshots.
- **Context Mount** — an explicit inclusion of prior knowledge or a session.

## Evidence

- **Event** — an append-only observation of execution.
- **Artifact** — content identified by digest and metadata; an `ArtifactRef` has no storage locator and the reference grants no access.
- **Artifact Access Grant** — a future authorization, separate from identity, limiting consumer, purpose, operations, classification, and time.
- **Progress Artifact** — a provisional, derived, append-only summary anchored to a boundary; schemas exist but the runtime observer/persistence does not. Not a file inventory or a second source of truth.
- **Checkpoint** — a validated milestone anchored in the ledger; it does not mean restore or replay.
- **Evidence Bundle (audit)** — a verifiable package of records, refs, and digests; it does not promise every blob or replay.
- **Evidence Bundle (portable)** — a future profile with authorized blobs and a completeness manifest for declared offline use.

## Evaluation

- **EvaluationPlan** — dimensions, stages, gates, disclosure, blinding, and optional aggregation.
- **EvaluationRecord** — a vectorized, anchored, append-only result produced by a grader, judge, or human.
- **Grader** — a versioned evaluator that produces an EvaluationRecord; Grade is a legacy projection.
- **Human review** — primary human evaluation declared as a stage of the plan.
- **Human adjudication** — a later human decision about precedence between records, without overwrite.
- **Bounded exploration result** — a two-axis result: operational disposition and factual stop reason; neither is pass/fail or a score.
- **Comparison** — a paired reading of runs and their trade-offs.

## Authority

- **Human Attestation** — typed evidence of human verification covering the exact principal, action, and content; without a trusted adapter the operation fails closed.
- **Repository Fixture Authority** — imports acceptance of a legacy fixture through an internal path; explicitly non-human.
- **General chat** — a session with no entity scope, still bounded to the workspace.

See [primitives](../primitives/index.md) for how these concepts map to Pydantic models in `src/evidrun/contracts/`.
