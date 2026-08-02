---
id: contract-lab-agent-errors-v1
type: contract
title: Erros estáveis do Lab Agent v1
status: accepted
authority: normative
volatility: timeless
owner: core
created_at: 2026-08-02
updated_at: 2026-08-02
applies_to: schema/lab-agent-error@1
sources:
  - docs/adr/0024-lab-agent-native-tool-runtime.md
  - docs/contracts/lab-agent-scope-v1.md
  - docs/contracts/lab-agent-tools-v1.md
  - docs/contracts/observable-errors.md
  - docs/contracts/triage-error.md
supersedes: []
superseded_by: null
implementation_refs: []
verification_refs: []
---

# Erros estáveis do Lab Agent v1

O Lab Agent recusa por código estável, nunca por texto. Este contrato declara a representação, o
catálogo e as duas propriedades que distinguem estas recusas das demais costuras do produto. Está
aceito e ainda não possui runtime.

Ele é uma costura separada de `TriageError` e `ScopeError` pela mesma razão que aquelas duas são
separadas entre si: recusar uma tool call de copiloto não é uma das seis fases que antecedem uma Run,
nem a criação de uma fronteira do Control Plane. Ver
[catálogo de erros observáveis](observable-errors.md).

## Representação

`LabAgentError` contém:

| Campo | Tipo | Obrigatório | Regra |
| --- | --- | --- | --- |
| `stage` | enum | sim | etapa de verificação que recusou |
| `code` | enum | sim | identificador estável prefixado pela etapa |
| `category` | enum | sim | derivada do código, nunca da mensagem |
| `message` | texto | sim | português brasileiro, livre e traduzível |
| `field_path` | lista de texto | não | caminho do argumento culpado |
| `remediation` | texto | sim | próxima ação válida, endereçada ao modelo |
| `tool_name` | texto | não | tool recusada, quando aplicável |

`remediation` é **obrigatória** neste contrato, ao contrário de `TriageError`, onde é opcional. A razão
é o consumidor: aqui o leitor primário da recusa é o modelo, dentro do laço. Uma recusa que apenas
nega convida à repetição; uma recusa que nomeia a próxima ação válida encerra a tentativa. É assim que
o produto evita laço de tool call sem heurística.

Mensagem não é contrato. Código, categoria, etapa, forma do payload, status HTTP e exit code são.

## Etapas

| Etapa | Recusa |
| --- | --- |
| `catalog` | tool inexistente ou não oferecida naquela forma de sessão |
| `budget` | teto do turno alcançado |
| `schema` | argumentos fora do schema estrito |
| `scope` | ref fora do Workspace/Project da sessão |
| `classification` | conteúdo classificado sem grant |
| `authority` | a chamada exigiria autoridade humana |
| `draft` | documento proposto não sobrevive à validação |

As etapas espelham a ordem de verificação do [loop v1](lab-agent-loop-v1.md). `authority` e `draft`
não são posições do laço: são recusas de natureza, que valem em qualquer ponto.

## Catálogo

| Código | Categoria | Significado |
| --- | --- | --- |
| `catalog.tool_unknown` | `not_found` | o nome não existe no catálogo efetivo |
| `catalog.tool_not_offered` | `not_found` | a tool existe, mas não nesta forma de sessão |
| `budget.tool_calls_exhausted` | `exhausted` | o teto de tool calls do turno foi alcançado |
| `budget.round_trips_exhausted` | `exhausted` | o teto de idas ao provider foi alcançado |
| `budget.wall_time_exhausted` | `exhausted` | o teto de tempo do turno foi alcançado |
| `budget.refusals_exhausted` | `exhausted` | o turno só produziu recusas até o teto |
| `budget.refusal_repeated` | `exhausted` | a mesma tool call recusada foi repetida |
| `schema.argument_set_invalid` | `invalid` | o conjunto de chaves não é exatamente o declarado |
| `schema.argument_type_invalid` | `invalid` | um argumento tem tipo divergente |
| `schema.argument_limit_exceeded` | `invalid` | um valor excede o teto declarado no schema |
| `schema.scope_argument_forbidden` | `invalid` | os argumentos declaram scope, sessão ou ator |
| `scope.target_not_visible` | `not_found` | o alvo não existe ou não pertence ao scope |
| `scope.focus_mismatch` | `not_found` | o foco declarado não pertence ao Project da sessão |
| `scope.project_required` | `rejected` | a operação exige Project chat e a sessão é General |
| `classification.grant_required` | `forbidden` | o conteúdo exige grant que o Lab Agent não tem |
| `authority.human_decision_required` | `rejected` | a ação é decisão humana e não pode ser proposta como fato |
| `authority.ledger_write_forbidden` | `rejected` | a ação escreveria no event ledger |
| `authority.persisted_effect_forbidden` | `rejected` | a ação criaria record persistido fora de draft |
| `draft.validation_failed` | `invalid` | o documento não satisfaz o contrato declarado |
| `draft.not_validated` | `rejected` | a proposta não passou por validação antes de ser registrada |
| `draft.scope_override_forbidden` | `rejected` | o documento tenta declarar Project divergente da sessão |

