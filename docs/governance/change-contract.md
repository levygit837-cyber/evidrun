---
id: governance-change-contract
type: governance
title: Contrato de mudança e gate de escopo
status: implemented
authority: normative
volatility: current
owner: core
created_at: 2026-07-31
updated_at: 2026-07-31
applies_to: repository
sources:
  - docs/planning/README.md
  - docs/templates/agent-workstream.md
supersedes: []
superseded_by: null
implementation_refs:
  - scripts/check_change_contract.py
  - scripts/change_contract
  - scripts/change_contract/merge_gate.py
  - docs/templates/change-contract.toml
  - .github/pull_request_template.md
  - .github/workflows/ci.yml
verification_refs:
  - tests/unit/test_change_contract.py
  - tests/unit/test_merge_gate.py
  - tests/unit/fixtures/merge-gate
---

# Contrato de mudança e gate de escopo

O contrato de mudança registra a intenção verificável de uma issue antes da implementação. Ele ajuda
o agente a planejar, reconhecer descobertas e entregar um diff explicável. Não é uma lista rígida de
arquivos que substitui julgamento: paths esperados orientam; somente proibições e riscos declarados
falham fechado.

Cada issue executada em branch/worktree própria adiciona `changes/<issue>.toml` a partir do
[template](../templates/change-contract.toml). O arquivo permanece no histórico depois do merge. A
CI descobre somente o contrato novo ou alterado desde o merge-base, portanto contratos antigos não
são reaplicados a diffs futuros.

## Interface do contrato

O schema v1 suporta `refactor`, `behavior-compatible`, `feature`, `breaking`, `docs-only` e
`generated`. Todo contrato declara:

- identidade da issue, classificação, base e resultado esperado;
- fatos confirmados, perguntas abertas/resolvidas e condições de parada;
- impactos em capability, contrato persistido e documentação normativa;
- paths esperados, proibidos, preexistentes, gerados e expansões justificadas;
- interfaces, erros e invariantes preservados;
- testes focais e gates completos.

`refactor` também exige `[oracle]` de `characterization` ou `equivalence`, com comando, evidência e
as preservações estruturadas `capability`, `persisted-contract` e `fail-closed`. O comando do
oráculo precisa constar nos testes focais. Um refactor não pode declarar adição/remoção de
capability, mudança persistida ou normativa. Se isso for necessário, reclassifique a mudança em vez
de esconder escopo.

Pergunta aberta com `affects_semantics=true` é blocker de planejamento. Pergunta sem efeito semântico
pode permanecer aberta e visível durante exploração.

## Merge gate em quatro camadas

CI verde prova que os checks rodaram. Ela não registra se o resultado atendeu a especificação, se a
arquitetura se manteve, nem se a verificação foi suficiente. São três conclusões diferentes, e
`[merge_gate]` as mantém separadas, na ordem de leitura:

1. **Spec** — resultado, invariantes e fora de escopo atendidos;
2. **Standards** — arquitetura, autoridade, segurança, docs e budgets;
3. **Verification** — testes focais, contratos, regressões e evidência independente;
4. **CI** — suíte determinística completa no commit candidato.

Cada camada conclui `passed` ou `not-applicable`. As quatro são obrigatórias: um contrato que declara
`[merge_gate]` sem alguma delas é inválido.

Duas regras carregam o peso. `passed` sem evidência é blocker, então `passed` nunca fica vazio. E as
três primeiras camadas não podem citar a execução de CI: reusar evidência `run:` nelas é exatamente a
substituição "CI verde, logo está tudo certo" que o gate existe para recusar. A camada `ci` também
nunca pode ser `not-applicable`, porque a suíte sempre roda.

Evidência tem a forma `<kind>:<referência>`, com kind em `diff`, `test`, `log`, `review` ou `run`.
`not-applicable` exige `justification` e dispensa evidência: é conclusão honesta quando justificada.

### Profundidade de revisão

`review` declara `orthogonal` (revisão independente de quem não escreveu a mudança) ou
`proportional` (revisão dimensionada à mudança). A profundidade mínima é derivada do risco declarado,
nunca do tamanho do diff: um diff pequeno pode remover capability e um grande pode ser um rename.

`orthogonal` é obrigatória quando a classificação é `breaking`, quando capability ou documentação
normativa é `removed`/`breaking`, ou quando o contrato persistido muda de qualquer forma. Declarar a
profundidade não é executá-la: com `orthogonal`, alguma camada precisa apontar evidência `review:`.

