---
id: operations-desktop-release
type: operations
title: Build e release Electron
status: proposed
authority: normative
volatility: timeless
owner: desktop
created_at: 2026-07-22
updated_at: 2026-07-31
applies_to: apps/desktop
sources:
  - https://www.electronforge.io/guides/code-signing/code-signing-macos
  - github:issue/90
supersedes: []
superseded_by: null
implementation_refs:
  - apps/desktop/forge.config.cjs
  - src/evidrun/infrastructure/providers/credentials.py
verification_refs:
  - tests/unit/test_credential_lookup.py
---

# Build e release Electron

O release pipeline deve gerar o executável Python com PyInstaller para a mesma plataforma e
arquitetura, colocá-lo em `apps/desktop/resources/backend`, construir React/Main/preload e só então
executar Electron Forge.

macOS exige assinatura de nested binaries, Hardened Runtime e notarização. Credenciais ficam no
keychain/CI, nunca no repositório. DMG/ZIP não serão publicados até que instalação limpa, migration,
backup, rollback e verificação de assinatura passem.

## Credencial de provider em binário não assinado

Num binário PyInstaller não assinado, o Keychain do macOS trata o processo como solicitante
desconhecido e bloqueia `keyring.get_password` esperando uma autorização que um processo não
interativo nunca fornece. A chamada é FFI: não levanta e não retorna, então `try/except` em volta
dela não protege nada. `doctor` e `demo` ficavam pendurados indefinidamente.

A consulta agora roda em thread abandonável com espera limitada e reporta três resultados distintos:
`available`, `absent` (o backend respondeu e não possui credencial) e `unavailable` (o backend não
respondeu ou falhou). Somente `absent` reprova o check do `doctor`, porque um backend que não
responde não afirma nada sobre configuração.

A thread é `threading.Thread(daemon=True)` e não um `ThreadPoolExecutor`: o executor registra um
hook `atexit` que faz join nas workers, então uma worker presa no backend manteria o interpretador
vivo na saída e reproduziria o mesmo hang no shutdown. Isso foi observado durante a correção.

Assinar e notarizar remove a causa desta espera — o solicitante deixa de ser desconhecido — mas não
substitui o limite de tempo: um backend de credencial pode estar lento, travado ou ausente por
outros motivos, e nenhum comando de diagnóstico deve depender disso para terminar. As duas medidas
são complementares e o limite permanece necessário depois da assinatura.

`EVIDRUN_CREDENTIAL_TIMEOUT_SECONDS` ajusta a espera quando um backend legítimo é mais lento. Valor
inválido, zero ou negativo volta ao default. Nenhuma dessas saídas expõe segredo, conta consultada
ou mensagem do backend.
