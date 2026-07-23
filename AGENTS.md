# Instruções para agentes

## Fonte de verdade

- Leia `docs/index.md` antes de alterar contratos ou arquitetura.
- ADRs aceitos não são reescritos para mudar uma decisão: crie um ADR sucessor.
- Não descreva roadmap como comportamento implementado.
- Resultados de runs não viram fatos sem referências `run:`, `event:` ou `artifact:`.

## Fronteiras

- Domínio Python não importa FastAPI, SQLAlchemy, OpenAI, Electron ou React.
- Electron Main gerencia lifecycle e capacidades desktop; não implementa domínio.
- Renderer nunca importa `electron`, `node:*` ou bindings nativos.
- Subject Agent não recebe chats, hidden graders ou evidência fora do manifest.
- Lab Agent cria drafts; aceitação e efeitos externos pertencem ao humano.
- O provider default é `cliproxyapi-local` com `deepseek-v4-flash` e `reasoning=max`; alterá-lo
  exige ADR sucessor ao ADR 0008.
- API keys permanecem no Keychain ou em variável de ambiente efêmera. Nunca grave credenciais em
  código, docs, ledger, bundles, fixtures, snapshots ou logs.

## Verificação mínima

```bash
uv run pytest
uv run ruff check .
uv run pyright
pnpm typecheck:web
pnpm typecheck:desktop
pnpm test
pnpm build
uv run python scripts/validate_docs.py
```

O benchmark `CRL-CTX-002` deve continuar offline e determinístico.
