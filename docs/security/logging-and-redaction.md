---
id: security-logging-redaction
type: security
title: Logging estruturado e redaction
status: implemented
authority: normative
volatility: timeless
owner: security
created_at: 2026-07-31
updated_at: 2026-07-31
applies_to: repository
sources:
  - docs/security/threat-model.md
  - docs/contracts/capture-and-retention.md
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun/security/logging.py
  - apps/desktop/src/main/secure-logging.ts
  - scripts/secret_scan
verification_refs:
  - tests/security/test_secure_logging.py
  - tests/security/test_secret_scan.py
  - apps/desktop/src/main/secure-logging.test.ts
---

# Logging estruturado e redaction

Todo registro operacional cruza um emissor próprio do runtime antes de chegar ao backend de log.
Python e Electron não compartilham implementação, mas aplicam a mesma allowlist fechada. Campo novo
é proibido até ser classificado e adicionado deliberadamente aos dois emissores quando aplicável.

## Campos permitidos

| Campo | Classificação | Uso |
| --- | --- | --- |
| `event_code` | public | Código estável do evento operacional. |
| `error_code`, `error_type` | public | Categoria segura; nunca mensagem, args ou traceback. |
| `status_code`, `exit_code`, `signal` | public | Estado numérico ou sinal do processo. |
| `process`, `operation`, `contract_type`, `bundle_version` | public | Dimensão operacional de enumeração curta. |
| `correlation_id`, `provider_id`, `worker_id`, `artifact_ref` | internal | Identidade operacional validada, sem conceder acesso ou autoridade. |

Valores textuais permitidos precisam respeitar o shape de identificador. Valor incompatível vira
`<redacted>`. Campos fora da allowlist são descartados. Exceções contribuem somente o nome do tipo;
`message`, `repr`, `args`, `cause`, traceback e payload do erro não são serializados.

São sempre proibidos: Authorization headers, API keys, cookies, ambiente completo, paths de dados,
URLs não classificadas, request/response brutos, prompts, Context Snapshots, SubjectEnvelopes,
EvaluatorEnvelopes e material `sensitive` ou `restricted`. O runtime ativo continua rejeitando
inputs `sensitive` e `restricted` antes da materialização; logging não é um caminho alternativo de
debug.

`actor`, username, role ou principal declarado não é campo permitido e nunca prova autoridade.
Correlação identifica operação, não pessoa. Autoridade humana continua exigindo
`HumanAttestationRecord` verificado.

## Scanner e allowlist

`scripts/check_secrets.py` analisa offline todos os arquivos rastreados pelo Git. O diagnóstico
contém regra, path e posição, nunca o valor encontrado. `secret-scan.toml` permite exceção somente
pela combinação exata de regra, path, linha e SHA-256 do match, acompanhada de motivo revisável.
Não existem marcadores amplos como `test`, `fake` ou `example` que desativem detecção.

Fixtures usam placeholders explícitos. A fixture positiva é a única exceção intencional e continua
detectável quando executada com a policy de teste sem allowlist.

## Evidence Bundle

Logs de export registram somente código, Run ou Comparison como correlação, operação e versão. Path
de saída e conteúdo do Bundle não entram no log. Redaction de observabilidade não modifica records,
checksums ou conteúdo canônico exportado e não transforma Bundle auditável em portátil ou replayable.
