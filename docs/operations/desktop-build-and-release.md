---
id: operations-desktop-release
type: operations
title: Build e release Electron
status: proposed
authority: normative
volatility: timeless
owner: desktop
created_at: 2026-07-22
updated_at: 2026-07-22
applies_to: apps/desktop
sources:
  - https://www.electronforge.io/guides/code-signing/code-signing-macos
supersedes: []
superseded_by: null
implementation_refs:
  - apps/desktop/forge.config.cjs
verification_refs: []
---

# Build e release Electron

O release pipeline deve gerar o executável Python com PyInstaller para a mesma plataforma e
arquitetura, colocá-lo em `apps/desktop/resources/backend`, construir React/Main/preload e só então
executar Electron Forge.

macOS exige assinatura de nested binaries, Hardened Runtime e notarização. Credenciais ficam no
keychain/CI, nunca no repositório. DMG/ZIP não serão publicados até que instalação limpa, migration,
backup, rollback e verificação de assinatura passem.

