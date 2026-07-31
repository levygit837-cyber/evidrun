---
id: operations-security-incident-response
type: operations
title: Resposta a incidente de credencial
status: implemented
authority: normative
volatility: current
owner: security
created_at: 2026-07-31
updated_at: 2026-07-31
applies_to: repository
sources:
  - docs/security/logging-and-redaction.md
  - docs/security/threat-model.md
supersedes: []
superseded_by: null
implementation_refs:
  - scripts/check_secrets.py
  - secret-scan.toml
  - scripts/hooks/pre-push
  - .github/workflows/ci.yml
verification_refs:
  - tests/security/test_secret_scan.py
---

# Resposta a incidente de credencial

Ao detectar possível credencial, interrompa push, export e compartilhamento do material. Não copie o
valor para issue, PR, chat, log, fixture, snapshot, bundle ou comando registrado. Use somente regra,
path, linha, código estável e correlation ID para coordenar a resposta.

1. Revogue a credencial no provider de origem e emita outra por canal confiável. Rotação acontece no
   Keychain ou na variável de ambiente efêmera; nunca no repositório.
2. Determine o alcance sem imprimir o valor: arquivos afetados, commits, artifacts, bundles e
   destinos externos que receberam o conteúdo. Trate cópias exportadas separadamente, pois purge
   local não as alcança.
3. Remova o material da versão corrente. Reescrita de histórico, remoção remota e invalidação de
   bundles são ações humanas deliberadas, coordenadas conforme os repositórios e consumidores
   afetados; o scanner não executa essas ações.
4. Execute `uv run python scripts/check_secrets.py`. Depois rode os gates completos de `AGENTS.md`.
5. Registre a resolução sem o segredo: regra, superfícies atingidas, horário da revogação, sistemas
   rotacionados e referências seguras de incidente.

Uma allowlist não resolve incidente. Ela só é aceita para material intencional, sintético e
revisável com match exato; credencial comprometida deve ser removida e rotacionada.
