---
id: adr-0008
type: adr
title: CLIProxyAPI com DeepSeek v4 Flash como provider padrão
status: accepted
authority: normative
owner: agents
created_at: 2026-07-22
updated_at: 2026-07-22
applies_to: providers/default@1
sources: []
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun/providers/profile.py
  - src/evidrun/infrastructure/providers/openai_responses.py
  - src/evidrun/infrastructure/providers/credentials.py
verification_refs:
  - tests/unit/test_provider.py
---

# Decisão

O provider padrão durável do Evidrun é `cliproxyapi-local`, acessível por
`http://127.0.0.1:8318/v1` e compatível com a OpenAI Responses API. O modelo padrão é
`deepseek-v4-flash` e toda invocação por esse perfil envia `reasoning.effort=max`.

“Durável” significa que essa configuração permanece como default entre reinicializações e versões
até ser substituída por um ADR explícito. Não significa disponibilidade externa garantida: container,
credenciais, upstream e catálogo ainda podem falhar.

# Segredos

Endpoint, model ID e reasoning são configuração normativa versionada. A API key fica no Keychain do
sistema sob o serviço `dev.evidrun.providers` e usuário `cliproxyapi-local`. O override
`EVIDRUN_PROVIDER_API_KEY` existe para CI e ambientes sem Keychain, mas nunca deve ser commitado.

# Autoridade e isolamento

O adapter implementa `ProviderPort`; domínio, manifests e benchmark determinístico não importam
HTTP nem conhecem CLIProxyAPI. A presença do provider não habilita automaticamente o Lab Agent nem
transforma seu output em evidência aceita.

# Consequências

- O Electron pode recuperar a credencial pelo sidecar Python sem entregar a chave ao renderer.
- O modelo e o reasoning efetivos ficam visíveis na UI, CLI e API, sem revelar a credencial.
- Mudanças futuras de modelo, endpoint default ou nível de reasoning exigem novo ADR ou supersession.
- Runs reais deverão registrar provider profile, model ID e reasoning observável nos eventos.