### Identidade do commit coberto

`ci_commit` é o SHA em que a suíte completa rodou. Exigir `ci_commit == HEAD` seria insatisfazível,
porque commitar o contrato que registra a execução move o HEAD para além dela. A regra verificável é
outra: nenhum arquivo **entregue** pode mudar depois desse commit. O próprio contrato pode, porque
registrar a evidência não invalida a evidência.

Commit desconhecido pelo repositório bloqueia; entrega alterada depois da execução bloqueia e nomeia
os paths afetados.

### Adoção

Contrato sem `[merge_gate]` produz `merge_gate.absent`, warning. No gate de merge, `--strict-warnings`
o transforma em falha, mas contratos escritos antes desta seção continuam carregáveis até serem
atualizados.

O [template de PR](../../.github/pull_request_template.md) pede o resumo legível das mesmas camadas.
Ele não é a fonte: um comentário de PR é efêmero e não verificável. Se o texto divergir do contrato,
o contrato vence e o gate falha. Há um exemplo carregável por classificação em
`tests/unit/fixtures/merge-gate/`.

## Escopo que orienta sem limitar

`scope.expected` descreve o melhor plano conhecido. Um path fora dele produz
`scope.unplanned_path`, warning por default, com a próxima ação de adicionar
`[[scope.expansions]]`. A emenda registra patterns e uma rationale concreta; não é justificativa
retroativa vaga.

`scope.forbidden` é deliberadamente diferente: tocar um path explicitamente proibido bloqueia. O
agente precisa parar ou emendar o contrato antes de continuar. Segredo de alta confiança e mudança
normativa/persistida declarada como `none` também bloqueiam. Essas proteções também são aplicadas a
paths marcados como preexistentes, antes de excluí-los da entrega.

`scope.preexisting` registra paths sujos observados antes da task. Eles aparecem no relatório, mas
são excluídos da entrega. Arquivos untracked aparecem em `untracked_not_delivery` e nunca contam como
resultado; o humano/agente precisa adicioná-los intencionalmente ao índice Git.

## Semântica Git

O checker calcula `git merge-base <base_ref> HEAD`; nunca compara somente com a ponta atual da base.
Ele combina o diff commitado desde esse ancestral com mudanças staged/unstaged de arquivos já
rastreados. Rename, copy e delete preservam status e paths de origem/destino. A worktree não precisa
estar limpa.

Uso local:

```bash
uv run python scripts/check_change_contract.py --contract changes/50.toml
uv run python scripts/check_change_contract.py --contract changes/50.toml --format json
```

Uso de CI/discovery:

```bash
uv run python scripts/check_change_contract.py --discover --base-ref origin/main --strict-warnings
```

Exit `0` significa nenhum blocker; warnings continuam visíveis. Exit `1` significa blocker. Exit `2`
significa contrato ou estado Git inválido. Localmente, `--strict-warnings` é opt-in para não limitar
a exploração. No gate de merge ele é obrigatório: um path descoberto continua warning, mas exige a
emenda explícita antes do handoff.

## O que o gate prova e não prova

O gate prova identidade do merge-base, cobertura de paths, proibições explícitas, declaração de
impacto por famílias sensíveis, disciplina do oráculo e ausência de alguns formatos de segredo de
alta confiança nas linhas adicionadas. A autoridade normativa de documentos alterados é lida do
frontmatter atual ou da versão no merge-base. O diagnóstico de segredo nunca inclui o valor
encontrado.

Sobre o merge gate, ele prova estrutura e disciplina de citação: as quatro camadas presentes, nenhuma
conclusão `passed` vazia, nenhuma das três primeiras camadas citando a execução de CI, profundidade de
revisão compatível com o risco declarado, e uma execução de CI que ainda cobre a entrega.

Ele não prova que a conclusão declarada em cada camada é verdadeira. Um agente pode apontar um teste
que não exercita o ramo relevante ou uma review superficial. O gate impede a substituição estrutural
— tratar CI verde como prova das outras três camadas — e força cada conclusão a nomear algo
inspecionável. Julgar a qualidade daquilo que foi apontado continua sendo trabalho humano.

Ele também não prova que toda mudança semântica foi percebida, que um teste é suficiente ou que um
novo comportamento não constitui capability. O scanner de secrets completo e a política de redaction
pertencem à issue dedicada; este gate implementa somente a defesa mínima exigida para não aprovar
segredo evidente.
