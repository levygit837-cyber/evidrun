# Patterns and conventions

This page describes the coding patterns and cross-cutting rules that hold across the Evidrun codebase. Read it before writing new code. The authoritative rules live in `AGENTS.md` and the accepted ADRs; this page explains how they show up in practice.

## Boundaries between layers

The most important convention is layering. It is enforced by review against `AGENTS.md`, not by a linter, so it is easy to break by accident.

- The Python **domain** never imports FastAPI, SQLAlchemy, OpenAI, Electron, or React.
- **Electron Main** manages lifecycle and desktop capabilities; it implements no domain logic.
- The **renderer** never imports `electron`, `node:*`, or native bindings.
- The **Subject Agent** never receives chats, hidden graders, or evidence outside the compiled `SubjectEnvelope`.
- The **Lab Agent** creates drafts; acceptance and external effects belong to the human.

The domain reaches the outside world through protocols in `src/evidrun/shared/ports.py` (`SubjectRunnerPort`, `ProviderPort`, `GraderPort`, `EventSink`, `ArtifactStorePort`, and others). Concrete adapters live under `src/evidrun/infrastructure/`. When you add a capability, define the port first and keep the adapter thin.

## Immutable, frozen contract models

Every authoring and runtime contract is a Pydantic model that extends `ContractModel` in `src/evidrun/contracts/base.py`:

```python
class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
```

`extra="forbid"` means an unknown field is a hard error, not a silent pass. `frozen=True` means instances are immutable. Corrections create a new revision rather than mutating an existing one. Follow this for any new contract type.

## Canonical digests

Identity and integrity come from SHA-256 over canonical JSON. The helpers live in `src/evidrun/shared/types.py`:

- `canonical_json` sorts keys and uses compact separators.
- `sha256_json` hashes a value's canonical JSON; `sha256_bytes` hashes raw bytes.
- `semantic_model_dump` (in `contracts/base.py`) drops computed fields, nulls, and empty modules so the digest is stable across serialization noise.

Digests are exposed as Pydantic `@computed_field` properties named `digest`. The event ledger chains events with SHA-256 over canonical JSON, so any change to a stored payload is detectable.

## Identifiers and time

- IDs use `new_id(prefix)`, which returns a sortable UUIDv7 with a human-readable prefix (`eval_...`, `run_...`). Prefer this over ad-hoc IDs so records sort by creation time.
- Timestamps are timezone-aware UTC. The `UtcDateTime` annotation in `contracts/base.py` rejects naive or non-UTC datetimes. Use `utc_now()`.

## Fail closed

Capabilities that are representable but not executable are rejected at admission, not silently ignored. The admission service and repository refuse anything the runtime cannot honor: non-`single_turn` interaction, budgets beyond `max_wall_seconds`, disclosure other than `none`, reserved events (`progress.*`, tool, skill, checkpoint), sensitive or restricted inputs, and human decisions without a trusted verifier. When you add runtime support, remove the corresponding closed gate deliberately and add tests that prove the new path is admitted.

## Classification

`Classification` (`public`, `internal`, `sensitive`, `restricted`) tags every artifact and input. The current runtime rejects `sensitive` and `restricted` inputs at admission; only `public` and `internal` can reach a materializer. `ArtifactRef` carries a classification but never a storage locator; a reference identifies content, it does not grant access.

## Contracts drive generated types

Schemas and TypeScript types are generated from the Pydantic models, not hand-written. `scripts/generate_schemas.py` emits JSON Schema for every contract plus the OpenAPI document into `schemas/generated/`, and `scripts/generate_contract_types.mjs` turns those into `apps/web/src/generated/contracts.ts`. CI runs both with `--check` and fails if the committed output is stale. After changing a contract, run `pnpm generate:contracts` and commit the regenerated files. See [tooling](tooling.md).

## Documentation as a checked artifact

Docs under `docs/` carry YAML frontmatter (id, type, status, authority, implementation_refs, verification_refs). `scripts/validate_docs.py` validates that frontmatter and regenerates `docs/_generated/manifest.json`, which CI diffs. Accepted ADRs are not rewritten to change a decision; you write a successor ADR. Run results never become facts without `run:`, `event:`, or `artifact:` references.

## Style

- Python targets 3.14, formatted and linted by ruff (line length 100, rule sets `E, F, I, UP, B, SIM, RUF`) and type-checked by pyright in strict mode.
- Comments are rare and explain why, not what. The contract models are meant to be self-documenting.
- TypeScript is strict; the renderer stays free of Node and Electron imports.

See [development workflow](development-workflow.md) for the branch-to-merge cycle and [testing](testing.md) for the test layout.
