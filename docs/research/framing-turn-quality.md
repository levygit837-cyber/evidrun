---
id: research-framing-turn-quality
type: research
title: Hipótese — turno de framing forçado e qualidade da resposta
status: draft
authority: research
volatility: snapshot
owner: evals
created_at: 2026-08-02
updated_at: 2026-08-02
applies_to: discovery/lab-agent-framing
sources:
  - user-conversation:2026-08-02-forcing-a-thinking-turn
  - docs/adr/0024-lab-agent-native-tool-runtime.md
  - docs/contracts/lab-agent-loop-v1.md
  - docs/contracts/lab-agent-tools-v1.md
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
observed_at: 2026-08-02
review_due: 2026-11-02
---

# Hipótese — turno de framing forçado e qualidade da resposta

> Estado: hipótese registrada, **não** decisão de produto. Nada aqui altera o ADR 0024 ou os
> contratos v1 do Lab Agent. O turno de framing não é parte do runtime decidido; ele é candidato a
> experimento quando o sistema executar o desenho que o mede.

## Origem

A pergunta veio de uma frustração concreta de uso: um agente que responde uma ideia incompleta em um
único passe de raciocínio, dá uma resposta direta e correta na superfície, e deixa de fora variáveis
que mudariam a conclusão. O pedido original foi "forçar mais um turno de thinking".

O reframe que a discussão produziu: um modelo de reasoning pensa uma vez por round-trip, e
round-trips pertencem ao loop, não ao modelo. `reasoning.effort` controla profundidade **dentro** de
um passe; a estrutura do loop controla **quantos** passes acontecem. Forçar raciocínio adicional é,
mecanicamente, recusar a resposta terminal até que uma precondição seja satisfeita.

O precedente existe no repositório e é do Subject, não do Lab Agent:

```python
# src/evidrun/runs/adapters/subject_responses.py:247
if state.tool_calls == 0:
    raise ValueError("real agent returned without using the required read tool")
```

O adapter recusa uma resposta final que não fez o trabalho. Não pede no prompt: verifica e rejeita.

## Pergunta do estudo

> Fazer o modelo declarar seu estado atual, citar referências e justificar por que aquele é seu
> último turno aumenta alguma métrica de qualidade da resposta?

A pergunta é sobre **mecanismo de loop**, não sobre prompt. Um pedido textual de "pense com cuidado"
é inverificável e desaparece quando o modelo está confiante; uma precondição de aceitação é código.

## Lacuna que a hipótese ataca

Os cinco budgets do [loop v1](../contracts/lab-agent-loop-v1.md) são todos **tetos**:
`max_tool_calls_per_turn`, `max_provider_round_trips_per_turn`, `max_wall_seconds_per_turn`,
`max_refusals_per_turn` e `max_output_tokens_per_round_trip`. Nenhum é piso.

O contrato impede o agente de trabalhar demais e não tem nada que o impeça de trabalhar de menos.
Essa assimetria é intencional na v1 — teto protege o humano de custo, e piso é critério de
completude, que depende do tipo de pedido e ainda não foi medido.

## Variável primária

A precondição de aceitação do terminal. Duas variants:

| Variant | Terminal aceito quando |
| --- | --- |
| baseline | o modelo para de pedir tool calls |
| candidate | o modelo emite um framing válido **e** justifica o encerramento |

Tudo o mais é mantido constante: mesmo Goal, mesmo Scenario, mesmo material de contexto, mesmo
provider profile, mesmo `reasoning.effort`, mesmo catálogo de tools, mesma base de instrução de
sistema.

O framing candidato é um artefato tipado, não prosa, e é validado pelo servidor:

| Campo | Recusado quando |
| --- | --- |
| variável primária | ausente ou múltipla |
| mantido constante | vazio |
| explicações rivais consideradas e descartadas | menos de duas, ou descarte sem motivo |
| critério de sucesso | não observável |
| o que falta saber | ausente quando o pedido é incompleto |
| justificativa de encerramento | ausente |

Um framing sem explicações rivais é recusado com remediação nomeada, o que produz o passe adicional
exatamente na dimensão que faltou — não um pedido genérico de mais esforço.

