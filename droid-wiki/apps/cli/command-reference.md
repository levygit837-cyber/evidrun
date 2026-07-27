# CLI command reference

Every command in `src/evidrun/entrypoints/cli/app.py`, with its purpose and notable options. Commands that touch the database open it through `_components(data_dir)` and dispose it in a `finally` block. Most accept `--data-dir` to override the resolved data directory.

## Top-level

| Command | Purpose | Options |
| --- | --- | --- |
| `evidrun --version` | Print the package version and exit | `--version` |
| `init` | Create the data directory, database, and artifacts directory | `--data-dir` |
| `doctor` | Table of environment checks: package, data dir, SQLite, artifacts, CRL-CTX-002 presence, offline demo, default model `deepseek-v4-flash`, reasoning `max`, provider credential. Exit 1 if any check fails | `--data-dir` |
| `serve` | Run the FastAPI backend. Plain mode: `uvicorn.run` on host/port. Handshake mode: stdin token, ephemeral port, readiness JSON | `--host`, `--port`, `--data-dir`, `--desktop-handshake` |
| `demo` | Bootstrap the CRL-CTX-002 demo offline via `EvidrunService.bootstrap_demo(benchmarks)` and print the JSON result | `--data-dir` |

## experiment

| Command | Purpose |
| --- | --- |
| `experiment validate <path>` | Load a YAML manifest, validate as `ExperimentManifest`, print `valid`, `digest`, and `validity` |

## contract

| Command | Purpose |
| --- | --- |
| `contract validate <path>` | Parse a YAML revision via `parse_revision`, print `valid`, `digest`, normalized semantic document |
| `contract register <path>` | Persist a revision with `--status draft` or `--status proposed`; print id, type, logical id, revision, digest, status |
| `contract accept <revision_id> --reason ...` | Fail closed: prints that a trusted WebAuthn verifier is required, exits 1. No mutation. Use `authority accept` instead |

## study

| Command | Purpose |
| --- | --- |
| `study compile <revision_id>` | Load a `StudyRevision`, build the contract registry for its project, run `StudyCompiler(...).compile(...)`, persist each RunSpec, print id/digest/variant/scenario/repetition per spec |

## run

| Command | Purpose |
| --- | --- |
| `run admit <run_spec_id>` | Run `admission_service.admit(spec)`, persist the `AdmissionRecord`, print decision, digest, and `missing_requirements` |
| `run inspect <run_id>` | Print the dashboard row for the run plus its full event ledger |

## bundle

| Command | Purpose | Options |
| --- | --- | --- |
| `bundle export <comparison_id>` | Export an evidence bundle (v2 by default) to `--output` or `<data>/exports/<id>.evidrun.zip`. `--legacy-v1` writes a v1 bundle | `--output`, `--legacy-v1`, `--data-dir` |
| `bundle verify <path>` | Verify a bundle in a scratch database; print the result JSON; exit 1 if invalid | — |

## chat

| Command | Purpose |
| --- | --- |
| `chat list` | Print all chat sessions from the dashboard projection |

## data

| Command | Purpose |
| --- | --- |
| `data purge` | Notice only: artifact deletion requires an explicit `artifact_id` through the retention API. Removes nothing |

## provider

| Command | Purpose |
| --- | --- |
| `provider status` | Print the default provider profile plus credential availability and source |
| `provider set-key` | Prompt (hidden, confirmed) for an API key and store it in the Keychain |
| `provider doctor` | Call `provider.check()`; exit 1 if the model is unavailable |
| `provider smoke` | Send a fixed one-line prompt and print status and output text |

## authority

| Command | Purpose | Options |
| --- | --- | --- |
| `authority enroll` | Enroll a local WebAuthn credential; print credential id, principal, status | `--principal-id`, `--display-name`, `--relying-party-id`, `--origin`, `--data-dir` |
| `authority credentials` | List enrolled credentials | `--data-dir` |
| `authority revoke <credential_id>` | Revoke a credential; print its new status | `--data-dir` |
| `authority accept <revision_id>` | Confirm a verified-human contract acceptance with the offline authenticator, then `decide_contract_revision`. Exit 1 on `ValueError`/`PermissionError`/`KeyError` | `--credential-id`, `--reason`, `--data-dir` |

The provider commands read the default profile from `Settings.load().default_provider`. See [providers](../../systems/providers.md) and [authority](../../systems/authority.md). Back to the [CLI overview](index.md).
