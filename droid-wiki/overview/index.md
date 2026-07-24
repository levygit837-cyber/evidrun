# Evidrun

> **Historical generated snapshot.** These pages were generated on 2026-07-23 from commit
> `101087964cb2361977085e9f62afd75d1dc58f6d`. They preserve that repository view and are not the
> source of truth for current capabilities. Start with `docs/index.md` on the current `main` before
> relying on implementation claims.

Evidrun is a local-first, auditable laboratory for testing how context, tools, policies, and environments change the behavior of AI agents. It treats a single answer as insufficient evidence. Every comparison records the variable that changed, the context that was actually delivered, the event trail, the graders, the gains, the losses, and the limits of the conclusion.

The repository is a modular monolith: a Python domain core with a CLI, a FastAPI backend, a local worker, a React renderer, and an Electron desktop shell. The reference benchmark `CRL-CTX-002` runs fully offline and deterministically, which proves the infrastructure works without measuring any language model's capability.

## What the project does

Prompt, context, memory, and tool changes are usually justified by intuition or a single lucky example. Without controlling variables and preserving evidence, you cannot tell whether a change helped, which change caused the effect, or whether the result holds. Evidrun turns hypotheses about agents into versioned experiments, auditable runs, paired comparisons, and reports that make gains, losses, and uncertainty visible.

The canonical flow is contract-first:

```text
accepted revisions → Study compiles RunSpecs → admission resolves capabilities → Run → event ledger
                                                       ↘ evaluations and checkpoints anchored to the ledger
```

Revisions, specs, and admissions are immutable. Checkpoints and evaluations anchor to a ledger sequence and hash. Run status, comparisons, grades, reports, and graphs are all projections derived from the event ledger, which is the normative source of truth.

## Who uses it

Developers and researchers who want to evaluate their own context and agent hypotheses in a local, inspectable, reproducible environment. Evidrun is deliberately not a multi-tenant SaaS, a prompt marketplace, a universal model leaderboard, or a replacement for existing agent frameworks. See the [charter](../background/index.md) for the full list of non-goals.

## The runtime is smaller than the contracts, on purpose

Evidrun models a large surface of contracts (tools, skills, nested agents, graph protocols, checkpoints, progress artifacts, bounded exploration, human adjudication) but the executable runtime is intentionally narrower. Today it supports:

- a deterministic scripted subject runner,
- `single_turn` interaction,
- `in_process` workspace,
- `max_wall_seconds` as the only budget,
- a single deterministic grader stage.

Anything beyond that is representable and compilable but rejected at admission. Admission fails closed: a contract being typable does not announce it as executable. This boundary is the single most important thing to understand before working in this codebase. See [admission and capability resolution](../features/study-to-run-lifecycle.md) for details.

## Quick links

- [Architecture](architecture.md) — the three planes and how data flows through them
- [Getting started](getting-started.md) — prerequisites, install, build, test, run
- [Glossary](glossary.md) — the domain vocabulary (Study, RunSpec, SubjectEnvelope, and more)
- [Study to Run lifecycle](../features/study-to-run-lifecycle.md) — the canonical contract-to-evidence flow
- [Contracts and compilation](../systems/contracts/index.md) — the immutable authoring and runtime model
- [Evidence and the event ledger](../systems/evidence.md) — how runs become verifiable evidence
- [How to contribute](../how-to-contribute/index.md) — workflow, testing, and the mandatory verification suite

## Documentation authority

The repository is the normative source. Inside `docs/`, accepted ADRs and contracts are normative, architecture describes the current state, research is temporal, and roadmap is future intent. Reports are projections generated from evidence and are never maintained by hand. This wiki summarizes that material for navigation; when the two disagree, the files under `docs/` and the code win.
