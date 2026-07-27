# Artifacts

An artifact is content identified by its digest and metadata. An `ArtifactRef` names that content — it never carries a storage locator and never grants access. This separation of identity from access runs through the whole system: a reference tells you what something is and lets you verify it, but says nothing about where it lives or whether you may read it.

## The concept

The rule is a hard invariant, repeated in `AGENTS.md`: `ArtifactRef` has no `locator`. It identifies content; it does not concede access, mounting, export, or reading. A future `Artifact Access Grant` — a separate authorization limiting consumer, purpose, operations, classification, and time — would govern access, but it is not implemented.

Every artifact and input carries a `Classification`: `public`, `internal`, `sensitive`, or `restricted`. Classification drives what the runtime will touch. The active pipeline admits only `public` and `internal` inputs; any `sensitive` or `restricted` input is rejected at admission because there is no classified materialization boundary. The `ArtifactStore` refuses `restricted` content before persistence outright.

Bundles enumerate the artifacts a run intentionally materialized through an `ArtifactManifest` of `ArtifactManifestEntry` rows. This is a declaration of intentional references, not a file-access log — it never claims to enumerate every file read, edited, or observed.

## The model

`ArtifactRef` (`src/evidrun/contracts/base.py`):

| Field | Type | Notes |
| --- | --- | --- |
| `artifact_id` | `NonEmptyStr` | Content identity. |
| `digest` | `Digest` | 64-hex SHA-256 of the content. |
| `media_type` | `NonEmptyStr` | MIME type. |
| `classification` | `Classification` | Defaults to `internal`. No `locator` field exists. |

`ArtifactManifestEntry`: `run_id`, a fixed `role` (`scenario_input`, `subject_input_materialized`, `agent_instruction`, `interaction_prompt`, `hidden_calibration`, `extension_schema`, and more), the `artifact_ref`, `content_included`, and an `omission_reason`. Its validator makes `content_included` and `omission_reason` mutually exclusive.

`ArtifactManifest`: `profile="audit"`, `portable=False`, `replayable=False`, unique entries per `(run_id, role, artifact_id)`, with a computed `digest`.

`ExtensionRef`: a typed extension slot pairing a `schema_ref` and `payload_ref` (both `ArtifactRef`); its validator requires the extension's digest and classification to match the payload artifact.

`Classification`: `public`, `internal`, `sensitive`, `restricted`.

## Storage: CAS and the encrypted vault

The `ArtifactStore` (`src/evidrun/infrastructure/artifacts/store.py`) keeps two backends. Public and internal content goes to a content-addressed store (`cas/`), keyed by digest, deduplicated, with `0o600` files. Sensitive content requires explicit `raw_authorized` opt-in and goes to an encrypted vault: a per-project AES-256-GCM key (from the OS keychain via `KeyringKeyProvider`), a random 12-byte nonce, and the artifact id bound as associated data. Restricted content is refused. Sensitive raw capture uses a default 30-day TTL; `purge` removes the blob and leaves a tombstone carrying the digest and reason. Credentials never enter the store — they stay in the keychain or environment.

## Progress artifacts

A `ProgressArtifact` is a provisional, derived, append-only summary anchored to a boundary (a reached checkpoint or a `subject_turn_interval`, where a turn is a valid `subject.responded` event). It is not a file inventory, a memory dump, or a second source of truth. The contracts — policy, content, record, and event payloads — exist, but there is no background observer or persistence, so admission rejects any progress-artifact policy as `runtime:background_progress_observer`.

## Invariants

- **No locator, ever.** `ArtifactRef` and every envelope identify content without a path, URL, or storage locator. Adding one is an explicit prohibition.
- **Identity is not access.** A reference grants no read, mount, export, or materialization.
- **Digest matches content.** The digest is the SHA-256 of the bytes; an `ExtensionRef`'s digest and classification must equal its payload artifact's.
- **Classification gates the runtime.** Only `public`/`internal` inputs are admitted; `restricted` is refused at the store; `sensitive` raw capture needs explicit authorization and encryption.
- **Manifest is intentional, not telemetry.** Entries are the artifacts a run deliberately materialized, unique per `(run, role, artifact)`, with `content_included`/`omission_reason` mutually exclusive.

## Where it appears in code

| File | Role |
| --- | --- |
| `src/evidrun/contracts/base.py` | `ArtifactRef`, `ArtifactManifest`, `ArtifactManifestEntry`, `ExtensionRef`, `EvidenceRef`. |
| `src/evidrun/infrastructure/artifacts/store.py` | `ArtifactStore` — CAS, encrypted vault, purge, TTL. |
| `src/evidrun/contracts/runtime.py` | `ProgressArtifactContent`, `ProgressArtifactRecord`, `ProgressStatement`. |
| `docs/contracts/capture-and-retention.md` | The normative capture and retention rules. |

## Cross-links

- [Evidence](../systems/evidence.md) — how the manifest is built and re-verified in a bundle.
- [Evidence bundles](../features/evidence-bundles.md) — the references-only profile that carries refs, not blobs.
- [Privacy and retention](../security/privacy-and-retention.md) — classification, capture modes, and retention in depth.
- [Contracts](../systems/contracts/index.md) — the shared refs and their validators.
