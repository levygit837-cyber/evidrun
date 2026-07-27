# Design decisions

This page explains the key architectural decisions and why they were made. Each maps to an ADR under `docs/adr/`. Read [background](index.md) for the one-line index and status of every ADR.

## Benchmark-first and local-first (0001)

Context hypotheses need to be tested with low friction and without shipping raw content to a remote service. So the product starts from auditable benchmarks and local storage: SQLite, local artifacts, and offline execution are the defaults; cloud and sync are future adapters. A negative result is preserved as evidence rather than discarded. This is why `CRL-CTX-002` runs fully offline and why the whole pipeline works with no provider.

## Control plane and execution plane split (0002)

The Lab Agent belongs to the control plane; the Subject Agent belongs to the execution plane. The Subject never receives chats, hidden graders, or another variant's results. Deterministic services own state, authority, and evidence. The consequence is that there is no "master agent" with implicit access to everything, and context mounts are explicit and auditable. This split is why the `SubjectEnvelope` exists as a separate, minimal, compiled view.

## Modular monolith, no microservices (0003)

One Python package organized by capability, plus one API, one worker, and one CLI. No microservices, Redis, Kafka, or Kubernetes in the MVP. This keeps the working set small and transactions local and simple. Processes can be separated later without distributing the domain.

## Python core, TypeScript UI, Electron shell (0004)

Python concentrates the domain, evaluations, and backend; React/TypeScript implements the UI; Electron provides Chromium, DevTools, desktop APIs, and packaging, running the backend as a loopback sidecar. End-to-end TypeScript was rejected because it would weaken the analytical base; Tauri was rejected in favor of the Electron/Node ecosystem. The accepted tradeoff is higher resource use and an obligation to keep Electron updated, in exchange for a Python analytical core and a sandboxed renderer with no Node access.

## Canonical evidence storage (0005)

SQLite is canonical for state and events. Artifacts use a managed filesystem. JSONL exists in bundles, not as a second live database. Events are append-only and hash-chained. This avoids dual-write and lets projections (full-text search, Parquet, reports) be rebuilt from the ledger. The ledger, not the run-status column, is the source of truth. See [systems: evidence](../systems/evidence.md).

## Provider-neutral core, OpenAI first (0006)

Provider-specific types stay in adapters behind the ports in `src/evidrun/shared/ports.py`. The Lab Agent will start on Pydantic AI; the first real Subject runner uses the Responses API directly, with an Agents SDK adapter to follow. The benchmark depends on no provider, and multi-provider parity is not simulated before a second real adapter exists.

## Repository docs as source of truth (0007)

Contracts, ADRs, and current architecture live in Git. Frontmatter is validated by `scripts/validate_docs.py`, the manifest is generated, research expires, and ADRs are superseded rather than rewritten. This is the rule that makes the wiki and the docs trustworthy: when they disagree, the files under `docs/` and the code win. See [how to contribute](../how-to-contribute/index.md).

## CLIProxyAPI / DeepSeek default (0008)

The durable default provider is `cliproxyapi-local` at `http://127.0.0.1:8318/v1`, OpenAI Responses-compatible, model `deepseek-v4-flash`, always sending `reasoning.effort=max`. "Durable" means the default persists across restarts and versions until an explicit successor ADR changes it; it does not promise external availability. The endpoint, model, and reasoning level are versioned normative config; the API key lives in the Keychain under `dev.evidrun.providers`, with `EVIDRUN_PROVIDER_API_KEY` as an ephemeral CI override that must never be committed. See [systems: providers](../systems/providers.md).

## Study/Run contract composition (0009)

`StudyRevision` is the single authoring root for controlled hypotheses, capability evaluations, diagnostics, regressions, qualitative investigations, and open exploration. Deterministic expansion of `scenarios × variants × repetitions` produces atomic `RunSpec`s, one scenario/variant/repetition each. A new Run is composed from four immutable sources rather than one mutable document: the `RunSpec` (what should run), the `AdmissionRecord` (what was resolved and authorized), the `RunRecord` (the attempt bound to both), and the `RunEvent` ledger (what actually happened). Checkpoints and evaluations are immutable records anchored to the ledger; status, totals, scorecards, and graphs are reconstructable projections. A required capability that fails, a policy, a workspace, or an interaction that cannot be honored rejects the admission before any Run exists. See [features: study-to-run lifecycle](../features/study-to-run-lifecycle.md).

