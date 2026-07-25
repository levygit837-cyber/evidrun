---
id: adr-0017
type: adr
title: Orçamento estrutural e costuras nomeadas por capacidade
status: accepted
authority: normative
owner: core
created_at: 2026-07-24
updated_at: 2026-07-24
applies_to: repository
sources:
  - docs/adr/0003-modular-monolith.md
  - docs/architecture/codebase-layout.md
supersedes: []
superseded_by: null
implementation_refs:
  - scripts/check_code_budget.py
  - code-budget.toml
  - .github/workflows/ci.yml
verification_refs:
  - tests/unit/test_code_budget.py
---

# Contexto

O ADR 0003 decidiu monólito modular por capacidade e continua válido. Ele não diz nada sobre o
tamanho das unidades dentro de cada capacidade, e a codebase derivou: em 2026-07-24, seis arquivos
carregam 8.500 das ~22.000 linhas de Python, com
`src/evidrun/infrastructure/database/repository.py` em 2.942 linhas e 50 métodos públicos numa classe
só, e `AdmissionService.admit` em 567 linhas numa função só.

A consequência não é estética. Uma capability nova exige hoje um `if` novo dentro de `admit` e um
método novo dentro de `Repository`, o que serializa frentes de trabalho que são logicamente
independentes: duas pessoas ou dois agentes adicionando capabilities diferentes editam o mesmo trecho
do mesmo arquivo. E um arquivo dessa escala não cabe numa janela de contexto sem paginação, o que
degrada tanto revisão humana quanto trabalho de agente.

# Decisão

Adotamos um orçamento estrutural verificado automaticamente, com ratchet, e um layout-alvo de
costuras nomeadas por capacidade descrito em `docs/architecture/codebase-layout.md`.

O orçamento é declarado em `code-budget.toml` e verificado por `scripts/check_code_budget.py`:

| Grupo | Limite de arquivo | Limite de função | Métodos públicos por classe |
| --- | --- | --- | --- |
| `source` (`src/**/*.py`, `apps/**/*.{ts,tsx}`, `scripts/*.{py,mjs}`) | 500 | 120 | 25 |
| `tests` (`tests/**/*.py`, `apps/**/*.test.{ts,tsx}`) | 800 | sem limite | sem limite |
| `exempt` (gerados e lockfiles) | sem limite | sem limite | sem limite |

O teto de 500 linhas não é uma medida de qualidade. É um gatilho de revisão: um arquivo que passa de
500 linhas está quase sempre escondendo uma costura que ninguém nomeou. O número certo é o menor que
não obriga a fatiar código coeso, e 500 é isso para este repositório — 76 dos 93 arquivos de código
já cabem em 150 linhas, e a mediana não é pressionada por esse teto.

O limite de função (120) e de métodos públicos (25) são a parte que realmente morde. Um arquivo de
400 linhas com uma função de 380 é pior que um arquivo de 600 bem fatiado, e uma classe com 50
métodos públicos é rasa por definição: a interface é tão complexa quanto a implementação.

**Ratchet, não big bang.** Os 14 arquivos que já violavam a política entraram numa tabela
`[baseline]` com sua métrica medida. Uma métrica no baseline pode encolher, nunca crescer. Quando ela
volta para dentro do orçamento do grupo, o gate exige a remoção da entrada. O ratchet só aperta.

**Aviso antes de violação.** Uma métrica que passa de `warn_at_ratio` do orçamento do grupo (default
0.8, declarável por grupo em `code-budget.toml`) é reportada como AVISO e **não** altera o exit code.
A razão de não falhar é operacional: aviso que quebra CI vira ruído que alguém silencia, e o valor
aqui é que um arquivo recém-extraído perto do teto seja visto antes de a próxima capability empurrá-lo
de volta ao `[baseline]`. A superfície escolhida é a saída do próprio gate, no job Python que já roda
em todo push — não um comentário de PR, que só apareceria depois do trabalho estar feito. Como a
medição parte de `git ls-files`, arquivo fora do índice não é medido, e portanto não avisa.

**Custo zero de CI.** O gate roda como um passo do job Python já existente, não como job novo, e há
um hook `pre-push` opcional (`scripts/install_git_hooks.py`) que faz a mesma verificação localmente.
No mesmo movimento, o trigger `on: push` passou a filtrar `branches: [main]`, porque um PR de branch
do próprio repositório disparava os dois workflows e pagava minutos duplicados num repositório
privado.

# Consequências

Estrutura passa a ser verificável, não opinião de revisão. Uma extração que quebra um arquivo grande
em unidades semânticas é confirmada pelo gate; um arquivo que volta a crescer é rejeitado antes do
merge.

O gate mede tamanho, não desenho. Ele não sabe distinguir uma decomposição boa de sete arquivos de
70 linhas que só empurram bytes. Ele também não impõe direção de import: as direções proibidas em
`docs/architecture/codebase-layout.md` continuam sendo responsabilidade de revisão.

A extração dos arquivos hoje no baseline é obrigatoriamente **neutra em comportamento**. Nenhuma
capability hoje rejeitada pode ser promovida: mesma decisão, mesmo código de rejeição, mesma mensagem
observável. Como a suíte atual não asserta `reason.code` nem `reason.detail`, cada extração de
admissão exige um oráculo de equivalência antes de mover código.

Uma decomposição que exija mudança normativa — outra ordem de eventos, outro conteúdo de record
persistido, outro contrato transacional — não é feita por ajuste de texto deste ADR. Ela exige um ADR
sucessor.
