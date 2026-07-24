# Background

This section records why Evidrun is built the way it is. Decisions are captured as Architecture Decision Records (ADRs) under `docs/adr/`. ADRs are normative: an accepted ADR is never rewritten to change a decision. When a decision changes, a successor ADR supersedes it, and both records stay in the history. ADR 0013 superseding ADR 0012 is the worked example. See [how to contribute](../how-to-contribute/index.md) for the documentation-as-source-of-truth rule.

## The product charter

`docs/product/charter.md` frames the whole project.

- **Problem.** Prompt, context, memory, and tool changes are usually justified by intuition or a single lucky example. Without controlling variables and preserving evidence, you cannot tell whether a change helped, which change caused the effect, or whether the result holds.
- **Proposal.** Turn hypotheses about agents into versioned experiments, auditable runs, comparisons, and reports that make gains, losses, and uncertainty visible.
- **Principles.** Benchmark-first; local-first; evidence before narrative; one primary variable per causal comparison; deterministic graders before judges; delivered context is a verifiable object; a negative result is useful information; no dependence on private chain-of-thought; the human keeps authority over acceptance, sensitive access, and external effects.
- **Non-goals.** Not a multi-tenant SaaS, not a prompt marketplace, not a universal model leaderboard, not unrestricted shell execution, not automatic global memory, not a replacement for existing agent frameworks.

## The ADRs

| ADR | Title | Status | One line |
| --- | --- | --- | --- |
| [0001](../../docs/adr/0001-benchmark-first-and-local-first.md) | Benchmark-first and local-first | accepted | Start from auditable benchmarks and local storage; cloud and sync are future adapters. |
| [0002](../../docs/adr/0002-control-plane-and-execution-plane.md) | Control plane and execution plane | accepted | Lab Agent in the control plane, Subject Agent in the execution plane; no master agent with implicit access. |
| [0003](../../docs/adr/0003-modular-monolith.md) | Modular monolith by capability | accepted | One Python package, one API, one worker, one CLI; no microservices, Redis, Kafka, or Kubernetes in the MVP. |
| [0004](../../docs/adr/0004-python-core-typescript-ui-and-electron.md) | Python core, TypeScript UI, Electron | accepted | Python for domain and backend, React/TS for UI, Electron for the desktop shell running the backend as a loopback sidecar. |
| [0005](../../docs/adr/0005-canonical-evidence-storage.md) | SQLite and event ledger as canonical evidence | accepted | SQLite is canonical for state and events; the append-only, hash-chained ledger is the source of truth; JSONL lives only in bundles. |
| [0006](../../docs/adr/0006-provider-neutral-openai-first.md) | Provider-neutral core, OpenAI first | accepted | Provider types stay in adapters behind ports; the first real runner uses the Responses API. |
| [0007](../../docs/adr/0007-repository-docs-source-of-truth.md) | Repository as the documentation source | accepted | Contracts, ADRs, and current architecture live in Git; frontmatter is validated; ADRs are superseded, not rewritten. |
| [0008](../../docs/adr/0008-cliproxyapi-deepseek-default.md) | CLIProxyAPI + DeepSeek v4 Flash default | accepted | The durable default provider is `cliproxyapi-local` with `deepseek-v4-flash` and `reasoning=max`; keys stay in the Keychain. |
| [0009](../../docs/adr/0009-study-run-contract-composition.md) | Unified Study and canonical Run composition | accepted | `StudyRevision` is the authoring root; it expands into atomic `RunSpec`s; a Run is spec + admission + record + events, not a mutable document. |
| [0010](../../docs/adr/0010-verifiable-human-authority.md) | Verifiable human authority | accepted | A human action counts only when bound to an authenticated principal and explicit confirmation; without a trusted verifier, fail closed. |
| [0011](../../docs/adr/0011-progress-artifacts-and-bundle-boundaries.md) | Progress artifacts and bundle boundaries | accepted | `ArtifactRef` identity is not access; progress artifacts are derived summaries; audit / portable / replay are distinct bundle guarantees. |
| [0012](../../docs/adr/0012-subject-disclosure-and-terminal-semantics.md) | Subject disclosure and terminal semantics | superseded | The `SubjectEnvelope` is a closed allowlist; lifecycle, goal state, and quality are separate axes. Its bounded-exploration taxonomy was superseded by 0013. |
| [0013](../../docs/adr/0013-bounded-exploration-terminal-semantics.md) | Bounded exploration terminal semantics | accepted | Bounded exploration ends on two independent axes: operational `disposition` and factual `stop_reason`, never pass/fail. Supersedes 0012's taxonomy only. |
| [0015](../../docs/adr/0015-human-subject-envelope-and-authenticator-lifecycle.md) | HumanSubjectEnvelope and authenticator lifecycle | accepted | Closes ADR 0010's open items: a versioned signed envelope, a local software authenticator (ES256), and an opt-in `EVIDRUN_AUTHORITY` flag. |

There is no ADR 0014; the sequence jumps from 0013 to 0015.

## Read next

- [Design decisions](design-decisions.md) — the rationale behind each ADR and how they build on one another.
- [Pitfalls](pitfalls.md) — the danger zones that follow from these decisions.
