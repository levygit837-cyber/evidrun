# Contracts

The contracts package is the identity and rule layer of Evidrun. Every Study, Goal, Scenario, RunSpec, admission decision, subject envelope, evaluation, and checkpoint is a frozen Pydantic model defined here. Identity is content-addressed: the SHA-256 of a model's canonical JSON is its digest, and references carry that digest so a mismatch is detectable anywhere in the pipeline.

This page covers the shared base in `src/evidrun/contracts/base.py`. The three large modules get their own pages:

- [authoring](authoring.md) — the nine revision types a human accepts.
- [compiler](compiler.md) — turning revisions into RunSpecs and admitting them.
- [runtime](runtime.md) — RunSpec, admission, envelopes, evaluation and checkpoint records, and event payloads.

## Directory layout

| File | Purpose |
| --- | --- |
| `src/evidrun/contracts/__init__.py` | Public re-exports for the whole package. |
| `src/evidrun/contracts/base.py` | `ContractModel`, `semantic_model_dump`, `ContractType`, the shared refs, and human-authority records. |
| `src/evidrun/contracts/authoring.py` | Authoring revisions and their specs (Study, Goal, Scenario, and the rest). |
| `src/evidrun/contracts/compiler.py` | `StudyCompiler`, `AdmissionService`, envelope compilers, `InMemoryContractRegistry`. |
| `src/evidrun/contracts/runtime.py` | Runtime records and the Run event payload models. |
| `src/evidrun/contracts/evaluation.py` | `EvaluationValidator` (gate results, stage visibility, human-relation boundary). |
| `src/evidrun/contracts/authority.py` | `HumanAttestationVerifier` protocol and the fail-closed default. |
| `src/evidrun/contracts/legacy.py` | Adapter that imports the CRL-CTX-002 experiment manifest as an accepted package. |

## The contract base model

Every contract extends `ContractModel`, which sets `extra="forbid"` and `frozen=True`. Unknown fields are rejected and instances are immutable, so a contract cannot silently grow a field or be mutated after construction.

```python
class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
```

Two annotated string types recur throughout: `NonEmptyStr` (whitespace-stripped, min length 1) and `Digest` (exactly 64 lowercase hex characters). `UtcDateTime` (in `base.py`) rejects any timestamp that is not timezone-aware UTC.

## Canonical serialization and digests

`semantic_model_dump` produces the JSON-ready document that every digest is computed over. It dumps in JSON mode, excludes computed fields (so the `digest` property does not feed itself), drops `None`, and recursively removes empty lists and empty maps.

```python
def semantic_model_dump(model: BaseModel) -> dict[str, object]:
    document = model.model_dump(mode="json", exclude_computed_fields=True, exclude_none=True)
    # ... normalize: drop None values, then drop empty [] and {} ...
```

Digests are then `sha256_json(semantic_model_dump(self))`, where `sha256_json` (in `src/evidrun/shared/types.py`) hashes `json.dumps(..., sort_keys=True, separators=(",", ":"))`. Because keys are sorted and empties are stripped, two semantically identical contracts always produce the same digest. Most records expose `digest` as a `@computed_field` property. `RevisionEnvelope` is the exception: it digests only a fixed subset of fields (see below).

## ContractType

`ContractType` is the closed set of authoring contract kinds. Each authoring revision pins its own type with a `Literal`, and the compiler and RunSpec validators check that every `ContractRef` sits in the correct slot.

```python
class ContractType(StrEnum):
    STUDY = "study"
    GOAL = "goal"
    SCENARIO = "scenario"
    AGENT_INVENTORY = "agent_inventory"
    WORKSPACE_TEMPLATE = "workspace_template"
    INTERACTION_PROTOCOL = "interaction_protocol"
    EVALUATION_PLAN = "evaluation_plan"
    CHECKPOINT_POLICY = "checkpoint_policy"
    PROGRESS_ARTIFACT_POLICY = "progress_artifact_policy"
```

`RevisionStatus` (`draft`, `proposed`, `accepted`, `rejected`, `superseded`) tracks a revision's lifecycle in the database, not in the contract itself.

