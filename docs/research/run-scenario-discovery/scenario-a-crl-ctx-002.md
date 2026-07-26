---
id: research-run-scenario-a-crl-ctx-002
type: research
title: Dossier A — CRL-CTX-002 determinístico
status: draft
authority: research
volatility: snapshot
owner: core
created_at: 2026-07-22
updated_at: 2026-07-22
applies_to: discovery/run-contracts/scenario-a
sources:
  - user-conversation:2026-07-22-scenario-oriented-discovery
  - repository:benchmark/crl-ctx-002@1
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
observed_at: 2026-07-22
review_due: 2026-10-22
---

# Dossier A — CRL-CTX-002 determinístico

> Estado: descrição de discovery, não um novo manifest. Este dossier documenta o benchmark atual
> sem alterar `ExperimentManifest v1`, `CRL-CTX-002@1`, seu runner ou seu grader.

## Estado e pergunta do discovery

| Item | Declaração |
| --- | --- |
| Capacidade atual | Executável pelo runtime determinístico existente |
| Natureza | Problema simples, offline e com oracle conhecido |
| Pergunta | O conceito mínimo de Run representa uma comparação de Context Policy sem carregar módulos não usados? |
| Evidence mode | `prospective_controlled` |
| Unidade comparada | Duas Runs, uma por variant, com `context_policy` como variável primária |

Fontes de verdade atuais:

- cenário: `benchmarks/scenarios/crl-ctx-002/scenario.yaml`;
- experimento: `benchmarks/experiments/crl-ctx-002-demo.yaml`;
- runner: `src/evidrun/subject_runners/scripted.py`;
- grader: `src/evidrun/evaluations/deterministic.py`;
- verificação: `tests/acceptance/test_demo_flow.py`.

## Intenção do estudo

A intenção pertence ao laboratory workspace: verificar se preservar o final de um log longo torna a
causa-raiz observável para o Subject Runner. Ela orienta hipótese, comparação e interpretação, mas
não é enviada ao Subject Runner como instrução adicional.

Hipótese predefinida: a policy que preserva o final do log deve expor o marcador decisivo; a policy
que preserva o início deve omiti-lo.

## Goal

O Goal recebido pelo Subject Runner é:

> Identifique a causa-raiz do incidente usando somente o log fornecido e cite a evidência.

O estado observável de conclusão é uma resposta terminal. O Goal não contém score, expected answer,
regra de comparação nem linguagem de aprovação.

Constraints:

- usar apenas o Context Snapshot composto a partir da fixture;
- não acessar rede, filesystem adicional, tools ou conhecimento externo;
- citar a linha de evidência quando a causa estiver observável;
- produzir uma única resposta terminal.

## Ambiente e workspaces

### Laboratory workspace

Contém a intenção, hipótese, variants, expected answer, grader, comparação e interpretação. Nenhum
desses dados ocultos é montado no contexto do Subject Runner.

### Execution workspace

É efêmero e somente leitura. Contém apenas o Goal compilado e o conteúdo selecionado da fixture pela
Context Policy da variant. Não há chat do laboratório, credenciais, rede, ferramentas ou arquivos
mutáveis.

| Propriedade de ambiente | Valor definido |
| --- | --- |
| Runner | `scripted-log-investigator-v1` |
| Rede | Desabilitada |
| Fixture | `benchmarks/scenarios/crl-ctx-002/fixtures/long.log` |
| Repetições | `1` |
| Budget | `max_wall_seconds: 5` |
| Seed strategy | Determinística |

## Inputs e interação

| Input | Classe | Visibilidade | Lifecycle |
| --- | --- | --- | --- |
| Goal | Instrução compilada | Subject Runner | Definição pré-Run |
| `long.log` | Fixture versionada | Apenas recorte selecionado para o Subject Runner | Definição pré-Run |
| Context Policy | Configuração da variant | Composer; identificador auditável | Definição pré-Run |
| Context Snapshot | Entrada efetivamente entregue | Subject Runner e evidência autorizada | Registro de runtime |
| `DB_POOL_EXHAUSTED` esperado | Hidden grader data | Grader e humano | Definição pré-Run protegida |

Não há system prompt independente nem protocolo condicional. A interação consiste em Goal mais um
Context Snapshot e termina na primeira saída. A forma exata entregue deve continuar registrada pelo
lifecycle de contexto existente.

