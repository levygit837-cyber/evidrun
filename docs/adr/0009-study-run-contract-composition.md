---
id: adr-0009
type: adr
title: Study unificado e composição canônica de Runs
status: accepted
authority: normative
volatility: timeless
owner: core
created_at: 2026-07-23
updated_at: 2026-07-26
applies_to: contracts/study-run@1
sources:
  - docs/product/run-laboratory-concept.md
  - docs/research/run-scenario-discovery/comparison.md
supersedes: []
superseded_by: null
implementation_refs:
  - src/evidrun/contracts
  - src/evidrun/infrastructure/database
  - src/evidrun/runs/service.py
verification_refs:
  - tests/unit/test_contract_revisions.py
  - tests/unit/test_contract_compilation.py
  - tests/unit/test_contract_admission.py
  - tests/integration/test_contract_api.py
---

# Decisão

O Evidrun usa `StudyRevision` como raiz de autoria para hipóteses controladas, avaliações de
capacidade, diagnósticos, regressões, investigações qualitativas e explorações abertas. A expansão
determinística `scenarios × variants × repetitions` produz `RunSpec`s atômicos. Cada spec contém um
único cenário, uma única variant e um índice de repetição.

Uma Run nova é formada por quatro fontes complementares, não por um documento mutável:

1. `RunSpec`, que fixa o que deveria ser executado;
2. `AdmissionRecord`, que registra o que foi resolvido e autorizado;
3. `RunRecord`, que liga a tentativa ao spec e à admissão exatos;
4. `RunEvent`, que registra em ledger append-only o que efetivamente aconteceu.

Checkpoints e avaliações são registros imutáveis ancorados ao ledger. Status, totais, scorecards,
timelines e grafos são projeções reconstruíveis.

# Fronteiras semânticas

- `StudyIntent` pertence ao laboratório; `Goal` orienta o Subject Agent.
- Toda Run possui Goal. Exploração aberta usa `bounded_exploration` e uma condição terminal limitada.
- Variants pré-Run são irmãs e substituem apenas slots tipados. Não existe JSON Patch genérico.
- Repetição ou retry cria nova Run; derivação futura por checkpoint também deverá criar nova Run.
- Requisitos de agente permanecem separados do inventário efetivamente resolvido na admissão.
- Avaliações são vetoriais. Score agregado só existe com projector declarado pelo plano.
- Protocolo em grafo pode ser validado, mas o runtime atual o rejeita como não suportado.
- Checkpoint atual é evidência auditável; não implica restore, replay ou estado privado recuperável.
- Extensões referenciam schema e artifact registrados. O core não usa `dict[str, Any]` como payload
  de domínio.

# Compatibilidade

O `Experiment Manifest v1`, o envelope `Run Event v1` e o `Evidence Bundle v1` permanecem válidos.
O adapter legado cria a nova composição sem mudar o parser ou os digests históricos. Exports novos
usam Evidence Bundle v2. `GradeRow` permanece uma projeção de compatibilidade.

# Autoridade

Revisions são imutáveis. O Lab Agent pode criar drafts; apenas um ator humano cria decisão de
aceitação, rejeição ou supersession. O provider default definido pelo ADR 0008 não muda.

# Consequências

- Referências incluem tipo, identidade lógica, revisão e digest.
- Falha de capability obrigatória, policy, workspace ou interação rejeita a admissão antes da Run.
- O `SubjectEnvelope` é compilado separadamente e exclui Intent, hipótese, outras variants, hidden
  inputs, chats, credenciais e decisões internas.
- Capacidade representável não é apresentada como capacidade executável.