## Verifiable human authority (0010)

Originally the contract restricted `actor_type` to the literal `human`, but that only validated a claim in the payload. ADR 0010 fixes this: an action can be presented as human only when bound to an authenticated principal and evidence of an explicit confirmation at that boundary. `actor_type=human` without that binding is merely `human_asserted`, never `verified_human`. Agents can prepare drafts and approval requests but cannot self-assert human authority. The ADR also separates `human_review` (a planned primary evaluation stage) from adjudication (a later append-only decision about precedence that never overwrites the judged record). `repository_fixture` is an explicitly non-human authority, allowed only through the dedicated import of the complete canonical `CRL-CTX-002` package. Because no trusted WebAuthn adapter is installed, the default verifier fails closed and the API, CLI, and repository refuse human decisions rather than trusting a client-supplied actor.

## HumanSubjectEnvelope and authenticator lifecycle (0015)

ADR 0010 left the actual authenticator, enrollment, recovery, and the exact signed document open. ADR 0015 closes the near-term part. The signed content becomes a closed, versioned `HumanSubjectEnvelope` (discriminated by `kind`: `RevisionDecisionSubject`, `EvaluationDecisionSubject`), which is the single source of truth for what is signed and whose `subject_digest()` must be byte-for-byte equal to the kernel's `human_subject_digest()`, guaranteed by an anti-drift test. The trusted adapter for this iteration is a local software authenticator (`KeyringAuthenticator`) with an EC P-256 (ES256) keypair in the OS keystore; `LocalWebAuthnVerifier` validates rpIdHash, UP/UV flags, origin, challenge, and signature, and is pure and idempotent so it can run during both persistence and ledger replay. The feature is opt-in via `EVIDRUN_AUTHORITY=1`; the default process verifier stays `UnavailableHumanAttestationVerifier` (fail-closed), preserving ADR 0010. Note this envelope is distinct from the Subject Agent's `SubjectEnvelope`; the name is deliberately not overloaded. See [systems: authority](../systems/authority.md).

## Progress artifacts and bundle boundaries (0011)

Three separate ideas that must not be conflated. First, `ArtifactRef` identity is not access: a ref identifies content and classification but grants no read, mount, export, or effect; access needs a separate verifiable grant, and materialization produces its own record. Second, a `ProgressArtifact` is a derived, immutable summary anchored to a verifiable boundary (a validated checkpoint or a declared subject-turn interval, where a turn is a valid `subject.responded` event); it is not a file inventory, a memory dump, a completion proof, or automatic Subject context. Third, "auditable bundle", "portable bundle", and "replay" are distinct guarantees with distinct profiles; an audit bundle carries records, refs, digests, and event chains but may leave blobs external. The current Evidence Bundle v2 is `profile=audit`, `references_only`, non-portable, non-replayable. None of grants, materialization, portable export, or replay is implemented; a RunSpec with a progress policy is rejected at admission as `runtime:background_progress_observer`.

## Subject disclosure and two-axis terminal semantics (0012, superseded by 0013)

ADR 0012 established that the `SubjectEnvelope` is compiled from a closed allowlist (Goal and constraints, visible materialized inputs, explicitly visible interaction, resolved capabilities, logical workspace and budgets, and separately compiled public evaluation disclosure) and never a denylist over a serialized RunSpec, so new RunSpec fields cannot leak in. It also separated three terminal axes: lifecycle (`completed`, `failed`, `cancelled`, `budget_exhausted`, `guardrail_stopped`), goal state (`achieved`, `partially_achieved`, `not_achieved`, `not_assessable`), and quality (a vector of `EvaluationRecord`s, no implicit score). ADR 0013 supersedes only the bounded-exploration part: a bounded exploration now ends on two independent axes, `disposition` (`concluded`, `incomplete`, `not_assessable`) and `stop_reason` (`evidence_saturation`, `bounded_completion`, `budget_limit`, `time_limit`, `turn_limit`, `human_stop`, `guardrail`, `provider_failure`). Hitting a budget or time limit never implies `concluded`, and `concluded` never asserts quality or causality. Everything else in 0012 (the allowlist, disclosure rules, the ban on turning exploration into pass/fail) remains in force. Both the bounded terminal and any disclosure other than `none` are still rejected by the active runtime. See [background: pitfalls](pitfalls.md).