## Aplicabilidade de capabilities

| Capability | Aplicabilidade | Motivo |
| --- | --- | --- |
| Provider real | Omitida por desenho | O runner é determinístico e offline |
| Tools | Omitidas por desenho | A fixture é a única entrada permitida |
| Skills | Omitidas por desenho | Não há resolução ou invocação de skill |
| Artifacts produzidos | Omitidos por desenho | A resposta e a evidência estruturada bastam |
| Findings | Omitidos por desenho | O cenário avalia um resultado exato, não discovery aberto |
| Checkpoints | Omitidos por desenho | Existe apenas uma resposta terminal |
| Fork | Omitido por desenho | A comparação nasce de variants predefinidas |

A ausência desses módulos é parte do cenário mínimo; não deve ser compilada como coleções vazias ou
campos `null` em um futuro contrato composto.

## Evaluation plan

### Grader determinístico

`exact-root-cause-v1` exige simultaneamente:

1. `DB_POOL_EXHAUSTED` na resposta;
2. `DB_POOL_EXHAUSTED` em pelo menos uma evidência citada.

O resultado por Run é binário: score `1.0` e `passed: true` quando ambos os predicados são atendidos;
score `0.0` e `passed: false` caso contrário.

### Métricas e comparação

| Definição pré-Run | Observação canônica de runtime | Projeção derivada |
| --- | --- | --- |
| Presença da causa na resposta | Grade do grader | Score exibido |
| Presença da causa na evidência | Evidências referenciadas pela grade | Explicação de pass/fail |
| Policy e limite de caracteres | Context Snapshot | Context Diff |
| Pareamento baseline/candidate | Runs e grades referenciadas | Delta de score |

O oracle esperado, já coberto pelo teste de aceitação, é baseline `0`, candidate `1` e
`added_root_cause: true`. Isso é uma expectativa determinística do protocolo, não o relato de uma
nova Run. Este dossier não cria referências `run:`, `event:` ou `artifact:`.

Não há judge, revisão humana obrigatória ou score multidimensional.

## Stop conditions

- primeira saída terminal do Subject Runner;
- timeout do budget;
- erro estrutural ao compor o contexto;
- falha do runner ou do grader.

A causa terminal efetiva pertence ao runtime e deve ser preservada em evento; a definição apenas
declara as condições possíveis.

## Visibilidade

| Dado | Lab Agent | Subject Runner | Grader | Humano |
| --- | --- | --- | --- | --- |
| Intenção e hipótese | Sim | Não | Não necessário | Sim |
| Goal compilado | Sim | Sim | Sim | Sim |
| Fixture completa | Autorizado | Não | Não | Autorizado |
| Context Snapshot selecionado | Autorizado | Sim | Sim | Autorizado |
| Expected answer | Sim | Não | Sim | Sim |
| Resultado da outra variant | Após conclusão | Não | Não | Sim |

## Canônico, runtime e derivado

| Categoria | Elementos deste cenário |
| --- | --- |
| Definição canônica pré-Run | Scenario revision, experiment revision, Goal, variants, Context Policies, grader e stop conditions |
| Registro canônico de runtime | Run events, Context Snapshot, resposta, evidência citada, Grade e causa terminal |
| Derivado reconstruível | Context Diff, delta, relatório, cards e gráficos |

## Limitações e linguagem permitida

- O cenário verifica infraestrutura e observabilidade de contexto; não mede capacidade de LLM.
- Uma repetição não demonstra estabilidade estatística.
- A linguagem causal fica limitada à mudança controlada de Context Policy nesta fixture.
- O resultado não autoriza generalização para outros logs, policies, modelos ou tarefas.
- Falhas de integridade estrutural ou de evidência invalidam a comparação antes do score.

## Compatibilidade e hipótese de contrato

O cenário cabe no `ExperimentManifest v1` e nos contratos atuais. Para o discovery, ele exige apenas
um núcleo conceitual com Goal separado da avaliação, ambiente, inputs, interação terminal,
Evaluation Plan, stop conditions, visibilidade e limitações. Tools, skills, checkpoints, findings e
fork não devem ser promovidos a campos universais obrigatórios por causa dos outros cenários.

Ver a [comparação transversal](comparison.md).
