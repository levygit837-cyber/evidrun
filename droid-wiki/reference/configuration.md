# Configuration

Evidrun's configuration is small and code-first. Runtime settings come from `src/evidrun/shared/settings.py`, the provider profile from `src/evidrun/providers/profile.py`, and a few environment variables read at the entry points. There is no config file for application settings; `.env.example` documents only the provider variables.

## Settings

`Settings.load(data_dir=None)` builds an immutable `Settings` dataclass. The data directory is resolved in order: the explicit `--data-dir` argument, then `EVIDRUN_DATA_DIR`, then the `platformdirs` default (`user_data_path("Evidrun", "Evidrun")`). The resolved root is expanded and made absolute.

| Field | Derived from | Value |
| --- | --- | --- |
| `data_dir` | resolved root | The base data directory |
| `database_path` | `data_dir / "evidrun.db"` | SQLite database file |
| `artifacts_dir` | `data_dir / "artifacts"` | Artifact store root (CAS, vault, metadata) |
| `default_provider` | `ProviderProfile.load_default()` | The default provider profile (below) |
| `authority_enabled` | `EVIDRUN_AUTHORITY` in `{"1","true"}` | Whether the human authority router mounts |

`ensure_directories()` creates `data_dir` and `artifacts_dir` with mode `0o700`. See [systems: database](../systems/database.md) and [security: privacy and retention](../security/privacy-and-retention.md).

## Provider profile

`ProviderProfile.load_default()` builds the durable default from ADR 0008, with environment overrides.

| Field | Default | Override |
| --- | --- | --- |
| `id` | `cliproxyapi-local` | fixed |
| `display_name` | `CLIProxyAPI local` | fixed |
| `api` | `openai_responses` | fixed |
| `base_url` | `http://127.0.0.1:8318/v1` | `EVIDRUN_PROVIDER_BASE_URL` (trailing slash stripped) |
| `model` | `deepseek-v4-flash` | `EVIDRUN_PROVIDER_MODEL` |
| `reasoning_effort` | `max` | `EVIDRUN_PROVIDER_REASONING_EFFORT` (one of `none`, `low`, `medium`, `high`, `max`; invalid raises) |
| `local_only` | `true` | fixed |
| `credential_service` | `dev.evidrun.providers` | fixed |

Changing the durable default model, endpoint, or reasoning level requires a successor to ADR 0008, not just an env var. The env vars are runtime overrides. See [systems: providers](../systems/providers.md) and [background: design decisions](../background/design-decisions.md).

## Environment variables

| Variable | Read by | Default | Effect |
| --- | --- | --- | --- |
| `EVIDRUN_DATA_DIR` | `Settings.load` | platform default | Base data directory; isolates state and artifacts |
| `EVIDRUN_AUTHORITY` | `Settings.load` | unset (off) | `1`/`true` mounts the human authority router; otherwise human decisions fail closed |
| `EVIDRUN_PORT` | `evidrun.entrypoints.api.app:run` | `8765` | Port for `evidrun-api` / `create_app().run()` |
| `EVIDRUN_DEV_SERVER_URL` | Electron main, `desktop:dev` | unset | Dev renderer origin; when set, the window loads it and it becomes a trusted renderer URL |
| `EVIDRUN_DISABLE_DEVTOOLS` | `createMainWindow` | unset | When set, disables DevTools in the Electron window |
| `EVIDRUN_PROVIDER_BASE_URL` | `ProviderProfile.load_default` | `http://127.0.0.1:8318/v1` | Provider endpoint |
| `EVIDRUN_PROVIDER_MODEL` | `ProviderProfile.load_default` | `deepseek-v4-flash` | Provider model id |
| `EVIDRUN_PROVIDER_REASONING_EFFORT` | `ProviderProfile.load_default` | `max` | Reasoning effort; invalid value raises |
| `EVIDRUN_PROVIDER_API_KEY` | `ProviderCredentialStore` | unset | Ephemeral credential override for CI or Keychain-less environments; never commit it |

The `serve --host` and `serve --port` CLI options default to `127.0.0.1` and `8765`; the `--desktop-handshake` path ignores them and binds an ephemeral loopback port chosen after the handshake. See [how-to-contribute: debugging](../how-to-contribute/debugging.md) for using `EVIDRUN_DATA_DIR` and `EVIDRUN_AUTHORITY` in practice.

## Credential storage

Provider credentials resolve in order: `EVIDRUN_PROVIDER_API_KEY` if set, otherwise the system Keychain under the profile's `credential_service` and `id`. `ProviderCredentialStore.source()` reports `environment`, `system_keychain`, or `None`. The API and CLI expose the profile and whether a credential is present, never the credential itself.
