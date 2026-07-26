---
id: governance-documentation
type: governance
title: Governança documental
status: implemented
authority: normative
volatility: current
owner: core
created_at: 2026-07-22
updated_at: 2026-07-26
applies_to: docs
sources: []
supersedes: []
superseded_by: null
implementation_refs:
  - scripts/validate_docs.py
  - scripts/doc_validation.py
  - scripts/doc_claims.py
  - scripts/doc_relations.py
  - scripts/doc_artifacts.py
  - docs/claims.toml
verification_refs:
  - docs/_generated/manifest.json
  - docs/_generated/claims.json
---

# Governança documental

Frontmatter é canônico; o roteador em `docs/index.md` é normativo e autorado, enquanto o manifest é
gerado. IDs são únicos. ADR aceito é superseded, não reescrito. Research usa `observed_at` e
`review_due`. Roadmap não descreve comportamento atual.

`implemented` exige `implementation_refs`. `verified` exige também `verification_refs`. Referências
devem apontar para paths existentes. Âncoras `#symbol` em Python resolvem somente definições,
imports e bindings no escopo do módulo; métodos e nomes locais não são âncoras documentais. CI
executa o validador documental e falha em divergências.

Claims mecanicamente verificáveis vivem no registro tipado `docs/claims.toml`. Cada entrada nomeia
o documento, uma afirmação curta, o verificador determinístico e o valor esperado. O snapshot
`docs/_generated/claims.json` registra o observado; claim sem verificador permanece
`not-verifiable`. Validação mecânica não equivale a aprovação semântica aberta da prosa.

## Volatilidade

Todo documento declara exatamente uma volatilidade:

| Valor | Significado | Combinações permitidas |
| --- | --- | --- |
| `timeless` | invariantes, decisões e contratos independentes do estado momentâneo do repositório | autoridade `normative`, `informative` ou `non-normative` |
| `current` | descrição do comportamento ou layout implementado que deve acompanhar o código | autoridade `normative`, `informative` ou `non-normative` |
| `snapshot` | observação, hipótese ou intenção temporal que pode ficar obsoleta | obrigatória para autoridade `planning`, `research` e `incubation`; nunca `normative` |
| `generated` | projeção reproduzível de entradas canônicas | nunca `normative`; não ganha autoridade própria |

`scripts/validate_docs.py` rejeita valores desconhecidos e combinações impossíveis. Em particular,
planning, research e incubação não podem se declarar `timeless` ou `current`; documento normativo
não pode ser `snapshot` ou `generated`; e incubação não pode afirmar status `implemented` ou
`verified`.

O documento `docs/architecture/codebase-layout.md`, por combinar navegação atual e regras
arquiteturais, separa explicitamente invariantes, estado atual medido, alvo futuro e histórico.
Contagens de arquivos, linhas, tickets e commits não são mantidas à mão em documentos `timeless`.
Histórico de entrega fica no Git e no tracker.

## Seleção de contexto

[`docs/index.md`](../index.md) é um roteador por intenção. Cada perfil comum seleciona 3–5
documentos obrigatórios e declara opcionais, fontes proibidas para comportamento atual e um orçamento
warning-only em documentos/palavras. Exceder o orçamento exige justificativa, mas ainda não falha CI.

Planning, research e incubação nunca entram por padrão no contexto de uma tarefa de implementação.
O manifest gerado inventaria metadata; ele não torna um snapshot atual nem transforma referência em
prova.

Documentos são escritos em português brasileiro; IDs, rotas, schemas e filenames permanecem em
inglês ASCII estável.
