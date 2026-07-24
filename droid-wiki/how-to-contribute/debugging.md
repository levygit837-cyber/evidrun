# Debugging

Practical troubleshooting for Evidrun. Most surprises come from the fail-closed boundary: a contract compiles and validates but admission rejects it because the runtime cannot honor it. This page maps the common failures to their causes, based on `src/evidrun/entrypoints/cli/app.py` and `src/evidrun/entrypoints/api/app.py`.

## Start with doctor

The CLI `doctor` command checks the environment and the default provider:

```bash
uv run evidrun doctor
```

It reports the Python package, data directory, SQLite database, artifacts directory, whether the `CRL-CTX-002` benchmark file exists, that the demo runs offline, that the default model is `deepseek-v4-flash` with `reasoning=max`, and whether a provider credential is available. It exits nonzero if any check fails. The API exposes the same information at `GET /api/v1/doctor`, plus `network_required_for_demo: false` and the default provider profile.

For the provider itself:

```bash
uv run evidrun provider status   # profile + whether a credential is present, without revealing it
uv run evidrun provider doctor   # live check that the model is available (needs the local CLIProxyAPI)
uv run evidrun provider smoke    # minimal live call; exits nonzero on failure
```

`provider doctor` and `provider smoke` are the only commands that need the provider running. The benchmark does not. See [systems: providers](../systems/providers.md).

## Isolate data with EVIDRUN_DATA_DIR

The data directory defaults to a `platformdirs` location. Override it to keep experiments from colliding:

```bash
EVIDRUN_DATA_DIR=/tmp/evidrun-scratch uv run evidrun demo
```

Every CLI command also accepts `--data-dir`. `Settings.load` resolves `--data-dir`, then `EVIDRUN_DATA_DIR`, then the platform default, and `ensure_directories()` creates the data and artifacts dirs with mode `0o700`. See [reference: configuration](../reference/configuration.md).

## Reconstruct a run from the event ledger

The event ledger is the normative source of truth; run status is a projection. To read a run and its events:

```bash
uv run evidrun run inspect <run_id>
```

Over HTTP, the events are at `GET /api/v1/runs/{run_id}/events`, the full detail (with the RunRecord and events) at `GET /api/v1/runs/{run_id}`, evaluations at `/evaluations`, and checkpoints at `/checkpoints`. Events are append-only and hash-chained (`prev_event_hash` → `event_hash`), so you can verify the chain and reconstruct status, comparisons, and grades from the ledger. See [systems: evidence](../systems/evidence.md) and [systems: database](../systems/database.md).

### The live event stream

`GET /api/v1/runs/{run_id}/stream` is a Server-Sent Events endpoint. It polls the ledger once a second, emits each new event as `event: <type>` with the JSON payload as `data`, sends `: heartbeat` comments between polls, and closes once the run reaches a terminal status (`completed`, `failed`, `cancelled`, `budget_exhausted`, `guardrail_stopped`) and at least one event has been emitted. If a stream never closes, the run has not reached a terminal event.

## Common fail-closed rejections

The runtime is intentionally smaller than the contracts. These are the rejections you will actually hit.

| Symptom | Cause | Where |
| --- | --- | --- |
| Admission returns `decision: rejected` with `missing_requirements` populated | A required capability is absent or not cataloged. A representable capability is not the same as an executable one. | `POST /api/v1/run-specs/{id}/admit`, `evidrun run admit` |
| Admission rejected with a `runtime:*` requirement | The RunSpec uses a capability the runtime cannot honor yet: `runtime:subject_evaluation_guidance_delivery` (disclosure other than `none`), `runtime:bounded_exploration_terminal`, `runtime:background_progress_observer`, `runtime:verified_human_adjudication`. | admission service |
| `503` on a contract decision | `POST /api/v1/contracts/revisions/{id}/decisions` and `evidrun contract accept` refuse: verified human authority is unavailable without a trusted WebAuthn verifier. | API and CLI |
| A reserved event is rejected on append | `progress.*`, tool, skill, and checkpoint events stay reserved until their coordinators exist; the repository rejects them. | repository event append |
| Sensitive/restricted input rejected at admission | The active runtime admits only `public` and `internal`. Sensitive/restricted have no classified materialization boundary yet. | admission service |
| `raw_encrypted` capture rejected at admission | No encrypted sink for the Subject response exists yet. | admission service |

Every rejection is a specific entry in `missing_requirements`, `denied_policies`, or a blocking `AdmissionIssue`, not a silent no-op. When you make a currently-rejected capability executable, remove its closed gate deliberately and add a test proving the new path is admitted. See [background: pitfalls](../background/pitfalls.md) and [systems: contracts compiler and admission](../systems/contracts/compiler.md).

## Enabling human authority for local testing

Human decisions fail closed by default. To exercise the local authenticator, set `EVIDRUN_AUTHORITY=1` and use the `authority` CLI group:

```bash
EVIDRUN_AUTHORITY=1 uv run evidrun authority enroll --principal-id you --display-name "You"
EVIDRUN_AUTHORITY=1 uv run evidrun authority accept <revision_id> --credential-id <id> --reason "..."
```

Without `EVIDRUN_AUTHORITY=1`, `create_app` does not mount the authority router and the API returns the 503. See [systems: authority](../systems/authority.md) and [security: index](../security/index.md).