Cada código recebe entrada nas tabelas de status HTTP e exit code no mesmo patch que o declara. As
tabelas são totais e a verificação falha quando um código fica sem entrada.

## Indistinguibilidade

`scope.target_not_visible` é um único código para três situações distintas: o alvo não existe, existe
em outro Project do mesmo Workspace, ou existe em outro Workspace.

Isso é normativo e é o ponto central deste contrato. Códigos diferentes para "não existe" e "não é
seu" transformariam a mensagem de erro num oráculo de existência: quem quisesse descobrir se um Study
existe em outro Project bastaria pedi-lo e ler o código de volta.

A propriedade tem três consequências que a implementação precisa preservar:

- mesma `category`, mesmo status HTTP e mesma forma de payload nos três casos;
- `message` não menciona o alvo, seu tipo, seu Project nem sua existência;
- `remediation` não sugere "peça acesso", porque isso confirmaria que há algo a acessar.

`scope.focus_mismatch` segue a mesma regra. `scope.project_required` é diferente e pode ser explícito:
ele não fala sobre um alvo, fala sobre a forma da sessão, que o humano já conhece.

## Remediação acionável

A remediação é redigida para que a próxima tentativa do modelo seja válida ou inexistente. Ela nomeia
a ação, não o problema.

| Situação | Remediação que funciona | Remediação que causa laço |
| --- | --- | --- |
| tool não oferecida em General chat | "Peça ao humano para abrir uma Project chat; esta leitura não existe aqui." | "Tool não disponível." |
| conjunto de argumentos inválido | "Use exatamente estas chaves: `<lista>`." | "Argumentos inválidos." |
| alvo não visível | "Liste os alvos deste Project antes de referenciar um id." | "Alvo não encontrado; verifique o id." |
| draft inválido | "Corrija `<field_path>` e valide de novo antes de propor." | "Documento inválido." |
| decisão humana | "Registre um pedido de aprovação; a decisão é do humano." | "Não autorizado." |

A coluna da direita é o modo de falha real: uma negação sem próxima ação faz o modelo tentar variações
até esgotar budget. A coluna da esquerda encerra a tentativa porque descreve o caminho válido.

Recusa de alvo não visível instrui a **listar** em vez de tentar outro id. Sem isso, o modelo enumera
ids e cada tentativa é uma recusa, o que é exatamente o laço que `budget.refusals_exhausted` teria de
cortar.

## Tradução nas bordas

A borda HTTP traduz por código, lendo apenas as tabelas. A borda de stream para a UI emite o evento de
erro com código, mensagem e remediação. A recusa devolvida ao modelo dentro do laço usa a mesma
representação: um consumidor não precisa saber se leu a recusa do provider, da API ou da UI.

Falha de provider não pertence a este catálogo. Ela já é coberta por `ProviderRequestError`, com
código sanitizado, e chega ao humano como terminal `provider_failed`.

## Provas mínimas

- alvo inexistente, alvo de Project irmão e alvo de outro Workspace produzem código, categoria, status
  e forma de payload idênticos;
- nenhuma mensagem de recusa de scope menciona tipo, nome, Project ou existência do alvo;
- toda recusa carrega `remediation` não vazia;
- as tabelas de status HTTP e exit code são totais sobre o enum;
- `schema.scope_argument_forbidden` recusa argumentos que declarem `project_id` ou `workspace_id`;
- `authority.*` recusa com o mesmo código que a superfície humana usaria para a mesma tentativa;
- `draft.not_validated` impede registro de proposta não validada;
- código antigo nunca é reutilizado com significado novo.