## Confounders declarados

A comparação é honesta somente se estes forem controlados ou declarados:

- **custo adicional**: a candidate gasta pelo menos um round-trip a mais por construção. Qualquer
  ganho precisa ser lido contra esse custo, não isolado dele;
- **verbosidade como proxy falso**: resposta mais longa não é resposta melhor. O grader não pode
  premiar extensão;
- **efeito de instrução versus efeito de recusa**: a candidate muda duas coisas ao mesmo tempo se o
  bloco de instrução também mudar. Para isolar o mecanismo, a instrução precisa ser idêntica e só a
  precondição de aceitação diferir — ou uma terceira variant separa os dois;
- **autoavaliação**: se o grader for o mesmo modelo, o resultado mede concordância consigo mesmo. A
  discussão sobre autocrítica registrou que ela só rende com verificação externa;
- **dificuldade do caso**: um pedido já completo não tem variável faltando, então o framing não tem o
  que descobrir. A matriz precisa separar pedido completo de pedido incompleto.

## Dimensões candidatas de qualidade

Nenhuma está implementada. Todas precisam ser observáveis sem julgamento aberto de prosa:

| Dimensão | Observável | Risco |
| --- | --- | --- |
| draft compila | `validate_draft` aceita na primeira tentativa | binária e barata; é a mais forte |
| variáveis rivais nomeadas | contagem de alternativas com motivo de descarte | contável, mas premiável por inflação |
| citação resolve | toda afirmação sobre execução tem `run:`, `event:` ou `artifact:` válida | forte; reusa refs reais |
| retrabalho humano | o humano aceita sem pedir correção | mede o que importa, mas exige humano na malha |
| custo por resposta aceita | tokens e round-trips até aceitação | o denominador correto para ler ganho |

A dimensão mais promissora é a primeira, porque o produto já tem oráculo determinístico:
`compile.controlled_slots_mismatch` e `compile.confounder_missing` sabem o que um desenho válido
exige. Iterar contra verificação real é diferente de iterar contra intuição.

## Por que não roda hoje

Esta é a ironia que a discussão expôs, e ela é registrada aqui em vez de escondida.

O experimento precisa de mais de um turno do Subject, e a admissão **rejeita** `max_turns > 1`. Ela
rejeita honestamente: o coordinator de turnos não existe. Promover essa capability exige o
coordinator com budget realmente aplicado, não afrouxar o check.

O [Mínimo Confortável](../planning/comfortable-minimum.md) já nomeia essa tensão: sem multi-turn, o
corredor entrega o laboratório e não entrega o experimento que o justifica. Este dossier é uma
instância concreta dela.

Outras dependências, todas fora do runtime atual:

- agregação sobre repetições com `pass@k` e `pass^k`, que não existem sem repetições;
- mais de um stage de evaluation, hoje rejeitado na admissão;
- `human_review` como stage, cujo branch humano não é exercitado por teste.

## O que este dossier não afirma

- não afirma que o turno de framing melhora a qualidade: essa é a hipótese, não um achado;
- não afirma que o mecanismo é decisão de produto: o ADR 0024 não o inclui;
- não afirma que qualquer dimensão acima é a métrica correta: são candidatas;
- não afirma que `reasoning.effort` por turno resolve o problema. Ele aprofunda o passe existente e
  não cria um segundo; hoje vem do profile e não é sobreponível por request, porque
  `OpenAIResponsesProvider.invoke` monta `reasoning` a partir de `self.profile` e não repassa o campo
  do request.

## Argumento a favor, hoje

O argumento disponível é **mecânico**, não empírico: uma precondição de aceitação garante o passe
adicional, enquanto uma instrução textual apenas o solicita. Essa distinção é verificável sem medir
qualidade.

O argumento empírico — que o passe adicional produz resposta melhor — permanece hipótese até um Study
medir. Manter os dois separados é o que este repositório exige de qualquer claim.

## Próximo passo

Quando multi-turn admitido existir, este dossier vira `ExperimentManifest` com Study, Scenario, duas
variants e repetições, pelo caminho normal de autoria. Até então ele permanece `research`, sem
`implementation_refs`, e não é citado como comportamento.
