---
id: architecture-provider-runtime
type: architecture
title: Runtime de providers
status: implemented
authority: normative
owner: agents
created_at: 2026-07-22
updated_at: 2026-07-26
applies_to: providers@1
sources: []
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun/providers/profile.py
  - src/evidrun/infrastructure/providers/openai_responses.py
  - src/evidrun/entrypoints/cli/app.py
  - src/evidrun/entrypoints/api/app.py
verification_refs:
  - tests/unit/test_provider.py
  - tests/integration/test_api.py
---

# Runtime de providers

O perfil padrão é carregado pelo Python sidecar e permanece fora do domínio. Ele identifica provider,
protocolo, endpoint, modelo, reasoning e estratégia de credencial. O adapter só aceita campos de
request conhecidos e fixa `model` e `reasoning` pelo perfil; callers não os substituem silenciosamente.

```text
ResponsesReadAgentAdapter (SubjectAdapter)
→ ProviderPort
→ OpenAIResponsesProvider
→ CLIProxyAPI em 127.0.0.1:8318/v1
→ deepseek-v4-flash com reasoning=max
```

## Superfícies

- CLI: `provider status`, `set-key`, `doctor` e `smoke`.
- API: `/api/v1/providers` e `/api/v1/providers/default`.
- UI: identidade do default e disponibilidade da credencial, nunca o seu valor.
- Keychain: segredo recuperado somente no processo Python.

`provider doctor` consulta o catálogo autenticado sem gerar resposta de modelo. `provider smoke`
realiza uma chamada mínima e pode consumir quota; por isso não roda no CI nem no startup do desktop.

## Falhas

Ausência de chave, modelo ausente do catálogo, timeout e HTTP não bem-sucedido são erros explícitos.
O adapter não inclui prompt ou corpo de erro em exceptions para reduzir vazamento de conteúdo.
O benchmark `CRL-CTX-002` continua funcionando offline mesmo com o provider indisponível.
