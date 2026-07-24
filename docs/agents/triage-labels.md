---
id: agents-triage-labels
type: guide
title: Labels de triagem das agent skills
status: accepted
authority: informative
owner: core
created_at: 2026-07-23
updated_at: 2026-07-23
applies_to: repository
sources: []
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
---

# Labels de triagem

As skills usam cinco funções canônicas de triagem. Este arquivo mapeia essas funções para as strings de labels reais usadas no rastreador de issues deste repositório.

| Label em mattpocock/skills | Label em nosso rastreador | Significado                              |
| -------------------------- | -------------------- | ---------------------------------------- |
| `needs-triage`             | `needs-triage`       | O mantenedor precisa avaliar esta issue  |
| `needs-info`               | `needs-info`         | Aguardando mais informações do relator   |
| `ready-for-agent`          | `ready-for-agent`    | Totalmente especificada, pronta para um agente AFK |
| `ready-for-human`          | `ready-for-human`    | Requer implementação humana              |
| `wontfix`                  | `wontfix`            | Não será atendida                        |

Quando uma skill mencionar uma função (por exemplo, "aplique a label de triagem pronta para AFK"), use a string de label correspondente nesta tabela.

Edite a coluna da direita para corresponder ao vocabulário que você realmente usa.
