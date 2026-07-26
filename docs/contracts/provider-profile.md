---
id: contract-provider-profile-v1
type: contract
title: Provider Profile v1
status: implemented
authority: normative
volatility: timeless
owner: agents
created_at: 2026-07-22
updated_at: 2026-07-22
applies_to: provider-profile@1
sources: []
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun/providers/profile.py
  - src/evidrun/infrastructure/providers/credentials.py
verification_refs:
  - tests/unit/test_provider.py
---

# Provider Profile v1

Campos públicos:

```text
id
display_name
api
base_url
model
reasoning_effort
local_only
credential_service
```

Campos de projeção, nunca persistidos como segredo:

```text
default
credential_available
credential_source
```

O contrato não possui `api_key`. O valor é resolvido por `EVIDRUN_PROVIDER_API_KEY` ou Keychain,
nessa ordem. A API e a UI podem indicar presença e origem, mas não conseguem solicitar o valor.

O request Responses produzido pelo perfil default contém obrigatoriamente:

```json
{
  "model": "deepseek-v4-flash",
  "reasoning": {"effort": "max"},
  "input": "..."
}
```

Campos opcionais autorizados nesta versão: `instructions`, `max_output_tokens`, `tools` e
`tool_choice`. Campos arbitrários não são encaminhados.
