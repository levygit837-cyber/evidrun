# Contracts and revisions

A contract in Evidrun is an immutable, content-addressed statement of intent that a human authors and accepts. Revisions are how contracts change: you never mutate an accepted contract, you write a new revision. This is the input layer for everything downstream — the compiler resolves accepted revisions into RunSpecs, and nothing else can run.

## The concept

Every authoring contract extends `ContractModel` (`src/evidrun/contracts/base.py`), which sets `extra="forbid"` and `frozen=True`. An unknown field is a hard error, and an instance cannot be mutated after construction. Identity comes from the SHA-256 of the model's canonical JSON (`semantic_model_dump` then `sha256_json`), exposed as a computed `digest`. Two semantically identical contracts always produce the same digest because keys are sorted and empty values are stripped.

A `RevisionEnvelope` wraps each contract with the common fields needed to version it. Nine concrete revision types cover the whole authoring surface — see [authoring revisions](../systems/contracts/authoring.md) for each one and its payload. A revision moves through a lifecycle (`draft` → `proposed` → `accepted`, or `rejected`, or `superseded`), but that status is tracked in the database, not inside the frozen contract.

The governing rule, from `AGENTS.md`: an accepted revision is never rewritten to change a decision. A correction is a successor revision with a higher revision number. This keeps the audit trail intact — you can always see what was accepted and when.

## The model

`RevisionEnvelope` fields (`src/evidrun/contracts/base.py`):

| Field | Type | Notes |
| --- | --- | --- |
| `schema_version` | `Literal["1"]` | Fixed at `"1"`. |
| `logical_id` | `NonEmptyStr` | Stable identity across revisions of the same contract. |
| `revision` | `int > 0` | Monotonic; each new revision is the previous max plus one. |
| `project_id` | `NonEmptyStr` | Owning project. |
| `title` | `NonEmptyStr` | Human label; excluded from the digest. |
| `contract_type` | `ContractType` literal | Added by each concrete subtype. |
| `payload` | spec model | The typed contract body (e.g. `StudySpec`, `GoalSpec`). |

`ContractType` is the closed set of kinds: `study`, `goal`, `scenario`, `agent_inventory`, `workspace_template`, `interaction_protocol`, `evaluation_plan`, `checkpoint_policy`, `progress_artifact_policy`.

`RevisionStatus` is the lifecycle enum: `draft`, `proposed`, `accepted`, `rejected`, `superseded`.

Acceptance is recorded by a `RevisionDecisionRecord` (`revision_ref`, `decision`, `authority`, `rationale`, `decided_at_utc`). Its `authority` is a `DecisionAuthority` — either a `VerifiedHumanDecisionAuthority` or the single non-human `RepositoryFixtureDecisionAuthority`.

## Invariants

- **Frozen and closed.** `extra="forbid"` and `frozen=True`; a contract cannot silently grow a field or be mutated.
- **Narrow digest.** `RevisionEnvelope.digest_document()` hashes only `schema_version`, `contract_type`, `logical_id`, `revision`, and `payload` — not incidental metadata like `title`. The `ref` property builds a `ContractRef` from the type, logical id, revision, and digest.
- **Monotonic revisions.** `InMemoryContractRegistry.add` rejects a second revision at the same key with different content and requires revisions to increment by exactly one.
- **Accepted-only resolution.** `resolve` returns a revision only if the reference digest matches and the revision carries an `accepted` decision, so the compiler can never pull in a draft or rejected contract.
- **Successor, not rewrite.** Only an accepted revision can be superseded, and a conflicting decision on the same revision is rejected.
- **Verifiable acceptance.** A human decision re-checks the attestation's action, target digest, and subject digest against the decision content; the repository fixture may only carry `accepted`. See [human authority](../features/human-authority.md).

## Where it appears in code

| File | Role |
| --- | --- |
| `src/evidrun/contracts/base.py` | `ContractModel`, `RevisionEnvelope`, `ContractType`, `RevisionStatus`, `RevisionDecisionRecord`, `DecisionAuthority`. |
| `src/evidrun/contracts/authoring.py` | The nine revision subtypes and their payload specs; `parse_revision`, `REVISION_MODELS`. |
| `src/evidrun/contracts/compiler.py` | `InMemoryContractRegistry` — immutability, monotonicity, accepted-only resolution. |
| `src/evidrun/infrastructure/database/repository.py` | Stores revisions and decisions; re-verifies digests and replays decisions on load. |

## Cross-links

- [Authoring revisions](../systems/contracts/authoring.md) — the code-level tour of all nine types.
- [Contracts](../systems/contracts/index.md) — the shared base, refs, and digest machinery.
- [RunSpec and admission](runspec-and-admission.md) — what accepted revisions compile into.
- [Human authority](../features/human-authority.md) — how acceptance is authorized.
