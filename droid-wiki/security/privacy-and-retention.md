# Privacy and retention

Evidrun classifies every artifact and input and enforces classification at two points: the `ArtifactStore` when content is persisted, and admission when a RunSpec tries to feed content into a Run. The normative sources are `docs/security/privacy-and-retention.md` and `docs/contracts/capture-and-retention.md`. The store is `src/evidrun/infrastructure/artifacts/store.py`; its tests are `tests/security/test_artifact_store.py`.

## Classification levels

`Classification` (in `src/evidrun/shared/types.py`) has four levels: `public`, `internal`, `sensitive`, `restricted`. They tag both stored artifacts and Run inputs, and they gate different behavior in each place.

| Level | In the ArtifactStore | At Run admission |
| --- | --- | --- |
| `public` | Content-addressed storage (CAS) | Admitted |
| `internal` | Content-addressed storage (CAS) | Admitted |
| `sensitive` | Requires `raw_authorized=True`; encrypted in the vault with a 30-day TTL | Rejected |
| `restricted` | Never persisted (`ValueError`) | Rejected |

## Sensitive and restricted inputs are rejected at admission today

The current Run runtime admits only `public` and `internal` inputs. Any `sensitive` or `restricted` input rejects the admission, because there is no classified materialization boundary yet; only `public` and `internal` reach a materializer. `raw_encrypted` capture is also rejected at admission because the encrypted sink for the Subject response does not exist yet. This is a fail-closed gate, not a silent drop. See [how-to-contribute: debugging](../how-to-contribute/debugging.md) for the rejection list.

## Storage: CAS plus an encrypted vault

`ArtifactStore` creates three subdirectories under the artifacts root, each with mode `0o700`: `cas`, `vault`, `metadata`.

- **CAS** holds `public`/`internal` content addressed by `sha256` of the bytes, sharded by the first two hex digits, deduplicated, written with mode `0o600`.
- **Vault** holds `sensitive` content. `put` requires `raw_authorized=True` (otherwise `PermissionError`), fetches a per-project AES-256 key from the `KeyProvider`, generates a 12-byte nonce, encrypts with AES-256-GCM binding the `artifact_id` as associated data, and writes `nonce + ciphertext` with mode `0o600`. `restricted` raises `ValueError` before any write. `tests/security/test_artifact_store.py` asserts the plaintext never appears in the encrypted file and that restricted content is never persisted.
- **Metadata** holds one JSON record per artifact (id, project, media type, classification, storage, digest, created-at, TTL, pinned), also `0o600`.

Keys come from `KeyringKeyProvider` (per-project AES-256 key stored in the system Keychain under `evidrun-project-keys`) in production, or `MemoryKeyProvider` in tests. Keys never enter the ledger, bundles, or logs.

## ArtifactRef has no storage locator

`ArtifactRef` identifies content by id, digest, media type, and classification. It carries no path, URL, or storage locator in any contract. A reference identifies content; it does not grant access, mounting, export, or read. Grants and materialization records are decided by ADR 0011 but are not implemented yet, so possession of a ref is never authorization. Do not reintroduce a locator into `SubjectEnvelope`, `EvaluatorEnvelope`, `ResolvedAgentInventory`, or bundles. See [primitives: artifacts](../primitives/artifacts.md).

## Subject response capture modes

The Subject response payload validates the shape allowed by its capture mode: `metadata`, `redacted` (only the `[REDACTED]` marker), `raw_encrypted` (only `artifact:` refs, never inline), or `disabled`. The repository requires the event's `capture_mode` to match the RunSpec's declared `default_mode` exactly. The system does not ask for private chain-of-thought; a reasoning summary is stored only if the provider supplies it explicitly and the capture policy allows it.

## Data purge and its limits

Deletion requires an explicit `artifact_id` through the retention API. `ArtifactStore.purge` removes the blob (CAS file or vault file) and writes a tombstone in its place, preserving the classification, digest, purge timestamp, and reason. The CLI has no bulk purge: `evidrun data purge` prints a notice that deletion requires an explicit `artifact_id` through the retention API and removes nothing. Cascade to snapshots, events, and projections does not exist yet. Exported copies are out of scope for purge and must be shown to the user before export. See [systems: evidence](../systems/evidence.md) for bundle boundaries.
