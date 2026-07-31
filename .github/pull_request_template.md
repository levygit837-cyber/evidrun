<!--
As quatro camadas vivem em `changes/<issue>.toml`, sob `[merge_gate]`, não neste texto.
Um comentário de PR é efêmero e não é verificável; o contrato é lido pelo CI.

Este template pede o resumo legível daquilo que o gate já checa. Se as duas fontes
divergirem, o contrato vence e o gate falha.
-->

Closes #

## O que mudou

<!-- O resultado observável, não a lista de arquivos. -->

## Contrato

- Contrato: `changes/<issue>.toml`
- Classificação:
- Revisão: <!-- orthogonal | proportional; orthogonal é obrigatória para breaking, remoção/quebra de capability ou normativa, e qualquer toque em contrato persistido -->
- CI commit: <!-- SHA em que a suíte completa rodou; nenhum arquivo entregue muda depois dele -->

## Quatro camadas

Cada linha conclui `passed` ou `not-applicable` com justificativa. `passed` sem evidência é
blocker. A evidência de CI pertence somente à última linha: usá-la nas três primeiras é
afirmar "CI verde, logo está tudo certo", que é exatamente o que o gate recusa.

| Camada | Conclusão | Evidência |
| --- | --- | --- |
| Spec — resultado, invariantes e fora de escopo atendidos | | |
| Standards — arquitetura, autoridade, segurança, docs, budgets | | |
| Verification — testes focais, contratos, regressões | | |
| CI — suíte determinística completa no commit candidato | | |

## Impacto

- capability:
- persisted_contract:
- normative:

## Fora de escopo

<!-- O que foi deliberadamente deixado de fora, e por quê. -->
