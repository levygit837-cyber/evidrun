# Evidence

`src/evidrun/evidence/bundle.py` holds `EvidenceBundleService`, which exports a comparison as a self-contained ZIP archive and verifies one back. A bundle is the portable audit artifact: it packages the runs, their contracts, the event ledgers, evaluations, checkpoints, and an artifact manifest, all keyed by digest so a third party can recompute every identity. For the cross-cutting feature view, see [evidence bundles](../features/evidence-bundles.md).

## Purpose

The service does two things:

- **export** a comparison to a ZIP (v1 or v2 layout);
- **verify** a ZIP by recomputing checksums, replaying each event chain against the phase rules, and (for v2) re-validating every contract, record, and manifest entry.

## Key source files

| File | Role |
| --- | --- |
| `src/evidrun/evidence/bundle.py` | `EvidenceBundleService` — export and verify. |
| `src/evidrun/contracts/runtime.py` | `EVENT_ALLOWED_RUN_STATUSES`, `UNSUPPORTED_RUNTIME_EVENT_TYPES`, `normalize_event_payload`. |
| `src/evidrun/contracts/evaluation.py` | `EvaluationValidator` — gate results and stage visibility used during verify. |
| `src/evidrun/infrastructure/database/repository.py` | Source of runs, specs, admissions, events, and records. |

## How events chain

Each event row carries `sequence`, `prev_event_hash`, and `event_hash`. The hash is `sha256_json` over the full event envelope (id, schema version, run id, sequence, type, timestamp, actor, classification, payload, correlation/causation, and `prev_event_hash`). Because each event commits to the previous hash, the sequence is a tamper-evident chain: changing any earlier event breaks every later hash. The chain is written by the [database](database.md); the bundle verifier recomputes it independently.

## Bundle v1

`export_comparison` writes the original flat layout: `manifest.json`, `comparison.json`, `grades.json`, `report.md`, one `events/{run}.jsonl` per run, and a `checksums.json` mapping each file to its SHA-256. It is a straightforward snapshot with no contract re-verification.

## Bundle v2

`export_comparison_v2` is the auditable layout. It requires Study-based runs (it raises if a run has no contracts) and writes:

- `bundle.json` — the manifest header: `schema_version="2"`, `kind="comparison"`, `profile="audit"`, `artifact_content="references_only"`, `portable=false`, `replayable=false`, and the two run ids;
- `comparison.json` and `report.md`;
- per run: `run-specs/{id}.json`, `admissions/{id}.json`, `runs/{id}.json` (the canonical `RunRecord`), `events/{id}.jsonl`, `evaluations/{id}.json`, `checkpoints/{id}.json`;
- `contracts/{type}/{logical_id}@{revision}.json` for every referenced revision (deduplicated across both runs);
- `artifact-manifest.json`;
- `checksums.json`.

Each record is dumped with `_record_dict`, which appends the computed digest (`digest` or, for checkpoints, `checkpoint_hash`) to the semantic document so the verifier can recompute and compare it.

### The audit / references-only profile

A v2 bundle is explicitly `portable=false` and `replayable=false`, and its artifact content is `references_only`. The `ArtifactManifest` enumerates the artifacts a run intentionally materialized — scenario inputs, interaction prompts, capability instructions, hidden calibration, extension schema/payload, and checkpoint captures — each as an `ArtifactManifestEntry` with `content_included=false` and an omission reason stating the audit profile carries identity and digest, not bytes. The manifest is a declaration of intentional refs, not a log of every file read or written. This matches the `ArtifactManifest` invariants in [contracts](contracts/index.md) and the rule in `AGENTS.md`.

## artifact-manifest.json

`_spec_artifact_entries` derives the expected entries from a RunSpec (scenario inputs, interaction prompt refs, capability instruction refs, hidden calibration refs, and extension schema/payload refs), and `_checkpoint_artifact_entries` adds checkpoint capture refs. Export builds the manifest from these; verify recomputes the same expected set from the parsed specs and checkpoints and requires the stored manifest's entries to match exactly, plus a matching digest and the `audit`/non-portable/non-replayable flags.

## What verify checks

`verify(bundle_path)` returns a result dict with `valid`, `integrity_valid`, `audit_complete`, the fixed `portable`/`replayable` flags, and the per-check maps `checksums`, `event_chains`, and `records`. The bundle is `valid` only when every checksum, every event chain, and every record check passes.

### Checksums

Every file listed in `checksums.json` must be present with a matching SHA-256, the file list must be complete (no extra or missing members), and member names must be unique.

### Event chains

For each `events/*.jsonl`, the verifier replays the chain from `queued`:

- schema version, run id, and monotonic sequence must be correct;
- the actor type must be in the allowed set and the actor id non-empty;
- the event type must not be a reserved (`UNSUPPORTED_RUNTIME_EVENT_TYPES`) type;
- `prev_event_hash` must equal the previous event's hash and the recomputed `sha256_json` must equal the stored `event_hash`;
- `normalize_event_payload` must reproduce the stored payload exactly (payload shape check);
- the first event must be `run.queued`, no `run.queued` may reappear, and nothing may follow a terminal state;
- the lifecycle transition must be legal and `from_status`/`status` payload fields must agree with the current and target status;
- subject invocations and responses must be paired, and `run.evaluating`/`run.completed` require a prior response.

### Records (v2)

`_verify_v2_records` validates the audit content:

- `__bundle_structure__`: the `bundle.json` header flags, exactly two distinct run ids, and the required per-run files exist;
- each run's `RunRecord` cross-checks its RunSpec digest, admission digest, admitted decision, and the study/scenario/variant/repetition lineage;
- every referenced contract is re-parsed, its digest recomputed, and its payload compared against the RunSpec's embedded payload;
- the artifact manifest matches the recomputed expected entries and digest;
- each event ledger ends in a terminal event, and the `run.queued`/terminal payloads match the spec, record, and admission (including bounded-exploration stop-condition consistency);
- evaluation records validate through `EvaluationValidator`, match their completion events, cover the required stages after gates, and keep evidence refs within the boundary sequence; human adjudication/review relations and boundaries are re-checked;
- checkpoint records match their definition digest, validators, capture spec, trigger, and event boundary;
- `comparison.json` run ids match the bundle header and the parsed run set.

A checksum match alone is never sufficient: the v2 verifier re-validates lifecycle, queued/terminal contracts, comparison ids, evaluation records and events, and the full artifact entry set, exactly as required by `AGENTS.md`.

## Integration points

- [database](database.md) is the sole read source; the verifier deliberately re-derives everything rather than trusting stored digests.
- [contracts / runtime](contracts/runtime.md) supplies the event tables and `normalize_event_payload`; [contracts / index](contracts/index.md) supplies the manifest model.
- [run execution](run-execution.md) produces the comparisons that get exported.

## Entry points for modification

- A new bundle file type needs handling in both `export_comparison_v2` and the verify record loop, or verification will flag it as missing.
- New event or record kinds need matching verifier branches; the verifier fails closed on anything it cannot re-validate.
