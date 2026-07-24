# Providers

The provider runtime is how Evidrun reaches a language model when a Study actually needs one. It is deliberately thin: a frozen profile that identifies the default provider, an adapter that speaks the OpenAI Responses API and pins the model and reasoning effort, and a credential store that keeps the API key out of code and logs. The [deterministic benchmark](../features/deterministic-benchmark.md) never touches any of this — CRL-CTX-002 runs offline with no provider at all.

## Directory layout

| File | Purpose |
| --- | --- |
| `src/evidrun/providers/profile.py` | `ProviderProfile` — the immutable provider identity and default loader. |
| `src/evidrun/providers/__init__.py` | Re-exports `ProviderProfile`. |
| `src/evidrun/infrastructure/providers/openai_responses.py` | `OpenAIResponsesProvider` — the HTTP adapter. |
| `src/evidrun/infrastructure/providers/credentials.py` | `ProviderCredentialStore` — Keychain/env secret access. |
| `docs/architecture/provider-runtime.md` | The normative architecture note (in Portuguese). |

## ProviderProfile

`ProviderProfile` is a frozen dataclass identifying the provider, protocol, endpoint, model, reasoning effort, and credential service. `load_default` builds the default from environment overrides:

```python
return cls(
    id="cliproxyapi-local",
    display_name="CLIProxyAPI local",
    api="openai_responses",
    base_url=os.environ.get("EVIDRUN_PROVIDER_BASE_URL", "http://127.0.0.1:8318/v1").rstrip("/"),
    model=os.environ.get("EVIDRUN_PROVIDER_MODEL", "deepseek-v4-flash"),
    reasoning_effort=cast(ReasoningEffort, reasoning),  # default "max"
    local_only=True,
    credential_service="dev.evidrun.providers",
)
```

The default is `cliproxyapi-local` with `deepseek-v4-flash` and `reasoning=max`, pointing at a local CLIProxyAPI on `127.0.0.1:8318/v1`. `AGENTS.md` treats this default as a decision fixed by ADR 0008 — changing it requires a successor ADR. `public_dict` exposes the profile fields for display; it never contains a secret.

## OpenAIResponsesProvider

`OpenAIResponsesProvider.invoke` sends a request to the `/responses` endpoint. It pins `model` and `reasoning` from the profile and only forwards a known allowlist of request fields:

```python
payload = {
    "model": self.profile.model,
    "input": provider_input,
    "reasoning": {"effort": self.profile.reasoning_effort},
}
for name in ("instructions", "max_output_tokens", "tools", "tool_choice"):
    if name in request:
        payload[name] = request[name]
```

A caller cannot silently substitute a different model or reasoning effort, and unknown request fields are dropped rather than passed through. `check` calls `list_models` and reports reachability, credential availability, whether the pinned model is in the catalog, and the catalog size, without generating any model output. `_request` attaches the bearer token, treats any HTTP status >= 400 as a `ProviderRequestError`, and requires a JSON-object response. Errors deliberately omit the prompt and response body to avoid leaking content. `extract_output_text` pulls text out of the response envelope shape.

## ProviderCredentialStore

`ProviderCredentialStore` resolves the API key from an ephemeral environment variable (`EVIDRUN_PROVIDER_API_KEY`) first, then the OS keychain (`keyring.get_password(profile.credential_service, profile.id)`). `require` raises `MissingProviderCredentialError` when no key is available; `set` writes to the keychain; `source` reports `environment`, `system_keychain`, or `None`. The store returns or reports the secret's location but the profile and status surfaces never render its value. This matches the `AGENTS.md` rule that API keys live only in the Keychain or an ephemeral environment variable and are never written to code, docs, logs, or bundles.

## CLI and API surfaces

The CLI exposes `provider status`, `provider set-key`, `provider doctor`, and `provider smoke`. `doctor` queries the authenticated catalog without generating a model response; `smoke` makes a minimal real call and can consume quota, so it does not run in CI or at desktop startup. The API serves the default profile identity and credential availability (never the key value). See [the API surface](../apps/api.md) and [the CLI](../apps/cli/index.md).

## Offline behavior

Because the secret is only ever read inside the Python process, and because the benchmark uses the scripted deterministic runner rather than a provider, `CRL-CTX-002` works with the provider entirely unavailable. Provider failures — missing key, model absent from the catalog, timeout, non-2xx HTTP — are explicit errors that never touch the offline path.

## Integration points

- The domain reaches a provider through `ProviderPort` in `src/evidrun/shared/ports.py`; `OpenAIResponsesProvider` is the adapter.
- A Study can name a `provider_profile_id` in its agent inventory; [admission](contracts/compiler.md) resolves it against the provider catalog and rejects an unknown profile.
- [run execution](run-execution.md) does not use a provider today; the scripted runner is provider-free.

## Entry points for modification

- Changing the default profile requires a successor ADR to ADR 0008, per `AGENTS.md`.
- A new provider API means a new adapter behind `ProviderPort`; keep the model/reasoning pinning and the known-field allowlist so callers cannot smuggle parameters.
- Never log or render the API key; route all access through `ProviderCredentialStore`.
