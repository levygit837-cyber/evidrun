# Testing

Evidrun has a Python test suite under `tests/` and TypeScript Vitest suites for the web and desktop apps. This page lists what each area covers and how the runners are configured.

## Python test layout

Tests live under `tests/` split by scope. `pyproject.toml` sets `pythonpath = ["src"]` and `testpaths = ["tests"]`, with `addopts = "-ra --strict-config --strict-markers"`. Run everything with `uv run pytest`.

| File | Area | Covers |
| --- | --- | --- |
| `tests/unit/test_contracts.py` | unit | The largest suite (~58 KB). Frozen contract models, digests, the SubjectEnvelope allowlist, disclosure rules, terminal payload unions, and the negative cases that must be rejected. |
| `tests/unit/test_authority_crypto.py` | unit | ES256 keypair, challenge digest, and the `LocalWebAuthnVerifier` signature checks. |
| `tests/unit/test_authority_policy.py` | unit | `AuthorityPolicy` mode × action-risk matrix; critical actions always require a verified human. |
| `tests/unit/test_authority_subject.py` | unit | `HumanSubjectEnvelope` subjects and the anti-drift check that `subject_digest()` equals the kernel's `human_subject_digest()`. |
| `tests/unit/test_context.py` | unit | Context policy application and snapshot hashing. |
| `tests/unit/test_manifest.py` | unit | The legacy `ExperimentManifest` parsing and digest. |
| `tests/unit/test_provider.py` | unit | The default provider profile and the OpenAI Responses adapter shape. |
| `tests/integration/test_admission_and_evaluation.py` | integration | Admission fail-closed behavior (~20 KB): which capabilities, budgets, disclosure modes, and evaluation plans are rejected, and which pass. |
| `tests/integration/test_api.py` | integration | Launch-token auth (401 without the bearer token), the demo dashboard, and that the provider endpoint never leaks a secret. |
| `tests/integration/test_authority_flow.py` | integration | End-to-end enroll → challenge → confirm → persist with the local authenticator. |
| `tests/integration/test_checkpoint_repository.py` | integration | Checkpoint record persistence and boundary uniqueness. |
| `tests/integration/test_contract_api.py` | integration | Contract validate/register/decide over HTTP (~20 KB), including the 503 on human decisions. |
| `tests/integration/test_contract_cli.py` | integration | The same contract flow through the Typer CLI. |
| `tests/integration/test_contract_migration.py` | integration | Alembic migration against the models. |
| `tests/acceptance/test_demo_flow.py` | acceptance | The full offline `CRL-CTX-002` demo: two runs, one comparison, terminal `goal_state` per variant, and a bundle that verifies. |
| `tests/security/test_artifact_store.py` | security | Sensitive raw requires opt-in and is encrypted; restricted content is never persisted. |

`tests/conftest.py` provides a `repository` fixture backed by a temporary SQLite database. Property-based tests use hypothesis (declared in the `dev` extra).

## The offline benchmark must stay deterministic

`tests/acceptance/test_demo_flow.py` asserts exact outcomes: `head-truncation` scores 0 and ends `not_achieved`, `tail-preservation` scores 1 and ends `achieved`, outputs are `[REDACTED]`, and the exported bundle verifies. The `CRL-CTX-002` benchmark must run fully offline with no provider. A change that makes the demo need the network or produce different numbers is a regression, not a new result.

## Web and desktop Vitest suites

| Suite | Config | Environment | Includes |
| --- | --- | --- | --- |
| Web | `apps/web/vitest.config.ts` | `jsdom`, React plugin, `src/test/setup.ts` (jest-dom matchers) | `src/**/*.test.ts`, `src/**/*.test.tsx` |
| Desktop | `apps/desktop/vitest.config.ts` | `node` | `apps/desktop/src/**/*.test.ts` |

Run them with `pnpm test:web` and `pnpm test:desktop`, or both plus the contract check with `pnpm test`. The desktop suite includes `external-links.test.ts`, the verification ref for the Electron security baseline.

## The contract generation check

`pnpm check:contracts` regenerates and diffs the generated artifacts without writing them:

```bash
uv run python scripts/generate_schemas.py --check      # JSON Schema + OpenAPI, exits nonzero if stale
node scripts/generate_contract_types.mjs --check       # apps/web/src/generated/contracts.ts, throws if stale
```

CI runs these two checks in separate jobs (the Python job checks schemas, the Node job checks the TS types). If either is stale, the fix is `pnpm generate:contracts` followed by committing the regenerated files. See [tooling](tooling.md) for the generators and [reference: data models](../reference/data-models.md) for the schema index.

## The desktop handshake smoke test

`pnpm test:handshake` runs `scripts/smoke_desktop_handshake.mjs`, which spawns `evidrun serve --desktop-handshake`, sends a launch token over stdin, and asserts that an unauthenticated `/api/v1/health` returns 401 while an authenticated one returns 200. It is not part of `pnpm test`; run it when you touch the backend spawn or the handshake contract. See [security: Electron security](../security/electron-security.md).