## RevisionEnvelope

`RevisionEnvelope` is the common shape for the immutable authoring revisions. It carries `schema_version`, `logical_id`, `revision` (a positive integer), `project_id`, and `title`. Each concrete revision adds a `contract_type` literal and a `payload`.

Its digest is intentionally narrow. `digest_document()` selects only `schema_version`, `contract_type`, `logical_id`, `revision`, and `payload`, so the digest identifies the contract content and version, not incidental metadata like the title. The `ref` property builds a `ContractRef` from the type, logical id, revision, and digest.

## Base references

| Type | Description |
| --- | --- |
| `ContractRef` | Points at one revision: `contract_type`, `logical_id`, `revision > 0`, `digest`. The universal contract pointer. |
| `ArtifactRef` | Identifies content by `artifact_id`, `digest`, `media_type`, and `classification`. It has no `locator` — it names content, it does not grant access, mounting, or export. |
| `ArtifactManifestEntry` | One intentionally materialized artifact with a fixed `role`. Validates that `content_included` and `omission_reason` are mutually exclusive. Not a file-access log. |
| `ArtifactManifest` | The closed bundle manifest: `profile="audit"`, `portable=False`, `replayable=False`, unique entries per (run, role, artifact), with a computed `digest`. |
| `CapabilityDescriptorRef` | Names a capability adapter by `namespace`, `name`, `version`, `digest`. |
| `ExtensionRef` | A typed extension slot with schema and payload artifact refs; validates that its digest and classification match the payload artifact. |
| `EvidenceRef` | A string ref that must start with `run:`, `event:`, or `artifact:`. This is how evaluation results point back at the ledger. |
| `KeyValue` | A simple keyed scalar used for anchors and parameters. |

`ArtifactRef` having no locator is a hard invariant: the same rule appears in `AGENTS.md`. See [artifacts](../../primitives/artifacts.md).

## Human-authority records

These records live in `base.py` because both revision decisions and evaluation records embed them. See [authority](../authority.md) for how they are produced and verified.

| Type | Description |
| --- | --- |
| `HumanAttestationRecord` | Evidence from a trusted verification adapter: principal, credential, `verification_method="webauthn"`, action, target/subject/challenge digests, assertion artifact ref, verifier ref, and verified timestamp. Computed `digest` and `ref`. |
| `HumanAttestationRef` | A lightweight pointer (`attestation_id`, `digest`). |
| `VerifiedHumanDecisionAuthority` | `kind="verified_human"`; binds a principal to an attestation and checks the principal matches. |
| `RepositoryFixtureDecisionAuthority` | `kind="repository_fixture"`; the only non-human authority, restricted to the CRL-CTX-002 import. Rejects a placeholder digest and can only carry `accepted`. |
| `DecisionAuthority` | Discriminated union of the two authorities above, keyed on `kind`. |
| `RevisionDecisionRecord` | Ties a `ContractRef` to a decision (`accepted`/`rejected`/`superseded`) and an authority. For human authority it re-checks the attestation action, target digest, subject digest, and timestamp against the decision content. |

The `RevisionDecisionRecord.validate_authority` model validator is where a human decision is cross-checked: the attestation's `action` must equal `revision.{decision}`, its `target_digest` must equal the revision digest, and its `subject_digest` must equal `human_subject_digest()` computed from the ref, decision, and rationale. A repository fixture may only accept.

## Integration points

- [authoring](authoring.md) builds on `RevisionEnvelope` for all nine revision types.
- [runtime](runtime.md) uses `ContractRef`, `ArtifactRef`, and the digest machinery for every record.
- [database](../database.md) stores revisions and decisions and re-verifies digests on load.
- [evidence](../evidence.md) re-parses every stored contract and recomputes its digest during bundle verification.

## Entry points for modification

- Adding a field to a contract changes its digest; every stored digest and every reference to it must be recomputed. Prefer a successor revision over mutating an accepted one (see `AGENTS.md`).
- New shared refs belong in `base.py` so authoring and runtime can both import them without a cycle.
- Never add a `locator` to `ArtifactRef` or any envelope. This is an explicit invariant.
